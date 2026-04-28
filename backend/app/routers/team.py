"""
Team management endpoints — invite colleagues to the workspace.
All routes require the caller to be an owner or admin.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.limiter import limiter
from app.models.company_invite import CompanyInvite
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/settings/team", tags=["Team"])

_INVITE_EXPIRE_DAYS = 7


def _require_owner(current_user: CurrentUser) -> None:
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners and admins can manage team members.",
        )


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MemberResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InviteResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    expires_at: datetime
    created_at: datetime
    invited_by_name: str | None = None

    model_config = {"from_attributes": True}


class TeamResponse(BaseModel):
    members: list[MemberResponse]
    pending_invites: list[InviteResponse]


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"


# ---------------------------------------------------------------------------
# GET /settings/team
# ---------------------------------------------------------------------------

@router.get("", response_model=TeamResponse)
def get_team(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all active members and pending invites for the workspace."""
    members = db.execute(
        select(User)
        .where(User.company_id == current_user.company_id, User.is_active == True)  # noqa: E712
        .order_by(User.created_at)
    ).scalars().all()

    now = datetime.now(timezone.utc)
    raw_invites = db.execute(
        select(CompanyInvite)
        .where(
            CompanyInvite.company_id == current_user.company_id,
            CompanyInvite.accepted_at == None,  # noqa: E711
            CompanyInvite.expires_at > now,
        )
        .order_by(CompanyInvite.created_at.desc())
    ).scalars().all()

    invite_responses = []
    for inv in raw_invites:
        invited_by_name = None
        if inv.invited_by_user_id:
            inviter = db.get(User, inv.invited_by_user_id)
            invited_by_name = inviter.full_name or inviter.email if inviter else None
        invite_responses.append(InviteResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
            invited_by_name=invited_by_name,
        ))

    return TeamResponse(
        members=[MemberResponse.model_validate(m) for m in members],
        pending_invites=invite_responses,
    )


# ---------------------------------------------------------------------------
# POST /settings/team/invite
# ---------------------------------------------------------------------------

@router.post("/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
def send_invite(
    request: Request,
    body: InviteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a workspace invite email to a colleague."""
    _require_owner(current_user)

    # --- Seat quota gate ---
    from app.models.company import Company
    from app.services.stripe_service import check_seat_quota_or_402
    company = db.get(Company, current_user.company_id)
    check_seat_quota_or_402(company, db, inviter_email=current_user.email)

    email_lower = body.email.lower()

    # Already a member?
    existing = db.execute(
        select(User).where(
            User.email == email_lower,
            User.company_id == current_user.company_id,
            User.is_active == True,  # noqa: E712
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="This person is already a member of your workspace.")

    # Already has a Boses account in a different workspace?
    other_account = db.execute(
        select(User).where(User.email == email_lower, User.is_active == True)  # noqa: E712
    ).scalar_one_or_none()
    if other_account:
        raise HTTPException(
            status_code=400,
            detail="This email already has a Boses account. Ask them to contact support to transfer workspaces.",
        )

    # Cancel any previously pending invite to the same email in this company
    now = datetime.now(timezone.utc)
    db.execute(
        select(CompanyInvite).where(
            CompanyInvite.company_id == current_user.company_id,
            CompanyInvite.email == email_lower,
            CompanyInvite.accepted_at == None,  # noqa: E711
        )
    )
    old_invites = db.execute(
        select(CompanyInvite).where(
            CompanyInvite.company_id == current_user.company_id,
            CompanyInvite.email == email_lower,
            CompanyInvite.accepted_at == None,  # noqa: E711
        )
    ).scalars().all()
    for old in old_invites:
        # Expire them immediately so the new one is the only valid one
        old.expires_at = now

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    invite = CompanyInvite(
        company_id=current_user.company_id,
        invited_by_user_id=current_user.id if current_user.id != uuid.UUID(int=0) else None,
        email=email_lower,
        token_hash=token_hash,
        role=body.role if body.role in ("member", "admin") else "member",
        expires_at=now + timedelta(days=_INVITE_EXPIRE_DAYS),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    # Send email (fire-and-forget)
    from app.models.company import Company
    company = db.get(Company, current_user.company_id)
    inviter = db.get(User, current_user.id) if current_user.id != uuid.UUID(int=0) else None
    invite_url = f"{settings.FRONTEND_URL}/invite/{raw_token}"

    try:
        from app.services.email_notifier import send_workspace_invite_email
        send_workspace_invite_email(
            to_email=email_lower,
            invite_url=invite_url,
            company_name=company.name if company else "Boses",
            inviter_name=inviter.full_name or inviter.email if inviter else "Your colleague",
        )
    except Exception:
        pass  # Email failure doesn't block the invite creation

    inviter_name = inviter.full_name or inviter.email if inviter else None
    return InviteResponse(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
        invited_by_name=inviter_name,
    )


# ---------------------------------------------------------------------------
# DELETE /settings/team/invites/{invite_id}
# ---------------------------------------------------------------------------

@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_invite(
    invite_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a pending invite."""
    _require_owner(current_user)
    invite = db.execute(
        select(CompanyInvite).where(
            CompanyInvite.id == invite_id,
            CompanyInvite.company_id == current_user.company_id,
        )
    ).scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found.")
    # Expire it immediately
    invite.expires_at = datetime.now(timezone.utc)
    db.commit()


# ---------------------------------------------------------------------------
# DELETE /settings/team/members/{user_id}
# ---------------------------------------------------------------------------

@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deactivate a team member (removes their access)."""
    _require_owner(current_user)

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself.")

    member = db.execute(
        select(User).where(
            User.id == user_id,
            User.company_id == current_user.company_id,
        )
    ).scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    if member.role == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the workspace owner.")

    member.is_active = False
    db.commit()
