from pydantic import BaseModel
from datetime import date
from typing import List


class AttendanceEntry(BaseModel):
    student_id: str
    status: str  # present | absent | late


class AttendanceBulkIn(BaseModel):
    date: date
    entries: List[AttendanceEntry]


class AttendanceOut(BaseModel):
    id: str
    student_id: str
    date: date
    status: str
    source: str

    class Config:
        from_attributes = True
