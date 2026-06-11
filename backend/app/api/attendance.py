from fastapi import APIRouter, Depends, HTTPException
from datetime import date, timedelta
from typing import Optional

from app.core.database import get_students_collection, get_attendance_collection
from app.core.security import get_current_user
from app.models.attendance import AttendanceRecord
from app.schemas.attendance import AttendanceBulkIn
from app.services import analytics

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.post("/bulk")
def upsert_bulk(body: AttendanceBulkIn, current = Depends(get_current_user)):
    """Bulk upsert attendance records using MontyDB."""
    students_col = get_students_collection()
    attendance_col = get_attendance_collection()
    current_id = current.get("id")
    
    # Get set of valid student IDs for this teacher
    students = students_col.find({"teacher_id": current_id})
    student_ids = {s["id"] for s in students}
    
    saved = 0
    date_str = body.date.isoformat()
    
    for entry in body.entries:
        # Skip if student doesn't belong to this teacher
        if entry.student_id not in student_ids:
            continue
        
        # Check if attendance record already exists
        existing = attendance_col.find_one({
            "student_id": entry.student_id,
            "date": date_str,
        })
        
        if existing:
            # Update existing record
            attendance_col.update_one(
                {"id": existing["id"]},
                {"$set": {"status": entry.status}}
            )
        else:
            # Create new attendance record
            record = AttendanceRecord(
                student_id=entry.student_id,
                teacher_id=current_id,
                date=body.date,
                status=entry.status,
            )
            attendance_col.insert_one(record.model_dump(mode="json"))
        
        saved += 1
    
    return {"saved": saved, "date": date_str}


@router.get("/summary")
def summary(
    start: Optional[date] = None,
    end: Optional[date] = None,
    current = Depends(get_current_user),
):
    """Get attendance summary for a date range using MontyDB."""
    current_id = current.get("id")
    end = end or date.today()
    start = start or (end - timedelta(days=30))
    return analytics.attendance_summary(current_id, start, end)


@router.get("/anomalies")
def anomalies(current = Depends(get_current_user)):
    """Get attendance anomalies (low attendance students) using MontyDB."""
    current_id = current.get("id")
    return {"anomalies": analytics.attendance_anomalies(current_id)}


@router.get("/by-date")
def by_date(d: date, current = Depends(get_current_user)):
    """Get attendance records for a specific date using MontyDB."""
    students_col = get_students_collection()
    attendance_col = get_attendance_collection()
    current_id = current.get("id")
    
    # Get all students for this teacher
    students_map = {s["id"]: s for s in students_col.find({"teacher_id": current_id})}
    
    # Get attendance records for this date
    date_str = d.isoformat()
    attendance_records = attendance_col.find({
        "teacher_id": current_id,
        "date": date_str
    })
    
    # Join with student data
    result = []
    for record in attendance_records:
        student = students_map.get(record.get("student_id"))
        if student:
            result.append({
                "student_id": student["id"],
                "name": student["name"],
                "roll_no": student["roll_no"],
                "status": record.get("status"),
                "source": record.get("source"),
            })
    
    return result
