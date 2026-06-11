"""Analytics queries using MontyDB document queries."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.core.database import (
    get_students_collection,
    get_attendance_collection,
    get_meal_collection,
    get_stock_collection,
    get_audit_collection,
    get_extracted_data_collection
)


def attendance_summary(teacher_id: str, start: date, end: date) -> dict[str, Any]:
    """Calculate attendance summary for a date range using MontyDB."""
    students_col = get_students_collection()
    attendance_col = get_attendance_collection()
    
    # Count total students for this teacher
    total_students = len(list(students_col.find({"teacher_id": teacher_id})))
    
    # Count attendance records by status in date range
    start_str = start.isoformat()
    end_str = end.isoformat()
    
    records = list(attendance_col.find({
        "teacher_id": teacher_id,
        "date": {"$gte": start_str, "$lte": end_str}
    }))
    
    # Calculate counts by status
    counts = {"present": 0, "absent": 0, "late": 0}
    for record in records:
        status = record.get("status", "absent")
        if status in counts:
            counts[status] += 1
    
    present = counts["present"]
    absent = counts["absent"]
    late = counts["late"]
    total_marked = present + absent + late
    pct = round((present / total_marked) * 100, 2) if total_marked else 0.0
    
    return {
        "total_students": total_students,
        "date_range": {"start": start_str, "end": end_str},
        "present": present,
        "absent": absent,
        "late": late,
        "total_marked": total_marked,
        "attendance_percentage": pct,
    }


def attendance_anomalies(teacher_id: str, threshold_pct: float = 75.0) -> list[dict]:
    """Find students with attendance below threshold using MontyDB."""
    students_col = get_students_collection()
    attendance_col = get_attendance_collection()
    
    end = date.today()
    start = end - timedelta(days=30)
    start_str = start.isoformat()
    end_str = end.isoformat()
    
    # Get all students for this teacher
    students = {s["id"]: s for s in students_col.find({"teacher_id": teacher_id})}
    
    # Get attendance records in date range
    attendance_records = list(attendance_col.find({
        "teacher_id": teacher_id,
        "date": {"$gte": start_str, "$lte": end_str}
    }))
    
    # Aggregate by student_id
    student_stats = {}
    for record in attendance_records:
        sid = record.get("student_id")
        if sid not in student_stats:
            student_stats[sid] = {"present": 0, "total": 0}
        student_stats[sid]["total"] += 1
        if record.get("status") == "present":
            student_stats[sid]["present"] += 1
    
    # Calculate attendance percentages and find anomalies
    anomalies = []
    for sid, stats in student_stats.items():
        if sid not in students:
            continue
        student = students[sid]
        total = stats["total"]
        present = stats["present"]
        pct = (present / total * 100) if total else 0
        
        if pct < threshold_pct:
            anomalies.append({
                "student_id": sid,
                "name": student.get("name"),
                "roll_no": student.get("roll_no"),
                "attendance_pct": round(pct, 2),
                "present_days": present,
                "total_days": total,
            })
    
    return sorted(anomalies, key=lambda x: x["attendance_pct"])


def poshan_summary(teacher_id: str, start: date, end: date) -> dict[str, Any]:
    """Calculate PM Poshan meal summary for a date range using MontyDB."""
    meal_col = get_meal_collection()
    
    start_str = start.isoformat()
    end_str = end.isoformat()
    
    # Query meals in date range
    records = list(meal_col.find({
        "teacher_id": teacher_id,
        "date": {"$gte": start_str, "$lte": end_str}
    }))
    
    # Aggregate values
    served = sum(r.get("meals_served", 0) for r in records)
    beneficiaries = sum(r.get("beneficiaries", 0) for r in records)
    rice = sum(r.get("rice_kg", 0.0) for r in records)
    dal = sum(r.get("dal_kg", 0.0) for r in records)
    veg = sum(r.get("vegetables_kg", 0.0) for r in records)
    oil = sum(r.get("oil_l", 0.0) for r in records)
    days = len(records)
    
    util = round(served / beneficiaries * 100, 2) if beneficiaries else 0.0
    
    return {
        "date_range": {"start": start_str, "end": end_str},
        "meals_served": served,
        "beneficiaries": beneficiaries,
        "utilization_pct": util,
        "rice_kg": float(rice),
        "dal_kg": float(dal),
        "vegetables_kg": float(veg),
        "oil_l": float(oil),
        "days_recorded": days,
    }


def stock_status(teacher_id: str) -> dict[str, Any]:
    """Get latest stock status for each item using MontyDB."""
    stock_col = get_stock_collection()
    
    # Get all stock records for this teacher
    all_records = list(stock_col.find({"teacher_id": teacher_id}))
    
    # Group by item and get the latest record for each
    latest_by_item = {}
    for record in all_records:
        item = record.get("item", "")
        record_date = record.get("date", "")
        
        if item not in latest_by_item or record_date > latest_by_item[item]["date"]:
            latest_by_item[item] = record
    
    # Format output
    items = []
    alerts = []
    LOW = {"rice": 10.0, "dal": 5.0, "oil": 2.0, "vegetables": 3.0}
    
    for item, record in latest_by_item.items():
        item_data = {
            "item": item,
            "closing_kg": record.get("closing_kg", 0.0),
            "as_of": record.get("date"),
        }
        items.append(item_data)
        
        thresh = LOW.get(item.lower(), 5.0)
        closing = record.get("closing_kg", 0.0)
        if closing < thresh:
            alerts.append({
                "item": item,
                "closing_kg": closing,
                "threshold": thresh
            })
    
    return {"items": items, "low_stock_alerts": alerts}


def audit_readiness(teacher_id: str) -> dict[str, Any]:
    """Compute audit readiness score based on recent activity + documents."""
    students_col = get_students_collection()
    attendance_col = get_attendance_collection()
    meal_col = get_meal_collection()
    stock_col = get_stock_collection()
    audit_col = get_audit_collection()
    
    today = date.today()
    last_30 = today - timedelta(days=30)
    last_30_str = last_30.isoformat()
    
    # Count unique attendance days in last 30 days
    attendance_records = list(attendance_col.find({
        "teacher_id": teacher_id,
        "date": {"$gte": last_30_str}
    }))
    attendance_days = len(set(r.get("date") for r in attendance_records))
    
    # Count unique meal days in last 30 days
    meal_records = list(meal_col.find({
        "teacher_id": teacher_id,
        "date": {"$gte": last_30_str}
    }))
    meal_days = len(set(r.get("date") for r in meal_records))
    
    # Count unique stock items
    stock_records = list(stock_col.find({"teacher_id": teacher_id}))
    stock_items = len(set(r.get("item") for r in stock_records))
    
    # Get uploaded audit documents
    docs = list(audit_col.find({"teacher_id": teacher_id}))
    required = {"attendance_summary", "stock_summary", "meal_summary", "compliance_certificate"}
    have = {d.get("doc_type") for d in docs}
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
        "documents_uploaded": [
            {
                "doc_type": d.get("doc_type"),
                "title": d.get("title"),
                "uploaded_at": d.get("uploaded_at")
            }
            for d in docs
        ],
        "recommendations": recommendations,
    }


def recent_uploads(teacher_id: str, limit: int = 5) -> list[dict]:
    """Get recent uploaded extracted register data using MontyDB."""
    extracted_col = get_extracted_data_collection()
    
    # Get all records for this teacher
    records = list(extracted_col.find({"teacher_id": teacher_id}))
    
    # Sort by created_at descending and take limit
    records.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    records = records[:limit]
    
    return [
        {
            "id": r.get("id"),
            "register_type": r.get("register_type"),
            "validation_status": r.get("validation_status"),
            "created_at": r.get("created_at"),
        }
        for r in records
    ]
