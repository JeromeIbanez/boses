import os
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.briefing import Briefing
from app.models.project import Project
from app.schemas.briefing import BriefingResponse
from app.services.briefing_extractor import extract_text

router = APIRouter(prefix="/projects/{project_id}/briefings", tags=["briefings"])


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=list[BriefingResponse])
def list_briefings(project_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    return db.execute(
        select(Briefing)
        .where(Briefing.project_id == project_id)
        .order_by(Briefing.created_at.desc())
    ).scalars().all()


@router.post("", response_model=BriefingResponse, status_code=201)
async def upload_briefing(
    project_id: str,
    title: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    _get_project_or_404(project_id, db)

    # Determine file type
    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    file_type = "pdf" if ext == "pdf" else ("image" if ext in ("png", "jpg", "jpeg", "webp", "gif") else "text")

    # Save to disk
    save_dir = os.path.join(settings.UPLOAD_DIR, project_id)
    os.makedirs(save_dir, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    save_path = os.path.join(save_dir, unique_name)

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text
    extracted = extract_text(save_path, file_type)

    briefing = Briefing(
        project_id=project_id,
        title=title,
        description=description,
        file_name=filename,
        file_path=save_path,
        file_type=file_type,
        extracted_text=extracted,
    )
    db.add(briefing)
    db.commit()
    db.refresh(briefing)
    return briefing


@router.get("/{briefing_id}", response_model=BriefingResponse)
def get_briefing(project_id: str, briefing_id: str, db: Session = Depends(get_db)):
    briefing = db.get(Briefing, briefing_id)
    if not briefing or str(briefing.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return briefing


@router.delete("/{briefing_id}", status_code=204)
def delete_briefing(project_id: str, briefing_id: str, db: Session = Depends(get_db)):
    briefing = db.get(Briefing, briefing_id)
    if not briefing or str(briefing.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Briefing not found")
    if os.path.exists(briefing.file_path):
        os.remove(briefing.file_path)
    db.delete(briefing)
    db.commit()
