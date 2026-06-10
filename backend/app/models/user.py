from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
import uuid


class User(BaseModel):
    """MontyDB User document schema for authentication and account management."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    school_name: str = "Government School"
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        
    def to_dict(self) -> dict:
        """Convert to dictionary for storage and API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "school_name": self.school_name,
            "password_hash": self.password_hash,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
