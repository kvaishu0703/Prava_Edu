"""Attendance module helpers."""

from __future__ import annotations

from datetime import date

from sqlalchemy import extract

from app.extensions import db
from app.models import Attendance, Faculty, Student, Subject, User
from app.services.dashboard import percent

ATTENDANCE_STATUSES = ("Present", "Absent", "Late")


def faculty_subject_choices(faculty: Faculty):
    """Return subject choices for a faculty attendance form."""
    return [
        (subject.id, f"{subject.code} - {subject.name}")
        for subject in Subject.query.filter_by(faculty_id=faculty.id, is_active=True)
        .order_by(Subject.semester, Subject.name)
        .all()
    ]


def get_faculty_subject(faculty: Faculty, subject_id: int) -> Subject | None:
    """Return a subject only if it belongs to the faculty member."""
    return Subject.query.filter_by(id=subject_id, faculty_id=faculty.id, is_active=True).first()


def students_for_subject(subject: Subject):
    """Return active students for a subject's course and semester."""
    return (
        Student.query.join(Student.user)
        .filter(
            Student.course_id == subject.course_id,
            Student.semester == subject.semester,
            User.is_active.is_(True),
        )
        .order_by(User.full_name)
        .all()
    )


def attendance_map(subject_id: int, attendance_date: date):
    """Return existing attendance records keyed by student id."""
    records = Attendance.query.filter_by(
        subject_id=subject_id,
        attendance_date=attendance_date,
    ).all()
    return {record.student_id: record for record in records}


def save_bulk_attendance(faculty: Faculty, subject: Subject, attendance_date: date, rows: list[dict]) -> tuple[int, int]:
    """Create or update attendance rows for one subject and date."""
    existing = attendance_map(subject.id, attendance_date)
    created = 0
    updated = 0

    for row in rows:
        student_id = row["student_id"]
        status = row["status"]
        remarks = row.get("remarks")
        if status not in ATTENDANCE_STATUSES:
            continue

        record = existing.get(student_id)
        if record:
            record.status = status
            record.remarks = remarks
            record.faculty_id = faculty.id
            updated += 1
        else:
            db.session.add(
                Attendance(
                    student_id=student_id,
                    subject_id=subject.id,
                    faculty_id=faculty.id,
                    attendance_date=attendance_date,
                    status=status,
                    remarks=remarks,
                )
            )
            created += 1

    return created, updated


def subject_attendance_report(subject: Subject, month: int | None = None, year: int | None = None):
    """Return student-wise attendance report for a subject."""
    students = students_for_subject(subject)
    report = []
    for student in students:
        query = Attendance.query.filter_by(student_id=student.id, subject_id=subject.id)
        if month and year:
            query = query.filter(
                extract("month", Attendance.attendance_date) == month,
                extract("year", Attendance.attendance_date) == year,
            )
        records = query.all()
        total = len(records)
        present = sum(1 for record in records if record.status in {"Present", "Late"})
        absent = sum(1 for record in records if record.status == "Absent")
        late = sum(1 for record in records if record.status == "Late")
        percentage = percent(present, total)
        report.append(
            {
                "student": student,
                "total": total,
                "present": present,
                "absent": absent,
                "late": late,
                "percentage": percentage,
                "low_warning": percentage < 75 if total else False,
            }
        )
    return report


def recent_attendance_dates(subject: Subject, limit: int = 5):
    """Return latest dates for which attendance was marked."""
    return (
        db.session.query(Attendance.attendance_date)
        .filter_by(subject_id=subject.id)
        .distinct()
        .order_by(Attendance.attendance_date.desc())
        .limit(limit)
        .all()
    )
