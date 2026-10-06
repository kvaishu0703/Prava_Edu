"""Reversible student removal with explicit, validated selections and audit history."""
from datetime import datetime, timezone
import hashlib
import hmac
import json
from sqlalchemy import select

from app.extensions import db
from app.models import Student, User
from app.services.workflow_updates import record_update

RECORD_SOURCES = {"provided": "Provided", "generated": "Generated project record", "imported": "Imported"}


def active_students_query():
    """Current enrolment totals use the same active accounts as teaching rosters."""
    return Student.query.join(Student.user).filter(
        User.role == 'student', User.is_active.is_(True), Student.archived_at.is_(None))


def student_edit_version(student):
    """Fingerprint this profile/account only; a login elsewhere is not an edit."""
    student_fields = ('id', 'user_id', 'enrollment_number', 'mobile_number', 'date_of_birth',
        'gender', 'address', 'course_id', 'semester', 'admission_year', 'profile_image',
        'curriculum_id', 'practical_batch', 'record_source', 'archived_at', 'archive_reason')
    user_fields = ('id', 'username', 'full_name', 'email', 'password_hash', 'role', 'admin_scope',
        'is_active', 'is_demo', 'profile_image', 'gender')
    payload = {'student':{field:getattr(student,field) for field in student_fields},
               'user':{field:getattr(student.user,field) for field in user_fields}}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode('utf8')).hexdigest()


def student_edit_is_current(student, expected):
    return bool(expected) and hmac.compare_digest(student_edit_version(student), str(expected))


def lock_student_accounts(ids):
    """Serialize edit/remove/restore and reload both halves of each account.

    Every writer locks profiles before users in ID order. SQLite reserves the
    write transaction before the first target query; PostgreSQL locks both rows.
    The caller owns commit/rollback and must not mutate before calling this.
    """
    ids = sorted(set(ids))
    connection = db.session.connection()
    if connection.dialect.name == 'sqlite':
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
    else:
        db.session.execute(select(Student.id).where(Student.id.in_(ids)).order_by(Student.id).with_for_update())
        user_ids = select(Student.user_id).where(Student.id.in_(ids))
        db.session.execute(select(User.id).where(User.id.in_(user_ids)).order_by(User.id).with_for_update())
    students = Student.query.filter(Student.id.in_(ids)).order_by(Student.id).populate_existing().all()
    # The login loader or a preceding view may already have cached a User.
    User.query.filter(User.id.in_([student.user_id for student in students])).populate_existing().all()
    return students


def change_student_status(actor, raw_ids, action, *, selected_count, reason=""):
    """Validate the entire selection before changing any row; caller commits."""
    if not actor or actor.role != "admin" or not actor.is_active:
        raise PermissionError("Student account management requires an active administrator or Principal.")
    if action not in {"archive", "restore"}:
        raise ValueError("Choose Remove or Restore.")
    try:
        ids = [int(value) for value in raw_ids]
    except (TypeError, ValueError):
        raise ValueError("Select valid student accounts.") from None
    if not ids or len(ids) > 500 or len(set(ids)) != len(ids) or len(ids) != selected_count or min(ids) < 1:
        raise ValueError("The selection changed. Select the students and confirm their names again.")
    reason = (reason or "").strip()
    if len(reason) > 500:
        raise ValueError("Keep the reason within 500 characters.")
    students = lock_student_accounts(ids)
    if len(students) != len(ids) or any(student.user.role != 'student' for student in students):
        raise ValueError("One or more selected student accounts no longer exist. Reload the directory.")
    if action == "archive" and any(s.archived_at for s in students):
        raise ValueError("A selected student was already removed. Reload and confirm the remaining students.")
    if action == "restore" and any(not s.archived_at for s in students):
        raise ValueError("Only removed students can be restored. Reload and confirm your selection.")
    now = datetime.now(timezone.utc)
    for student in students:
        student.user.is_active = action == "restore"
        student.archived_at = now if action == "archive" else None
        student.archive_reason = (reason or None) if action == "archive" else None
        record_update(actor, "students", "removed" if action == "archive" else "restored",
                      f"Student #{student.id}: {student.user.full_name} ({student.enrollment_number}). "
                      f"Academic records retained. Reason: {reason or 'Not specified' }.")
    return students
