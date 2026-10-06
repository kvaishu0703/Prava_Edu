"""Principal/Office staff attendance and programme class teachers."""
from datetime import date, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.campus.forms import CampusActionForm, ClassTeacherForm, StaffRegisterForm
from app.decorators import roles_required
from app.extensions import db
from app.models import Course, Curriculum, Faculty, Student, User
from app.models.class_teacher import ClassTeacherAssignment
from app.models.staff_attendance import StaffAttendance
from app.models.base import utc_now
from app.services.campus import (
    STAFF_ATTENDANCE_STATUSES, StaleStaffRegisterError, class_teacher_assignments, college_timestamp,
    month_bounds, save_class_teacher, save_staff_attendance,
    staff_attendance_summary, staff_register_version, student_academic_record, students_for_assignment,
)
from app.services.timetable import academic_year_for, college_today
from app.services.attendance_policy import attendance_edit_policy, require_attendance_edit
from app.services.workflow_updates import record_update

campus_bp = Blueprint("campus", __name__, url_prefix="/campus")


def _active_staff():
    return Faculty.query.join(User).filter(User.is_active.is_(True), User.role == "faculty").order_by(User.full_name).all()


def _month(default=None):
    month = request.args.get("month", default or college_today().strftime("%Y-%m"))
    try:
        first, last = month_bounds(month)
    except ValueError as error:
        flash(str(error), "warning")
        month = college_today().strftime("%Y-%m")
        first, last = month_bounds(month)
    return month, first, last


@campus_bp.route("/staff-attendance", methods=["GET", "POST"])
@roles_required("admin")
def staff_attendance():
    """The Principal and Office share one daily staff register."""
    form = StaffRegisterForm()
    today = college_today()
    day = today
    if request.method == "GET":
        try:
            day = date.fromisoformat(request.args.get("date", day.isoformat()))
            if not 2000 <= day.year <= 2100:
                raise ValueError
        except ValueError:
            day = today
            flash("Choose a valid attendance date.", "warning")
        form.attendance_date.data = day
        form.register_version.data = staff_register_version(day)
    elif form.attendance_date.data:
        day = form.attendance_date.data

    members = _active_staff()
    policy = attendance_edit_policy(current_user, day, today)
    editing = policy['can_edit'] and (request.args.get('edit') == '1' or request.method == 'POST')
    response_code = 200
    conflict = False
    if form.validate_on_submit():
        entries = []
        for member in members:
            status = request.form.get(f"status_{member.id}", "")
            if status:
                entries.append({"faculty_id": member.id, "status": status,
                    "check_in": request.form.get(f"check_in_{member.id}", "") if status == 'Present' else "",
                    "check_out": request.form.get(f"check_out_{member.id}", "") if status == 'Present' else "",
                    "remarks": request.form.get(f"remarks_{member.id}", "")})
        try:
            reason = require_attendance_edit(current_user, day, form.correction_reason.data, today)
            if not entries:
                raise ValueError("Select a status for at least one staff member before saving.")
            changed = save_staff_attendance(current_user, day, entries, expected_version=form.register_version.data, correction_reason=reason)
            if changed:
                record_update(current_user, 'staff_attendance', 'corrected' if policy['requires_reason'] else 'saved',
                    f'{day.isoformat()}: {changed} staff attendance record(s) updated.' + (f' Correction reason: {reason}' if reason else ''))
            db.session.commit()
            flash(f"Attendance for {day.strftime('%A, %d %B %Y')} saved at {college_timestamp(utc_now())}. {changed} record(s) updated.", "success")
            return redirect(url_for("campus.staff_attendance", date=day.isoformat()))
        except StaleStaffRegisterError as error:
            db.session.rollback()
            flash(str(error), "danger")
            response_code = 409
            conflict = True
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            response_code = 400
        except SQLAlchemyError:
            db.session.rollback()
            flash("The register could not be saved. Reload this page and try again.", "danger")
            response_code = 409
    elif request.method == "POST":
        response_code = 400

    month, first, last = _month(day.strftime("%Y-%m"))
    existing = {row.faculty_id: row for row in StaffAttendance.query.filter_by(attendance_date=day).all()}
    active_records = [existing[member.id] for member in members if member.id in existing]
    daily_counts = {status: sum(row.status == status for row in active_records) for status in STAFF_ATTENDANCE_STATUSES}
    daily_counts['Unrecorded'] = len(members) - len(active_records)
    latest_saved = max(active_records, key=lambda row: row.updated_at) if active_records else None
    draft_counts = {status: 0 for status in (*STAFF_ATTENDANCE_STATUSES, 'Unrecorded')}
    for member in members:
        row = existing.get(member.id)
        selected = request.form.get(f'status_{member.id}', row.status if row else '') if editing else (row.status if row else '')
        draft_counts[selected if selected in STAFF_ATTENDANCE_STATUSES else 'Unrecorded'] += 1
    selected_staff = request.args.get("staff", type=int)
    records_query = StaffAttendance.query.filter(StaffAttendance.attendance_date >= first,
        StaffAttendance.attendance_date <= min(last, college_today()))
    if selected_staff:
        records_query = records_query.filter(StaffAttendance.faculty_id == selected_staff)
    records = records_query.order_by(StaffAttendance.attendance_date.desc(), StaffAttendance.faculty_id).all()
    summary_members = Faculty.query.join(User).order_by(User.full_name).all()
    return render_template("campus/staff_attendance.html", form=form, day=day, members=members,
        existing=existing, statuses=STAFF_ATTENDANCE_STATUSES, today=today, month=month,
        records=records, summary=staff_attendance_summary(records), selected_staff=selected_staff,
        summary_members=summary_members, timefmt=college_timestamp, editing=editing, policy=policy, conflict=conflict,
        saved_count=len(active_records), daily_counts=daily_counts, draft_counts=draft_counts, latest_saved=latest_saved,
        yesterday=today-timedelta(days=1), previous_day=day-timedelta(days=1), next_day=day+timedelta(days=1)), response_code


@campus_bp.get("/my-attendance")
@roles_required("faculty")
def my_attendance():
    """Staff can review only their own attendance and correction history."""
    if not current_user.faculty_profile:
        abort(404)
    month, first, last = _month()
    records = StaffAttendance.query.filter(
        StaffAttendance.faculty_id == current_user.faculty_profile.id,
        StaffAttendance.attendance_date >= first, StaffAttendance.attendance_date <= min(last, college_today()),
    ).order_by(StaffAttendance.attendance_date.desc()).all()
    return render_template("campus/my_attendance.html", records=records, summary=staff_attendance_summary(records),
                           month=month, timefmt=college_timestamp)


@campus_bp.route("/class-teachers", methods=["GET", "POST"])
@roles_required("admin", "faculty")
def class_teachers():
    year = request.args.get("year", academic_year_for(college_today()), type=int)
    if not 2000 <= year <= 2100:
        year = academic_year_for(college_today())
    if request.method == "POST" and current_user.role != "admin":
        abort(403)
    form = ClassTeacherForm()
    curricula = Curriculum.query.join(Course).filter(Course.is_active.is_(True)).order_by(Course.code, Curriculum.pattern).all()
    members = _active_staff()
    form.curriculum_id.choices = [(row.id, f"{row.course.code} / {row.pattern}") for row in curricula]
    form.faculty_id.choices = [(row.id, f"{row.user.display_name} / {row.department}") for row in members]
    if request.method == "GET":
        form.academic_year.data = year
    response_code = 200
    if form.validate_on_submit():
        try:
            save_class_teacher(current_user, form.curriculum_id.data, form.semester.data, form.academic_year.data, form.faculty_id.data)
            db.session.commit()
            flash("Class teacher assigned. The class list and student profiles now use this assignment.", "success")
            return redirect(url_for("campus.class_teachers", year=form.academic_year.data))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            response_code = 400
        except SQLAlchemyError:
            db.session.rollback()
            flash("The assignment could not be saved. Reload this page and try again.", "danger")
            response_code = 409
    elif request.method == "POST":
        response_code = 400
    if current_user.role == "admin":
        assignments = ClassTeacherAssignment.query.filter_by(academic_year=year, is_active=True).order_by(
            ClassTeacherAssignment.course_id, ClassTeacherAssignment.semester).all()
    else:
        faculty = current_user.faculty_profile
        assignments = class_teacher_assignments(faculty.id, year) if faculty else []
    return render_template("campus/class_teachers.html", form=form, assignments=assignments, year=year,
        action_form=CampusActionForm(), timefmt=college_timestamp,
        counts={row.id: len(students_for_assignment(row)) for row in assignments}), response_code


@campus_bp.post("/class-teachers/<int:assignment_id>/remove")
@roles_required("admin")
def remove_class_teacher(assignment_id):
    form = CampusActionForm()
    if not form.validate_on_submit():
        abort(400)
    row = db.get_or_404(ClassTeacherAssignment, assignment_id)
    row.is_active = False
    row.assigned_by_id = current_user.id
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("The assignment could not be removed. Reload and try again.", "danger")
    else:
        flash("Class teacher assignment removed for this academic year.", "success")
    return redirect(url_for("campus.class_teachers", year=row.academic_year))


@campus_bp.get("/class-teachers/<int:assignment_id>/students")
@roles_required("admin", "faculty")
def class_students(assignment_id):
    assignment = db.get_or_404(ClassTeacherAssignment, assignment_id)
    if not assignment.is_active:
        abort(404)
    if current_user.role == "faculty":
        faculty = current_user.faculty_profile
        if not faculty or assignment.faculty_id != faculty.id or assignment.academic_year != academic_year_for(college_today()):
            abort(403)
    students = students_for_assignment(assignment)
    records = {student.id: student_academic_record(current_user, student, assignment.academic_year) for student in students}
    return render_template("campus/class_students.html", assignment=assignment, students=students, records=records)


@campus_bp.get("/students/<int:student_id>")
@roles_required("admin", "faculty")
def student_record(student_id):
    student = db.get_or_404(Student, student_id)
    year = request.args.get("year", academic_year_for(college_today()), type=int)
    if not 2000 <= year <= 2100:
        abort(400)
    try:
        record = student_academic_record(current_user, student, year)
    except PermissionError:
        abort(403)
    return render_template("campus/student_record.html", **record, timefmt=college_timestamp)
