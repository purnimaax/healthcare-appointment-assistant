"""Router — figures out intent and language from the user's message.

Structured output means we get a typed object back, not raw text we'd have to parse.
"""
from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.llm import get_chat_model
from app.agents.state import AgentState, Intent
from app.core.logging import get_logger

log = get_logger(__name__)


class RouterDecision(BaseModel):
    intent: Literal["appointment", "rag", "document", "summary", "smalltalk"] = Field(
        ...,
        description=(
            "appointment = booking/cancelling/rescheduling/slots. "
            "rag = general healthcare questions, insurance, FAQs. "
            "document = user asking about something they uploaded. "
            "summary = user wants a recap. "
            "smalltalk = greetings, thanks, off-topic."
        ),
    )
    language: str = Field(
        ...,
        description="ISO 639-1 code. 'en', 'hi' for Hindi, 'ml' for Malayalam. Pick dominant one for mixed.",
    )
    reasoning: str = Field(..., description="One sentence explaining the call.")


ROUTER_SYSTEM = (
    "You're the routing layer of a healthcare assistant. "
    "Pick exactly one intent for the user's latest message. "
    "Default to 'rag' for health questions, 'appointment' for anything about booking or slots."
)


def route(state: AgentState) -> dict:
    messages = state["messages"]
    if not messages:
        return {"intent": "smalltalk", "language": "en"}

    model = get_chat_model(temperature=0.0).with_structured_output(RouterDecision)

    recent = messages[-6:]
    convo = "\n".join(f"{getattr(m, 'type', 'msg').upper()}: {m.content}" for m in recent)

    decision: RouterDecision = model.invoke([
        SystemMessage(content=ROUTER_SYSTEM),
        HumanMessage(content=f"Conversation:\n{convo}\n\nClassify the latest message."),
    ])

    log.info("Router → %s (%s) — %s", decision.intent, decision.language, decision.reasoning)
    return {
        "intent": decision.intent,
        "language": decision.language,
        "last_tool_calls": [{
            "tool": "router",
            "status": "done",
            "label": f"Routed to {decision.intent} agent",
            "args": {"intent": decision.intent, "language": decision.language},
        }],
    }


def route_decider(state: AgentState) -> Intent:
    return state.get("intent", "smalltalk")  # type: ignore[return-value]
