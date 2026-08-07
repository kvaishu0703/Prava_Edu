"""Student profile model."""

from app.extensions import db
from app.models.base import TimestampMixin


class Student(TimestampMixin, db.Model):
    """Academic profile for a student user."""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    enrollment_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    mobile_number = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    address = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    admission_year = db.Column(db.Integer, nullable=False)
    profile_image = db.Column(db.String(255))

    user = db.relationship("User", back_populates="student_profile")
    course = db.relationship("Course", back_populates="students")
    attendance_records = db.relationship(
        "Attendance",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    marks_records = db.relationship(
        "Marks",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    submissions = db.relationship(
        "Submission",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Student {self.enrollment_number}>"
