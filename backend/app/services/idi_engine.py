"""
IDI (In-Depth Interview) simulation engine.

Handles two modes:
  - run_idi_ai: fully automated — Boses interviews each persona in the group
    using the user's script, then generates a cross-persona IDI report.
  - generate_idi_report_from_messages: manual mode — called after the user
    ends their chat session; generates a single-persona report from the stored
    idi_messages transcript.
"""
import json
import logging
import re
from datetime import datetime

from openai import OpenAI
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.idi_message import IDIMessage
from app.models.persona import Persona
from app.models.simulation import Simulation
from app.models.simulation_result import SimulationResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_persona_system_prompt(persona: Persona, briefing_text: str) -> str:
    traits = ", ".join(persona.personality_traits or [])
    briefing_block = (
        f"\n\nFor context, here is background material relevant to this interview:\n---\n{briefing_text}\n---"
        if briefing_text else ""
    )
    return (
        f"You are {persona.full_name}, a {persona.age}-year-old {persona.gender} from {persona.location}. "
        f"You work as {persona.occupation} and earn a {persona.income_level} income. "
        f"Background: {persona.educational_background or 'Not specified'}. "
        f"Family: {persona.family_situation or 'Not specified'}. "
        f"Personality: {traits or 'Not specified'}. "
        f"What drives you: {persona.values_and_motivations or 'Not specified'}. "
        f"Your frustrations: {persona.pain_points or 'Not specified'}. "
        f"Media habits: {persona.media_consumption or 'Not specified'}. "
        f"Purchase behavior: {persona.purchase_behavior or 'Not specified'}. "
        "You are participating in a one-on-one research interview. "
        "Respond naturally and authentically as this person. "
        "Answer each question thoughtfully in your own voice — do not break character. "
        "Keep answers conversational (3–6 sentences) unless a question calls for more depth."
        f"{briefing_block}"
    )


def _parse_questions(script_text: str) -> list[str]:
    """Split a script into a list of questions, stripping numbering/bullets."""
    lines = [l.strip() for l in script_text.splitlines() if l.strip()]
    questions = []
    for line in lines:
        # Strip leading numbering like "1.", "1)", "Q1.", "-", "*"
        cleaned = re.sub(r'^(\d+[\.\)]\s*|[Q]\d+[\.\):\s]+|[-*•]\s*)', '', line).strip()
        if cleaned:
            questions.append(cleaned)
    return questions


def _format_transcript(questions: list[str], answers: list[str]) -> str:
    parts = []
    for i, (q, a) in enumerate(zip(questions, answers)):
        parts.append(f"INTERVIEWER: {q}\nRESPONDENT: {a}")
    return "\n\n".join(parts)


def _analyse_persona_transcript(client: OpenAI, persona: Persona, transcript: str) -> dict:
    """Ask GPT to analyse a single persona's interview transcript."""
    prompt = f"""You are a qualitative research analyst. Below is an interview transcript with {persona.full_name} ({persona.age}, {persona.occupation}, {persona.location}).

TRANSCRIPT:
{transcript}

Analyse this interview and respond in the following EXACT format:

SENTIMENT: <Positive | Neutral | Negative>
SUMMARY: <2-3 sentence summary of this person's overall perspective>
KEY THEMES: <3-5 comma-separated themes that emerged>
NOTABLE QUOTES:
- "<verbatim quote from transcript>" — <1 sentence context>
- "<verbatim quote from transcript>" — <1 sentence context>
- "<verbatim quote from transcript>" — <1 sentence context>"""

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw = response.choices[0].message.content or ""

    result: dict = {
        "sentiment": "Neutral",
        "summary": "",
        "key_themes": [],
        "notable_quotes": [],
    }
    current = None
    for line in raw.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("SENTIMENT:"):
            val = stripped.split(":", 1)[-1].strip().capitalize()
            result["sentiment"] = val if val in ("Positive", "Neutral", "Negative") else "Neutral"
        elif upper.startswith("SUMMARY:"):
            current = "summary"
            result["summary"] = stripped.split(":", 1)[-1].strip()
        elif upper.startswith("KEY THEMES:"):
            current = "key_themes"
            raw_themes = stripped.split(":", 1)[-1].strip()
            if raw_themes:
                result["key_themes"] = [t.strip() for t in raw_themes.split(",") if t.strip()]
        elif upper.startswith("NOTABLE QUOTES:"):
            current = "quotes"
        elif stripped.startswith("-") and current == "quotes":
            quote_line = stripped.lstrip("- ").strip()
            result["notable_quotes"].append(quote_line)
        elif stripped and current == "summary":
            result["summary"] += " " + stripped
    return result


def _generate_aggregate_report(client: OpenAI, group_name: str, question_summary: str, persona_analyses: list[dict]) -> dict:
    """Generate a cross-persona IDI aggregate report."""
    per_persona_block = "\n\n".join(
        f"[{a['name']}, {a['age']}, {a['occupation']}]\n"
        f"Sentiment: {a['sentiment']}\n"
        f"Summary: {a['summary']}\n"
        f"Themes: {', '.join(a['key_themes'])}"
        for a in persona_analyses
    )

    prompt = f"""You are a senior qualitative research analyst. You have just completed in-depth interviews with {len(persona_analyses)} participants from the "{group_name}" segment.

RESEARCH FOCUS:
{question_summary}

INDIVIDUAL INTERVIEW SUMMARIES:
{per_persona_block}

Write a professional IDI research report with the following EXACT sections:

EXECUTIVE SUMMARY:
<2-3 paragraphs synthesising the key findings across all respondents>

CROSS-PERSONA THEMES:
<List 3-5 themes that appeared across multiple interviews. For each theme, note which respondents held it. Format: "Theme name: description (held by: Name1, Name2)">

PER-PERSONA HIGHLIGHTS:
<One key takeaway per respondent that captures their unique perspective. Format: "Name: key takeaway">

RECOMMENDATIONS:
<3 concrete, actionable recommendations for the team based on these findings>"""

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    raw = response.choices[0].message.content or ""

    sections: dict = {
        "executive_summary": "",
        "cross_persona_themes": [],
        "per_persona_highlights": [],
        "recommendations": "",
    }
    current = None
    for line in raw.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("EXECUTIVE SUMMARY:"):
            current = "executive_summary"
            tail = stripped.split(":", 1)[-1].strip()
            if tail:
                sections["executive_summary"] = tail
        elif upper.startswith("CROSS-PERSONA THEMES:"):
            current = "cross_persona_themes"
        elif upper.startswith("PER-PERSONA HIGHLIGHTS:"):
            current = "per_persona_highlights"
        elif upper.startswith("RECOMMENDATIONS:"):
            current = "recommendations"
            tail = stripped.split(":", 1)[-1].strip()
            if tail:
                sections["recommendations"] = tail
        elif stripped:
            if current == "executive_summary":
                sections["executive_summary"] += (" " if sections["executive_summary"] else "") + stripped
            elif current == "cross_persona_themes" and (stripped.startswith("-") or stripped[0].isdigit()):
                sections["cross_persona_themes"].append(stripped.lstrip("-•1234567890. ").strip())
            elif current == "per_persona_highlights" and (stripped.startswith("-") or ":" in stripped):
                sections["per_persona_highlights"].append(stripped.lstrip("-•1234567890. ").strip())
            elif current == "recommendations":
                sections["recommendations"] += (" " if sections["recommendations"] else "") + stripped

    return sections


# ---------------------------------------------------------------------------
# AI-Assisted IDI runner
# ---------------------------------------------------------------------------

def run_idi_ai(simulation_id: str) -> None:
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
            raise ValueError("No personas found for this group.")

        questions = _parse_questions(simulation.idi_script_text or "")
        if not questions:
            raise ValueError("No questions found in the interview script.")

        briefing_text = simulation.briefing.extracted_text if simulation.briefing else ""
        question_summary = "; ".join(questions[:5])  # for aggregate prompt context

        persona_analyses = []
        failed_personas = []
        total = len(personas)

        for i, persona in enumerate(personas, 1):
            logger.info(f"[idi:{sim_ref}] Persona {i}/{total}: {persona.full_name}")
            simulation.progress = {
                "current": i,
                "total": total,
                "current_name": persona.full_name,
                "completed": [a["name"] for a in persona_analyses],
                "failed": failed_personas[:],
                "stage": "interviewing",
            }
            db.commit()
            try:
                system_prompt = _build_persona_system_prompt(persona, briefing_text)
                messages = [{"role": "system", "content": system_prompt}]
                answers = []

                for question in questions:
                    messages.append({"role": "user", "content": question})
                    response = client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=messages,
                        temperature=0.85,
                    )
                    answer = response.choices[0].message.content or ""
                    messages.append({"role": "assistant", "content": answer})
                    answers.append(answer)

                transcript = _format_transcript(questions, answers)
                analysis = _analyse_persona_transcript(client, persona, transcript)

                result = SimulationResult(
                    simulation_id=simulation_id,
                    persona_id=persona.id,
                    result_type="idi_individual",
                    sentiment=analysis["sentiment"],
                    sentiment_score={"Positive": 1.0, "Neutral": 0.0, "Negative": -1.0}.get(analysis["sentiment"], 0.0),
                    transcript=transcript,
                    key_themes=analysis["key_themes"] or None,
                    notable_quote=analysis["notable_quotes"][0] if analysis["notable_quotes"] else None,
                    report_sections={
                        "summary": analysis["summary"],
                        "notable_quotes": analysis["notable_quotes"],
                    },
                )
                db.add(result)
                db.flush()

                persona_analyses.append({
                    "name": persona.full_name,
                    "age": persona.age,
                    "occupation": persona.occupation,
                    **analysis,
                })
                logger.info(f"[idi:{sim_ref}] ✓ {persona.full_name} ({analysis['sentiment']})")

            except Exception as e:
                logger.error(f"[idi:{sim_ref}] ✗ {persona.full_name} failed: {e}")
                failed_personas.append(persona.full_name)

        if not persona_analyses:
            raise RuntimeError(f"All {len(personas)} personas failed during IDI.")

        if failed_personas:
            simulation.error_message = (
                f"{len(failed_personas)} of {len(personas)} persona(s) failed: "
                + ", ".join(failed_personas)
            )

        # Aggregate report
        simulation.progress = {
            "current": total,
            "total": total,
            "current_name": None,
            "completed": [a["name"] for a in persona_analyses],
            "failed": failed_personas[:],
            "stage": "generating_report",
        }
        db.commit()

        group = simulation.persona_group
        agg_sections = _generate_aggregate_report(client, group.name, question_summary, persona_analyses)

        # Top themes: collect from all individual analyses
        all_themes: list[str] = []
        for a in persona_analyses:
            all_themes.extend(a.get("key_themes", []))
        # Deduplicate preserving order
        seen: set = set()
        top_themes = [t for t in all_themes if not (t in seen or seen.add(t))][:5]  # type: ignore[func-returns-value]

        agg_result = SimulationResult(
            simulation_id=simulation_id,
            persona_id=None,
            result_type="idi_aggregate",
            summary_text=agg_sections["executive_summary"],
            top_themes=top_themes or None,
            recommendations=agg_sections["recommendations"] or None,
            report_sections=agg_sections,
        )
        db.add(agg_result)

        simulation.status = "complete"
        simulation.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"[idi:{sim_ref}] IDI complete ({len(persona_analyses)}/{len(personas)} personas)")

    except Exception as e:
        logger.error(f"[idi:{sim_ref}] IDI failed: {e}")
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


# ---------------------------------------------------------------------------
# Manual IDI report generator (called after user ends the session)
# ---------------------------------------------------------------------------

def generate_idi_report_from_messages(simulation_id: str) -> None:
    client = OpenAI(api_key=settings.openai_api_key)
    db = SessionLocal()
    sim_ref = simulation_id[:8]
    try:
        simulation = db.get(Simulation, simulation_id)
        if not simulation:
            return

        persona = db.get(Persona, simulation.idi_persona_id)
        if not persona:
            raise ValueError("Persona not found for this manual IDI session.")

        messages = db.execute(
            select(IDIMessage)
            .where(IDIMessage.simulation_id == simulation_id)
            .order_by(IDIMessage.created_at)
        ).scalars().all()

        if not messages:
            raise ValueError("No messages found for this interview session.")

        # Build transcript from stored messages
        transcript_parts = []
        for msg in messages:
            label = "INTERVIEWER" if msg.role == "user" else "RESPONDENT"
            transcript_parts.append(f"{label}: {msg.content}")
        transcript = "\n\n".join(transcript_parts)

        analysis = _analyse_persona_transcript(client, persona, transcript)

        result = SimulationResult(
            simulation_id=simulation_id,
            persona_id=persona.id,
            result_type="idi_individual",
            sentiment=analysis["sentiment"],
            sentiment_score={"Positive": 1.0, "Neutral": 0.0, "Negative": -1.0}.get(analysis["sentiment"], 0.0),
            transcript=transcript,
            key_themes=analysis["key_themes"] or None,
            notable_quote=analysis["notable_quotes"][0] if analysis["notable_quotes"] else None,
            report_sections={
                "summary": analysis["summary"],
                "notable_quotes": analysis["notable_quotes"],
            },
        )
        db.add(result)

        # For manual IDI (single persona), also generate a summary aggregate result
        # so the results page can render consistently with AI-assisted
        agg_sections = _generate_aggregate_report(
            client,
            simulation.persona_group.name,
            "Manual in-depth interview",
            [{
                "name": persona.full_name,
                "age": persona.age,
                "occupation": persona.occupation,
                **analysis,
            }],
        )

        agg_result = SimulationResult(
            simulation_id=simulation_id,
            persona_id=None,
            result_type="idi_aggregate",
            summary_text=agg_sections["executive_summary"],
            top_themes=analysis["key_themes"] or None,
            recommendations=agg_sections["recommendations"] or None,
            report_sections=agg_sections,
        )
        db.add(agg_result)

        simulation.status = "complete"
        simulation.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"[idi:{sim_ref}] Manual IDI report generated for {persona.full_name}")

    except Exception as e:
        logger.error(f"[idi:{sim_ref}] Report generation failed: {e}")
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
