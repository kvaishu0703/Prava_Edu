"""Study material model."""

from app.extensions import db
from app.models.base import utc_now


class StudyMaterial(db.Model):
    """Uploaded notes, books, presentations, and other learning files."""

    __tablename__ = "study_materials"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(30), nullable=False)
    uploaded_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    subject = db.relationship("Subject", back_populates="materials")
    faculty = db.relationship("Faculty", back_populates="materials")

    def __repr__(self) -> str:
        return f"<StudyMaterial {self.title}>"
