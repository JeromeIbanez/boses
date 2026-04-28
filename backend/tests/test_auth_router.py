"""Tests for app/routers/auth.py — login, logout, /me, refresh, forgot/reset password, invite."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.hashing import hash_password
from app.routers.auth import _slugify


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_client(mock_db):
    """TestClient with only get_db overridden (auth routes are public)."""
    from app.main import app
    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    return client


def _auth_client_with_auth(mock_db, current_user):
    """TestClient with get_db + get_current_user overridden (for /me)."""
    from app.main import app
    from app.database import get_db
    from app.auth.dependencies import get_current_user
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def _fake_company():
    c = MagicMock()
    c.id = uuid.uuid4()
    c.name = "Test Co"
    c.slug = "test-co"
    c.slack_webhook_url = None
    c.plan = "free"
    c.simulations_used = 0
    c.billing_period_ends_at = None
    c.created_at = datetime.now(timezone.utc)
    return c


def _fake_full_user(user_id=None, company_id=None, password="password123"):
    """Build a fake User ORM object with all fields UserResponse.model_validate needs."""
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.company_id = company_id or uuid.uuid4()
    u.email = "test@example.com"
    u.full_name = "Test User"
    u.role = "owner"
    u.is_active = True
    u.is_boses_staff = False
    u.created_at = datetime.now(timezone.utc)
    u.hashed_password = hash_password(password)
    u.password_reset_token = None
    u.password_reset_token_expiry = None
    u.company = _fake_company()
    return u


def _fake_refresh_token(user_id, valid=True):
    rt = MagicMock()
    rt.user_id = user_id
    rt.is_valid = valid
    rt.revoked_at = None
    return rt


# ---------------------------------------------------------------------------
# Pure-function tests — _slugify
# ---------------------------------------------------------------------------

def test_slugify_basic():
    assert _slugify("Hello World") == "hello-world"


def test_slugify_strips_special_chars():
    assert _slugify("Boses! Co., Ltd.") == "boses-co-ltd"


def test_slugify_leading_trailing_hyphens():
    assert not _slugify("---foo---").startswith("-")
    assert not _slugify("---foo---").endswith("-")


def test_slugify_empty_string_returns_company():
    assert _slugify("") == "company"
    assert _slugify("!!!") == "company"


def test_slugify_truncates_at_100():
    long = "a" * 150
    assert len(_slugify(long)) == 100


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------

def test_login_valid_credentials_returns_200(mock_db):
    user = _fake_full_user()
    mock_db.query.return_value.filter.return_value.first.return_value = user

    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "password123"})

    assert r.status_code == 200
    assert r.json()["user"]["email"] == "test@example.com"
    mock_db.commit.assert_called()


def test_login_wrong_password_returns_401(mock_db):
    user = _fake_full_user(password="correct-pass")
    mock_db.query.return_value.filter.return_value.first.return_value = user

    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "wrong-pass"})

    assert r.status_code == 401
    assert "Invalid" in r.json()["detail"]


def test_login_user_not_found_returns_401(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "password123"})

    assert r.status_code == 401


def test_login_inactive_user_returns_403(mock_db):
    user = _fake_full_user()
    user.is_active = False
    mock_db.query.return_value.filter.return_value.first.return_value = user

    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "password123"})

    assert r.status_code == 403
    assert "deactivated" in r.json()["detail"].lower()


def test_login_invalid_request_body_returns_422(mock_db):
    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/login", json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------

def test_logout_no_cookie_returns_204(mock_db):
    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/logout")
    assert r.status_code == 204


def test_logout_with_refresh_cookie_revokes_token(mock_db):
    rt = _fake_refresh_token(uuid.uuid4())
    mock_db.query.return_value.filter.return_value.first.return_value = rt

    with _auth_client(mock_db) as c:
        c.cookies.set("refresh_token", "some-raw-token")
        r = c.post("/api/v1/auth/logout")

    assert r.status_code == 204
    assert rt.revoked_at is not None
    mock_db.commit.assert_called()


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------

def test_get_me_returns_user(mock_db, current_user):
    user = _fake_full_user(user_id=current_user.id, company_id=current_user.company_id)
    mock_db.get.return_value = user

    with _auth_client_with_auth(mock_db, current_user) as c:
        r = c.get("/api/v1/auth/me")

    assert r.status_code == 200
    assert r.json()["user"]["email"] == "test@example.com"
    from app.main import app
    app.dependency_overrides.clear()


def test_get_me_user_not_found_returns_404(mock_db, current_user):
    mock_db.get.return_value = None

    with _auth_client_with_auth(mock_db, current_user) as c:
        r = c.get("/api/v1/auth/me")

    assert r.status_code == 404
    from app.main import app
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------

def test_refresh_no_cookie_returns_401(mock_db):
    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/refresh")
    assert r.status_code == 401
    assert "No refresh token" in r.json()["detail"]


def test_refresh_invalid_token_returns_401(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with _auth_client(mock_db) as c:
        c.cookies.set("refresh_token", "invalid-token")
        r = c.post("/api/v1/auth/refresh")

    assert r.status_code == 401


def test_refresh_revoked_token_returns_401(mock_db):
    rt = _fake_refresh_token(uuid.uuid4(), valid=False)
    mock_db.query.return_value.filter.return_value.first.return_value = rt

    with _auth_client(mock_db) as c:
        c.cookies.set("refresh_token", "revoked-token")
        r = c.post("/api/v1/auth/refresh")

    assert r.status_code == 401


def test_refresh_valid_token_returns_200(mock_db):
    user_id = uuid.uuid4()
    rt = _fake_refresh_token(user_id, valid=True)
    user = _fake_full_user(user_id=user_id)
    mock_db.query.return_value.filter.return_value.first.return_value = rt
    mock_db.get.return_value = user

    with _auth_client(mock_db) as c:
        c.cookies.set("refresh_token", "valid-token")
        r = c.post("/api/v1/auth/refresh")

    assert r.status_code == 200
    assert r.json()["user"]["email"] == "test@example.com"
    assert rt.revoked_at is not None  # old token rotated out


# ---------------------------------------------------------------------------
# POST /api/v1/auth/forgot-password
# ---------------------------------------------------------------------------

def test_forgot_password_always_returns_204(mock_db):
    user = _fake_full_user()
    mock_db.query.return_value.filter.return_value.first.return_value = user

    with patch("app.services.email_notifier.send_password_reset_email", side_effect=Exception("no email")):
        with _auth_client(mock_db) as c:
            r = c.post("/api/v1/auth/forgot-password", json={"email": "test@example.com"})

    assert r.status_code == 204


def test_forgot_password_nonexistent_email_still_204(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})

    assert r.status_code == 204


# ---------------------------------------------------------------------------
# POST /api/v1/auth/reset-password
# ---------------------------------------------------------------------------

def test_reset_password_valid_token_returns_204(mock_db):
    user = _fake_full_user()
    user.password_reset_token = "some-hash"
    user.password_reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_db.query.return_value.filter.return_value.first.return_value = user
    mock_db.query.return_value.filter.return_value.update.return_value = 1

    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/reset-password", json={"token": "raw-token", "new_password": "NewPass123!"})

    assert r.status_code == 204
    assert user.password_reset_token is None


def test_reset_password_invalid_token_returns_400(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/reset-password", json={"token": "bad-token", "new_password": "NewPass123!"})

    assert r.status_code == 400
    assert "invalid" in r.json()["detail"].lower()


def test_reset_password_expired_token_returns_400(mock_db):
    user = _fake_full_user()
    user.password_reset_token = "some-hash"
    user.password_reset_token_expiry = datetime.now(timezone.utc) - timedelta(hours=1)
    mock_db.query.return_value.filter.return_value.first.return_value = user

    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/reset-password", json={"token": "expired-token", "new_password": "NewPass123!"})

    assert r.status_code == 400


def test_reset_password_too_short_returns_400(mock_db):
    with _auth_client(mock_db) as c:
        r = c.post("/api/v1/auth/reset-password", json={"token": "any", "new_password": "short"})
    # Pydantic min_length=8 catches this first
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/auth/invite
# ---------------------------------------------------------------------------

def test_validate_invite_valid_returns_email(mock_db):
    invite = MagicMock()
    invite.used_at = None
    invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    invite.email = "invited@example.com"
    mock_db.query.return_value.filter.return_value.first.return_value = invite

    with _auth_client(mock_db) as c:
        r = c.get("/api/v1/auth/invite?token=valid-token")

    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["email"] == "invited@example.com"


def test_validate_invite_not_found_returns_invalid(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with _auth_client(mock_db) as c:
        r = c.get("/api/v1/auth/invite?token=bad-token")

    assert r.status_code == 200
    assert r.json()["valid"] is False


def test_validate_invite_already_used_returns_invalid(mock_db):
    invite = MagicMock()
    invite.used_at = datetime.now(timezone.utc)
    invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_db.query.return_value.filter.return_value.first.return_value = invite

    with _auth_client(mock_db) as c:
        r = c.get("/api/v1/auth/invite?token=used-token")

    assert r.json()["valid"] is False


def test_validate_invite_expired_returns_invalid(mock_db):
    invite = MagicMock()
    invite.used_at = None
    invite.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    mock_db.query.return_value.filter.return_value.first.return_value = invite

    with _auth_client(mock_db) as c:
        r = c.get("/api/v1/auth/invite?token=expired-token")

    assert r.json()["valid"] is False
