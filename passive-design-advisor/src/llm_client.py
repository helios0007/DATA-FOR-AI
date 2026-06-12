"""
Provider-agnostic LLM access.

Provider selection (env vars):
  LLM_PROVIDER=anthropic | ollama   — force a provider
  unset / auto                      — anthropic if ANTHROPIC_API_KEY is set,
                                      otherwise a local Ollama server

  ANTHROPIC_MODEL  (default claude-haiku-4-5-20251001)
  OLLAMA_URL       (default http://localhost:11434)
  OLLAMA_MODEL     (default llama3.1)
"""

import json
import os
from typing import Iterator

import httpx

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
OLLAMA_URL      = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "llama3.1")

# Local models can be slow to generate long answers — be generous.
_OLLAMA_TIMEOUT = httpx.Timeout(600.0, connect=10.0)


def get_provider() -> str:
    forced = os.environ.get("LLM_PROVIDER", "").lower()
    if forced in ("anthropic", "ollama"):
        return forced
    return "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "ollama"


def describe_provider() -> str:
    if get_provider() == "anthropic":
        return f"anthropic ({ANTHROPIC_MODEL})"
    return f"ollama ({OLLAMA_MODEL} @ {OLLAMA_URL})"


def complete(system: str, messages: list[dict], max_tokens: int = 1000) -> str:
    """Single non-streamed completion. messages = [{"role", "content"}, ...]."""
    if get_provider() == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return resp.content[0].text

    resp = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": False,
            "options": {"num_predict": max_tokens},
        },
        timeout=_OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def stream_text(system: str, messages: list[dict], max_tokens: int = 1024) -> Iterator[str]:
    """Yield response text chunks as they are generated."""
    if get_provider() == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        with client.messages.stream(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        ) as stream:
            yield from stream.text_stream
        return

    with httpx.stream(
        "POST",
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": True,
            "options": {"num_predict": max_tokens},
        },
        timeout=_OLLAMA_TIMEOUT,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            chunk = data.get("message", {}).get("content", "")
            if chunk:
                yield chunk
            if data.get("done"):
                break
