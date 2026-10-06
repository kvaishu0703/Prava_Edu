from datetime import date
from pathlib import Path
from flask import Blueprint, abort, current_app, flash, redirect, render_template, Response, send_file, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp
from sqlalchemy.exc import SQLAlchemyError
from app.decorators import roles_required
from app.extensions import db
from app.models import User, Student, Faculty, Course, Curriculum, ActivityLog
from app.models.record_import import RecordImport
from app.services.roster import HEADERS, MAX_FILE_BYTES, validate_roster, encode_roster
from app.services.roster_credentials import (HANDOUT_KIND, LIFETIME, utc_now, purge_expired_imports,
                                             create_handout, consume_handout, temporary_password)

office_bp = Blueprint('office', __name__, url_prefix='/admin')


class ImportForm(FlaskForm):
    kind = SelectField('Record type', choices=[('students', 'Students'), ('staff', 'Staff')])
    file = FileField('College roster (.xlsx or UTF-8 CSV, up to 200 rows)', validators=[FileRequired()])
    submit = SubmitField('Validate & preview')


class ConfirmForm(FlaskForm):
    submit = SubmitField('Create accounts and generate passwords')


class CredentialDownloadForm(FlaskForm):
    submit = SubmitField('Download login IDs and passwords (CSV)')


class OfficeAccountForm(FlaskForm):
    full_name = StringField('Full name', validators=[DataRequired(), Length(max=120)])
    username = StringField('Username', validators=[DataRequired(), Regexp(r'^[a-zA-Z0-9_.-]{3,80}$')])
    email = StringField('Email', validators=[DataRequired(), Length(max=120), Regexp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')])
    password = PasswordField('Initial password', validators=[DataRequired(), Length(min=12, max=128)])
    admin_scope = SelectField('Access', choices=[('office', 'Office · manage academic records'), ('principal', 'Principal · manage students, staff attendance and reports')])
    submit = SubmitField('Create account')


def require_office(administrator=False):
    if administrator and current_user.admin_scope != 'administrator':
        abort(403)


def local_account_import_enabled():
    if current_app.config.get('SUPABASE_AUTH_ENABLED'):
        raise ValueError('This server uses external authentication. Provision matching external login accounts before importing; local password generation is available when local authentication is enabled.')


def private_response(response):
    response.headers['Cache-Control'] = 'no-store, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@office_bp.route('/records/import', methods=['GET', 'POST'])
@roles_required('admin')
def roster_import():
    require_office()
    form = ImportForm()
    if form.validate_on_submit():
        try:
            local_account_import_enabled()
            rows = validate_roster(form.file.data.stream.read(MAX_FILE_BYTES + 1), form.kind.data, form.file.data.filename)
            purge_expired_imports()
            batch = RecordImport(user_id=current_user.id, kind=form.kind.data, payload=rows)
            db.session.add(batch)
            db.session.commit()
            return redirect(url_for('office.import_preview', batch_id=batch.id))
        except ValueError as exc:
            form.file.errors.append(str(exc))
    pending_handouts = RecordImport.query.filter_by(user_id=current_user.id, kind=HANDOUT_KIND).filter(RecordImport.created_at >= utc_now() - LIFETIME).order_by(RecordImport.created_at.desc()).all()
    return render_template('office/import.html', form=form, pending_handouts=pending_handouts)


@office_bp.get('/records/template/<kind>.csv')
@roles_required('admin')
def roster_template(kind):
    require_office()
    if kind not in HEADERS:
        abort(404)
    return Response(encode_roster([], kind), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename="prava-{kind}-template.csv"'})


@office_bp.get('/records/template/<kind>.xlsx')
@roles_required('admin')
def roster_excel_template(kind):
    require_office()
    if kind not in HEADERS:
        abort(404)
    return send_file(Path(current_app.root_path) / 'data' / 'roster_templates' / f'prava-{kind}-template.xlsx', as_attachment=True)


@office_bp.route('/records/import/<batch_id>', methods=['GET', 'POST'])
@roles_required('admin')
def import_preview(batch_id):
    require_office()
    batch = RecordImport.query.filter_by(id=batch_id, user_id=current_user.id).filter(RecordImport.kind.in_(HEADERS)).first_or_404()
    if batch.created_at < utc_now() - LIFETIME:
        db.session.delete(batch)
        db.session.commit()
        flash('This preview expired. Upload the file again.', 'info')
        return redirect(url_for('office.roster_import'))
    form = ConfirmForm()
    if form.validate_on_submit():
        try:
            local_account_import_enabled()
            rows = validate_roster(encode_roster(batch.payload, batch.kind), batch.kind)
            credentials = []
            for row in rows:
                password = temporary_password()
                user = User(full_name=row['full_name'], username=row['username'], email=row['email'], gender=row['gender'] or None,
                            role='student' if batch.kind == 'students' else 'faculty', is_active=True, is_demo=False)
                user.set_password(password)
                db.session.add(user)
                if batch.kind == 'students':
                    course = Course.query.filter_by(code=row['programme']).one()
                    curriculum = Curriculum.query.filter_by(course_id=course.id, pattern=row['pattern']).one()
                    db.session.add(Student(user=user, enrollment_number=row['enrollment_number'], course=course, curriculum=curriculum,
                                           semester=int(row['semester']), admission_year=int(row['admission_year']), record_source='imported',
                                           mobile_number=row['mobile_number'] or None, gender=row['gender'] or None,
                                           date_of_birth=date.fromisoformat(row['date_of_birth']) if row['date_of_birth'] else None,
                                           address=row['address'] or None, practical_batch=row['practical_batch'] or None))
                    login_path = url_for('auth.student_login', department='bca' if course.code == 'BCA' else 'home-science')
                else:
                    db.session.add(Faculty(user=user, employee_id=row['employee_id'], department=row['department'], qualification=row['qualification'],
                                           mobile_number=row['mobile_number'] or None,
                                           joining_date=date.fromisoformat(row['joining_date']) if row['joining_date'] else None))
                    login_path = url_for('auth.role_login', role_slug='staff')
                credentials.append({'full_name': row['full_name'], 'role': user.role,
                                    'programme_or_department': row.get('programme', row.get('department')),
                                    'student_or_employee_id': row.get('enrollment_number', row.get('employee_id')),
                                    'login_id': user.username, 'temporary_password': password, 'login_path': login_path})
            count, kind = len(rows), batch.kind
            handout = create_handout(current_user.id, kind, credentials)
            db.session.add(ActivityLog(user_id=current_user.id, action='import_roster', module='office', description=f'Imported {count} active {kind} accounts.'))
            db.session.delete(batch)
            db.session.commit()
            flash(f'{count} {kind} accounts created and ready to log in. Download the private credential handout now.', 'success')
            return redirect(url_for('office.import_credentials', batch_id=handout.id))
        except (ValueError, SQLAlchemyError, OSError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else 'Records changed while importing. Nothing was imported; upload a fresh file.', 'danger')
            return redirect(url_for('office.roster_import'))
    return render_template('office/preview.html', batch=batch, headers=HEADERS[batch.kind], form=form)


@office_bp.route('/records/credentials/<batch_id>', methods=['GET', 'POST'])
@roles_required('admin')
def import_credentials(batch_id):
    require_office()
    handout = RecordImport.query.filter_by(id=batch_id, user_id=current_user.id, kind=HANDOUT_KIND).first_or_404()
    if handout.created_at < utc_now() - LIFETIME:
        db.session.delete(handout)
        db.session.commit()
        flash('This credential handout expired. Accounts remain active; reset an individual password from the account editor if needed.', 'info')
        return redirect(url_for('office.roster_import'))
    form = CredentialDownloadForm()
    if form.validate_on_submit():
        try:
            body = consume_handout(handout)
            db.session.add(ActivityLog(user_id=current_user.id, action='download_roster_credentials', module='office', description='Downloaded a private one-time account handout.'))
            db.session.commit()
            return private_response(Response(body, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename="prava-private-login-handout.csv"'}))
        except (ValueError, SQLAlchemyError, OSError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else 'The handout could not be downloaded. Try again.', 'danger')
            return redirect(url_for('office.roster_import'))
    return private_response(current_app.make_response(render_template('office/credentials.html', batch=handout, form=form)))


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
