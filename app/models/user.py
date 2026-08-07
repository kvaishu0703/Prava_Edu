"""User account model."""

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.base import TimestampMixin


class User(UserMixin, TimestampMixin, db.Model):
    """Login account shared by Admin, Faculty, and Student users."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime(timezone=True))

    student_profile = db.relationship(
        "Student",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    faculty_profile = db.relationship(
        "Faculty",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    notifications_created = db.relationship(
        "Notification",
        back_populates="creator",
        foreign_keys="Notification.created_by",
    )
    activity_logs = db.relationship("ActivityLog", back_populates="user")
    notification_reads = db.relationship(
        "NotificationRead",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        """Hash and store a password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check a plain password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"
