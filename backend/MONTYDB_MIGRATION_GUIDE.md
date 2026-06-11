# MontyDB Migration Guide for ShikshaSetu Backend

This document provides comprehensive guidance for completing the migration from SQLAlchemy/SQLite to MontyDB.

## Overview

The backend has been successfully migrated to use **MontyDB** as the document database. MontyDB is a serverless, file-based Python implementation of MongoDB, eliminating the need for external database infrastructure.

### What Changed

| Aspect | Before (SQLAlchemy) | After (MontyDB) |
|--------|-------------------|-----------------|
| **Storage** | SQLite file-based | MontyDB JSON files in `data/db_repo/` |
| **ORM** | SQLAlchemy declarative models | Pydantic Schemas |
| **IDs** | Auto-increment integers | String UUIDs (generated client-side) |
| **Dependencies** | sqlalchemy, aiosqlite | montydb |
| **Query Language** | SQLAlchemy ORM | MongoDB Query Language (MQL) |

## Installation & Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Database Initialization

MontyDB automatically creates the database repository on first use:
- Location: `data/db_repo/`
- Structure: Auto-created with flat-file layout
- No migration scripts needed

## MQL Query Reference

MontyDB uses MongoDB Query Language (MQL) for all operations. Here are common patterns:

### Finding Documents

```python
from app.core.database import get_users_collection

users = get_users_collection()

# Find one document by ID
user = users.find_one({"id": "user-uuid-string"})

# Find one by email
user = users.find_one({"email": "teacher@example.com"})

# Find multiple documents
teacher_users = users.find({"school_name": "Primary School"})

# Find with condition
recent_users = users.find({"created_at": {"$gte": "2024-01-01"}})
```

### Inserting Documents

```python
from app.models.user import User
from app.core.database import get_users_collection

users = get_users_collection()

# Create Pydantic model
new_user = User(
    name="Ramesh Kumar",
    email="ramesh@example.com",
    password_hash=hash_password("secret123"),
    school_name="Govt Primary School"
)

# Convert to dict and insert
user_dict = new_user.model_dump()
users.insert_one(user_dict)
```

### Updating Documents

```python
users = get_users_collection()

# Update single field
users.update_one(
    {"id": "user-123"},
    {"$set": {"school_name": "New School Name"}}
)

# Update multiple fields
users.update_one(
    {"id": "user-123"},
    {"$set": {
        "school_name": "New School",
        "updated_at": datetime.utcnow().isoformat()
    }}
)
```

### Deleting Documents

```python
users = get_users_collection()

# Delete single document
result = users.delete_one({"id": "user-123"})

# Delete multiple documents
result = users.delete_many({"school_name": "Closed School"})
```

## API Pattern Examples

### Registration Endpoint

```python
@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn):
    """Register a new user using MontyDB collection."""
    users_collection = get_users_collection()
    
    # Check if user already exists using MQL syntax
    existing = users_collection.find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user document
    user_data = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    
    # Insert document
    user_dict = user_data.model_dump()
    users_collection.insert_one(user_dict)
    
    # Generate token
    token = create_access_token(user_data.id)
    return TokenOut(access_token=token, user=_user_to_dict(user_dict))
```

### Attendance Endpoint Example

```python
from app.core.database import get_attendance_collection
from app.models.attendance import AttendanceRecord
from datetime import date

@router.post("/attendance", response_model=dict)
def log_attendance(student_id: str, status: str, teacher_id: str = Depends(get_current_user)):
    """Log student attendance using MontyDB."""
    attendance_collection = get_attendance_collection()
    
    # Create attendance record
    record = AttendanceRecord(
        student_id=student_id,
        teacher_id=teacher_id.get("id"),
        date=date.today(),
        status=status  # present | absent | late
    )
    
    # Insert document
    attendance_collection.insert_one(record.model_dump())
    
    return {"status": "success", "message": "Attendance logged"}
```

### Query with Nested Filters

```python
from app.core.database import get_attendance_collection
from datetime import datetime, timedelta

attendance = get_attendance_collection()

# Find attendance records for a student in a date range
start_date = (datetime.now() - timedelta(days=30)).isoformat()
records = attendance.find({
    "student_id": "student-123",
    "date": {"$gte": start_date}
})

for record in records:
    print(f"Date: {record['date']}, Status: {record['status']}")
```

## Working with Extracted Documents

MontyDB excels at storing deeply nested JSON structures. Example:

```python
from app.models.extracted import ExtractedRegisterData
from app.core.database import get_extracted_data_collection

extracted = get_extracted_data_collection()

# Create polymorphic document wrapper
doc = ExtractedRegisterData(
    teacher_id="teacher-456",
    register_type="daily_pm_poshan",
    file_path="uploads/attendance/file_123.jpg",
    raw_json={
        "classification": {
            "type": "daily_pm_poshan",
            "confidence": "high"
        },
        "data": {
            "date": "2024-06-10",
            "meal_type": "lunch",
            "beneficiaries": 45,
            "meals_served": 42,
            "items": {
                "rice_kg": 12.5,
                "dal_kg": 3.2,
                "vegetables_kg": 8.1,
                "oil_l": 1.5
            }
        }
    },
    validation_status="pending"
)

# Insert document
extracted.insert_one(doc.model_dump())

# Later, verify and patch
extracted.update_one(
    {"id": doc.id},
    {"$set": {
        "payload": updated_payload,
        "is_verified": True,
        "validation_status": "validated"
    }}
)
```

## Handling DateTime in Pydantic Models

All Pydantic models include datetime fields. When storing/retrieving:

```python
from datetime import datetime

# Models automatically serialize datetime to ISO format
record = User(
    name="Teacher Name",
    email="teacher@example.com",
    created_at=datetime.utcnow()
)

# When converting to dict for storage
record_dict = record.model_dump()
# created_at is now ISO format string

# When retrieving from collection, convert back if needed
doc = users.find_one({"id": user_id})
created_date = datetime.fromisoformat(doc["created_at"])
```

## Removing MontyDB Internal Fields

MontyDB adds an `_id` field to all documents. Always clean it up before returning to API:

```python
def _user_to_dict(u: dict) -> dict:
    """Convert user document to response, removing internal fields."""
    u.pop("_id", None)  # Remove MontyDB internal ID
    u.pop("password_hash", None)  # Don't expose passwords
    return u
```

## Collection Access Functions

The `database.py` module provides getter functions for each collection:

```python
from app.core.database import (
    get_users_collection,
    get_registers_collection,
    get_attendance_collection,
    get_extracted_data_collection
)

# Use in your endpoints
@router.get("/data")
def get_data():
    users = get_users_collection()
    registers = get_registers_collection()
    # ... your logic
```

## API Endpoints to Migrate

The following endpoints require refactoring to use MontyDB. Use the patterns above:

- [ ] `POST /api/students` - Create student
- [ ] `GET /api/students` - List students
- [ ] `GET /api/students/{id}` - Get student
- [ ] `PUT /api/students/{id}` - Update student
- [ ] `DELETE /api/students/{id}` - Delete student
- [ ] `POST /api/attendance` - Log attendance
- [ ] `GET /api/attendance` - Query attendance
- [ ] `POST /api/poshan` - Log meal data
- [ ] `GET /api/poshan` - Query meal records
- [ ] `POST /api/audit` - Upload audit document
- [ ] `GET /api/audit` - Query audit docs
- [ ] `POST /api/chat` - Send message
- [ ] `GET /api/chat/history` - Get chat history
- [ ] `POST /api/upload` - Upload register image
- [ ] `GET /api/dashboard` - Dashboard metrics

## Dependency Injection Pattern

For cleaner code, MontyDB collections can be passed as dependencies:

```python
from fastapi import Depends
from app.core.database import get_users_collection

def users_collection_dependency():
    return get_users_collection()

@router.get("/users")
def list_users(users = Depends(users_collection_dependency)):
    return list(users.find({}))
```

## Querying Complex Nested Data

MontyDB supports dot notation for nested queries:

```python
from app.core.database import get_extracted_data_collection

extracted = get_extracted_data_collection()

# Query nested field
high_confidence = extracted.find({
    "raw_json.classification.confidence": "high"
})

# Query array elements
for doc in high_confidence:
    confidence = doc["raw_json"]["classification"]["confidence"]
    print(f"Document type: {doc['register_type']}, Confidence: {confidence}")
```

## Transactions & Validation

For multi-step operations, you may want to add validation:

```python
def save_and_validate_extraction(doc_data: dict):
    """Save extracted data with validation."""
    extracted = get_extracted_data_collection()
    
    # Create document from Pydantic model
    doc = ExtractedRegisterData(**doc_data)
    
    # Validate before insert
    if not doc.raw_json:
        raise ValueError("Extracted data cannot be empty")
    
    # Insert
    extracted.insert_one(doc.model_dump())
    return doc
```

## Testing Your Migration

### 1. Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Test Registration

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Teacher",
    "email": "test@example.com",
    "password": "securepass123",
    "school_name": "Test School"
  }'
```

### 3. Test Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepass123"
  }'
```

### 4. Verify Data Persistence

```bash
ls -la data/db_repo/
# You should see JSON files for each collection
```

## Performance Considerations

- **Indexing**: MontyDB automatically indexes ID and simple fields
- **Disk Usage**: JSON storage is less efficient than binary databases; ~2-3x size
- **Query Speed**: Suitable for small-to-medium datasets (< 100K documents)
- **Concurrent Access**: Single-file collections support concurrent reads; limit simultaneous writes

## Troubleshooting

### "MontyClient not initialized"
Solution: Ensure `data/db_repo/` directory exists and is writable

### "KeyError: '_id'"
Solution: Always use `doc.pop("_id", None)` before returning documents

### UUID not found
Solution: User IDs are strings, not integers. Use string comparison in queries

### "Cannot decode JSON"
Solution: Ensure datetime objects are converted to ISO format strings

## Common Migration Patterns

### From SQLAlchemy Session Query
```python
# Before (SQLAlchemy)
user = db.query(User).filter(User.email == email).first()

# After (MontyDB)
users = get_users_collection()
user = users.find_one({"email": email})
```

### From SQLAlchemy Relationship
```python
# Before (SQLAlchemy)
teacher = db.query(User).filter(User.id == teacher_id).first()
students = db.query(Student).filter(Student.teacher_id == teacher.id).all()

# After (MontyDB)
students = get_students_collection()
students_for_teacher = list(students.find({"teacher_id": teacher_id}))
```

### From SQLAlchemy Bulk Insert
```python
# Before (SQLAlchemy)
db.add_all([student1, student2, student3])
db.commit()

# After (MontyDB)
students = get_students_collection()
students.insert_many([
    student1.model_dump(),
    student2.model_dump(),
    student3.model_dump()
])
```

## Next Steps

1. ✅ Core infrastructure migrated
2. ⏳ Refactor remaining API endpoints (see list above)
3. ⏳ Test all CRUD operations
4. ⏳ Verify authentication flow
5. ⏳ Load test with sample data
6. ⏳ Deploy to production

## Support & Documentation

- [MontyDB GitHub](https://github.com/scottpersinger/montydb)
- [MongoDB Query Language Reference](https://docs.mongodb.com/manual/reference/method/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
