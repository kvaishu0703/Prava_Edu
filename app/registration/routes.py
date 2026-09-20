from datetime import datetime, timedelta, timezone
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.decorators import roles_required
from app.models import Course, Curriculum, User, Student, StudentRegistration, ActivityLog
from app.registration.forms import SignupForm, ReviewRegistrationForm
from app.services.college import PROGRAMMES, DEPARTMENTS

registration_bp = Blueprint('registration', __name__)


@registration_bp.route('/signup', methods=['GET', 'POST'])
@registration_bp.route('/signup/<department>', methods=['GET', 'POST'])
def signup(department=None):
    if department and department not in DEPARTMENTS:
        abort(404)
    available = current_app.config.get('STUDENT_SIGNUP_ENABLED') and not current_app.config.get('SUPABASE_AUTH_ENABLED')
    form = SignupForm()
    codes = [code for code, _, slug, _ in PROGRAMMES if not department or slug == department]
    curricula = Curriculum.query.join(Course).filter(Course.code.in_(codes), Course.is_active.is_(True), Curriculum.pattern == '2024 NEP').all()
    options = {c.course.code: c for c in curricula}
    form.programme.choices = [(c.course.code, c.course.name) for c in curricula]
    if form.validate_on_submit() and available:
        username = form.username.data.strip().lower()
        email = form.email.data.strip().lower()
        enrollment = form.enrollment_number.data.strip().upper()
        now = datetime.now(timezone.utc).timestamp()
        attempts = [stamp for stamp in session.get('signup_attempts', []) if stamp > now - 600]
        if len(attempts) >= 5:
            flash('Please wait a few minutes before submitting another request.', 'warning')
            return render_template('auth/signup.html', form=form, department=department, available=available), 429
        session['signup_attempts'] = [*attempts, now]
        conflict = (User.query.filter(or_(User.username == username, User.email == email)).first()
                    or Student.query.filter_by(enrollment_number=enrollment).first()
                    or StudentRegistration.query.filter(or_(StudentRegistration.username == username, StudentRegistration.email == email,
                                                            StudentRegistration.enrollment_number == enrollment)).first())
        if conflict:
            form.enrollment_number.errors.append('An account or request already uses these details. Contact the office to check your enrollment or sign-up.')
        else:
            item = StudentRegistration(username=username, email=email, enrollment_number=enrollment,
                                       full_name=form.full_name.data.strip(), password_hash=generate_password_hash(form.password.data),
                                       curriculum=options[form.programme.data], semester=form.semester.data, admission_year=form.admission_year.data)
            db.session.add(item)
            try:
                db.session.commit()
                return redirect(url_for('registration.signup_complete'))
            except IntegrityError:
                db.session.rollback()
                form.enrollment_number.errors.append('These details already have a request. Contact the office for help.')
    return render_template('auth/signup.html', form=form, department=department, available=available)


@registration_bp.get('/signup/complete')
def signup_complete():
    return render_template('auth/signup_complete.html')


@registration_bp.get('/admin/registrations')
@roles_required('admin')
def registrations():
    status = request.args.get('status', 'Pending')
    if status not in {'Pending', 'Approved', 'Rejected', 'All'}:
        abort(400)
    query = StudentRegistration.query
    if status != 'All':
        query = query.filter_by(status=status)
    return render_template('office/registrations.html', registrations=query.order_by(StudentRegistration.created_at.desc()).all(), selected=status)


@registration_bp.route('/admin/registrations/<int:registration_id>', methods=['GET', 'POST'])
@roles_required('admin')
def review(registration_id):
    item = StudentRegistration.query.get_or_404(registration_id)
    form = ReviewRegistrationForm()
    if request.method == 'POST' and current_user.admin_scope == 'principal':
        abort(403)
    if form.validate_on_submit():
        if current_app.config.get('SUPABASE_AUTH_ENABLED'):
            flash('This request uses local authentication. Complete external identity provisioning before approval.', 'warning')
            return redirect(url_for('registration.review', registration_id=item.id))
        claimed = db.session.execute(update(StudentRegistration).where(StudentRegistration.id == item.id, StudentRegistration.status == 'Pending').values(status='Reviewing'))
        if claimed.rowcount != 1:
            db.session.rollback()
            flash('This request has already been reviewed.', 'info')
            return redirect(url_for('registration.registrations'))
        if form.decision.data == 'Approved':
            if not item.curriculum.course.is_active or not item.password_hash:
                db.session.rollback()
                flash('Check the programme and the registration credentials before approval.', 'warning')
                return redirect(url_for('registration.review', registration_id=item.id))
            user = User(username=item.username, email=item.email, full_name=item.full_name, password_hash=item.password_hash,
                        role='student', is_active=True, is_demo=False)
            db.session.add(user)
            db.session.add(Student(user=user, enrollment_number=item.enrollment_number, curriculum=item.curriculum,
                                   course=item.curriculum.course, semester=item.semester, admission_year=item.admission_year))
            item.user = user
        item.status = form.decision.data
        item.review_note = (form.note.data or '').strip()
        item.reviewed_by = current_user.id
        item.reviewed_at = datetime.now(timezone.utc)
        item.password_hash = None
        db.session.add(ActivityLog(user_id=current_user.id, action='review_signup', module='office', description=f'Student registration {item.id}: {item.status}'))
        try:
            db.session.commit()
            flash('Student account activated.' if item.status == 'Approved' else 'Registration declined.', 'success')
            return redirect(url_for('registration.registrations'))
        except IntegrityError:
            db.session.rollback()
            flash('An existing account or enrollment conflicts with this request. Nothing was changed; check the college records.', 'danger')
    return render_template('office/registration_review.html', item=item, form=form)
