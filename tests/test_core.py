"""Tests for inputs, JSON extraction, and report rendering (no network needed)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cv_fit_explainer.analyzer import FitReport
from cv_fit_explainer.inputs import JobDescription, is_url, load_cv
from cv_fit_explainer.llm import extract_json
from cv_fit_explainer.report import render_report


# ---------- inputs ----------

def test_is_url_positive():
    assert is_url("https://example.com/job/123")
    assert is_url("http://jobs.io/x")


def test_is_url_negative():
    assert not is_url("just some text about a role")
    assert not is_url("")
    assert not is_url("ftp://nope.example")


def test_load_cv_txt(tmp_path: Path):
    p = tmp_path / "cv.txt"
    p.write_text("Max Ortiz — Strategy & Ops Leader", encoding="utf-8")
    assert "Strategy" in load_cv(p)


def test_load_cv_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_cv(tmp_path / "nope.pdf")


# ---------- llm JSON extraction ----------

def test_extract_json_plain():
    raw = '{"match_score": 72}'
    assert extract_json(raw)["match_score"] == 72


def test_extract_json_fenced():
    raw = 'Here you go:\n```json\n{"match_score": 88, "verdict": "strong"}\n```\nDone.'
    data = extract_json(raw)
    assert data["match_score"] == 88


def test_extract_json_embedded():
    raw = 'prefix {"a": {"b": 1}} suffix'
    assert extract_json(raw)["a"]["b"] == 1


def test_extract_json_invalid():
    with pytest.raises(ValueError):
        extract_json("no json here at all")


# ---------- report rendering ----------

def _sample_report() -> FitReport:
    return FitReport(
        match_score=76,
        verdict="Strong overall fit with two addressable gaps.",
        matched_requirements=[{"requirement": "5+ years Python", "evidence_from_cv": "Automated L2 workflows with scripts (2015-2018)"}],
        missing_requirements=[{"requirement": "Kubernetes", "severity": "nice_to_have", "suggestion": "Highlight containerized deployments instead"}],
        tailored_bullet_suggestions=["Reframe migration work as platform modernization"],
        interview_prep_questions=["Describe a migration you led end to end"],
        ats_keywords_missing=["terraform", "k8s"],
    )


def test_render_report_contains_sections():
    text = render_report(_sample_report())
    assert "Match: 76%" in text
    assert "Matched requirements" in text
    assert "Gaps" in text
    assert "Interview prep" in text
    assert "terraform" in text


def test_report_to_json_roundtrip():
    from cv_fit_explainer.analyzer import report_to_json

    data = json.loads(report_to_json(_sample_report()))
    assert data["match_score"] == 76
    assert isinstance(data["matched_requirements"], list)


def test_jd_dataclass():
    jd = JobDescription(source="text", text="Senior Python role")
    assert jd.source == "text"
