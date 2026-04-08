"""Shared helpers for route handlers."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import Project


def get_project_or_404(project_id: str, db: Session, company_id) -> Project:
    project = db.get(Project, project_id)
    if not project or project.company_id != company_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
