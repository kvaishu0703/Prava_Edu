"""Daily staff attendance and an append-only record of corrections."""
from app.extensions import db
from app.models.base import utc_now


class StaffAttendance(db.Model):
    __tablename__ = "staff_attendance"
    __table_args__ = (
        db.UniqueConstraint("faculty_id", "attendance_date", name="uq_staff_attendance_day"),
        db.CheckConstraint("status IN ('Present', 'Absent', 'Leave', 'Holiday')", name="ck_staff_attendance_status"),
    )
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False, index=True)
    attendance_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)
    check_in = db.Column(db.Time)
    check_out = db.Column(db.Time)
    remarks = db.Column(db.String(255))
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    faculty = db.relationship("Faculty")
    recorded_by = db.relationship("User", foreign_keys=[recorded_by_id])
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    changes = db.relationship("StaffAttendanceChange", back_populates="attendance", order_by="StaffAttendanceChange.changed_at.desc()")


class StaffAttendanceChange(db.Model):
    __tablename__ = "staff_attendance_changes"
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey("staff_attendance.id"), nullable=False, index=True)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    changed_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    previous_values = db.Column(db.JSON)
    current_values = db.Column(db.JSON, nullable=False)
    attendance = db.relationship("StaffAttendance", back_populates="changes")
    changed_by = db.relationship("User")
