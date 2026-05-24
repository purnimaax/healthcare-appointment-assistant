from __future__ import annotations

from datetime import date, timedelta

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from app.agents.llm import get_chat_model
from app.agents.state import AgentState
from app.core.logging import get_logger
from app.tools.registry import APPOINTMENT_TOOLS

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


def _system_prompt(language: str) -> str:
    today = date.today()
    return f"""You are the Appointment Agent at Mykare Health.

TODAY: {today.isoformat()} ({today.strftime('%A')}). Booking window: up to {(today + timedelta(days=14)).isoformat()}.

Help with: checking slots, booking, cancelling, rescheduling, viewing history.

Before booking you need: name, phone or email, department, date, time. Ask for missing info one thing at a time.
Never make up details. Always call fetch_slots before booking. Always include appointment_id in confirmations.

IMPORTANT: You MUST reply in {_LANG_MAP.get(language, f"the same language as the user ({language})")}. Do not switch to English."""

def appointment_node(state: AgentState) -> dict:
    model = get_chat_model(tools=APPOINTMENT_TOOLS)
    sys = SystemMessage(content=_system_prompt(state.get("language") or "en"))
    history = list(state["messages"])
    tool_trace = list(state.get("last_tool_calls") or [])
    new_msgs: list = []
    tool_map = {t.name: t for t in APPOINTMENT_TOOLS}

    for _ in range(6):
        response: AIMessage = model.invoke([sys, *history, *new_msgs])
        new_msgs.append(response)

        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            break

        for tc in tool_calls:
            name, args = tc["name"], tc.get("args", {}) or {}
            log.info("appointment calling %s %s", name, args)
            tool_trace.append({"tool": name, "status": "running", "label": _label(name), "args": args})
            try:
                result = tool_map[name].invoke(args)
            except Exception as e:  # noqa: BLE001
                result = {"ok": False, "error": str(e)}
            tool_trace[-1]["status"] = "done" if result.get("ok") else "error"
            tool_trace[-1]["result"] = result
            new_msgs.append(ToolMessage(content=str(result), tool_call_id=tc["id"], name=name))

    return {"messages": new_msgs, "last_tool_calls": tool_trace}


def _label(name: str) -> str:
    return {
        "fetch_slots": "Fetching available slots…",
        "book_appointment": "Booking appointment…",
        "cancel_appointment": "Cancelling appointment…",
        "modify_appointment": "Rescheduling appointment…",
        "retrieve_appointments": "Retrieving appointments…",
        "list_departments": "Listing departments…",
    }.get(name, f"Running {name}…")
