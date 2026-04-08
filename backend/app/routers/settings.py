from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.company import Company
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


def _get_company_or_404(company_id, db: Session) -> Company:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.get("/company", response_model=CompanyResponse)
def get_company_settings(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_company_or_404(current_user.company_id, db)


@router.patch("/company", response_model=CompanyResponse)
def update_company_settings(
    body: CompanySettingsUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = _get_company_or_404(current_user.company_id, db)
    if "slack_webhook_url" in body.model_fields_set:
        company.slack_webhook_url = body.slack_webhook_url
    db.commit()
    db.refresh(company)
    return company
