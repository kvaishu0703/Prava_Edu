"""Dashboard data helpers.

Routes should stay small. These helpers collect the database values that each
role dashboard needs and return template-friendly dictionaries.
"""

from __future__ import annotations

from sqlalchemy import func

from app.models import (
    Assignment,
    Attendance,
    ContactInquiry,
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


def average_marks(student_id: int | None = None) -> int | None:
    """Calculate average marks percentage for one student or all students."""
    query = Marks.query.join(Marks.subject)
    if student_id is not None:
        query = query.filter(Marks.student_id == student_id)

    obtained, maximum = query.with_entities(func.sum(Marks.total_marks), func.sum(Subject.maximum_marks)).one()
    return round(obtained * 100 / maximum) if maximum else None


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
        ("New Inquiries", ContactInquiry.query.filter_by(status="New").count(), "bi-envelope-paper", "blue"),
    ]
    recent_students = (
        Student.query.join(Student.user)
        .join(Student.course)
        .order_by(Student.created_at.desc())
        .limit(5)
        .all()
    )
    from app.services.college import PROGRAMMES, DEPARTMENTS
    departments = []
    for slug, info in DEPARTMENTS.items():
        codes = [code for code, _, department, _ in PROGRAMMES if department == slug]
        programmes = Course.query.filter(Course.code.in_(codes), Course.is_active.is_(True)).all()
        ids = [course.id for course in programmes]
        departments.append({'name': info['name'], 'slug': slug, 'programmes': len(programmes),
                            'students': Student.query.filter(Student.course_id.in_(ids)).count(),
                            'subjects': Subject.query.filter(Subject.course_id.in_(ids), Subject.is_active.is_(True)).count()})
    return {
        "departments_overview": departments,
        "has_attendance": Attendance.query.first() is not None,
        "stats": stats,
        "recent_students": recent_students,
        "recent_inquiries": ContactInquiry.query.order_by(ContactInquiry.created_at.desc()).limit(4).all(),
        "notifications": recent_notifications(),
        "attendance_percentage": attendance_percentage(),
    }


def get_faculty_dashboard_data(user) -> dict:
    """Collect statistics and lists for the Faculty dashboard."""
    faculty = user.faculty_profile
    if faculty is None:
        return empty_dashboard_data("Faculty profile is not linked yet.")

    from app.services.faculty import assigned_students
    subject_ids = [subject.id for subject in faculty.subjects if subject.is_active]
    total_students = len(assigned_students(faculty))

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
        "notifications": role_notifications(user, faculty),
    }


def get_student_dashboard_data(user) -> dict:
    """Collect statistics and lists for the Student dashboard."""
    student = user.student_profile
    if student is None:
        return empty_dashboard_data("Student profile is not linked yet.")

    from app.services.student import student_subjects
    subjects = student_subjects(student)
    subject_ids = [subject.id for subject in subjects]
    assignment_count = Assignment.query.filter(
        Assignment.subject_id.in_(subject_ids),
        Assignment.is_active.is_(True),
    ).count() if subject_ids else 0
    submitted_assignment_ids = {submission.assignment_id for submission in student.submissions}
    pending_count = sum(
        1
        for assignment in Assignment.query.filter(Assignment.subject_id.in_(subject_ids), Assignment.is_active.is_(True)).all()
        if assignment.id not in submitted_assignment_ids
    ) if subject_ids else 0

    average = average_marks(student.id)
    has_attendance = Attendance.query.filter_by(student_id=student.id).first() is not None
    stats = [
        ("Attendance", f"{attendance_percentage(student.id)}%" if has_attendance else 'Pending', "bi-calendar2-check", "green"),
        ("Average Marks", f"{average}%" if average is not None else 'Pending', "bi-award", "purple"),
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
        "notifications": role_notifications(user, student),
    }


def role_notifications(user, profile):
    from app.services.notifications import visible_notifications_for_user
    return [row['notification'] for row in visible_notifications_for_user(user, profile)[:4]]


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
