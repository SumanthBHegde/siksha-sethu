from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.services import analytics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/home")
def home(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    today = date.today()
    last_30 = today - timedelta(days=30)
    month_start = today.replace(day=1)
    return {
        "attendance": analytics.attendance_summary(db, current.id, last_30, today),
        "poshan": analytics.poshan_summary(db, current.id, month_start, today),
        "stock": analytics.stock_status(db, current.id),
        "audit": analytics.audit_readiness(db, current.id),
        "recent_uploads": analytics.recent_uploads(db, current.id),
    }
