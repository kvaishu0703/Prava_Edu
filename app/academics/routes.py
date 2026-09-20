from datetime import date
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import case
from app.extensions import db
from app.decorators import roles_required
from app.models import Course, Curriculum, CurriculumSubject, SyllabusDocument, ActivityLog
from app.services.college import DEPARTMENTS, PROGRAMMES, STAFF_DIRECTORY, department_for_course
from app.academics.forms import DocumentForm, CurriculumSubjectForm

academics_bp = Blueprint('academics', __name__)


def audit(action, description):
    db.session.add(ActivityLog(user_id=current_user.id, action=action, module='academics', description=description))


def require_editor():
    if current_user.admin_scope == 'principal':
        abort(403)


@academics_bp.get('/academics/<department>')
def department(department):
    if department not in DEPARTMENTS:
        abort(404)
    codes = [code for code, _, slug, _ in PROGRAMMES if slug == department]
    programmes = Course.query.filter(Course.code.in_(codes), Course.is_active.is_(True)).order_by(Course.code).all()
    code = request.args.get('programme', programmes[0].code if programmes else '')
    programme = next((p for p in programmes if p.code == code), None)
    if programmes and not programme:
        abort(404)
    curriculum = Curriculum.query.filter_by(course_id=programme.id, pattern='2024 NEP').first() if programme else None
    try:
        year = int(request.args.get('year', '1'))
        semester = int(request.args.get('semester', str(year * 2 - 1)))
        if year not in (1, 2, 3) or semester not in (year * 2 - 1, year * 2):
            raise ValueError
    except ValueError:
        abort(400)
    document = SyllabusDocument.query.filter_by(curriculum_id=curriculum.id, year=year).first() if curriculum else None
    subjects = CurriculumSubject.query.filter_by(curriculum_id=curriculum.id, semester=semester, is_verified=True).order_by(case({'Major': 0, 'VSC': 1, 'VSEC': 1, 'SEC': 1, 'IKS': 2, 'Field Project': 3, 'Community Engagement': 3, 'Internship': 3, 'Minor': 4}, value=CurriculumSubject.category, else_=5), CurriculumSubject.code).all() if curriculum else []
    return render_template('academics/department.html', department_slug=department, info=DEPARTMENTS[department],
                           programmes=programmes, programme=programme, curriculum=curriculum, year=year,
                           semester=semester, document=document, subjects=subjects)


@academics_bp.get('/academics/subject/<int:subject_id>')
def subject(subject_id):
    item = CurriculumSubject.query.filter_by(id=subject_id, is_verified=True).first_or_404()
    return render_template('academics/subject.html', item=item)


@academics_bp.get('/about/faculty')
def faculty():
    selected = request.args.get('department', 'all')
    if selected not in {'all', *DEPARTMENTS}:
        abort(400)
    staff = [row for row in STAFF_DIRECTORY if selected == 'all' or row[0] == selected]
    return render_template('core/faculty_directory.html', staff=staff, selected=selected)


@academics_bp.get('/student/syllabus')
@roles_required('student')
def student_syllabus():
    student = current_user.student_profile
    slug = department_for_course(student.course) if student else None
    if not slug or not student.curriculum or student.curriculum.pattern != '2024 NEP':
        flash('Please ask the office to link your enrolled curriculum pattern.', 'info')
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('academics.department', department=slug, programme=student.course.code,
                            year=(student.semester + 1)//2, semester=student.semester))


@academics_bp.get('/admin/curriculum')
@roles_required('admin')
def manage():
    return render_template('academics/manage.html', curricula=Curriculum.query.join(Curriculum.course).order_by(Course.code).all())


@academics_bp.route('/admin/curriculum/document/<int:document_id>', methods=['GET', 'POST'])
@roles_required('admin')
def document_edit(document_id):
    require_editor()
    document = SyllabusDocument.query.get_or_404(document_id)
    form = DocumentForm(obj=document)
    if form.validate_on_submit():
        form.populate_obj(document)
        document.checked_at = date.today()
        audit('update_document', f'Updated syllabus document {document.id}: {document.status}')
        db.session.commit()
        flash('Syllabus reference updated.', 'success')
        return redirect(url_for('academics.manage'))
    return render_template('academics/editor.html', form=form, title=f'{document.curriculum.course.code} · Year {document.year} document')


@academics_bp.route('/admin/curriculum/<int:curriculum_id>/subjects/new', methods=['GET', 'POST'])
@roles_required('admin')
def subject_new(curriculum_id):
    require_editor()
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    return edit_subject_form(curriculum, None)


@academics_bp.route('/admin/curriculum/subjects/<int:subject_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def subject_edit(subject_id):
    require_editor()
    item = CurriculumSubject.query.get_or_404(subject_id)
    return edit_subject_form(item.curriculum, item)


def edit_subject_form(curriculum, item):
    form = CurriculumSubjectForm(obj=item)
    if form.validate_on_submit():
        if item is None:
            item = CurriculumSubject(curriculum=curriculum)
            db.session.add(item)
        form.populate_obj(item)
        item.code = item.code.strip().upper()
        audit('save_curriculum_subject', f'{curriculum.course.code}: semester {item.semester}, {item.code}')
        try:
            db.session.commit()
            flash('Curriculum subject saved.', 'success')
            return redirect(url_for('academics.manage'))
        except IntegrityError:
            db.session.rollback()
            form.code.errors.append('This code already exists in the selected semester.')
    return render_template('academics/editor.html', form=form, title=f'{curriculum.course.code} · {curriculum.pattern} · Subject')
