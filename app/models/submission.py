"""Assignment submission model."""

from app.extensions import db
from app.models.base import utc_now


class Submission(db.Model):
    """Student file submission for an assignment."""

    __tablename__ = "submissions"
    __table_args__ = (
        db.UniqueConstraint("assignment_id", "student_id", name="uq_submission_assignment_student"),
    )

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    submitted_file = db.Column(db.String(255))
    submitted_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(30), default="Pending", nullable=False)
    marks_obtained = db.Column(db.Integer)
    faculty_feedback = db.Column(db.Text)
    graded_at = db.Column(db.DateTime(timezone=True))

    assignment = db.relationship("Assignment", back_populates="submissions")
    student = db.relationship("Student", back_populates="submissions")

    def mark_submitted(self, file_path: str) -> None:
        """Update the submission when a student uploads work."""
        self.submitted_file = file_path
        self.submitted_at = utc_now()
        self.status = "Submitted"

    def __repr__(self) -> str:
        return f"<Submission assignment={self.assignment_id} student={self.student_id}>"
