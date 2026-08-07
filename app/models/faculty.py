"""Faculty profile model."""

from app.extensions import db
from app.models.base import TimestampMixin


class Faculty(TimestampMixin, db.Model):
    """Academic profile for a faculty user."""

    __tablename__ = "faculty"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    employee_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    mobile_number = db.Column(db.String(20))
    qualification = db.Column(db.String(120))
    department = db.Column(db.String(120), nullable=False)
    joining_date = db.Column(db.Date)
    profile_image = db.Column(db.String(255))

    user = db.relationship("User", back_populates="faculty_profile")
    subjects = db.relationship("Subject", back_populates="faculty")
    attendance_records = db.relationship("Attendance", back_populates="faculty")
    marks_entered = db.relationship("Marks", back_populates="entered_by_user")
    materials = db.relationship("StudyMaterial", back_populates="faculty")
    assignments = db.relationship("Assignment", back_populates="faculty")

    def __repr__(self) -> str:
        return f"<Faculty {self.employee_id}>"
