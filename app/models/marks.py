"""Marks model."""

from app.extensions import db
from app.models.base import TimestampMixin


class Marks(TimestampMixin, db.Model):
    """Marks obtained by one student in one subject and exam type."""

    __tablename__ = "marks"
    __table_args__ = (
        db.UniqueConstraint("student_id", "subject_id", "exam_type", name="uq_marks_student_subject_exam"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False)
    internal_marks = db.Column(db.Integer, default=0, nullable=False)
    external_marks = db.Column(db.Integer, default=0, nullable=False)
    total_marks = db.Column(db.Integer, default=0, nullable=False)
    grade = db.Column(db.String(5))
    remarks = db.Column(db.String(255))
    entered_by = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False)

    student = db.relationship("Student", back_populates="marks_records")
    subject = db.relationship("Subject", back_populates="marks_records")
    entered_by_user = db.relationship("Faculty", back_populates="marks_entered")

    def __repr__(self) -> str:
        return f"<Marks student={self.student_id} subject={self.subject_id} total={self.total_marks}>"
