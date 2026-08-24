# CV Fit Explainer

An agent that explains **how well a CV fits a job description** — with evidence, not vibes.

Given your CV (PDF/DOCX/MD/TXT) and a job description (raw text or URL), it produces:

- **Match score** (0–100) with one-line verdict
- **Matched requirements** — each backed by quoted evidence from your CV
- **Gaps** — rated critical vs nice-to-have, with suggestions to reframe or address
- **Tailored CV bullet suggestions** — rewritten for this specific JD
- **Missing ATS keywords**
- **Interview prep questions** — likely questions for *you* against *this* JD

## Why an agent (and not just a prompt)?

The JD loader is a tool-using step: given a URL, the agent fetches the page,
strips HTML, and extracts the description before analysis. PDF/DOCX parsing is
likewise handled by dedicated tooling, then fed as clean text to the model.
Structured output is validated and extracted robustly (JSON fences, embedded
objects).

## Architecture

```
CV (pdf/docx/md/txt) ──► loader ─┐
                                 ├─► LLM (OpenAI-compatible endpoint)
JD (text or URL) ──► fetcher ────┘        │
                                          ▼
                              structured JSON fit report
                                          │
                                ┌─────────┴─────────┐
                            JSON report         Markdown report
```

Works with any OpenAI-compatible API — point it at
[ai-model-gateway](https://github.com/MaxOS17/ai-model-gateway), LM Studio,
Ollama, or OpenAI directly.

## Quickstart

```bash
pip install -e .

# Against a local gateway / LM Studio:
export CVFIT_BASE_URL=http://127.0.0.1:8000/v1   # your OpenAI-compatible endpoint
export CVFIT_MODEL=your-model-name

cv-fit-explainer --cv my_cv.pdf --jd "Senior Python engineer... (paste text)" 
cv-fit-explainer --cv my_cv.pdf --jd https://jobs.example.com/123 --json > report.json
```

## What this project proves (for AI engineering roles)

- **Tool-using agent design**: URL fetching + document parsing as discrete steps feeding an LLM analysis
- **Structured output handling**: strict JSON schema prompting with robust extraction
- **Provider-agnostic inference**: works against any OpenAI-compatible endpoint (local or cloud)
- **Tested**: unit tests for parsing, extraction, and rendering — no network required

## Configuration (env vars)

| Variable | Default | Purpose |
|---|---|---|
| `CVFIT_BASE_URL` | `http://127.0.0.1:8000/v1` | OpenAI-compatible base URL |
| `CVFIT_API_KEY` | `not-needed` | API key if required |
| `CVFIT_MODEL` | *(none)* | Model name (required) |

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
