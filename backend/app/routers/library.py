from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.library_persona import LibraryPersona, PersonaLibraryLink
from app.models.persona import Persona
from app.models.persona_group import PersonaGroup
from app.models.project import Project
from app.schemas.library_persona import (
    LibraryPersonaResponse,
    LibraryPersonaListResponse,
    LibraryPersonaProjectEntry,
)

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/personas", response_model=LibraryPersonaListResponse)
def list_library_personas(
    location: Optional[str] = None,
    gender: Optional[str] = None,
    income_level: Optional[str] = None,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    occupation: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    query = db.query(LibraryPersona).filter(LibraryPersona.is_retired == False)  # noqa: E712

    if location:
        query = query.filter(LibraryPersona.location.ilike(f"%{location}%"))
    if gender:
        query = query.filter(LibraryPersona.gender.ilike(f"%{gender}%"))
    if income_level:
        query = query.filter(LibraryPersona.income_level.ilike(f"%{income_level}%"))
    if age_min is not None:
        query = query.filter(LibraryPersona.age >= age_min)
    if age_max is not None:
        query = query.filter(LibraryPersona.age <= age_max)
    if occupation:
        query = query.filter(LibraryPersona.occupation.ilike(f"%{occupation}%"))

    total = query.count()
    items = query.order_by(LibraryPersona.simulation_count.desc(), LibraryPersona.created_at.desc()).offset(offset).limit(limit).all()

    return LibraryPersonaListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/personas/{library_persona_id}", response_model=LibraryPersonaResponse)
def get_library_persona(
    library_persona_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    lp = db.get(LibraryPersona, library_persona_id)
    if not lp or lp.is_retired:
        raise HTTPException(status_code=404, detail="Library persona not found")
    return lp


@router.get("/personas/{library_persona_id}/projects", response_model=list[LibraryPersonaProjectEntry])
def get_library_persona_projects(
    library_persona_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    lp = db.get(LibraryPersona, library_persona_id)
    if not lp:
        raise HTTPException(status_code=404, detail="Library persona not found")

    rows = (
        db.query(
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            PersonaGroup.id.label("group_id"),
            PersonaGroup.name.label("group_name"),
            PersonaLibraryLink.linked_at,
        )
        .join(PersonaLibraryLink, PersonaLibraryLink.library_persona_id == library_persona_id)
        .join(Persona, Persona.id == PersonaLibraryLink.persona_id)
        .join(PersonaGroup, PersonaGroup.id == Persona.persona_group_id)
        .join(Project, Project.id == PersonaGroup.project_id)
        .order_by(PersonaLibraryLink.linked_at.desc())
        .all()
    )

    return [
        LibraryPersonaProjectEntry(
            project_id=r.project_id,
            project_name=r.project_name,
            group_id=r.group_id,
            group_name=r.group_name,
            linked_at=r.linked_at,
        )
        for r in rows
    ]


@router.post("/personas/{library_persona_id}/retire", response_model=LibraryPersonaResponse)
def retire_library_persona(
    library_persona_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    lp = db.get(LibraryPersona, library_persona_id)
    if not lp:
        raise HTTPException(status_code=404, detail="Library persona not found")
    lp.is_retired = True
    db.commit()
    db.refresh(lp)
    return lp


@router.delete("/personas/{library_persona_id}", status_code=204)
def delete_library_persona(
    library_persona_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    lp = db.get(LibraryPersona, library_persona_id)
    if not lp:
        raise HTTPException(status_code=404, detail="Library persona not found")
    # Null out denormalised FK on project personas
    db.query(Persona).filter(Persona.library_persona_id == library_persona_id).update(
        {"library_persona_id": None}, synchronize_session=False
    )
    # Remove junction records — use synchronize_session=False so the session does not
    # try to SET NULL library_persona_id (which is NOT NULL) on the ORM objects
    db.query(PersonaLibraryLink).filter(
        PersonaLibraryLink.library_persona_id == library_persona_id
    ).delete(synchronize_session=False)
    # Expire lp so SQLAlchemy re-checks the (now empty) links collection before deletion
    db.expire(lp)
    db.delete(lp)
    db.commit()


@router.delete("/personas", status_code=204)
def delete_all_library_personas(
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    # Null out all library persona references on project personas
    db.query(Persona).filter(Persona.library_persona_id.isnot(None)).update(
        {"library_persona_id": None}, synchronize_session=False
    )
    # Remove all junction records first (library_persona_id is NOT NULL — must delete before parent)
    db.query(PersonaLibraryLink).delete(synchronize_session=False)
    # Delete all library personas
    db.query(LibraryPersona).delete(synchronize_session=False)
    db.commit()
