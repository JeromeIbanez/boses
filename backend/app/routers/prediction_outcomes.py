import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.prediction_outcome import PredictionOutcome
from app.models.simulation import Simulation
from app.routers.common import get_project_or_404
from app.schemas.prediction_outcome import (
    PredictionOutcomeCreate,
    PredictionOutcomeResponse,
    PredictionOutcomeUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/simulations/{simulation_id}/prediction-commitment",
    tags=["prediction-outcomes"],
)


def _get_simulation_or_404(project_id: str, simulation_id: str, db: Session) -> Simulation:
    sim = db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim


@router.get("", response_model=PredictionOutcomeResponse | None)
def get_commitment(
    project_id: str,
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    get_project_or_404(project_id, db, current_user.company_id)
    return db.execute(
        select(PredictionOutcome).where(PredictionOutcome.simulation_id == simulation_id)
    ).scalar_one_or_none()


@router.post("", response_model=PredictionOutcomeResponse, status_code=201)
def create_commitment(
    project_id: str,
    simulation_id: str,
    body: PredictionOutcomeCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    get_project_or_404(project_id, db, current_user.company_id)
    sim = _get_simulation_or_404(project_id, simulation_id, db)

    existing = db.execute(
        select(PredictionOutcome).where(PredictionOutcome.simulation_id == simulation_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Commitment already exists for this simulation")

    outcome = PredictionOutcome(
        id=uuid.uuid4(),
        simulation_id=sim.id,
        project_id=uuid.UUID(project_id),
        created_by_user_id=current_user.id,
        kpi_description=body.kpi_description,
        outcome_due_date=body.outcome_due_date,
        predicted_sentiment=body.predicted_sentiment,
        predicted_themes=body.predicted_themes,
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    logger.info("Prediction commitment created for simulation %s", simulation_id)
    return outcome


@router.patch("", response_model=PredictionOutcomeResponse)
def update_commitment(
    project_id: str,
    simulation_id: str,
    body: PredictionOutcomeUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    get_project_or_404(project_id, db, current_user.company_id)

    outcome = db.execute(
        select(PredictionOutcome).where(PredictionOutcome.simulation_id == simulation_id)
    ).scalar_one_or_none()
    if not outcome:
        raise HTTPException(status_code=404, detail="No commitment found for this simulation")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(outcome, field, value)

    if body.actual_outcome_description and outcome.status == "pending":
        outcome.status = "received"

    db.commit()
    db.refresh(outcome)
    return outcome
