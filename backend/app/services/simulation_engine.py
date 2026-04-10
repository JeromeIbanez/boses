import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from app.services.openai_client import get_openai_client
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.persona import Persona
from app.models.simulation import Simulation
from app.models.simulation_result import SimulationResult
from app.services.prompts import concept_test_system_prompt, concept_test_user_prompt, concept_test_aggregate_user_prompt

logger = logging.getLogger(__name__)

SENTIMENT_SCORES = {"Positive": 1.0, "Neutral": 0.0, "Negative": -1.0}


def _parse_individual_response(text: str) -> dict:
    sections = {
        "reaction": "",
        "sentiment": "Neutral",
        "reasoning": "",
        "notable_quote": "",
        "key_themes": [],
    }
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("1. REACTION:") or upper.startswith("REACTION:"):
            current = "reaction"
            sections["reaction"] = stripped.split(":", 1)[-1].strip()
        elif upper.startswith("2. SENTIMENT:") or upper.startswith("SENTIMENT:"):
            current = "sentiment"
            val = stripped.split(":", 1)[-1].strip().capitalize()
            sections["sentiment"] = val if val in ("Positive", "Neutral", "Negative") else "Neutral"
        elif upper.startswith("3. REASONING:") or upper.startswith("REASONING:"):
            current = "reasoning"
            sections["reasoning"] = stripped.split(":", 1)[-1].strip()
        elif upper.startswith("4. NOTABLE QUOTE:") or upper.startswith("NOTABLE QUOTE:"):
            current = "notable_quote"
            sections["notable_quote"] = stripped.split(":", 1)[-1].strip()
        elif upper.startswith("5. KEY THEMES:") or upper.startswith("KEY THEMES:"):
            current = "key_themes"
            raw_themes = stripped.split(":", 1)[-1].strip()
            sections["key_themes"] = [t.strip() for t in raw_themes.split(",") if t.strip()]
        elif stripped and current:
            if current == "key_themes":
                sections["key_themes"].extend([t.strip() for t in stripped.split(",") if t.strip()])
            else:
                sections[current] += " " + stripped
    return sections


def _parse_aggregate_response(text: str) -> dict:
    sections = {
        "overall_sentiment": "",
        "distribution": {},
        "top_themes": [],
        "summary": "",
        "recommendations": "",
    }
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("1. OVERALL SENTIMENT:") or upper.startswith("OVERALL SENTIMENT:"):
            current = "overall_sentiment"
            sections["overall_sentiment"] = stripped.split(":", 1)[-1].strip()
        elif upper.startswith("2. SENTIMENT DISTRIBUTION:") or upper.startswith("SENTIMENT DISTRIBUTION:"):
            current = "distribution"
        elif upper.startswith("3. TOP THEMES:") or upper.startswith("TOP THEMES:"):
            current = "top_themes"
            raw = stripped.split(":", 1)[-1].strip()
            if raw:
                sections["top_themes"] = [t.strip() for t in raw.split(",") if t.strip()]
        elif upper.startswith("4. SUMMARY:") or upper.startswith("SUMMARY:"):
            current = "summary"
            sections["summary"] = stripped.split(":", 1)[-1].strip()
        elif upper.startswith("5. STRATEGIC RECOMMENDATIONS:") or upper.startswith("STRATEGIC RECOMMENDATIONS:"):
            current = "recommendations"
            sections["recommendations"] = stripped.split(":", 1)[-1].strip()
        elif stripped and current:
            if current == "distribution":
                # Parse lines like "Positive: 3" or "- Positive: 3"
                if ":" in stripped:
                    k, v = stripped.lstrip("- ").split(":", 1)
                    try:
                        sections["distribution"][k.strip()] = int(v.strip())
                    except ValueError:
                        pass
            elif current == "top_themes" and not sections["top_themes"]:
                sections["top_themes"] = [t.strip() for t in stripped.split(",") if t.strip()]
            else:
                sections[current] += " " + stripped
    return sections


_MAX_PARALLEL_PERSONAS = 5


def _concept_test_persona_worker(
    persona,
    briefing_text: str,
    prompt_question: str,
) -> tuple:
    """Run a single persona's concept test LLM call. DB-free — no session needed."""
    client = get_openai_client()
    system_prompt = concept_test_system_prompt(persona)
    user_prompt = concept_test_user_prompt(briefing_text, prompt_question)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
    )
    raw_text = response.choices[0].message.content or ""
    return persona, _parse_individual_response(raw_text)


def run_simulation(simulation_id: str) -> None:
    from app.services.idi_engine import run_idi_ai  # local import avoids circular dependency

    # Route to the appropriate engine based on simulation type
    _db = SessionLocal()
    try:
        _sim = _db.get(Simulation, simulation_id)
        sim_type = _sim.simulation_type if _sim else "concept_test"
    finally:
        _db.close()

    if sim_type == "idi_ai":
        run_idi_ai(simulation_id)
        return
    if sim_type == "idi_manual":
        return  # manual sessions are driven by the chat endpoint
    if sim_type == "survey":
        from app.services.survey_engine import run_survey
        run_survey(simulation_id)
        return
    if sim_type == "focus_group":
        from app.services.focus_group_engine import run_focus_group
        run_focus_group(simulation_id)
        return
    if sim_type == "conjoint":
        from app.services.conjoint_engine import run_conjoint
        run_conjoint(simulation_id)
        return

    # concept_test path
    client = get_openai_client()
    db = SessionLocal()
    # See idi_engine.py — same reason: prevent concurrent lazy-loads in worker threads.
    db.expire_on_commit = False
    try:
        simulation = db.get(Simulation, simulation_id)
        if not simulation:
            return

        simulation.status = "running"
        db.commit()

        # Load personas for this group
        personas = db.execute(
            select(Persona).where(Persona.persona_group_id == simulation.persona_group_id)
        ).scalars().all()

        if not personas:
            raise ValueError("No personas found for this group. Please generate personas first.")

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
                executor.submit(
                    _concept_test_persona_worker,
                    persona,
                    briefing_text,
                    simulation.prompt_question,
                ): persona
                for persona in personas
            }
            for future in as_completed(futures):
                persona = futures[future]
                try:
                    _, parsed = future.result()
                    result = SimulationResult(
                        simulation_id=simulation_id,
                        persona_id=persona.id,
                        result_type="individual",
                        sentiment=parsed["sentiment"],
                        sentiment_score=SENTIMENT_SCORES.get(parsed["sentiment"], 0.0),
                        reaction_text=parsed["reaction"] + (" " + parsed["reasoning"]).rstrip(),
                        key_themes=parsed["key_themes"] or None,
                        notable_quote=parsed["notable_quote"] or None,
                    )
                    db.add(result)
                    db.flush()
                    individual_results.append((persona, parsed))
                    logger.info(f"[sim:{sim_ref}] ✓ {persona.full_name} ({parsed['sentiment']})")
                except Exception as persona_err:
                    logger.error(f"[sim:{sim_ref}] ✗ {persona.full_name} failed: {persona_err}")
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

        # Aggregate summary
        group = simulation.persona_group
        reactions_text = "\n".join(
            f"[{p.full_name}, {p.age}, {p.occupation}]: "
            f"{r['reaction']} {r['reasoning']} | Sentiment: {r['sentiment']}"
            for p, r in individual_results
        )

        agg_prompt = concept_test_aggregate_user_prompt(
            n=len(individual_results),
            group_name=group.name,
            group_location=group.location,
            group_occupation=group.occupation,
            age_min=group.age_min,
            age_max=group.age_max,
            prompt_question=simulation.prompt_question,
            reactions_text=reactions_text,
        )

        agg_response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": agg_prompt}],
            temperature=0.7,
        )

        agg_text = agg_response.choices[0].message.content or ""
        agg_parsed = _parse_aggregate_response(agg_text)

        # Build sentiment distribution from individual results
        dist: dict[str, int] = {"Positive": 0, "Neutral": 0, "Negative": 0}
        for _, r in individual_results:
            dist[r["sentiment"]] = dist.get(r["sentiment"], 0) + 1

        agg_result = SimulationResult(
            simulation_id=simulation_id,
            persona_id=None,
            result_type="aggregate",
            summary_text=agg_parsed["summary"].strip(),
            sentiment_distribution=dist,
            top_themes=agg_parsed["top_themes"] or None,
            recommendations=agg_parsed["recommendations"].strip() or None,
        )
        db.add(agg_result)

        simulation.status = "complete"
        simulation.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"[sim:{sim_ref}] Simulation complete ({len(individual_results)}/{len(personas)} personas)")
        _trigger_post_completion_scoring(simulation_id)

    except Exception as e:
        logger.error(f"[sim:{simulation_id[:8]}] Simulation failed: {e}")
        try:
            simulation = db.get(Simulation, simulation_id)
            if simulation:
                simulation.status = "failed"
                simulation.error_message = str(e)
                db.commit()
        except Exception:
            db.rollback()
        _trigger_post_completion_scoring(simulation_id)
    finally:
        db.close()


def _trigger_post_completion_scoring(simulation_id: str) -> None:
    """Fire-and-forget: score reproducibility + send Slack notification."""
    try:
        from app.services.benchmarking_service import maybe_score_reproducibility
        maybe_score_reproducibility(simulation_id)
    except Exception as e:
        logger.warning(f"Post-completion scoring skipped for {simulation_id[:8]}: {e}")

    try:
        from app.services.slack_notifier import maybe_notify_slack
        from app.services.email_notifier import maybe_notify_email
        from app.database import SessionLocal
        from app.models.simulation import Simulation as _Sim
        _db = SessionLocal()
        try:
            _sim = _db.get(_Sim, simulation_id)
            _status = _sim.status if _sim else "failed"
        finally:
            _db.close()
        maybe_notify_slack(simulation_id, _status)
        maybe_notify_email(simulation_id, _status)
    except Exception as e:
        logger.warning(f"Notifications skipped for {simulation_id[:8]}: {e}")
