from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import MealRecord, StockRecord, User
from app.schemas.poshan import MealIn, StockIn
from app.services import analytics

router = APIRouter(prefix="/api/poshan", tags=["poshan"])


@router.post("/meals")
def add_meal(body: MealIn, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rec = MealRecord(**body.model_dump(), teacher_id=current.id)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"id": rec.id}


@router.post("/stock")
def add_stock(body: StockIn, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rec = StockRecord(**body.model_dump(), teacher_id=current.id)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"id": rec.id}


@router.get("/summary")
def summary(
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    end = end or date.today()
    start = start or (end - timedelta(days=30))
    return analytics.poshan_summary(db, current.id, start, end)


@router.get("/stock-status")
def stock_status(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return analytics.stock_status(db, current.id)
