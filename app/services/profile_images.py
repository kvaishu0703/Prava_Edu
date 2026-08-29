"""Profile image upload helpers for Student and Faculty modules."""

from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_PROFILE_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


def image_extension(filename: str) -> str:
    """Return lowercase file extension without the dot."""
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def is_allowed_profile_image(filename: str) -> bool:
    """Check if a profile image filename uses a supported extension."""
    return image_extension(filename) in ALLOWED_PROFILE_IMAGE_EXTENSIONS


def save_profile_image(file: FileStorage | None) -> str | None:
    """Save an uploaded profile image and return its static relative path."""
    if not file or not file.filename:
        return None

    original_name = secure_filename(file.filename)
    if not original_name or not is_allowed_profile_image(original_name):
        raise ValueError("Please upload a JPG, PNG, GIF, or WEBP image.")

    extension = image_extension(original_name)
    safe_name = f"{uuid4().hex}.{extension}"
    subdir = "profiles"
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    target_dir = upload_root / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    file.save(target_dir / safe_name)
    return f"uploads/{subdir}/{safe_name}"
