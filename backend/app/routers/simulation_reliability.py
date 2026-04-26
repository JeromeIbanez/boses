"""
Reliability check (reproducibility) endpoints.
Handles POST (kick off N repeat runs) and GET (fetch study status/scores).
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.constants import RELIABILITY_DEFAULT_RUNS, RELIABILITY_MAX_RUNS, RELIABILITY_MIN_RUNS
from app.database import get_db
from app.models.simulation import Simulation
from app.routers.common import get_project_or_404 as _get_project_or_404
from app.services.simulation_engine import run_simulation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/simulations", tags=["simulations"])


@router.post("/{simulation_id}/reliability-check")
def create_reliability_check(
    project_id: str,
    simulation_id: str,
    body: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Kick off N repeat runs of a simulation to compute a confidence score."""
    from app.models.reproducibility import ReproducibilityStudy, ReproducibilityRun

    _get_project_or_404(project_id, db, current_user.company_id)
    source = db.get(Simulation, simulation_id)
    if not source or str(source.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if source.status != "complete":
        raise HTTPException(status_code=422, detail="Only completed simulations can be checked for reliability")

    n_runs = max(RELIABILITY_MIN_RUNS, min(int(body.get("n_runs", RELIABILITY_DEFAULT_RUNS)), RELIABILITY_MAX_RUNS))

    study = ReproducibilityStudy(
        project_id=project_id,
        source_simulation_id=source.id,
        n_runs=n_runs,
        status="running",
    )
    db.add(study)
    db.flush()

    for i in range(1, n_runs + 1):
        repeat_sim = Simulation(
            project_id=str(source.project_id),
            persona_group_id=source.persona_group_id,
            prompt_question=source.prompt_question,
            simulation_type=source.simulation_type,
            idi_script_text=source.idi_script_text,
            survey_schema=source.survey_schema,
            status="pending",
        )
        db.add(repeat_sim)
        db.flush()
        repeat_sim.persona_groups = list(source.persona_groups)
        repeat_sim.briefings = list(source.briefings)

        from app.models.reproducibility import ReproducibilityRun
        repro_run = ReproducibilityRun(
            study_id=study.id,
            simulation_id=repeat_sim.id,
            run_index=i,
        )
        db.add(repro_run)
        background_tasks.add_task(run_simulation, simulation_id=str(repeat_sim.id))

    db.commit()
    db.refresh(study)
    return {
        "id": str(study.id),
        "source_simulation_id": simulation_id,
        "n_runs": n_runs,
        "status": study.status,
        "confidence_score": None,
        "created_at": study.created_at.isoformat(),
    }


@router.get("/{simulation_id}/reliability-check")
def get_reliability_check(
    project_id: str,
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get the latest reliability study for a simulation."""
    from app.models.reproducibility import ReproducibilityStudy

    _get_project_or_404(project_id, db, current_user.company_id)

    study = db.execute(
        select(ReproducibilityStudy)
        .where(ReproducibilityStudy.source_simulation_id == simulation_id)
        .order_by(ReproducibilityStudy.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if not study:
        return {"exists": False}

    return {
        "exists": True,
        "id": str(study.id),
        "source_simulation_id": simulation_id,
        "n_runs": study.n_runs,
        "status": study.status,
        "confidence_score": study.confidence_score,
        "sentiment_agreement_rate": study.sentiment_agreement_rate,
        "distribution_variance_score": study.distribution_variance_score,
        "theme_overlap_coefficient": study.theme_overlap_coefficient,
        "score_breakdown": study.score_breakdown,
        "created_at": study.created_at.isoformat(),
        "completed_at": study.completed_at.isoformat() if study.completed_at else None,
    }
