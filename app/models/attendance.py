"""Attendance model."""

from app.extensions import db
from app.models.base import utc_now


class Attendance(db.Model):
    """Daily attendance entry for one student and subject."""

    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "subject_id",
            "attendance_date",
            "session_number",
            name="uq_attendance_student_subject_date_session",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)
    session_number = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    session_type = db.Column(db.String(20), nullable=False, default="Theory", server_default="Theory")
    starts_at = db.Column(db.Time)
    ends_at = db.Column(db.Time)
    timetable_slot_id = db.Column(db.Integer, db.ForeignKey("timetable_slots.id"))
    remarks = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    student = db.relationship("Student", back_populates="attendance_records")
    subject = db.relationship("Subject", back_populates="attendance_records")
    faculty = db.relationship("Faculty", back_populates="attendance_records")
    timetable_slot = db.relationship("TimetableSlot")

    def __repr__(self) -> str:
        return f"<Attendance student={self.student_id} subject={self.subject_id} date={self.attendance_date}>"
