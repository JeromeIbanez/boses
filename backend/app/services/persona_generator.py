"""
Persona generation service.

Architecture
------------
PersonaDataSource (abstract base)
    └── SyntheticPersonaSource   ← current implementation (GPT-4o)
    └── CsvPersonaSource         ← future: import from CSV/survey export
    └── InterviewPersonaSource   ← future: extract personas from interview transcripts

generate_personas() is the public entry point. It resolves the correct
source based on PersonaGroup.data_source (defaults to "synthetic") and
delegates to it. The rest of the system never needs to change.
"""
import json
import logging
import uuid as _uuid
from abc import ABC, abstractmethod

from openai import OpenAI

from app.config import settings
from app.database import SessionLocal
from app.models.persona import Persona
from app.models.persona_group import PersonaGroup
from app.services.grounding import format_grounding_context
from app.services.library_matcher import find_library_matches, save_persona_to_library
from app.services.reddit_grounding import fetch_reddit_signals

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base — all future data sources implement this interface
# ---------------------------------------------------------------------------

class PersonaDataSource(ABC):
    @abstractmethod
    def fetch(self, group: PersonaGroup) -> list[dict]:
        """
        Return a list of raw persona dicts for the given group.
        Each dict must contain at minimum: full_name, age, gender,
        location, occupation, income_level.
        """


# ---------------------------------------------------------------------------
# Synthetic source — GPT-4o two-pass generation with source citations
# ---------------------------------------------------------------------------

class SyntheticPersonaSource(PersonaDataSource):
    def __init__(self, client: OpenAI):
        self.client = client

    def fetch(self, group: PersonaGroup) -> list[dict]:
        # Load real-world grounding data for this location (empty string if not found)
        grounding_context, grounding_sources = format_grounding_context(group.location or "")

        # Append Reddit social signals if credentials are configured
        reddit_context = fetch_reddit_signals(
            group.location or "",
            group.psychographic_notes or "",
        )
        if reddit_context:
            grounding_context = grounding_context + "\n" + reddit_context

        skeletons = self._pass1_skeletons(group, grounding_context)
        profiles = self._pass2_expand(group, skeletons, grounding_context, grounding_sources)
        return profiles

    def _pass1_skeletons(self, group: PersonaGroup, grounding_context: str) -> list[dict]:
        """
        Pass 1: generate diverse skeleton stubs anchored to real demographic data.
        """
        system = (
            "You are a senior market research strategist. "
            "Your job is to define a diverse cast of consumer archetypes "
            "that span the realistic range of a target demographic — "
            "not averages, but distinct individuals with different outlooks, "
            "life stages, and relationships with money and brands. "
            "When real demographic statistics are provided, treat them as hard facts "
            "and ensure your archetypes reflect the actual distribution of the population."
        )

        grounding_block = f"\n{grounding_context}\n" if grounding_context else ""

        user = f"""{grounding_block}Create {group.persona_count} distinct consumer archetypes for this demographic:

- Age range: {group.age_min}–{group.age_max}
- Gender: {group.gender}
- Location: {group.location}
- Occupation: {group.occupation}
- Income level: {group.income_level}
- Additional context: {group.psychographic_notes or "None"}

Rules:
- Each archetype must be meaningfully different (vary life stage, optimism, tech-savviness, brand relationship, financial mindset)
- Avoid averaging — include edge cases (the skeptic, the aspirational striver, the pragmatist, etc.)
- Ground them culturally and statistically in {group.location} using the data above
- Income levels and digital behaviors must reflect the real distribution shown above

Return a JSON array of {group.persona_count} objects, each with:
{{
  "index": <1-based integer>,
  "full_name": "...",
  "age": <integer>,
  "gender": "...",
  "occupation": "...",
  "archetype_label": "...",
  "one_line_bio": "..."
}}"""

        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=1.2,
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        if isinstance(raw, dict):
            return next(iter(raw.values()))
        return raw

    def _pass2_expand(
        self,
        group: PersonaGroup,
        skeletons: list[dict],
        grounding_context: str,
        grounding_sources: list[str],
    ) -> list[dict]:
        """
        Pass 2: expand each skeleton into a full profile grounded in real stats.
        """
        profiles = []
        for skeleton in skeletons:
            system = (
                "You are a behavioral researcher and cultural anthropologist. "
                "Expand a consumer archetype into a richly detailed, realistic individual. "
                "When real demographic statistics are provided, treat them as ground truth — "
                "your persona's behaviors, habits, and attitudes must be consistent with "
                "the actual data for this market. "
                "Return only valid JSON."
            )

            grounding_block = f"\n{grounding_context}\n" if grounding_context else ""

            # Merge real sources with instruction to add any additional ones
            sources_instruction = (
                "Include these verified sources in data_source_references (you may add others):\n"
                + "\n".join(f'  - "{s}"' for s in grounding_sources)
            ) if grounding_sources else (
                "List the specific reports or studies that informed each field."
            )

            user = f"""{grounding_block}Expand this archetype into a full consumer profile:

Archetype: {skeleton.get('archetype_label')} — {skeleton.get('one_line_bio')}
Name: {skeleton.get('full_name')}, Age: {skeleton.get('age')}, Gender: {skeleton.get('gender')}
Occupation: {skeleton.get('occupation')}
Location: {group.location}
Income level: {group.income_level}
Additional context: {group.psychographic_notes or "None"}

Return a single JSON object with these exact fields:
{{
  "full_name": "...",
  "age": <integer>,
  "gender": "...",
  "location": "...",
  "occupation": "...",
  "income_level": "...",
  "educational_background": "...",
  "family_situation": "...",
  "personality_traits": ["...", "...", "..."],
  "values_and_motivations": "...",
  "pain_points": "...",
  "media_consumption": "...",
  "purchase_behavior": "...",
  "day_in_the_life": "A 2–3 sentence narrative of a typical day, grounded in the real cultural and economic context of {group.location}.",
  "data_source_references": ["..."]
}}

{sources_instruction}
Be specific. Every detail must be consistent with the demographic data above."""

            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                temperature=1.0,
            )
            raw = json.loads(response.choices[0].message.content or "{}")
            if isinstance(raw, dict) and "full_name" not in raw:
                raw = next(iter(raw.values()))

            # Ensure grounding sources are always present in the references
            existing_refs = raw.get("data_source_references") or []
            merged_refs = list(dict.fromkeys(grounding_sources + existing_refs))  # deduplicate, preserve order
            raw["data_source_references"] = merged_refs

            profiles.append(raw)

        return profiles


# ---------------------------------------------------------------------------
# Stubs for future data sources
# ---------------------------------------------------------------------------

class CsvPersonaSource(PersonaDataSource):
    """Future: parse personas from an uploaded CSV or survey export."""
    def fetch(self, group: PersonaGroup) -> list[dict]:
        raise NotImplementedError("CsvPersonaSource is not yet implemented.")


class InterviewPersonaSource(PersonaDataSource):
    """Future: extract personas from interview transcripts via GPT."""
    def fetch(self, group: PersonaGroup) -> list[dict]:
        raise NotImplementedError("InterviewPersonaSource is not yet implemented.")


# ---------------------------------------------------------------------------
# Source registry — maps data_source string → class
# ---------------------------------------------------------------------------

_SOURCES: dict[str, type[PersonaDataSource]] = {
    "synthetic": SyntheticPersonaSource,
    "csv": CsvPersonaSource,
    "interview": InterviewPersonaSource,
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_personas(group_id: str) -> None:
    client = OpenAI(api_key=settings.openai_api_key)
    db = SessionLocal()
    try:
        group = db.get(PersonaGroup, group_id)
        if not group:
            return

        source_key = getattr(group, "data_source", "synthetic") or "synthetic"
        source_class = _SOURCES.get(source_key, SyntheticPersonaSource)

        if source_class is SyntheticPersonaSource:
            source = SyntheticPersonaSource(client)
        else:
            source = source_class()

        # --- Step 1: try to fill from library first ---
        library_matches = find_library_matches(db, group, limit=group.persona_count * 2)
        used_library_ids: set = set()
        personas_created = 0

        for lib_persona, match_score in library_matches:
            if personas_created >= group.persona_count:
                break
            if lib_persona.id in used_library_ids:
                continue

            _pid = _uuid.uuid4()
            persona = Persona(
                id=_pid,
                persona_code=str(_pid).replace('-', '')[:8].upper(),
                persona_group_id=group_id,
                full_name=lib_persona.full_name,
                age=lib_persona.age,
                gender=lib_persona.gender,
                location=lib_persona.location,
                occupation=lib_persona.occupation,
                income_level=lib_persona.income_level,
                educational_background=lib_persona.educational_background,
                family_situation=lib_persona.family_situation,
                personality_traits=lib_persona.personality_traits,
                values_and_motivations=None,
                pain_points=lib_persona.pain_points,
                media_consumption=lib_persona.media_consumption,
                purchase_behavior=lib_persona.spending_habits,
                day_in_the_life=lib_persona.day_in_the_life,
                data_source=lib_persona.data_source,
                data_source_references=lib_persona.data_source_references,
                raw_profile_json=None,
            )
            db.add(persona)
            db.flush()  # get persona.id
            save_persona_to_library(db, persona, match_score=match_score, existing_library_id=lib_persona.id)
            used_library_ids.add(lib_persona.id)
            personas_created += 1

        logger.info(f"Filled {personas_created} persona(s) from library for group {group_id}")

        # --- Step 2: generate remaining synthetically ---
        remaining = group.persona_count - personas_created
        if remaining > 0:
            # Temporarily override persona_count without mutating the DB row
            group.persona_count = remaining
            profiles = source.fetch(group)
            group.persona_count = group.persona_count + personas_created  # restore

            for profile in profiles:
                _pid = _uuid.uuid4()
                persona = Persona(
                    id=_pid,
                    persona_code=str(_pid).replace('-', '')[:8].upper(),
                    persona_group_id=group_id,
                    full_name=profile.get("full_name", "Unknown"),
                    age=int(profile.get("age", group.age_min or 25)),
                    gender=profile.get("gender", group.gender),
                    location=profile.get("location", group.location),
                    occupation=profile.get("occupation", group.occupation),
                    income_level=profile.get("income_level", group.income_level),
                    educational_background=profile.get("educational_background"),
                    family_situation=profile.get("family_situation"),
                    personality_traits=profile.get("personality_traits"),
                    values_and_motivations=profile.get("values_and_motivations"),
                    pain_points=profile.get("pain_points"),
                    media_consumption=profile.get("media_consumption"),
                    purchase_behavior=profile.get("purchase_behavior"),
                    day_in_the_life=profile.get("day_in_the_life"),
                    data_source=source_key,
                    data_source_references=profile.get("data_source_references"),
                    raw_profile_json=profile,
                )
                db.add(persona)
                db.flush()
                save_persona_to_library(db, persona)
                personas_created += 1

            logger.info(f"Generated {remaining} new persona(s) synthetically for group {group_id}")

        group.generation_status = "complete"
        db.commit()
        logger.info(f"Total {personas_created} personas for group {group_id} (source={source_key})")

    except Exception as e:
        logger.error(f"Persona generation failed for group {group_id}: {e}")
        try:
            group = db.get(PersonaGroup, group_id)
            if group:
                group.generation_status = "failed"
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
