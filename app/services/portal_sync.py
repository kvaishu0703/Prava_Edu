"""Refresh read views after a committed change, without interrupting data entry."""
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from app.extensions import db
from app.models.portal_revision import PortalRevision

portal_sync_bp = Blueprint('portal_sync', __name__)
READ_VIEWS = {
    'student.dashboard', 'student.profile', 'student.subjects', 'student.attendance',
    'student.timetable', 'student.marks', 'student.notifications', 'student.materials',
    'student.assignments', 'faculty.dashboard', 'faculty.students', 'faculty.subjects',
    'faculty.attendance_report', 'faculty.marks_report', 'faculty.notifications',
    'faculty.materials', 'faculty.assignments', 'faculty.assignment_submissions',
    'admin.dashboard', 'admin.students', 'admin.faculty', 'admin.courses',
    'admin.subjects', 'admin.reports', 'admin.notifications', 'admin.contact_inquiries',
    'timetables.index', 'activities.index', 'activities.portfolio',
    'campus.my_attendance', 'campus.class_students', 'campus.student_record',
    'campus_corrections.list_register',
    'academic_history.mine', 'academic_history.student_record',
}
IGNORED_TABLES = {'portal_revision', 'activity_logs', 'notification_reads'}


def _meaningful_change(obj, session):
    table = getattr(obj, '__tablename__', None)
    if not table or table in IGNORED_TABLES:
        return False
    if obj in session.new or obj in session.deleted:
        return True
    changed = {attr.key for attr in inspect(obj).attrs if attr.history.has_changes()}
    if table in {'attendance', 'staff_attendance'}:
        return bool(changed)
    return bool(changed - ({'last_login', 'updated_at'} if table == 'users' else {'updated_at'}))


@event.listens_for(Session, 'after_flush')
def revision_after_flush(session, flush_context):
    if not any(_meaningful_change(obj, session) for obj in session.new | session.dirty | session.deleted):
        return
    connection = session.connection()
    table = PortalRevision.__table__
    now = datetime.now(timezone.utc)
    result = connection.execute(table.update().where(table.c.id == 1).values(
        version=table.c.version + 1, updated_at=now))
    if result.rowcount == 0:
        connection.execute(table.insert().values(id=1, version=1, updated_at=now))


def current_revision():
    row = db.session.get(PortalRevision, 1)
    return row.version if row else 0


def ensure_revision():
    if db.session.get(PortalRevision, 1) is None:
        db.session.add(PortalRevision(id=1, version=0))
        db.session.commit()


@portal_sync_bp.get('/api/portal-state')
@login_required
def state():
    # No other student's or staff member's data is exposed by this endpoint.
    return jsonify(version=current_revision(), checked_at=datetime.now(timezone.utc).isoformat())


def register_portal_sync(app):
    app.register_blueprint(portal_sync_bp)

    @app.context_processor
    def sync_context():
        if not current_user.is_authenticated:
            return {'portal_live': False}
        return {'portal_live': True, 'portal_revision': current_revision(),
                'portal_auto_refresh': request.endpoint in READ_VIEWS or (
                    current_user.role == 'faculty' and request.endpoint == 'campus.class_teachers')}
