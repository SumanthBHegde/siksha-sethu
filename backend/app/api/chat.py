from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import ChatHistory, User
from app.schemas.chat import ChatIn, ChatOut
from app.agents.graph import run_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatOut)
def chat(body: ChatIn, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    result = run_agent(current.id, body.message)

    db.add(ChatHistory(teacher_id=current.id, role="user", content=body.message, agent="supervisor"))
    db.add(ChatHistory(teacher_id=current.id, role="assistant", content=result["reply"], agent=result["agent"]))
    db.commit()

    return ChatOut(reply=result["reply"], agent=result["agent"], data=result.get("data"))


@router.get("/history")
def history(limit: int = 50, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.teacher_id == current.id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "role": r.role,
            "content": r.content,
            "agent": r.agent,
            "created_at": r.created_at.isoformat(),
        }
        for r in reversed(rows)
    ]
