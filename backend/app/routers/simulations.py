import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, BackgroundTasks, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.database import get_db
from app.models.idi_message import IDIMessage
from app.models.persona import Persona
from app.models.simulation import Simulation
from app.models.simulation_result import SimulationResult
from app.models.project import Project
from app.schemas.simulation import (
    IDIMessageCreate,
    IDIMessageResponse,
    SimulationCreate,
    SimulationResponse,
    SimulationResultResponse,
)
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

    # Validate based on type
    if body.simulation_type == "concept_test":
        if not body.briefing_id:
            raise HTTPException(status_code=422, detail="briefing_id is required for concept tests")
        if not body.prompt_question or not body.prompt_question.strip():
            raise HTTPException(status_code=422, detail="prompt_question is required for concept tests")

    if body.simulation_type == "idi_manual":
        if not body.idi_persona_id:
            raise HTTPException(status_code=422, detail="idi_persona_id is required for manual IDI")

    # For idi_ai with inline script, validate it's non-empty.
    # File-upload mode sends no script here — the background task is triggered by the upload endpoint instead.
    idi_ai_ready = body.simulation_type == "idi_ai" and bool(body.idi_script_text and body.idi_script_text.strip())

    initial_status = "active" if body.simulation_type == "idi_manual" else "pending"

    simulation = Simulation(
        project_id=project_id,
        persona_group_id=body.persona_group_id,
        briefing_id=body.briefing_id,
        prompt_question=body.prompt_question,
        simulation_type=body.simulation_type,
        idi_script_text=body.idi_script_text,
        idi_persona_id=body.idi_persona_id,
        status=initial_status,
    )
    db.add(simulation)
    db.commit()
    db.refresh(simulation)

    # Schedule background task now only if we already have the script (text mode).
    # File-upload mode: task is scheduled after the script file is processed.
    if body.simulation_type == "concept_test" or idi_ai_ready:
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


@router.post("/{simulation_id}/script", response_model=SimulationResponse)
async def upload_idi_script(
    project_id: str,
    simulation_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload a script file (.txt or .docx) for an IDI simulation.
    Extracts the text and stores it in idi_script_text."""
    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = db.get(Simulation, simulation_id)
    if not simulation or str(simulation.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if simulation.simulation_type not in ("idi_ai", "idi_manual"):
        raise HTTPException(status_code=422, detail="Script upload only applies to IDI simulations")

    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in (".txt", ".docx"):
        raise HTTPException(status_code=422, detail="Only .txt and .docx files are supported for scripts")

    # Save file temporarily, extract text
    save_dir = Path(settings.UPLOAD_DIR) / project_id / "scripts"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{uuid.uuid4().hex}_{filename}"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    if ext == ".txt":
        script_text = save_path.read_text(errors="replace")
    else:
        try:
            import docx
            doc = docx.Document(str(save_path))
            script_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception:
            raise HTTPException(status_code=422, detail="Could not read .docx file")

    simulation.idi_script_text = script_text
    db.commit()
    db.refresh(simulation)

    # If this is an idi_ai simulation waiting on its script, kick off the background task now
    if simulation.simulation_type == "idi_ai" and simulation.status == "pending":
        background_tasks.add_task(run_simulation, simulation_id=str(simulation.id))

    return simulation


# ---------------------------------------------------------------------------
# Manual IDI chat endpoints
# ---------------------------------------------------------------------------

@router.get("/{simulation_id}/messages", response_model=list[IDIMessageResponse])
def get_idi_messages(
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
        select(IDIMessage)
        .where(IDIMessage.simulation_id == simulation_id)
        .order_by(IDIMessage.created_at)
    ).scalars().all()


@router.post("/{simulation_id}/messages", response_model=IDIMessageResponse)
def send_idi_message(
    project_id: str,
    simulation_id: str,
    body: IDIMessageCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Send a message as the interviewer and receive the persona's response."""
    from openai import OpenAI
    from app.services.idi_engine import _build_persona_system_prompt

    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = db.get(Simulation, simulation_id)
    if not simulation or str(simulation.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if simulation.simulation_type != "idi_manual":
        raise HTTPException(status_code=422, detail="Messages endpoint is only for manual IDI sessions")
    if simulation.status != "active":
        raise HTTPException(status_code=422, detail="This interview session is no longer active")

    persona = db.get(Persona, simulation.idi_persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Save user message
    user_msg = IDIMessage(
        simulation_id=simulation_id,
        persona_id=None,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    db.flush()

    # Build full conversation history for OpenAI
    history = db.execute(
        select(IDIMessage)
        .where(IDIMessage.simulation_id == simulation_id)
        .order_by(IDIMessage.created_at)
    ).scalars().all()

    briefing_text = simulation.briefing.extracted_text if simulation.briefing else ""
    system_prompt = _build_persona_system_prompt(persona, briefing_text)

    # Build script context block if available
    script_block = ""
    if simulation.idi_script_text:
        script_block = (
            f"\n\nNote: The interviewer has prepared the following research questions as a guide "
            f"(they may not follow this exactly):\n{simulation.idi_script_text}"
        )

    oai_messages = [{"role": "system", "content": system_prompt + script_block}]
    for msg in history:
        oai_messages.append({
            "role": "user" if msg.role == "user" else "assistant",
            "content": msg.content,
        })

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=oai_messages,
        temperature=0.85,
    )
    answer = response.choices[0].message.content or ""

    # Save persona response
    persona_msg = IDIMessage(
        simulation_id=simulation_id,
        persona_id=persona.id,
        role="persona",
        content=answer,
    )
    db.add(persona_msg)
    db.commit()
    db.refresh(persona_msg)
    return persona_msg


@router.post("/{simulation_id}/end", response_model=SimulationResponse)
def end_idi_session(
    project_id: str,
    simulation_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """End a manual IDI session and trigger report generation."""
    from app.services.idi_engine import generate_idi_report_from_messages

    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = db.get(Simulation, simulation_id)
    if not simulation or str(simulation.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if simulation.simulation_type != "idi_manual":
        raise HTTPException(status_code=422, detail="Only manual IDI sessions can be ended this way")
    if simulation.status != "active":
        raise HTTPException(status_code=422, detail="Session is not active")

    simulation.status = "generating_report"
    db.commit()
    db.refresh(simulation)

    background_tasks.add_task(generate_idi_report_from_messages, simulation_id=simulation_id)
    return simulation
