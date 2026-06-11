from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class AuditDocument(BaseModel):
    """MontyDB document schema for audit documents."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    teacher_id: str  # User ID
    doc_type: str
    title: str = ""
    file_path: str = ""
    status: str = "uploaded"  # uploaded | verified | missing
    notes: str = ""
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "doc_type": self.doc_type,
            "title": self.title,
            "file_path": self.file_path,
            "status": self.status,
            "notes": self.notes,
            "uploaded_at": self.uploaded_at.isoformat() if isinstance(self.uploaded_at, datetime) else self.uploaded_at,
        }
