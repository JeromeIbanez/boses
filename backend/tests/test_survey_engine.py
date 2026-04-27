"""Tests for app/services/survey_engine.py — _parse_json, _build_survey_prompt, worker."""
import json
from unittest.mock import patch

import pytest

from app.services.survey_engine import (
    _build_survey_prompt,
    _parse_json,
    _survey_persona_worker,
)
from tests.conftest import make_mock_openai


# ---------------------------------------------------------------------------
# _parse_json
# ---------------------------------------------------------------------------

def test_parse_json_valid_object():
    assert _parse_json('{"a": 1}', None) == {"a": 1}


def test_parse_json_valid_array():
    assert _parse_json('[1, 2, 3]', None) == [1, 2, 3]


def test_parse_json_strips_markdown_json_fence():
    raw = '```json\n{"a": 1}\n```'
    assert _parse_json(raw, None) == {"a": 1}


def test_parse_json_strips_plain_fence():
    raw = '```\n{"a": 1}\n```'
    assert _parse_json(raw, None) == {"a": 1}


def test_parse_json_extracts_json_from_surrounding_text():
    raw = 'Here is the answer: {"a": 1} (end)'
    assert _parse_json(raw, None) == {"a": 1}


def test_parse_json_returns_fallback_on_invalid():
    assert _parse_json("not json at all", []) == []


def test_parse_json_returns_fallback_on_empty_string():
    assert _parse_json("", "fallback") == "fallback"


def test_parse_json_returns_fallback_on_none():
    assert _parse_json(None, []) == []


def test_parse_json_returns_fallback_on_whitespace():
    assert _parse_json("   \n  ", "fb") == "fb"


# ---------------------------------------------------------------------------
# _build_survey_prompt
# ---------------------------------------------------------------------------

def test_build_survey_prompt_likert_includes_scale_labels(fake_persona):
    questions = [{
        "id": "q1",
        "type": "likert",
        "text": "How much do you like it?",
        "scale": 5,
        "low_label": "Hate it",
        "high_label": "Love it",
    }]
    sys_p, user_p = _build_survey_prompt(fake_persona, "briefing", questions)
    assert "Hate it" in user_p
    assert "Love it" in user_p
    assert "1–5" in user_p
    assert "How much do you like it?" in user_p


def test_build_survey_prompt_multiple_choice_includes_options(fake_persona):
    questions = [{
        "id": "q1",
        "type": "multiple_choice",
        "text": "Which color?",
        "options": ["red", "blue", "green"],
    }]
    _, user_p = _build_survey_prompt(fake_persona, "briefing", questions)
    assert "red" in user_p
    assert "blue" in user_p
    assert "green" in user_p
    assert "choose one" in user_p


def test_build_survey_prompt_open_ended(fake_persona):
    questions = [{"id": "q1", "type": "open_ended", "text": "Tell us more"}]
    _, user_p = _build_survey_prompt(fake_persona, "briefing", questions)
    assert "open_ended" in user_p
    assert "Tell us more" in user_p


# ---------------------------------------------------------------------------
# _survey_persona_worker (with patched OpenAI)
# ---------------------------------------------------------------------------

def test_survey_persona_worker_enriches_answers(fake_persona):
    questions = [
        {"id": "q1", "type": "likert", "text": "Rate it", "scale": 5,
         "low_label": "low", "high_label": "high"},
        {"id": "q2", "type": "open_ended", "text": "Why?"},
    ]
    response = json.dumps([
        {"id": "q1", "answer": 4},
        {"id": "q2", "answer": "Because it's good."},
    ])
    with patch("app.services.survey_engine.get_openai_client",
               return_value=make_mock_openai(response)):
        persona, enriched = _survey_persona_worker(fake_persona, "brief", questions)

    assert persona is fake_persona
    assert len(enriched) == 2
    assert enriched[0]["id"] == "q1"
    assert enriched[0]["question_text"] == "Rate it"
    assert enriched[0]["type"] == "likert"
    assert enriched[0]["answer"] == 4
    assert enriched[0]["scale"] == 5
    assert enriched[1]["id"] == "q2"
    assert enriched[1]["answer"] == "Because it's good."


def test_survey_persona_worker_handles_invalid_json_response(fake_persona):
    questions = [{"id": "q1", "type": "open_ended", "text": "Why?"}]
    with patch("app.services.survey_engine.get_openai_client",
               return_value=make_mock_openai("not-json")):
        _, enriched = _survey_persona_worker(fake_persona, "brief", questions)
    # _parse_json returns the [] fallback, so enriched is empty
    assert enriched == []
