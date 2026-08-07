"""Student module routes."""

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.decorators import roles_required
from app.extensions import db
from app.models import User
from app.services.dashboard import get_student_dashboard_data
from app.services.assignments import (
    assignment_for_student,
    split_upload_path,
    submission_by_id_for_student,
    submission_for_student,
    submit_assignment,
    uploaded_file_exists,
)
from app.services.notifications import mark_notification_read, notification_for_reader, visible_notifications_for_user
from app.services.student import (
    get_student_for_user,
    student_assignments,
    student_attendance_summary,
    student_marks_summary,
    student_materials,
    student_subjects,
)
from app.services.materials import material_file_exists, material_for_student, split_material_path
from app.student.forms import AssignmentSubmissionForm, NotificationActionForm, StudentProfileForm

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.get("/dashboard")
@roles_required("student")
def dashboard():
    """Show the protected Student dashboard."""
    return render_template("student/dashboard.html", **get_student_dashboard_data(current_user))


@student_bp.get("/profile")
@roles_required("student")
def profile():
    """Show the current student profile."""
    student = get_student_for_user(current_user)
    return render_template("student/profile.html", student=student)


@student_bp.route("/profile/edit", methods=["GET", "POST"])
@roles_required("student")
def edit_profile():
    """Allow students to update their own basic profile."""
    student = get_student_for_user(current_user)
    if student is None:
        flash("Student profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("student.dashboard"))

    form = StudentProfileForm()
    if request.method == "GET":
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
        form.mobile_number.data = student.mobile_number
        form.date_of_birth.data = student.date_of_birth
        form.gender.data = student.gender or ""
        form.address.data = student.address

    if form.validate_on_submit() and validate_profile_form(form):
        if current_app.config["SUPABASE_AUTH_ENABLED"] and form.email.data.strip().lower() != current_user.email:
            form.email.errors.append("Email changes are managed by Admin when Supabase Auth is enabled.")
            return render_template("student/profile_form.html", form=form)

        current_user.full_name = form.full_name.data.strip()
        current_user.email = form.email.data.strip().lower()
        student.mobile_number = form.mobile_number.data
        student.date_of_birth = form.date_of_birth.data
        student.gender = form.gender.data or None
        student.address = form.address.data
        try:
            db.session.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for("student.profile"))
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database error. Please try again.", "danger")

    return render_template("student/profile_form.html", form=form)


@student_bp.get("/subjects")
@roles_required("student")
def subjects():
    """Show subjects for the current student."""
    student = get_student_for_user(current_user)
    subjects_list = student_subjects(student) if student else []
    return render_template("student/subjects.html", student=student, subjects=subjects_list)


@student_bp.get("/attendance")
@roles_required("student")
def attendance():
    """Show subject-wise attendance summary."""
    student = get_student_for_user(current_user)
    rows = student_attendance_summary(student) if student else []
    return render_template("student/attendance.html", student=student, rows=rows)


@student_bp.get("/marks")
@roles_required("student")
def marks():
    """Show student marks summary."""
    student = get_student_for_user(current_user)
    marks_list = student_marks_summary(student) if student else []
    return render_template("student/marks.html", student=student, marks=marks_list)


@student_bp.get("/materials")
@roles_required("student")
def materials():
    """Show study materials available for the student."""
    student = get_student_for_user(current_user)
    search = request.args.get("q", "").strip()
    materials_list = student_materials(student, search) if student else []
    return render_template("student/materials.html", student=student, materials=materials_list, search=search)


@student_bp.get("/materials/<int:material_id>/download")
@roles_required("student")
def download_material(material_id: int):
    """Download an active material that belongs to the student's subjects."""
    student = get_student_for_user(current_user)
    material = material_for_student(student, material_id) if student else None
    if material is None:
        flash("Material not found for your subjects.", "danger")
        return redirect(url_for("student.materials"))
    if not material_file_exists(material):
        flash("Material file is missing. Please contact your faculty.", "danger")
        return redirect(url_for("student.materials"))
    directory, filename = split_material_path(material)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"] + "/" + directory,
        filename,
        as_attachment=True,
        download_name=material.file_name,
    )


@student_bp.get("/assignments")
@roles_required("student")
def assignments():
    """Show assignment status for the current student."""
    student = get_student_for_user(current_user)
    rows = student_assignments(student) if student else []
    return render_template("student/assignments.html", student=student, rows=rows)


@student_bp.route("/assignments/<int:assignment_id>/submit", methods=["GET", "POST"])
@roles_required("student")
def submit_assignment_route(assignment_id: int):
    """Submit or replace work for an assignment."""
    student = get_student_for_user(current_user)
    assignment = assignment_for_student(student, assignment_id) if student else None
    if assignment is None:
        flash("Assignment not found for your subjects.", "danger")
        return redirect(url_for("student.assignments"))

    form = AssignmentSubmissionForm()
    submission = submission_for_student(student, assignment)
    if request.method == "POST" and form.validate():
        try:
            submission = submit_assignment(student, assignment, request.files.get("file"))
            db.session.add(submission)
            db.session.commit()
            flash("Assignment submitted successfully.", "success")
            return redirect(url_for("student.assignments"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database error while submitting assignment. Please try again.", "danger")

    return render_template("student/assignment_submit_form.html", form=form, assignment=assignment, submission=submission)


@student_bp.get("/assignments/<int:assignment_id>/download")
@roles_required("student")
def download_assignment_attachment(assignment_id: int):
    """Download an assignment attachment for the student."""
    student = get_student_for_user(current_user)
    assignment = assignment_for_student(student, assignment_id) if student else None
    if assignment is None:
        flash("Assignment not found for your subjects.", "danger")
        return redirect(url_for("student.assignments"))
    if not uploaded_file_exists(assignment.attachment_path):
        flash("Assignment attachment is missing.", "danger")
        return redirect(url_for("student.assignments"))
    directory, filename = split_upload_path(assignment.attachment_path)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"] + "/" + directory, filename, as_attachment=True)


@student_bp.get("/submissions/<int:submission_id>/download")
@roles_required("student")
def download_submission(submission_id: int):
    """Download the student's own submitted file."""
    student = get_student_for_user(current_user)
    submission = submission_by_id_for_student(student, submission_id) if student else None
    if submission is None:
        flash("Submission not found.", "danger")
        return redirect(url_for("student.assignments"))
    if not uploaded_file_exists(submission.submitted_file):
        flash("Submission file is missing.", "danger")
        return redirect(url_for("student.assignments"))
    directory, filename = split_upload_path(submission.submitted_file)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"] + "/" + directory, filename, as_attachment=True)


@student_bp.get("/notifications")
@roles_required("student")
def notifications():
    """Show notifications relevant to the current student."""
    student = get_student_for_user(current_user)
    rows = visible_notifications_for_user(current_user, student)
    return render_template("student/notifications.html", rows=rows, action_form=NotificationActionForm())


@student_bp.post("/notifications/<int:notification_id>/read")
@roles_required("student")
def mark_notification_read_route(notification_id: int):
    """Mark a visible notification as read."""
    student = get_student_for_user(current_user)
    form = NotificationActionForm()
    if not form.validate_on_submit():
        flash("Invalid notification action request.", "danger")
        return redirect(url_for("student.notifications"))
    notification = notification_for_reader(current_user, notification_id, student)
    if notification is None:
        flash("Notification not found.", "danger")
        return redirect(url_for("student.notifications"))
    try:
        mark_notification_read(current_user, notification)
        db.session.commit()
        flash("Notification marked as read.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Database error while updating notification.", "danger")
    return redirect(url_for("student.notifications"))


def validate_profile_form(form: StudentProfileForm) -> bool:
    """Ensure profile email is unique across users."""
    email = form.email.data.strip().lower()
    existing = User.query.filter(User.email == email, User.id != current_user.id).first()
    if existing:
        form.email.errors.append("Email already exists.")
        return False
    return True
