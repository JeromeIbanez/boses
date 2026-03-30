import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
from openai import OpenAI

from app.config import settings
from app.database import get_db
from app.models.persona_group import PersonaGroup
from app.models.project import Project
from app.schemas.persona_group import PersonaGroupCreate, PersonaGroupUpdate, PersonaGroupResponse
from app.services.persona_generator import generate_personas

router = APIRouter(prefix="/projects/{project_id}/persona-groups", tags=["persona-groups"])


class ParsePromptRequest(BaseModel):
    prompt: str


@router.post("/parse-prompt")
def parse_prompt(project_id: str, body: ParsePromptRequest):
    """
    Parse a natural language demographic description into structured persona group fields.
    e.g. "Metro Manila moms, 28-40, middle income, health-conscious"
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
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
                    "Return a JSON object with these fields (use sensible defaults if not mentioned):\n"
                    "{\n"
                    '  "name": "short descriptive group name",\n'
                    '  "age_min": <integer, default 18>,\n'
                    '  "age_max": <integer, default 45>,\n'
                    '  "gender": "All" | "Female" | "Male" | "Non-binary",\n'
                    '  "location": "city/region, country",\n'
                    '  "occupation": "occupation or type of work",\n'
                    '  "income_level": "Low" | "Middle" | "Upper-middle" | "High",\n'
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


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=list[PersonaGroupResponse])
def list_persona_groups(project_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    return db.execute(
        select(PersonaGroup)
        .where(PersonaGroup.project_id == project_id)
        .order_by(PersonaGroup.created_at.desc())
    ).scalars().all()


@router.post("", response_model=PersonaGroupResponse, status_code=201)
def create_persona_group(project_id: str, body: PersonaGroupCreate, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    group = PersonaGroup(project_id=project_id, **body.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/{group_id}", response_model=PersonaGroupResponse)
def get_persona_group(project_id: str, group_id: str, db: Session = Depends(get_db)):
    group = db.get(PersonaGroup, group_id)
    if not group or str(group.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Persona group not found")
    return group


@router.patch("/{group_id}", response_model=PersonaGroupResponse)
def update_persona_group(project_id: str, group_id: str, body: PersonaGroupUpdate, db: Session = Depends(get_db)):
    group = db.get(PersonaGroup, group_id)
    if not group or str(group.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Persona group not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(group, k, v)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
def delete_persona_group(project_id: str, group_id: str, db: Session = Depends(get_db)):
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
):
    group = db.get(PersonaGroup, group_id)
    if not group or str(group.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Persona group not found")

    group.generation_status = "generating"
    db.commit()

    background_tasks.add_task(generate_personas, group_id=str(group_id))
    return {"status": "generating", "persona_count": group.persona_count}
