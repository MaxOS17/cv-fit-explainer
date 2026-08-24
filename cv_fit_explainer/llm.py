"""LLM client: routes to any OpenAI-compatible endpoint (model gateway or direct)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import httpx


@dataclass
class LLMConfig:
    base_url: str = field(default_factory=lambda: os.environ.get("CVFIT_BASE_URL", "http://127.0.0.1:8000/v1"))
    api_key: str = field(default_factory=lambda: os.environ.get("CVFIT_API_KEY", "not-needed"))
    model: str = field(default_factory=lambda: os.environ.get("CVFIT_MODEL", ""))
    temperature: float = 0.2
    timeout: float = 120.0


def chat(system_prompt: str, user_prompt: str, config: LLMConfig) -> str:
    """Single-turn chat completion against an OpenAI-compatible /chat/completions API."""
    if not config.model:
        raise RuntimeError("No model configured. Set CVFIT_MODEL or pass --model.")
    payload = {
        "model": config.model,
        "temperature": config.temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {"Authorization": f"Bearer {config.api_key}"}
    resp = httpx.post(
        f"{config.base_url.rstrip('/')}/chat/completions",
        json=payload,
        headers=headers,
        timeout=config.timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected LLM response shape: {json.dumps(data)[:300]}") from exc


def extract_json(text: str) -> dict:
    """Extract the first JSON object from an LLM response (handles ```json fences)."""
    fence_match = None
    import re

    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if m:
        fence_match = m.group(1)
    raw = fence_match or text
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in response: {text[:200]}")
    return json.loads(raw[start : end + 1])
