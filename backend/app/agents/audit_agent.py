"""Audit specialist agent."""
from __future__ import annotations

from app.agents.state import AgentState
from app.core.database import SessionLocal
from app.services import analytics


def audit_node(state: AgentState) -> AgentState:
    teacher_id = state["teacher_id"]
    db = SessionLocal()
    try:
        readiness = analytics.audit_readiness(db, teacher_id)
        score = readiness["readiness_score"]
        emoji = "✅" if score >= 80 else ("⚠" if score >= 50 else "❌")
        lines = [
            f"Audit Readiness: {emoji} {score}/100",
            f"• Attendance days (last 30): {readiness['attendance_days_30']}",
            f"• Meal days recorded (last 30): {readiness['meal_days_30']}",
            f"• Stock items tracked: {readiness['stock_items_tracked']}",
        ]
        if readiness["missing_documents"]:
            lines.append(f"• Missing documents: {', '.join(readiness['missing_documents'])}")
        if readiness["recommendations"]:
            lines.append("\nRecommendations:")
            lines.extend(f"  → {r}" for r in readiness["recommendations"])
        reply = "\n".join(lines)
        return {**state, "agent": "audit", "data": readiness, "reply": reply}
    finally:
        db.close()
