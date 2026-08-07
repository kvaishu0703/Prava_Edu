"""Subject model."""

from app.extensions import db
from app.models.base import TimestampMixin


class Subject(TimestampMixin, db.Model):
    """Subject taught in a course semester."""

    __tablename__ = "subjects"
    __table_args__ = (
        db.UniqueConstraint("code", "course_id", "semester", name="uq_subject_code_course_semester"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(30), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"))
    maximum_marks = db.Column(db.Integer, default=100, nullable=False)
    passing_marks = db.Column(db.Integer, default=40, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    course = db.relationship("Course", back_populates="subjects")
    faculty = db.relationship("Faculty", back_populates="subjects")
    attendance_records = db.relationship("Attendance", back_populates="subject")
    marks_records = db.relationship("Marks", back_populates="subject")
    materials = db.relationship("StudyMaterial", back_populates="subject")
    assignments = db.relationship("Assignment", back_populates="subject")

    def __repr__(self) -> str:
        return f"<Subject {self.code}>"
