from datetime import date, datetime
from sqlalchemy import Integer, String, Date, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class StockRecord(Base):
    __tablename__ = "stock_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    item: Mapped[str] = mapped_column(String(60), nullable=False, index=True)  # rice/dal/oil/...
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    opening_kg: Mapped[float] = mapped_column(Float, default=0.0)
    received_kg: Mapped[float] = mapped_column(Float, default=0.0)
    consumed_kg: Mapped[float] = mapped_column(Float, default=0.0)
    closing_kg: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(String(500), default="")
    source: Mapped[str] = mapped_column(String(20), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
