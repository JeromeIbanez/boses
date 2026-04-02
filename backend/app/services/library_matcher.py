"""
library_matcher.py
Scores library personas against a requested persona group demographic.
No ML — deterministic weighted scoring over categorical fields.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.library_persona import LibraryPersona, PersonaLibraryLink
from app.models.persona import Persona
from app.models.persona_group import PersonaGroup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MATCH_THRESHOLD = 0.70  # minimum score to be considered a match

# Set to False to always generate fresh (skip library lookup)
USE_LIBRARY = True

# Income level ordering for adjacency scoring
_INCOME_ORDER = [
    "low",
    "lower-middle",
    "middle",
    "upper-middle",
    "high",
]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _normalise(s: str) -> str:
    return s.strip().lower() if s else ""


def _income_adjacent(a: str, b: str) -> bool:
    """True if two income levels are one step apart."""
    try:
        ia = _INCOME_ORDER.index(_normalise(a))
        ib = _INCOME_ORDER.index(_normalise(b))
        return abs(ia - ib) == 1
    except ValueError:
        return False


def score_persona(library_persona: LibraryPersona, group: PersonaGroup) -> float:
    """
    Score a library persona against a requested persona group.
    Returns a float in [0.0, 1.0].
    """
    score = 0.0

    # --- Age (0.35) ---
    age_min = group.age_min or 0
    age_max = group.age_max or 120
    age = library_persona.age
    if age_min <= age <= age_max:
        score += 0.35
    elif abs(age - age_min) <= 3 or abs(age - age_max) <= 3:
        score += 0.15

    # --- Gender (0.20) ---
    group_gender = _normalise(group.gender or "")
    lib_gender = _normalise(library_persona.gender)
    if group_gender in ("", "all", "any") or group_gender == lib_gender:
        score += 0.20

    # --- Income level (0.20) ---
    group_income = _normalise(group.income_level or "")
    lib_income = _normalise(library_persona.income_level)
    if group_income in ("", "any"):
        score += 0.20
    elif group_income == lib_income:
        score += 0.20
    elif _income_adjacent(group_income, lib_income):
        score += 0.08

    # --- Location (0.15) ---
    group_loc = _normalise(group.location or "")
    lib_loc = _normalise(library_persona.location)
    if group_loc in ("", "any"):
        score += 0.15
    elif group_loc == lib_loc:
        score += 0.15
    else:
        # Same country: compare last comma-separated token
        group_country = group_loc.split(",")[-1].strip()
        lib_country = lib_loc.split(",")[-1].strip()
        if group_country and group_country == lib_country:
            score += 0.07

    # --- Occupation (0.10) ---
    group_occ = _normalise(group.occupation or "")
    lib_occ = _normalise(library_persona.occupation)
    if group_occ in ("", "any") or group_occ == lib_occ:
        score += 0.10

    return round(score, 4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_library_matches(
    db: Session,
    group: PersonaGroup,
    limit: int = 50,
) -> list[tuple[LibraryPersona, float]]:
    """
    Return (LibraryPersona, score) pairs that score >= MATCH_THRESHOLD,
    ordered by score descending.
    """
    if not USE_LIBRARY:
        return []

    age_min = (group.age_min or 0) - 5
    age_max = (group.age_max or 120) + 5

    # Pre-filter in SQL to narrow candidates before Python scoring
    candidates: list[LibraryPersona] = (
        db.query(LibraryPersona)
        .filter(
            LibraryPersona.is_retired == False,  # noqa: E712
            LibraryPersona.age >= age_min,
            LibraryPersona.age <= age_max,
        )
        .limit(500)  # hard cap to keep scoring fast
        .all()
    )

    scored = [
        (lp, score_persona(lp, group))
        for lp in candidates
    ]
    matches = [
        (lp, s) for lp, s in scored if s >= MATCH_THRESHOLD
    ]
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:limit]


def save_persona_to_library(
    db: Session,
    persona: Persona,
    match_score: float | None = None,
    existing_library_id: uuid.UUID | None = None,
) -> LibraryPersona:
    """
    Link a project persona to the library.

    - If existing_library_id is provided, link to that entry (reuse match).
    - Otherwise create a new LibraryPersona from the persona's data.

    Does NOT commit — caller owns the transaction.
    """
    if existing_library_id:
        lib = db.get(LibraryPersona, existing_library_id)
    else:
        lib = LibraryPersona(
            full_name=persona.full_name,
            age=persona.age,
            gender=persona.gender,
            location=persona.location,
            occupation=persona.occupation,
            income_level=persona.income_level,
            educational_background=persona.educational_background,
            family_situation=persona.family_situation,
            background=getattr(persona, "background", None),
            personality_traits=persona.personality_traits,
            goals=getattr(persona, "goals", None),
            pain_points=persona.pain_points,
            tech_savviness=getattr(persona, "tech_savviness", None),
            media_consumption=persona.media_consumption,
            spending_habits=getattr(persona, "spending_habits", None),
            archetype_label=getattr(persona, "archetype_label", None),
            psychographic_segment=getattr(persona, "psychographic_segment", None),
            brand_attitudes=getattr(persona, "brand_attitudes", None),
            buying_triggers=getattr(persona, "buying_triggers", None),
            aspirational_identity=getattr(persona, "aspirational_identity", None),
            digital_behavior=getattr(persona, "digital_behavior", None),
            day_in_the_life=persona.day_in_the_life,
            data_source=persona.data_source or "synthetic",
            data_source_references=persona.data_source_references,
        )
        db.add(lib)
        db.flush()  # get lib.id without committing

    # Denormalised shortcut on the persona row
    persona.library_persona_id = lib.id

    # Junction record
    link = PersonaLibraryLink(
        persona_id=persona.id,
        library_persona_id=lib.id,
        match_score=match_score,
        linked_at=datetime.utcnow(),
    )
    db.add(link)

    return lib
