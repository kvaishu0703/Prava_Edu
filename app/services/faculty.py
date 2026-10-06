"""Faculty module data helpers."""

from __future__ import annotations

from sqlalchemy import or_

from app.models import Assignment, Faculty, Notification, Student, Subject, User


def get_faculty_for_user(user) -> Faculty | None:
    """Return the faculty profile linked with the current user."""
    return user.faculty_profile


def assigned_subjects(faculty: Faculty):
    """Return subjects assigned to a faculty member."""
    return (
        Subject.query.filter_by(faculty_id=faculty.id)
        .join(Subject.course)
        .order_by(Subject.semester, Subject.name)
        .all()
    )


def assigned_students(faculty: Faculty, search: str = ""):
    """Return students from the courses and semesters taught by a faculty member."""
    query = Student.query.join(Student.user).join(Student.course).filter(
        Subject.query.filter(
            Subject.faculty_id == faculty.id,
            Subject.is_active.is_(True),
            Subject.course_id == Student.course_id,
            Subject.semester == Student.semester,
            Subject.curriculum_id.is_not_distinct_from(Student.curriculum_id),
        ).exists(),
        User.is_active.is_(True),
    )

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                User.full_name.ilike(like),
                User.email.ilike(like),
                Student.enrollment_number.ilike(like),
            )
        )

    return query.order_by(User.full_name).all()


def faculty_assignments(faculty: Faculty):
    """Return assignments created by a faculty member."""
    return (
        Assignment.query.filter_by(faculty_id=faculty.id, is_active=True)
        .join(Assignment.subject)
        .order_by(Assignment.due_date.desc())
        .all()
    )


def faculty_notifications(user, faculty=None):
    """Reuse the same targeting and expiry rules as the announcements page."""
    from app.services.notifications import visible_notifications_for_user
    return [row['notification'] for row in visible_notifications_for_user(user, faculty)]
