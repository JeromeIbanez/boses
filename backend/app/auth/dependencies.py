import hashlib
import uuid
from dataclasses import dataclass

from fastapi import Cookie, Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.tokens import decode_access_token
from app.database import get_db
from app.models.user import User


@dataclass
class CurrentUser:
    id: uuid.UUID
    company_id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    is_boses_staff: bool


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )

    if not access_token:
        raise credentials_exception

    try:
        payload = decode_access_token(access_token)
        user_id = uuid.UUID(payload["sub"])
        company_id = uuid.UUID(payload["company_id"])
    except (JWTError, KeyError, ValueError):
        raise credentials_exception

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise credentials_exception

    # Sanity check — company_id in token matches DB
    if user.company_id != company_id:
        raise credentials_exception

    return CurrentUser(
        id=user.id,
        company_id=user.company_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_boses_staff=user.is_boses_staff,
    )


def require_boses_staff(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current_user.is_boses_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Boses staff access required",
        )
    return current_user


def get_current_user_from_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """
    Authenticate via X-API-Key header.
    Returns the same CurrentUser dataclass as cookie auth, scoped to the key's company.
    Used by the MCP server and any programmatic clients.
    """
    from app.models.api_key import APIKey
    from datetime import datetime

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )

    if not x_api_key:
        raise credentials_exception

    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()

    api_key = db.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,  # noqa: E712
        )
    ).scalar_one_or_none()

    if not api_key:
        raise credentials_exception

    # Update last_used_at (best-effort, don't fail the request if this errors)
    try:
        api_key.last_used_at = datetime.utcnow()
        db.commit()
    except Exception:
        db.rollback()

    # Return a CurrentUser scoped to this key's company.
    # We use a sentinel UUID for the user id since API keys are company-scoped, not user-scoped.
    return CurrentUser(
        id=api_key.created_by_user_id or uuid.UUID(int=0),
        company_id=api_key.company_id,
        email="api-key@boses.internal",
        full_name=f"API Key: {api_key.name}",
        role="member",
        is_boses_staff=False,
    )
