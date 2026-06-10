from fastapi import APIRouter, Depends
from datetime import datetime

from app.core.database import get_chat_collection
from app.core.security import get_current_user
from app.models.chat import ChatHistory
from app.schemas.chat import ChatIn, ChatOut
from app.agents.graph import run_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatOut)
def chat(body: ChatIn, current = Depends(get_current_user)):
    """Send a chat message and get agent response using MontyDB."""
    chat_col = get_chat_collection()
    current_id = current.get("id")
    
    # Run agent
    result = run_agent(current_id, body.message)

    # Store user message
    user_msg = ChatHistory(
        teacher_id=current_id,
        role="user",
        content=body.message,
        agent="supervisor"
    )
    chat_col.insert_one(user_msg.model_dump())
    
    # Store assistant response
    assistant_msg = ChatHistory(
        teacher_id=current_id,
        role="assistant",
        content=result["reply"],
        agent=result["agent"]
    )
    chat_col.insert_one(assistant_msg.model_dump())

    return ChatOut(reply=result["reply"], agent=result["agent"], data=result.get("data"))


@router.get("/history")
def history(limit: int = 50, current = Depends(get_current_user)):
    """Get chat history for current user using MontyDB."""
    chat_col = get_chat_collection()
    current_id = current.get("id")
    
    # Query chat history, sorted by created_at descending
    rows = list(chat_col.find({"teacher_id": current_id}))
    
    # Sort by created_at descending, then take limit
    rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    rows = rows[:limit]
    
    # Format response and reverse for chronological order
    result = []
    for r in reversed(rows):
        result.append({
            "id": r.get("id"),
            "role": r.get("role"),
            "content": r.get("content"),
            "agent": r.get("agent"),
            "created_at": r.get("created_at"),
        })
    
    return result
