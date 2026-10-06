"""One class teacher for each programme, curriculum, semester and year."""
from app.extensions import db
from app.models.base import TimestampMixin


class ClassTeacherAssignment(TimestampMixin, db.Model):
    __tablename__ = "class_teacher_assignments"
    __table_args__ = (
        db.UniqueConstraint("course_id", "curriculum_id", "semester", "academic_year", name="uq_class_teacher_class_year"),
        db.CheckConstraint("semester >= 1 AND semester <= 12", name="ck_class_teacher_semester"),
    )
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    curriculum_id = db.Column(db.Integer, db.ForeignKey("curricula.id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.Integer, nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False, index=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default="true")
    course = db.relationship("Course")
    curriculum = db.relationship("Curriculum")
    faculty = db.relationship("Faculty")
    assigned_by = db.relationship("User")

    @property
    def label(self):
        return f"{self.course.code} / Semester {self.semester} / {self.curriculum.pattern}"
