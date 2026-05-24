"""LLM factory — uses Groq.

All agents call get_chat_model() so switching models is just a .env change.
"""
from __future__ import annotations

from typing import Optional

from langchain_groq import ChatGroq

from app.core.config import settings


def get_chat_model(
    *,
    temperature: Optional[float] = None,
    tools: Optional[list] = None,
) -> ChatGroq:
    model = ChatGroq(
        model=settings.LLM_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
    )
    if tools:
        model = model.bind_tools(tools)
    return model