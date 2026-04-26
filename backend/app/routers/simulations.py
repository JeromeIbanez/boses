"""
Core simulation CRUD endpoints.
Type-specific endpoints live in focused sub-routers:
  - simulation_idi.py       — IDI script upload, chat messages, session end
  - simulation_survey.py    — survey file upload + run confirmation
  - simulation_conjoint.py  — conjoint design + start
  - simulation_reliability.py — reliability check (reproducibility)
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.constants import SIMULATION_CREATE_RATE_LIMIT, SIMULATION_TIMEOUT_MINUTES
from app.database import get_db
from app.limiter import limiter
from app.models.simulation import Simulation
from app.models.simulation_result import SimulationResult
from app.routers.common import get_project_or_404 as _get_project_or_404
from app.schemas.simulation import SimulationCreate, SimulationResponse, SimulationResultResponse
from app.request_context import get_request_id
from app.services.simulation_engine import run_simulation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/simulations", tags=["simulations"])


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get("", response_model=list[SimulationResponse])
def list_simulations(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from app.models.reproducibility import ReproducibilityRun
    _get_project_or_404(project_id, db, current_user.company_id)
    reliability_run_ids = select(ReproducibilityRun.simulation_id)
    return db.execute(
        select(Simulation)
        .where(Simulation.project_id == project_id)
        .where(Simulation.id.not_in(reliability_run_ids))
        .order_by(Simulation.created_at.desc())
    ).scalars().all()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("", response_model=SimulationResponse, status_code=201)
@limiter.limit(SIMULATION_CREATE_RATE_LIMIT)
def create_simulation(
    request: Request,
    project_id: str,
    body: SimulationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)

    # --- Type-specific validation ---
    if body.simulation_type == "concept_test":
        if not body.briefing_ids:
            raise HTTPException(status_code=422, detail="At least one briefing is required for concept tests")
        if not body.prompt_question or not body.prompt_question.strip():
            raise HTTPException(status_code=422, detail="prompt_question is required for concept tests")

    if body.simulation_type == "idi_manual":
        if not body.idi_persona_id:
            raise HTTPException(status_code=422, detail="idi_persona_id is required for manual IDI")

    if body.simulation_type == "focus_group":
        if not body.prompt_question or not body.prompt_question.strip():
            raise HTTPException(status_code=422, detail="prompt_question is required for focus groups")

    if body.simulation_type == "conjoint":
        if not body.prompt_question or not body.prompt_question.strip():
            raise HTTPException(status_code=422, detail="prompt_question (product category) is required for conjoint tests")

    # For idi_ai with inline script — file-upload mode sends no script here;
    # the background task is triggered by the upload endpoint instead.
    idi_ai_ready = body.simulation_type == "idi_ai" and bool(body.idi_script_text and body.idi_script_text.strip())

    initial_status = "active" if body.simulation_type == "idi_manual" else "pending"

    # --- Validate persona groups ---
    from app.models.persona_group import PersonaGroup as PersonaGroupModel
    groups = db.execute(
        select(PersonaGroupModel).where(PersonaGroupModel.id.in_(body.persona_group_ids))
    ).scalars().all()
    if len(groups) != len(body.persona_group_ids):
        raise HTTPException(status_code=422, detail="One or more persona group IDs not found")
    for g in groups:
        if str(g.project_id) != project_id:
            raise HTTPException(status_code=403, detail="Persona group does not belong to this project")
        if g.generation_status != "complete":
            raise HTTPException(status_code=422, detail=f"Persona group '{g.name}' has not finished generating personas yet")

    simulation = Simulation(
        project_id=project_id,
        persona_group_id=body.persona_group_ids[0],  # legacy compat — first group
        prompt_question=body.prompt_question,
        simulation_type=body.simulation_type,
        idi_script_text=body.idi_script_text,
        idi_persona_id=body.idi_persona_id,
        survey_schema=body.survey_schema,
        status=initial_status,
    )
    db.add(simulation)
    db.flush()
    simulation.persona_groups = groups

    # --- Attach briefings ---
    if body.briefing_ids:
        from app.models.briefing import Briefing as BriefingModel
        briefings = db.execute(
            select(BriefingModel).where(BriefingModel.id.in_(body.briefing_ids))
        ).scalars().all()
        if len(briefings) != len(body.briefing_ids):
            raise HTTPException(status_code=422, detail="One or more briefing IDs not found")
        for b in briefings:
            if str(b.project_id) != project_id:
                raise HTTPException(status_code=403, detail="Briefing does not belong to this project")
        simulation.briefings = briefings

    db.commit()
    db.refresh(simulation)

    # Schedule background task now only if we already have the script (text mode).
    # File-upload mode (IDI/survey): task is scheduled after the file is processed.
    if body.simulation_type in ("concept_test", "focus_group") or idi_ai_ready:
        background_tasks.add_task(run_simulation, simulation_id=str(simulation.id), request_id=get_request_id())

    return simulation


# ---------------------------------------------------------------------------
# Convergence
# ---------------------------------------------------------------------------

@router.get("/convergence")
def get_convergence(
    project_id: str,
    persona_group_id: str,
    briefing_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return convergence scores across completed simulations sharing the same persona group."""
    from app.services.benchmarking_service import compute_convergence
    _get_project_or_404(project_id, db, current_user.company_id)
    return compute_convergence(
        project_id=project_id,
        briefing_id=briefing_id,
        persona_group_id=persona_group_id,
        db=db,
    )


# ---------------------------------------------------------------------------
# Get / abort / delete
# ---------------------------------------------------------------------------

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

    # If stuck in running/pending for too long, auto-fail
    if simulation.status in ("running", "pending", "generating_report"):
        age = datetime.utcnow() - simulation.created_at
        if age > timedelta(minutes=SIMULATION_TIMEOUT_MINUTES):
            simulation.status = "failed"
            simulation.error_message = "Simulation timed out — the background task may have been interrupted. Please try again."
            db.commit()

    return simulation


@router.post("/{simulation_id}/abort", response_model=SimulationResponse)
def abort_simulation(
    project_id: str,
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Abort a running or pending simulation."""
    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = db.get(Simulation, simulation_id)
    if not simulation or str(simulation.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if simulation.status not in ("pending", "running", "generating_report"):
        raise HTTPException(status_code=422, detail="Simulation is not currently running")
    simulation.status = "failed"
    simulation.error_message = "Aborted by user"
    db.commit()
    db.refresh(simulation)
    return simulation


@router.delete("/{simulation_id}", status_code=204)
def delete_simulation(
    project_id: str,
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = db.get(Simulation, simulation_id)
    if not simulation or str(simulation.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")
    db.delete(simulation)
    db.commit()


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

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
