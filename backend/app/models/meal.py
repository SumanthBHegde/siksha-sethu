from datetime import date, datetime
from sqlalchemy import Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class MealRecord(Base):
    __tablename__ = "meal_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(40), default="lunch")
    beneficiaries: Mapped[int] = mapped_column(Integer, default=0)
    meals_served: Mapped[int] = mapped_column(Integer, default=0)
    rice_kg: Mapped[float] = mapped_column(default=0.0)
    dal_kg: Mapped[float] = mapped_column(default=0.0)
    vegetables_kg: Mapped[float] = mapped_column(default=0.0)
    oil_l: Mapped[float] = mapped_column(default=0.0)
    notes: Mapped[str] = mapped_column(String(500), default="")
    source: Mapped[str] = mapped_column(String(20), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
