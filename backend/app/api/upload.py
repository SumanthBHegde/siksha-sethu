"""Register image upload + Gemini Vision extraction + DB persistence."""
from __future__ import annotations

import json
from datetime import datetime, date as date_cls
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models import (
    User, Student, AttendanceRecord, MealRecord, StockRecord,
    ExtractedRegisterData, AuditDocument,
)
from app.services import gemini_vision, validation

router = APIRouter(prefix="/api/upload", tags=["upload"])
settings = get_settings()


def _save_upload(file: UploadFile, teacher_id: int, register_type: str) -> Path:
    upload_dir = Path(settings.UPLOAD_DIR) / register_type / str(teacher_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{stamp}_{file.filename}"
    out_path = upload_dir / safe_name
    return out_path


def _persist_attendance(db: Session, teacher_id: int, data: dict) -> dict:
    entries = data.get("entries", [])
    d_str = data.get("date")
    try:
        target_date = date_cls.fromisoformat(d_str) if d_str else date_cls.today()
    except (TypeError, ValueError):
        target_date = date_cls.today()

    students_by_roll = {
        s.roll_no.strip().lower(): s
        for s in db.query(Student).filter(Student.teacher_id == teacher_id).all()
    }
    students_by_name = {s.name.strip().lower(): s for s in students_by_roll.values()}

    # 1) Resolve / create students and dedupe by student.id; last status in the
    #    extracted list wins. Prevents UNIQUE(student_id, date) violations when
    #    Gemini returns the same student twice from a messy register.
    final_status: dict[int, str] = {}
    skipped: list[dict] = []
    for e in entries:
        roll = str(e.get("roll_no", "")).strip().lower()
        name = str(e.get("name", "")).strip().lower()
        status = e.get("status", "absent")
        if status not in {"present", "absent", "late"}:
            status = "absent"

        student = students_by_roll.get(roll) or students_by_name.get(name)
        if not student:
            if roll and name:
                student = Student(
                    roll_no=str(e.get("roll_no")).strip(),
                    name=str(e.get("name")).strip(),
                    teacher_id=teacher_id,
                )
                db.add(student)
                db.flush()  # need student.id for the dedupe key
                students_by_roll[roll] = student
                students_by_name[name] = student
            else:
                skipped.append(e)
                continue
        final_status[student.id] = status

    # 2) Load existing attendance rows for this date in one query.
    existing_rows = {
        r.student_id: r
        for r in db.query(AttendanceRecord).filter(
            AttendanceRecord.teacher_id == teacher_id,
            AttendanceRecord.date == target_date,
            AttendanceRecord.student_id.in_(final_status.keys()) if final_status else AttendanceRecord.student_id.is_(None),
        ).all()
    }

    # 3) Upsert per unique student.
    for student_id, status in final_status.items():
        if student_id in existing_rows:
            r = existing_rows[student_id]
            r.status = status
            r.source = "register"
        else:
            db.add(AttendanceRecord(
                student_id=student_id,
                teacher_id=teacher_id,
                date=target_date,
                status=status,
                source="register",
            ))

    db.commit()
    return {
        "saved": len(final_status),
        "date": target_date.isoformat(),
        "skipped": len(skipped),
        "duplicates_collapsed": len(entries) - len(final_status) - len(skipped),
    }


def _persist_poshan(db: Session, teacher_id: int, data: dict) -> dict:
    d_str = data.get("date")
    try:
        target_date = date_cls.fromisoformat(d_str) if d_str else date_cls.today()
    except (TypeError, ValueError):
        target_date = date_cls.today()
    ing = data.get("ingredients") or {}
    rec = MealRecord(
        teacher_id=teacher_id,
        date=target_date,
        meal_type=data.get("meal_type", "lunch"),
        beneficiaries=int(data.get("beneficiaries") or 0),
        meals_served=int(data.get("meals_served") or 0),
        rice_kg=float(ing.get("rice_kg") or 0),
        dal_kg=float(ing.get("dal_kg") or 0),
        vegetables_kg=float(ing.get("vegetables_kg") or 0),
        oil_l=float(ing.get("oil_l") or 0),
        notes=data.get("notes", ""),
        source="register",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"id": rec.id, "date": target_date.isoformat()}


def _persist_stock(db: Session, teacher_id: int, data: dict) -> dict:
    d_str = data.get("date")
    try:
        target_date = date_cls.fromisoformat(d_str) if d_str else date_cls.today()
    except (TypeError, ValueError):
        target_date = date_cls.today()
    saved = 0
    for it in data.get("items", []):
        rec = StockRecord(
            teacher_id=teacher_id,
            item=str(it.get("item", "unknown")).lower().strip(),
            date=target_date,
            opening_kg=float(it.get("opening_kg") or 0),
            received_kg=float(it.get("received_kg") or 0),
            consumed_kg=float(it.get("consumed_kg") or 0),
            closing_kg=float(it.get("closing_kg") or 0),
            source="register",
        )
        db.add(rec)
        saved += 1
    db.commit()
    return {"saved": saved, "date": target_date.isoformat()}


@router.post("/register")
async def upload_register(
    register_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    register_type = register_type.lower().replace("-", "_")
    if register_type not in {"attendance", "pm_poshan", "stock", "audit"}:
        raise HTTPException(status_code=400, detail=f"Unknown register_type: {register_type}")

    out_path = _save_upload(file, current.id, register_type)
    out_path.write_bytes(await file.read())

    try:
        extracted = gemini_vision.extract_register(out_path, register_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini extraction failed: {e}")

    valid, issues = validation.validate(register_type, extracted)
    extracted_row = ExtractedRegisterData(
        teacher_id=current.id,
        register_type=register_type,
        file_path=str(out_path),
        raw_json=json.dumps(extracted, ensure_ascii=False),
        validation_status="valid" if valid else "issues",
        validation_notes="; ".join(issues),
    )
    db.add(extracted_row)
    db.commit()
    db.refresh(extracted_row)

    persisted: dict = {}
    persist_error: str | None = None
    if "error" not in extracted:
        try:
            if register_type == "attendance":
                persisted = _persist_attendance(db, current.id, extracted)
            elif register_type == "pm_poshan":
                persisted = _persist_poshan(db, current.id, extracted)
            elif register_type == "stock":
                persisted = _persist_stock(db, current.id, extracted)
            elif register_type == "audit":
                doc = AuditDocument(
                    teacher_id=current.id,
                    doc_type=extracted.get("doc_type", "other"),
                    title=extracted.get("title", file.filename),
                    file_path=str(out_path),
                    notes=json.dumps(extracted.get("key_fields", {})),
                    status="uploaded",
                )
                db.add(doc)
                db.commit()
                persisted = {"audit_doc_id": doc.id}
        except Exception as e:
            db.rollback()
            persist_error = str(e)
            extracted_row.validation_status = "issues"
            extracted_row.validation_notes = (
                (extracted_row.validation_notes + "; " if extracted_row.validation_notes else "")
                + f"persist failed: {persist_error}"
            )
            db.commit()

    return {
        "extracted_id": extracted_row.id,
        "register_type": register_type,
        "extracted": extracted,
        "validation": {"valid": valid, "issues": issues},
        "persisted": persisted,
        "persist_error": persist_error,
        "file_path": str(out_path),
    }


@router.get("/history")
def history(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rows = (
        db.query(ExtractedRegisterData)
        .filter(ExtractedRegisterData.teacher_id == current.id)
        .order_by(ExtractedRegisterData.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "register_type": r.register_type,
            "validation_status": r.validation_status,
            "validation_notes": r.validation_notes,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
