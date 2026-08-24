"""Core fit analysis: CV vs job description through structured LLM analysis."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .inputs import JobDescription
from .llm import LLMConfig, chat, extract_json

SYSTEM_PROMPT = """You are an expert technical recruiter and hiring manager.
Compare the candidate CV against the job description and respond with ONLY a JSON object (no prose) matching this schema:
{
  "match_score": <int 0-100>,
  "verdict": "<one sentence summary>",
  "matched_requirements": [{"requirement": "...", "evidence_from_cv": "..."}],
  "missing_requirements": [{"requirement": "...", "severity": "critical|nice_to_have", "suggestion": "how to address or reframe"}],
  "tailored_bullet_suggestions": ["<CV bullet rewritten for this JD>", ...],
  "interview_prep_questions": ["<likely interview question for THIS candidate against THIS JD>", ...],
  "ats_keywords_missing": ["keyword1", ...]
}
Be specific: quote actual evidence from the CV. Do not invent experience the CV does not show."""


@dataclass
class FitReport:
    match_score: int
    verdict: str
    matched_requirements: list[dict[str, str]] = field(default_factory=list)
    missing_requirements: list[dict[str, str]] = field(default_factory=list)
    tailored_bullet_suggestions: list[str] = field(default_factory=list)
    interview_prep_questions: list[str] = field(default_factory=list)
    ats_keywords_missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_fit(cv_text: str, jd: JobDescription, config: LLMConfig | None = None) -> FitReport:
    """Analyze how well a CV fits a job description."""
    cfg = config or LLMConfig()
    user_prompt = f"""# JOB DESCRIPTION ({jd.source})
{jd.text[:12000]}

# CANDIDATE CV
{cv_text[:12000]}

Produce the JSON fit report now."""
    raw = chat(SYSTEM_PROMPT, user_prompt, cfg)
    data = extract_json(raw)
    return FitReport(
        match_score=int(data.get("match_score", 0)),
        verdict=str(data.get("verdict", "")),
        matched_requirements=list(data.get("matched_requirements", [])),
        missing_requirements=list(data.get("missing_requirements", [])),
        tailored_bullet_suggestions=list(data.get("tailored_bullet_suggestions", [])),
        interview_prep_questions=list(data.get("interview_prep_questions", [])),
        ats_keywords_missing=list(data.get("ats_keywords_missing", [])),
    )


def report_to_json(report: FitReport) -> str:
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
