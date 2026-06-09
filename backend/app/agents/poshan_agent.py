"""PM POSHAN specialist agent."""
from __future__ import annotations

from datetime import date, timedelta

from app.agents.state import AgentState
from app.core.database import SessionLocal
from app.services import analytics


def poshan_node(state: AgentState) -> AgentState:
    msg = state.get("user_message", "").lower()
    teacher_id = state["teacher_id"]
    db = SessionLocal()
    try:
        if "stock" in msg:
            status = analytics.stock_status(db, teacher_id)
            if not status["items"]:
                reply = "No stock records found. Upload a stock register or add records to track inventory."
            else:
                lines = [f"• {i['item']}: {i['closing_kg']} kg (as of {i['as_of']})" for i in status["items"]]
                reply = "Current PM POSHAN Stock:\n" + "\n".join(lines)
                if status["low_stock_alerts"]:
                    alerts = "\n".join(
                        f"  ⚠ {a['item']}: only {a['closing_kg']} kg (threshold {a['threshold']} kg)"
                        for a in status["low_stock_alerts"]
                    )
                    reply += "\n\nLow stock alerts:\n" + alerts
            return {**state, "agent": "pm_poshan", "data": status, "reply": reply}

        # Default: monthly meal summary
        today = date.today()
        start = today.replace(day=1)
        summary = analytics.poshan_summary(db, teacher_id, start, today)
        reply = (
            f"PM POSHAN Summary ({summary['date_range']['start']} → {summary['date_range']['end']}):\n"
            f"• Meals served: {summary['meals_served']}\n"
            f"• Beneficiaries: {summary['beneficiaries']}\n"
            f"• Utilization: {summary['utilization_pct']}%\n"
            f"• Rice used: {summary['rice_kg']} kg | Dal: {summary['dal_kg']} kg | Veg: {summary['vegetables_kg']} kg | Oil: {summary['oil_l']} L\n"
            f"• Days recorded: {summary['days_recorded']}"
        )
        return {**state, "agent": "pm_poshan", "data": {"summary": summary}, "reply": reply}
    finally:
        db.close()
