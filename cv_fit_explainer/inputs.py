"""Input loaders: CV files and job descriptions (text or URL)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx


@dataclass
class JobDescription:
    source: str  # "url" or "text"
    text: str


def _pdf_to_text(path: Path) -> str:
    try:
        import pymupdf  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF is required for PDF CVs: pip install pymupdf"
        ) from exc
    with pymupdf.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def _docx_to_text(path: Path) -> str:
    try:
        import docx2txt
    except ImportError as exc:
        raise RuntimeError("docx2txt is required for DOCX CVs: pip install docx2txt") from exc
    return docx2txt.process(str(path))


def load_cv(path: str | Path) -> str:
    """Load a CV from PDF, DOCX, MD, or TXT."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CV file not found: {p}")
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        text = _pdf_to_text(p)
    elif suffix == ".docx":
        text = _docx_to_text(p)
    elif suffix in (".md", ".markdown", ".txt"):
        text = p.read_text(encoding="utf-8", errors="replace")
    else:
        # best effort: try plain text
        text = p.read_text(encoding="utf-8", errors="replace")
    return text.strip()


def is_url(candidate: str) -> bool:
    try:
        parts = urlparse(candidate)
        return parts.scheme in ("http", "https") and bool(parts.netloc)
    except ValueError:
        return False


def _strip_html(html: str) -> str:
    # Remove script/style blocks, then tags, then collapse whitespace.
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def fetch_jd_from_url(url: str, timeout: float = 30.0) -> JobDescription:
    """Fetch a job description from a URL (agent tool call step)."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; cv-fit-explainer/0.1)"}
    resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "")
    if "html" in content_type:
        text = _strip_html(resp.text)
    else:
        text = resp.text
    return JobDescription(source="url", text=text)


def load_jd(value: str) -> JobDescription:
    """Load a JD from raw text or a URL."""
    if is_url(value):
        return fetch_jd_from_url(value)
    if not value.strip():
        raise ValueError("Job description is empty")
    return JobDescription(source="text", text=value.strip())
