"""
/api/chat — Streaming LLM chat endpoint.
Streams Claude responses via Server-Sent Events.
The FinalReport from the session is injected as context so the user
can ask questions grounded in their specific building analysis.
"""

import json

import anthropic
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models import ChatRequest
from app.session import session_store

router = APIRouter(prefix="/api/chat", tags=["chat"])

MODEL_ID = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024


def _build_system_prompt(report_context: str | None, session: dict) -> str:
    base = """You are a passive building design advisor specialising in Mediterranean climates,
specifically Barcelona, Spain. You are helping an architect understand the analysis
results for their specific building project.

Rules:
- Ground every answer in the analysis results provided
- Be specific: reference facade element IDs, scores, and factor values when relevant
- Acknowledge limitations honestly (e.g. Barcelona's limited night cooling potential)
- Do not recommend active mechanical systems — passive design only
- Keep answers concise (150–250 words) unless a detailed breakdown is requested"""

    if report_context:
        return base + f"\n\nANALYSIS RESULTS FOR THIS BUILDING:\n{report_context}"

    # Try to build context from session report
    report = session.get("report")
    if report:
        strategies_summary = "\n".join(
            f"- {s['name'].replace('_',' ').title()}: {s['impact_level']} "
            f"(score {s['impact_score']:.0f}/100, {s['precondition_met']})"
            for s in report.strategies
        )
        diagnosis = session.get("diagnosis")
        risk = diagnosis.overheating_risk_level if diagnosis else "unknown"
        odh = diagnosis.estimated_proxy_ODH if diagnosis else 0

        context = (
            f"\nBUILDING ANALYSIS SUMMARY:\n"
            f"Overheating risk: {risk} (proxy ODH = {odh:.2f})\n"
            f"Strategy rankings:\n{strategies_summary}"
        )
        return base + context

    return base


def _event(data: str) -> str:
    return f"data: {json.dumps({'text': data})}\n\n"


def _done_event() -> str:
    return "data: [DONE]\n\n"


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    session = session_store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    system_prompt = _build_system_prompt(req.report_context, session)

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    def generate():
        client = anthropic.Anthropic()
        with client.messages.stream(
            model=MODEL_ID,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield _event(text)
        yield _done_event()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
