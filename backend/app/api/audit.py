from fastapi import APIRouter, Depends, UploadFile, File, Form
from pathlib import Path
from datetime import datetime

from app.core.database import get_audit_collection
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.audit import AuditDocument
from app.services import analytics

router = APIRouter(prefix="/api/audit", tags=["audit"])
settings = get_settings()


@router.get("/readiness")
def readiness(current = Depends(get_current_user)):
    """Get audit readiness score using MontyDB."""
    current_id = current.get("id")
    return analytics.audit_readiness(current_id)


@router.post("/documents")
async def upload_document(
    doc_type: str = Form(...),
    title: str = Form(""),
    notes: str = Form(""),
    file: UploadFile = File(...),
    current = Depends(get_current_user),
):
    """Upload an audit document using MontyDB."""
    audit_col = get_audit_collection()
    current_id = current.get("id")
    
    # Create upload directory
    upload_dir = Path(settings.UPLOAD_DIR) / "audit" / current_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{stamp}_{file.filename}"
    out_path = upload_dir / safe_name
    out_path.write_bytes(await file.read())

    # Create and store audit document
    doc = AuditDocument(
        teacher_id=current_id,
        doc_type=doc_type,
        title=title or file.filename,
        file_path=str(out_path),
        notes=notes,
        status="uploaded",
    )
    audit_col.insert_one(doc.model_dump(mode="json"))
    
    return {"id": doc.id, "file_path": doc.file_path, "doc_type": doc.doc_type}


@router.get("/documents")
def list_documents(current = Depends(get_current_user)):
    """List audit documents for current user using MontyDB."""
    audit_col = get_audit_collection()
    current_id = current.get("id")
    
    # Query documents for this teacher
    docs = list(audit_col.find({"teacher_id": current_id}))
    
    # Sort by uploaded_at descending
    docs.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
    
    return [
        {
            "id": d.get("id"),
            "doc_type": d.get("doc_type"),
            "title": d.get("title"),
            "status": d.get("status"),
            "uploaded_at": d.get("uploaded_at"),
            "notes": d.get("notes"),
        }
        for d in docs
    ]
