"""Public homepage data helpers."""

from app.models import Course, Faculty, Notification, Student, Subject


def public_homepage_data() -> dict:
    """Return database-backed values for the professional public homepage."""
    courses = Course.query.filter_by(is_active=True).order_by(Course.name.asc()).limit(6).all()
    latest_notices = (
        Notification.query.filter_by(is_active=True)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )
    return {
        "summary_cards": [
            ("Total Students", Student.query.count(), "bi-people-fill", "green"),
            ("Total Faculty", Faculty.query.count(), "bi-person-workspace", "orange"),
            ("Total Courses", Course.query.filter_by(is_active=True).count(), "bi-journal-bookmark-fill", "blue"),
            ("Latest Notices", len(latest_notices), "bi-bell-fill", "purple"),
        ],
        "courses": [
            {
                "course": course,
                "description": course.description or "Course description will be updated by Admin.",
            }
            for course in courses
        ],
        "latest_notices": latest_notices,
    }


def course_detail_data(course: Course) -> dict:
    """Return public details for one active course."""
    subjects = (
        Subject.query.filter_by(course_id=course.id, is_active=True)
        .order_by(Subject.semester.asc(), Subject.name.asc())
        .all()
    )
    semester_groups: dict[int, list[Subject]] = {}
    for subject in subjects:
        semester_groups.setdefault(subject.semester, []).append(subject)

    return {
        "course": course,
        "description": course.description or "Course description will be updated by Admin.",
        "semester_groups": semester_groups,
        "student_count": Student.query.filter_by(course_id=course.id).count(),
    }
