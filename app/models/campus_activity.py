"""Scheduled college activities and staff-verified participation."""
from app.extensions import db
from app.models.base import TimestampMixin


class CampusActivity(TimestampMixin, db.Model):
    __tablename__ = 'campus_activities'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    department = db.Column(db.String(30), nullable=False, default='all')
    starts_at = db.Column(db.DateTime, nullable=False)
    venue = db.Column(db.String(180), nullable=False)
    coordinator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    coordinator = db.relationship('User')
    participations = db.relationship('ActivityParticipation', back_populates='activity')


class ActivityParticipation(TimestampMixin, db.Model):
    __tablename__ = 'activity_participations'
    __table_args__ = (db.UniqueConstraint('activity_id', 'student_id', name='uq_activity_student'),)
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('campus_activities.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    status = db.Column(db.String(30), default='Registered', nullable=False)
    evidence = db.Column(db.Text)
    hours = db.Column(db.Numeric(5, 1))
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    activity = db.relationship('CampusActivity', back_populates='participations')
    student = db.relationship('Student')
    reviewer = db.relationship('User')
