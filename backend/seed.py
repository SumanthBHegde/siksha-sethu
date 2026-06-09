"""Seed a demo teacher + students + a few days of attendance and meal records."""
from datetime import date, timedelta
import random

from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models import User, Student, AttendanceRecord, MealRecord, StockRecord


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "teacher@demo.in").first():
            print("Demo data already seeded.")
            return

        teacher = User(
            name="Ms. Lakshmi Devi",
            email="teacher@demo.in",
            school_name="Govt. Higher Primary School, Bengaluru",
            password_hash=hash_password("password"),
        )
        db.add(teacher)
        db.flush()

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
            db.add(s)
            students.append(s)
        db.flush()

        # Attendance for last 20 days
        today = date.today()
        for i in range(20):
            d = today - timedelta(days=i)
            if d.weekday() == 6:  # Skip Sundays
                continue
            for s in students:
                # ~92% attendance overall, a few low-attendance students
                low = s.roll_no in {"07", "13"}
                p = 0.55 if low else 0.92
                status = "present" if random.random() < p else random.choice(["absent", "absent", "late"])
                db.add(AttendanceRecord(
                    student_id=s.id, teacher_id=teacher.id, date=d,
                    status=status, source="manual",
                ))

        # Meals for last 15 working days
        for i in range(15):
            d = today - timedelta(days=i)
            if d.weekday() == 6:
                continue
            served = random.randint(12, 15)
            db.add(MealRecord(
                teacher_id=teacher.id, date=d, meal_type="lunch",
                beneficiaries=15, meals_served=served,
                rice_kg=served * 0.1, dal_kg=served * 0.03,
                vegetables_kg=served * 0.05, oil_l=served * 0.01,
                source="manual",
            ))

        # Stock snapshots
        items = [
            ("rice", 50.0, 15.0),
            ("dal", 20.0, 8.0),
            ("oil", 10.0, 3.5),
            ("vegetables", 8.0, 4.0),
        ]
        for item, opening, consumed in items:
            db.add(StockRecord(
                teacher_id=teacher.id, item=item, date=today,
                opening_kg=opening, received_kg=0, consumed_kg=consumed,
                closing_kg=opening - consumed, source="manual",
            ))

        db.commit()
        print("✓ Seeded teacher: teacher@demo.in / password")
        print(f"✓ Seeded {len(students)} students")
        print("✓ Seeded ~20 days of attendance + 15 days of meals + stock snapshot")
    finally:
        db.close()


if __name__ == "__main__":
    main()
