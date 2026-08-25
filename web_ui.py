"""Tiny web UI for cv-fit-explainer. Reuses the existing analyzer/inputs modules."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, render_template_string, request, jsonify

# Make sure the package imports work when run from the repo root
sys.path.insert(0, str(Path(__file__).parent))

from cv_fit_explainer.analyzer import analyze_fit, FitReport
from cv_fit_explainer.inputs import load_cv, load_jd, JobDescription
from cv_fit_explainer.llm import LLMConfig

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>CV Fit Analysis</title>
<style>
  :root { --bg: #0f172a; --panel: #1e293b; --border: #334155; --text: #e2e8f0; --muted: #94a3b8; --accent: #38bdf8; }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.45 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; }
  header { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 16px; margin: 0; font-weight: 600; }
  header .pill { font-size: 11px; color: var(--muted); background: var(--panel); border: 1px solid var(--border); padding: 4px 8px; border-radius: 999px; }
  main { max-width: 980px; margin: 0 auto; padding: 20px; display: grid; gap: 14px; }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 14px; }
  label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; }
  input[type=text], textarea { width: 100%; background: #0b1220; color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 10px; font: inherit; }
  textarea { min-height: 180px; resize: vertical; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  button { background: var(--accent); color: #0f172a; border: 0; padding: 10px 14px; border-radius: 8px; font-weight: 600; cursor: pointer; }
  button:disabled { opacity: .5; cursor: not-allowed; }
  .result { white-space: pre-wrap; word-wrap: break-word; }
  .result h2 { font-size: 14px; margin: 14px 0 6px; color: var(--accent); }
  .result p { margin: 6px 0; }
  .error { color: #fca5a5; }
</style>
</head>
<body>
<header>
  <h1>CV Fit Analysis</h1>
  <span class="pill">local model</span>
</header>
<main>
  <div class="panel">
    <div class="row">
      <div>
        <label for="cv">Master CV</label>
        <input id="cv" type="text" value="C:/Users/maxor/Documents/Max CV-CL/CV_Master_v2.md" />
      </div>
      <div>
        <label for="jd">Job description</label>
        <input id="jd" type="text" placeholder="Paste JD text or a URL" />
      </div>
    </div>
    <div style="margin-top:10px">
      <label for="jdtext">Or paste full JD text here</label>
      <textarea id="jdtext" placeholder="Paste the job description text here…"></textarea>
    </div>
    <div style="margin-top:10px; display:flex; gap:10px; align-items:center;">
      <button id="run" onclick="run()">Run analysis</button>
      <span id="status" class="result" style="color:var(--muted)"></span>
    </div>
  </div>
  <div id="out" class="panel result" style="display:none"></div>
</main>
<script>
  async function run() {
    const out = document.getElementById('out');
    const status = document.getElementById('status');
    const btn = document.getElementById('run');
    const cv = document.getElementById('cv').value.trim();
    const jd = document.getElementById('jd').value.trim();
    const jdtext = document.getElementById('jdtext').value.trim();
    if (!cv || (!jd && !jdtext)) {
      status.textContent = 'Provide a JD URL or paste JD text.';
      return;
    }
    btn.disabled = true;
    out.style.display = 'none';
    status.textContent = 'Running…';
    try {
      const form = new FormData();
      form.append('cv', cv);
      form.append('jd', jd);
      form.append('jdtext', jdtext);
      const r = await fetch('/api/analyze', { method: 'POST', body: form });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Request failed');
      out.textContent = data.report;
      out.classList.remove('error');
      out.style.display = 'block';
      status.textContent = '';
    } catch (e) {
      out.textContent = 'Error: ' + e.message;
      out.classList.add('error');
      out.style.display = 'block';
      status.textContent = '';
    } finally {
      btn.disabled = false;
    }
  }
</script>
</body>
</html>
"""


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template_string(TEMPLATE)

    @app.post("/api/analyze")
    def api_analyze():
        cv_path = request.form.get("cv", "").strip()
        jd_url = request.form.get("jd", "").strip()
        jd_text = request.form.get("jdtext", "").strip()
        if not cv_path or not (jd_url or jd_text):
            return jsonify(error="Provide a CV path and a JD URL or text."), 400

        # Load CV
        try:
            cv_text = load_cv(Path(cv_path))
        except Exception as e:
            return jsonify(error=f"CV load failed: {e}"), 400

        # Resolve JD
        try:
            if jd_url and not jd_text:
                jd_final = load_jd(jd_url)
            else:
                jd_final = JobDescription(source="text", text=jd_text.strip())
        except Exception as e:
            return jsonify(error=f"JD fetch failed: {e}"), 400

        # Run analysis
        try:
            llm = LLMConfig(
                base_url=os.environ.get("CVFIT_BASE_URL", "http://127.0.0.1:1234/v1"),
                api_key=os.environ.get("CVFIT_API_KEY", "not-needed"),
                model=os.environ.get("CVFIT_MODEL", "local-model"),
            )
            report = analyze_fit(cv_text, jd_final, llm)
        except Exception as e:
            return jsonify(error=f"Analysis failed: {e}"), 500

        return jsonify(report=report.markdown)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5001, debug=False)
