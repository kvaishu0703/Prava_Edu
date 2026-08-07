"""Dashboard data helpers.

Routes should stay small. These helpers collect the database values that each
role dashboard needs and return template-friendly dictionaries.
"""

from __future__ import annotations

from sqlalchemy import func

from app.models import (
    Assignment,
    Attendance,
    Course,
    Faculty,
    Marks,
    Notification,
    Student,
    StudyMaterial,
    Subject,
)


def percent(part: int, total: int) -> int:
    """Return a rounded percentage and avoid divide-by-zero errors."""
    if total == 0:
        return 0
    return round((part / total) * 100)


def attendance_percentage(student_id: int | None = None) -> int:
    """Calculate attendance percentage for one student or all students."""
    query = Attendance.query
    if student_id is not None:
        query = query.filter(Attendance.student_id == student_id)

    total = query.count()
    present = query.filter(Attendance.status.in_(["Present", "Late"])).count()
    return percent(present, total)


def average_marks(student_id: int | None = None) -> int:
    """Calculate average marks percentage for one student or all students."""
    query = Marks.query
    if student_id is not None:
        query = query.filter(Marks.student_id == student_id)

    average = query.with_entities(func.avg(Marks.total_marks)).scalar()
    return round(average or 0)


def recent_notifications(limit: int = 4):
    """Return latest active notifications."""
    return (
        Notification.query.filter_by(is_active=True)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def get_admin_dashboard_data() -> dict:
    """Collect statistics and lists for the Admin dashboard."""
    stats = [
        ("Students", Student.query.count(), "bi-people-fill", "purple"),
        ("Faculty", Faculty.query.count(), "bi-person-workspace", "orange"),
        ("Courses", Course.query.filter_by(is_active=True).count(), "bi-journal-bookmark-fill", "green"),
        ("Attendance", f"{attendance_percentage()}%", "bi-calendar2-check", "blue"),
    ]
    recent_students = (
        Student.query.join(Student.user)
        .join(Student.course)
        .order_by(Student.created_at.desc())
        .limit(5)
        .all()
    )
    return {
        "stats": stats,
        "recent_students": recent_students,
        "notifications": recent_notifications(),
        "attendance_percentage": attendance_percentage(),
    }


def get_faculty_dashboard_data(user) -> dict:
    """Collect statistics and lists for the Faculty dashboard."""
    faculty = user.faculty_profile
    if faculty is None:
        return empty_dashboard_data("Faculty profile is not linked yet.")

    subject_ids = [subject.id for subject in faculty.subjects]
    course_ids = {subject.course_id for subject in faculty.subjects}
    semesters = {subject.semester for subject in faculty.subjects}

    total_students = Student.query.filter(
        Student.course_id.in_(course_ids),
        Student.semester.in_(semesters),
    ).count() if course_ids and semesters else 0

    active_assignments = Assignment.query.filter_by(
        faculty_id=faculty.id,
        is_active=True,
    ).count()

    pending_submissions = sum(
        1
        for assignment in faculty.assignments
        for submission in assignment.submissions
        if submission.status in {"Submitted", "Late"}
    )

    stats = [
        ("Assigned Subjects", len(subject_ids), "bi-book-half", "orange"),
        ("Students", total_students, "bi-people", "purple"),
        ("Active Assignments", active_assignments, "bi-clipboard-check", "green"),
        ("Pending Reviews", pending_submissions, "bi-hourglass-split", "blue"),
    ]

    return {
        "stats": stats,
        "subjects": faculty.subjects,
        "assignments": faculty.assignments[:5],
        "notifications": recent_notifications(),
    }


def get_student_dashboard_data(user) -> dict:
    """Collect statistics and lists for the Student dashboard."""
    student = user.student_profile
    if student is None:
        return empty_dashboard_data("Student profile is not linked yet.")

    subjects = Subject.query.filter_by(
        course_id=student.course_id,
        semester=student.semester,
        is_active=True,
    ).all()
    subject_ids = [subject.id for subject in subjects]
    assignment_count = Assignment.query.filter(
        Assignment.subject_id.in_(subject_ids),
        Assignment.is_active.is_(True),
    ).count() if subject_ids else 0
    submitted_assignment_ids = {submission.assignment_id for submission in student.submissions}
    pending_count = sum(
        1
        for assignment in Assignment.query.filter(Assignment.subject_id.in_(subject_ids)).all()
        if assignment.id not in submitted_assignment_ids
    ) if subject_ids else 0

    stats = [
        ("Attendance", f"{attendance_percentage(student.id)}%", "bi-calendar2-check", "green"),
        ("Average Marks", f"{average_marks(student.id)}%", "bi-award", "purple"),
        ("Assignments", assignment_count, "bi-clipboard", "orange"),
        ("Pending", pending_count, "bi-hourglass-split", "blue"),
    ]

    materials = StudyMaterial.query.filter(
        StudyMaterial.subject_id.in_(subject_ids),
        StudyMaterial.is_active.is_(True),
    ).order_by(StudyMaterial.uploaded_at.desc()).limit(5).all() if subject_ids else []

    return {
        "stats": stats,
        "student": student,
        "subjects": subjects,
        "materials": materials,
        "notifications": recent_notifications(),
    }


def empty_dashboard_data(message: str) -> dict:
    """Return a safe empty dashboard payload when a profile is missing."""
    return {
        "stats": [],
        "subjects": [],
        "assignments": [],
        "materials": [],
        "notifications": [],
        "message": message,
    }
