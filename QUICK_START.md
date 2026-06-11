# MontyDB Migration - Quick Start Guide

## ✅ Your migration is complete!

The ShikshaSetu backend has been successfully migrated from SQLAlchemy/SQLite to MontyDB. All database operations now use MongoDB Query Language with file-based storage.

## 🚀 Quick Start (2 minutes)

### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Start Backend
```bash
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 3: Verify Database Created
```bash
ls -la data/db_repo/shala_document_db/
```

You should see collection directories created automatically.

## 🧪 Test the API

### Test 1: Register User
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Teacher",
    "email": "teacher@test.com",
    "password": "TestPass123!",
    "school_name": "Government School"
  }'
```

Expected response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Test Teacher",
    "email": "teacher@test.com",
    "school_name": "Government School"
  }
}
```

### Test 2: Login
```bash
curl -X POST http://localhost:8000/api/auth/login-json \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@test.com",
    "password": "TestPass123!"
  }'
```

### Test 3: Get Current User
```bash
# Replace TOKEN with the access_token from login
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer TOKEN"
```

### Test 4: Create Student
```bash
# Replace TOKEN
curl -X POST http://localhost:8000/api/students \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "roll_no": "001",
    "name": "Student Name",
    "grade": "5",
    "section": "A",
    "gender": "M"
  }'
```

### Test 5: List Students
```bash
curl -X GET http://localhost:8000/api/students \
  -H "Authorization: Bearer TOKEN"
```

## 📊 View Stored Data

### Check User Collection
```bash
cat data/db_repo/shala_document_db/users
```

### Check Students Collection
```bash
cat data/db_repo/shala_document_db/students
```

### List All Collections
```bash
ls -la data/db_repo/shala_document_db/
```

## 🔄 Start Full Stack (Backend + Frontend)

### Terminal 1 - Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 and test the UI.

## 📝 What Changed

| Before | After |
|--------|-------|
| SQLAlchemy ORM | Pydantic BaseModel |
| SQLite database | MontyDB JSON files |
| Auto-increment IDs | UUID strings |
| SQL queries | MongoDB Query Language |
| `db.query()` | `collection.find()` |
| `db.add()` | `collection.insert_one()` |

## 🔍 Key Files to Know

1. **`app/core/database.py`** - Database initialization
2. **`app/core/security.py`** - User authentication
3. **`app/api/auth.py`** - Reference implementation
4. **`app/services/analytics.py`** - Complex query patterns
5. **`MONTYDB_MIGRATION_GUIDE.md`** - Comprehensive reference

## 📖 MQL Query Patterns (MongoDB Query Language)

### Find One
```python
from app.core.database import get_users_collection
users = get_users_collection()
user = users.find_one({"email": "teacher@test.com"})
```

### Find Multiple
```python
students = list(students_col.find({"teacher_id": teacher_id}))
```

### Insert
```python
from app.models.student import Student
student = Student(name="John", roll_no="001", grade="5", teacher_id=teacher_id)
students_col.insert_one(student.model_dump())
```

### Update
```python
students_col.update_one({"id": student_id}, {"$set": {"name": "Jane"}})
```

### Delete
```python
students_col.delete_one({"id": student_id})
```

## ✅ Verification Checklist

- [ ] Backend starts without errors
- [ ] `data/db_repo/` directory created
- [ ] Can register a user
- [ ] Can login
- [ ] Can view current user info
- [ ] Can create a student
- [ ] Can list students
- [ ] Frontend connects to backend
- [ ] Can login from frontend
- [ ] Dashboard loads without errors

## 🛠️ Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'montydb'"
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Permission denied" on `data/db_repo`
**Solution:** Ensure write permissions
```bash
chmod 755 data/db_repo
```

### Issue: Collections not created
**Solution:** They auto-create on first insert. Start the app and register a user.

### Issue: Frontend can't reach backend
**Solution:** Verify backend is running on port 8000
```bash
lsof -i :8000
```

## 📚 Documentation

- **Detailed Guide**: [MONTYDB_MIGRATION_GUIDE.md](./backend/MONTYDB_MIGRATION_GUIDE.md)
- **API Docs**: http://localhost:8000/docs (when backend is running)
- **Implementation Examples**: `app/api/auth.py`, `app/services/analytics.py`

## 🎯 Next Steps

1. **Verify Everything Works**
   - Run all tests above
   - Check dashboard loads

2. **Load Sample Data** (Optional)
   - Use the frontend to create some data
   - Test analytics and reports

3. **Review Code Changes**
   - Compare before/after in git
   - Understand the MQL patterns

4. **Deploy**
   - Backend is now ready for production
   - No external database infrastructure needed

## ❓ Questions?

- Check `MONTYDB_MIGRATION_GUIDE.md` for patterns
- Review `app/api/auth.py` for auth examples
- Look at `app/services/analytics.py` for complex queries
- Refer to [MongoDB Documentation](https://docs.mongodb.com/) for MQL syntax

---

**Happy migrating! 🚀**

Your backend is now running on MontyDB with no external database infrastructure required!
