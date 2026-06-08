import json
import os
from pathlib import Path

import anthropic
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/graph")
async def get_knowledge_graph():
    path = Path("graph/strategy_graph.json")
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Graph not built yet — run: python scripts/build_graph.py",
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@router.get("/test-llm")
async def test_llm():
    """Quick check: is the API key valid and can we reach Claude?"""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return {"status": "error", "detail": "ANTHROPIC_API_KEY not set in environment"}
    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "hi"}],
        )
        return {"status": "ok", "key_prefix": key[:18] + "...", "response": resp.content[0].text}
    except Exception as e:
        return {"status": "error", "key_prefix": key[:18] + "...", "detail": str(e)}
