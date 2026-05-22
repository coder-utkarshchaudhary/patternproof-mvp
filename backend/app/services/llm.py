"""Hybrid LLM wrappers.

- Claude (Anthropic) for agent reasoning and vision explanations. System
  prompts are sent with ``cache_control`` so the cacheable prefix is reused
  across the many per-page calls in an audit (lower latency + cost).
- A cheap model (OpenAI) for high-volume per-page HTML semantic parsing,
  using JSON response format for structured output.
"""

from __future__ import annotations

import base64
import json
import requests
from functools import lru_cache
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _anthropic():
    from anthropic import Anthropic
    return Anthropic(api_key=settings.anthropic_api_key)


# ── Claude: agent reasoning ──────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20), reraise=True)
def claude_chat(system: str, user: str, *, max_tokens: int = 1024, temperature: float = 0.0) -> str:
    """Single-turn Claude completion. The system prompt is cached."""
    resp = _anthropic().messages.create(
        model=settings.claude_agent_model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if block.type == "text").strip()


def claude_json(system: str, user: str, *, max_tokens: int = 1500) -> Any:
    """Claude completion expected to return JSON; tolerant of code fences."""
    raw = claude_chat(system, user, max_tokens=max_tokens)
    return _loads_lenient(raw)


# ── Claude: vision explanation ────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20), reraise=True)
def claude_vision(image_bytes: bytes, system: str, user: str, *, max_tokens: int = 600) -> str:
    """Explain a (cropped) screenshot region with Claude vision."""
    img_b64 = base64.b64encode(image_bytes).decode()
    resp = _anthropic().messages.create(
        model=settings.claude_vision_model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
                    },
                    {"type": "text", "text": user},
                ],
            }
        ],
    )
    return "".join(block.text for block in resp.content if block.type == "text").strip()


# ── Cheap model: per-page HTML semantic parsing ───────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20), reraise=True)
def cheap_parse_json(system: str, user: str, *, max_tokens: int = 2000) -> Any:
    """Call the cheap model with JSON output mode; return parsed JSON."""
    url = f"{settings.ollama_base_url}/api/chat"

    payload = {
        "model": settings.cheap_parse_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": max_tokens,
        },
    }

    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.ollama_api_key}",
            "Content-Type": "application/json",
        },
        timeout=120,
    )

    response.raise_for_status()
    data = response.json()
    content = data.get("message", {}).get("content", "{}")

    return _loads_lenient(content)


def _loads_lenient(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1] if "```" in raw[3:] else raw.strip("`")
        raw = raw.removeprefix("json").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to salvage the first JSON object/array in the string.
        for opener, closer in (("{", "}"), ("[", "]")):
            i, j = raw.find(opener), raw.rfind(closer)
            if i != -1 and j > i:
                try:
                    return json.loads(raw[i : j + 1])
                except json.JSONDecodeError:
                    continue
        logger.warning("Could not parse JSON from LLM output: %s", raw[:200])
        return {}
