"""LangGraph shared state for ShikshaSetu agents."""
from __future__ import annotations
from typing import TypedDict, Any, Literal


class AgentState(TypedDict, total=False):
    teacher_id: int
    user_message: str
    intent: Literal["attendance", "pm_poshan", "audit", "general"]
    agent: str
    data: dict[str, Any]
    reply: str
