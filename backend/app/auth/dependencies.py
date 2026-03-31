import uuid
from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError
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
    )
