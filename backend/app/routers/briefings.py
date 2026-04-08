import mimetypes
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.database import get_db
from app.models.briefing import Briefing
from app.models.project import Project
from app.routers.common import get_project_or_404 as _get_project_or_404
from app.schemas.briefing import BriefingResponse
from app.services.briefing_extractor import extract_text, summarize_if_long

router = APIRouter(prefix="/projects/{project_id}/briefings", tags=["briefings"])



@router.get("", response_model=list[BriefingResponse])
def list_briefings(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
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
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)

    filename = Path(file.filename or "upload").name
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    _IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "gif"}
    _VIDEO_EXTS = {"mp4", "mov", "avi", "mkv", "webm"}
    _AUDIO_EXTS = {"mp3", "wav", "m4a", "aac", "ogg", "flac"}
    if ext == "pdf":
        file_type = "pdf"
    elif ext in _IMAGE_EXTS:
        file_type = "image"
    elif ext in _VIDEO_EXTS:
        file_type = "video"
    elif ext in _AUDIO_EXTS:
        file_type = "audio"
    else:
        file_type = "text"

    save_dir = os.path.join(settings.UPLOAD_DIR, project_id)
    os.makedirs(save_dir, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    save_path = os.path.join(save_dir, unique_name)

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    extracted = extract_text(save_path, file_type)
    summary = summarize_if_long(extracted, title) if extracted else None

    briefing = Briefing(
        project_id=project_id,
        title=title,
        description=description,
        file_name=filename,
        file_path=save_path,
        file_type=file_type,
        extracted_text=extracted,
        summary_text=summary,
    )
    db.add(briefing)
    db.commit()
    db.refresh(briefing)
    return briefing


@router.get("/{briefing_id}", response_model=BriefingResponse)
def get_briefing(
    project_id: str,
    briefing_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    briefing = db.get(Briefing, briefing_id)
    if not briefing or str(briefing.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return briefing


@router.get("/{briefing_id}/file")
def get_briefing_file(
    project_id: str,
    briefing_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    briefing = db.get(Briefing, briefing_id)
    if not briefing or str(briefing.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Briefing not found")
    if not os.path.exists(briefing.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    mime, _ = mimetypes.guess_type(briefing.file_name)
    return FileResponse(briefing.file_path, media_type=mime or "application/octet-stream", filename=briefing.file_name)


@router.patch("/{briefing_id}", response_model=BriefingResponse)
def update_briefing(
    project_id: str,
    briefing_id: str,
    title: str = Body(...),
    description: str | None = Body(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    briefing = db.get(Briefing, briefing_id)
    if not briefing or str(briefing.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Briefing not found")
    briefing.title = title
    briefing.description = description
    db.commit()
    db.refresh(briefing)
    return briefing


@router.delete("/{briefing_id}", status_code=204)
def delete_briefing(
    project_id: str,
    briefing_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _get_project_or_404(project_id, db, current_user.company_id)
    briefing = db.get(Briefing, briefing_id)
    if not briefing or str(briefing.project_id) != project_id:
        raise HTTPException(status_code=404, detail="Briefing not found")
    if os.path.exists(briefing.file_path):
        os.remove(briefing.file_path)
    db.delete(briefing)
    db.commit()
