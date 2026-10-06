"""Administrative review and reasoned correction of student attendance."""
import hashlib
import json
from datetime import date
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy.exc import SQLAlchemyError
from wtforms import HiddenField, SelectField, StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from app.decorators import roles_required
from app.extensions import db
from app.models import Attendance, ActivityLog, Student, User
from app.models.base import utc_now
from app.services.attendance import ATTENDANCE_STATUSES
from app.services.attendance_policy import attendance_edit_policy, require_attendance_edit
from app.services.register_version import lock_subject_register
from app.services.timetable import college_today
from app.services.workflow_updates import record_update

corrections_bp = Blueprint('campus_corrections', __name__, url_prefix='/campus/student-attendance')


class CorrectionForm(FlaskForm):
    register_version = HiddenField(validators=[DataRequired()])
    status = SelectField('Attendance status', choices=[(x, x) for x in ATTENDANCE_STATUSES], validators=[DataRequired()])
    remarks = StringField('Attendance note', validators=[Length(max=255)])
    reason = TextAreaField('Reason for correction', validators=[DataRequired(), Length(min=5, max=500)])
    submit = SubmitField('Save correction')


def record_version(row):
    state = [row.id, row.student_id, row.subject_id, row.attendance_date.isoformat(),
             row.session_number, row.status, row.remarks, str(row.updated_at), row.updated_by_user_id]
    return hashlib.sha256(json.dumps(state).encode()).hexdigest()


@corrections_bp.get('')
@roles_required('admin')
def list_register():
    try:
        day = date.fromisoformat(request.args.get('date', college_today().isoformat()))
    except ValueError:
        day = college_today()
        flash('Choose a valid attendance date.', 'warning')
    student_id = request.args.get('student', type=int)
    students = Student.query.join(Student.user).order_by(User.full_name).all()
    query = Attendance.query.filter_by(attendance_date=day)
    if student_id:
        query = query.filter_by(student_id=student_id)
    records = query.join(Attendance.student).join(Student.user).order_by(User.full_name, Attendance.session_number).all()
    return render_template('campus/student_attendance_review.html', records=records, students=students,
        selected_student=student_id, day=day, today=college_today(),
        may_correct=current_user.admin_scope == 'administrator' and day <= college_today())


@corrections_bp.route('/<int:attendance_id>/correct', methods=['GET', 'POST'])
@roles_required('admin')
def correct(attendance_id):
    if current_user.admin_scope != 'administrator':
        abort(403)
    row = db.get_or_404(Attendance, attendance_id)
    form = CorrectionForm()
    policy = attendance_edit_policy(current_user, row.attendance_date)
    conflict = False
    status_code = 200
    if request.method == 'GET':
        form.status.data = row.status
        form.remarks.data = row.remarks
        form.register_version.data = record_version(row)
    if form.validate_on_submit():
        try:
            lock_subject_register(row.subject)
            db.session.refresh(row)
            reason = require_attendance_edit(current_user, row.attendance_date, form.reason.data)
            if form.register_version.data != record_version(row):
                conflict = True
                raise ValueError('This record changed after you opened it. Your draft is retained. Reload the latest record before saving.')
            before = {'status': row.status, 'remarks': row.remarks}
            row.status = form.status.data
            row.remarks = (form.remarks.data or '').strip() or None
            row.updated_at = utc_now()
            row.updated_by_user_id = current_user.id
            record_update(current_user, 'attendance', 'administrator_correction', json.dumps({
                'attendance_id': row.id, 'student_id': row.student_id,
                'attendance_date': row.attendance_date.isoformat(), 'session': row.session_number,
                'reason': reason, 'before': before, 'after': {'status': row.status, 'remarks': row.remarks}}))
            db.session.commit()
            flash('Attendance correction saved. The student and teacher views now show the updated record and your audit time.', 'success')
            return redirect(url_for('campus_corrections.list_register', date=row.attendance_date.isoformat(), student=row.student_id))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), 'danger')
            status_code = 409 if conflict else 400
        except SQLAlchemyError:
            db.session.rollback()
            flash('The correction was not saved. Reload the register and try again.', 'danger')
            status_code = 409
    elif request.method == 'POST':
        status_code = 400
    history = []
    logs = ActivityLog.query.filter_by(module='attendance', action='administrator_correction').filter(
        ActivityLog.description.contains(f'"attendance_id": {row.id},')).order_by(ActivityLog.id.desc()).limit(20)
    for log in logs:
        try:
            details = json.loads(log.description)
        except (TypeError, ValueError):
            continue
        if details.get('attendance_id') == row.id:
            history.append({'log': log, 'details': details})
    return render_template('campus/attendance_correction.html', row=row, form=form,
        policy=policy, conflict=conflict, history=history), status_code
