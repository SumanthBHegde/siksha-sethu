from app.models.user import User
from app.models.student import Student
from app.models.attendance import AttendanceRecord
from app.models.meal import MealRecord
from app.models.stock import StockRecord
from app.models.audit import AuditDocument
from app.models.extracted import ExtractedRegisterData
from app.models.chat import ChatHistory

__all__ = [
    "User",
    "Student",
    "AttendanceRecord",
    "MealRecord",
    "StockRecord",
    "AuditDocument",
    "ExtractedRegisterData",
    "ChatHistory",
]
