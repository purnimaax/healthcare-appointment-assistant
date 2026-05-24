"""LangGraph workflow.

START → router → appointment | rag | document | summary | smalltalk → END

State is persisted via SqliteSaver so conversations survive restarts.
"""
from __future__ import annotations

import sqlite3
from functools import lru_cache

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.agents.appointment import appointment_node
from app.agents.document_agent import document_node
from app.agents.rag_agent import rag_node
from app.agents.router import route, route_decider
from app.agents.state import AgentState
from app.agents.summary_agent import smalltalk_node, summary_node
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def _build_graph(checkpointer):
    g = StateGraph(AgentState)
    g.add_node("router", route)
    g.add_node("appointment", appointment_node)
    g.add_node("rag", rag_node)
    g.add_node("document", document_node)
    g.add_node("summary", summary_node)
    g.add_node("smalltalk", smalltalk_node)

    g.add_edge(START, "router")
    g.add_conditional_edges("router", route_decider, {
        "appointment": "appointment",
        "rag": "rag",
        "document": "document",
        "summary": "summary",
        "smalltalk": "smalltalk",
    })
    for node in ("appointment", "rag", "document", "summary", "smalltalk"):
        g.add_edge(node, END)

    return g.compile(checkpointer=checkpointer)


@lru_cache
def get_graph():
    # check_same_thread=False needed since FastAPI hits this from multiple threads
    conn = sqlite3.connect(settings.CHECKPOINT_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    log.info("Graph ready, checkpointer at %s", settings.CHECKPOINT_DB_PATH)
    return _build_graph(checkpointer)
