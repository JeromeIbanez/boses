"""
Utilities for extracting plain text from uploaded files (.txt / .docx).
Shared by the IDI script upload and survey file upload endpoints.
"""
import logging
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".txt", ".docx"}


def extract_text_from_upload(file: UploadFile, save_dir: Path) -> str:
    """
    Save an uploaded file to save_dir and return its plain-text content.
    Supports .txt and .docx. Raises HTTPException on unsupported type or read failure.
    """
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Only {', '.join(ALLOWED_EXTENSIONS)} files are supported",
        )

    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{uuid.uuid4().hex}_{filename}"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    if ext == ".txt":
        return save_path.read_text(errors="replace")

    # .docx
    try:
        import docx
        doc = docx.Document(str(save_path))
        return "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        logger.error(f"Failed to read .docx file '{filename}': {e}")
        raise HTTPException(status_code=422, detail="Could not read .docx file")
