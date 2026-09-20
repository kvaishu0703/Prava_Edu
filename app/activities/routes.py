from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.decorators import roles_required
from app.models import CampusActivity, ActivityParticipation, ActivityLog
from app.services.college import ACTIVITY_AREAS, department_for_course
from app.activities.forms import ActivityForm, ParticipationForm, ReviewForm

activities_bp = Blueprint('activities', __name__)


def now_ist():
    return datetime.now(ZoneInfo('Asia/Kolkata')).replace(tzinfo=None)


def can_manage(activity):
    return current_user.is_authenticated and (
        (current_user.role == 'admin' and current_user.admin_scope != 'principal') or
        (current_user.role == 'faculty' and activity.coordinator_id == current_user.id))


def eligible_student(activity):
    student = current_user.student_profile if current_user.role == 'student' else None
    if not student or activity.department not in ('all', department_for_course(student.course)):
        abort(403)
    return student


def workspace_base():
    return f'{current_user.role}/{current_user.role}_base.html'


@activities_bp.get('/activities')
def index():
    department = request.args.get('department', 'all')
    if department not in ('all', 'bca', 'home-science'):
        abort(400)
    query = CampusActivity.query.filter_by(is_active=True)
    if department != 'all':
        query = query.filter(CampusActivity.department.in_(['all', department]))
    items = query.order_by(CampusActivity.starts_at.desc()).all()
    today = now_ist()
    return render_template('activities/index.html', items=items, upcoming=[a for a in reversed(items) if a.starts_at >= today],
                           past=[a for a in items if a.starts_at < today], areas=ACTIVITY_AREAS, selected=department)


@activities_bp.get('/activities/<int:activity_id>')
def detail(activity_id):
    activity = CampusActivity.query.get_or_404(activity_id)
    if not activity.is_active and not can_manage(activity):
        abort(404)
    participation = None
    eligible = False
    if current_user.is_authenticated and current_user.role == 'student' and current_user.student_profile:
        student = current_user.student_profile
        eligible = activity.department in ('all', department_for_course(student.course))
        participation = ActivityParticipation.query.filter_by(activity_id=activity.id, student_id=student.id).first()
    return render_template('activities/detail.html', activity=activity, participation=participation,
                           eligible=eligible, can_manage=can_manage(activity), form=ParticipationForm(), registration_open=activity.starts_at > now_ist())


@activities_bp.post('/activities/<int:activity_id>/register')
@roles_required('student')
def register(activity_id):
    activity = CampusActivity.query.filter_by(id=activity_id, is_active=True).first_or_404()
    student = eligible_student(activity)
    if activity.starts_at <= now_ist():
        abort(400)
    form = ParticipationForm()
    if not form.validate_on_submit():
        abort(400)
    if not ActivityParticipation.query.filter_by(activity_id=activity.id, student_id=student.id).first():
        db.session.add(ActivityParticipation(activity=activity, student=student))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    flash('Your registration is saved.', 'success')
    return redirect(url_for('activities.detail', activity_id=activity.id))


@activities_bp.post('/activities/<int:activity_id>/evidence')
@roles_required('student')
def evidence(activity_id):
    activity = CampusActivity.query.filter_by(id=activity_id, is_active=True).first_or_404()
    student = eligible_student(activity)
    row = ActivityParticipation.query.filter_by(activity_id=activity.id, student_id=student.id).first_or_404()
    form = ParticipationForm()
    if not form.validate_on_submit() or row.status == 'Completed':
        abort(400)
    row.evidence = form.evidence.data
    db.session.commit()
    flash('Participation details saved for review.', 'success')
    return redirect(url_for('activities.detail', activity_id=activity.id))


@activities_bp.route('/campus/activities/new', methods=['GET', 'POST'])
@roles_required('admin', 'faculty')
def create():
    if current_user.role == 'admin' and current_user.admin_scope == 'principal':
        abort(403)
    form = ActivityForm()
    if form.validate_on_submit():
        item = CampusActivity(coordinator_id=current_user.id)
        form.populate_obj(item)
        db.session.add(item)
        db.session.commit()
        flash('Activity saved.', 'success')
        return redirect(url_for('activities.detail', activity_id=item.id))
    return render_template('activities/editor.html', form=form, base=workspace_base(), title='Create activity')


@activities_bp.route('/campus/activities/<int:activity_id>/edit', methods=['GET', 'POST'])
@roles_required('admin', 'faculty')
def edit(activity_id):
    item = CampusActivity.query.get_or_404(activity_id)
    if not can_manage(item):
        abort(403)
    form = ActivityForm(obj=item)
    if form.validate_on_submit():
        # Keep the department stable after registration so enrolled students retain access.
        if item.participations and item.department != form.department.data:
            form.department.errors.append('Department cannot change after students register.')
        elif any(row.status == 'Completed' for row in item.participations) and (item.title, item.venue, item.starts_at) != (form.title.data, form.venue.data, form.starts_at.data):
            form.title.errors.append('This activity has verified participation records. Return them to review before changing the title, venue or date.')
        else:
            form.populate_obj(item)
            db.session.commit()
            flash('Activity updated.', 'success')
            return redirect(url_for('activities.detail', activity_id=item.id))
    return render_template('activities/editor.html', form=form, base=workspace_base(), title='Edit activity')


@activities_bp.route('/campus/activities/<int:activity_id>/participants', methods=['GET', 'POST'])
@roles_required('admin', 'faculty')
def participants(activity_id):
    item = CampusActivity.query.get_or_404(activity_id)
    if not can_manage(item):
        abort(403)
    form = ReviewForm()
    if form.validate_on_submit():
        row = ActivityParticipation.query.filter_by(id=request.form.get('participation_id', type=int), activity_id=item.id).first_or_404()
        if form.status.data == 'Completed' and (form.hours.data is None or form.hours.data <= 0 or item.starts_at > now_ist()):
            flash('Completion requires positive verified hours and an activity that has started.', 'danger')
        else:
            row.status = form.status.data
            row.hours = form.hours.data
            row.reviewed_by = current_user.id
            row.reviewed_at = datetime.utcnow()
            db.session.add(ActivityLog(user_id=current_user.id, action='activity_review', module='activities', description=f'Participation {row.id}: {row.status}'))
            db.session.commit()
            flash('Participation reviewed.', 'success')
            return redirect(url_for('activities.participants', activity_id=item.id))
    return render_template('activities/participants.html', activity=item, form=form, base=workspace_base())


@activities_bp.get('/student/activities')
@roles_required('student')
def portfolio():
    student = current_user.student_profile
    rows = ActivityParticipation.query.filter_by(student_id=student.id).join(ActivityParticipation.activity).order_by(CampusActivity.starts_at.desc()).all() if student else []
    return render_template('activities/portfolio.html', rows=rows)


@activities_bp.get('/activities/participation/<int:participation_id>/certificate')
@roles_required('student', 'admin', 'faculty')
def certificate(participation_id):
    row = ActivityParticipation.query.get_or_404(participation_id)
    owns = current_user.role == 'student' and current_user.student_profile and row.student_id == current_user.student_profile.id
    if not owns and not can_manage(row.activity):
        abort(403)
    if row.status != 'Completed' or not row.reviewer:
        abort(404)
    return render_template('activities/certificate.html', row=row)
