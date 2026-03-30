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
from abc import ABC, abstractmethod

from openai import OpenAI

from app.config import settings
from app.database import SessionLocal
from app.models.persona import Persona
from app.models.persona_group import PersonaGroup

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
        skeletons = self._pass1_skeletons(group)
        profiles = self._pass2_expand(group, skeletons)
        return profiles

    def _pass1_skeletons(self, group: PersonaGroup) -> list[dict]:
        """
        Pass 1: generate diverse skeleton stubs to anchor diversity
        before full expansion.
        """
        system = (
            "You are a senior market research strategist. "
            "Your job is to define a diverse cast of consumer archetypes "
            "that span the realistic range of a target demographic — "
            "not averages, but distinct individuals with different outlooks, "
            "life stages, and relationships with money and brands."
        )

        user = f"""Create {group.persona_count} distinct consumer archetypes for this demographic:

- Age range: {group.age_min}–{group.age_max}
- Gender: {group.gender}
- Location: {group.location}
- Occupation: {group.occupation}
- Income level: {group.income_level}
- Additional context: {group.psychographic_notes or "None"}

Rules:
- Each archetype must be meaningfully different (vary life stage, optimism, tech-savviness, brand relationship, financial mindset)
- Avoid averaging — include edge cases (the skeptic, the aspirational striver, the pragmatist, etc.)
- Ground them culturally in {group.location}

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

    def _pass2_expand(self, group: PersonaGroup, skeletons: list[dict]) -> list[dict]:
        """
        Pass 2: expand each skeleton into a full profile with source citations.
        Each call is individual so GPT gives full attention per persona.
        """
        profiles = []
        for skeleton in skeletons:
            system = (
                "You are a behavioral researcher and cultural anthropologist. "
                "Expand a consumer archetype into a richly detailed, realistic individual. "
                "Draw on published consumer research, cultural studies, and market data. "
                "Cite the specific sources (reports, studies, datasets) you are drawing from — "
                "be honest about what real-world research informs each field. "
                "Return only valid JSON."
            )

            user = f"""Expand this archetype into a full consumer profile:

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
  "day_in_the_life": "A 2–3 sentence narrative of a typical day for this person, grounded in their cultural context.",
  "data_source_references": [
    "Name of report or study this profile draws from (e.g. GWI Southeast Asia Q3 2024)",
    "..."
  ]
}}

Be specific. Avoid generic statements. Ground cultural details in {group.location}."""

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
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
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

        profiles = source.fetch(group)

        for profile in profiles:
            persona = Persona(
                persona_group_id=group_id,
                full_name=profile.get("full_name", "Unknown"),
                age=int(profile.get("age", group.age_min)),
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

        group.generation_status = "complete"
        db.commit()
        logger.info(f"Generated {len(profiles)} personas for group {group_id} via source={source_key}")

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
