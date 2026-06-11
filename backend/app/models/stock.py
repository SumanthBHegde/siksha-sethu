from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class StockRecord(BaseModel):
    """MontyDB document schema for stock records."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    teacher_id: str  # User ID
    item: str  # rice | dal | oil | vegetables | etc.
    date: date
    opening_kg: float = 0.0
    received_kg: float = 0.0
    consumed_kg: float = 0.0
    closing_kg: float = 0.0
    notes: str = ""
    source: str = "manual"  # manual | register
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "item": self.item,
            "date": self.date.isoformat() if isinstance(self.date, date) else self.date,
            "opening_kg": self.opening_kg,
            "received_kg": self.received_kg,
            "consumed_kg": self.consumed_kg,
            "closing_kg": self.closing_kg,
            "notes": self.notes,
            "source": self.source,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
