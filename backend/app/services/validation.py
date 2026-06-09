"""Validation layer between Gemini-extracted JSON and database insertion."""
from __future__ import annotations
from typing import Any


def validate_attendance(data: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if data.get("register_type") != "attendance":
        issues.append("register_type mismatch")
    entries = data.get("entries", [])
    if not isinstance(entries, list) or not entries:
        issues.append("no entries extracted")
    for i, e in enumerate(entries or []):
        if not e.get("roll_no") and not e.get("name"):
            issues.append(f"row {i}: missing roll_no and name")
        if e.get("status") not in {"present", "absent", "late"}:
            issues.append(f"row {i}: invalid status '{e.get('status')}'")
    return (len(issues) == 0, issues)


def validate_poshan(data: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if data.get("register_type") != "pm_poshan":
        issues.append("register_type mismatch")
    if not isinstance(data.get("meals_served"), int):
        issues.append("meals_served not an integer")
    if not isinstance(data.get("beneficiaries"), int):
        issues.append("beneficiaries not an integer")
    served = data.get("meals_served") or 0
    benef = data.get("beneficiaries") or 0
    if served and benef and served > benef * 1.05:
        issues.append(f"meals_served ({served}) > beneficiaries ({benef}) — possible over-reporting")
    return (len(issues) == 0, issues)


def validate_stock(data: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if data.get("register_type") != "stock":
        issues.append("register_type mismatch")
    items = data.get("items", [])
    if not isinstance(items, list) or not items:
        issues.append("no items extracted")
    for i, it in enumerate(items or []):
        opening = float(it.get("opening_kg") or 0)
        received = float(it.get("received_kg") or 0)
        consumed = float(it.get("consumed_kg") or 0)
        closing = float(it.get("closing_kg") or 0)
        expected = opening + received - consumed
        if abs(expected - closing) > 0.5:
            issues.append(f"item {it.get('item')}: closing mismatch (expected {expected:.2f}, got {closing:.2f})")
    return (len(issues) == 0, issues)


VALIDATORS = {
    "attendance": validate_attendance,
    "pm_poshan": validate_poshan,
    "stock": validate_stock,
}


def validate(register_type: str, data: dict[str, Any]) -> tuple[bool, list[str]]:
    fn = VALIDATORS.get(register_type.lower().replace("-", "_"))
    if not fn:
        return True, []
    return fn(data)
