from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.hashing import hash_password, verify_password
from app.database import get_db
from app.models.company import Company
from app.models.refresh_token import RefreshToken
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


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)


@router.patch("/password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for the currently logged-in user."""
    user = db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    user.hashed_password = hash_password(body.new_password)

    # Revoke all existing refresh tokens so other sessions are logged out
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at == None,  # noqa: E711
    ).update({"revoked_at": datetime.now(timezone.utc)})

    db.commit()


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
