from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import CompanyResponse

router = APIRouter(prefix="/settings", tags=["Settings"])


class CompanySettingsUpdate(BaseModel):
    slack_webhook_url: Optional[str] = None

    @field_validator("slack_webhook_url")
    @classmethod
    def validate_slack_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not v.startswith("https://hooks.slack.com/"):
            raise ValueError("Must be a valid Slack incoming webhook URL (https://hooks.slack.com/...)")
        return v


@router.get("/company", response_model=CompanyResponse)
def get_company_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return current_user.company


@router.patch("/company", response_model=CompanyResponse)
def update_company_settings(
    body: CompanySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = current_user.company
    if body.slack_webhook_url is not None or "slack_webhook_url" in body.model_fields_set:
        company.slack_webhook_url = body.slack_webhook_url
    db.commit()
    db.refresh(company)
    return company
