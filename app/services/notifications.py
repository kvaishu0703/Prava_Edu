"""Notification creation, targeting, and read-status helpers."""

from __future__ import annotations

from sqlalchemy import or_

from app.extensions import db
from app.models import Course, Notification, NotificationRead, Subject
from app.models.base import utc_now
from app.services.attendance import get_faculty_subject


def notification_type_choices() -> list[tuple[str, str]]:
    """Return supported notification type choices."""
    return [
        ("General", "General"),
        ("Holiday", "Holiday"),
        ("Exam", "Exam"),
        ("Assignment", "Assignment"),
        ("Material", "Material"),
        ("Attendance", "Attendance"),
        ("Marks", "Marks"),
    ]


def target_role_choices() -> list[tuple[str, str]]:
    """Return supported target role choices for admin notifications."""
    return [
        ("all", "All Users"),
        ("student", "Students"),
        ("faculty", "Faculty"),
        ("admin", "Admin"),
    ]


def course_filter_choices() -> list[tuple[int, str]]:
    """Return active course choices with an all-courses option."""
    return [(0, "All Courses")] + [
        (course.id, f"{course.code} - {course.name}")
        for course in Course.query.filter_by(is_active=True).order_by(Course.name).all()
    ]


def visible_notifications_for_user(user, profile=None):
    """Return notifications visible to a user with read/unread status."""
    now = utc_now()
    query = Notification.query.filter(Notification.is_active.is_(True)).filter(
        or_(Notification.expires_at.is_(None), Notification.expires_at > now)
    ).filter(
        or_(
            Notification.target_role == "all",
            Notification.target_role == user.role,
            Notification.target_user_id == user.id,
            Notification.created_by == user.id,
        )
    )

    if user.role == "student" and profile is not None:
        query = query.filter(
            or_(
                Notification.target_course_id.is_(None),
                Notification.target_course_id == profile.course_id,
            )
        ).filter(
            or_(
                Notification.target_semester.is_(None),
                Notification.target_semester == profile.semester,
            )
        )

    notifications = query.order_by(Notification.created_at.desc()).all()
    read_ids = {
        receipt.notification_id
        for receipt in NotificationRead.query.filter_by(user_id=user.id).all()
    }
    return [{"notification": notification, "is_read": notification.id in read_ids} for notification in notifications]


def admin_notifications(search: str = ""):
    """Return notifications for the admin management page."""
    query = Notification.query.join(Notification.creator)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Notification.title.ilike(like),
                Notification.message.ilike(like),
                Notification.notification_type.ilike(like),
                Notification.target_role.ilike(like),
            )
        )
    return query.order_by(Notification.created_at.desc()).all()


def create_admin_notification(user, title: str, message: str, notification_type: str, target_role: str, target_course_id: int | None, target_semester: int | None, expires_at) -> Notification:
    """Create a notification from Admin."""
    return Notification(
        title=title.strip(),
        message=message.strip(),
        notification_type=notification_type,
        created_by=user.id,
        target_role=target_role,
        target_course_id=target_course_id or None,
        target_semester=target_semester or None,
        expires_at=expires_at,
    )


def faculty_subject_notification_choices(faculty) -> list[tuple[int, str]]:
    """Return subject choices used by faculty notification targeting."""
    return [
        (subject.id, f"{subject.code} - {subject.name} ({subject.course.code}, Sem {subject.semester})")
        for subject in Subject.query.filter_by(faculty_id=faculty.id, is_active=True).join(Subject.course).order_by(Subject.name).all()
    ]


def create_faculty_notification(faculty, user, subject_id: int, title: str, message: str, notification_type: str, expires_at) -> Notification:
    """Create a student-targeted notification from Faculty for an assigned subject."""
    subject = get_faculty_subject(faculty, subject_id)
    if subject is None:
        raise PermissionError("Selected subject is not assigned to you.")
    return Notification(
        title=title.strip(),
        message=message.strip(),
        notification_type=notification_type,
        created_by=user.id,
        target_role="student",
        target_course_id=subject.course_id,
        target_semester=subject.semester,
        expires_at=expires_at,
    )


def notification_for_reader(user, notification_id: int, profile=None) -> Notification | None:
    """Return a notification only if it is visible to this user."""
    for row in visible_notifications_for_user(user, profile):
        if row["notification"].id == notification_id:
            return row["notification"]
    return None


def mark_notification_read(user, notification: Notification) -> None:
    """Create a read receipt if one does not already exist."""
    existing = NotificationRead.query.filter_by(notification_id=notification.id, user_id=user.id).first()
    if existing is None:
        db.session.add(NotificationRead(notification_id=notification.id, user_id=user.id))


def can_deactivate_notification(user, notification: Notification) -> bool:
    """Return True when the user can deactivate a notification."""
    return user.role == "admin" or notification.created_by == user.id
