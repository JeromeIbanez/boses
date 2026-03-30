import re
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.hashing import hash_password, verify_password
from app.auth.tokens import create_access_token, create_refresh_token, hash_token
from app.config import settings
from app.database import get_db
from app.models.company import Company
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:100] or "company"


def _make_unique_slug(db: Session, base: str) -> str:
    slug = base
    counter = 1
    while db.query(Company).filter(Company.slug == slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _build_auth_response(response: Response, user: User) -> AuthResponse:
    access_token = create_access_token(user.id, user.company_id)
    raw_refresh, refresh_hash = create_refresh_token()
    set_auth_cookies(response, access_token, raw_refresh)
    return AuthResponse(user=UserResponse.model_validate(user))


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, response: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Create company
    base_slug = _slugify(body.company_name)
    slug = _make_unique_slug(db, base_slug)
    company = Company(name=body.company_name, slug=slug)
    db.add(company)
    db.flush()  # get company.id

    # Create owner user
    user = User(
        company_id=company.id,
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role="owner",
    )
    db.add(user)
    db.flush()

    # Store refresh token
    raw_refresh, refresh_hash = create_refresh_token()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(user.id, user.company_id)
    set_auth_cookies(response, access_token, raw_refresh)
    return AuthResponse(user=UserResponse.model_validate(user))


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    raw_refresh, refresh_hash = create_refresh_token()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    db.commit()

    access_token = create_access_token(user.id, user.company_id)
    set_auth_cookies(response, access_token, raw_refresh)
    return AuthResponse(user=UserResponse.model_validate(user))


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if refresh_token:
        token_hash = hash_token(refresh_token)
        rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if rt:
            rt.revoked_at = datetime.utcnow()
            db.commit()
    clear_auth_cookies(response)


# ---------------------------------------------------------------------------
# Get current user
# ---------------------------------------------------------------------------

@router.get("/me", response_model=AuthResponse)
def get_me(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return AuthResponse(user=UserResponse.model_validate(user))


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=AuthResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    token_hash = hash_token(refresh_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if not rt or not rt.is_valid:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.get(User, rt.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate: revoke old, issue new
    rt.revoked_at = datetime.utcnow()
    raw_refresh, refresh_hash = create_refresh_token()
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_rt)
    db.commit()

    access_token = create_access_token(user.id, user.company_id)
    set_auth_cookies(response, access_token, raw_refresh)
    return AuthResponse(user=UserResponse.model_validate(user))


# ---------------------------------------------------------------------------
# Forgot / Reset password
# ---------------------------------------------------------------------------

@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    # Always return 204 — don't leak whether email exists
    if not user:
        return

    token = secrets.token_urlsafe(32)
    user.password_reset_token = token
    user.password_reset_token_expiry = datetime.utcnow() + timedelta(hours=2)
    db.commit()

    # TODO: send email with reset link
    # reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    # For now, token is stored but email sending is a future step


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.password_reset_token == body.token).first()

    if (
        not user
        or not user.password_reset_token_expiry
        or user.password_reset_token_expiry < datetime.utcnow()
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user.hashed_password = hash_password(body.new_password)
    user.password_reset_token = None
    user.password_reset_token_expiry = None

    # Revoke all refresh tokens on password change
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at == None,  # noqa: E711
    ).update({"revoked_at": datetime.utcnow()})

    db.commit()
