"""Assignment model."""

from app.extensions import db
from app.models.base import utc_now


class Assignment(db.Model):
    """Assignment created by faculty for a subject."""

    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False)
    due_date = db.Column(db.DateTime(timezone=True), nullable=False)
    maximum_marks = db.Column(db.Integer, default=100, nullable=False)
    attachment_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    subject = db.relationship("Subject", back_populates="assignments")
    faculty = db.relationship("Faculty", back_populates="assignments")
    submissions = db.relationship(
        "Submission",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Assignment {self.title}>"
