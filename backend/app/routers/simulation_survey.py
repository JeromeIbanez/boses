"""
Survey simulation endpoints.
Handles survey file upload (parse to schema) and the /run confirmation step.
"""
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pathlib import Path
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.constants import SURVEY_PARSE_TEMPERATURE
from app.database import get_db
from app.models.simulation import Simulation
from app.routers.common import get_project_or_404 as _get_project_or_404
from app.schemas.simulation import SimulationResponse
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
# Survey file upload
# ---------------------------------------------------------------------------

@router.post("/{simulation_id}/survey", response_model=SimulationResponse)
def upload_survey_file(
    project_id: str,
    simulation_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload a survey form (.txt or .docx). AI parses it into structured questions.
    Returns the updated simulation with survey_schema populated for preview.
    Does NOT start the simulation — call /run to confirm and start."""
    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = _get_simulation_or_404(simulation_id, project_id, db)

    if simulation.simulation_type != "survey":
        raise HTTPException(status_code=422, detail="Survey upload only applies to survey simulations")

    save_dir = Path(settings.UPLOAD_DIR) / project_id / "surveys"
    raw_text = extract_text_from_upload(file, save_dir)

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{
                "role": "user",
                "content": (
                    "Parse the following survey document into a structured JSON object. "
                    "Return ONLY valid JSON with no markdown, no code blocks, no explanation — just the raw JSON object.\n\n"
                    "The JSON must have this exact shape:\n"
                    '{"questions": [...]}\n\n'
                    "Each question object must have:\n"
                    '- "id": string (q1, q2, q3, ...)\n'
                    '- "type": one of "likert", "multiple_choice", "open_ended"\n'
                    '- "text": the question text\n'
                    "For likert: also include \"scale\" (integer, default 5), \"low_label\" (string), \"high_label\" (string)\n"
                    "For multiple_choice: also include \"options\" (array of strings)\n"
                    "For open_ended: no extra fields needed\n\n"
                    "Infer the type from context: rating/agreement/likelihood scales → likert; "
                    "choose one/select → multiple_choice; free text → open_ended.\n\n"
                    f"SURVEY DOCUMENT:\n{raw_text}"
                ),
            }],
            temperature=SURVEY_PARSE_TEMPERATURE,
        )
        raw_json = response.choices[0].message.content or ""
        survey_schema = json.loads(raw_json)
    except Exception as e:
        logger.error(f"Survey parsing failed: {e}")
        raise HTTPException(status_code=422, detail="Could not parse survey questions from the uploaded file")

    simulation.survey_schema = survey_schema
    db.commit()
    db.refresh(simulation)
    return simulation


# ---------------------------------------------------------------------------
# Run (confirm + start)
# ---------------------------------------------------------------------------

@router.post("/{simulation_id}/run", response_model=SimulationResponse)
def run_survey_simulation(
    project_id: str,
    simulation_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Confirm and start a survey simulation after the user has previewed the parsed questions."""
    _get_project_or_404(project_id, db, current_user.company_id)
    simulation = _get_simulation_or_404(simulation_id, project_id, db)

    if simulation.simulation_type != "survey":
        raise HTTPException(status_code=422, detail="Run endpoint is only for survey simulations")
    if simulation.status != "pending":
        raise HTTPException(status_code=422, detail="Simulation is not in pending state")
    if not simulation.survey_schema:
        raise HTTPException(status_code=422, detail="Survey questions not uploaded yet")

    questions = (simulation.survey_schema or {}).get("questions", [])
    bad = [q["id"] for q in questions if q.get("type") == "multiple_choice" and not q.get("options")]
    if bad:
        raise HTTPException(
            status_code=422,
            detail=f"Multiple choice question(s) {', '.join(bad)} have no options. Please re-upload the survey or edit the questions."
        )

    background_tasks.add_task(run_simulation, simulation_id=str(simulation.id), request_id=get_request_id())
    db.refresh(simulation)
    return simulation
