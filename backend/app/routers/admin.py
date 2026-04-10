import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_boses_staff
from app.auth.tokens import hash_token
from app.database import get_db
from app.models.invite_token import InviteToken
from app.models.user import User
from app.config import settings
from app.limiter import limiter
from app.services.email_notifier import send_invite_email

router = APIRouter(prefix="/admin", tags=["admin"])

INVITE_EXPIRE_DAYS = 7


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateInviteRequest(BaseModel):
    email: EmailStr


class InviteResponse(BaseModel):
    id: uuid.UUID
    email: str
    status: str  # "pending" | "used" | "expired"
    invite_url: Optional[str] = None  # Only present in the creation response
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InviteListResponse(BaseModel):
    items: list[InviteResponse]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _invite_status(invite: InviteToken) -> str:
    if invite.used_at is not None:
        return "used"
    if invite.expires_at < datetime.now(timezone.utc):
        return "expired"
    return "pending"


def _to_response(invite: InviteToken) -> InviteResponse:
    """Convert an invite to a response. invite_url is NOT set — raw token is not recoverable from the hash."""
    return InviteResponse(
        id=invite.id,
        email=invite.email,
        status=_invite_status(invite),
        invite_url=None,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        used_at=invite.used_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    body: CreateInviteRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_boses_staff),
):
    email_lower = body.email.lower()

    # Check if already a registered user
    if db.query(User).filter(User.email == email_lower).first():
        raise HTTPException(status_code=400, detail=f"{email_lower} already has an account.")

    # Check for an existing pending invite to the same email
    existing = (
        db.query(InviteToken)
        .filter(InviteToken.email == email_lower, InviteToken.used_at == None)  # noqa: E711
        .first()
    )
    if existing and existing.expires_at > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail=f"A pending invite already exists for {email_lower}. Revoke it first or wait for it to expire.",
        )

    # Generate token — store only the hash, return raw once
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)

    invite = InviteToken(
        token=token_hash,
        email=email_lower,
        created_by=current_user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRE_DAYS),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    invite_url = f"{settings.FRONTEND_URL}/signup?token={raw_token}"
    try:
        send_invite_email(email_lower, invite_url)
    except Exception:
        # Email failure does not roll back the token — staff can copy the URL manually
        pass

    response = _to_response(invite)
    response.invite_url = invite_url  # Only time the raw URL is returned
    return response


@router.get("/invites", response_model=InviteListResponse)
def list_invites(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_boses_staff),
):
    invites = db.query(InviteToken).order_by(InviteToken.created_at.desc()).all()
    return InviteListResponse(
        items=[_to_response(i) for i in invites],
        total=len(invites),
    )


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(
    invite_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_boses_staff),
):
    invite = db.get(InviteToken, invite_id)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.used_at is not None:
        raise HTTPException(status_code=400, detail="Cannot revoke a used invite")
    invite.expires_at = datetime.now(timezone.utc)
    db.commit()
