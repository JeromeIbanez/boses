"""Tests for app/auth/dependencies.py — _auth_from_cookie, _auth_from_api_key, get_current_user."""
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from app.auth.dependencies import (
    CurrentUser,
    _auth_from_api_key,
    _auth_from_cookie,
    get_current_user,
    require_boses_staff,
)
from app.auth.tokens import create_access_token
from app.config import settings


# ---------------------------------------------------------------------------
# _auth_from_cookie
# ---------------------------------------------------------------------------

def test_auth_from_cookie_valid_token_returns_current_user(mock_db, fake_user, user_id, company_id):
    token = create_access_token(user_id, company_id)
    mock_db.get.return_value = fake_user

    result = _auth_from_cookie(token, mock_db)

    assert isinstance(result, CurrentUser)
    assert result.id == user_id
    assert result.company_id == company_id
    assert result.email == "test@example.com"


def test_auth_from_cookie_expired_token_raises_401(mock_db):
    payload = {
        "sub": str(uuid.uuid4()),
        "company_id": str(uuid.uuid4()),
        "exp": datetime.utcnow() - timedelta(minutes=1),
        "type": "access",
    }
    expired = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(HTTPException) as exc:
        _auth_from_cookie(expired, mock_db)
    assert exc.value.status_code == 401


def test_auth_from_cookie_invalid_token_raises_401(mock_db):
    with pytest.raises(HTTPException) as exc:
        _auth_from_cookie("not-a-jwt", mock_db)
    assert exc.value.status_code == 401


def test_auth_from_cookie_user_not_found_raises_401(mock_db, user_id, company_id):
    token = create_access_token(user_id, company_id)
    mock_db.get.return_value = None  # user not found

    with pytest.raises(HTTPException) as exc:
        _auth_from_cookie(token, mock_db)
    assert exc.value.status_code == 401


def test_auth_from_cookie_inactive_user_raises_401(mock_db, fake_user, user_id, company_id):
    token = create_access_token(user_id, company_id)
    fake_user.is_active = False
    mock_db.get.return_value = fake_user

    with pytest.raises(HTTPException) as exc:
        _auth_from_cookie(token, mock_db)
    assert exc.value.status_code == 401


def test_auth_from_cookie_company_mismatch_raises_401(mock_db, fake_user, user_id, company_id):
    token = create_access_token(user_id, company_id)
    fake_user.company_id = uuid.uuid4()  # different company
    mock_db.get.return_value = fake_user

    with pytest.raises(HTTPException) as exc:
        _auth_from_cookie(token, mock_db)
    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# _auth_from_api_key
# ---------------------------------------------------------------------------

def test_auth_from_api_key_valid_returns_current_user(mock_db, fake_api_key, company_id, user_id):
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_api_key

    result = _auth_from_api_key("any-raw-key", mock_db)

    assert isinstance(result, CurrentUser)
    assert result.company_id == company_id
    assert result.id == user_id
    assert result.email == "api-key@boses.internal"
    assert result.role == "member"
    assert result.is_boses_staff is False


def test_auth_from_api_key_not_found_raises_401(mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(HTTPException) as exc:
        _auth_from_api_key("missing-key", mock_db)
    assert exc.value.status_code == 401


def test_auth_from_api_key_expired_raises_401(mock_db, fake_api_key):
    fake_api_key.is_expired = True
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_api_key

    with pytest.raises(HTTPException) as exc:
        _auth_from_api_key("expired-key", mock_db)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


def test_auth_from_api_key_updates_last_used_at(mock_db, fake_api_key):
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_api_key

    _auth_from_api_key("good-key", mock_db)

    assert fake_api_key.last_used_at is not None
    mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

def test_get_current_user_prefers_cookie_when_both_present(mock_db, fake_user, user_id, company_id):
    token = create_access_token(user_id, company_id)
    mock_db.get.return_value = fake_user

    # If cookie is preferred, _auth_from_api_key should NOT be called.
    # We verify by leaving execute unconfigured — if api-key path were taken,
    # MagicMock would return a truthy object and test_get_current_user_falls_back_to_api_key
    # behavior would fire. Instead we assert the returned user matches cookie path.
    result = get_current_user(access_token=token, x_api_key="some-key", db=mock_db)
    assert result.id == user_id
    assert result.email == "test@example.com"


def test_get_current_user_falls_back_to_api_key(mock_db, fake_api_key, company_id, user_id):
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_api_key

    result = get_current_user(access_token=None, x_api_key="some-key", db=mock_db)
    assert result.company_id == company_id
    assert result.email == "api-key@boses.internal"


def test_get_current_user_no_credentials_raises_401(mock_db):
    with pytest.raises(HTTPException) as exc:
        get_current_user(access_token=None, x_api_key=None, db=mock_db)
    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# require_boses_staff
# ---------------------------------------------------------------------------

def test_require_boses_staff_allows_staff_user(staff_user):
    result = require_boses_staff(current_user=staff_user)
    assert result is staff_user


def test_require_boses_staff_rejects_non_staff(current_user):
    with pytest.raises(HTTPException) as exc:
        require_boses_staff(current_user=current_user)
    assert exc.value.status_code == 403
