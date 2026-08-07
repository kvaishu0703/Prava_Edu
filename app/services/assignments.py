"""Assignment creation, submission, and grading helpers."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.models import Assignment, Student, Subject, Submission, User
from app.models.base import utc_now
from app.services.attendance import get_faculty_subject
from app.services.student import student_subjects


def assignment_extension(filename: str) -> str:
    """Return lowercase file extension without the dot."""
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def is_allowed_assignment_file(filename: str) -> bool:
    """Check whether an assignment upload has an allowed extension."""
    return assignment_extension(filename) in current_app.config["ALLOWED_ASSIGNMENT_EXTENSIONS"]


def save_assignment_file(file: FileStorage, subdir: str) -> str:
    """Save an uploaded assignment/submission file and return its relative path."""
    original_name = secure_filename(file.filename or "")
    if not original_name or not is_allowed_assignment_file(original_name):
        raise ValueError("Invalid or unsupported file type.")

    safe_name = f"{uuid4().hex}-{original_name}"
    target_dir = Path(current_app.config["UPLOAD_FOLDER"]) / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    file.save(target_dir / safe_name)
    return f"{subdir}/{safe_name}"


def create_assignment(faculty, subject_id: int, title: str, description: str | None, due_date, maximum_marks: int, attachment: FileStorage | None) -> Assignment:
    """Create an assignment for a subject assigned to the faculty member."""
    subject = get_faculty_subject(faculty, subject_id)
    if subject is None:
        raise PermissionError("Selected subject is not assigned to you.")

    attachment_path = None
    if attachment and attachment.filename:
        attachment_path = save_assignment_file(attachment, current_app.config["ASSIGNMENT_UPLOAD_SUBDIR"])

    return Assignment(
        title=title.strip(),
        description=description.strip() if description else None,
        subject_id=subject.id,
        faculty_id=faculty.id,
        due_date=due_date,
        maximum_marks=maximum_marks,
        attachment_path=attachment_path,
    )


def faculty_assignments(faculty, search: str = ""):
    """Return assignments created by a faculty member."""
    query = Assignment.query.filter_by(faculty_id=faculty.id).join(Assignment.subject)
    if search:
        like = f"%{search}%"
        query = query.filter((Assignment.title.ilike(like)) | (Subject.code.ilike(like)) | (Subject.name.ilike(like)))
    return query.order_by(Assignment.due_date.desc()).all()


def assignment_for_faculty(faculty, assignment_id: int) -> Assignment | None:
    """Return an assignment only if it belongs to the faculty member."""
    return Assignment.query.filter_by(id=assignment_id, faculty_id=faculty.id).first()


def assignment_for_student(student, assignment_id: int) -> Assignment | None:
    """Return an active assignment only if it belongs to the student's subjects."""
    subject_ids = [subject.id for subject in student_subjects(student)]
    if not subject_ids:
        return None
    return Assignment.query.filter(
        Assignment.id == assignment_id,
        Assignment.subject_id.in_(subject_ids),
        Assignment.is_active.is_(True),
    ).first()


def students_for_assignment(assignment: Assignment):
    """Return active students who should receive an assignment."""
    return (
        Student.query.join(Student.user)
        .filter(
            Student.course_id == assignment.subject.course_id,
            Student.semester == assignment.subject.semester,
            User.is_active.is_(True),
        )
        .order_by(User.full_name)
        .all()
    )


def assignment_submission_rows(assignment: Assignment):
    """Return expected students paired with their submission row, if any."""
    students = students_for_assignment(assignment)
    submissions = {
        submission.student_id: submission
        for submission in Submission.query.filter_by(assignment_id=assignment.id).all()
    }
    return [{"student": student, "submission": submissions.get(student.id)} for student in students]


def submission_for_student(student, assignment: Assignment) -> Submission | None:
    """Return the student's submission for an assignment."""
    return Submission.query.filter_by(student_id=student.id, assignment_id=assignment.id).first()


def submission_by_id_for_student(student, submission_id: int) -> Submission | None:
    """Return a submission only if it belongs to the student."""
    return Submission.query.filter_by(id=submission_id, student_id=student.id).first()


def submit_assignment(student, assignment: Assignment, file: FileStorage) -> Submission:
    """Create or update a student's assignment submission."""
    if not file or not file.filename:
        raise ValueError("Please select a submission file.")
    file_path = save_assignment_file(file, current_app.config["SUBMISSION_UPLOAD_SUBDIR"])
    submission = submission_for_student(student, assignment)
    if submission is None:
        submission = Submission(assignment_id=assignment.id, student_id=student.id)
    submission.mark_submitted(file_path)
    return submission


def submission_for_faculty(faculty, submission_id: int) -> Submission | None:
    """Return a submission only if its assignment belongs to the faculty member."""
    return (
        Submission.query.join(Submission.assignment)
        .filter(Submission.id == submission_id, Assignment.faculty_id == faculty.id)
        .first()
    )


def grade_submission(submission: Submission, marks_obtained: int, feedback: str | None) -> None:
    """Store faculty marks and feedback for a submission."""
    if marks_obtained < 0:
        raise ValueError("Marks cannot be negative.")
    if marks_obtained > submission.assignment.maximum_marks:
        raise ValueError("Marks cannot be greater than assignment maximum marks.")
    submission.marks_obtained = marks_obtained
    submission.faculty_feedback = feedback.strip() if feedback else None
    submission.status = "Graded"
    submission.graded_at = utc_now()


def split_upload_path(file_path: str) -> tuple[str, str]:
    """Split a stored relative upload path into directory and filename."""
    path = Path(file_path)
    if path.parts and path.parts[0] == "uploads":
        path = Path(*path.parts[1:])
    return path.parent.as_posix(), path.name


def uploaded_file_exists(file_path: str | None) -> bool:
    """Return True when a stored upload path exists on disk."""
    if not file_path:
        return False
    directory, filename = split_upload_path(file_path)
    return (Path(current_app.config["UPLOAD_FOLDER"]) / directory / filename).exists()
