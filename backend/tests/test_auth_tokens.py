"""Pure-function tests for app/auth/tokens.py."""
import uuid
from datetime import datetime, timedelta

import pytest
from jose import JWTError, jwt

from app.auth.tokens import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_token,
)
from app.config import settings


def test_create_access_token_returns_string():
    token = create_access_token(uuid.uuid4(), uuid.uuid4())
    assert isinstance(token, str)
    assert token.count(".") == 2  # JWT has three dot-separated segments


def test_create_access_token_decode_roundtrip():
    user_id = uuid.uuid4()
    company_id = uuid.uuid4()
    token = create_access_token(user_id, company_id)
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["company_id"] == str(company_id)
    assert payload["type"] == "access"


def test_decode_access_token_wrong_type_raises():
    payload = {
        "sub": str(uuid.uuid4()),
        "company_id": str(uuid.uuid4()),
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "type": "refresh",
    }
    bad_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(JWTError):
        decode_access_token(bad_token)


def test_decode_access_token_expired_raises():
    payload = {
        "sub": str(uuid.uuid4()),
        "company_id": str(uuid.uuid4()),
        "exp": datetime.utcnow() - timedelta(minutes=1),
        "type": "access",
    }
    expired = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(JWTError):
        decode_access_token(expired)


def test_decode_access_token_wrong_secret_raises():
    payload = {
        "sub": str(uuid.uuid4()),
        "company_id": str(uuid.uuid4()),
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "type": "access",
    }
    bad = jwt.encode(payload, "wrong-secret", algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(JWTError):
        decode_access_token(bad)


def test_create_refresh_token_returns_raw_and_hash_tuple():
    raw, h = create_refresh_token()
    assert isinstance(raw, str) and len(raw) > 32
    assert isinstance(h, str) and len(h) == 64  # SHA-256 hex
    assert raw != h
    assert hash_token(raw) == h


def test_hash_token_deterministic():
    assert hash_token("hello") == hash_token("hello")


def test_hash_token_different_inputs_differ():
    assert hash_token("a") != hash_token("b")
