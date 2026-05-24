from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.llm import get_chat_model
from app.agents.state import AgentState
from app.core.logging import get_logger
from app.services.rag import get_rag

log = get_logger(__name__)

_LANG_MAP = {
    "hi": "Hindi (use Devanagari script or Roman Hindi, whichever the user used)",
    "ml": "Malayalam script",
    "ta": "Tamil script",
    "te": "Telugu script",
    "kn": "Kannada script",
}

def _lang_instruction(language: str) -> str:
    lang = _LANG_MAP.get(language, f"the same language as the user ({language})")
    return f"IMPORTANT: You MUST reply in {lang}. Do not switch to English."


def _system_prompt(language: str, context: str) -> str:
    return f"""You are the Information Agent at Mykare Health.
Answer using ONLY the context below. If it doesn't cover the question, say so and suggest booking a consultation.

CONTEXT:
---
{context}
---

- Stick to what's in the context, mention source files when useful
- No diagnosis or dosage advice — refer to a doctor for that
- Reply in the user's language ({language!r})
- Keep it short, 4-6 sentences
- {_lang_instruction(language)}"""


def rag_node(state: AgentState) -> dict:
    messages = state["messages"]
    if not messages:
        return {}

    user_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    if not user_msg:
        return {}

    query = user_msg.content if isinstance(user_msg.content, str) else str(user_msg.content)
    session_id = state.get("session_id")

    tool_trace = list(state.get("last_tool_calls") or [])
    tool_trace.append({
        "tool": "retrieve_documents",
        "status": "running",
        "label": "Searching knowledge base…",
        "args": {"query": query[:120]},
    })

    try:
        results = get_rag().search(query, k=4, session_id=session_id)
        tool_trace[-1]["status"] = "done"
        tool_trace[-1]["result"] = {
            "ok": True,
            "count": len(results),
            "sources": list({r["metadata"].get("source", "?") for r in results}),
        }
    except Exception as e:  # noqa: BLE001
        log.exception("RAG retrieval failed")
        tool_trace[-1]["status"] = "error"
        tool_trace[-1]["result"] = {"ok": False, "error": str(e)}
        results = []

    context = "\n\n".join(
        f"[{r['metadata'].get('source', 'unknown')}]\n{r['text']}" for r in results
    ) or "(no relevant context found)"

    response: AIMessage = get_chat_model().invoke([
        SystemMessage(content=_system_prompt(state.get("language") or "en", context)),
        *messages,
    ])

    return {"messages": [response], "last_tool_calls": tool_trace}
