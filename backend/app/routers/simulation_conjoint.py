"""
Conjoint simulation endpoints.
Handles the design-and-start step for conjoint analyses.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.constants import CONJOINT_MAX_TASKS, CONJOINT_MIN_TASKS
from app.database import get_db
from app.models.simulation import Simulation
from app.routers.common import get_project_or_404 as _get_project_or_404
from app.schemas.simulation import ConjointDesignCreate, SimulationResponse
from app.services.simulation_engine import run_simulation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/simulations", tags=["simulations"])


def _get_simulation_or_404(simulation_id: str, project_id: str, db: Session) -> Simulation:
    simulation = db.get(Simulation, simulation_id)
    if not simulation or str(simulation.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return simulation


@router.post("/{simulation_id}/conjoint-design", response_model=SimulationResponse)
def run_conjoint_simulation(
    project_id: str,
    simulation_id: str,
    body: ConjointDesignCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Save conjoint attribute/level design and start the simulation."""
    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = _get_simulation_or_404(simulation_id, project_id, db)

    if simulation.simulation_type != "conjoint":
        raise HTTPException(status_code=422, detail="This endpoint is only for conjoint simulations")
    if simulation.status != "pending":
        raise HTTPException(status_code=422, detail="Simulation is not in pending state")
    if len(body.attributes) < 2:
        raise HTTPException(status_code=422, detail="At least 2 attributes are required")
    if any(len(a.levels) < 2 for a in body.attributes):
        raise HTTPException(status_code=422, detail="Each attribute must have at least 2 levels")

    simulation.survey_schema = {
        "attributes": [{"name": a.name, "levels": a.levels} for a in body.attributes],
        "n_tasks": min(max(body.n_tasks, CONJOINT_MIN_TASKS), CONJOINT_MAX_TASKS),
    }
    db.commit()
    db.refresh(simulation)

    background_tasks.add_task(run_simulation, simulation_id=str(simulation.id))
    return simulation
