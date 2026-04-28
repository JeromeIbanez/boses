"""POST/GET simulation ratings — one rating per user per simulation."""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.project import Project
from app.models.simulation import Simulation
from app.models.simulation_rating import SimulationRating

router = APIRouter(tags=["Simulation Ratings"])


class RatingCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    feedback: Optional[str] = Field(default=None, max_length=2000)


class RatingResponse(BaseModel):
    id: uuid.UUID
    rating: int
    feedback: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


def _get_simulation_or_403(
    project_id: uuid.UUID,
    simulation_id: uuid.UUID,
    current_user: CurrentUser,
    db: Session,
) -> Simulation:
    project = db.get(Project, project_id)
    if not project or project.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Project not found or access denied.")
    simulation = db.get(Simulation, simulation_id)
    if not simulation or simulation.project_id != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found.")
    return simulation


@router.post(
    "/projects/{project_id}/simulations/{simulation_id}/rating",
    response_model=RatingResponse,
)
def upsert_rating(
    project_id: uuid.UUID,
    simulation_id: uuid.UUID,
    body: RatingCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update the current user's rating for a simulation."""
    simulation = _get_simulation_or_403(project_id, simulation_id, current_user, db)

    if simulation.status != "complete":
        raise HTTPException(status_code=422, detail="Can only rate completed simulations.")

    existing = db.execute(
        select(SimulationRating).where(
            SimulationRating.simulation_id == simulation.id,
            SimulationRating.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.rating = body.rating
        existing.feedback = body.feedback
        db.commit()
        db.refresh(existing)
        return existing

    rating = SimulationRating(
        simulation_id=simulation.id,
        user_id=current_user.id,
        rating=body.rating,
        feedback=body.feedback,
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    return rating


@router.get(
    "/projects/{project_id}/simulations/{simulation_id}/rating",
    response_model=RatingResponse,
)
def get_rating(
    project_id: uuid.UUID,
    simulation_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's rating for a simulation, or 404 if not yet rated."""
    _get_simulation_or_403(project_id, simulation_id, current_user, db)

    rating = db.execute(
        select(SimulationRating).where(
            SimulationRating.simulation_id == simulation_id,
            SimulationRating.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not rating:
        raise HTTPException(status_code=404, detail="No rating found.")
    return rating
