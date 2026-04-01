"""
Survey simulation engine.

Each persona in the group fills out the uploaded survey independently via AI.
Results are stored as survey_individual (per persona) and survey_aggregate (roll-up).
"""
import json
import logging
from collections import defaultdict
from datetime import datetime

from openai import OpenAI
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.persona import Persona
from app.models.simulation import Simulation
from app.models.simulation_result import SimulationResult

logger = logging.getLogger(__name__)


def _build_survey_prompt(persona: "Persona", briefing_text: str, questions: list[dict]) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for a persona filling out the survey."""
    traits = ", ".join(persona.personality_traits or [])
    briefing_block = (
        f"\n\nFor context, here is background material relevant to this survey:\n---\n{briefing_text}\n---"
        if briefing_text else ""
    )
    system_prompt = (
        f"You are {persona.full_name}, a {persona.age}-year-old {persona.gender} from {persona.location}. "
        f"You work as {persona.occupation} and earn a {persona.income_level} income. "
        f"Background: {persona.educational_background or 'Not specified'}. "
        f"Family: {persona.family_situation or 'Not specified'}. "
        f"Personality: {traits or 'Not specified'}. "
        f"What drives you: {persona.values_and_motivations or 'Not specified'}. "
        f"Your frustrations: {persona.pain_points or 'Not specified'}. "
        f"Media habits: {persona.media_consumption or 'Not specified'}. "
        f"Purchase behavior: {persona.purchase_behavior or 'Not specified'}. "
        "You are filling out a market research survey. Answer authentically as this person — "
        "in their real voice, with their genuine opinions and concerns. Do not break character."
        f"{briefing_block}"
    )

    question_lines = []
    for q in questions:
        if q["type"] == "likert":
            scale = q.get("scale", 5)
            low = q.get("low_label", "Strongly disagree")
            high = q.get("high_label", "Strongly agree")
            question_lines.append(
                f'- id: "{q["id"]}", type: likert (1–{scale}, where 1={low}, {scale}={high})\n  Question: {q["text"]}'
            )
        elif q["type"] == "multiple_choice":
            opts = ", ".join(f'"{o}"' for o in q.get("options", []))
            question_lines.append(
                f'- id: "{q["id"]}", type: multiple_choice (choose one: {opts})\n  Question: {q["text"]}'
            )
        else:
            question_lines.append(
                f'- id: "{q["id"]}", type: open_ended\n  Question: {q["text"]}'
            )

    user_prompt = (
        "Please fill out the following survey questions as yourself. "
        "Return ONLY a valid JSON array — no markdown, no explanation. "
        "Each element: {\"id\": \"<question id>\", \"answer\": <value>}.\n"
        "For likert: answer is an integer.\n"
        "For multiple_choice: answer is the exact option string.\n"
        "For open_ended: answer is a string (2–4 sentences).\n\n"
        "QUESTIONS:\n" + "\n".join(question_lines)
    )
    return system_prompt, user_prompt


def run_survey(simulation_id: str) -> None:
    client = OpenAI(api_key=settings.openai_api_key)
    db = SessionLocal()
    try:
        simulation = db.get(Simulation, simulation_id)
        if not simulation:
            return

        simulation.status = "running"
        db.commit()

        personas = db.execute(
            select(Persona).where(Persona.persona_group_id == simulation.persona_group_id)
        ).scalars().all()

        if not personas:
            raise ValueError("No personas found for this group.")

        questions: list[dict] = (simulation.survey_schema or {}).get("questions", [])
        if not questions:
            raise ValueError("No questions found in survey schema.")

        briefing_text = simulation.briefing.extracted_text or "" if simulation.briefing else ""
        individual_results = []
        failed_personas = []
        sim_ref = simulation_id[:8]
        total = len(personas)

        for i, persona in enumerate(personas, 1):
            logger.info(f"[survey:{sim_ref}] Persona {i}/{total}: {persona.full_name}")
            simulation.progress = {
                "current": i,
                "total": total,
                "current_name": persona.full_name,
                "completed": [p.full_name for p, _ in individual_results],
                "failed": failed_personas[:],
                "stage": "interviewing",
            }
            db.commit()

            try:
                system_prompt, user_prompt = _build_survey_prompt(persona, briefing_text, questions)
                response = client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.85,
                )
                raw = response.choices[0].message.content or "[]"
                answers = json.loads(raw)

                # Attach question text/type to each answer for display convenience
                q_map = {q["id"]: q for q in questions}
                enriched = []
                for a in answers:
                    q = q_map.get(a.get("id", ""), {})
                    enriched.append({
                        "id": a.get("id"),
                        "question_text": q.get("text", ""),
                        "type": q.get("type", "open_ended"),
                        "answer": a.get("answer"),
                        "options": q.get("options"),
                        "scale": q.get("scale"),
                        "low_label": q.get("low_label"),
                        "high_label": q.get("high_label"),
                    })

                result = SimulationResult(
                    simulation_id=simulation_id,
                    persona_id=persona.id,
                    result_type="survey_individual",
                    report_sections={"answers": enriched},
                )
                db.add(result)
                db.flush()
                individual_results.append((persona, enriched))
                logger.info(f"[survey:{sim_ref}] ✓ {persona.full_name}")
            except Exception as persona_err:
                logger.error(f"[survey:{sim_ref}] ✗ {persona.full_name}: {persona_err}")
                failed_personas.append(persona.full_name)

        if not individual_results:
            raise RuntimeError(f"All {len(personas)} persona(s) failed to respond.")
        if failed_personas:
            simulation.error_message = (
                f"{len(failed_personas)} of {len(personas)} persona(s) failed: "
                + ", ".join(failed_personas)
            )

        # Aggregate
        simulation.progress = {
            "current": total,
            "total": total,
            "current_name": None,
            "completed": [p.full_name for p, _ in individual_results],
            "failed": failed_personas[:],
            "stage": "generating_report",
        }
        db.commit()

        per_question_agg = []
        open_ended_summaries = []

        for q in questions:
            qid = q["id"]
            answers_for_q = []
            for _, enriched in individual_results:
                for a in enriched:
                    if a["id"] == qid:
                        answers_for_q.append(a["answer"])
                        break

            if q["type"] == "likert":
                nums = [a for a in answers_for_q if isinstance(a, (int, float))]
                scale = q.get("scale", 5)
                dist = {str(k): 0 for k in range(1, scale + 1)}
                for n in nums:
                    key = str(max(1, min(scale, int(round(n)))))
                    dist[key] = dist.get(key, 0) + 1
                avg = round(sum(nums) / len(nums), 2) if nums else None
                per_question_agg.append({
                    "id": qid,
                    "type": "likert",
                    "text": q["text"],
                    "scale": scale,
                    "low_label": q.get("low_label"),
                    "high_label": q.get("high_label"),
                    "average": avg,
                    "distribution": dist,
                    "n": len(nums),
                })

            elif q["type"] == "multiple_choice":
                dist: dict[str, int] = defaultdict(int)
                for a in answers_for_q:
                    if isinstance(a, str):
                        dist[a] += 1
                per_question_agg.append({
                    "id": qid,
                    "type": "multiple_choice",
                    "text": q["text"],
                    "options": q.get("options", []),
                    "distribution": dict(dist),
                    "n": len(answers_for_q),
                })

            else:  # open_ended
                text_answers = [a for a in answers_for_q if isinstance(a, str) and a.strip()]
                themes = []
                notable_quotes = []
                if text_answers:
                    try:
                        joined = "\n".join(f"- {a}" for a in text_answers)
                        oe_response = client.chat.completions.create(
                            model=settings.OPENAI_MODEL,
                            messages=[{
                                "role": "user",
                                "content": (
                                    f"Question: {q['text']}\n\n"
                                    f"Responses:\n{joined}\n\n"
                                    "Return ONLY valid JSON (no markdown) with:\n"
                                    '{"themes": ["theme1", "theme2", ...], "notable_quotes": ["quote1", "quote2"]}\n'
                                    "themes: 3–5 recurring themes (short phrases).\n"
                                    "notable_quotes: 2–3 most insightful verbatim responses."
                                ),
                            }],
                            temperature=0.5,
                        )
                        oe_json = json.loads(oe_response.choices[0].message.content or "{}")
                        themes = oe_json.get("themes", [])
                        notable_quotes = oe_json.get("notable_quotes", [])
                    except Exception as e:
                        logger.error(f"[survey:{sim_ref}] Open-ended synthesis failed for {qid}: {e}")

                per_question_agg.append({
                    "id": qid,
                    "type": "open_ended",
                    "text": q["text"],
                    "themes": themes,
                    "notable_quotes": notable_quotes,
                    "n": len(text_answers),
                })
                open_ended_summaries.append(f"Q: {q['text']}\nThemes: {', '.join(themes)}")

        # Overall executive summary
        executive_summary = ""
        recommendations = ""
        try:
            group = simulation.persona_group
            summary_context = "\n".join(
                f"- {p.get('text', '')} ({p.get('type')}): "
                + (f"avg {p.get('average')}/{p.get('scale')}" if p["type"] == "likert"
                   else (f"top answer: {max(p.get('distribution', {}).items(), key=lambda x: x[1])[0]}" if p["type"] == "multiple_choice" and p.get("distribution")
                         else f"themes: {', '.join(p.get('themes', []))}"))
                for p in per_question_agg
            )
            exec_response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": (
                        f"You are a senior market researcher. {len(individual_results)} respondents "
                        f"from the '{group.name}' group ({group.location}, {group.occupation}, ages {group.age_min}–{group.age_max}) "
                        f"completed a survey. Here are the results per question:\n\n{summary_context}\n\n"
                        "Return ONLY valid JSON (no markdown):\n"
                        '{"executive_summary": "2–3 paragraph narrative", "recommendations": "2–3 actionable bullet points"}'
                    ),
                }],
                temperature=0.7,
            )
            exec_json = json.loads(exec_response.choices[0].message.content or "{}")
            executive_summary = exec_json.get("executive_summary", "")
            recommendations = exec_json.get("recommendations", "")
        except Exception as e:
            logger.error(f"[survey:{sim_ref}] Executive summary failed: {e}")

        agg_result = SimulationResult(
            simulation_id=simulation_id,
            persona_id=None,
            result_type="survey_aggregate",
            report_sections={
                "per_question": per_question_agg,
                "executive_summary": executive_summary,
                "recommendations": recommendations,
            },
        )
        db.add(agg_result)
        simulation.status = "complete"
        simulation.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"[survey:{sim_ref}] Complete ({len(individual_results)}/{total} personas)")

    except Exception as e:
        logger.error(f"[survey:{simulation_id[:8]}] Failed: {e}")
        try:
            simulation = db.get(Simulation, simulation_id)
            if simulation:
                simulation.status = "failed"
                simulation.error_message = str(e)
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
