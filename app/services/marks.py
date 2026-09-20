"""Marks module helpers."""

from __future__ import annotations

from app.extensions import db
from app.models import Marks, Student, Subject, User
from app.services.attendance import get_faculty_subject, students_for_subject

GRADE_SCALE = [
    (90, "A+"),
    (80, "A"),
    (70, "B+"),
    (60, "B"),
    (50, "C"),
    (40, "D"),
    (0, "F"),
]


def calculate_grade(total_marks: int, maximum_marks: int = 100) -> str:
    """Return a grade from total marks and maximum marks."""
    if maximum_marks <= 0:
        return "F"
    percentage = round((total_marks / maximum_marks) * 100)
    for minimum, grade in GRADE_SCALE:
        if percentage >= minimum:
            return grade
    return "F"


def validate_marks(internal_marks: int, external_marks: int, subject: Subject) -> tuple[bool, str]:
    """Validate marks before saving."""
    if internal_marks < 0 or external_marks < 0:
        return False, "Marks cannot be negative."
    if subject.curriculum_id:
        item = subject.curriculum_subject
        if not item or not item.is_verified or item.internal_max is None or item.external_max is None:
            return False, 'The office must link a verified assessment scheme before entering NEP marks.'
        if subject.maximum_marks != item.internal_max + item.external_max:
            return False, 'The linked assessment scheme changed. Ask the office to review the subject maximum.'
        if internal_marks > item.internal_max or external_marks > item.external_max:
            return False, f'Internal marks must be at most {item.internal_max}; external marks at most {item.external_max}.'
    total = internal_marks + external_marks
    if total > subject.maximum_marks:
        return False, f"Total marks cannot be greater than {subject.maximum_marks}."
    return True, ""


def marks_map(subject_id: int, exam_type: str):
    """Return existing marks keyed by student id."""
    records = Marks.query.filter_by(subject_id=subject_id, exam_type=exam_type).all()
    return {record.student_id: record for record in records}


def save_bulk_marks(faculty, subject: Subject, exam_type: str, rows: list[dict]) -> tuple[int, int, list[str]]:
    """Create or update marks rows for one subject and exam type."""
    existing = marks_map(subject.id, exam_type)
    created = 0
    updated = 0
    errors = []
    if subject.curriculum_id and exam_type != 'Semester Exam':
        return 0, 0, ['NEP assessment uses the verified semester internal and external totals.']
    eligible_ids = {student.id for student in students_for_subject(subject)}

    for row in rows:
        student_id = row["student_id"]
        if subject.faculty_id != faculty.id or student_id not in eligible_ids:
            errors.append(f'Student ID {student_id}: not assigned to this subject.')
            continue
        internal_marks = row["internal_marks"]
        external_marks = row["external_marks"]
        remarks = row.get("remarks")
        is_valid, error = validate_marks(internal_marks, external_marks, subject)
        if not is_valid:
            errors.append(f"Student ID {student_id}: {error}")
            continue

        total = internal_marks + external_marks
        # NEP grades require the verified course's component/grade rules.
        # Preserve actual scores while those rules are being configured.
        grade = None if subject.curriculum_id else calculate_grade(total, subject.maximum_marks)
        record = existing.get(student_id)
        if record:
            record.internal_marks = internal_marks
            record.external_marks = external_marks
            record.total_marks = total
            record.grade = grade
            record.remarks = remarks
            record.entered_by = faculty.id
            updated += 1
        else:
            db.session.add(
                Marks(
                    student_id=student_id,
                    subject_id=subject.id,
                    exam_type=exam_type,
                    internal_marks=internal_marks,
                    external_marks=external_marks,
                    total_marks=total,
                    grade=grade,
                    remarks=remarks,
                    entered_by=faculty.id,
                )
            )
            created += 1
    return created, updated, errors


def subject_marks_report(subject: Subject, exam_type: str | None = None):
    """Return marks records for a subject."""
    query = Marks.query.filter_by(subject_id=subject.id).join(Marks.student).join(Student.user)
    if exam_type:
        query = query.filter(Marks.exam_type == exam_type)
    return query.order_by(User.full_name, Marks.exam_type).all()


def students_for_marks_subject(faculty, subject_id: int):
    """Return subject and students only when the faculty owns the subject."""
    subject = get_faculty_subject(faculty, subject_id)
    if subject is None:
        return None, []
    return subject, students_for_subject(subject)
