"""Additive academic-history schema; current marks and attendance remain intact."""
from app.extensions import db
from app.models.academic_history import AcademicYearRecord


def upgrade_academic_history_schema():
    AcademicYearRecord.__table__.create(db.engine, checkfirst=True)
