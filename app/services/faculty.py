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
    subjects = assigned_subjects(faculty)
    course_ids = {subject.course_id for subject in subjects}
    semesters = {subject.semester for subject in subjects}
    if not course_ids or not semesters:
        return []

    query = Student.query.join(Student.user).join(Student.course).filter(
        Student.course_id.in_(course_ids),
        Student.semester.in_(semesters),
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


def faculty_notifications(user, faculty: Faculty | None = None):
    """Return notifications relevant to a faculty user."""
    query = Notification.query.filter(Notification.is_active.is_(True)).filter(
        or_(
            Notification.target_role == "all",
            Notification.target_role == "faculty",
            Notification.target_user_id == user.id,
            Notification.created_by == user.id,
        )
    )
    return query.order_by(Notification.created_at.desc()).all()
