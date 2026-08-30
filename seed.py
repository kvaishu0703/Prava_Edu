"""Create development database tables and sample data."""

from datetime import date, datetime, timedelta, timezone
import sys

from app import create_app
from app.extensions import db
from app.models import (
    ActivityLog,
    Assignment,
    Attendance,
    Course,
    Faculty,
    Marks,
    Notification,
    Student,
    StudyMaterial,
    Subject,
    Submission,
    User,
)
from app.services.supabase_auth import SupabaseAuthError, upsert_auth_user


def create_user(username: str, full_name: str, email: str, role: str, password: str) -> User:
    """Create a user and hash the password before saving."""
    user = User(username=username, full_name=full_name, email=email, role=role)
    user.set_password(password)
    try:
        upsert_auth_user(email=email, password=password, full_name=full_name, role=role)
    except SupabaseAuthError as exc:
        raise RuntimeError(f"Could not create Supabase Auth user for {email}: {exc}") from exc
    db.session.add(user)
    return user


def grade_for(total_marks: int) -> str:
    """Return a simple grade for seed marks."""
    if total_marks >= 90:
        return "A+"
    if total_marks >= 80:
        return "A"
    if total_marks >= 70:
        return "B+"
    if total_marks >= 60:
        return "B"
    if total_marks >= 50:
        return "C"
    if total_marks >= 40:
        return "D"
    return "F"


def seed_database(reset: bool = False) -> None:
    """Create tables and insert beginner-friendly sample data."""
    if reset:
        db.drop_all()

    db.create_all()

    if User.query.filter_by(username="admin").first():
        print("Sample data already exists. Use: python seed.py --reset")
        return

    admin_user = create_user(
        "admin",
        "System Admin",
        "admin@example.com",
        "admin",
        "Admin@123",
    )

    faculty_users = [
        create_user("faculty", "Dr. Anjali Patil", "faculty@example.com", "faculty", "Faculty@123"),
        create_user("faculty_ds", "Prof. Rahul Deshmukh", "rahul@example.com", "faculty", "Faculty@123"),
        create_user("faculty_py", "Prof. Meera Kulkarni", "meera@example.com", "faculty", "Faculty@123"),
    ]

    course = Course(
        name="Bachelor of Computer Applications",
        code="BCA",
        description="Computer applications, programming, databases, web technology, and practical software development.",
        duration="3 Years",
        total_semesters=6,
    )
    db.session.add(course)
    db.session.flush()

    faculty_profiles = [
        Faculty(
            user=faculty_users[0],
            employee_id="FAC001",
            mobile_number="9876543201",
            qualification="MCA, PhD",
            department="Computer Applications",
            joining_date=date(2020, 7, 1),
        ),
        Faculty(
            user=faculty_users[1],
            employee_id="FAC002",
            mobile_number="9876543202",
            qualification="M.Tech",
            department="Computer Applications",
            joining_date=date(2021, 8, 2),
        ),
        Faculty(
            user=faculty_users[2],
            employee_id="FAC003",
            mobile_number="9876543203",
            qualification="M.Sc Computer Science",
            department="Computer Applications",
            joining_date=date(2022, 6, 15),
        ),
    ]
    db.session.add_all(faculty_profiles)
    db.session.flush()

    subjects = [
        Subject(name="Data Structures", code="BCA501", course=course, semester=5, faculty=faculty_profiles[1]),
        Subject(name="Database Management System", code="BCA502", course=course, semester=5, faculty=faculty_profiles[0]),
        Subject(name="Python Programming", code="BCA503", course=course, semester=5, faculty=faculty_profiles[2]),
        Subject(name="Operating System", code="BCA504", course=course, semester=5, faculty=faculty_profiles[0]),
        Subject(name="Web Technology", code="BCA505", course=course, semester=5, faculty=faculty_profiles[2]),
        Subject(name="Software Engineering", code="BCA506", course=course, semester=5, faculty=faculty_profiles[1]),
    ]
    db.session.add_all(subjects)
    db.session.flush()

    student_names = [
        ("Vaishnavi Kale", "vaishnavi", "vaishnavi@example.com"),
        ("Rohit Patil", "rohit", "rohit@example.com"),
        ("Sneha Jadhav", "sneha", "sneha@example.com"),
        ("Amit Singh", "amit", "amit@example.com"),
        ("Pooja Sharma", "pooja", "pooja@example.com"),
        ("Yash Verma", "yash", "yash@example.com"),
        ("Neha Gupta", "neha", "neha@example.com"),
        ("Kiran More", "kiran", "kiran@example.com"),
        ("Priya Joshi", "priya", "priya@example.com"),
        ("Sagar Pawar", "sagar", "sagar@example.com"),
    ]

    students = []
    for index, (full_name, username, email) in enumerate(student_names, start=1):
        password = "Student@123" if username == "vaishnavi" else "Student@123"
        if username == "vaishnavi":
            username = "student"
        user = create_user(username, full_name, email, "student", password)
        student = Student(
            user=user,
            enrollment_number=f"BCA2024{index:03d}",
            mobile_number=f"98765000{index:02d}",
            date_of_birth=date(2003, min(index, 12), min(index + 5, 28)),
            gender="Female" if index in {1, 3, 5, 7, 9} else "Male",
            address=f"Sample Address {index}, Pune",
            course=course,
            semester=5,
            admission_year=2022,
        )
        students.append(student)
    db.session.add_all(students)
    db.session.flush()

    attendance_dates = [date.today() - timedelta(days=offset) for offset in range(5)]
    for student_index, student in enumerate(students):
        for subject in subjects[:3]:
            for attendance_date in attendance_dates:
                status = "Absent" if (student_index + attendance_date.day + subject.id) % 7 == 0 else "Present"
                db.session.add(
                    Attendance(
                        student=student,
                        subject=subject,
                        faculty=subject.faculty,
                        attendance_date=attendance_date,
                        status=status,
                    )
                )

    for student_index, student in enumerate(students):
        for subject_index, subject in enumerate(subjects[:4]):
            internal = 14 + ((student_index + subject_index) % 6)
            external = 48 + ((student_index * 4 + subject_index * 5) % 35)
            total = internal + external
            db.session.add(
                Marks(
                    student=student,
                    subject=subject,
                    exam_type="Semester Exam",
                    internal_marks=internal,
                    external_marks=external,
                    total_marks=total,
                    grade=grade_for(total),
                    remarks="Sample marks",
                    entered_by_user=subject.faculty,
                )
            )

    materials = [
        StudyMaterial(
            title="Data Structures Notes",
            description="Linked list, stack, queue, and tree basics.",
            subject=subjects[0],
            faculty=subjects[0].faculty,
            file_name="data-structures-notes.pdf",
            file_path="uploads/materials/data-structures-notes.pdf",
            file_type="pdf",
        ),
        StudyMaterial(
            title="DBMS Notes",
            description="Database design and SQL basics.",
            subject=subjects[1],
            faculty=subjects[1].faculty,
            file_name="dbms-notes.pdf",
            file_path="uploads/materials/dbms-notes.pdf",
            file_type="pdf",
        ),
        StudyMaterial(
            title="Python Basics",
            description="Variables, functions, lists, and dictionaries.",
            subject=subjects[2],
            faculty=subjects[2].faculty,
            file_name="python-basics.pdf",
            file_path="uploads/materials/python-basics.pdf",
            file_type="pdf",
        ),
    ]
    db.session.add_all(materials)

    now = datetime.now(timezone.utc)
    assignments = [
        Assignment(
            title="Math Assignment 1",
            description="Practice problems for internal assessment.",
            subject=subjects[0],
            faculty=subjects[0].faculty,
            due_date=now + timedelta(days=7),
            maximum_marks=100,
        ),
        Assignment(
            title="DBMS Assignment",
            description="Draw ER diagram and write SQL queries.",
            subject=subjects[1],
            faculty=subjects[1].faculty,
            due_date=now + timedelta(days=5),
            maximum_marks=100,
        ),
        Assignment(
            title="Python Assignment",
            description="Create a simple menu-driven Python program.",
            subject=subjects[2],
            faculty=subjects[2].faculty,
            due_date=now + timedelta(days=10),
            maximum_marks=100,
        ),
    ]
    db.session.add_all(assignments)
    db.session.flush()

    for student in students[:5]:
        db.session.add(
            Submission(
                assignment=assignments[0],
                student=student,
                submitted_file=f"uploads/submissions/{student.enrollment_number}-math.pdf",
                submitted_at=now - timedelta(days=1),
                status="Submitted",
            )
        )

    notifications = [
        Notification(
            title="Holiday Announcement",
            message="College will remain closed on Friday.",
            notification_type="Holiday",
            creator=admin_user,
            target_role="all",
        ),
        Notification(
            title="Exam Schedule Released",
            message="Mid-term exam schedule has been published.",
            notification_type="Exam",
            creator=admin_user,
            target_role="student",
            target_course=course,
            target_semester=5,
        ),
        Notification(
            title="New Assignment Published",
            message="Data Structures assignment has been published.",
            notification_type="Assignment",
            creator=faculty_users[1],
            target_role="student",
            target_course=course,
            target_semester=5,
        ),
    ]
    db.session.add_all(notifications)

    db.session.add(
        ActivityLog(
            user=admin_user,
            action="seed_database",
            module="database",
            description="Development sample data created.",
            ip_address="127.0.0.1",
        )
    )

    db.session.commit()
    print("Database tables and sample data created successfully.")
    print("Admin: admin / Admin@123")
    print("Faculty: faculty / Faculty@123")
    print("Student: student / Student@123")


def main() -> None:
    """Run the seed command inside the Flask app context."""
    app = create_app()
    with app.app_context():
        seed_database(reset="--reset" in sys.argv)


if __name__ == "__main__":
    main()
