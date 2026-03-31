from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.simulation import Simulation
from app.models.simulation_result import SimulationResult
from app.models.project import Project
from app.schemas.simulation import SimulationCreate, SimulationResponse, SimulationResultResponse
from app.services.simulation_engine import run_simulation

router = APIRouter(prefix="/projects/{project_id}/simulations", tags=["simulations"])


def _get_project_or_404(project_id: str, db: Session, company_id) -> Project:
    project = db.get(Project, project_id)
    if not project or project.company_id != company_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=list[SimulationResponse])
def list_simulations(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    return db.execute(
        select(Simulation)
        .where(Simulation.project_id == project_id)
        .order_by(Simulation.created_at.desc())
    ).scalars().all()


@router.post("", response_model=SimulationResponse, status_code=201)
def create_simulation(
    project_id: str,
    body: SimulationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = Simulation(
        project_id=project_id,
        persona_group_id=body.persona_group_id,
        briefing_id=body.briefing_id,
        prompt_question=body.prompt_question,
        status="pending",
    )
    db.add(simulation)
    db.commit()
    db.refresh(simulation)
    background_tasks.add_task(run_simulation, simulation_id=str(simulation.id))
    return simulation


@router.get("/{simulation_id}", response_model=SimulationResponse)
def get_simulation(
    project_id: str,
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = db.get(Simulation, simulation_id)
    if not simulation or str(simulation.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return simulation


@router.get("/{simulation_id}/results", response_model=list[SimulationResultResponse])
def get_simulation_results(
    project_id: str,
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = db.get(Simulation, simulation_id)
    if not simulation or str(simulation.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return db.execute(
        select(SimulationResult)
        .where(SimulationResult.simulation_id == simulation_id)
        .order_by(SimulationResult.created_at)
    ).scalars().all()
