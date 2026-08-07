"""Notification and activity log models."""

from app.extensions import db
from app.models.base import utc_now


class Notification(db.Model):
    """Announcement sent by Admin or Faculty."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(40), nullable=False, default="General")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_role = db.Column(db.String(30), default="all", nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    target_course_id = db.Column(db.Integer, db.ForeignKey("courses.id"))
    target_semester = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True))
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    creator = db.relationship("User", back_populates="notifications_created", foreign_keys=[created_by])
    target_user = db.relationship("User", foreign_keys=[target_user_id])
    target_course = db.relationship("Course")
    read_receipts = db.relationship(
        "NotificationRead",
        back_populates="notification",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Notification {self.title}>"


class NotificationRead(db.Model):
    """Tracks read/unread status per user."""

    __tablename__ = "notification_reads"
    __table_args__ = (
        db.UniqueConstraint("notification_id", "user_id", name="uq_notification_read_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    read_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    notification = db.relationship("Notification", back_populates="read_receipts")
    user = db.relationship("User", back_populates="notification_reads")


class ActivityLog(db.Model):
    """Security and audit trail entry."""

    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(80), nullable=False)
    module = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    user = db.relationship("User", back_populates="activity_logs")
