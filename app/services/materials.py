"""Study material upload and access helpers."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.models import StudyMaterial, Subject
from app.services.attendance import get_faculty_subject
from app.services.student import student_subjects


def material_extension(filename: str) -> str:
    """Return lowercase file extension without the dot."""
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def is_allowed_material(filename: str) -> bool:
    """Check if a filename has an allowed extension."""
    return material_extension(filename) in current_app.config["ALLOWED_MATERIAL_EXTENSIONS"]


def save_material_file(file: FileStorage) -> tuple[str, str, str]:
    """Save an uploaded material file and return name, relative path, and type."""
    original_name = secure_filename(file.filename or "")
    if not original_name or not is_allowed_material(original_name):
        raise ValueError("Invalid or unsupported file type.")

    extension = material_extension(original_name)
    safe_name = f"{uuid4().hex}-{original_name}"
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    subdir = current_app.config["MATERIAL_UPLOAD_SUBDIR"]
    target_dir = upload_root / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    file.save(target_dir / safe_name)
    return original_name, f"{subdir}/{safe_name}", extension


def faculty_materials(faculty, search: str = ""):
    """Return materials uploaded by a faculty member."""
    query = StudyMaterial.query.filter_by(faculty_id=faculty.id).join(StudyMaterial.subject)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (StudyMaterial.title.ilike(like))
            | (StudyMaterial.file_type.ilike(like))
            | (Subject.name.ilike(like))
            | (Subject.code.ilike(like))
        )
    return query.order_by(StudyMaterial.uploaded_at.desc()).all()


def create_material(faculty, subject_id: int, title: str, description: str | None, file: FileStorage) -> StudyMaterial:
    """Create a StudyMaterial row after saving the uploaded file."""
    subject = get_faculty_subject(faculty, subject_id)
    if subject is None:
        raise PermissionError("Selected subject is not assigned to you.")
    file_name, file_path, file_type = save_material_file(file)
    return StudyMaterial(
        title=title.strip(),
        description=description.strip() if description else None,
        subject_id=subject.id,
        faculty_id=faculty.id,
        file_name=file_name,
        file_path=file_path,
        file_type=file_type,
    )


def material_for_faculty(faculty, material_id: int) -> StudyMaterial | None:
    """Return a material only if it belongs to the faculty member."""
    return StudyMaterial.query.filter_by(id=material_id, faculty_id=faculty.id).first()


def material_for_student(student, material_id: int) -> StudyMaterial | None:
    """Return a material only if it belongs to the student's subjects."""
    subject_ids = [subject.id for subject in student_subjects(student)]
    if not subject_ids:
        return None
    return StudyMaterial.query.filter(
        StudyMaterial.id == material_id,
        StudyMaterial.subject_id.in_(subject_ids),
        StudyMaterial.is_active.is_(True),
    ).first()


def split_material_path(material: StudyMaterial) -> tuple[str, str]:
    """Split a stored relative path into directory and filename."""
    path = Path(material.file_path)
    if path.parts and path.parts[0] == "uploads":
        path = Path(*path.parts[1:])
    return path.parent.as_posix(), path.name


def material_file_exists(material: StudyMaterial) -> bool:
    """Return True when the material file exists on disk."""
    directory, filename = split_material_path(material)
    return (Path(current_app.config["UPLOAD_FOLDER"]) / directory / filename).exists()
