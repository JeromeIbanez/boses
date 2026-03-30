from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.persona_group import PersonaGroup
from app.models.project import Project
from app.schemas.persona_group import PersonaGroupCreate, PersonaGroupUpdate, PersonaGroupResponse
from app.services.persona_generator import generate_personas

router = APIRouter(prefix="/projects/{project_id}/persona-groups", tags=["persona-groups"])


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
