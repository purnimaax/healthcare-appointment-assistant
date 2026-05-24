"""Document Analysis agent.

Handles questions about documents/images the user has uploaded in this session.
Retrieves only from the user_uploads collection (scoped by session_id), since
the user is asking about *their* document, not the general KB.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.llm import get_chat_model
from app.agents.state import AgentState
from app.core.logging import get_logger
from app.services.rag import get_rag

log = get_logger(__name__)


def _system_prompt(language: str, context: str) -> str:
    return f"""You are a Document Analysis assistant. The user has uploaded one \
or more documents/images, and is asking about them. Use the context below \
(extracted from their uploads) to answer.

UPLOADED DOCUMENT CONTEXT:
---
{context}
---

RULES
- Stay grounded in what the document actually says.
- For lab results, point out values outside normal range when shown — but \
remind the user that interpretation requires a doctor.
- For prescriptions, list medicines, dosage, frequency, duration clearly.
- Never invent values or doctor's instructions not present in the document.
- Reply in the user's language (detected: {language!r}). Keep it focused."""


def document_node(state: AgentState) -> dict:
    messages = state["messages"]
    session_id = state.get("session_id")

    user_msg = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    query = (
        user_msg.content
        if user_msg and isinstance(user_msg.content, str)
        else "summarise the uploaded document"
    )

    tool_trace = list(state.get("last_tool_calls") or [])
    tool_trace.append(
        {
            "tool": "retrieve_documents",
            "status": "running",
            "label": "Reading uploaded document…",
            "args": {"query": query[:120], "scope": "user_uploads"},
        }
    )

    # Look only in user uploads for this session
    rag = get_rag()
    try:
        # Search with a high k so we get most of the uploaded doc
        results = rag.search(query, k=8, session_id=session_id) if session_id else []
        # Filter to only user-upload sources (RAG search merges KB+uploads)
        results = [r for r in results if r["metadata"].get("type") == "user_upload"]
        tool_trace[-1]["status"] = "done"
        tool_trace[-1]["result"] = {
            "ok": True,
            "count": len(results),
            "sources": list({r["metadata"].get("source", "?") for r in results}),
        }
    except Exception as e:  # noqa: BLE001
        log.exception("Document retrieval failed")
        tool_trace[-1]["status"] = "error"
        tool_trace[-1]["result"] = {"ok": False, "error": str(e)}
        results = []

    if not results:
        msg = AIMessage(
            content=(
                "I don't see an uploaded document in this session yet. "
                "Upload a PDF or image using the paperclip button and I'll analyse it."
            )
        )
        return {"messages": [msg], "last_tool_calls": tool_trace}

    context = "\n\n".join(
        f"[{r['metadata'].get('source', 'doc')}]\n{r['text']}" for r in results
    )

    model = get_chat_model()
    response: AIMessage = model.invoke(
        [
            SystemMessage(
                content=_system_prompt(state.get("language") or "en", context)
            ),
            *messages,
        ]
    )
    return {"messages": [response], "last_tool_calls": tool_trace}
