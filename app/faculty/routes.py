"""Faculty module routes."""

from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.decorators import roles_required
from app.extensions import db
from app.faculty.forms import (
    AssignmentActionForm,
    AssignmentForm,
    AttendanceSelectionForm,
    FacultyProfileForm,
    FacultyNotificationForm,
    MarksSelectionForm,
    MaterialActionForm,
    MaterialUploadForm,
    NotificationActionForm,
    SubmissionGradeForm,
)
from app.models import User
from app.services.dashboard import get_faculty_dashboard_data
from app.services.attendance import (
    ATTENDANCE_STATUSES,
    attendance_map,
    faculty_subject_choices,
    get_faculty_subject,
    recent_attendance_dates,
    save_bulk_attendance,
    students_for_subject,
    subject_attendance_report,
)
from app.services.faculty import (
    assigned_students,
    assigned_subjects,
    get_faculty_for_user,
)
from app.services.marks import marks_map, save_bulk_marks, subject_marks_report, students_for_marks_subject
from app.services.materials import create_material, faculty_materials, material_file_exists, material_for_faculty, split_material_path
from app.services.assignments import (
    assignment_for_faculty,
    assignment_submission_rows,
    create_assignment,
    faculty_assignments,
    grade_submission,
    split_upload_path,
    submission_for_faculty,
    uploaded_file_exists,
)
from app.services.notifications import (
    can_deactivate_notification,
    create_faculty_notification,
    faculty_subject_notification_choices,
    mark_notification_read,
    notification_for_reader,
    notification_type_choices,
    visible_notifications_for_user,
)
from app.services.reports import csv_response, marks_report_rows

faculty_bp = Blueprint("faculty", __name__, url_prefix="/faculty")


@faculty_bp.get("/dashboard")
@roles_required("faculty")
def dashboard():
    """Show the protected Faculty dashboard."""
    return render_template("faculty/dashboard.html", **get_faculty_dashboard_data(current_user))


@faculty_bp.get("/profile")
@roles_required("faculty")
def profile():
    """Show the current faculty profile."""
    faculty = get_faculty_for_user(current_user)
    return render_template("faculty/profile.html", faculty=faculty)


@faculty_bp.route("/profile/edit", methods=["GET", "POST"])
@roles_required("faculty")
def edit_profile():
    """Allow faculty to update their own basic profile."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))

    form = FacultyProfileForm()
    if request.method == "GET":
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
        form.mobile_number.data = faculty.mobile_number
        form.qualification.data = faculty.qualification
        form.department.data = faculty.department
        form.joining_date.data = faculty.joining_date

    if form.validate_on_submit() and validate_profile_form(form):
        if current_app.config["SUPABASE_AUTH_ENABLED"] and form.email.data.strip().lower() != current_user.email:
            form.email.errors.append("Email changes are managed by Admin when Supabase Auth is enabled.")
            return render_template("faculty/profile_form.html", form=form)

        current_user.full_name = form.full_name.data.strip()
        current_user.email = form.email.data.strip().lower()
        faculty.mobile_number = form.mobile_number.data
        faculty.qualification = form.qualification.data
        faculty.department = form.department.data.strip()
        faculty.joining_date = form.joining_date.data
        try:
            db.session.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for("faculty.profile"))
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database error. Please try again.", "danger")

    return render_template("faculty/profile_form.html", form=form)


@faculty_bp.get("/subjects")
@roles_required("faculty")
def subjects():
    """Show subjects assigned to the current faculty member."""
    faculty = get_faculty_for_user(current_user)
    subjects_list = assigned_subjects(faculty) if faculty else []
    return render_template("faculty/subjects.html", faculty=faculty, subjects=subjects_list)


@faculty_bp.get("/students")
@roles_required("faculty")
def students():
    """Show students connected with the faculty member's assigned subjects."""
    faculty = get_faculty_for_user(current_user)
    search = request.args.get("q", "").strip()
    students_list = assigned_students(faculty, search) if faculty else []
    return render_template("faculty/students.html", faculty=faculty, students=students_list, search=search)


@faculty_bp.route("/attendance", methods=["GET", "POST"])
@roles_required("faculty")
def attendance():
    """Mark or edit attendance for an assigned subject and date."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))

    form = AttendanceSelectionForm()
    form.subject_id.choices = faculty_subject_choices(faculty)
    if form.attendance_date.data is None:
        form.attendance_date.data = date.today()
    if not form.subject_id.choices:
        flash("No active subjects are assigned to you yet.", "warning")
        return render_template("faculty/attendance.html", form=form, subject=None, students=[], existing={}, statuses=ATTENDANCE_STATUSES)

    if request.method == "GET":
        selected_subject = request.args.get("subject_id", type=int) or form.subject_id.choices[0][0]
        form.subject_id.data = selected_subject
        if request.args.get("attendance_date"):
            try:
                form.attendance_date.data = date.fromisoformat(request.args["attendance_date"])
            except ValueError:
                flash("Invalid attendance date. Showing today's attendance.", "warning")

    if form.validate_on_submit():
        subject = get_faculty_subject(faculty, form.subject_id.data)
        if subject is None:
            flash("Selected subject is not assigned to you.", "danger")
            return redirect(url_for("faculty.attendance"))

        students_list = students_for_subject(subject)
        rows = []
        valid_student_ids = {student.id for student in students_list}
        for student in students_list:
            status = request.form.get(f"status_{student.id}", "Absent")
            remarks = request.form.get(f"remarks_{student.id}", "").strip() or None
            if student.id in valid_student_ids:
                rows.append({"student_id": student.id, "status": status, "remarks": remarks})

        try:
            created, updated = save_bulk_attendance(faculty, subject, form.attendance_date.data, rows)
            db.session.commit()
            flash(f"Attendance saved. Created: {created}, Updated: {updated}.", "success")
            return redirect(
                url_for(
                    "faculty.attendance",
                    subject_id=subject.id,
                    attendance_date=form.attendance_date.data.isoformat(),
                )
            )
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database error while saving attendance. Please try again.", "danger")

    subject = get_faculty_subject(faculty, form.subject_id.data or form.subject_id.choices[0][0])
    students_list = students_for_subject(subject) if subject else []
    existing = attendance_map(subject.id, form.attendance_date.data) if subject and form.attendance_date.data else {}
    return render_template(
        "faculty/attendance.html",
        form=form,
        subject=subject,
        students=students_list,
        existing=existing,
        statuses=ATTENDANCE_STATUSES,
    )


@faculty_bp.get("/attendance/report")
@roles_required("faculty")
def attendance_report():
    """Show a subject-wise attendance report for faculty."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))

    choices = faculty_subject_choices(faculty)
    selected_subject_id = request.args.get("subject_id", type=int) or (choices[0][0] if choices else None)
    subject = get_faculty_subject(faculty, selected_subject_id) if selected_subject_id else None
    month_value = request.args.get("month", "").strip()
    month = None
    year = None
    if month_value:
        try:
            year, month = [int(part) for part in month_value.split("-")]
        except ValueError:
            flash("Invalid month filter. Use YYYY-MM format.", "warning")

    report_rows = subject_attendance_report(subject, month, year) if subject else []
    recent_dates = recent_attendance_dates(subject) if subject else []
    return render_template(
        "faculty/attendance_report.html",
        choices=choices,
        subject=subject,
        selected_subject_id=selected_subject_id,
        month_value=month_value,
        rows=report_rows,
        recent_dates=recent_dates,
    )


@faculty_bp.get("/attendance/report.csv")
@roles_required("faculty")
def export_attendance_report():
    """Download the filtered faculty attendance report as CSV."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))

    selected_subject_id = request.args.get("subject_id", type=int)
    subject = get_faculty_subject(faculty, selected_subject_id) if selected_subject_id else None
    if subject is None:
        flash("Select a valid assigned subject before exporting.", "danger")
        return redirect(url_for("faculty.attendance_report"))

    month_value = request.args.get("month", "").strip()
    month = None
    year = None
    if month_value:
        try:
            year, month = [int(part) for part in month_value.split("-")]
        except ValueError:
            flash("Invalid month filter. Use YYYY-MM format.", "warning")
            return redirect(url_for("faculty.attendance_report", subject_id=subject.id))

    rows = subject_attendance_report(subject, month, year)
    csv_rows = [
        [
            row["student"].enrollment_number,
            row["student"].user.full_name,
            subject.code,
            subject.name,
            row["total"],
            row["present"],
            row["absent"],
            row["late"],
            row["percentage"],
            "Below 75%" if row["low_warning"] else "OK",
        ]
        for row in rows
    ]
    return csv_response(
        f"{subject.code}-attendance-report.csv",
        ["Enrollment", "Student", "Subject Code", "Subject", "Total", "Present/Late", "Absent", "Late", "Percentage", "Warning"],
        csv_rows,
    )


@faculty_bp.route("/marks", methods=["GET", "POST"])
@roles_required("faculty")
def marks():
    """Add or update marks for an assigned subject."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))

    form = MarksSelectionForm()
    form.subject_id.choices = faculty_subject_choices(faculty)
    if not form.subject_id.choices:
        flash("No active subjects are assigned to you yet.", "warning")
        return render_template("faculty/marks.html", form=form, subject=None, students=[], existing={})

    if request.method == "GET":
        form.subject_id.data = request.args.get("subject_id", type=int) or form.subject_id.choices[0][0]
        form.exam_type.data = request.args.get("exam_type") or form.exam_type.choices[0][0]

    if form.validate_on_submit():
        subject, students_list = students_for_marks_subject(faculty, form.subject_id.data)
        if subject is None:
            flash("Selected subject is not assigned to you.", "danger")
            return redirect(url_for("faculty.marks"))

        rows = []
        for student in students_list:
            internal_raw = request.form.get(f"internal_{student.id}", "0").strip() or "0"
            external_raw = request.form.get(f"external_{student.id}", "0").strip() or "0"
            remarks = request.form.get(f"remarks_{student.id}", "").strip() or None
            try:
                rows.append(
                    {
                        "student_id": student.id,
                        "internal_marks": int(internal_raw),
                        "external_marks": int(external_raw),
                        "remarks": remarks,
                    }
                )
            except ValueError:
                flash(f"Invalid marks entered for {student.user.full_name}.", "danger")
                return redirect(url_for("faculty.marks", subject_id=subject.id, exam_type=form.exam_type.data))

        try:
            created, updated, errors = save_bulk_marks(faculty, subject, form.exam_type.data, rows)
            if errors:
                for error in errors[:3]:
                    flash(error, "danger")
                db.session.rollback()
            else:
                db.session.commit()
                flash(f"Marks saved. Created: {created}, Updated: {updated}.", "success")
            return redirect(url_for("faculty.marks", subject_id=subject.id, exam_type=form.exam_type.data))
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database error while saving marks. Please try again.", "danger")

    subject, students_list = students_for_marks_subject(faculty, form.subject_id.data or form.subject_id.choices[0][0])
    existing = marks_map(subject.id, form.exam_type.data) if subject and form.exam_type.data else {}
    return render_template("faculty/marks.html", form=form, subject=subject, students=students_list, existing=existing)


@faculty_bp.get("/marks/report")
@roles_required("faculty")
def marks_report():
    """Show marks report for an assigned subject."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))

    form = MarksSelectionForm()
    form.subject_id.choices = faculty_subject_choices(faculty)
    choices = form.subject_id.choices
    selected_subject_id = request.args.get("subject_id", type=int) or (choices[0][0] if choices else None)
    selected_exam_type = request.args.get("exam_type", "").strip()
    subject = get_faculty_subject(faculty, selected_subject_id) if selected_subject_id else None
    rows = subject_marks_report(subject, selected_exam_type or None) if subject else []
    return render_template(
        "faculty/marks_report.html",
        choices=choices,
        exam_choices=form.exam_type.choices,
        selected_subject_id=selected_subject_id,
        selected_exam_type=selected_exam_type,
        subject=subject,
        rows=rows,
    )


@faculty_bp.get("/marks/report.csv")
@roles_required("faculty")
def export_marks_report():
    """Download the filtered faculty marks report as CSV."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))

    selected_subject_id = request.args.get("subject_id", type=int)
    selected_exam_type = request.args.get("exam_type", "").strip()
    subject = get_faculty_subject(faculty, selected_subject_id) if selected_subject_id else None
    if subject is None:
        flash("Select a valid assigned subject before exporting.", "danger")
        return redirect(url_for("faculty.marks_report"))

    headers, rows = marks_report_rows(subject_marks_report(subject, selected_exam_type or None))
    return csv_response(f"{subject.code}-marks-report.csv", headers, rows)


@faculty_bp.get("/materials")
@roles_required("faculty")
def materials():
    """List study materials uploaded by the current faculty member."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))
    search = request.args.get("q", "").strip()
    materials_list = faculty_materials(faculty, search)
    return render_template("faculty/materials.html", materials=materials_list, search=search, action_form=MaterialActionForm())


@faculty_bp.route("/materials/upload", methods=["GET", "POST"])
@roles_required("faculty")
def upload_material():
    """Upload a study material for an assigned subject."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))

    form = MaterialUploadForm()
    form.subject_id.choices = faculty_subject_choices(faculty)
    if not form.subject_id.choices:
        flash("No active subjects are assigned to you yet.", "warning")
        return redirect(url_for("faculty.materials"))

    if request.method == "POST" and form.validate():
        uploaded_file = request.files.get("file")
        if not uploaded_file or not uploaded_file.filename:
            form.file.errors.append("Please select a material file.")
            return render_template("faculty/material_form.html", form=form)
        try:
            material = create_material(
                faculty,
                form.subject_id.data,
                form.title.data,
                form.description.data,
                uploaded_file,
            )
            db.session.add(material)
            db.session.commit()
            flash("Study material uploaded successfully.", "success")
            return redirect(url_for("faculty.materials"))
        except PermissionError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database error while uploading material. Please try again.", "danger")

    return render_template("faculty/material_form.html", form=form)


@faculty_bp.post("/materials/<int:material_id>/deactivate")
@roles_required("faculty")
def deactivate_material(material_id: int):
    """Deactivate a material uploaded by the current faculty member."""
    faculty = get_faculty_for_user(current_user)
    material = material_for_faculty(faculty, material_id) if faculty else None
    if material is None:
        flash("Material not found.", "danger")
        return redirect(url_for("faculty.materials"))
    form = MaterialActionForm()
    if not form.validate_on_submit():
        flash("Invalid material action request.", "danger")
        return redirect(url_for("faculty.materials"))
    material.is_active = False
    try:
        db.session.commit()
        flash("Study material deactivated successfully.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Database error while deactivating material.", "danger")
    return redirect(url_for("faculty.materials"))


@faculty_bp.get("/materials/<int:material_id>/download")
@roles_required("faculty")
def download_material(material_id: int):
    """Download a material uploaded by the current faculty member."""
    faculty = get_faculty_for_user(current_user)
    material = material_for_faculty(faculty, material_id) if faculty else None
    if material is None:
        flash("Material not found.", "danger")
        return redirect(url_for("faculty.materials"))
    if not material_file_exists(material):
        flash("Material file is missing on disk. Please upload it again.", "danger")
        return redirect(url_for("faculty.materials"))
    directory, filename = split_material_path(material)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"] + "/" + directory,
        filename,
        as_attachment=True,
        download_name=material.file_name,
    )


@faculty_bp.get("/assignments")
@roles_required("faculty")
def assignments():
    """Show assignments created by the current faculty member."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))
    search = request.args.get("q", "").strip()
    assignments_list = faculty_assignments(faculty, search)
    return render_template(
        "faculty/assignments.html",
        faculty=faculty,
        assignments=assignments_list,
        search=search,
        action_form=AssignmentActionForm(),
    )


@faculty_bp.route("/assignments/create", methods=["GET", "POST"])
@roles_required("faculty")
def create_assignment_route():
    """Create a new assignment for an assigned subject."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))

    form = AssignmentForm()
    form.subject_id.choices = faculty_subject_choices(faculty)
    if form.due_date.data is None:
        form.due_date.data = datetime.now() + timedelta(days=7)
    if not form.subject_id.choices:
        flash("No active subjects are assigned to you yet.", "warning")
        return redirect(url_for("faculty.assignments"))

    if request.method == "POST" and form.validate():
        try:
            assignment = create_assignment(
                faculty,
                form.subject_id.data,
                form.title.data,
                form.description.data,
                form.due_date.data,
                form.maximum_marks.data,
                request.files.get("attachment"),
            )
            db.session.add(assignment)
            db.session.commit()
            flash("Assignment created successfully.", "success")
            return redirect(url_for("faculty.assignments"))
        except PermissionError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database error while creating assignment. Please try again.", "danger")

    return render_template("faculty/assignment_form.html", form=form)


@faculty_bp.post("/assignments/<int:assignment_id>/deactivate")
@roles_required("faculty")
def deactivate_assignment(assignment_id: int):
    """Deactivate an assignment created by the current faculty member."""
    faculty = get_faculty_for_user(current_user)
    assignment = assignment_for_faculty(faculty, assignment_id) if faculty else None
    if assignment is None:
        flash("Assignment not found.", "danger")
        return redirect(url_for("faculty.assignments"))
    form = AssignmentActionForm()
    if not form.validate_on_submit():
        flash("Invalid assignment action request.", "danger")
        return redirect(url_for("faculty.assignments"))
    assignment.is_active = False
    try:
        db.session.commit()
        flash("Assignment deactivated successfully.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Database error while deactivating assignment.", "danger")
    return redirect(url_for("faculty.assignments"))


@faculty_bp.get("/assignments/<int:assignment_id>/download")
@roles_required("faculty")
def download_assignment_attachment(assignment_id: int):
    """Download an assignment attachment."""
    faculty = get_faculty_for_user(current_user)
    assignment = assignment_for_faculty(faculty, assignment_id) if faculty else None
    if assignment is None:
        flash("Assignment not found.", "danger")
        return redirect(url_for("faculty.assignments"))
    if not uploaded_file_exists(assignment.attachment_path):
        flash("Assignment attachment is missing.", "danger")
        return redirect(url_for("faculty.assignments"))
    directory, filename = split_upload_path(assignment.attachment_path)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"] + "/" + directory, filename, as_attachment=True)


@faculty_bp.get("/assignments/<int:assignment_id>/submissions")
@roles_required("faculty")
def assignment_submissions(assignment_id: int):
    """Show submissions for an assignment."""
    faculty = get_faculty_for_user(current_user)
    assignment = assignment_for_faculty(faculty, assignment_id) if faculty else None
    if assignment is None:
        flash("Assignment not found.", "danger")
        return redirect(url_for("faculty.assignments"))
    rows = assignment_submission_rows(assignment)
    return render_template("faculty/assignment_submissions.html", assignment=assignment, rows=rows)


@faculty_bp.get("/submissions/<int:submission_id>/download")
@roles_required("faculty")
def download_submission(submission_id: int):
    """Download a student submission file."""
    faculty = get_faculty_for_user(current_user)
    submission = submission_for_faculty(faculty, submission_id) if faculty else None
    if submission is None:
        flash("Submission not found.", "danger")
        return redirect(url_for("faculty.assignments"))
    if not uploaded_file_exists(submission.submitted_file):
        flash("Submission file is missing.", "danger")
        return redirect(url_for("faculty.assignment_submissions", assignment_id=submission.assignment_id))
    directory, filename = split_upload_path(submission.submitted_file)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"] + "/" + directory, filename, as_attachment=True)


@faculty_bp.route("/submissions/<int:submission_id>/grade", methods=["GET", "POST"])
@roles_required("faculty")
def grade_assignment_submission(submission_id: int):
    """Grade a submitted assignment."""
    faculty = get_faculty_for_user(current_user)
    submission = submission_for_faculty(faculty, submission_id) if faculty else None
    if submission is None:
        flash("Submission not found.", "danger")
        return redirect(url_for("faculty.assignments"))

    form = SubmissionGradeForm()
    if request.method == "GET":
        form.marks_obtained.data = submission.marks_obtained
        form.faculty_feedback.data = submission.faculty_feedback

    if form.validate_on_submit():
        try:
            grade_submission(submission, form.marks_obtained.data, form.faculty_feedback.data)
            db.session.commit()
            flash("Submission graded successfully.", "success")
            return redirect(url_for("faculty.assignment_submissions", assignment_id=submission.assignment_id))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database error while grading submission.", "danger")

    return render_template("faculty/submission_grade_form.html", form=form, submission=submission)


@faculty_bp.get("/notifications")
@roles_required("faculty")
def notifications():
    """Show notifications relevant to the current faculty member."""
    faculty = get_faculty_for_user(current_user)
    rows = visible_notifications_for_user(current_user, faculty)
    return render_template("faculty/notifications.html", rows=rows, action_form=NotificationActionForm())


@faculty_bp.route("/notifications/new", methods=["GET", "POST"])
@roles_required("faculty")
def new_notification():
    """Send a notification to students for one assigned subject."""
    faculty = get_faculty_for_user(current_user)
    if faculty is None:
        flash("Faculty profile is not linked yet. Please contact Admin.", "warning")
        return redirect(url_for("faculty.dashboard"))

    form = FacultyNotificationForm()
    form.notification_type.choices = notification_type_choices()
    form.subject_id.choices = faculty_subject_notification_choices(faculty)
    if not form.subject_id.choices:
        flash("No active subjects are assigned to you yet.", "warning")
        return redirect(url_for("faculty.notifications"))

    if form.validate_on_submit():
        try:
            notification = create_faculty_notification(
                faculty,
                current_user,
                form.subject_id.data,
                form.title.data,
                form.message.data,
                form.notification_type.data,
                form.expires_at.data,
            )
            db.session.add(notification)
            db.session.commit()
            flash("Notification sent successfully.", "success")
            return redirect(url_for("faculty.notifications"))
        except PermissionError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database error while sending notification.", "danger")

    return render_template("faculty/notification_form.html", form=form)


@faculty_bp.post("/notifications/<int:notification_id>/read")
@roles_required("faculty")
def mark_notification_read_route(notification_id: int):
    """Mark a visible notification as read."""
    faculty = get_faculty_for_user(current_user)
    form = NotificationActionForm()
    if not form.validate_on_submit():
        flash("Invalid notification action request.", "danger")
        return redirect(url_for("faculty.notifications"))
    notification = notification_for_reader(current_user, notification_id, faculty)
    if notification is None:
        flash("Notification not found.", "danger")
        return redirect(url_for("faculty.notifications"))
    try:
        mark_notification_read(current_user, notification)
        db.session.commit()
        flash("Notification marked as read.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Database error while updating notification.", "danger")
    return redirect(url_for("faculty.notifications"))


@faculty_bp.post("/notifications/<int:notification_id>/deactivate")
@roles_required("faculty")
def deactivate_notification(notification_id: int):
    """Deactivate a notification created by this faculty member."""
    faculty = get_faculty_for_user(current_user)
    form = NotificationActionForm()
    if not form.validate_on_submit():
        flash("Invalid notification action request.", "danger")
        return redirect(url_for("faculty.notifications"))
    notification = notification_for_reader(current_user, notification_id, faculty)
    if notification is None or not can_deactivate_notification(current_user, notification):
        flash("Notification not found.", "danger")
        return redirect(url_for("faculty.notifications"))
    notification.is_active = False
    try:
        db.session.commit()
        flash("Notification deactivated successfully.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Database error while deactivating notification.", "danger")
    return redirect(url_for("faculty.notifications"))


def validate_profile_form(form: FacultyProfileForm) -> bool:
    """Ensure profile email is unique across users."""
    email = form.email.data.strip().lower()
    existing = User.query.filter(User.email == email, User.id != current_user.id).first()
    if existing:
        form.email.errors.append("Email already exists.")
        return False
    return True
