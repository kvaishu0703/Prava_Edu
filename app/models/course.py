"""Course model."""

from app.extensions import db
from app.models.base import TimestampMixin


class Course(TimestampMixin, db.Model):
    """College course such as BCA."""

    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    duration = db.Column(db.String(50), nullable=False)
    total_semesters = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    students = db.relationship("Student", back_populates="course")
    subjects = db.relationship("Subject", back_populates="course")

    def __repr__(self) -> str:
        return f"<Course {self.code}>"
