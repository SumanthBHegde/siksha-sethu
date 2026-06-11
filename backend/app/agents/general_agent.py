"""General-purpose agent — answers via Gemini when no specialist matches."""
from __future__ import annotations

from app.agents.state import AgentState
from app.services.gemini_vision import chat_with_gemini
from app.services import analytics


def general_node(state: AgentState) -> AgentState:
    msg = state.get("user_message", "")
    teacher_id = state["teacher_id"]

    # Provide brief school context to Gemini so answers are grounded
    from datetime import date, timedelta
    today = date.today()
    ctx = {
        "attendance_30d": analytics.attendance_summary(teacher_id, today - timedelta(days=30), today),
        "poshan_30d": analytics.poshan_summary(teacher_id, today - timedelta(days=30), today),
        "audit": analytics.audit_readiness(teacher_id),
    }

    system = (
        "You are ShikshaSetu, an AI administrative assistant for Indian government school teachers. "
        "Keep replies concise, practical, and in plain English. "
        "If asked about attendance, PM POSHAN, or audit, use the school context below. "
        "If the question is unrelated to school administration, politely redirect.\n\n"
        f"School context (JSON): {ctx}"
    )
    reply = chat_with_gemini(msg, system=system)
    if not reply or reply.startswith("[Gemini"):
        reply = (
            "I'm your ShikshaSetu assistant. Ask me about:\n"
            "• Attendance summaries and anomalies\n"
            "• PM POSHAN meals and stock\n"
            "• Audit readiness and missing documents\n"
            "Or upload a register image and I'll extract the data."
        )
    return {**state, "agent": "general", "data": {}, "reply": reply}
