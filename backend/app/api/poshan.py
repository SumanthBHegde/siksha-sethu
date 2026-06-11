from fastapi import APIRouter, Depends
from datetime import date, timedelta
from typing import Optional

from app.core.database import get_meal_collection, get_stock_collection
from app.core.security import get_current_user
from app.models.meal import MealRecord
from app.models.stock import StockRecord
from app.schemas.poshan import MealIn, StockIn
from app.services import analytics

router = APIRouter(prefix="/api/poshan", tags=["poshan"])


@router.post("/meals")
def add_meal(body: MealIn, current = Depends(get_current_user)):
    """Add a meal record using MontyDB."""
    meal_col = get_meal_collection()
    current_id = current.get("id")
    
    record = MealRecord(**body.model_dump(), teacher_id=current_id)
    meal_col.insert_one(record.model_dump(mode="json"))
    return {"id": record.id}


@router.post("/stock")
def add_stock(body: StockIn, current = Depends(get_current_user)):
    """Add a stock record using MontyDB."""
    stock_col = get_stock_collection()
    current_id = current.get("id")
    
    record = StockRecord(**body.model_dump(), teacher_id=current_id)
    stock_col.insert_one(record.model_dump(mode="json"))
    return {"id": record.id}


@router.get("/summary")
def summary(
    start: Optional[date] = None,
    end: Optional[date] = None,
    current = Depends(get_current_user),
):
    """Get PM Poshan summary for a date range using MontyDB."""
    current_id = current.get("id")
    end = end or date.today()
    start = start or (end - timedelta(days=30))
    return analytics.poshan_summary(current_id, start, end)


@router.get("/stock-status")
def stock_status(current = Depends(get_current_user)):
    """Get current stock status using MontyDB."""
    current_id = current.get("id")
    return analytics.stock_status(current_id)
