"""Analytics queries used by dashboards and agents."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models import (
    Student, AttendanceRecord, MealRecord, StockRecord, AuditDocument
)


def attendance_summary(db: Session, teacher_id: int, start: date, end: date) -> dict[str, Any]:
    total_students = db.query(func.count(Student.id)).filter(Student.teacher_id == teacher_id).scalar() or 0
    rows = (
        db.query(AttendanceRecord.status, func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.teacher_id == teacher_id,
            AttendanceRecord.date >= start,
            AttendanceRecord.date <= end,
        )
        .group_by(AttendanceRecord.status)
        .all()
    )
    counts = {s: c for s, c in rows}
    present = counts.get("present", 0)
    absent = counts.get("absent", 0)
    late = counts.get("late", 0)
    total_marked = present + absent + late
    pct = round((present / total_marked) * 100, 2) if total_marked else 0.0
    return {
        "total_students": total_students,
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "present": present,
        "absent": absent,
        "late": late,
        "total_marked": total_marked,
        "attendance_percentage": pct,
    }


def attendance_anomalies(db: Session, teacher_id: int, threshold_pct: float = 75.0) -> list[dict]:
    end = date.today()
    start = end - timedelta(days=30)
    rows = (
        db.query(
            Student.id, Student.name, Student.roll_no,
            func.sum(case((AttendanceRecord.status == "present", 1), else_=0)).label("p"),
            func.count(AttendanceRecord.id).label("total"),
        )
        .join(AttendanceRecord, AttendanceRecord.student_id == Student.id)
        .filter(
            Student.teacher_id == teacher_id,
            AttendanceRecord.date >= start,
            AttendanceRecord.date <= end,
        )
        .group_by(Student.id)
        .all()
    )
    out = []
    for sid, name, roll, p, total in rows:
        pct = (p or 0) / total * 100 if total else 0
        if pct < threshold_pct:
            out.append({
                "student_id": sid, "name": name, "roll_no": roll,
                "attendance_pct": round(pct, 2),
                "present_days": p or 0, "total_days": total,
            })
    return sorted(out, key=lambda x: x["attendance_pct"])


def poshan_summary(db: Session, teacher_id: int, start: date, end: date) -> dict[str, Any]:
    rows = db.query(
        func.coalesce(func.sum(MealRecord.meals_served), 0),
        func.coalesce(func.sum(MealRecord.beneficiaries), 0),
        func.coalesce(func.sum(MealRecord.rice_kg), 0.0),
        func.coalesce(func.sum(MealRecord.dal_kg), 0.0),
        func.coalesce(func.sum(MealRecord.vegetables_kg), 0.0),
        func.coalesce(func.sum(MealRecord.oil_l), 0.0),
        func.count(MealRecord.id),
    ).filter(
        MealRecord.teacher_id == teacher_id,
        MealRecord.date >= start,
        MealRecord.date <= end,
    ).first()
    served, beneficiaries, rice, dal, veg, oil, days = rows or (0, 0, 0, 0, 0, 0, 0)
    util = round(served / beneficiaries * 100, 2) if beneficiaries else 0.0
    return {
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "meals_served": served,
        "beneficiaries": beneficiaries,
        "utilization_pct": util,
        "rice_kg": float(rice or 0),
        "dal_kg": float(dal or 0),
        "vegetables_kg": float(veg or 0),
        "oil_l": float(oil or 0),
        "days_recorded": days,
    }


def stock_status(db: Session, teacher_id: int) -> dict[str, Any]:
    sub = (
        db.query(
            StockRecord.item,
            func.max(StockRecord.date).label("latest"),
        )
        .filter(StockRecord.teacher_id == teacher_id)
        .group_by(StockRecord.item)
        .subquery()
    )
    rows = (
        db.query(StockRecord)
        .join(sub, (StockRecord.item == sub.c.item) & (StockRecord.date == sub.c.latest))
        .filter(StockRecord.teacher_id == teacher_id)
        .all()
    )
    items = []
    alerts = []
    LOW = {"rice": 10.0, "dal": 5.0, "oil": 2.0, "vegetables": 3.0}
    for r in rows:
        item = {
            "item": r.item,
            "closing_kg": r.closing_kg,
            "as_of": r.date.isoformat(),
        }
        items.append(item)
        thresh = LOW.get(r.item.lower(), 5.0)
        if r.closing_kg < thresh:
            alerts.append({"item": r.item, "closing_kg": r.closing_kg, "threshold": thresh})
    return {"items": items, "low_stock_alerts": alerts}


def audit_readiness(db: Session, teacher_id: int) -> dict[str, Any]:
    """Compute a simple readiness score based on recent activity + required docs."""
    today = date.today()
    last_30 = today - timedelta(days=30)

    attendance_days = db.query(func.count(func.distinct(AttendanceRecord.date))).filter(
        AttendanceRecord.teacher_id == teacher_id,
        AttendanceRecord.date >= last_30,
    ).scalar() or 0

    meal_days = db.query(func.count(func.distinct(MealRecord.date))).filter(
        MealRecord.teacher_id == teacher_id,
        MealRecord.date >= last_30,
    ).scalar() or 0

    stock_items = db.query(func.count(func.distinct(StockRecord.item))).filter(
        StockRecord.teacher_id == teacher_id,
    ).scalar() or 0

    docs = db.query(AuditDocument).filter(AuditDocument.teacher_id == teacher_id).all()
    required = {"attendance_summary", "stock_summary", "meal_summary", "compliance_certificate"}
    have = {d.doc_type for d in docs}
    missing = sorted(required - have)

    # Weighted score
    score = 0
    score += min(attendance_days / 22, 1.0) * 30  # 30 pts for daily attendance
    score += min(meal_days / 22, 1.0) * 30        # 30 pts for daily meals
    score += min(stock_items / 4, 1.0) * 15       # 15 pts for stock tracking
    score += (len(required) - len(missing)) / len(required) * 25  # 25 pts for documents
    score = round(score, 1)

    recommendations = []
    if attendance_days < 20:
        recommendations.append(f"Only {attendance_days} days of attendance in last 30. Update daily.")
    if meal_days < 20:
        recommendations.append(f"Only {meal_days} days of PM POSHAN meals recorded. Update daily.")
    if missing:
        recommendations.append(f"Upload missing documents: {', '.join(missing)}")
    if stock_items < 4:
        recommendations.append("Track stock for at least rice, dal, oil, vegetables.")

    return {
        "readiness_score": score,
        "attendance_days_30": attendance_days,
        "meal_days_30": meal_days,
        "stock_items_tracked": stock_items,
        "missing_documents": missing,
        "documents_uploaded": [{"doc_type": d.doc_type, "title": d.title, "uploaded_at": d.uploaded_at.isoformat()} for d in docs],
        "recommendations": recommendations,
    }


def recent_uploads(db: Session, teacher_id: int, limit: int = 5) -> list[dict]:
    from app.models import ExtractedRegisterData
    rows = (
        db.query(ExtractedRegisterData)
        .filter(ExtractedRegisterData.teacher_id == teacher_id)
        .order_by(ExtractedRegisterData.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "register_type": r.register_type,
            "validation_status": r.validation_status,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
