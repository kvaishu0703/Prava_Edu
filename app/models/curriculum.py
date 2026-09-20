"""Versioned university curriculum, separate from teaching assignments."""
from app.extensions import db
from app.models.base import TimestampMixin


class Curriculum(TimestampMixin, db.Model):
    __tablename__ = 'curricula'
    __table_args__ = (db.UniqueConstraint('course_id', 'pattern', name='uq_curriculum_course_pattern'),)
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    pattern = db.Column(db.String(80), nullable=False)
    university = db.Column(db.String(160), nullable=False, default='Savitribai Phule Pune University')
    faculty = db.Column(db.String(100), default='Science and Technology', nullable=False)
    effective_year = db.Column(db.Integer, nullable=False)
    course = db.relationship('Course', backref='curricula')
    documents = db.relationship('SyllabusDocument', back_populates='curriculum', cascade='all, delete-orphan')
    subjects = db.relationship('CurriculumSubject', back_populates='curriculum', cascade='all, delete-orphan')


class SyllabusDocument(TimestampMixin, db.Model):
    __tablename__ = 'syllabus_documents'
    __table_args__ = (db.UniqueConstraint('curriculum_id', 'year', name='uq_syllabus_year'),)
    id = db.Column(db.Integer, primary_key=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curricula.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(180), nullable=False)
    source_url = db.Column(db.String(1000))
    status = db.Column(db.String(30), nullable=False, default='pending')
    notes = db.Column(db.Text)
    checked_at = db.Column(db.Date)
    curriculum = db.relationship('Curriculum', back_populates='documents')


class CurriculumSubject(TimestampMixin, db.Model):
    __tablename__ = 'curriculum_subjects'
    __table_args__ = (db.UniqueConstraint('curriculum_id', 'semester', 'code', name='uq_curriculum_subject'),)
    id = db.Column(db.Integer, primary_key=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curricula.id'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    code = db.Column(db.String(60), nullable=False)
    name = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    credits = db.Column(db.Numeric(4, 1), nullable=False)
    internal_max = db.Column(db.Integer)
    external_max = db.Column(db.Integer)
    practical_max = db.Column(db.Integer)
    units = db.Column(db.Text)
    source_url = db.Column(db.String(1000), nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    curriculum = db.relationship('Curriculum', back_populates='subjects')
