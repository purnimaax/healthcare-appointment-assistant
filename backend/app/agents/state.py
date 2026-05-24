"""Shared state for the LangGraph workflow."""
from __future__ import annotations

from typing import Annotated, Literal, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

# Intent classifications produced by the router
Intent = Literal[
    "appointment",  # Anything about booking / cancelling / rescheduling / listing slots
    "rag",          # Healthcare information / FAQ questions
    "document",     # Talking about an uploaded document/image
    "summary",      # Summarise the conversation
    "smalltalk",    # Greetings, thanks, off-topic — handled with a direct reply
]


class AgentState(TypedDict, total=False):
    """State passed between LangGraph nodes.

    - messages: full chat history (LangGraph appends via add_messages reducer)
    - intent: set by the router
    - language: detected language code (e.g. "en", "hi") — used for response
    - session_id: passed through so the RAG agent can scope user-uploads
    - last_tool_calls: a UI-friendly trace of tool calls made this turn
    """

    messages: Annotated[list[AnyMessage], add_messages]
    intent: Optional[Intent]
    language: Optional[str]
    session_id: Optional[str]
    last_tool_calls: list[dict]
