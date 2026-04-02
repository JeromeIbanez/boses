"""
Focus Group simulation engine.

Runs a multi-turn group discussion where personas react to each other's
statements, surfacing consensus and disagreement. A moderator LLM call
guides the session at the opening and between rounds.

Flow:
  1. Moderator opening  — introduces topic, poses first question
  2. Round 1            — each persona gives an initial response
  3. Moderator bridge   — synthesises Round 1, poses follow-up question
  4. Round 2            — each persona reacts to others + bridge question
  5. Aggregate report   — extract consensus themes, disagreements, summary
"""
import logging
from datetime import datetime

from openai import OpenAI
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.persona import Persona
from app.models.simulation import Simulation
from app.models.simulation_result import SimulationResult
from app.services.prompts import (
    focus_group_system_prompt,
    focus_group_round2_user_prompt,
    FOCUS_GROUP_MODERATOR_SYSTEM_PROMPT,
    focus_group_moderator_opening_user_prompt,
    focus_group_moderator_bridge_user_prompt,
    focus_group_aggregate_user_prompt,
)

logger = logging.getLogger(__name__)

SENTIMENT_SCORES = {"Positive": 1.0, "Neutral": 0.0, "Negative": -1.0}




def _moderator_opening(client: OpenAI, topic: str, briefing_text: str, n_participants: int) -> str:
    """Generate the moderator's opening statement and first question."""
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": FOCUS_GROUP_MODERATOR_SYSTEM_PROMPT},
            {"role": "user", "content": focus_group_moderator_opening_user_prompt(topic, briefing_text, n_participants)},
        ],
        temperature=0.7,
    )
    return (response.choices[0].message.content or "").strip()


def _moderator_bridge(client: OpenAI, topic: str, round1_entries: list[dict]) -> str:
    """Generate the moderator's bridge between Round 1 and Round 2."""
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": FOCUS_GROUP_MODERATOR_SYSTEM_PROMPT},
            {"role": "user", "content": focus_group_moderator_bridge_user_prompt(topic, round1_entries)},
        ],
        temperature=0.7,
    )
    return (response.choices[0].message.content or "").strip()


def _persona_round1_response(client: OpenAI, system_prompt: str, opening: str) -> str:
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": opening},
        ],
        temperature=0.9,
    )
    return (response.choices[0].message.content or "").strip()


def _persona_round2_response(
    client: OpenAI,
    system_prompt: str,
    opening: str,
    round1_entries: list[dict],
    bridge: str,
    persona_name: str,
) -> str:
    # Present Round 1 responses from *other* participants
    others = [e for e in round1_entries if e["speaker"] != persona_name]
    others_block = "\n".join(f"- {e['speaker']}: {e['text']}" for e in others)
    user_prompt = focus_group_round2_user_prompt(opening, others_block, bridge)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
    )
    return (response.choices[0].message.content or "").strip()


def _generate_aggregate_report(
    client: OpenAI,
    topic: str,
    transcript: list[dict],
    group_name: str,
) -> dict:
    """Synthesise the full transcript into a structured aggregate report."""
    transcript_text = "\n".join(
        f"[{e['speaker']} — Round {e['round']}]: {e['text']}"
        for e in transcript
    )

    prompt = focus_group_aggregate_user_prompt(topic, transcript_text, group_name)

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    raw = (response.choices[0].message.content or "").strip()
    return _parse_aggregate_report(raw)


def _parse_aggregate_report(text: str) -> dict:
    result = {
        "moderator_summary": "",
        "consensus_themes": [],
        "disagreements": [],
        "sentiment_distribution": {"Positive": 0, "Neutral": 0, "Negative": 0},
        "recommendations": "",
    }
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        upper = stripped.upper()

        if upper.startswith("MODERATOR SUMMARY:"):
            current = "moderator_summary"
            result["moderator_summary"] = stripped.split(":", 1)[-1].strip()
        elif upper.startswith("CONSENSUS THEMES:"):
            current = "consensus_themes"
            raw = stripped.split(":", 1)[-1].strip()
            if raw:
                result["consensus_themes"] = [t.strip() for t in raw.split(",") if t.strip()]
        elif upper.startswith("DISAGREEMENTS:"):
            current = "disagreements"
            raw = stripped.split(":", 1)[-1].strip()
            if raw:
                result["disagreements"] = [t.strip() for t in raw.split(",") if t.strip()]
        elif upper.startswith("SENTIMENT DISTRIBUTION:"):
            current = "distribution"
        elif upper.startswith("RECOMMENDATIONS:"):
            current = "recommendations"
            result["recommendations"] = stripped.split(":", 1)[-1].strip()
        elif stripped and current:
            if current == "moderator_summary":
                result["moderator_summary"] += (" " + stripped) if result["moderator_summary"] else stripped
            elif current == "consensus_themes" and not result["consensus_themes"]:
                result["consensus_themes"] = [t.strip() for t in stripped.split(",") if t.strip()]
            elif current == "disagreements" and not result["disagreements"]:
                result["disagreements"] = [t.strip() for t in stripped.split(",") if t.strip()]
            elif current == "distribution" and ":" in stripped:
                k, v = stripped.lstrip("- ").split(":", 1)
                k = k.strip()
                if k in ("Positive", "Neutral", "Negative"):
                    try:
                        result["sentiment_distribution"][k] = int(v.strip())
                    except ValueError:
                        pass
            elif current == "recommendations":
                result["recommendations"] += (" " + stripped) if result["recommendations"] else stripped

    return result


def run_focus_group(simulation_id: str) -> None:
    client = OpenAI(api_key=settings.openai_api_key)
    db = SessionLocal()
    sim_ref = simulation_id[:8]

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
            raise ValueError("No personas found for this group. Please generate personas first.")

        briefing_text = simulation.briefing.extracted_text if simulation.briefing else ""
        topic = simulation.prompt_question or "the topic under discussion"
        group = simulation.persona_group
        total_personas = len(personas)
        total_steps = total_personas * 2  # round 1 + round 2 per persona
        step = 0

        # ------------------------------------------------------------------ #
        # Moderator opening
        # ------------------------------------------------------------------ #
        logger.info(f"[fg:{sim_ref}] Moderator opening…")
        simulation.progress = {
            "stage": "round_1",
            "current": 0,
            "total": total_personas,
            "current_name": None,
            "completed": [],
            "failed": [],
        }
        db.commit()

        opening = _moderator_opening(client, topic, briefing_text, total_personas)
        transcript: list[dict] = [{"speaker": "Moderator", "round": 0, "text": opening}]

        # ------------------------------------------------------------------ #
        # Round 1 — initial responses
        # ------------------------------------------------------------------ #
        round1_entries: list[dict] = []
        failed_personas: list[str] = []
        round1_per_persona: dict[str, str] = {}  # persona_id → text

        for i, persona in enumerate(personas, 1):
            step += 1
            simulation.progress = {
                "stage": "round_1",
                "current": i,
                "total": total_personas,
                "current_name": persona.full_name,
                "completed": [e["speaker"] for e in round1_entries],
                "failed": failed_personas[:],
            }
            db.commit()
            logger.info(f"[fg:{sim_ref}] Round 1 — {persona.full_name} ({i}/{total_personas})")

            try:
                system_prompt = focus_group_system_prompt(persona, briefing_text)
                text = _persona_round1_response(client, system_prompt, opening)
                entry = {"speaker": persona.full_name, "persona_id": str(persona.id), "round": 1, "text": text}
                round1_entries.append(entry)
                transcript.append(entry)
                round1_per_persona[str(persona.id)] = text
                logger.info(f"[fg:{sim_ref}] ✓ Round 1 {persona.full_name}")
            except Exception as e:
                logger.error(f"[fg:{sim_ref}] ✗ Round 1 {persona.full_name}: {e}")
                failed_personas.append(persona.full_name)

        if not round1_entries:
            raise RuntimeError(f"All {len(personas)} persona(s) failed in Round 1.")

        # ------------------------------------------------------------------ #
        # Moderator bridge
        # ------------------------------------------------------------------ #
        logger.info(f"[fg:{sim_ref}] Moderator bridge…")
        simulation.progress = {
            "stage": "moderator_bridge",
            "current": total_personas,
            "total": total_personas,
            "current_name": None,
            "completed": [e["speaker"] for e in round1_entries],
            "failed": failed_personas[:],
        }
        db.commit()

        # Only include personas that succeeded in Round 1
        bridge = _moderator_bridge(client, topic, round1_entries)
        transcript.append({"speaker": "Moderator", "round": 1, "text": bridge})

        # ------------------------------------------------------------------ #
        # Round 2 — reactions
        # Skip Round 2 entirely if only one persona succeeded (nothing to react to)
        # ------------------------------------------------------------------ #
        round2_per_persona: dict[str, str] = {}

        if len(round1_entries) > 1:
            for i, persona in enumerate(personas, 1):
                if str(persona.id) not in round1_per_persona:
                    continue  # skip personas that failed Round 1

                simulation.progress = {
                    "stage": "round_2",
                    "current": i,
                    "total": total_personas,
                    "current_name": persona.full_name,
                    "completed": [e["speaker"] for e in round1_entries],
                    "failed": failed_personas[:],
                }
                db.commit()
                logger.info(f"[fg:{sim_ref}] Round 2 — {persona.full_name} ({i}/{total_personas})")

                try:
                    system_prompt = focus_group_system_prompt(persona, briefing_text)
                    text = _persona_round2_response(
                        client, system_prompt, opening, round1_entries, bridge, persona.full_name
                    )
                    entry = {"speaker": persona.full_name, "persona_id": str(persona.id), "round": 2, "text": text}
                    transcript.append(entry)
                    round2_per_persona[str(persona.id)] = text
                    logger.info(f"[fg:{sim_ref}] ✓ Round 2 {persona.full_name}")
                except Exception as e:
                    logger.error(f"[fg:{sim_ref}] ✗ Round 2 {persona.full_name}: {e}")
                    # Round 2 failures are non-fatal — persona still has a Round 1 result

        # ------------------------------------------------------------------ #
        # Store individual results
        # ------------------------------------------------------------------ #
        for persona in personas:
            pid = str(persona.id)
            r1 = round1_per_persona.get(pid)
            if not r1:
                continue  # no data for this persona
            r2 = round2_per_persona.get(pid)
            result = SimulationResult(
                simulation_id=simulation_id,
                persona_id=persona.id,
                result_type="focus_group_individual",
                report_sections={
                    "round_1_text": r1,
                    "round_2_text": r2,
                },
            )
            db.add(result)

        # ------------------------------------------------------------------ #
        # Aggregate report
        # ------------------------------------------------------------------ #
        simulation.status = "generating_report"
        simulation.progress = {
            "stage": "generating_report",
            "current": total_personas,
            "total": total_personas,
            "current_name": None,
            "completed": [e["speaker"] for e in round1_entries],
            "failed": failed_personas[:],
        }
        db.commit()
        logger.info(f"[fg:{sim_ref}] Generating aggregate report…")

        agg = _generate_aggregate_report(client, topic, transcript, group.name)

        agg_result = SimulationResult(
            simulation_id=simulation_id,
            persona_id=None,
            result_type="focus_group_aggregate",
            sentiment_distribution=agg["sentiment_distribution"],
            report_sections={
                "transcript": transcript,
                "moderator_summary": agg["moderator_summary"],
                "consensus_themes": agg["consensus_themes"],
                "disagreements": agg["disagreements"],
                "recommendations": agg["recommendations"],
            },
        )
        db.add(agg_result)

        if failed_personas:
            simulation.error_message = (
                f"{len(failed_personas)} of {len(personas)} persona(s) failed in Round 1: "
                + ", ".join(failed_personas)
            )

        simulation.status = "complete"
        simulation.completed_at = datetime.utcnow()
        db.commit()
        logger.info(
            f"[fg:{sim_ref}] Focus group complete — "
            f"{len(round1_per_persona)}/{total_personas} personas participated"
        )

    except Exception as e:
        logger.error(f"[fg:{sim_ref}] Focus group failed: {e}")
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
