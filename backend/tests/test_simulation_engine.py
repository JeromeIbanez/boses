"""Tests for app/services/simulation_engine.py — parse helpers + worker."""
import json
from unittest.mock import patch

import pytest

from app.services.simulation_engine import (
    _concept_test_persona_worker,
    _parse_aggregate_response,
    _parse_individual_response,
)
from tests.conftest import make_mock_openai


# ---------------------------------------------------------------------------
# _parse_individual_response
# ---------------------------------------------------------------------------

def test_parse_individual_valid_json():
    raw = json.dumps({
        "reaction": "I love it",
        "sentiment": "Positive",
        "reasoning": "It solves my problem",
        "notable_quote": "Finally!",
        "key_themes": ["convenience", "value"],
    })
    result = _parse_individual_response(raw)
    assert result["reaction"] == "I love it"
    assert result["sentiment"] == "Positive"
    assert result["key_themes"] == ["convenience", "value"]
    assert result["notable_quote"] == "Finally!"


def test_parse_individual_invalid_json_returns_defaults():
    result = _parse_individual_response("this is not json")
    assert result == {
        "reaction": "",
        "sentiment": "Neutral",
        "reasoning": "",
        "notable_quote": "",
        "key_themes": [],
    }


def test_parse_individual_normalizes_unknown_sentiment_to_neutral():
    raw = json.dumps({"sentiment": "ecstatic"})
    result = _parse_individual_response(raw)
    assert result["sentiment"] == "Neutral"


def test_parse_individual_capitalizes_sentiment():
    raw = json.dumps({"sentiment": "positive"})
    result = _parse_individual_response(raw)
    assert result["sentiment"] == "Positive"


def test_parse_individual_handles_string_themes():
    raw = json.dumps({"key_themes": "convenience, value, speed"})
    result = _parse_individual_response(raw)
    assert result["key_themes"] == ["convenience", "value", "speed"]


def test_parse_individual_handles_list_themes():
    raw = json.dumps({"key_themes": ["a", "b"]})
    result = _parse_individual_response(raw)
    assert result["key_themes"] == ["a", "b"]


def test_parse_individual_handles_empty_string():
    result = _parse_individual_response("")
    assert result["sentiment"] == "Neutral"
    assert result["reaction"] == ""


# ---------------------------------------------------------------------------
# _parse_aggregate_response
# ---------------------------------------------------------------------------

def test_parse_aggregate_parses_all_sections():
    raw = (
        "1. OVERALL SENTIMENT: Positive\n"
        "2. SENTIMENT DISTRIBUTION:\n"
        "Positive: 5\n"
        "Neutral: 2\n"
        "Negative: 1\n"
        "3. TOP THEMES: convenience, price, trust\n"
        "4. SUMMARY: Most respondents reacted favorably to the concept.\n"
        "5. STRATEGIC RECOMMENDATIONS: Lead with convenience messaging.\n"
    )
    result = _parse_aggregate_response(raw)
    assert result["overall_sentiment"] == "Positive"
    assert result["distribution"] == {"Positive": 5, "Neutral": 2, "Negative": 1}
    assert result["top_themes"] == ["convenience", "price", "trust"]
    assert "favorably" in result["summary"]
    assert "convenience messaging" in result["recommendations"]


def test_parse_aggregate_distribution_with_dash_prefix():
    raw = (
        "SENTIMENT DISTRIBUTION:\n"
        "- Positive: 3\n"
        "- Neutral: 1\n"
    )
    result = _parse_aggregate_response(raw)
    assert result["distribution"] == {"Positive": 3, "Neutral": 1}


def test_parse_aggregate_top_themes_inline():
    raw = "TOP THEMES: trust, value\n"
    result = _parse_aggregate_response(raw)
    assert result["top_themes"] == ["trust", "value"]


def test_parse_aggregate_top_themes_next_line():
    raw = "TOP THEMES:\nconvenience, simplicity\n"
    result = _parse_aggregate_response(raw)
    assert result["top_themes"] == ["convenience", "simplicity"]


def test_parse_aggregate_multiline_summary():
    raw = (
        "SUMMARY: First line.\n"
        "Continued explanation.\n"
        "Final note.\n"
    )
    result = _parse_aggregate_response(raw)
    assert "First line" in result["summary"]
    assert "Continued explanation" in result["summary"]
    assert "Final note" in result["summary"]


def test_parse_aggregate_empty_string_returns_empty_sections():
    result = _parse_aggregate_response("")
    assert result["overall_sentiment"] == ""
    assert result["distribution"] == {}
    assert result["top_themes"] == []
    assert result["summary"] == ""
    assert result["recommendations"] == ""


def test_parse_aggregate_distribution_skips_invalid_numbers():
    raw = (
        "SENTIMENT DISTRIBUTION:\n"
        "Positive: many\n"
        "Neutral: 2\n"
    )
    result = _parse_aggregate_response(raw)
    # "many" is not parseable; should be skipped
    assert "Positive" not in result["distribution"]
    assert result["distribution"]["Neutral"] == 2


# ---------------------------------------------------------------------------
# _concept_test_persona_worker (with patched OpenAI)
# ---------------------------------------------------------------------------

def test_concept_test_persona_worker_calls_openai_and_parses(fake_persona):
    mock_content = json.dumps({
        "reaction": "It's interesting",
        "sentiment": "Positive",
        "reasoning": "novel approach",
        "notable_quote": "wow",
        "key_themes": ["novelty"],
    })
    with patch("app.services.simulation_engine.get_openai_client",
               return_value=make_mock_openai(mock_content)):
        persona, parsed = _concept_test_persona_worker(
            fake_persona, "briefing", "What do you think?"
        )

    assert persona is fake_persona
    assert parsed["sentiment"] == "Positive"
    assert parsed["reaction"] == "It's interesting"
    assert parsed["key_themes"] == ["novelty"]


def test_concept_test_persona_worker_handles_invalid_json(fake_persona):
    with patch("app.services.simulation_engine.get_openai_client",
               return_value=make_mock_openai("not-json")):
        _, parsed = _concept_test_persona_worker(
            fake_persona, "briefing", "What do you think?"
        )
    assert parsed["sentiment"] == "Neutral"
    assert parsed["reaction"] == ""
