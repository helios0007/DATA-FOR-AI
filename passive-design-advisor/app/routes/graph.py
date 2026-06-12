import json

from fastapi import APIRouter, HTTPException

from src import llm_client
from src.utils import resolve_path

router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/graph")
def get_knowledge_graph():
    path = resolve_path("graph/strategy_graph.json")
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Graph not built yet — run: python scripts/build_graph.py",
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@router.get("/test-llm")
def test_llm():
    """Quick check: which LLM provider is active and is it reachable?"""
    provider = llm_client.describe_provider()
    try:
        text = llm_client.complete(
            "You are a health check. Reply with one word.",
            [{"role": "user", "content": "Say OK"}],
            max_tokens=10,
        )
        return {"status": "ok", "provider": provider, "response": text}
    except Exception as e:
        return {"status": "error", "provider": provider, "detail": str(e)}
