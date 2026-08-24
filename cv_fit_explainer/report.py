"""Human-readable report rendering."""
from __future__ import annotations

from .analyzer import FitReport


def render_report(report: FitReport, title: str = "CV Fit Report") -> str:
    lines: list[str] = []
    bar_len = 20
    filled = round(report.match_score / 100 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)

    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Match: {report.match_score}%**  `{bar}`")
    lines.append("")
    lines.append(f"> {report.verdict}")
    lines.append("")

    if report.matched_requirements:
        lines.append("## ✅ Matched requirements")
        for item in report.matched_requirements:
            req = item.get("requirement", "?")
            ev = item.get("evidence_from_cv", "")
            lines.append(f"- **{req}** — {ev}")
        lines.append("")

    if report.missing_requirements:
        lines.append("## ⚠️ Gaps")
        for item in report.missing_requirements:
            req = item.get("requirement", "?")
            sev = item.get("severity", "?")
            sug = item.get("suggestion", "")
            lines.append(f"- **{req}** _({sev})_ → {sug}")
        lines.append("")

    if report.tailored_bullet_suggestions:
        lines.append("## 📝 Tailored CV bullet suggestions")
        for b in report.tailored_bullet_suggestions:
            lines.append(f"- {b}")
        lines.append("")

    if report.ats_keywords_missing:
        lines.append("## 🔑 Missing ATS keywords")
        lines.append(", ".join(report.ats_keywords_missing))
        lines.append("")

    if report.interview_prep_questions:
        lines.append("## 🎤 Interview prep questions")
        for q in report.interview_prep_questions:
            lines.append(f"- {q}")
        lines.append("")

    return "\n".join(lines)
