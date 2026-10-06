"""Student-owned and staff-scoped, read-only academic year history."""
from flask import Blueprint, abort, render_template, request, url_for
from flask_login import current_user
from app.decorators import roles_required
from app.models import Student
from app.services.academic_history import academic_history_view
from app.services.audit_time import college_timestamp

academic_history_bp = Blueprint('academic_history', __name__)


def _page(student, mine):
    raw_year = request.args.get('year')
    try:
        year = int(raw_year) if raw_year else None
        view = academic_history_view(current_user, student, year)
    except PermissionError:
        abort(403)
    except (ValueError, TypeError):
        abort(404)
    base_url = url_for('academic_history.mine') if mine else url_for('academic_history.student_record', student_id=student.id)
    current_url = url_for('student.attendance', year=view['years'][0]['academic_year']) if mine else url_for('campus.student_record', student_id=student.id, year=view['years'][0]['academic_year'])
    return render_template('academic_history.html', **view, mine=mine, history_url=base_url,
                           current_record_url=current_url, timefmt=college_timestamp)


@academic_history_bp.get('/student/academic-history')
@roles_required('student')
def mine():
    student = current_user.student_profile
    if not student:
        abort(404)
    return _page(student, True)


@academic_history_bp.get('/campus/students/<int:student_id>/history')
@roles_required('admin', 'faculty')
def student_record(student_id):
    student = Student.query.get_or_404(student_id)
    return _page(student, False)
