from datetime import datetime, timedelta, timezone
import secrets
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, Response, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, PasswordField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Regexp
from sqlalchemy.exc import SQLAlchemyError
from app.decorators import roles_required
from app.extensions import db
from app.models import User, Student, Faculty, Course, Curriculum, ActivityLog
from app.models.record_import import RecordImport
from app.services.roster import HEADERS, validate_roster, encode_roster

office_bp = Blueprint('office', __name__, url_prefix='/admin')


class ImportForm(FlaskForm):
    kind = SelectField('Record type', choices=[('students', 'Students'), ('staff', 'Staff')])
    file = FileField('College roster (UTF-8 CSV, up to 200 rows)', validators=[FileRequired()])
    submit = SubmitField('Validate & preview')


class ConfirmForm(FlaskForm):
    submit = SubmitField('Import these records')


class OfficeAccountForm(FlaskForm):
    full_name = StringField('Full name', validators=[DataRequired(), Length(max=120)])
    username = StringField('Username', validators=[DataRequired(), Regexp(r'^[a-zA-Z0-9_.-]{3,80}$')])
    email = StringField('Email', validators=[DataRequired(), Length(max=120), Regexp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')])
    password = PasswordField('Initial password', validators=[DataRequired(), Length(min=12, max=128)])
    admin_scope = SelectField('Access', choices=[('office', 'Office · manage academic records'), ('principal', 'Principal · view both departments and reports')])
    submit = SubmitField('Create account')


def require_office(administrator=False):
    if current_user.admin_scope == 'principal' or (administrator and current_user.admin_scope != 'administrator'):
        abort(403)


@office_bp.route('/records/import', methods=['GET', 'POST'])
@roles_required('admin')
def roster_import():
    require_office()
    form = ImportForm()
    if form.validate_on_submit():
        try:
            rows = validate_roster(form.file.data.stream.read(1024 * 1024 + 1), form.kind.data)
            RecordImport.query.filter(RecordImport.created_at < datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)).delete()
            batch = RecordImport(user_id=current_user.id, kind=form.kind.data, payload=rows)
            db.session.add(batch)
            db.session.commit()
            return redirect(url_for('office.import_preview', batch_id=batch.id))
        except ValueError as exc:
            form.file.errors.append(str(exc))
    return render_template('office/import.html', form=form)


@office_bp.get('/records/template/<kind>.csv')
@roles_required('admin')
def roster_template(kind):
    require_office()
    if kind not in HEADERS:
        abort(404)
    return Response(encode_roster([], kind), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename="prava-{kind}-template.csv"'})


@office_bp.route('/records/import/<batch_id>', methods=['GET', 'POST'])
@roles_required('admin')
def import_preview(batch_id):
    require_office()
    batch = RecordImport.query.filter_by(id=batch_id, user_id=current_user.id).first_or_404()
    if batch.created_at < datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1):
        db.session.delete(batch)
        db.session.commit()
        flash('This preview expired. Upload the file again.', 'info')
        return redirect(url_for('office.roster_import'))
    form = ConfirmForm()
    if form.validate_on_submit():
        try:
            rows = validate_roster(encode_roster(batch.payload, batch.kind), batch.kind)
            for row in rows:
                user = User(full_name=row['full_name'], username=row['username'], email=row['email'], role='student' if batch.kind == 'students' else 'faculty', is_active=False)
                user.set_password(secrets.token_urlsafe(32))
                db.session.add(user)
                if batch.kind == 'students':
                    course = Course.query.filter_by(code=row['programme']).one()
                    curriculum = Curriculum.query.filter_by(course_id=course.id, pattern=row['pattern']).one()
                    db.session.add(Student(user=user, enrollment_number=row['enrollment_number'], course=course, curriculum=curriculum, semester=int(row['semester']), admission_year=int(row['admission_year'])))
                else:
                    db.session.add(Faculty(user=user, employee_id=row['employee_id'], department=row['department'], qualification=row['qualification']))
            count, kind = len(rows), batch.kind
            db.session.add(ActivityLog(user_id=current_user.id, action='import_roster', module='office', description=f'Imported {count} inactive {kind} accounts.'))
            db.session.delete(batch)
            db.session.commit()
            flash(f'{count} {kind} records imported. Set each account password and activate it from the account editor.', 'success')
            return redirect(url_for('admin.students' if kind == 'students' else 'admin.faculty'))
        except (ValueError, SQLAlchemyError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else 'Records changed while importing. Nothing was imported; upload a fresh file.', 'danger')
            return redirect(url_for('office.roster_import'))
    return render_template('office/preview.html', batch=batch, headers=HEADERS[batch.kind], form=form)


@office_bp.route('/access', methods=['GET', 'POST'])
@roles_required('admin')
def access():
    require_office(administrator=True)
    form = OfficeAccountForm()
    if form.validate_on_submit():
        username, email = form.username.data.strip().lower(), form.email.data.strip().lower()
        if User.query.filter((User.username == username) | (User.email == email)).first():
            form.username.errors.append('Username or email already exists.')
        elif current_app.config.get('SUPABASE_AUTH_ENABLED'):
            form.username.errors.append('Provision the matching external authentication account before enabling this workflow.')
        else:
            user = User(username=username, email=email, full_name=form.full_name.data.strip(), role='admin', admin_scope=form.admin_scope.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.add(ActivityLog(user_id=current_user.id, action='create_office_account', module='office', description=f'Created {form.admin_scope.data} access for {username}.'))
            try:
                db.session.commit()
                flash('Account created. Both departments are available through the Administration login.', 'success')
                return redirect(url_for('office.access'))
            except SQLAlchemyError:
                db.session.rollback()
                form.username.errors.append('Account could not be saved. Check for an existing username or email.')
    return render_template('office/access.html', form=form, accounts=User.query.filter_by(role='admin').order_by(User.full_name).all())
