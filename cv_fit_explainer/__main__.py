"""CLI entry point."""
from __future__ import annotations

import argparse
import sys

from .analyzer import analyze_fit, report_to_json
from .inputs import load_cv, load_jd
from .llm import LLMConfig
from .report import render_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cv-fit-explainer",
        description="Explain how well a CV fits a job description.",
    )
    parser.add_argument("--cv", required=True, help="Path to CV (PDF/DOCX/MD/TXT)")
    parser.add_argument("--jd", required=True, help="Job description: raw text or URL")
    parser.add_argument("--url", default=None, help="LLM base URL (default: $CVFIT_BASE_URL or http://127.0.0.1:8000/v1)")
    parser.add_argument("--model", default=None, help="Model name (default: $CVFIT_MODEL)")
    parser.add_argument("--api-key", default=None, help="API key (default: $CVFIT_API_KEY)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output JSON instead of markdown")
    args = parser.parse_args(argv)

    config = LLMConfig()
    if args.url:
        config.base_url = args.url
    if args.model:
        config.model = args.model
    if args.api_key:
        config.api_key = args.api_key

    try:
        cv_text = load_cv(args.cv)
        jd = load_jd(args.jd)
        report = analyze_fit(cv_text, jd, config)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(report_to_json(report))
    else:
        print(render_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
