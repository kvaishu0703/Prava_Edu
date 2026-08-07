"""Configuration classes for PRAVA."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = (BASE_DIR / "instance" / "prava.sqlite3").as_posix()


def database_url() -> str:
    """Return a SQLAlchemy URL and select Psycopg 3 for PostgreSQL."""
    value = os.environ.get("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


class BaseConfig:
    """Shared settings used by all environments."""

    PROJECT_NAME = "PRAVA College Academic Management System"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-this-secret-key")
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER",
        str(BASE_DIR / "app" / "static" / "uploads"),
    )
    MATERIAL_UPLOAD_SUBDIR = "materials"
    ASSIGNMENT_UPLOAD_SUBDIR = "assignments"
    SUBMISSION_UPLOAD_SUBDIR = "submissions"
    ALLOWED_MATERIAL_EXTENSIONS = {
        "pdf",
        "doc",
        "docx",
        "ppt",
        "pptx",
        "xls",
        "xlsx",
        "txt",
        "png",
        "jpg",
        "jpeg",
        "gif",
    }
    ALLOWED_ASSIGNMENT_EXTENSIONS = ALLOWED_MATERIAL_EXTENSIONS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    IS_PRODUCTION = False
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_PUBLISHABLE_KEY = os.environ.get(
        "SUPABASE_PUBLISHABLE_KEY",
        os.environ.get("SUPABASE_ANON_KEY", ""),
    )
    SUPABASE_SECRET_KEY = os.environ.get(
        "SUPABASE_SECRET_KEY",
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
    )
    SUPABASE_AUTH_ENABLED = os.environ.get(
        "SUPABASE_AUTH_ENABLED",
        "true" if SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY else "false",
    ).lower() in {"1", "true", "yes", "on"}


class DevelopmentConfig(BaseConfig):
    """Local development settings."""

    DEBUG = True


class TestingConfig(BaseConfig):
    """Testing settings."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}


class ProductionConfig(BaseConfig):
    """Production settings."""

    DEBUG = False
    IS_PRODUCTION = True
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(config_name: str | None = None):
    """Return a config class based on FLASK_ENV or an explicit name."""
    selected = config_name or os.environ.get("FLASK_ENV", "development")
    return CONFIG_BY_NAME.get(selected, DevelopmentConfig)
