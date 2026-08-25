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

PRESETS = {
    "lmstudio": {
        "base_url": "http://localhost:1234/v1",
        "api_key": "not-needed",
        "model": "local-model",
    },
    "gateway": {
        "base_url": "http://localhost:8080/v1",
        "api_key": "not-needed",
        "model": "local-model",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
    },
}


def _llm_from_form(form) -> LLMConfig:
    provider = form.get("provider", "lmstudio")
    model = form.get("model", "").strip()
    base_url = form.get("base_url", "").strip()
    api_key = form.get("api_key", "").strip() or "not-needed"

    if provider == "custom":
        if not base_url or not model:
            raise ValueError("Custom provider requires both base URL and model name.")
        return LLMConfig(base_url=base_url, api_key=api_key, model=model)

    preset = PRESETS.get(provider, PRESETS["lmstudio"])
    if not model:
        model = preset["model"]
    return LLMConfig(
        base_url=base_url or preset["base_url"],
        api_key=api_key or preset["api_key"],
        model=model,
    )

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
  <span id="pill" class="pill">local model</span>
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
    <div style="margin-top:10px; display:grid; grid-template-columns: 1fr 1fr 1fr auto; gap:10px; align-items:end;">
      <div>
        <label for="provider">Provider</label>
        <select id="provider">
          <option value="lmstudio">LM Studio (local)</option>
          <option value="gateway">AI Model Gateway</option>
          <option value="openai">OpenAI</option>
          <option value="custom">Custom…</option>
        </select>
      </div>
      <div>
        <label for="model">Model</label>
        <input id="model" type="text" value="local-model" placeholder="Model name" />
      </div>
      <div id="custom_url_group" style="display:none">
        <label for="base_url">Base URL</label>
        <input id="base_url" type="text" value="http://localhost:1234/v1" placeholder="https://..." />
      </div>
      <div>
        <label for="api_key">API key</label>
        <input id="api_key" type="text" value="not-needed" placeholder="Optional" />
      </div>
    </div>
    <div style="margin-top:10px; display:flex; gap:10px; align-items:center;">
      <button id="run" onclick="run()">Run analysis</button>
      <span id="status" class="result" style="color:var(--muted)"></span>
    </div>
  </div>
  <div id="out" class="panel result" style="display:none"></div>
</main>
<script>
  const STORAGE_KEY = 'cvfit-provider-config';
  const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  const providerEl = document.getElementById('provider');
  const modelEl = document.getElementById('model');
  const baseUrlEl = document.getElementById('base_url');
  const apiKeyEl = document.getElementById('api_key');
  const customUrlGroup = document.getElementById('custom_url_group');
  const pill = document.getElementById('pill');

  function applySaved() {
    providerEl.value = saved.provider || 'lmstudio';
    modelEl.value = saved.model || 'local-model';
    baseUrlEl.value = saved.base_url || 'http://localhost:1234/v1';
    apiKeyEl.value = saved.api_key || 'not-needed';
    customUrlGroup.style.display = providerEl.value === 'custom' ? 'block' : 'none';
    updatePill();
  }

  function updatePill() {
    const p = providerEl.value;
    const map = { lmstudio: 'LM Studio', gateway: 'Gateway', openai: 'OpenAI', custom: 'Custom' };
    pill.textContent = (map[p] || p) + ' · ' + (modelEl.value.trim() || '—');
  }

  providerEl.addEventListener('change', () => {
    customUrlGroup.style.display = providerEl.value === 'custom' ? 'block' : 'none';
    updatePill();
  });
  modelEl.addEventListener('input', updatePill);

  applySaved();

  async function run() {
    const out = document.getElementById('out');
    const status = document.getElementById('status');
    const btn = document.getElementById('run');
    const cv = document.getElementById('cv').value.trim();
    const jd = document.getElementById('jd').value.trim();
    const jdtext = document.getElementById('jdtext').value.trim();
    const provider = providerEl.value;
    const model = modelEl.value.trim();
    const base_url = baseUrlEl.value.trim();
    const api_key = apiKeyEl.value.trim();
    if (!cv || (!jd && !jdtext)) {
      status.textContent = 'Provide a JD URL or paste JD text.';
      return;
    }
    if (!model) {
      status.textContent = 'Provide a model name.';
      return;
    }
    const config = { provider, model, base_url, api_key };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    btn.disabled = true;
    out.style.display = 'none';
    status.textContent = 'Running…';
    try {
      const form = new FormData();
      form.append('cv', cv);
      form.append('jd', jd);
      form.append('jdtext', jdtext);
      form.append('provider', provider);
      form.append('model', model);
      form.append('base_url', base_url);
      form.append('api_key', api_key);
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
            llm = _llm_from_form(request.form)
            report = analyze_fit(cv_text, jd_final, llm)
        except Exception as e:
            return jsonify(error=f"Analysis failed: {e}"), 500

        return jsonify(report=report.markdown)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5001, debug=False)
