from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class AttendanceRecord(BaseModel):
    """MontyDB document schema for attendance records."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str  # Student ID
    teacher_id: str  # User ID
    date: date
    status: str  # present | absent | late
    source: str = "manual"  # manual | register
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "teacher_id": self.teacher_id,
            "date": self.date.isoformat() if isinstance(self.date, date) else self.date,
            "status": self.status,
            "source": self.source,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
