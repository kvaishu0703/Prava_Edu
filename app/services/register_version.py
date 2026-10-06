"""Serialize selected-register checks with the associated academic write."""
from sqlalchemy import select
from app.extensions import db
from app.models import Subject


def lock_subject_register(subject):
    """Refresh only after taking a write lock, including an empty register.

    SQLite's deferred read transaction does not protect a read/compare/write
    cycle. PostgreSQL locks the parent subject so inserts are protected too.
    The caller commits or rolls back the lock with the academic records.
    """
    connection = db.session.connection()
    if connection.dialect.name == 'sqlite':
        driver_connection = connection.connection.driver_connection
        if not driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
    else:
        db.session.execute(select(Subject.id).where(Subject.id == subject.id).with_for_update())
    db.session.refresh(subject)
