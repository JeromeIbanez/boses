from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.persona import Persona
from app.models.persona_group import PersonaGroup
from app.schemas.persona import PersonaResponse

router = APIRouter(prefix="/projects/{project_id}/persona-groups/{group_id}/personas", tags=["personas"])


@router.get("", response_model=list[PersonaResponse])
def list_personas(project_id: str, group_id: str, db: Session = Depends(get_db)):
    group = db.get(PersonaGroup, group_id)
    if not group or str(group.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Persona group not found")
    return db.execute(
        select(Persona)
        .where(Persona.persona_group_id == group_id)
        .order_by(Persona.created_at)
    ).scalars().all()
