"""Weekly teaching sessions, scoped to a programme, semester and academic year."""
from app.extensions import db


class TimetableSlot(db.Model):
    __tablename__ = 'timetable_slots'
    __table_args__ = (
        db.UniqueConstraint('curriculum_id', 'semester', 'academic_year', 'weekday', 'batch', 'session_number', name='uq_timetable_class_slot'),
        db.CheckConstraint('weekday >= 0 AND weekday <= 5', name='ck_timetable_weekday'),
        db.CheckConstraint('session_number >= 1 AND session_number <= 6', name='ck_timetable_session'),
    )
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curricula.id'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.Integer, nullable=False)
    weekday = db.Column(db.Integer, nullable=False)
    session_number = db.Column(db.Integer, nullable=False)
    starts_at = db.Column(db.Time, nullable=False)
    ends_at = db.Column(db.Time, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    session_type = db.Column(db.String(20), nullable=False)
    batch = db.Column(db.String(10), nullable=False, default='All')
    room = db.Column(db.String(80), nullable=False)
    subject_label = db.Column(db.String(120))
    teacher_code = db.Column(db.String(30))
    source = db.Column(db.String(80), nullable=False)

    course = db.relationship('Course')
    curriculum = db.relationship('Curriculum')
    subject = db.relationship('Subject')
    faculty = db.relationship('Faculty')

    @property
    def title(self):
        return self.subject_label or self.subject.name

    @property
    def teacher_label(self):
        return self.teacher_code or self.faculty.user.display_name
