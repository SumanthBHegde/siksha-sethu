"""Attendance specialist agent."""
from __future__ import annotations

import re
from datetime import date, timedelta
from calendar import monthrange

from app.agents.state import AgentState
from app.services import analytics
from app.services.gemini_vision import chat_with_gemini


MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_date_range(message: str) -> tuple[date, date]:
    msg = message.lower()
    today = date.today()
    for name, m in MONTHS.items():
        if re.search(rf"\b{name}\b", msg):
            year = today.year
            ym = re.search(r"(20\d{2})", msg)
            if ym:
                year = int(ym.group(1))
            last_day = monthrange(year, m)[1]
            return date(year, m, 1), date(year, m, last_day)
    if "week" in msg:
        return today - timedelta(days=7), today
    if "today" in msg:
        return today, today
    # Default: last 30 days
    return today - timedelta(days=30), today


def _format_summary(s: dict) -> str:
    return (
        f"Attendance Summary ({s['date_range']['start']} → {s['date_range']['end']}):\n"
        f"• Total students: {s['total_students']}\n"
        f"• Present: {s['present']} | Absent: {s['absent']} | Late: {s['late']}\n"
        f"• Attendance: {s['attendance_percentage']}%"
    )


def attendance_node(state: AgentState) -> AgentState:
    msg = state.get("user_message", "")
    teacher_id = state["teacher_id"]
    msg_l = msg.lower()

    if "anomal" in msg_l or "low attendance" in msg_l or "missing" in msg_l:
        anomalies = analytics.attendance_anomalies(teacher_id)
        if not anomalies:
            reply = "No attendance anomalies detected. All students have ≥75% attendance over the last 30 days."
        else:
            lines = [
                f"• {a['name']} (Roll {a['roll_no']}): {a['attendance_pct']}% — {a['present_days']}/{a['total_days']} days"
                for a in anomalies[:10]
            ]
            reply = f"Found {len(anomalies)} students with attendance anomalies (<75%):\n" + "\n".join(lines)
        return {**state, "agent": "attendance", "data": {"anomalies": anomalies}, "reply": reply}

    start, end = _parse_date_range(msg)
    summary = analytics.attendance_summary(teacher_id, start, end)
    reply = _format_summary(summary)
    return {**state, "agent": "attendance", "data": {"summary": summary}, "reply": reply}
