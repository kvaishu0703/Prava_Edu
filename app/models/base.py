"""Reusable model mixins."""

from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    """Return the current UTC time for database timestamps."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Add created and updated timestamps to a model."""

    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
