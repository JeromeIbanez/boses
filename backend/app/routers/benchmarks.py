import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.benchmark import BenchmarkCase, BenchmarkRun
from app.models.simulation import Simulation
from app.services.simulation_engine import run_simulation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


# ---------------------------------------------------------------------------
# Cases (platform-managed)
# ---------------------------------------------------------------------------

@router.get("")
def list_benchmark_cases(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all active benchmark cases."""
    cases = db.execute(
        select(BenchmarkCase)
        .where(BenchmarkCase.is_active == True)
        .order_by(BenchmarkCase.created_at)
    ).scalars().all()

    return [
        {
            "id": str(c.id),
            "slug": c.slug,
            "title": c.title,
            "category": c.category,
            "description": c.description,
            "simulation_type": c.simulation_type,
            "ground_truth": {
                "sentiment": c.ground_truth.get("sentiment"),
                "outcome_summary": c.ground_truth.get("outcome_summary"),
                "top_themes": c.ground_truth.get("top_themes", []),
            },
        }
        for c in cases
    ]


@router.get("/runs")
def list_my_benchmark_runs(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all benchmark runs for the current company."""
    runs = db.execute(
        select(BenchmarkRun)
        .where(BenchmarkRun.company_id == current_user.company_id)
        .order_by(BenchmarkRun.created_at.desc())
    ).scalars().all()

    result = []
    for r in runs:
        case = db.get(BenchmarkCase, r.benchmark_case_id)
        result.append({
            "id": str(r.id),
            "benchmark_case_id": str(r.benchmark_case_id),
            "benchmark_case_title": case.title if case else None,
            "benchmark_case_slug": case.slug if case else None,
            "simulation_id": str(r.simulation_id),
            "status": r.status,
            "overall_accuracy_score": r.overall_accuracy_score,
            "score_breakdown": r.score_breakdown,
            "created_at": r.created_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        })
    return result


@router.get("/{slug}")
def get_benchmark_case(
    slug: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a benchmark case by slug (full detail including ground truth)."""
    case = db.execute(
        select(BenchmarkCase).where(BenchmarkCase.slug == slug, BenchmarkCase.is_active == True)
    ).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Benchmark case not found")

    return {
        "id": str(case.id),
        "slug": case.slug,
        "title": case.title,
        "category": case.category,
        "description": case.description,
        "briefing_text": case.briefing_text,
        "prompt_question": case.prompt_question,
        "simulation_type": case.simulation_type,
        "ground_truth": case.ground_truth,
        "source_citations": case.source_citations or [],
    }


@router.post("/{slug}/run")
def run_benchmark(
    slug: str,
    body: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Create a simulation pre-loaded with the benchmark case briefing and kick it off.
    Body: { "persona_group_id": "<uuid>", "project_id": "<uuid>" }
    """
    from app.models.project import Project

    case = db.execute(
        select(BenchmarkCase).where(BenchmarkCase.slug == slug, BenchmarkCase.is_active == True)
    ).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Benchmark case not found")

    persona_group_id = body.get("persona_group_id")
    project_id = body.get("project_id")
    if not persona_group_id or not project_id:
        raise HTTPException(status_code=422, detail="persona_group_id and project_id are required")

    project = db.get(Project, project_id)
    if not project or project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create a special simulation — briefing_text injected via prompt_question workaround:
    # We store the briefing text as idi_script_text (repurposed), and handle it in scoring.
    # Actually: create a transient Briefing record for the benchmark text.
    from app.models.briefing import Briefing

    briefing = Briefing(
        project_id=project_id,
        title=f"[Benchmark] {case.title}",
        description=f"Auto-created for benchmark: {case.slug}",
        file_name=f"benchmark_{case.slug}.txt",
        file_path="",
        file_type="text",
        extracted_text=case.briefing_text,
    )
    db.add(briefing)
    db.flush()

    sim = Simulation(
        project_id=project_id,
        persona_group_id=persona_group_id,
        briefing_id=briefing.id,
        prompt_question=case.prompt_question,
        simulation_type=case.simulation_type,
        status="pending",
    )
    db.add(sim)
    db.flush()

    bench_run = BenchmarkRun(
        benchmark_case_id=case.id,
        simulation_id=sim.id,
        company_id=current_user.company_id,
        status="pending",
    )
    db.add(bench_run)
    db.commit()

    background_tasks.add_task(run_simulation, simulation_id=str(sim.id))

    return {
        "id": str(bench_run.id),
        "simulation_id": str(sim.id),
        "benchmark_case_slug": case.slug,
        "status": bench_run.status,
        "created_at": bench_run.created_at.isoformat(),
    }
