"""Public student website test response model."""

import uuid

from app.extensions import db
from app.models.base import TimestampMixin


class StudentTestResponse(TimestampMixin, db.Model):
    """Store one scored response from the public student test form."""

    __tablename__ = "student_test_responses"

    id = db.Column(db.Integer, primary_key=True)
    public_token = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    college_name = db.Column(db.String(160))
    course_year = db.Column(db.String(80), nullable=False)
    answers_json = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    website_rating = db.Column(db.Integer, nullable=False)
    feedback = db.Column(db.Text)

    @property
    def score_percentage(self) -> int:
        """Return a whole-number score percentage for display."""
        if not self.total_questions:
            return 0
        return round((self.score / self.total_questions) * 100)

    def __repr__(self) -> str:
        return f"<StudentTestResponse {self.email} score={self.score}/{self.total_questions}>"
