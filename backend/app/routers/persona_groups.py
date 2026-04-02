import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
from openai import OpenAI

from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.database import get_db
from app.models.persona_group import PersonaGroup
from app.models.project import Project
from app.schemas.persona_group import PersonaGroupCreate, PersonaGroupUpdate, PersonaGroupResponse
from app.services.persona_generator import generate_personas
from app.services.ethnography_service import should_refresh, refresh_market_context

router = APIRouter(prefix="/projects/{project_id}/persona-groups", tags=["persona-groups"])


class ParsePromptRequest(BaseModel):
    prompt: str


def _get_project_or_404(project_id: str, db: Session, company_id) -> Project:
    project = db.get(Project, project_id)
    if not project or project.company_id != company_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/parse-prompt")
def parse_prompt(
    project_id: str,
    body: ParsePromptRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a market research assistant. Extract structured demographic fields "
                        "from a natural language description. Return valid JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Extract demographic fields from this description:\n\"{body.prompt}\"\n\n"
                        "Return a JSON object with these exact fields (use sensible defaults if not mentioned):\n"
                        "{\n"
                        '  "name": "short descriptive group name",\n'
                        '  "age_min": <integer, default 18>,\n'
                        '  "age_max": <integer, default 45>,\n'
                        '  "gender": "All" or "Female" or "Male" or "Non-binary",\n'
                        '  "location": "city/region, country",\n'
                        '  "occupation": "occupation or type of work",\n'
                        '  "income_level": "Low" or "Middle" or "Upper-middle" or "High",\n'
                        '  "psychographic_notes": "any lifestyle, values, or behavioral notes",\n'
                        '  "persona_count": <integer between 3 and 10, default 5>\n'
                        "}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[PersonaGroupResponse])
def list_persona_groups(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    return db.execute(
        select(PersonaGroup)
        .where(PersonaGroup.project_id == project_id)
        .order_by(PersonaGroup.created_at.desc())
    ).scalars().all()


@router.post("", response_model=PersonaGroupResponse, status_code=201)
def create_persona_group(
    project_id: str,
    body: PersonaGroupCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    group = PersonaGroup(project_id=project_id, **body.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/{group_id}", response_model=PersonaGroupResponse)
def get_persona_group(
    project_id: str,
    group_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    group = db.get(PersonaGroup, group_id)
    if not group or str(group.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Persona group not found")
    return group


@router.patch("/{group_id}", response_model=PersonaGroupResponse)
def update_persona_group(
    project_id: str,
    group_id: str,
    body: PersonaGroupUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    group = db.get(PersonaGroup, group_id)
    if not group or str(group.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Persona group not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(group, k, v)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
def delete_persona_group(
    project_id: str,
    group_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    group = db.get(PersonaGroup, group_id)
    if not group or str(group.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Persona group not found")
    db.delete(group)
    db.commit()


@router.post("/{group_id}/generate", status_code=202)
def generate_group_personas(
    project_id: str,
    group_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    group = db.get(PersonaGroup, group_id)
    if not group or str(group.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Persona group not found")
    group.generation_status = "generating"
    db.commit()
    background_tasks.add_task(generate_personas, group_id=str(group_id))

    # Lazily refresh cultural context if this market's snapshot is missing or stale.
    # The current generation uses whatever context already exists (could be None on
    # first run). Future generations for this market will benefit from the refresh.
    if should_refresh(group.location or ""):
        from app.services.ethnography_service import _detect_market
        market_code = _detect_market(group.location or "")
        if market_code:
            background_tasks.add_task(refresh_market_context, market_code)

    return {"status": "generating", "persona_count": group.persona_count}
