"""Tests for app/routers/simulations.py — validation logic and CRUD paths.

We use FastAPI's dependency_overrides to swap get_db (→ MagicMock session)
and get_current_user (→ pre-built CurrentUser dataclass), so no real DB
or JWT is involved. Tests focus on validation branches, since happy-path
response serialization requires an ID populated by a real DB flush.
"""
import uuid
from unittest.mock import MagicMock

import pytest


def _url(project_id: str) -> str:
    return f"/api/v1/projects/{project_id}/simulations"


# ---------------------------------------------------------------------------
# Pydantic-level validation
# ---------------------------------------------------------------------------

def test_create_missing_persona_group_ids_returns_422(client, project_id):
    body = {"simulation_type": "concept_test", "prompt_question": "What do you think?"}
    r = client.post(_url(project_id), json=body)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Type-specific validation (raises before any DB query)
# ---------------------------------------------------------------------------

def test_create_concept_test_missing_briefing_ids_returns_422(client, project_id, persona_group_id):
    body = {
        "simulation_type": "concept_test",
        "persona_group_ids": [str(persona_group_id)],
        "briefing_ids": [],
        "prompt_question": "What do you think?",
    }
    r = client.post(_url(project_id), json=body)
    assert r.status_code == 422
    assert "briefing" in r.json()["detail"].lower()


def test_create_concept_test_empty_prompt_question_returns_422(client, project_id, persona_group_id, briefing_id):
    body = {
        "simulation_type": "concept_test",
        "persona_group_ids": [str(persona_group_id)],
        "briefing_ids": [str(briefing_id)],
        "prompt_question": "",
    }
    r = client.post(_url(project_id), json=body)
    assert r.status_code == 422
    assert "prompt_question" in r.json()["detail"]


def test_create_concept_test_whitespace_prompt_question_returns_422(client, project_id, persona_group_id, briefing_id):
    body = {
        "simulation_type": "concept_test",
        "persona_group_ids": [str(persona_group_id)],
        "briefing_ids": [str(briefing_id)],
        "prompt_question": "   \n  ",
    }
    r = client.post(_url(project_id), json=body)
    assert r.status_code == 422


def test_create_idi_manual_missing_persona_id_returns_422(client, project_id, persona_group_id):
    body = {
        "simulation_type": "idi_manual",
        "persona_group_ids": [str(persona_group_id)],
    }
    r = client.post(_url(project_id), json=body)
    assert r.status_code == 422
    assert "idi_persona_id" in r.json()["detail"]


def test_create_focus_group_missing_prompt_question_returns_422(client, project_id, persona_group_id):
    body = {
        "simulation_type": "focus_group",
        "persona_group_ids": [str(persona_group_id)],
    }
    r = client.post(_url(project_id), json=body)
    assert r.status_code == 422
    assert "prompt_question" in r.json()["detail"]


def test_create_conjoint_missing_prompt_question_returns_422(client, project_id, persona_group_id):
    body = {
        "simulation_type": "conjoint",
        "persona_group_ids": [str(persona_group_id)],
    }
    r = client.post(_url(project_id), json=body)
    assert r.status_code == 422
    assert "prompt_question" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# DB-level validation paths
# ---------------------------------------------------------------------------

def _set_groups(mock_db, groups):
    """Configure mock_db.execute().scalars().all() to return the given list."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = groups
    mock_db.execute.return_value = result


def test_create_persona_group_not_found_returns_422(client, mock_db, project_id, persona_group_id, briefing_id):
    _set_groups(mock_db, [])  # no groups returned
    body = {
        "simulation_type": "concept_test",
        "persona_group_ids": [str(persona_group_id)],
        "briefing_ids": [str(briefing_id)],
        "prompt_question": "What do you think?",
    }
    r = client.post(_url(project_id), json=body)
    assert r.status_code == 422
    assert "not found" in r.json()["detail"].lower()


def test_create_persona_group_wrong_project_returns_403(
    client, mock_db, project_id, persona_group_id, briefing_id, fake_persona_group,
):
    fake_persona_group.project_id = uuid.uuid4()  # different project
    _set_groups(mock_db, [fake_persona_group])
    body = {
        "simulation_type": "concept_test",
        "persona_group_ids": [str(persona_group_id)],
        "briefing_ids": [str(briefing_id)],
        "prompt_question": "What do you think?",
    }
    r = client.post(_url(project_id), json=body)
    assert r.status_code == 403
    assert "does not belong" in r.json()["detail"].lower()


def test_create_persona_group_not_complete_returns_422(
    client, mock_db, project_id, persona_group_id, briefing_id, fake_persona_group,
):
    fake_persona_group.generation_status = "pending"
    _set_groups(mock_db, [fake_persona_group])
    body = {
        "simulation_type": "concept_test",
        "persona_group_ids": [str(persona_group_id)],
        "briefing_ids": [str(briefing_id)],
        "prompt_question": "What do you think?",
    }
    r = client.post(_url(project_id), json=body)
    assert r.status_code == 422
    assert "generating" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# get / abort / delete paths
# ---------------------------------------------------------------------------

def test_get_simulation_not_found_returns_404(client, mock_db, project_id, fake_project):
    # First db.get → fake_project (project lookup); second db.get → None (simulation)
    mock_db.get.side_effect = [fake_project, None]
    r = client.get(f"{_url(project_id)}/{uuid.uuid4()}")
    assert r.status_code == 404


def test_get_simulation_wrong_project_returns_404(client, mock_db, project_id, fake_project):
    sim = MagicMock()
    sim.project_id = uuid.uuid4()  # different project
    sim.status = "complete"
    mock_db.get.side_effect = [fake_project, sim]
    r = client.get(f"{_url(project_id)}/{uuid.uuid4()}")
    assert r.status_code == 404


def test_abort_simulation_not_running_returns_422(client, mock_db, project_id, fake_project):
    sim = MagicMock()
    sim.project_id = uuid.UUID(project_id)
    sim.status = "complete"  # not abortable
    mock_db.get.side_effect = [fake_project, sim]
    r = client.post(f"{_url(project_id)}/{uuid.uuid4()}/abort")
    assert r.status_code == 422
    assert "not currently running" in r.json()["detail"].lower()


def test_abort_simulation_not_found_returns_404(client, mock_db, project_id, fake_project):
    mock_db.get.side_effect = [fake_project, None]
    r = client.post(f"{_url(project_id)}/{uuid.uuid4()}/abort")
    assert r.status_code == 404


def test_delete_simulation_not_found_returns_404(client, mock_db, project_id, fake_project):
    mock_db.get.side_effect = [fake_project, None]
    r = client.delete(f"{_url(project_id)}/{uuid.uuid4()}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Auth tests (no auth fixture overrides → 401)
# ---------------------------------------------------------------------------

def test_create_simulation_no_auth_returns_401(client_no_auth, project_id, persona_group_id, briefing_id):
    body = {
        "simulation_type": "concept_test",
        "persona_group_ids": [str(persona_group_id)],
        "briefing_ids": [str(briefing_id)],
        "prompt_question": "What do you think?",
    }
    r = client_no_auth.post(_url(project_id), json=body)
    assert r.status_code == 401
