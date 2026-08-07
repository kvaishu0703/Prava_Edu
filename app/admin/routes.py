"""Admin dashboard and CRUD routes."""

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin.forms import CourseForm, EmptyForm, FacultyForm, NotificationForm, StudentForm, SubjectForm
from app.decorators import roles_required
from app.extensions import db
from app.models import Course, Faculty, Notification, Student, Subject, User
from app.services.dashboard import get_admin_dashboard_data
from app.services.notifications import (
    admin_notifications,
    course_filter_choices,
    create_admin_notification,
    notification_type_choices,
    target_role_choices,
)
from app.services.reports import (
    admin_attendance_records,
    admin_marks_records,
    admin_report_cards,
    assignment_report_rows,
    attendance_report_rows,
    csv_response,
    faculty_report_rows,
    marks_report_rows,
    notification_report_rows,
    student_report_rows,
)
from app.services.supabase_auth import SupabaseAuthError, upsert_auth_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/dashboard")
@roles_required("admin")
def dashboard():
    """Show the protected Admin dashboard."""
    return render_template("admin/dashboard.html", **get_admin_dashboard_data())


@admin_bp.get("/students")
@roles_required("admin")
def students():
    """List students with simple search."""
    search = request.args.get("q", "").strip()
    query = Student.query.join(Student.user).join(Student.course)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                User.full_name.ilike(like),
                User.email.ilike(like),
                Student.enrollment_number.ilike(like),
                Course.code.ilike(like),
            )
        )
    students_list = query.order_by(Student.created_at.desc()).all()
    return render_template("admin/students.html", students=students_list, search=search, action_form=EmptyForm())


@admin_bp.route("/students/new", methods=["GET", "POST"])
@roles_required("admin")
def new_student():
    """Create a student login account and profile."""
    form = StudentForm()
    populate_student_form_choices(form)
    if form.validate_on_submit() and validate_student_form(form):
        user = User(
            full_name=form.full_name.data.strip(),
            username=form.username.data.strip().lower(),
            email=form.email.data.strip().lower(),
            role="student",
            is_active=form.is_active.data,
        )
        user.set_password(form.password.data or "Student@123")
        if not save_supabase_auth_account(form, "student"):
            return render_template("admin/student_form.html", form=form, mode="Create")
        student = Student(
            user=user,
            enrollment_number=form.enrollment_number.data.strip().upper(),
            mobile_number=form.mobile_number.data,
            date_of_birth=form.date_of_birth.data,
            gender=form.gender.data or None,
            address=form.address.data,
            course_id=form.course_id.data,
            semester=form.semester.data,
            admission_year=form.admission_year.data,
        )
        return save_and_redirect([user, student], "Student created successfully.", "admin.students")
    return render_template("admin/student_form.html", form=form, mode="Create")


@admin_bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@roles_required("admin")
def edit_student(student_id: int):
    """Edit a student login account and profile."""
    student = Student.query.get_or_404(student_id)
    form = StudentForm(obj=student)
    populate_student_form_choices(form)

    if request.method == "GET":
        fill_student_form(form, student)

    if form.validate_on_submit() and validate_student_form(form, student):
        previous_email = student.user.email
        if not save_supabase_auth_account(form, "student", previous_email):
            return render_template("admin/student_form.html", form=form, mode="Edit", student=student)
        student.user.full_name = form.full_name.data.strip()
        student.user.username = form.username.data.strip().lower()
        student.user.email = form.email.data.strip().lower()
        student.user.is_active = form.is_active.data
        if form.password.data:
            student.user.set_password(form.password.data)
        student.enrollment_number = form.enrollment_number.data.strip().upper()
        student.mobile_number = form.mobile_number.data
        student.date_of_birth = form.date_of_birth.data
        student.gender = form.gender.data or None
        student.address = form.address.data
        student.course_id = form.course_id.data
        student.semester = form.semester.data
        student.admission_year = form.admission_year.data
        return save_and_redirect([], "Student updated successfully.", "admin.students")

    return render_template("admin/student_form.html", form=form, mode="Edit", student=student)


@admin_bp.post("/students/<int:student_id>/deactivate")
@roles_required("admin")
def deactivate_student(student_id: int):
    """Deactivate a student account instead of deleting records."""
    form = EmptyForm()
    if form.validate_on_submit():
        student = Student.query.get_or_404(student_id)
        student.user.is_active = False
        return save_and_redirect([], "Student deactivated successfully.", "admin.students")
    flash("Invalid request. Please try again.", "danger")
    return redirect(url_for("admin.students"))


@admin_bp.get("/faculty")
@roles_required("admin")
def faculty():
    """List faculty members with simple search."""
    search = request.args.get("q", "").strip()
    query = Faculty.query.join(Faculty.user)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                User.full_name.ilike(like),
                User.email.ilike(like),
                Faculty.employee_id.ilike(like),
                Faculty.department.ilike(like),
            )
        )
    faculty_list = query.order_by(Faculty.created_at.desc()).all()
    return render_template("admin/faculty.html", faculty_members=faculty_list, search=search, action_form=EmptyForm())


@admin_bp.route("/faculty/new", methods=["GET", "POST"])
@roles_required("admin")
def new_faculty():
    """Create a faculty login account and profile."""
    form = FacultyForm()
    if form.validate_on_submit() and validate_faculty_form(form):
        user = User(
            full_name=form.full_name.data.strip(),
            username=form.username.data.strip().lower(),
            email=form.email.data.strip().lower(),
            role="faculty",
            is_active=form.is_active.data,
        )
        user.set_password(form.password.data or "Faculty@123")
        if not save_supabase_auth_account(form, "faculty"):
            return render_template("admin/faculty_form.html", form=form, mode="Create")
        faculty_member = Faculty(
            user=user,
            employee_id=form.employee_id.data.strip().upper(),
            mobile_number=form.mobile_number.data,
            qualification=form.qualification.data,
            department=form.department.data.strip(),
            joining_date=form.joining_date.data,
        )
        return save_and_redirect([user, faculty_member], "Faculty created successfully.", "admin.faculty")
    return render_template("admin/faculty_form.html", form=form, mode="Create")


@admin_bp.route("/faculty/<int:faculty_id>/edit", methods=["GET", "POST"])
@roles_required("admin")
def edit_faculty(faculty_id: int):
    """Edit a faculty login account and profile."""
    faculty_member = Faculty.query.get_or_404(faculty_id)
    form = FacultyForm(obj=faculty_member)

    if request.method == "GET":
        fill_faculty_form(form, faculty_member)

    if form.validate_on_submit() and validate_faculty_form(form, faculty_member):
        previous_email = faculty_member.user.email
        if not save_supabase_auth_account(form, "faculty", previous_email):
            return render_template("admin/faculty_form.html", form=form, mode="Edit", faculty_member=faculty_member)
        faculty_member.user.full_name = form.full_name.data.strip()
        faculty_member.user.username = form.username.data.strip().lower()
        faculty_member.user.email = form.email.data.strip().lower()
        faculty_member.user.is_active = form.is_active.data
        if form.password.data:
            faculty_member.user.set_password(form.password.data)
        faculty_member.employee_id = form.employee_id.data.strip().upper()
        faculty_member.mobile_number = form.mobile_number.data
        faculty_member.qualification = form.qualification.data
        faculty_member.department = form.department.data.strip()
        faculty_member.joining_date = form.joining_date.data
        return save_and_redirect([], "Faculty updated successfully.", "admin.faculty")

    return render_template("admin/faculty_form.html", form=form, mode="Edit", faculty_member=faculty_member)


@admin_bp.post("/faculty/<int:faculty_id>/deactivate")
@roles_required("admin")
def deactivate_faculty(faculty_id: int):
    """Deactivate a faculty account instead of deleting records."""
    form = EmptyForm()
    if form.validate_on_submit():
        faculty_member = Faculty.query.get_or_404(faculty_id)
        faculty_member.user.is_active = False
        return save_and_redirect([], "Faculty deactivated successfully.", "admin.faculty")
    flash("Invalid request. Please try again.", "danger")
    return redirect(url_for("admin.faculty"))


@admin_bp.get("/courses")
@roles_required("admin")
def courses():
    """List courses with simple search."""
    search = request.args.get("q", "").strip()
    query = Course.query
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Course.name.ilike(like), Course.code.ilike(like)))
    course_list = query.order_by(Course.name).all()
    return render_template("admin/courses.html", courses=course_list, search=search, action_form=EmptyForm())


@admin_bp.route("/courses/new", methods=["GET", "POST"])
@roles_required("admin")
def new_course():
    """Create a course."""
    form = CourseForm()
    if form.validate_on_submit() and validate_course_form(form):
        course = Course(
            name=form.name.data.strip(),
            code=form.code.data.strip().upper(),
            duration=form.duration.data.strip(),
            total_semesters=form.total_semesters.data,
            is_active=form.is_active.data,
        )
        return save_and_redirect([course], "Course created successfully.", "admin.courses")
    return render_template("admin/course_form.html", form=form, mode="Create")


@admin_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@roles_required("admin")
def edit_course(course_id: int):
    """Edit a course."""
    course = Course.query.get_or_404(course_id)
    form = CourseForm(obj=course)
    if form.validate_on_submit() and validate_course_form(form, course):
        course.name = form.name.data.strip()
        course.code = form.code.data.strip().upper()
        course.duration = form.duration.data.strip()
        course.total_semesters = form.total_semesters.data
        course.is_active = form.is_active.data
        return save_and_redirect([], "Course updated successfully.", "admin.courses")
    return render_template("admin/course_form.html", form=form, mode="Edit", course=course)


@admin_bp.post("/courses/<int:course_id>/deactivate")
@roles_required("admin")
def deactivate_course(course_id: int):
    """Deactivate a course."""
    form = EmptyForm()
    if form.validate_on_submit():
        course = Course.query.get_or_404(course_id)
        course.is_active = False
        return save_and_redirect([], "Course deactivated successfully.", "admin.courses")
    flash("Invalid request. Please try again.", "danger")
    return redirect(url_for("admin.courses"))


@admin_bp.get("/subjects")
@roles_required("admin")
def subjects():
    """List subjects with simple search."""
    search = request.args.get("q", "").strip()
    query = Subject.query.join(Subject.course).outerjoin(Subject.faculty).outerjoin(Faculty.user)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Subject.name.ilike(like),
                Subject.code.ilike(like),
                Course.code.ilike(like),
                User.full_name.ilike(like),
            )
        )
    subject_list = query.order_by(Subject.semester, Subject.name).all()
    return render_template("admin/subjects.html", subjects=subject_list, search=search, action_form=EmptyForm())


@admin_bp.get("/notifications")
@roles_required("admin")
def notifications():
    """Manage notifications sent across the system."""
    search = request.args.get("q", "").strip()
    notifications_list = admin_notifications(search)
    return render_template(
        "admin/notifications.html",
        notifications=notifications_list,
        search=search,
        action_form=EmptyForm(),
    )


@admin_bp.get("/reports")
@roles_required("admin")
def reports():
    """Show Admin CSV reports dashboard."""
    return render_template("admin/reports.html", report_cards=admin_report_cards())


@admin_bp.get("/reports/export/<report_type>")
@roles_required("admin")
def export_report(report_type: str):
    """Download an Admin report as CSV."""
    builders = {
        "students": ("students-report.csv", student_report_rows),
        "faculty": ("faculty-report.csv", faculty_report_rows),
        "assignments": ("assignments-report.csv", assignment_report_rows),
        "notifications": ("notifications-report.csv", notification_report_rows),
    }
    if report_type == "attendance":
        headers, rows = attendance_report_rows(admin_attendance_records())
        return csv_response("attendance-report.csv", headers, rows)
    if report_type == "marks":
        headers, rows = marks_report_rows(admin_marks_records())
        return csv_response("marks-report.csv", headers, rows)
    if report_type not in builders:
        flash("Report not found.", "danger")
        return redirect(url_for("admin.reports"))
    filename, builder = builders[report_type]
    headers, rows = builder()
    return csv_response(filename, headers, rows)


@admin_bp.route("/notifications/new", methods=["GET", "POST"])
@roles_required("admin")
def new_notification():
    """Create a system notification."""
    form = NotificationForm()
    populate_notification_form_choices(form)
    if form.validate_on_submit():
        notification = create_admin_notification(
            current_user,
            form.title.data,
            form.message.data,
            form.notification_type.data,
            form.target_role.data,
            form.target_course_id.data,
            form.target_semester.data,
            form.expires_at.data,
        )
        return save_and_redirect([notification], "Notification sent successfully.", "admin.notifications")
    return render_template("admin/notification_form.html", form=form)


@admin_bp.post("/notifications/<int:notification_id>/deactivate")
@roles_required("admin")
def deactivate_notification(notification_id: int):
    """Deactivate a notification."""
    form = EmptyForm()
    if form.validate_on_submit():
        notification = Notification.query.get_or_404(notification_id)
        notification.is_active = False
        return save_and_redirect([], "Notification deactivated successfully.", "admin.notifications")
    flash("Invalid request. Please try again.", "danger")
    return redirect(url_for("admin.notifications"))


@admin_bp.route("/subjects/new", methods=["GET", "POST"])
@roles_required("admin")
def new_subject():
    """Create a subject."""
    form = SubjectForm()
    populate_subject_form_choices(form)
    if form.validate_on_submit() and validate_subject_form(form):
        subject = Subject(
            name=form.name.data.strip(),
            code=form.code.data.strip().upper(),
            course_id=form.course_id.data,
            semester=form.semester.data,
            faculty_id=form.faculty_id.data or None,
            maximum_marks=form.maximum_marks.data,
            passing_marks=form.passing_marks.data,
            is_active=form.is_active.data,
        )
        return save_and_redirect([subject], "Subject created successfully.", "admin.subjects")
    return render_template("admin/subject_form.html", form=form, mode="Create")


@admin_bp.route("/subjects/<int:subject_id>/edit", methods=["GET", "POST"])
@roles_required("admin")
def edit_subject(subject_id: int):
    """Edit a subject."""
    subject = Subject.query.get_or_404(subject_id)
    form = SubjectForm(obj=subject)
    populate_subject_form_choices(form)
    if request.method == "GET":
        form.faculty_id.data = subject.faculty_id or 0
    if form.validate_on_submit() and validate_subject_form(form, subject):
        subject.name = form.name.data.strip()
        subject.code = form.code.data.strip().upper()
        subject.course_id = form.course_id.data
        subject.semester = form.semester.data
        subject.faculty_id = form.faculty_id.data or None
        subject.maximum_marks = form.maximum_marks.data
        subject.passing_marks = form.passing_marks.data
        subject.is_active = form.is_active.data
        return save_and_redirect([], "Subject updated successfully.", "admin.subjects")
    return render_template("admin/subject_form.html", form=form, mode="Edit", subject=subject)


@admin_bp.post("/subjects/<int:subject_id>/deactivate")
@roles_required("admin")
def deactivate_subject(subject_id: int):
    """Deactivate a subject."""
    form = EmptyForm()
    if form.validate_on_submit():
        subject = Subject.query.get_or_404(subject_id)
        subject.is_active = False
        return save_and_redirect([], "Subject deactivated successfully.", "admin.subjects")
    flash("Invalid request. Please try again.", "danger")
    return redirect(url_for("admin.subjects"))


def populate_student_form_choices(form: StudentForm) -> None:
    """Load course choices into a student form."""
    form.course_id.choices = [(course.id, f"{course.code} - {course.name}") for course in Course.query.filter_by(is_active=True).order_by(Course.name)]


def populate_subject_form_choices(form: SubjectForm) -> None:
    """Load course and faculty choices into a subject form."""
    form.course_id.choices = [(course.id, f"{course.code} - {course.name}") for course in Course.query.filter_by(is_active=True).order_by(Course.name)]
    form.faculty_id.choices = [(0, "Not assigned")] + [
        (faculty.id, f"{faculty.employee_id} - {faculty.user.full_name}")
        for faculty in Faculty.query.join(Faculty.user).filter(User.is_active.is_(True)).order_by(User.full_name)
    ]


def populate_notification_form_choices(form: NotificationForm) -> None:
    """Load choices into the Admin notification form."""
    form.notification_type.choices = notification_type_choices()
    form.target_role.choices = target_role_choices()
    form.target_course_id.choices = course_filter_choices()


def fill_student_form(form: StudentForm, student: Student) -> None:
    """Copy student and linked user values into the edit form."""
    form.full_name.data = student.user.full_name
    form.username.data = student.user.username
    form.email.data = student.user.email
    form.enrollment_number.data = student.enrollment_number
    form.mobile_number.data = student.mobile_number
    form.date_of_birth.data = student.date_of_birth
    form.gender.data = student.gender or ""
    form.address.data = student.address
    form.course_id.data = student.course_id
    form.semester.data = student.semester
    form.admission_year.data = student.admission_year
    form.is_active.data = student.user.is_active


def fill_faculty_form(form: FacultyForm, faculty_member: Faculty) -> None:
    """Copy faculty and linked user values into the edit form."""
    form.full_name.data = faculty_member.user.full_name
    form.username.data = faculty_member.user.username
    form.email.data = faculty_member.user.email
    form.employee_id.data = faculty_member.employee_id
    form.mobile_number.data = faculty_member.mobile_number
    form.qualification.data = faculty_member.qualification
    form.department.data = faculty_member.department
    form.joining_date.data = faculty_member.joining_date
    form.is_active.data = faculty_member.user.is_active


def validate_user_unique(form, existing_user: User | None = None) -> bool:
    """Check duplicate username and email before saving."""
    is_valid = True
    username = form.username.data.strip().lower()
    email = form.email.data.strip().lower()
    user_id = existing_user.id if existing_user else None

    username_exists = User.query.filter(User.username == username, User.id != user_id).first()
    email_exists = User.query.filter(User.email == email, User.id != user_id).first()
    if username_exists:
        form.username.errors.append("Username already exists.")
        is_valid = False
    if email_exists:
        form.email.errors.append("Email already exists.")
        is_valid = False
    return is_valid


def save_supabase_auth_account(form, role: str, previous_email: str | None = None) -> bool:
    """Provision or update the matching Supabase Auth account."""
    try:
        upsert_auth_user(
            email=form.email.data.strip().lower(),
            password=form.password.data or None,
            full_name=form.full_name.data.strip(),
            role=role,
            previous_email=previous_email,
        )
    except SupabaseAuthError as exc:
        form.email.errors.append(str(exc))
        return False
    return True


def validate_student_form(form: StudentForm, student: Student | None = None) -> bool:
    """Check student-specific duplicate records."""
    existing_user = student.user if student else None
    is_valid = validate_user_unique(form, existing_user)
    student_id = student.id if student else None
    enrollment = form.enrollment_number.data.strip().upper()
    enrollment_exists = Student.query.filter(Student.enrollment_number == enrollment, Student.id != student_id).first()
    if enrollment_exists:
        form.enrollment_number.errors.append("Enrollment number already exists.")
        is_valid = False
    if not student and not form.password.data:
        form.password.errors.append("Password is required for a new student.")
        is_valid = False
    return is_valid


def validate_faculty_form(form: FacultyForm, faculty_member: Faculty | None = None) -> bool:
    """Check faculty-specific duplicate records."""
    existing_user = faculty_member.user if faculty_member else None
    is_valid = validate_user_unique(form, existing_user)
    faculty_id = faculty_member.id if faculty_member else None
    employee_id = form.employee_id.data.strip().upper()
    employee_exists = Faculty.query.filter(Faculty.employee_id == employee_id, Faculty.id != faculty_id).first()
    if employee_exists:
        form.employee_id.errors.append("Employee ID already exists.")
        is_valid = False
    if not faculty_member and not form.password.data:
        form.password.errors.append("Password is required for a new faculty member.")
        is_valid = False
    return is_valid


def validate_course_form(form: CourseForm, course: Course | None = None) -> bool:
    """Check duplicate course code."""
    course_id = course.id if course else None
    code = form.code.data.strip().upper()
    code_exists = Course.query.filter(Course.code == code, Course.id != course_id).first()
    if code_exists:
        form.code.errors.append("Course code already exists.")
        return False
    return True


def validate_subject_form(form: SubjectForm, subject: Subject | None = None) -> bool:
    """Check subject marks and duplicate subject code for a course semester."""
    is_valid = True
    subject_id = subject.id if subject else None
    if form.passing_marks.data > form.maximum_marks.data:
        form.passing_marks.errors.append("Passing marks cannot be greater than maximum marks.")
        is_valid = False

    code = form.code.data.strip().upper()
    duplicate = Subject.query.filter(
        Subject.code == code,
        Subject.course_id == form.course_id.data,
        Subject.semester == form.semester.data,
        Subject.id != subject_id,
    ).first()
    if duplicate:
        form.code.errors.append("Subject code already exists for this course and semester.")
        is_valid = False
    return is_valid


def save_and_redirect(objects: list, success_message: str, endpoint: str):
    """Save database changes with rollback on error."""
    try:
        for obj in objects:
            db.session.add(obj)
        db.session.commit()
        flash(success_message, "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Database error. Please check the form and try again.", "danger")
    return redirect(url_for(endpoint))
