"""Register image upload + Gemini Vision extraction + MontyDB persistence."""
from __future__ import annotations

import json
import re
from datetime import datetime, date as date_cls
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException

from app.core.database import (
    get_students_collection,
    get_attendance_collection,
    get_meal_collection,
    get_stock_collection,
    get_audit_collection,
    get_extracted_data_collection
)
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models import (
    Student, AttendanceRecord, MealRecord, StockRecord,
    ExtractedRegisterData, AuditDocument,
)
from app.services import gemini_vision, validation

router = APIRouter(prefix="/api/upload", tags=["upload"])
settings = get_settings()


KANNADA_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯", "0123456789")


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).translate(KANNADA_DIGITS).strip()


def _as_number(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)

    text = _as_str(value).replace(",", "")
    text = re.sub(r"[^0-9.+-]", "", text)
    if text in {"", ".", "+", "-"}:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _as_int(value: Any, default: int = 0) -> int:
    return int(round(_as_number(value, float(default))))


def _as_date(value: Any) -> date_cls:
    if isinstance(value, date_cls):
        return value

    text = _as_str(value).lower()
    if not text or text in {"null", "none", "not visible", "not available", "ಗೊತ್ತಿಲ್ಲ"}:
        return date_cls.today()

    text = re.split(r"\s+(?:to|ವರೆಗೆ|-)\s+", text)[0].strip()
    formats = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y")
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return date_cls.fromisoformat(text)
    except ValueError:
        return date_cls.today()


def _normalize_status(value: Any) -> str:
    text = _as_str(value, "absent").lower()
    present_values = {"present", "p", "yes", "y", "tick", "checked", "attended", "1", "true", "ಹಾಜರು", "ಹಾ", "ಉಪಸ್ಥಿತ"}
    absent_values = {"absent", "a", "no", "n", "cross", "0", "false", "ಗೈರು", "ಗೈ", "ಅನುಪಸ್ಥಿತ"}
    if text in present_values or "ಹಾಜ" in text:
        return "present"
    if text in {"late", "l", "ತಡ"}:
        return "late"
    if text in absent_values or "ಗೈ" in text:
        return "absent"
    return "absent"


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row and row[key] not in {None, ""}:
            return row[key]
    return None


def _normalize_item_name(value: Any) -> str:
    text = _as_str(value, "unknown").lower()
    if any(word in text for word in ("ಅಕ್ಕಿ", "rice")):
        return "rice"
    if any(word in text for word in ("ಬೇಳೆ", "dal", "dhal", "lentil")):
        return "dal"
    if any(word in text for word in ("ಎಣ್ಣೆ", "oil")):
        return "oil"
    if any(word in text for word in ("ತರಕಾರಿ", "vegetable", "veg")):
        return "vegetables"
    return text or "unknown"


def _normalize_register_payload(register_type: str, data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data or {})
    normalized["register_type"] = register_type
    normalized["date"] = _as_date(normalized.get("date")).isoformat()

    if register_type == "attendance":
        entries = normalized.get("entries") or normalized.get("students") or normalized.get("rows")
        normalized["entries"] = [
            {
                "roll_no": _as_str(_first_present(e, ("roll_no", "roll", "serial_no", "sl_no", "ಕ್ರಮ ಸಂಖ್ಯೆ"))),
                "name": _as_str(_first_present(e, ("name", "student_name", "ವಿದ್ಯಾರ್ಥಿ ಹೆಸರು", "ಹೆಸರು"))),
                "status": _normalize_status(_first_present(e, ("status", "attendance", "ಹಾಜರಾತಿ", "ಸ್ಥಿತಿ"))),
            }
            for e in _as_list(entries)
            if isinstance(e, dict)
        ]
    elif register_type == "pm_poshan":
        ingredients = normalized.get("ingredients") or {}
        normalized["meal_type"] = _as_str(normalized.get("meal_type"), "lunch").lower() or "lunch"
        normalized["beneficiaries"] = _as_int(normalized.get("beneficiaries") or normalized.get("children") or normalized.get("ವಿದ್ಯಾರ್ಥಿಗಳು"))
        normalized["meals_served"] = _as_int(normalized.get("meals_served") or normalized.get("served") or normalized.get("ಊಟ ನೀಡಿದವರು"))
        normalized["ingredients"] = {
            "rice_kg": _as_number(ingredients.get("rice_kg") or ingredients.get("ಅಕ್ಕಿ") or normalized.get("rice_kg")),
            "dal_kg": _as_number(ingredients.get("dal_kg") or ingredients.get("ಬೇಳೆ") or normalized.get("dal_kg")),
            "vegetables_kg": _as_number(ingredients.get("vegetables_kg") or ingredients.get("ತರಕಾರಿ") or normalized.get("vegetables_kg")),
            "oil_l": _as_number(ingredients.get("oil_l") or ingredients.get("ಎಣ್ಣೆ") or normalized.get("oil_l")),
        }
    elif register_type == "stock":
        items = normalized.get("items") or normalized.get("stock_items") or normalized.get("rows")
        normalized["items"] = [
            {
                "item": _normalize_item_name(_first_present(it, ("item", "name", "ವಸ್ತು", "ಸಾಮಾನು"))),
                "opening_kg": _as_number(_first_present(it, ("opening_kg", "opening", "opening_balance", "ಆರಂಭಿಕ"))),
                "received_kg": _as_number(_first_present(it, ("received_kg", "received", "ಸ್ವೀಕೃತ"))),
                "consumed_kg": _as_number(_first_present(it, ("consumed_kg", "consumed", "issued_kg", "used", "ಬಳಕೆ"))),
                "closing_kg": _as_number(_first_present(it, ("closing_kg", "closing", "balance_kg", "closing_balance", "ಉಳಿಕೆ"))),
            }
            for it in _as_list(items)
            if isinstance(it, dict)
        ]
    elif register_type == "audit":
        normalized["doc_type"] = _as_str(normalized.get("doc_type"), "other") or "other"
        normalized["title"] = _as_str(normalized.get("title"), "Uploaded document") or "Uploaded document"
        if not isinstance(normalized.get("key_fields"), dict):
            normalized["key_fields"] = {}

    return normalized


def _save_upload(file: UploadFile, teacher_id: str, register_type: str) -> Path:
    upload_dir = Path(settings.UPLOAD_DIR) / register_type / teacher_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{stamp}_{file.filename}"
    out_path = upload_dir / safe_name
    return out_path


def _persist_attendance(teacher_id: str, data: dict) -> dict:
    """Persist attendance records to MontyDB using MQL."""
    students_col = get_students_collection()
    attendance_col = get_attendance_collection()
    
    entries = data.get("entries", [])
    target_date = _as_date(data.get("date")).isoformat()

    # Get students indexed by roll_no and name
    students_list = list(students_col.find({"teacher_id": teacher_id}))
    students_by_roll = {s.get("roll_no", "").strip().lower(): s for s in students_list}
    students_by_name = {s.get("name", "").strip().lower(): s for s in students_list}

    # Dedupe entries by student ID
    final_status: dict[str, str] = {}
    skipped: list[dict] = []
    created_student_ids = []
    
    for e in entries:
        roll = _as_str(e.get("roll_no")).lower()
        name = _as_str(e.get("name")).lower()
        status = _normalize_status(e.get("status"))

        student = students_by_roll.get(roll) or students_by_name.get(name)
        if not student:
            if roll and name:
                # Create new student
                new_student = Student(
                    roll_no=str(e.get("roll_no")).strip(),
                    name=str(e.get("name")).strip(),
                    teacher_id=teacher_id,
                )
                students_col.insert_one(new_student.model_dump())
                student = new_student.model_dump()
                created_student_ids.append(new_student.id)
                students_by_roll[roll] = student
                students_by_name[name] = student
            else:
                skipped.append(e)
                continue
        
        final_status[student.get("id")] = status

    # Upsert attendance records
    for student_id, status in final_status.items():
        existing = attendance_col.find_one({
            "student_id": student_id,
            "date": target_date,
            "teacher_id": teacher_id,
        })
        
        if existing:
            attendance_col.update_one(
                {"id": existing.get("id")},
                {"$set": {"status": status, "source": "register"}}
            )
        else:
            record = AttendanceRecord(
                student_id=student_id,
                teacher_id=teacher_id,
                date=_as_date(target_date),
                status=status,
                source="register",
            )
            attendance_col.insert_one(record.model_dump())

    return {
        "saved": len(final_status),
        "date": target_date,
        "skipped": len(skipped),
        "duplicates_collapsed": len(entries) - len(final_status) - len(skipped),
        "students_created": len(created_student_ids),
    }


def _persist_poshan(teacher_id: str, data: dict) -> dict:
    """Persist meal records to MontyDB."""
    meal_col = get_meal_collection()
    target_date = _as_date(data.get("date"))
    ing = data.get("ingredients") or {}
    
    rec = MealRecord(
        teacher_id=teacher_id,
        date=target_date,
        meal_type=_as_str(data.get("meal_type"), "lunch") or "lunch",
        beneficiaries=_as_int(data.get("beneficiaries")),
        meals_served=_as_int(data.get("meals_served")),
        rice_kg=_as_number(ing.get("rice_kg")),
        dal_kg=_as_number(ing.get("dal_kg")),
        vegetables_kg=_as_number(ing.get("vegetables_kg")),
        oil_l=_as_number(ing.get("oil_l")),
        notes=_as_str(data.get("notes")),
        source="register",
    )
    meal_col.insert_one(rec.model_dump())
    return {"id": rec.id, "date": target_date.isoformat()}


def _persist_stock(teacher_id: str, data: dict) -> dict:
    """Persist stock records to MontyDB."""
    stock_col = get_stock_collection()
    target_date = _as_date(data.get("date"))
    saved = 0
    
    for it in data.get("items", []):
        rec = StockRecord(
            teacher_id=teacher_id,
            item=_normalize_item_name(it.get("item")),
            date=target_date,
            opening_kg=_as_number(it.get("opening_kg")),
            received_kg=_as_number(it.get("received_kg")),
            consumed_kg=_as_number(it.get("consumed_kg")),
            closing_kg=_as_number(it.get("closing_kg")),
            source="register",
        )
        stock_col.insert_one(rec.model_dump())
        saved += 1
    
    return {"saved": saved, "date": target_date.isoformat()}


def _save_extracted_and_persist(
    *,
    current: dict,
    register_type: str,
    extracted: dict[str, Any],
    file_path: Path,
    filename: str,
) -> dict[str, Any]:
    """Save extracted data and persist to appropriate collection using MontyDB."""
    extracted_col = get_extracted_data_collection()
    current_id = current.get("id")
    
    extracted = _normalize_register_payload(register_type, extracted)
    valid, issues = validation.validate(register_type, extracted)
    
    extracted_row = ExtractedRegisterData(
        teacher_id=current_id,
        register_type=register_type,
        file_path=str(file_path),
        raw_json=extracted,
        validation_status="valid" if valid else "issues",
        validation_notes="; ".join(issues),
    )
    extracted_col.insert_one(extracted_row.model_dump())

    persisted: dict = {}
    persist_error: str | None = None
    
    if "error" not in extracted:
        try:
            if register_type == "attendance":
                persisted = _persist_attendance(current_id, extracted)
            elif register_type == "pm_poshan":
                persisted = _persist_poshan(current_id, extracted)
            elif register_type == "stock":
                persisted = _persist_stock(current_id, extracted)
            elif register_type == "audit":
                audit_col = get_audit_collection()
                doc = AuditDocument(
                    teacher_id=current_id,
                    doc_type=extracted.get("doc_type", "other"),
                    title=extracted.get("title", filename),
                    file_path=str(file_path),
                    notes=json.dumps(extracted.get("key_fields", {}), ensure_ascii=False),
                    status="uploaded",
                )
                audit_col.insert_one(doc.model_dump())
                persisted = {"audit_doc_id": doc.id}
        except Exception as e:
            persist_error = str(e)
            # Update extracted row with error
            extracted_col.update_one(
                {"id": extracted_row.id},
                {"$set": {
                    "validation_status": "issues",
                    "validation_notes": (extracted_row.validation_notes or "") + f"; persist failed: {persist_error}"
                }}
            )

    return {
        "extracted_id": extracted_row.id,
        "register_type": register_type,
        "extracted": extracted,
        "validation": {"valid": valid, "issues": issues},
        "persisted": persisted,
        "persist_error": persist_error,
        "file_path": str(file_path),
    }


@router.post("/register")
async def upload_register(
    register_type: str = Form(...),
    file: UploadFile = File(...),
    current = Depends(get_current_user),
):
    """Upload and process a register image using MontyDB."""
    register_type = register_type.lower().replace("-", "_")
    current_id = current.get("id")
    
    if register_type not in {"attendance", "pm_poshan", "stock", "audit"}:
        raise HTTPException(status_code=400, detail=f"Unknown register_type: {register_type}")

    out_path = _save_upload(file, current_id, register_type)
    out_path.write_bytes(await file.read())

    try:
        extracted = gemini_vision.extract_register(out_path, register_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini extraction failed: {e}")
    
    return _save_extracted_and_persist(
        current=current,
        register_type=register_type,
        extracted=extracted,
        file_path=out_path,
        filename=file.filename,
    )


@router.post("/helper")
async def upload_helper(
    file: UploadFile = File(...),
    current = Depends(get_current_user),
):
    """Upload and auto-classify a register image using MontyDB."""
    current_id = current.get("id")
    
    out_path = _save_upload(file, current_id, "ai_helper")
    out_path.write_bytes(await file.read())

    try:
        extracted = gemini_vision.extract_auto_register(out_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini helper extraction failed: {e}")

    register_type = _as_str(extracted.get("register_type")).lower().replace("-", "_")
    if register_type not in {"attendance", "pm_poshan", "stock", "audit"}:
        register_type = "audit"
        extracted["register_type"] = register_type
        extracted["notes"] = (
            (_as_str(extracted.get("notes")) + "; ") if extracted.get("notes") else ""
        ) + "AI helper could not confidently label the image; saved as audit document."

    return _save_extracted_and_persist(
        current=current,
        register_type=register_type,
        extracted=extracted,
        file_path=out_path,
        filename=file.filename,
    )


@router.get("/history")
def history(current = Depends(get_current_user)):
    """Get upload history for current user using MontyDB."""
    extracted_col = get_extracted_data_collection()
    current_id = current.get("id")
    
    rows = list(extracted_col.find({"teacher_id": current_id}))
    rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    rows = rows[:50]
    
    return [
        {
            "id": r.get("id"),
            "register_type": r.get("register_type"),
            "validation_status": r.get("validation_status"),
            "validation_notes": r.get("validation_notes"),
            "created_at": r.get("created_at"),
        }
        for r in rows
    ]


KANNADA_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯", "0123456789")


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).translate(KANNADA_DIGITS).strip()


def _as_number(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)

    text = _as_str(value).replace(",", "")
    text = re.sub(r"[^0-9.+-]", "", text)
    if text in {"", ".", "+", "-"}:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _as_int(value: Any, default: int = 0) -> int:
    return int(round(_as_number(value, float(default))))


def _as_date(value: Any) -> date_cls:
    if isinstance(value, date_cls):
        return value

    text = _as_str(value).lower()
    if not text or text in {"null", "none", "not visible", "not available", "ಗೊತ್ತಿಲ್ಲ"}:
        return date_cls.today()

    text = re.split(r"\s+(?:to|ವರೆಗೆ|-)\s+", text)[0].strip()
    formats = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y")
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return date_cls.fromisoformat(text)
    except ValueError:
        return date_cls.today()


def _normalize_status(value: Any) -> str:
    text = _as_str(value, "absent").lower()
    present_values = {"present", "p", "yes", "y", "tick", "checked", "attended", "1", "true", "ಹಾಜರು", "ಹಾ", "ಉಪಸ್ಥಿತ"}
    absent_values = {"absent", "a", "no", "n", "cross", "0", "false", "ಗೈರು", "ಗೈ", "ಅನುಪಸ್ಥಿತ"}
    if text in present_values or "ಹಾಜ" in text:
        return "present"
    if text in {"late", "l", "ತಡ"}:
        return "late"
    if text in absent_values or "ಗೈ" in text:
        return "absent"
    return "absent"


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row and row[key] not in {None, ""}:
            return row[key]
    return None


def _normalize_item_name(value: Any) -> str:
    text = _as_str(value, "unknown").lower()
    if any(word in text for word in ("ಅಕ್ಕಿ", "rice")):
        return "rice"
    if any(word in text for word in ("ಬೇಳೆ", "dal", "dhal", "lentil")):
        return "dal"
    if any(word in text for word in ("ಎಣ್ಣೆ", "oil")):
        return "oil"
    if any(word in text for word in ("ತರಕಾರಿ", "vegetable", "veg")):
        return "vegetables"
    return text or "unknown"


def _normalize_register_payload(register_type: str, data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data or {})
    normalized["register_type"] = register_type
    normalized["date"] = _as_date(normalized.get("date")).isoformat()

    if register_type == "attendance":
        entries = normalized.get("entries") or normalized.get("students") or normalized.get("rows")
        normalized["entries"] = [
            {
                "roll_no": _as_str(_first_present(e, ("roll_no", "roll", "serial_no", "sl_no", "ಕ್ರಮ ಸಂಖ್ಯೆ"))),
                "name": _as_str(_first_present(e, ("name", "student_name", "ವಿದ್ಯಾರ್ಥಿ ಹೆಸರು", "ಹೆಸರು"))),
                "status": _normalize_status(_first_present(e, ("status", "attendance", "ಹಾಜರಾತಿ", "ಸ್ಥಿತಿ"))),
            }
            for e in _as_list(entries)
            if isinstance(e, dict)
        ]
    elif register_type == "pm_poshan":
        ingredients = normalized.get("ingredients") or {}
        normalized["meal_type"] = _as_str(normalized.get("meal_type"), "lunch").lower() or "lunch"
        normalized["beneficiaries"] = _as_int(normalized.get("beneficiaries") or normalized.get("children") or normalized.get("ವಿದ್ಯಾರ್ಥಿಗಳು"))
        normalized["meals_served"] = _as_int(normalized.get("meals_served") or normalized.get("served") or normalized.get("ಊಟ ನೀಡಿದವರು"))
        normalized["ingredients"] = {
            "rice_kg": _as_number(ingredients.get("rice_kg") or ingredients.get("ಅಕ್ಕಿ") or normalized.get("rice_kg")),
            "dal_kg": _as_number(ingredients.get("dal_kg") or ingredients.get("ಬೇಳೆ") or normalized.get("dal_kg")),
            "vegetables_kg": _as_number(ingredients.get("vegetables_kg") or ingredients.get("ತರಕಾರಿ") or normalized.get("vegetables_kg")),
            "oil_l": _as_number(ingredients.get("oil_l") or ingredients.get("ಎಣ್ಣೆ") or normalized.get("oil_l")),
        }
    elif register_type == "stock":
        items = normalized.get("items") or normalized.get("stock_items") or normalized.get("rows")
        normalized["items"] = [
            {
                "item": _normalize_item_name(_first_present(it, ("item", "name", "ವಸ್ತು", "ಸಾಮಾನು"))),
                "opening_kg": _as_number(_first_present(it, ("opening_kg", "opening", "opening_balance", "ಆರಂಭಿಕ"))),
                "received_kg": _as_number(_first_present(it, ("received_kg", "received", "ಸ್ವೀಕೃತ"))),
                "consumed_kg": _as_number(_first_present(it, ("consumed_kg", "consumed", "issued_kg", "used", "ಬಳಕೆ"))),
                "closing_kg": _as_number(_first_present(it, ("closing_kg", "closing", "balance_kg", "closing_balance", "ಉಳಿಕೆ"))),
            }
            for it in _as_list(items)
            if isinstance(it, dict)
        ]
    elif register_type == "audit":
        normalized["doc_type"] = _as_str(normalized.get("doc_type"), "other") or "other"
        normalized["title"] = _as_str(normalized.get("title"), "Uploaded document") or "Uploaded document"
        if not isinstance(normalized.get("key_fields"), dict):
            normalized["key_fields"] = {}

    return normalized


def _save_upload(file: UploadFile, teacher_id: int, register_type: str) -> Path:
    upload_dir = Path(settings.UPLOAD_DIR) / register_type / str(teacher_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{stamp}_{file.filename}"
    out_path = upload_dir / safe_name
    return out_path


def _persist_attendance(db: Session, teacher_id: int, data: dict) -> dict:
    entries = data.get("entries", [])
    target_date = _as_date(data.get("date"))

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
        roll = _as_str(e.get("roll_no")).lower()
        name = _as_str(e.get("name")).lower()
        status = _normalize_status(e.get("status"))

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
    target_date = _as_date(data.get("date"))
    ing = data.get("ingredients") or {}
    rec = MealRecord(
        teacher_id=teacher_id,
        date=target_date,
        meal_type=_as_str(data.get("meal_type"), "lunch") or "lunch",
        beneficiaries=_as_int(data.get("beneficiaries")),
        meals_served=_as_int(data.get("meals_served")),
        rice_kg=_as_number(ing.get("rice_kg")),
        dal_kg=_as_number(ing.get("dal_kg")),
        vegetables_kg=_as_number(ing.get("vegetables_kg")),
        oil_l=_as_number(ing.get("oil_l")),
        notes=_as_str(data.get("notes")),
        source="register",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"id": rec.id, "date": target_date.isoformat()}


def _persist_stock(db: Session, teacher_id: int, data: dict) -> dict:
    target_date = _as_date(data.get("date"))
    saved = 0
    for it in data.get("items", []):
        rec = StockRecord(
            teacher_id=teacher_id,
            item=_normalize_item_name(it.get("item")),
            date=target_date,
            opening_kg=_as_number(it.get("opening_kg")),
            received_kg=_as_number(it.get("received_kg")),
            consumed_kg=_as_number(it.get("consumed_kg")),
            closing_kg=_as_number(it.get("closing_kg")),
            source="register",
        )
        db.add(rec)
        saved += 1
    db.commit()
    return {"saved": saved, "date": target_date.isoformat()}


def _save_extracted_and_persist(
    *,
    db: Session,
    current: User,
    register_type: str,
    extracted: dict[str, Any],
    file_path: Path,
    filename: str,
) -> dict[str, Any]:
    extracted = _normalize_register_payload(register_type, extracted)
    valid, issues = validation.validate(register_type, extracted)
    extracted_row = ExtractedRegisterData(
        teacher_id=current.id,
        register_type=register_type,
        file_path=str(file_path),
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
                    title=extracted.get("title", filename),
                    file_path=str(file_path),
                    notes=json.dumps(extracted.get("key_fields", {}), ensure_ascii=False),
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
        "file_path": str(file_path),
    }


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
    return _save_extracted_and_persist(
        db=db,
        current=current,
        register_type=register_type,
        extracted=extracted,
        file_path=out_path,
        filename=file.filename,
    )


@router.post("/helper")
async def upload_helper(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    out_path = _save_upload(file, current.id, "ai_helper")
    out_path.write_bytes(await file.read())

    try:
        extracted = gemini_vision.extract_auto_register(out_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini helper extraction failed: {e}")

    register_type = _as_str(extracted.get("register_type")).lower().replace("-", "_")
    if register_type not in {"attendance", "pm_poshan", "stock", "audit"}:
        register_type = "audit"
        extracted["register_type"] = register_type
        extracted["notes"] = (
            (_as_str(extracted.get("notes")) + "; ") if extracted.get("notes") else ""
        ) + "AI helper could not confidently label the image; saved as audit document."

    return _save_extracted_and_persist(
        db=db,
        current=current,
        register_type=register_type,
        extracted=extracted,
        file_path=out_path,
        filename=file.filename,
    )


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
