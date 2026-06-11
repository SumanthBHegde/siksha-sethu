from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.core.database import get_students_collection
from app.core.security import get_current_user
from app.models.student import Student
from app.schemas.student import StudentIn, StudentOut

router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("", response_model=List[StudentOut])
def list_students(current = Depends(get_current_user)):
    """List all students for current teacher using MontyDB."""
    students_collection = get_students_collection()
    current_id = current.get("id")
    
    # Query using MQL syntax - find all students for this teacher
    docs = students_collection.find({"teacher_id": current_id})
    result = []
    for doc in docs:
        doc.pop("_id", None)  # Remove MontyDB internal ID
        result.append(doc)
    
    # Sort by roll_no
    result.sort(key=lambda x: x.get("roll_no", ""), reverse=False)
    return result


@router.post("", response_model=StudentOut)
def create_student(body: StudentIn, current = Depends(get_current_user)):
    """Create a new student record using MontyDB."""
    students_collection = get_students_collection()
    current_id = current.get("id")
    
    # Create student document
    student = Student(
        **body.model_dump(),
        teacher_id=current_id
    )
    
    # Insert into collection
    student_dict = student.model_dump(mode="json")
    students_collection.insert_one(student_dict)
    
    student_dict.pop("_id", None)
    return student_dict


@router.delete("/{student_id}")
def delete_student(student_id: str, current = Depends(get_current_user)):
    """Delete a student record using MontyDB."""
    students_collection = get_students_collection()
    current_id = current.get("id")
    
    # Find student - ensure it belongs to current teacher
    student = students_collection.find_one({"id": student_id, "teacher_id": current_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Delete using MQL syntax
    students_collection.delete_one({"id": student_id})
    return {"deleted": True}
