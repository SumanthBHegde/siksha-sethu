from pydantic import BaseModel
from typing import Optional


class StudentIn(BaseModel):
    roll_no: str
    name: str
    grade: str = "5"
    section: str = "A"
    gender: str = ""


class StudentOut(StudentIn):
    id: int

    class Config:
        from_attributes = True
