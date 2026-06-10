from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class MealRecord(BaseModel):
    """MontyDB document schema for meal records (PM Poshan)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    teacher_id: str  # User ID
    date: date
    meal_type: str = "lunch"  # lunch | breakfast | snacks
    beneficiaries: int = 0
    meals_served: int = 0
    rice_kg: float = 0.0
    dal_kg: float = 0.0
    vegetables_kg: float = 0.0
    oil_l: float = 0.0
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
            "date": self.date.isoformat() if isinstance(self.date, date) else self.date,
            "meal_type": self.meal_type,
            "beneficiaries": self.beneficiaries,
            "meals_served": self.meals_served,
            "rice_kg": self.rice_kg,
            "dal_kg": self.dal_kg,
            "vegetables_kg": self.vegetables_kg,
            "oil_l": self.oil_l,
            "notes": self.notes,
            "source": self.source,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
