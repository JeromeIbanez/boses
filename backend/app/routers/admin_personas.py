"""
Admin-only endpoints for managing Boses-curated library personas.

All routes require is_boses_staff=True. These personas are platform-wide
(not company-scoped) and appear in every user's library.
"""
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_boses_staff
from app.config import settings
from app.database import get_db
from app.models.library_persona import LibraryPersona
from app.schemas.library_persona import LibraryPersonaResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/personas", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CuratedPersonaCreate(BaseModel):
    full_name: str
    age: int
    gender: str
    location: str
    occupation: str
    income_level: str
    source_type: Optional[str] = None  # "ethnographic", "interview", "composite"
    research_notes: Optional[str] = None
    educational_background: Optional[str] = None
    family_situation: Optional[str] = None
    background: Optional[str] = None
    personality_traits: Optional[list[str]] = None
    goals: Optional[str] = None
    pain_points: Optional[str] = None
    tech_savviness: Optional[str] = None
    media_consumption: Optional[str] = None
    spending_habits: Optional[str] = None
    archetype_label: Optional[str] = None
    psychographic_segment: Optional[str] = None
    brand_attitudes: Optional[str] = None
    buying_triggers: Optional[str] = None
    aspirational_identity: Optional[str] = None
    digital_behavior: Optional[str] = None
    day_in_the_life: Optional[str] = None


class CuratedPersonaUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    income_level: Optional[str] = None
    source_type: Optional[str] = None
    research_notes: Optional[str] = None
    educational_background: Optional[str] = None
    family_situation: Optional[str] = None
    background: Optional[str] = None
    personality_traits: Optional[list[str]] = None
    goals: Optional[str] = None
    pain_points: Optional[str] = None
    tech_savviness: Optional[str] = None
    media_consumption: Optional[str] = None
    spending_habits: Optional[str] = None
    archetype_label: Optional[str] = None
    psychographic_segment: Optional[str] = None
    brand_attitudes: Optional[str] = None
    buying_triggers: Optional[str] = None
    aspirational_identity: Optional[str] = None
    digital_behavior: Optional[str] = None
    day_in_the_life: Optional[str] = None
    is_retired: Optional[bool] = None


class AdminLibraryPersonaResponse(LibraryPersonaResponse):
    is_boses_curated: bool
    research_notes: Optional[str]
    source_type: Optional[str]


class AdminPersonaListResponse(BaseModel):
    items: list[AdminLibraryPersonaResponse]
    total: int
    limit: int
    offset: int


class GenerateFromNotesRequest(BaseModel):
    full_name: str
    age: int
    gender: str
    location: str
    occupation: str
    income_level: str
    source_type: Optional[str] = "composite"
    research_notes: str  # Required for AI-assisted generation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_404(db: Session, persona_id: uuid.UUID) -> LibraryPersona:
    lp = db.get(LibraryPersona, persona_id)
    if not lp:
        raise HTTPException(status_code=404, detail="Curated persona not found")
    return lp


def _generate_avatar_for_library_persona(library_persona_id: str) -> None:
    """Background task: generate DALL-E avatar and save on the LibraryPersona."""
    from app.services.avatar_service import generate_avatar
    from app.services.openai_client import get_openai_client

    db_local = None
    try:
        from app.database import SessionLocal
        db_local = SessionLocal()
        lp = db_local.get(LibraryPersona, uuid.UUID(library_persona_id))
        if not lp:
            return
        client = get_openai_client()
        url = generate_avatar(client, lp)
        if url:
            lp.avatar_url = url
            db_local.commit()
    except Exception as e:
        logger.warning("Avatar generation failed for library persona %s: %s", library_persona_id, e)
        if db_local:
            db_local.rollback()
    finally:
        if db_local:
            db_local.close()


def _ai_enrich_persona(
    demographics: dict,
    research_notes: str,
) -> dict:
    """
    Call GPT-4o to expand demographics + research notes into a full persona profile.
    Returns a dict with all profile fields.
    """
    from app.services.openai_client import get_openai_client
    client = get_openai_client()

    system = (
        "You are a senior behavioral researcher and cultural anthropologist "
        "building a hyper-specific consumer profile for a market research platform. "
        "You have been provided with real-world research notes about an actual person "
        "(anonymized/composite). Use these notes as the primary source of truth — "
        "do not invent details that contradict the notes. You may enrich and extrapolate "
        "to fill gaps, but always anchor to what was observed in the field."
    )

    user = f"""Research notes (primary source):
{research_notes}

Demographics:
- Name: {demographics['full_name']}
- Age: {demographics['age']}
- Gender: {demographics['gender']}
- Location: {demographics['location']}
- Occupation: {demographics['occupation']}
- Income level: {demographics['income_level']}

Expand these into a complete consumer profile. Return a single JSON object with these exact keys:
{{
  "educational_background": "...",
  "family_situation": "...",
  "background": "2-3 sentences of life context",
  "personality_traits": ["trait1", "trait2", "trait3", "trait4", "trait5"],
  "goals": "specific personal and financial goals",
  "pain_points": "three distinct pain areas: financial, logistical, social/identity",
  "tech_savviness": "Low/Medium/High with brief qualifier",
  "media_consumption": "specific platforms, creators, content, timing",
  "spending_habits": "specific categories, brands, decision process",
  "archetype_label": "2-4 word archetype, e.g. 'The Reluctant Upgrader'",
  "psychographic_segment": "one VALS segment: Innovator/Thinker/Achiever/Experiencer/Believer/Striver/Maker/Survivor",
  "brand_attitudes": "specific brand relationships — loyalty, skepticism, aspirations",
  "buying_triggers": "what actually moves them to purchase",
  "aspirational_identity": "who they want to become, what they want to signal",
  "digital_behavior": "specific apps, usage patterns, online behavior",
  "day_in_the_life": "3-sentence scene: morning + core life tension + evening"
}}

Critical rules:
- NEVER generic statements. Every detail must be specific and grounded.
- Include 2+ negative personality traits.
- Reference specific brands, platforms, and locations from their market.
- Ensure everything coheres with the research notes provided."""

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.9,
        max_tokens=4096,
    )
    raw = json.loads(response.choices[0].message.content or "{}")
    return raw


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_model=AdminPersonaListResponse)
def list_curated_personas(
    curated_only: bool = True,
    source_type: Optional[str] = None,
    location: Optional[str] = None,
    is_retired: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _staff: CurrentUser = Depends(require_boses_staff),
):
    query = db.query(LibraryPersona)
    if curated_only:
        query = query.filter(LibraryPersona.is_boses_curated == True)  # noqa: E712
    if source_type:
        query = query.filter(LibraryPersona.source_type == source_type)
    if location:
        query = query.filter(LibraryPersona.location.ilike(f"%{location}%"))
    if is_retired is not None:
        query = query.filter(LibraryPersona.is_retired == is_retired)

    total = query.count()
    items = query.order_by(LibraryPersona.created_at.desc()).offset(offset).limit(limit).all()
    return AdminPersonaListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/", response_model=AdminLibraryPersonaResponse, status_code=201)
def create_curated_persona(
    body: CuratedPersonaCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _staff: CurrentUser = Depends(require_boses_staff),
):
    lp = LibraryPersona(
        is_boses_curated=True,
        data_source="boses_curated",
        **body.model_dump(exclude_none=True),
    )
    db.add(lp)
    db.commit()
    db.refresh(lp)

    # Auto-generate avatar in background if persona has enough info
    if lp.gender and lp.age and lp.location:
        background_tasks.add_task(_generate_avatar_for_library_persona, str(lp.id))

    return lp


@router.get("/{persona_id}", response_model=AdminLibraryPersonaResponse)
def get_curated_persona(
    persona_id: uuid.UUID,
    db: Session = Depends(get_db),
    _staff: CurrentUser = Depends(require_boses_staff),
):
    return _get_or_404(db, persona_id)


@router.patch("/{persona_id}", response_model=AdminLibraryPersonaResponse)
def update_curated_persona(
    persona_id: uuid.UUID,
    body: CuratedPersonaUpdate,
    db: Session = Depends(get_db),
    _staff: CurrentUser = Depends(require_boses_staff),
):
    lp = _get_or_404(db, persona_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lp, field, value)
    db.commit()
    db.refresh(lp)
    return lp


@router.delete("/{persona_id}", status_code=204)
def retire_curated_persona(
    persona_id: uuid.UUID,
    db: Session = Depends(get_db),
    _staff: CurrentUser = Depends(require_boses_staff),
):
    lp = _get_or_404(db, persona_id)
    lp.is_retired = True
    db.commit()


@router.post("/{persona_id}/avatar", response_model=AdminLibraryPersonaResponse)
def regenerate_avatar(
    persona_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _staff: CurrentUser = Depends(require_boses_staff),
):
    lp = _get_or_404(db, persona_id)
    background_tasks.add_task(_generate_avatar_for_library_persona, str(lp.id))
    return lp


@router.post("/generate", response_model=AdminLibraryPersonaResponse, status_code=201)
def generate_from_notes(
    body: GenerateFromNotesRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _staff: CurrentUser = Depends(require_boses_staff),
):
    """
    AI-assisted creation: provide demographics + research notes and GPT-4o
    will expand them into a complete persona profile. The result is saved
    as a Boses-curated LibraryPersona.
    """
    demographics = {
        "full_name": body.full_name,
        "age": body.age,
        "gender": body.gender,
        "location": body.location,
        "occupation": body.occupation,
        "income_level": body.income_level,
    }
    try:
        enriched = _ai_enrich_persona(demographics, body.research_notes)
    except Exception as e:
        logger.error("AI enrichment failed: %s", e)
        raise HTTPException(status_code=502, detail=f"AI generation failed: {e}")

    lp = LibraryPersona(
        full_name=body.full_name,
        age=body.age,
        gender=body.gender,
        location=body.location,
        occupation=body.occupation,
        income_level=body.income_level,
        source_type=body.source_type or "composite",
        research_notes=body.research_notes,
        is_boses_curated=True,
        data_source="boses_curated",
        educational_background=enriched.get("educational_background"),
        family_situation=enriched.get("family_situation"),
        background=enriched.get("background"),
        personality_traits=enriched.get("personality_traits"),
        goals=enriched.get("goals"),
        pain_points=enriched.get("pain_points"),
        tech_savviness=enriched.get("tech_savviness"),
        media_consumption=enriched.get("media_consumption"),
        spending_habits=enriched.get("spending_habits"),
        archetype_label=enriched.get("archetype_label"),
        psychographic_segment=enriched.get("psychographic_segment"),
        brand_attitudes=enriched.get("brand_attitudes"),
        buying_triggers=enriched.get("buying_triggers"),
        aspirational_identity=enriched.get("aspirational_identity"),
        digital_behavior=enriched.get("digital_behavior"),
        day_in_the_life=enriched.get("day_in_the_life"),
    )
    db.add(lp)
    db.commit()
    db.refresh(lp)

    # Kick off avatar generation in background
    background_tasks.add_task(_generate_avatar_for_library_persona, str(lp.id))

    return lp
