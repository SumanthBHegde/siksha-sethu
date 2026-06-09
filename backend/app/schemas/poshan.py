from pydantic import BaseModel
from datetime import date


class MealIn(BaseModel):
    date: date
    meal_type: str = "lunch"
    beneficiaries: int = 0
    meals_served: int = 0
    rice_kg: float = 0.0
    dal_kg: float = 0.0
    vegetables_kg: float = 0.0
    oil_l: float = 0.0
    notes: str = ""


class StockIn(BaseModel):
    item: str
    date: date
    opening_kg: float = 0.0
    received_kg: float = 0.0
    consumed_kg: float = 0.0
    closing_kg: float = 0.0
    notes: str = ""
