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
    admin_scope = db.Column(db.String(30), nullable=False, default="office", server_default="office")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_demo = db.Column(db.Boolean, default=False, server_default="false", nullable=False)
    last_login = db.Column(db.DateTime(timezone=True))
    profile_image = db.Column(db.String(255))
    gender = db.Column(db.String(20))

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

    @property
    def profile_gender(self):
        """Use the recorded gender, never a guess based on a person's name."""
        if self.role == "student" and self.student_profile:
            return self.student_profile.gender
        return self.gender

    @property
    def profile_photo_path(self):
        """Keep uploaded photos ahead of the gender-specific illustrated avatar."""
        profile = self.student_profile if self.role == "student" else self.faculty_profile if self.role == "faculty" else self
        photo = profile.profile_image if profile else None
        if photo:
            return photo
        return {
            "Female": "img/profile-female.png",
            "Male": "img/profile-male.png",
        }.get(self.profile_gender, "img/prava-mark.svg")

    @property
    def profile_photo_alt(self):
        if self.profile_photo_path.startswith("uploads/"):
            return f"{self.display_name} profile photo"
        return "Profile avatar"

    @property
    def display_name(self):
        """Present legacy local account labels without changing real names."""
        legacy = {
            'BCA Demo Student': 'BCA Student',
            'Home Science Demo Student': 'Home Science Student',
            'Demo Staff': 'Faculty', 'Demo Administrator': 'College Administration',
        }
        return legacy.get(self.full_name, self.full_name) if self.is_demo else self.full_name

    @property
    def display_email(self):
        """Do not present a reserved local address as a college contact."""
        if self.is_demo and self.email.endswith('@demo.prava.test'):
            return 'Not recorded'
        return self.email

    def set_password(self, password: str) -> None:
        """Hash and store a password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check a plain password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"
