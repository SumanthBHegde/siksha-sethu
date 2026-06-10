from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class ExtractedRegisterData(BaseModel):
    """MontyDB document schema for extracted register data."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    teacher_id: str  # User ID
    register_type: str  # attendance | daily_pm_poshan | monthly_pm_poshan | stock | audit | unknown
    file_path: str = ""
    raw_json: Dict[str, Any] = Field(default_factory=dict)
    validation_status: str = "pending"  # pending | validated | needs_review | rejected
    validation_notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "register_type": self.register_type,
            "file_path": self.file_path,
            "raw_json": self.raw_json,
            "validation_status": self.validation_status,
            "validation_notes": self.validation_notes,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
