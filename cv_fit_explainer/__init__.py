"""CV Fit Explainer — agent that explains how well a CV fits a job description.

Pipeline:
1. Load CV (PDF/MD/TXT)
2. Load job description (text or URL via tool call)
3. Structured fit analysis through an LLM (routed via ai-model-gateway or any
   OpenAI-compatible endpoint)
4. Output: JSON report + human-readable summary

Usage:
    python -m cv_fit_explainer --cv my_cv.pdf --jd https://example.com/job --url http://localhost:8000/v1
"""
from __future__ import annotations

from .analyzer import analyze_fit
from .inputs import load_cv, load_jd
from .report import render_report

__all__ = ["analyze_fit", "load_cv", "load_jd", "render_report"]
__version__ = "0.1.0"
