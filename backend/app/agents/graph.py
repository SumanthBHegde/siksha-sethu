"""LangGraph workflow assembling Supervisor → specialist agents."""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.supervisor import supervisor_node
from app.agents.attendance_agent import attendance_node
from app.agents.poshan_agent import poshan_node
from app.agents.audit_agent import audit_node
from app.agents.general_agent import general_node


def _route(state: AgentState) -> str:
    intent = state.get("intent", "general")
    return {
        "attendance": "attendance",
        "pm_poshan": "pm_poshan",
        "audit": "audit",
        "general": "general",
    }.get(intent, "general")


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("attendance", attendance_node)
    g.add_node("pm_poshan", poshan_node)
    g.add_node("audit", audit_node)
    g.add_node("general", general_node)

    g.set_entry_point("supervisor")
    g.add_conditional_edges(
        "supervisor",
        _route,
        {
            "attendance": "attendance",
            "pm_poshan": "pm_poshan",
            "audit": "audit",
            "general": "general",
        },
    )
    g.add_edge("attendance", END)
    g.add_edge("pm_poshan", END)
    g.add_edge("audit", END)
    g.add_edge("general", END)
    return g.compile()


# Singleton compiled graph
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_agent(teacher_id: int, message: str) -> dict:
    graph = get_graph()
    result = graph.invoke({"teacher_id": teacher_id, "user_message": message})
    return {
        "reply": result.get("reply", ""),
        "agent": result.get("agent", "supervisor"),
        "intent": result.get("intent", "general"),
        "data": result.get("data", {}),
    }
