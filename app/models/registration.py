"""Student sign-up requests, kept separate from verified academic records."""
from app.extensions import db
from app.models.base import TimestampMixin


class StudentRegistration(TimestampMixin, db.Model):
    __tablename__ = 'student_registrations'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    enrollment_number = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curricula.id'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    admission_year = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending', index=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime(timezone=True))
    review_note = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    curriculum = db.relationship('Curriculum')
    user = db.relationship('User', foreign_keys=[user_id])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
