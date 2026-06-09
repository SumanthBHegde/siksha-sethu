from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentIn, StudentOut

router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("", response_model=List[StudentOut])
def list_students(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(Student).filter(Student.teacher_id == current.id).order_by(Student.roll_no).all()


@router.post("", response_model=StudentOut)
def create_student(body: StudentIn, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    s = Student(**body.model_dump(), teacher_id=current.id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    s = db.query(Student).filter(Student.id == student_id, Student.teacher_id == current.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(s)
    db.commit()
    return {"deleted": True}
