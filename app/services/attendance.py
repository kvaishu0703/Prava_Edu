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
            Student.curriculum_id == subject.curriculum_id,
            User.is_active.is_(True),
        )
        .order_by(User.full_name)
        .all()
    )


def attendance_map(subject_id: int, attendance_date: date, session_number: int = 1):
    """Return existing attendance records keyed by student id."""
    records = Attendance.query.filter_by(
        subject_id=subject_id,
        attendance_date=attendance_date,
        session_number=session_number,
    ).all()
    return {record.student_id: record for record in records}


def save_bulk_attendance(faculty: Faculty, subject: Subject, attendance_date: date, rows: list[dict], slot=None) -> tuple[int, int]:
    """Create or update attendance rows for one subject and date."""
    from app.services.timetable import college_today
    if subject.faculty_id != faculty.id:
        raise ValueError('This subject is not assigned to you.')
    if attendance_date > college_today():
        raise ValueError('Attendance cannot be marked for a future date.')
    if slot and (slot.subject_id != subject.id or slot.weekday != attendance_date.weekday()):
        raise ValueError('Choose a scheduled session for this subject and date.')
    number = slot.session_number if slot else 1
    existing = attendance_map(subject.id, attendance_date, number)
    eligible = {s.id for s in students_for_subject(subject) if not slot or slot.batch == 'All' or (s.practical_batch or 'A') == slot.batch}
    created = 0
    updated = 0

    for row in rows:
        student_id = row["student_id"]
        if student_id not in eligible:
            raise ValueError('A student does not belong to this subject or practical batch.')
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
            conflict = Attendance.query.filter_by(student_id=student_id, attendance_date=attendance_date, session_number=number).first()
            if conflict and slot:
                raise ValueError('This student already has another subject recorded in that session.')
            db.session.add(
                Attendance(
                    student_id=student_id,
                    subject_id=subject.id,
                    faculty_id=faculty.id,
                    attendance_date=attendance_date,
                    status=status,
                    remarks=remarks,
                    session_number=number,
                    session_type=slot.session_type if slot else 'Theory',
                    starts_at=slot.starts_at if slot else None,
                    ends_at=slot.ends_at if slot else None,
                    timetable_slot_id=slot.id if slot else None,
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
