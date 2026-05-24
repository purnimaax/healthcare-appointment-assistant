"""Chat API — both standard JSON and Server-Sent Events streaming endpoints.

The SSE endpoint emits events as the LangGraph executes, so the frontend can
show tool calls live:

  event: status   { phase: "thinking" }
  event: tool     { tool: "fetch_slots", status: "running", label: "..." }
  event: tool     { tool: "fetch_slots", status: "done", result: {...} }
  event: reply    { content: "...", intent: "appointment", language: "en" }
  event: done     {}

Non-streaming `/chat` returns the same data in one JSON response.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.graph import get_graph
from app.api.schemas import ChatRequest, ChatResponse, ToolCallEvent
from app.core.logging import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def _extract_reply(state_messages: list) -> str:
    """Last AI message in the new messages becomes the reply."""
    for m in reversed(state_messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


@router.post("/chat", response_model=ChatResponse, summary="Send a chat message")
def chat(req: ChatRequest) -> ChatResponse:
    """Single-shot chat: returns the final reply plus the tool-call trace.

    Use this for simple integration. For live UI updates, use `/chat/stream`.
    """
    graph = get_graph()
    try:
        final_state = graph.invoke(
            {
                "messages": [HumanMessage(content=req.message)],
                "session_id": req.session_id,
                "last_tool_calls": [],
            },
            config=_config(req.session_id),
        )
    except Exception as e:  # noqa: BLE001
        log.exception("Chat failed")
        raise HTTPException(500, f"Chat failed: {e}") from e

    reply = _extract_reply(final_state["messages"])
    return ChatResponse(
        session_id=req.session_id,
        reply=reply,
        intent=final_state.get("intent"),
        language=final_state.get("language"),
        tool_calls=[ToolCallEvent(**tc) for tc in final_state.get("last_tool_calls") or []],
    )


# ---------------------------------------------------------------------------
# Streaming endpoint
# ---------------------------------------------------------------------------
async def _sse_event(event: str, data: dict) -> str:
    """Format a single SSE message."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _chat_stream(req: ChatRequest) -> AsyncIterator[str]:
    graph = get_graph()
    cfg = _config(req.session_id)
    emitted_tools: set[str] = set()

    yield await _sse_event("status", {"phase": "thinking"})

    try:
        # stream_mode='values' yields the full state after each node — we diff
        # the tool trace to emit only NEW tool events.
        for state in graph.stream(
            {
                "messages": [HumanMessage(content=req.message)],
                "session_id": req.session_id,
                "last_tool_calls": [],
            },
            config=cfg,
            stream_mode="values",
        ):
            for tc in state.get("last_tool_calls") or []:
                # Unique key per tool call: tool name + args signature + status
                key = f"{tc.get('tool')}::{json.dumps(tc.get('args') or {}, sort_keys=True)}::{tc.get('status')}"
                if key in emitted_tools:
                    continue
                emitted_tools.add(key)
                yield await _sse_event("tool", tc)

        # Final state
        final = graph.get_state(cfg).values
        reply = _extract_reply(final.get("messages") or [])
        yield await _sse_event(
            "reply",
            {
                "content": reply,
                "intent": final.get("intent"),
                "language": final.get("language"),
            },
        )
    except Exception as e:  # noqa: BLE001
        log.exception("Stream failed")
        yield await _sse_event("error", {"message": str(e)})

    yield await _sse_event("done", {})


@router.post("/chat/stream", summary="Stream a chat response (Server-Sent Events)")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    """Returns a `text/event-stream` with tool-call updates as the graph runs.

    Frontend reads with EventSource or fetch+ReadableStream. See `frontend/`
    for the consumer implementation.
    """
    return StreamingResponse(
        _chat_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # nginx hint to disable buffering
            "Connection": "keep-alive",
        },
    )


@router.get("/chat/history/{session_id}", summary="Get chat history for a session")
def chat_history(session_id: str) -> dict:
    """Return the conversation history stored in the checkpointer for the
    given session. Used by the frontend to restore on page reload."""
    graph = get_graph()
    snap = graph.get_state(_config(session_id))
    if not snap or not snap.values:
        return {"session_id": session_id, "messages": []}

    msgs = snap.values.get("messages") or []
    return {
        "session_id": session_id,
        "messages": [
            {
                "role": "user" if isinstance(m, HumanMessage) else "assistant",
                "content": m.content if isinstance(m.content, str) else str(m.content),
            }
            for m in msgs
            if isinstance(m, (HumanMessage, AIMessage)) and m.content
        ],
    }
