from __future__ import annotations

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

from app.services.openai_client import get_openai_client

from app.config import settings
from app.database import SessionLocal
from app.models.persona import Persona
from app.models.persona_group import PersonaGroup
from app.services.avatar_service import generate_avatars_for_group
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
    def __init__(self, client):
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

        # Append cultural context from automated web ethnography pipeline (ID/PH/VN only).
        # Returns None for unsupported markets or when no active snapshot exists —
        # in which case grounding_context is unchanged (safe fallback to existing behaviour).
        from app.services.ethnography_service import get_cultural_context_block
        cultural_ctx = get_cultural_context_block(group.location or "")
        if cultural_ctx:
            grounding_context = grounding_context + "\n\n" + cultural_ctx

        skeletons = self._pass1_skeletons(group, grounding_context)
        profiles = self._pass2_expand(group, skeletons, grounding_context, grounding_sources)
        return profiles

    def _pass1_skeletons(self, group: PersonaGroup, grounding_context: str, count: int | None = None) -> list[dict]:
        """
        Pass 1: generate diverse skeleton stubs anchored to real demographic data.
        """
        n = count if count is not None else group.persona_count

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

        user = f"""{grounding_block}Create {n} distinct consumer archetypes for this demographic:

- Age range: {group.age_min}–{group.age_max}
- Gender: {group.gender}
- Location: {group.location}
- Occupation: {group.occupation}
- Income level: {group.income_level}
- Additional context: {group.psychographic_notes or "None"}

Rules:
- Each archetype must be meaningfully different. Mandatory spread: include at least one skeptic, one aspirational striver, and one pragmatist/value-seeker across the set.
- Vary dominant_brand_stance across personas — do not give more than two the same stance.
- Psychographic segment must be chosen from: Innovator, Thinker, Achiever, Experiencer, Believer, Striver, Maker, Survivor (VALS framework). For non-US markets use the closest cultural equivalent.
- AVOID these as bio descriptors: "optimistic", "loves socializing", "enjoys family time". Describe the tension and friction in their life instead.
- Ground them culturally and statistically in {group.location} using the data above.
- Income levels and digital behaviors must reflect the real distribution shown above.

Return a JSON array of {group.persona_count} objects, each with:
{{
  "index": <1-based integer>,
  "full_name": "...",
  "age": <integer>,
  "gender": "...",
  "occupation": "...",
  "archetype_label": "2–4 word label, e.g. 'The Reluctant Upgrader'",
  "one_line_bio": "One sentence describing their core tension or life friction — not their hobbies",
  "psychographic_segment": "one VALS segment name",
  "dominant_brand_stance": "one of: Loyal, Skeptical, Aspirational, Burned, Indifferent, Vocal Advocate"
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
            for v in raw.values():
                if isinstance(v, list):
                    return v
            return []
        return raw if isinstance(raw, list) else []

    def _expand_one_skeleton(
        self,
        skeleton: dict,
        group: PersonaGroup,
        grounding_context: str,
        grounding_sources: list[str],
        peer_skeletons: list[dict] | None = None,
    ) -> dict:
        """Expand a single skeleton into a full profile."""
        system = (
            "You are a senior behavioral researcher and cultural anthropologist "
            "writing ultra-specific consumer profiles for a marketing agency pitch deck.\n\n"
            "CRITICAL RULES — violating any of these will make the output unusable:\n"
            "1. NEVER write generic statements. Every sentence must contain a specific detail "
            "that could only apply to this exact person.\n"
            "   BAD: 'She enjoys spending time with family.'\n"
            "   GOOD: 'She video-calls her mother in Cebu every Sunday at 8pm while making arroz caldo.'\n"
            "2. personality_traits must include AT LEAST TWO negative traits or shadow sides "
            "(e.g. 'avoids difficult conversations', 'prone to lifestyle inflation'). "
            "Include 5–7 traits total — do not list only positive ones.\n"
            "3. brand_attitudes must name AT LEAST ONE brand they actively distrust, with a specific reason "
            "(a bad experience, a news story they read, a friend's warning).\n"
            "4. pain_points must be systemic and concrete — not 'busy schedule' but "
            "'spends 40 minutes daily in gridlock on EDSA and resents every minute of it.'\n"
            "5. All currency amounts must be specific: not 'limited budget' but "
            "'₱3,500 monthly discretionary spend after rent, utilities, and remittance.'\n"
            "6. media_consumption must list exact platform names, content formats, specific creator types, "
            "and usage windows — not 'uses social media' but "
            "'scrolls TikTok for 45 minutes before sleeping, follows cooking and K-drama recap accounts, "
            "skips all pre-roll ads.'\n"
            "7. day_in_the_life must read like a scene from a novel: "
            "Sentence 1 = morning routine with one sensory detail. "
            "Sentence 2 = the central tension or trade-off of their workday. "
            "Sentence 3 = evening wind-down with what they consume and how they feel.\n"
            "8. When real demographic statistics are provided, treat them as ground truth — "
            "behaviors, habits, and attitudes must be consistent with the actual data for this market.\n"
            "9. Return only valid JSON."
        )

        grounding_block = f"\n{grounding_context}\n" if grounding_context else ""

        sources_instruction = (
            "Include these verified sources in data_source_references (you may add others):\n"
            + "\n".join(f'  - "{s}"' for s in grounding_sources)
        ) if grounding_sources else (
            "List the specific reports or studies that informed each field."
        )

        # Build peer awareness block — show the other skeletons in this batch so
        # Pass 2 can actively diverge in routine, habits, and texture.
        peers = [p for p in (peer_skeletons or []) if p.get("full_name") != skeleton.get("full_name")]
        if peers:
            peer_lines = "\n".join(
                f'  - {p.get("full_name")}, {p.get("age")}, {p.get("gender")} | '
                f'{p.get("archetype_label")} | {p.get("psychographic_segment")} | '
                f'Brand stance: {p.get("dominant_brand_stance")}'
                for p in peers
            )
            peer_block = (
                f"\nOTHER PERSONAS IN THIS BATCH (do not duplicate their routines, "
                f"habits, schedules, or day-in-the-life details):\n{peer_lines}\n"
                f"Ensure this persona's day_in_the_life, digital_behavior, and "
                f"media_consumption are meaningfully distinct from every person above.\n"
            )
        else:
            peer_block = ""

        user = f"""{grounding_block}{peer_block}Expand this archetype into a full consumer profile:

Archetype: {skeleton.get('archetype_label')} — {skeleton.get('one_line_bio')}
Name: {skeleton.get('full_name')}, Age: {skeleton.get('age')}, Gender: {skeleton.get('gender')}
Occupation: {skeleton.get('occupation')}
Location: {group.location}
Income level: {group.income_level}
Psychographic segment: {skeleton.get('psychographic_segment', '')}
Brand stance: {skeleton.get('dominant_brand_stance', '')}
Additional context: {group.psychographic_notes or "None"}

Return a single JSON object with these exact fields:
{{
  "full_name": "...",
  "age": <integer>,
  "gender": "...",
  "location": "specific neighbourhood/district, city, country — not just the city",
  "occupation": "specific job title at a specific type of company (e.g. 'Junior Account Manager at a mid-size BPO firm in Ortigas')",
  "income_level": "...",
  "archetype_label": "carry forward from archetype above — refine wording if needed",
  "psychographic_segment": "carry forward VALS segment from archetype",
  "educational_background": "Degree, institution type, graduation year if relevant — and whether it met their expectations",
  "family_situation": "Who lives with them, relationship quality, and specific financial interdependencies (e.g. 'sends ₱4,000/month remittance to parents in Batangas')",
  "personality_traits": ["positive trait with brief context", "second trait", "third trait", "NEGATIVE trait — a genuine flaw or blind spot", "NEGATIVE trait — a second shadow side"],
  "values_and_motivations": "What they are optimizing their life for, in their own internal language. Must reference a specific life goal with a concrete timeline.",
  "pain_points": "Three specific, systemic frustrations with concrete details — one financial, one time/logistics, one social/identity. No vague generalities.",
  "brand_attitudes": "Name 2–3 specific brands they love and exactly why. Name 1–2 brands they distrust and the specific incident or reason. Format: 'Loves [Brand] because [specific reason]. Distrusts [Brand] since [specific incident].'",
  "buying_triggers": "What specific conditions, events, or emotional states cause them to make a purchase. Include at least one irrational/emotional trigger and one rational/functional trigger. Also what kills a deal for them.",
  "aspirational_identity": "The version of themselves they are trying to become. What does success look like in 5 years? What specific status marker (brand, lifestyle, title, address) would signal they've arrived?",
  "media_consumption": "Specific platforms, content types, creator archetypes or shows they follow, and what they actively avoid. Use morning/commute/evening breakdown format.",
  "digital_behavior": "Primary device model type, data plan constraints if relevant, top 5 apps by daily usage, e-commerce behaviour (where they shop online, preferred payment method), and one online habit they would be embarrassed to admit.",
  "purchase_behavior": "How they research before buying. Who do they ask for advice? What is their relationship with discounts and promotions? Estimate their monthly spend on the category most relevant to this study.",
  "day_in_the_life": "Three immersive sentences: (1) morning routine with one specific sensory detail, (2) the central tension or trade-off of their workday today, (3) evening wind-down — what they watch/read, how they feel, what small thing they look forward to.",
  "data_source_references": ["..."]
}}

{sources_instruction}
Be hyper-specific. Generic statements are not allowed."""

        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=1.0,
            max_tokens=8192,
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        if isinstance(raw, dict) and "full_name" not in raw:
            raw = next(iter(raw.values()))

        # Ensure grounding sources are always present in the references
        existing_refs = raw.get("data_source_references") or []
        raw["data_source_references"] = list(dict.fromkeys(grounding_sources + existing_refs))

        return raw

    def _pass2_expand(
        self,
        group: PersonaGroup,
        skeletons: list[dict],
        grounding_context: str,
        grounding_sources: list[str],
    ) -> list[dict]:
        """Expand all skeletons — used by fetch() for non-progress callers."""
        return [
            self._expand_one_skeleton(s, group, grounding_context, grounding_sources, peer_skeletons=skeletons)
            for s in skeletons
        ]


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

def _trunc(value: str | None, max_len: int) -> str | None:
    return value[:max_len] if value else value


def _set_progress(db, group: PersonaGroup, current: int, total: int, current_name: str | None, completed: list[str]) -> None:
    """Write progress to DB and commit so the frontend polling can see it."""
    from sqlalchemy.orm.attributes import flag_modified
    group.generation_progress = {
        "current": current,
        "total": total,
        "current_name": current_name,
        "completed": list(completed),
    }
    flag_modified(group, "generation_progress")
    db.commit()


def generate_personas(group_id: str) -> None:
    client = get_openai_client()
    db = SessionLocal()
    try:
        group = db.get(PersonaGroup, group_id)
        if not group:
            return

        source_key = getattr(group, "data_source", "synthetic") or "synthetic"
        source_class = _SOURCES.get(source_key, SyntheticPersonaSource)
        total = group.persona_count
        completed_names: list[str] = []
        personas_created = 0
        created_persona_ids: list[str] = []

        # Initialise progress
        _set_progress(db, group, 0, total, None, [])

        if source_class is SyntheticPersonaSource:
            source = SyntheticPersonaSource(client)
        else:
            source = source_class()

        # --- Step 1: fill from library ---
        library_matches = find_library_matches(db, group, limit=total * 2)
        used_library_ids: set = set()

        for lib_persona, match_score in library_matches:
            if personas_created >= total:
                break
            if lib_persona.id in used_library_ids:
                continue

            name = lib_persona.full_name
            _set_progress(db, group, personas_created + 1, total, name, completed_names)

            _pid = _uuid.uuid4()
            persona = Persona(
                id=_pid,
                persona_code=str(_pid).replace('-', '')[:8].upper(),
                persona_group_id=group_id,
                full_name=name,
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
                archetype_label=getattr(lib_persona, "archetype_label", None),
                psychographic_segment=getattr(lib_persona, "psychographic_segment", None),
                brand_attitudes=getattr(lib_persona, "brand_attitudes", None),
                buying_triggers=getattr(lib_persona, "buying_triggers", None),
                aspirational_identity=getattr(lib_persona, "aspirational_identity", None),
                digital_behavior=getattr(lib_persona, "digital_behavior", None),
                day_in_the_life=lib_persona.day_in_the_life,
                data_source=lib_persona.data_source,
                data_source_references=lib_persona.data_source_references,
                raw_profile_json=None,
            )
            db.add(persona)
            db.flush()
            created_persona_ids.append(str(persona.id))
            save_persona_to_library(db, persona, match_score=match_score, existing_library_id=lib_persona.id)
            used_library_ids.add(lib_persona.id)
            completed_names.append(name)
            personas_created += 1
            _set_progress(db, group, personas_created, total, None, completed_names)

        logger.info(f"Filled {personas_created} persona(s) from library for group {group_id}")

        # --- Step 2: generate remaining synthetically ---
        remaining = total - personas_created
        if remaining > 0:
            if source_class is SyntheticPersonaSource:
                # Load grounding once
                grounding_context, grounding_sources = format_grounding_context(group.location or "")
                reddit_context = fetch_reddit_signals(group.location or "", group.psychographic_notes or "")
                if reddit_context:
                    grounding_context = grounding_context + "\n" + reddit_context

                # Pass 1: generate all skeletons at once (fast)
                skeletons = source._pass1_skeletons(group, grounding_context, count=remaining)

                # Pass 2: expand one skeleton at a time with per-persona progress commits
                for skeleton in skeletons:
                    name = skeleton.get("full_name", f"Persona {personas_created + 1}")
                    _set_progress(db, group, personas_created + 1, total, name, completed_names)

                    profile = source._expand_one_skeleton(
                        skeleton, group, grounding_context, grounding_sources,
                        peer_skeletons=skeletons,
                    )

                    _pid = _uuid.uuid4()
                    persona = Persona(
                        id=_pid,
                        persona_code=str(_pid).replace('-', '')[:8].upper(),
                        persona_group_id=group_id,
                        full_name=profile.get("full_name", name),
                        age=int(profile.get("age", group.age_min or 25)),
                        gender=profile.get("gender", group.gender),
                        location=profile.get("location", group.location),
                        occupation=profile.get("occupation", group.occupation),
                        income_level=_trunc(profile.get("income_level", group.income_level), 100),
                        educational_background=profile.get("educational_background"),
                        family_situation=profile.get("family_situation"),
                        personality_traits=profile.get("personality_traits"),
                        values_and_motivations=profile.get("values_and_motivations"),
                        pain_points=profile.get("pain_points"),
                        media_consumption=profile.get("media_consumption"),
                        purchase_behavior=profile.get("purchase_behavior"),
                        archetype_label=_trunc(profile.get("archetype_label"), 100),
                        psychographic_segment=_trunc(profile.get("psychographic_segment"), 100),
                        brand_attitudes=profile.get("brand_attitudes"),
                        buying_triggers=profile.get("buying_triggers"),
                        aspirational_identity=profile.get("aspirational_identity"),
                        digital_behavior=profile.get("digital_behavior"),
                        day_in_the_life=profile.get("day_in_the_life"),
                        data_source=source_key,
                        data_source_references=profile.get("data_source_references"),
                        raw_profile_json=profile,
                    )
                    db.add(persona)
                    db.flush()
                    created_persona_ids.append(str(persona.id))
                    save_persona_to_library(db, persona)
                    completed_names.append(profile.get("full_name", name))
                    personas_created += 1
                    _set_progress(db, group, personas_created, total, None, completed_names)
            else:
                # Non-synthetic sources: fetch all at once (no per-persona progress)
                profiles = source.fetch(group)
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
                        income_level=_trunc(profile.get("income_level", group.income_level), 100),
                        educational_background=profile.get("educational_background"),
                        family_situation=profile.get("family_situation"),
                        personality_traits=profile.get("personality_traits"),
                        values_and_motivations=profile.get("values_and_motivations"),
                        pain_points=profile.get("pain_points"),
                        media_consumption=profile.get("media_consumption"),
                        purchase_behavior=profile.get("purchase_behavior"),
                        archetype_label=_trunc(profile.get("archetype_label"), 100),
                        psychographic_segment=_trunc(profile.get("psychographic_segment"), 100),
                        brand_attitudes=profile.get("brand_attitudes"),
                        buying_triggers=profile.get("buying_triggers"),
                        aspirational_identity=profile.get("aspirational_identity"),
                        digital_behavior=profile.get("digital_behavior"),
                        day_in_the_life=profile.get("day_in_the_life"),
                        data_source=source_key,
                        data_source_references=profile.get("data_source_references"),
                        raw_profile_json=profile,
                    )
                    db.add(persona)
                    db.flush()
                    created_persona_ids.append(str(persona.id))
                    save_persona_to_library(db, persona)
                    personas_created += 1

            logger.info(f"Generated {remaining} new persona(s) for group {group_id}")

        group.generation_status = "complete"
        group.generation_progress = None
        db.commit()
        logger.info(f"Total {personas_created} personas for group {group_id} (source={source_key})")

        # Generate avatars concurrently — all DALL-E calls run in parallel after
        # text generation is complete so persona creation speed is unaffected.
        generate_avatars_for_group(client, created_persona_ids)

    except Exception as e:
        logger.error(f"Persona generation failed for group {group_id}: {e}")
        try:
            group = db.get(PersonaGroup, group_id)
            if group:
                group.generation_status = "failed"
                group.generation_progress = None
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
