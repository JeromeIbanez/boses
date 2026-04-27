"""Tests for app/services/idi_engine.py — parse helpers + analyse + aggregate."""
from unittest.mock import patch

import pytest

from app.services.idi_engine import (
    _analyse_persona_transcript,
    _format_transcript,
    _generate_aggregate_report,
    _parse_questions,
)
from tests.conftest import make_mock_openai


# ---------------------------------------------------------------------------
# _parse_questions
# ---------------------------------------------------------------------------

def test_parse_questions_strips_numeric_prefix():
    script = "1. Tell me about your morning routine.\n2. What apps do you use?"
    qs = _parse_questions(script)
    assert qs == ["Tell me about your morning routine.", "What apps do you use?"]


def test_parse_questions_strips_q_prefix():
    script = "Q1. What is your job?\nQ2: Where do you live?"
    qs = _parse_questions(script)
    assert qs == ["What is your job?", "Where do you live?"]


def test_parse_questions_strips_bullet_prefix():
    script = "- What do you eat?\n* When do you sleep?\n• Where do you go?"
    qs = _parse_questions(script)
    assert qs == ["What do you eat?", "When do you sleep?", "Where do you go?"]


def test_parse_questions_strips_paren_numeric():
    script = "1) First question?\n2) Second question?"
    qs = _parse_questions(script)
    assert qs == ["First question?", "Second question?"]


def test_parse_questions_skips_blank_lines():
    script = "1. First\n\n\n2. Second\n"
    qs = _parse_questions(script)
    assert qs == ["First", "Second"]


def test_parse_questions_empty_string_returns_empty_list():
    assert _parse_questions("") == []


def test_parse_questions_no_prefix():
    script = "Just a plain question?"
    qs = _parse_questions(script)
    assert qs == ["Just a plain question?"]


# ---------------------------------------------------------------------------
# _format_transcript
# ---------------------------------------------------------------------------

def test_format_transcript_interleaves_q_and_a():
    qs = ["Q1?", "Q2?"]
    ans = ["A1.", "A2."]
    out = _format_transcript(qs, ans)
    assert "INTERVIEWER: Q1?" in out
    assert "RESPONDENT: A1." in out
    assert "INTERVIEWER: Q2?" in out
    assert "RESPONDENT: A2." in out


def test_format_transcript_truncates_to_shorter_list():
    qs = ["Q1?", "Q2?", "Q3?"]
    ans = ["A1."]  # only one answer
    out = _format_transcript(qs, ans)
    assert "Q1?" in out
    assert "A1." in out
    assert "Q2?" not in out  # zip stops at shorter list
    assert "Q3?" not in out


def test_format_transcript_empty_lists():
    assert _format_transcript([], []) == ""


# ---------------------------------------------------------------------------
# _analyse_persona_transcript (with patched OpenAI)
# ---------------------------------------------------------------------------

def test_analyse_persona_parses_sentiment_positive(fake_persona):
    raw = (
        "SENTIMENT: Positive\n"
        "SUMMARY: Loved it overall.\n"
        "KEY THEMES: ease, value\n"
        "NOTABLE QUOTES:\n"
        "- This is great\n"
        "- Game changer\n"
    )
    client = make_mock_openai(raw)
    result = _analyse_persona_transcript(client, fake_persona, "transcript")
    assert result["sentiment"] == "Positive"
    assert "Loved it" in result["summary"]
    assert result["key_themes"] == ["ease", "value"]
    assert "This is great" in result["notable_quotes"]
    assert "Game changer" in result["notable_quotes"]


def test_analyse_persona_normalizes_unknown_sentiment_to_neutral(fake_persona):
    raw = "SENTIMENT: confused\nSUMMARY: x\n"
    client = make_mock_openai(raw)
    result = _analyse_persona_transcript(client, fake_persona, "tx")
    assert result["sentiment"] == "Neutral"


def test_analyse_persona_parses_summary_multiline(fake_persona):
    raw = (
        "SENTIMENT: Neutral\n"
        "SUMMARY: First line.\n"
        "Second line.\n"
        "Third line.\n"
    )
    client = make_mock_openai(raw)
    result = _analyse_persona_transcript(client, fake_persona, "tx")
    assert "First line" in result["summary"]
    assert "Second line" in result["summary"]
    assert "Third line" in result["summary"]


def test_analyse_persona_handles_empty_response(fake_persona):
    client = make_mock_openai("")
    result = _analyse_persona_transcript(client, fake_persona, "tx")
    assert result["sentiment"] == "Neutral"
    assert result["summary"] == ""
    assert result["key_themes"] == []
    assert result["notable_quotes"] == []


# ---------------------------------------------------------------------------
# _generate_aggregate_report
# ---------------------------------------------------------------------------

def test_generate_aggregate_report_parses_sections():
    raw = (
        "EXECUTIVE SUMMARY: Most respondents found the concept compelling.\n"
        "CROSS-PERSONA THEMES:\n"
        "- ease of use\n"
        "- price sensitivity\n"
        "PER-PERSONA HIGHLIGHTS:\n"
        "- Sari: loved it\n"
        "- Budi: hesitant\n"
        "RECOMMENDATIONS: Emphasize ease.\n"
    )
    client = make_mock_openai(raw)
    persona_analyses = [
        {"name": "Sari", "age": 32, "occupation": "MM", "sentiment": "Positive",
         "summary": "loved", "key_themes": ["ease"]}
    ]
    result = _generate_aggregate_report(client, "Group", "summary", persona_analyses)
    assert "compelling" in result["executive_summary"]
    assert "ease of use" in result["cross_persona_themes"]
    assert "price sensitivity" in result["cross_persona_themes"]
    assert any("loved it" in h for h in result["per_persona_highlights"])
    assert "Emphasize ease" in result["recommendations"]


def test_generate_aggregate_report_handles_empty_response():
    client = make_mock_openai("")
    result = _generate_aggregate_report(client, "Group", "ctx", [])
    assert result["executive_summary"] == ""
    assert result["cross_persona_themes"] == []
    assert result["per_persona_highlights"] == []
    assert result["recommendations"] == ""
