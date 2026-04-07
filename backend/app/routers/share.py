"""Public share endpoints — no authentication required."""
import secrets
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.simulation import Simulation
from app.models.simulation_result import SimulationResult
from app.models.project import Project
from app.schemas.simulation import SimulationResponse, SimulationResultResponse
from app.auth.dependencies import CurrentUser, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["share"])


# ---------------------------------------------------------------------------
# Authenticated: generate / revoke share token
# ---------------------------------------------------------------------------

@router.post(
    "/projects/{project_id}/simulations/{simulation_id}/share",
    response_model=SimulationResponse,
)
def generate_share_link(
    project_id: str,
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Generate a public share token for a completed simulation."""
    project = db.get(Project, project_id)
    if not project or project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Project not found")

    simulation = db.get(Simulation, simulation_id)
    if not simulation or str(simulation.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if simulation.status != "complete":
        raise HTTPException(status_code=422, detail="Only completed simulations can be shared")

    if not simulation.share_token:
        simulation.share_token = secrets.token_urlsafe(32)
        db.commit()
        db.refresh(simulation)

    return simulation


@router.delete(
    "/projects/{project_id}/simulations/{simulation_id}/share",
    response_model=SimulationResponse,
)
def revoke_share_link(
    project_id: str,
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Revoke a simulation's share token, making the link inaccessible."""
    project = db.get(Project, project_id)
    if not project or project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Project not found")

    simulation = db.get(Simulation, simulation_id)
    if not simulation or str(simulation.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation.share_token = None
    db.commit()
    db.refresh(simulation)
    return simulation


# ---------------------------------------------------------------------------
# Public: view shared simulation (no auth)
# ---------------------------------------------------------------------------

class SharedSimulationResponse(SimulationResponse):
    project_name: str
    results: list[SimulationResultResponse] = []


@router.get("/share/{share_token}", response_model=SharedSimulationResponse)
def get_shared_simulation(
    share_token: str,
    db: Session = Depends(get_db),
):
    """Public endpoint — returns simulation + results for a valid share token."""
    simulation = db.execute(
        select(Simulation).where(Simulation.share_token == share_token)
    ).scalar_one_or_none()

    if not simulation:
        raise HTTPException(status_code=404, detail="Share link not found or has been revoked")

    project = db.get(Project, simulation.project_id)
    results = db.execute(
        select(SimulationResult)
        .where(SimulationResult.simulation_id == simulation.id)
        .order_by(SimulationResult.created_at)
    ).scalars().all()

    response_data = SimulationResponse.model_validate(simulation).model_dump()
    response_data["project_name"] = project.name if project else "Untitled Project"
    response_data["results"] = [SimulationResultResponse.model_validate(r) for r in results]

    return response_data
