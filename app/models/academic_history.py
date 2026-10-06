"""Read-only snapshots of completed academic years, separate from live registers."""
from app.extensions import db
from app.models.base import TimestampMixin


class AcademicYearRecord(TimestampMixin, db.Model):
    __tablename__ = 'academic_year_records'
    __table_args__ = (
        db.UniqueConstraint('student_id', 'academic_year', name='uq_student_academic_history_year'),
        db.CheckConstraint('study_year BETWEEN 1 AND 3', name='ck_history_study_year'),
        db.CheckConstraint('academic_year BETWEEN 2000 AND 2100', name='ck_history_academic_year'),
    )
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    academic_year = db.Column(db.Integer, nullable=False)
    study_year = db.Column(db.Integer, nullable=False)
    snapshot = db.Column(db.JSON, nullable=False)
    source_kind = db.Column(db.String(32), nullable=False)
    provenance = db.Column(db.String(500), nullable=False)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    student = db.relationship('Student', backref='academic_year_records')
    updated_by = db.relationship('User')

    @property
    def year_label(self):
        return f'{self.academic_year}–{self.academic_year + 1}'
