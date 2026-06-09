from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models import AuditDocument, User
from app.services import analytics

router = APIRouter(prefix="/api/audit", tags=["audit"])
settings = get_settings()


@router.get("/readiness")
def readiness(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return analytics.audit_readiness(db, current.id)


@router.post("/documents")
async def upload_document(
    doc_type: str = Form(...),
    title: str = Form(""),
    notes: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    upload_dir = Path(settings.UPLOAD_DIR) / "audit" / str(current.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{stamp}_{file.filename}"
    out_path = upload_dir / safe_name
    out_path.write_bytes(await file.read())

    doc = AuditDocument(
        teacher_id=current.id,
        doc_type=doc_type,
        title=title or file.filename,
        file_path=str(out_path),
        notes=notes,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "file_path": doc.file_path, "doc_type": doc.doc_type}


@router.get("/documents")
def list_documents(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    docs = db.query(AuditDocument).filter(AuditDocument.teacher_id == current.id).order_by(
        AuditDocument.uploaded_at.desc()
    ).all()
    return [
        {
            "id": d.id, "doc_type": d.doc_type, "title": d.title,
            "status": d.status, "uploaded_at": d.uploaded_at.isoformat(),
            "notes": d.notes,
        }
        for d in docs
    ]
