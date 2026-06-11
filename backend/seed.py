"""Seed a demo teacher + students + a few days of attendance and meal records."""
from datetime import date, timedelta
import random

from app.core.database import (
    get_users_collection,
    get_students_collection,
    get_attendance_collection,
    get_meal_collection,
    get_stock_collection,
)
from app.core.security import hash_password
from app.models import User, Student, AttendanceRecord, MealRecord, StockRecord


def main():
    users_col = get_users_collection()
    students_col = get_students_collection()
    attendance_col = get_attendance_collection()
    meal_col = get_meal_collection()
    stock_col = get_stock_collection()

    if users_col.find_one({"email": "teacher@demo.in"}):
        print("Demo data already seeded.")
        return

    teacher = User(
        name="Ms. Lakshmi Devi",
        email="teacher@demo.in",
        school_name="Govt. Higher Primary School, Bengaluru",
        password_hash=hash_password("password"),
    )
    users_col.insert_one(teacher.model_dump(mode="json"))

    students_data = [
        ("01", "Arjun Kumar"), ("02", "Priya Sharma"), ("03", "Rahul Verma"),
        ("04", "Sneha Reddy"), ("05", "Karthik Iyer"), ("06", "Ananya Patel"),
        ("07", "Vikram Singh"), ("08", "Meera Nair"), ("09", "Rohan Gupta"),
        ("10", "Divya Krishnan"), ("11", "Aditya Rao"), ("12", "Pooja Joshi"),
        ("13", "Siddharth Menon"), ("14", "Kavya Pillai"), ("15", "Manish Yadav"),
    ]
    students = []
    for roll, name in students_data:
        s = Student(roll_no=roll, name=name, grade="5", section="A", teacher_id=teacher.id)
        students_col.insert_one(s.model_dump(mode="json"))
        students.append(s)

    today = date.today()
    for i in range(20):
        d = today - timedelta(days=i)
        if d.weekday() == 6:  # Skip Sundays
            continue
        for s in students:
            low = s.roll_no in {"07", "13"}
            p = 0.55 if low else 0.92
            status = "present" if random.random() < p else random.choice(["absent", "absent", "late"])
            record = AttendanceRecord(
                student_id=s.id,
                teacher_id=teacher.id,
                date=d,
                status=status,
                source="manual",
            )
            attendance_col.insert_one(record.model_dump(mode="json"))

    for i in range(15):
        d = today - timedelta(days=i)
        if d.weekday() == 6:
            continue
        served = random.randint(12, 15)
        record = MealRecord(
            teacher_id=teacher.id,
            date=d,
            meal_type="lunch",
            beneficiaries=15,
            meals_served=served,
            rice_kg=served * 0.1,
            dal_kg=served * 0.03,
            vegetables_kg=served * 0.05,
            oil_l=served * 0.01,
            source="manual",
        )
        meal_col.insert_one(record.model_dump(mode="json"))

    items = [
        ("rice", 50.0, 15.0),
        ("dal", 20.0, 8.0),
        ("oil", 10.0, 3.5),
        ("vegetables", 8.0, 4.0),
    ]
    for item, opening, consumed in items:
        record = StockRecord(
            teacher_id=teacher.id,
            item=item,
            date=today,
            opening_kg=opening,
            received_kg=0,
            consumed_kg=consumed,
            closing_kg=opening - consumed,
            source="manual",
        )
        stock_col.insert_one(record.model_dump(mode="json"))

    print("✓ Seeded teacher: teacher@demo.in / password")
    print(f"✓ Seeded {len(students)} students")
    print("✓ Seeded ~20 days of attendance + 15 days of meals + stock snapshot")


if __name__ == "__main__":
    main()
