"""PM POSHAN specialist agent."""
from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, timedelta

from app.agents.state import AgentState
from app.services import analytics


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
            ym = re.search(r"(19\d{2}|20\d{2})", msg)
            if ym:
                year = int(ym.group(1))
            last_day = monthrange(year, m)[1]
            return date(year, m, 1), date(year, m, last_day)
    if "week" in msg:
        return today - timedelta(days=7), today
    if "today" in msg:
        return today, today
    if "year" in msg:
        return today.replace(month=1, day=1), today
    # Default: current month-to-date
    return today.replace(day=1), today


def poshan_node(state: AgentState) -> AgentState:
    msg = state.get("user_message", "").lower()
    teacher_id = state["teacher_id"]

    if "stock" in msg:
        status = analytics.stock_status(teacher_id)
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

    start, end = _parse_date_range(msg)
    summary = analytics.poshan_summary(teacher_id, start, end)

    if summary["days_recorded"] == 0:
        reply = (
            f"No PM POSHAN records found between {summary['date_range']['start']} and {summary['date_range']['end']}. "
            f"Try a different date range, e.g. 'summary for July 2021' if that's when your data is from."
        )
    else:
        reply = (
            f"PM POSHAN Summary ({summary['date_range']['start']} → {summary['date_range']['end']}):\n"
            f"• Meals served: {summary['meals_served']}\n"
            f"• Beneficiaries: {summary['beneficiaries']}\n"
            f"• Utilization: {summary['utilization_pct']}%\n"
            f"• Rice used: {summary['rice_kg']} kg | Dal: {summary['dal_kg']} kg | Veg: {summary['vegetables_kg']} kg | Oil: {summary['oil_l']} L\n"
            f"• Days recorded: {summary['days_recorded']}"
        )
    return {**state, "agent": "pm_poshan", "data": {"summary": summary}, "reply": reply}
