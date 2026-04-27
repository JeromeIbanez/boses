"""
API Key management endpoints.
Allows companies to generate, list, and revoke API keys for MCP / programmatic access.
"""
import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.api_key import APIKey

router = APIRouter(prefix="/settings/api-keys", tags=["API Keys"])

_KEY_PREFIX = "boses_"
_KEY_BYTES = 32  # 256-bit entropy → 64-char hex string


def _generate_raw_key() -> str:
    """Generate a new random API key."""
    return _KEY_PREFIX + secrets.token_hex(_KEY_BYTES)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _display_prefix(raw_key: str) -> str:
    """Return the first 16 chars (prefix + 10 chars) for display."""
    return raw_key[:16]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class APIKeyCreate(BaseModel):
    name: str
    expires_at: Optional[datetime] = None  # ISO-8601 datetime; None means never expires


class APIKeyCreatedResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    key: str            # Full key — shown ONCE
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class APIKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    body: APIKeyCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a new API key for the current workspace. The full key is returned ONCE — store it securely."""
    raw_key = _generate_raw_key()
    prefix = _display_prefix(raw_key)
    key_hash = _hash_key(raw_key)

    api_key = APIKey(
        company_id=current_user.company_id,
        created_by_user_id=current_user.id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        expires_at=body.expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        key=raw_key,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
    )


@router.get("", response_model=list[APIKeyResponse])
def list_api_keys(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all active API keys for the current workspace (prefix only — full keys are never stored)."""
    keys = db.execute(
        select(APIKey)
        .where(APIKey.company_id == current_user.company_id, APIKey.is_active == True)  # noqa: E712
        .order_by(APIKey.created_at.desc())
    ).scalars().all()
    return keys


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke (deactivate) an API key. The key will immediately stop working."""
    key = db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.company_id == current_user.company_id,
        )
    ).scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = False
    db.commit()
