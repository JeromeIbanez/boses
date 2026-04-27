"""Shared pytest fixtures.

This file MUST set environment variables before any `app.*` import,
because `app/config.py` raises RuntimeError at import time when
JWT_SECRET is left at the default placeholder.
"""
import os

os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://unused:unused@localhost/unused")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake")
os.environ.setdefault("UPLOAD_DIR", "/tmp/boses-test-uploads")
os.environ.setdefault("ENVIRONMENT", "development")

# Make sure the upload dir exists so StaticFiles mount in app/main.py succeeds
os.makedirs(os.path.join("/tmp/boses-test-uploads", "avatars"), exist_ok=True)

# Stub `magic` (libmagic native lib may be unavailable in test env). It's used
# only by file-upload routes which our tests don't exercise.
import sys
import types as _types
if "magic" not in sys.modules:
    _stub = _types.ModuleType("magic")
    _stub.from_buffer = lambda *a, **kw: "application/octet-stream"
    _stub.from_file = lambda *a, **kw: "application/octet-stream"
    sys.modules["magic"] = _stub

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db() -> MagicMock:
    """A MagicMock that quacks like a SQLAlchemy Session.

    Tests configure the chain (e.g. .execute().scalars().all()) per-test.
    """
    db = MagicMock(spec=Session)
    return db


# ---------------------------------------------------------------------------
# Identity fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def company_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def project_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def persona_group_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def briefing_id() -> uuid.UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Auth fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_user(user_id, company_id):
    """A MagicMock standing in for a User ORM instance."""
    user = MagicMock()
    user.id = user_id
    user.company_id = company_id
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.role = "owner"
    user.is_active = True
    user.is_boses_staff = False
    return user


@pytest.fixture
def current_user(user_id, company_id):
    """A real CurrentUser dataclass — bypasses auth in router tests."""
    from app.auth.dependencies import CurrentUser
    return CurrentUser(
        id=user_id,
        company_id=company_id,
        email="test@example.com",
        full_name="Test User",
        role="owner",
        is_boses_staff=False,
    )


@pytest.fixture
def staff_user(user_id, company_id):
    from app.auth.dependencies import CurrentUser
    return CurrentUser(
        id=user_id,
        company_id=company_id,
        email="staff@boses.internal",
        full_name="Staff User",
        role="owner",
        is_boses_staff=True,
    )


@pytest.fixture
def access_token(user_id, company_id) -> str:
    from app.auth.tokens import create_access_token
    return create_access_token(user_id, company_id)


@pytest.fixture
def fake_api_key(company_id, user_id):
    """A MagicMock standing in for an APIKey ORM instance (active, not expired)."""
    api_key = MagicMock()
    api_key.id = uuid.uuid4()
    api_key.company_id = company_id
    api_key.created_by_user_id = user_id
    api_key.name = "Test API Key"
    api_key.is_active = True
    api_key.is_expired = False
    api_key.last_used_at = None
    return api_key


# ---------------------------------------------------------------------------
# Project / persona / briefing fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_project(project_id, company_id):
    project = MagicMock()
    project.id = uuid.UUID(project_id)
    project.company_id = company_id
    project.name = "Test Project"
    return project


@pytest.fixture
def fake_persona_group(persona_group_id, project_id):
    pg = MagicMock()
    pg.id = persona_group_id
    pg.project_id = uuid.UUID(project_id)
    pg.name = "Test Group"
    pg.location = "Jakarta"
    pg.occupation = "Professional"
    pg.age_min = 25
    pg.age_max = 40
    pg.generation_status = "complete"
    return pg


@pytest.fixture
def fake_briefing(briefing_id, project_id):
    b = MagicMock()
    b.id = briefing_id
    b.project_id = uuid.UUID(project_id)
    b.extracted_text = "This is a test briefing about a new product."
    return b


@pytest.fixture
def fake_persona():
    p = MagicMock()
    p.id = uuid.uuid4()
    p.full_name = "Sari Dewi"
    p.age = 32
    p.occupation = "Marketing Manager"
    p.location = "Jakarta"
    p.persona_group_id = uuid.uuid4()
    return p


# ---------------------------------------------------------------------------
# FastAPI TestClient with dependency overrides
# ---------------------------------------------------------------------------

@pytest.fixture
def client(mock_db, current_user, fake_project):
    """TestClient with get_db, get_current_user, and project lookup overridden."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db
    from app.auth.dependencies import get_current_user

    # Pre-configure mock_db.get to return a fake project for any project lookup
    mock_db.get.return_value = fake_project

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth(mock_db):
    """TestClient with only get_db overridden — for testing 401 paths."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# OpenAI mock helper
# ---------------------------------------------------------------------------

def make_mock_openai(content: str) -> MagicMock:
    """Build a mock OpenAI client that returns ``content`` from chat.completions.create."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client
