from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.persona import Persona
from app.models.persona_group import PersonaGroup
from app.models.project import Project
from app.schemas.persona import PersonaResponse

router = APIRouter(prefix="/projects/{project_id}/persona-groups/{group_id}/personas", tags=["personas"])


def _get_group_or_404(project_id: str, group_id: str, db: Session, company_id) -> PersonaGroup:
    project = db.get(Project, project_id)
    if not project or project.company_id != company_id:
        raise HTTPException(status_code=404, detail="Project not found")
    group = db.get(PersonaGroup, group_id)
    if not group or str(group.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Persona group not found")
    return group


@router.get("", response_model=list[PersonaResponse])
def list_personas(
    project_id: str,
    group_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_group_or_404(project_id, group_id, db, current_user.company_id)
    return db.execute(
        select(Persona)
        .where(Persona.persona_group_id == group_id)
        .order_by(Persona.created_at)
    ).scalars().all()
