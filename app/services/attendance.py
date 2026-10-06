"""Attendance module helpers."""

from __future__ import annotations

from datetime import date
import hashlib
import hmac
import json

from sqlalchemy import extract

from app.extensions import db
from app.models import Attendance, Faculty, Student, Subject, User
from app.models.base import utc_now
from app.services.dashboard import percent

ATTENDANCE_STATUSES = ("Present", "Absent", "Late")


class AttendanceRegisterConflict(ValueError):
    """The class register changed since a teacher loaded the form."""


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
        .populate_existing()
        .all()
    )


def attendance_map(subject_id: int, attendance_date: date, session_number: int = 1):
    """Return existing attendance records keyed by student id."""
    records = Attendance.query.filter_by(
        subject_id=subject_id,
        attendance_date=attendance_date,
        session_number=session_number,
    ).populate_existing().all()
    return {record.student_id: record for record in records}


def attendance_register_version(subject: Subject, attendance_date: date, slot=None) -> str:
    """Version only this subject/date/session and its eligible practical batch."""
    number = slot.session_number if slot else 1
    eligible = sorted(s.id for s in students_for_subject(subject)
                      if not slot or slot.batch == 'All' or (s.practical_batch or 'A') == slot.batch)
    records = attendance_map(subject.id, attendance_date, number)
    payload = {
        'scope': [subject.id, subject.course_id, subject.curriculum_id, subject.semester,
                  subject.faculty_id, subject.is_active, attendance_date.isoformat(), number],
        'slot': [slot.id, slot.batch, slot.weekday, slot.starts_at, slot.ends_at, slot.session_type] if slot else None,
        'students': eligible,
        'records': [[r.id, r.student_id, r.faculty_id, r.status, r.remarks, r.created_at,
                     r.recorded_by_user_id, r.updated_at, r.updated_by_user_id,
                     r.session_type, r.starts_at, r.ends_at, r.timetable_slot_id]
                    for student_id in eligible if (r := records.get(student_id)) is not None],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode('utf8')).hexdigest()


def save_bulk_attendance(faculty: Faculty, subject: Subject, attendance_date: date, rows: list[dict], slot=None, expected_version: str | None = None) -> tuple[int, int]:
    """Create or update attendance rows for one subject and date."""
    from app.services.timetable import college_today
    if expected_version is not None:
        from app.services.register_version import lock_subject_register
        lock_subject_register(subject)
        if slot:
            db.session.refresh(slot)
    if subject.faculty_id != faculty.id:
        raise ValueError('This subject is not assigned to you.')
    if attendance_date > college_today():
        raise ValueError('Attendance cannot be marked for a future date.')
    if slot and (slot.subject_id != subject.id or slot.weekday != attendance_date.weekday()):
        raise ValueError('Choose a scheduled session for this subject and date.')
    if expected_version is not None and not hmac.compare_digest(expected_version, attendance_register_version(subject, attendance_date, slot)):
        raise AttendanceRegisterConflict('This attendance register changed after you opened it. Your entries are kept below. Review the latest saved values, then reload the register before saving again.')
    number = slot.session_number if slot else 1
    existing = attendance_map(subject.id, attendance_date, number)
    eligible = {s.id for s in students_for_subject(subject) if not slot or slot.batch == 'All' or (s.practical_batch or 'A') == slot.batch}
    created = 0
    updated = 0
    saved_at = utc_now()

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
            record.updated_at = saved_at
            record.updated_by_user_id = faculty.user_id
            record.session_type = slot.session_type if slot else 'Theory'
            record.starts_at = slot.starts_at if slot else None
            record.ends_at = slot.ends_at if slot else None
            record.timetable_slot_id = slot.id if slot else None
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
                    created_at=saved_at,
                    recorded_by_user_id=faculty.user_id,
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
