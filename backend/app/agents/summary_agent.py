"""Summary + smalltalk agents.

- summary_node: condenses the conversation so far into a recap. Useful when
  the user says "what have we discussed?" or "summarise this chat".
- smalltalk_node: a thin LLM call for greetings, thanks, and off-topic asks.
  Kept separate so we don't waste tokens on retrieval or tool-binding.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage

from app.agents.llm import get_chat_model
from app.agents.state import AgentState


# ----- Summary -------------------------------------------------------------
def _summary_system(language: str) -> str:
    return f"""You are the Summary Agent. The user asked you to recap or summarise \
the conversation. Produce a short, structured summary covering:
 - The patient's identity (only fields the user actually provided)
 - Any appointments booked / cancelled / discussed (with IDs if available)
 - Healthcare questions answered
 - Outstanding next steps

Reply in the user's language (detected: {language!r}). Keep it under 150 words. \
Do not invent details that weren't part of the conversation."""


def summary_node(state: AgentState) -> dict:
    model = get_chat_model(temperature=0.1)
    response: AIMessage = model.invoke(
        [
            SystemMessage(content=_summary_system(state.get("language") or "en")),
            *state["messages"],
        ]
    )
    tool_trace = list(state.get("last_tool_calls") or [])
    tool_trace.append(
        {
            "tool": "summarize_conversation",
            "status": "done",
            "label": "Summarising conversation…",
            "args": {},
        }
    )
    return {"messages": [response], "last_tool_calls": tool_trace}


# ----- Smalltalk -----------------------------------------------------------
def _smalltalk_system(language: str) -> str:
    return f"""You are the front-desk assistant at Mykare Health. The user has \
sent a greeting, thanks, or off-topic message. Reply warmly and briefly, then \
gently steer them toward what you can help with: booking appointments, \
healthcare questions, or analysing uploaded reports.

Reply in the user's language (detected: {language!r}). Keep it to 1–2 sentences."""


def smalltalk_node(state: AgentState) -> dict:
    model = get_chat_model(temperature=0.5)
    response: AIMessage = model.invoke(
        [
            SystemMessage(content=_smalltalk_system(state.get("language") or "en")),
            *state["messages"],
        ]
    )
    return {"messages": [response]}
