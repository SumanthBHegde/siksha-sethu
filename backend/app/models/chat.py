from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class ChatHistory(BaseModel):
    """MontyDB document schema for chat history."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    teacher_id: str  # User ID
    role: str  # user | assistant
    content: str
    agent: str = "supervisor"  # Agent type
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "role": self.role,
            "content": self.content,
            "agent": self.agent,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
