from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class Student(BaseModel):
    """MontyDB document schema for student records."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    roll_no: str
    name: str
    grade: str = "5"
    section: str = "A"
    gender: str = ""
    teacher_id: str  # User ID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "roll_no": self.roll_no,
            "name": self.name,
            "grade": self.grade,
            "section": self.section,
            "gender": self.gender,
            "teacher_id": self.teacher_id,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
