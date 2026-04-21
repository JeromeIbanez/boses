"""
Survey simulation engine.

Each persona in the group fills out the uploaded survey independently via AI.
Results are stored as survey_individual (per persona) and survey_aggregate (roll-up).
"""
import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from app.services.openai_client import get_openai_client
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.persona import Persona
from app.models.simulation import Simulation
from app.models.simulation_result import SimulationResult
from app.services.prompts import survey_system_prompt, survey_user_prompt, survey_aggregate_user_prompt

logger = logging.getLogger(__name__)


def _parse_json(raw: str | None, fallback: object) -> object:
    """Parse JSON from an OpenAI response, stripping markdown code fences if present."""
    if not raw or not raw.strip():
        return fallback
    text = raw.strip()
    # Strip ```json ... ``` or ``` ... ``` wrappers
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop first line (```json or ```) and last line (```)
        inner = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = inner.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last resort: find the first { or [ and parse from there
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            s = text.find(start_char)
            e = text.rfind(end_char)
            if s != -1 and e > s:
                try:
                    return json.loads(text[s:e + 1])
                except json.JSONDecodeError:
                    pass
        return fallback


def _build_survey_prompt(persona: "Persona", briefing_text: str, questions: list[dict]) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for a persona filling out the survey."""
    sys_prompt = survey_system_prompt(persona, briefing_text)

    question_lines = []
    for q in questions:
        if q["type"] == "likert":
            scale = q.get("scale", 5)
            low = q.get("low_label", "Strongly disagree")
            high = q.get("high_label", "Strongly agree")
            question_lines.append(
                f'- id: "{q["id"]}", type: likert (1–{scale}, where 1={low}, {scale}={high})\n  Question: {q["text"]}'
            )
        elif q["type"] == "multiple_choice" and q.get("options"):
            opts = ", ".join(f'"{o}"' for o in q["options"])
            question_lines.append(
                f'- id: "{q["id"]}", type: multiple_choice (choose one: {opts})\n  Question: {q["text"]}'
            )
        else:
            question_lines.append(
                f'- id: "{q["id"]}", type: open_ended\n  Question: {q["text"]}'
            )

    return sys_prompt, survey_user_prompt(question_lines)


_MAX_PARALLEL_PERSONAS = 5


def _survey_persona_worker(persona, briefing_text: str, questions: list) -> tuple:
    """Run a single persona's survey via LLM. DB-free — no session needed."""
    client = get_openai_client()
    system_prompt, user_prompt = _build_survey_prompt(persona, briefing_text, questions)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.85,
    )
    raw = response.choices[0].message.content
    answers = _parse_json(raw, [])
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
    return persona, enriched


def run_survey(simulation_id: str) -> None:
    client = get_openai_client()
    db = SessionLocal()
    db.expire_on_commit = False  # prevent concurrent lazy-loads in worker threads
    try:
        simulation = db.get(Simulation, simulation_id)
        if not simulation:
            return

        simulation.status = "running"
        db.commit()

        from app.services.simulation_engine import get_personas_for_simulation
        personas = get_personas_for_simulation(simulation, db)

        questions: list[dict] = (simulation.survey_schema or {}).get("questions", [])
        if not questions:
            raise ValueError("No questions found in survey schema.")

        from app.services.briefing_utils import combine_briefing_texts
        briefing_text = combine_briefing_texts(simulation.briefings)
        individual_results = []
        failed_personas: list[dict] = []
        sim_ref = simulation_id[:8]
        total = len(personas)

        simulation.progress = {
            "current": 0,
            "total": total,
            "current_name": None,
            "completed": [],
            "failed": [],
            "stage": "interviewing",
        }
        db.commit()

        with ThreadPoolExecutor(max_workers=min(total, _MAX_PARALLEL_PERSONAS)) as executor:
            futures = {
                executor.submit(_survey_persona_worker, persona, briefing_text, questions): persona
                for persona in personas
            }
            for future in as_completed(futures):
                persona = futures[future]
                try:
                    _, enriched = future.result()
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
                    failed_personas.append({
                        "name": persona.full_name,
                        "persona_id": str(persona.id),
                        "error": str(persona_err),
                        "stage": "interviewing",
                    })

        if not individual_results:
            raise RuntimeError(f"All {len(personas)} persona(s) failed to respond.")
        if failed_personas:
            simulation.failed_personas = failed_personas
            simulation.error_message = (
                f"{len(failed_personas)} of {len(personas)} persona(s) failed: "
                + ", ".join(f["name"] for f in failed_personas)
            )

        # Aggregate
        simulation.progress = {
            "current": total,
            "total": total,
            "current_name": None,
            "completed": [p.full_name for p, _ in individual_results],
            "failed": [f["name"] for f in failed_personas],
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
                        oe_json = _parse_json(oe_response.choices[0].message.content, {})
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
            sv_groups = simulation.persona_groups or []
            group = sv_groups[0] if sv_groups else simulation.persona_group
            sv_group_label = group.name if group else "Persona Group"
            if len(sv_groups) > 1:
                sv_group_label = f"{sv_group_label} + {len(sv_groups) - 1} more group{'s' if len(sv_groups) > 2 else ''}"
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
                        survey_aggregate_user_prompt(
                            sv_group_label,
                            group.location if group else None,
                            group.occupation if group else None,
                            group.age_min if group else None,
                            group.age_max if group else None,
                            len(individual_results), summary_context,
                        )
                    ),
                }],
                temperature=0.7,
            )
            exec_json = _parse_json(exec_response.choices[0].message.content, {})
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
        _trigger_scoring(simulation_id)

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
        _trigger_scoring(simulation_id)
    finally:
        db.close()


def _trigger_scoring(simulation_id: str) -> None:
    try:
        from app.services.simulation_engine import _trigger_post_completion_scoring
        _trigger_post_completion_scoring(simulation_id)
    except Exception:
        pass
