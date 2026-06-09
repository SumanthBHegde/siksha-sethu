from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, timedelta
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import AttendanceRecord, Student, User
from app.schemas.attendance import AttendanceBulkIn
from app.services import analytics

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.post("/bulk")
def upsert_bulk(body: AttendanceBulkIn, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    student_ids = {s.id for s in db.query(Student.id).filter(Student.teacher_id == current.id).all()}
    saved = 0
    for entry in body.entries:
        if entry.student_id not in student_ids:
            continue
        existing = db.query(AttendanceRecord).filter(
            and_(
                AttendanceRecord.student_id == entry.student_id,
                AttendanceRecord.date == body.date,
            )
        ).first()
        if existing:
            existing.status = entry.status
        else:
            db.add(AttendanceRecord(
                student_id=entry.student_id,
                teacher_id=current.id,
                date=body.date,
                status=entry.status,
            ))
        saved += 1
    db.commit()
    return {"saved": saved, "date": body.date.isoformat()}


@router.get("/summary")
def summary(
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    end = end or date.today()
    start = start or (end - timedelta(days=30))
    return analytics.attendance_summary(db, current.id, start, end)


@router.get("/anomalies")
def anomalies(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return {"anomalies": analytics.attendance_anomalies(db, current.id)}


@router.get("/by-date")
def by_date(d: date, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rows = (
        db.query(AttendanceRecord, Student)
        .join(Student, AttendanceRecord.student_id == Student.id)
        .filter(AttendanceRecord.teacher_id == current.id, AttendanceRecord.date == d)
        .all()
    )
    return [
        {
            "student_id": s.id, "name": s.name, "roll_no": s.roll_no,
            "status": a.status, "source": a.source,
        }
        for a, s in rows
    ]
