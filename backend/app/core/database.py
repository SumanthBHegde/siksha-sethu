import os
from montydb import MontyClient

# Ensure database repository directory exists
DB_REPO_DIR = "data/db_repo"
os.makedirs(DB_REPO_DIR, exist_ok=True)

# Initialize MontyClient pointed at the local directory repo
# Uses standard flat-file storage layout natively
client = MontyClient(DB_REPO_DIR)
db = client.shala_document_db


def get_users_collection():
    """Get users collection for authentication and account management."""
    return db.users


def get_registers_collection():
    """Get registers collection for extracted document storage."""
    return db.registers


def get_attendance_collection():
    """Get attendance records collection."""
    return db.attendance_records


def get_extracted_data_collection():
    """Get extracted register data collection."""
    return db.extracted_register_data


def get_students_collection():
    """Get students collection for student records."""
    return db.students


def get_chat_collection():
    """Get chat history collection."""
    return db.chat_history


def get_meal_collection():
    """Get meal records collection."""
    return db.meal_records


def get_audit_collection():
    """Get audit documents collection."""
    return db.audit_documents


def get_stock_collection():
    """Get stock records collection."""
    return db.stock_records


def get_db():
    """Dependency for FastAPI to provide database collection accessors."""
    return db
