"""Student module data helpers."""

from __future__ import annotations

from sqlalchemy import or_

from app.models import Assignment, Attendance, Marks, Notification, Student, StudyMaterial, Subject, Submission
from app.services.dashboard import percent


def get_student_for_user(user) -> Student | None:
    """Return the student profile linked with the current user."""
    return user.student_profile


def student_subjects(student: Student):
    """Return active subjects for the student's course and semester."""
    return (
        Subject.query.filter_by(
            course_id=student.course_id,
            semester=student.semester,
            is_active=True,
        )
        .order_by(Subject.name)
        .all()
    )


def student_attendance_summary(student: Student):
    """Return subject-wise attendance totals and percentages."""
    rows = []
    for subject in student_subjects(student):
        records = Attendance.query.filter_by(student_id=student.id, subject_id=subject.id).all()
        total = len(records)
        present = sum(1 for record in records if record.status in {"Present", "Late"})
        rows.append(
            {
                "subject": subject,
                "total": total,
                "present": present,
                "absent": sum(1 for record in records if record.status == "Absent"),
                "percentage": percent(present, total),
            }
        )
    return rows


def student_marks_summary(student: Student):
    """Return marks records ordered by subject."""
    return (
        Marks.query.filter_by(student_id=student.id)
        .join(Marks.subject)
        .order_by(Subject.name, Marks.exam_type)
        .all()
    )


def student_materials(student: Student, search: str = ""):
    """Return study materials for the student's subjects."""
    subject_ids = [subject.id for subject in student_subjects(student)]
    if not subject_ids:
        return []

    query = StudyMaterial.query.filter(
        StudyMaterial.subject_id.in_(subject_ids),
        StudyMaterial.is_active.is_(True),
    ).join(StudyMaterial.subject)

    if search:
        like = f"%{search}%"
        query = query.filter(or_(StudyMaterial.title.ilike(like), Subject.name.ilike(like), Subject.code.ilike(like)))

    return query.order_by(StudyMaterial.uploaded_at.desc()).all()


def student_assignments(student: Student):
    """Return assignments for the student's subjects with submission status."""
    subject_ids = [subject.id for subject in student_subjects(student)]
    if not subject_ids:
        return []

    assignments = (
        Assignment.query.filter(
            Assignment.subject_id.in_(subject_ids),
            Assignment.is_active.is_(True),
        )
        .join(Assignment.subject)
        .order_by(Assignment.due_date)
        .all()
    )
    submissions = {
        submission.assignment_id: submission
        for submission in Submission.query.filter_by(student_id=student.id).all()
    }
    return [{"assignment": assignment, "submission": submissions.get(assignment.id)} for assignment in assignments]


def student_notifications(user, student: Student | None = None):
    """Return notifications relevant to a student."""
    query = Notification.query.filter(Notification.is_active.is_(True)).filter(
        or_(
            Notification.target_role == "all",
            Notification.target_role == "student",
            Notification.target_user_id == user.id,
        )
    )
    if student is not None:
        query = query.filter(
            or_(
                Notification.target_course_id.is_(None),
                Notification.target_course_id == student.course_id,
            )
        ).filter(
            or_(
                Notification.target_semester.is_(None),
                Notification.target_semester == student.semester,
            )
        )
    return query.order_by(Notification.created_at.desc()).all()
