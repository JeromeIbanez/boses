"""
IDI (In-Depth Interview) simulation endpoints.
Handles script upload, manual chat messages, and session end/report generation.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.constants import SURVEY_PARSE_TEMPERATURE
from app.database import get_db
from app.models.idi_message import IDIMessage
from app.models.persona import Persona
from app.models.simulation import Simulation
from app.routers.common import get_project_or_404 as _get_project_or_404
from app.schemas.simulation import IDIMessageCreate, IDIMessageResponse, SimulationResponse
from app.request_context import get_request_id
from app.services.openai_client import get_openai_client
from app.services.simulation_engine import run_simulation
from app.utils.file_parsing import extract_text_from_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/simulations", tags=["simulations"])


def _get_simulation_or_404(simulation_id: str, project_id: str, db: Session) -> Simulation:
    simulation = db.get(Simulation, simulation_id)
    if not simulation or str(simulation.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return simulation


# ---------------------------------------------------------------------------
# Script upload
# ---------------------------------------------------------------------------

@router.post("/{simulation_id}/script", response_model=SimulationResponse)
def upload_idi_script(
    project_id: str,
    simulation_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload a script file (.txt or .docx) for an IDI simulation.
    Extracts interview questions via LLM and stores them in idi_script_text."""
    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = _get_simulation_or_404(simulation_id, project_id, db)

    if simulation.simulation_type not in ("idi_ai", "idi_manual"):
        raise HTTPException(status_code=422, detail="Script upload only applies to IDI simulations")

    save_dir = Path(settings.UPLOAD_DIR) / project_id / "scripts"
    raw_text = extract_text_from_upload(file, save_dir)

    # Use LLM to extract only the interview questions, ignoring headings and notes
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{
                "role": "user",
                "content": (
                    "Extract only the interview questions from the document below. "
                    "Return one question per line, with no numbering, no interviewer notes, "
                    "no section headings, no instructions, and no other text. "
                    "If something is not a question asked to the respondent, exclude it.\n\n"
                    f"DOCUMENT:\n{raw_text}"
                ),
            }],
            temperature=SURVEY_PARSE_TEMPERATURE,
        )
        script_text = response.choices[0].message.content or raw_text
    except Exception as e:
        logger.error(f"LLM question extraction failed, falling back to raw text: {e}")
        script_text = raw_text

    simulation.idi_script_text = script_text
    db.commit()
    db.refresh(simulation)

    # Kick off background task if this idi_ai simulation was waiting on its script
    if simulation.simulation_type == "idi_ai" and simulation.status == "pending":
        background_tasks.add_task(run_simulation, simulation_id=str(simulation.id), request_id=get_request_id())

    return simulation


# ---------------------------------------------------------------------------
# Manual IDI chat
# ---------------------------------------------------------------------------

@router.get("/{simulation_id}/messages", response_model=list[IDIMessageResponse])
def get_idi_messages(
    project_id: str,
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    _get_simulation_or_404(simulation_id, project_id, db)
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
    from app.services.prompts import idi_system_prompt
    from app.services.briefing_utils import combine_briefing_texts

    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = _get_simulation_or_404(simulation_id, project_id, db)

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

    # Build full conversation history
    history = db.execute(
        select(IDIMessage)
        .where(IDIMessage.simulation_id == simulation_id)
        .order_by(IDIMessage.created_at)
    ).scalars().all()

    briefing_text = combine_briefing_texts(simulation.briefings)
    system_prompt = idi_system_prompt(persona, briefing_text)

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

    client = get_openai_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=oai_messages,
        temperature=0.85,
    )
    answer = response.choices[0].message.content or ""

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


# ---------------------------------------------------------------------------
# End session / report generation
# ---------------------------------------------------------------------------

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
    simulation = _get_simulation_or_404(simulation_id, project_id, db)

    if simulation.simulation_type != "idi_manual":
        raise HTTPException(status_code=422, detail="Only manual IDI sessions can be ended this way")
    if simulation.status != "active":
        raise HTTPException(status_code=422, detail="Session is not active")

    simulation.status = "generating_report"
    db.commit()
    db.refresh(simulation)

    background_tasks.add_task(generate_idi_report_from_messages, simulation_id=simulation_id, request_id=get_request_id())
    return simulation
