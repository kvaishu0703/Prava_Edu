"""Report row builders and CSV response helpers."""

from __future__ import annotations

import csv
from io import StringIO

from flask import Response

from app.models import Assignment, Attendance, Course, Faculty, Marks, Notification, Student, StudyMaterial, Subject, Submission, User


def csv_response(filename: str, headers: list[str], rows: list[list]) -> Response:
    """Return rows as a downloadable CSV response."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def admin_report_cards() -> list[dict]:
    """Return report cards used by the Admin reports page."""
    return [
        {
            "title": "Student Report",
            "description": "Enrollment, contact, course, semester, and active status.",
            "icon": "bi-people",
            "endpoint": "students",
        },
        {
            "title": "Faculty Report",
            "description": "Employee ID, department, contact, subject count, and active status.",
            "icon": "bi-person-workspace",
            "endpoint": "faculty",
        },
        {
            "title": "Attendance Report",
            "description": "Daily attendance rows with student, subject, status, and faculty.",
            "icon": "bi-calendar2-check",
            "endpoint": "attendance",
        },
        {
            "title": "Marks Report",
            "description": "Subject marks, totals, grades, and pass/fail result.",
            "icon": "bi-award",
            "endpoint": "marks",
        },
        {
            "title": "Assignment Report",
            "description": "Assignments, due dates, maximum marks, and submission counts.",
            "icon": "bi-clipboard-check",
            "endpoint": "assignments",
        },
        {
            "title": "Notification Report",
            "description": "Announcements, target filters, creator, and active status.",
            "icon": "bi-bell",
            "endpoint": "notifications",
        },
    ]


def student_report_rows() -> tuple[list[str], list[list]]:
    """Return rows for the Admin student report."""
    students = Student.query.join(Student.user).join(Student.course).order_by(User.full_name).all()
    return [
        "Enrollment",
        "Name",
        "Username",
        "Email",
        "Mobile",
        "Course",
        "Semester",
        "Admission Year",
        "Active",
    ], [
        [
            student.enrollment_number,
            student.user.full_name,
            student.user.username,
            student.user.email,
            student.mobile_number or "",
            student.course.code,
            student.semester,
            student.admission_year,
            "Yes" if student.user.is_active else "No",
        ]
        for student in students
    ]


def faculty_report_rows() -> tuple[list[str], list[list]]:
    """Return rows for the Admin faculty report."""
    faculty_members = Faculty.query.join(Faculty.user).order_by(User.full_name).all()
    return [
        "Employee ID",
        "Name",
        "Username",
        "Email",
        "Mobile",
        "Department",
        "Qualification",
        "Subjects",
        "Active",
    ], [
        [
            faculty.employee_id,
            faculty.user.full_name,
            faculty.user.username,
            faculty.user.email,
            faculty.mobile_number or "",
            faculty.department,
            faculty.qualification or "",
            len(faculty.subjects),
            "Yes" if faculty.user.is_active else "No",
        ]
        for faculty in faculty_members
    ]


def attendance_report_rows(records) -> tuple[list[str], list[list]]:
    """Return CSV rows from attendance records."""
    return [
        "Date",
        "Enrollment",
        "Student",
        "Subject Code",
        "Subject",
        "Status",
        "Faculty",
        "Remarks",
    ], [
        [
            record.attendance_date.isoformat(),
            record.student.enrollment_number,
            record.student.user.full_name,
            record.subject.code,
            record.subject.name,
            record.status,
            record.faculty.user.full_name,
            record.remarks or "",
        ]
        for record in records
    ]


def admin_attendance_records():
    """Return all attendance records for Admin exports."""
    return (
        Attendance.query.join(Attendance.student)
        .join(Student.user)
        .join(Attendance.subject)
        .order_by(Attendance.attendance_date.desc(), User.full_name)
        .all()
    )


def marks_report_rows(records) -> tuple[list[str], list[list]]:
    """Return CSV rows from marks records."""
    return [
        "Enrollment",
        "Student",
        "Subject Code",
        "Subject",
        "Exam Type",
        "Internal",
        "External",
        "Total",
        "Grade",
        "Result",
        "Entered By",
        "Remarks",
    ], [
        [
            record.student.enrollment_number,
            record.student.user.full_name,
            record.subject.code,
            record.subject.name,
            record.exam_type,
            record.internal_marks,
            record.external_marks,
            record.total_marks,
            record.grade or "",
            "Pass" if record.total_marks >= record.subject.passing_marks else "Fail",
            record.entered_by_user.user.full_name,
            record.remarks or "",
        ]
        for record in records
    ]


def admin_marks_records():
    """Return all marks records for Admin exports."""
    return (
        Marks.query.join(Marks.student)
        .join(Student.user)
        .join(Marks.subject)
        .order_by(Subject.code, User.full_name, Marks.exam_type)
        .all()
    )


def assignment_report_rows() -> tuple[list[str], list[list]]:
    """Return rows for the Admin assignment report."""
    assignments = Assignment.query.join(Assignment.subject).order_by(Assignment.due_date.desc()).all()
    return [
        "Title",
        "Subject Code",
        "Subject",
        "Faculty",
        "Due Date",
        "Maximum Marks",
        "Submissions",
        "Graded",
        "Active",
    ], [
        [
            assignment.title,
            assignment.subject.code,
            assignment.subject.name,
            assignment.faculty.user.full_name,
            assignment.due_date.strftime("%Y-%m-%d %H:%M"),
            assignment.maximum_marks,
            len(assignment.submissions),
            sum(1 for submission in assignment.submissions if submission.status == "Graded"),
            "Yes" if assignment.is_active else "No",
        ]
        for assignment in assignments
    ]


def notification_report_rows() -> tuple[list[str], list[list]]:
    """Return rows for the Admin notification report."""
    notifications = Notification.query.order_by(Notification.created_at.desc()).all()
    return [
        "Title",
        "Type",
        "Message",
        "Target Role",
        "Target Course",
        "Target Semester",
        "Creator",
        "Created At",
        "Expires At",
        "Read Receipts",
        "Active",
    ], [
        [
            notification.title,
            notification.notification_type,
            notification.message,
            notification.target_role,
            notification.target_course.code if notification.target_course else "",
            notification.target_semester or "",
            notification.creator.full_name,
            notification.created_at.strftime("%Y-%m-%d %H:%M"),
            notification.expires_at.strftime("%Y-%m-%d %H:%M") if notification.expires_at else "",
            len(notification.read_receipts),
            "Yes" if notification.is_active else "No",
        ]
        for notification in notifications
    ]


def material_report_rows() -> tuple[list[str], list[list]]:
    """Return rows for a study material report."""
    materials = StudyMaterial.query.join(StudyMaterial.subject).order_by(StudyMaterial.uploaded_at.desc()).all()
    return [
        "Title",
        "Subject Code",
        "Subject",
        "Faculty",
        "File Name",
        "File Type",
        "Uploaded At",
        "Active",
    ], [
        [
            material.title,
            material.subject.code,
            material.subject.name,
            material.faculty.user.full_name,
            material.file_name,
            material.file_type,
            material.uploaded_at.strftime("%Y-%m-%d %H:%M"),
            "Yes" if material.is_active else "No",
        ]
        for material in materials
    ]


def admin_course_report_rows() -> tuple[list[str], list[list]]:
    """Return course and subject master report rows."""
    courses = Course.query.order_by(Course.name).all()
    return ["Course Code", "Course Name", "Duration", "Total Semesters", "Students", "Subjects", "Active"], [
        [
            course.code,
            course.name,
            course.duration,
            course.total_semesters,
            len(course.students),
            len(course.subjects),
            "Yes" if course.is_active else "No",
        ]
        for course in courses
    ]
