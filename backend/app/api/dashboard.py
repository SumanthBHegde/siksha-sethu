from fastapi import APIRouter, Depends
from datetime import date, timedelta

from app.core.security import get_current_user
from app.services import analytics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/home")
def home(current = Depends(get_current_user)):
    """Get dashboard home data using MontyDB."""
    current_id = current.get("id")
    today = date.today()
    last_30 = today - timedelta(days=30)
    month_start = today.replace(day=1)
    
    return {
        "attendance": analytics.attendance_summary(current_id, last_30, today),
        "poshan": analytics.poshan_summary(current_id, month_start, today),
        "stock": analytics.stock_status(current_id),
        "audit": analytics.audit_readiness(current_id),
        "recent_uploads": analytics.recent_uploads(current_id),
    }
