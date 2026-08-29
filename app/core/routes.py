"""Public routes and project overview pages."""

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.core.forms import ContactForm
from app.models import ContactInquiry, Course, StudentTestResponse
from app.services.homepage import course_detail_data, public_homepage_data
from app.services.student_test import TEST_QUESTIONS, grade_answers, response_result_rows, serialize_answers
from app.student.forms import StudentTestForm

core_bp = Blueprint("core", __name__)


@core_bp.route("/", methods=["GET", "POST"])
def index():
    """Render the professional public college homepage."""
    form = ContactForm()
    if form.validate_on_submit():
        inquiry = ContactInquiry(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            subject=form.subject.data.strip(),
            message=form.message.data.strip(),
        )
        try:
            db.session.add(inquiry)
            db.session.commit()
            flash("Thank you. Your message has been submitted successfully.", "success")
            return redirect(url_for("core.index", _anchor="contact"))
        except SQLAlchemyError:
            db.session.rollback()
            flash("Your message could not be saved. Please try again.", "danger")

    return render_template("core/index.html", form=form, **public_homepage_data())


@core_bp.get("/courses/<string:course_code>")
def course_detail(course_code: str):
    """Show public information for one active course."""
    course = Course.query.filter_by(code=course_code.upper(), is_active=True).first_or_404()
    return render_template("core/course_detail.html", **course_detail_data(course))


@core_bp.route("/student-test", methods=["GET", "POST"])
def student_test():
    """Show and process the public PRAVA student website test."""
    form = StudentTestForm()
    if request.method == "GET" and current_user.is_authenticated:
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
        if current_user.role == "student" and current_user.student_profile:
            student = current_user.student_profile
            form.course_year.data = f"{student.course.code} - Semester {student.semester}"

    if form.validate_on_submit():
        answers, score = grade_answers(request.form)
        response = StudentTestResponse(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            college_name=form.college_name.data.strip() if form.college_name.data else None,
            course_year=form.course_year.data.strip(),
            answers_json=serialize_answers(answers),
            score=score,
            total_questions=len(TEST_QUESTIONS),
            website_rating=form.website_rating.data,
            feedback=form.feedback.data.strip() if form.feedback.data else None,
        )
        try:
            db.session.add(response)
            db.session.commit()
            return redirect(url_for("core.student_test_confirmation", token=response.public_token))
        except SQLAlchemyError:
            db.session.rollback()
            flash("Your response could not be saved. Please try again.", "danger")

    return render_template("core/student_test_form.html", form=form, questions=TEST_QUESTIONS)


@core_bp.get("/student-test/response/<uuid:token>")
def student_test_confirmation(token):
    """Show a Google Forms-style response confirmation page."""
    response = StudentTestResponse.query.filter_by(public_token=str(token)).first_or_404()
    return render_template("core/student_test_confirmation.html", response=response)


@core_bp.get("/student-test/response/<uuid:token>/score")
def student_test_score(token):
    """Show the student's score and question-wise review."""
    response = StudentTestResponse.query.filter_by(public_token=str(token)).first_or_404()
    return render_template(
        "core/student_test_score.html",
        response=response,
        result_rows=response_result_rows(response),
    )


@core_bp.get("/phase-summary")
def phase_summary():
    """Show completed phase work in a browser-friendly page."""
    phases = [
        {
            "name": "Phase 1",
            "title": "Planning, Setup, and Initial Flask App",
            "status": "Completed",
            "tasks": [
                "Project folder structure",
                "Flask application factory",
                "Welcome page and health route",
                "Bootstrap-based starter UI",
                "README, .env.example, and learning notes",
            ],
        },
        {
            "name": "Phase 2",
            "title": "Database Models, Relationships, and Sample Data",
            "status": "Completed",
            "tasks": [
                "SQLAlchemy database extension",
                "14 database models",
                "Foreign keys and relationships",
                "Duplicate prevention constraints",
                "Seed script with Admin, Faculty, Student, BCA sample data",
                "Database design document with ER diagram",
            ],
        },
        {
            "name": "Phase 3",
            "title": "Login, Logout, and Role-Based Access",
            "status": "Completed",
            "tasks": [
                "Flask-Login session setup",
                "Login form with CSRF protection",
                "Password hash verification",
                "Inactive user login block",
                "Admin, Faculty, and Student protected dashboards",
                "Role-based access decorator and audit log entries",
            ],
        },
        {
            "name": "Phase 4",
            "title": "Common Layout and Dashboard UI",
            "status": "Completed",
            "tasks": [
                "Reusable dashboard shell with sidebar and topbar",
                "Role-specific dashboard navigation",
                "Database-backed dashboard statistics",
                "Admin recent students and notifications panels",
                "Faculty subjects and assignments panels",
                "Student subjects, materials, and notifications panels",
                "Responsive layout styling for desktop and mobile",
            ],
        },
        {
            "name": "Phase 5",
            "title": "Admin Module CRUD",
            "status": "Completed",
            "tasks": [
                "Student list, create, edit, and deactivate",
                "Faculty list, create, edit, and deactivate",
                "Course list, create, edit, and deactivate",
                "Subject list, create, edit, and deactivate",
                "Search boxes for admin master data",
                "Duplicate validation for username, email, enrollment, employee, course, and subject codes",
                "Soft delete style deactivation instead of permanent delete",
            ],
        },
        {
            "name": "Phase 6",
            "title": "Faculty Module",
            "status": "Completed",
            "tasks": [
                "Faculty profile view and edit",
                "Assigned subjects page",
                "Assigned students page with search",
                "Faculty assignments overview",
                "Faculty notifications page",
                "Faculty sidebar navigation",
                "Reusable faculty service helpers",
            ],
        },
        {
            "name": "Phase 7",
            "title": "Student Module",
            "status": "Completed",
            "tasks": [
                "Student profile view and edit",
                "My subjects page",
                "Subject-wise attendance summary",
                "Subject-wise marks summary",
                "Study materials list with search",
                "Assignment status overview",
                "Student notifications page",
                "Student sidebar navigation",
            ],
        },
        {
            "name": "Phase 8",
            "title": "Attendance Module",
            "status": "Completed",
            "tasks": [
                "Faculty subject/date attendance selection",
                "Bulk attendance marking for assigned students",
                "Present, Absent, and Late statuses",
                "Existing attendance edit on same subject/date",
                "Duplicate attendance prevention with update workflow",
                "Subject-wise attendance report",
                "Monthly filter and low-attendance warning",
                "Student attendance summary integration",
            ],
        },
        {
            "name": "Phase 9",
            "title": "Marks Module",
            "status": "Completed",
            "tasks": [
                "Faculty subject/exam marks selection",
                "Bulk marks entry for assigned students",
                "Internal, external, total marks handling",
                "Grade calculation service",
                "Maximum marks validation",
                "Duplicate-safe marks update workflow",
                "Faculty marks report",
                "Student marks summary integration",
            ],
        },
        {
            "name": "Phase 10",
            "title": "Study Materials Module",
            "status": "Completed",
            "tasks": [
                "Faculty material upload form",
                "Secure filename handling",
                "Allowed file extension validation",
                "Faculty material list, search, download, and deactivate",
                "Student material list and search",
                "Student material download workflow",
                "Missing-file friendly error handling",
                "10 MB upload size limit",
            ],
        },
        {
            "name": "Phase 11",
            "title": "Assignment and Submission Module",
            "status": "Completed",
            "tasks": [
                "Faculty assignment creation with optional attachment",
                "Secure assignment and submission file uploads",
                "Faculty assignment list, search, download, and deactivate",
                "Student assignment list and attachment download",
                "Student assignment submission and resubmission",
                "Faculty submission list and submission download",
                "Faculty grading with marks and feedback",
                "Student grade and feedback visibility",
            ],
        },
        {
            "name": "Phase 12",
            "title": "Notifications Module",
            "status": "Completed",
            "tasks": [
                "Admin notification create and deactivate workflow",
                "Admin target role, course, and semester filters",
                "Faculty subject-wise student notification workflow",
                "Faculty notification deactivate for own notices",
                "Student notification list with read/unread status",
                "Faculty notification list with read/unread status",
                "Notification read receipt tracking",
                "Expiry-aware active notification filtering",
            ],
        },
        {
            "name": "Phase 13",
            "title": "Reports and Export Module",
            "status": "Completed",
            "tasks": [
                "Admin reports dashboard",
                "Admin student and faculty CSV exports",
                "Admin attendance and marks CSV exports",
                "Admin assignment and notification CSV exports",
                "Faculty attendance report CSV export",
                "Faculty marks report CSV export",
                "Print-friendly report styling",
                "Report navigation links",
            ],
        },
        {
            "name": "Phase 14",
            "title": "Testing, Error Handling, and Security Review",
            "status": "Completed",
            "tasks": [
                "Automated authentication and authorization regression tests",
                "Global CSRF protection with POST-only logout",
                "Safe post-login redirect validation",
                "Security headers and authenticated-page cache protection",
                "Friendly 400, 403, 404, 413, and 500 error pages",
                "Database rollback after unexpected server errors",
                "Production secret and Supabase configuration validation",
                "Upload extension and grading boundary tests",
            ],
        },
        {
            "name": "Phase 15",
            "title": "Final Documentation, Viva, and Deployment",
            "status": "Completed",
            "tasks": [
                "Final project report and architecture summary",
                "Role-wise Admin, Faculty, and Student user guide",
                "Production WSGI entrypoint with Gunicorn",
                "PostgreSQL database support through Psycopg 3",
                "Render deployment blueprint and health check",
                "Secure first-Admin bootstrap command",
                "Deployment verification and troubleshooting guide",
                "Viva demonstration flow and 25 expected Q&A",
            ],
        },
        {
            "name": "Enhancement",
            "title": "Public Student Test Form",
            "status": "Completed",
            "tasks": [
                "Shareable form that works without login",
                "Student details and eight PRAVA website MCQs",
                "Server-side scoring and response storage",
                "Google Forms-style confirmation screen",
                "Question-wise score and answer review",
                "Website rating and student feedback",
                "Admin-only response list",
                "Responsive desktop and mobile layout",
            ],
        },
    ]
    return render_template("core/phase_summary.html", phases=phases)


@core_bp.get("/system-overview")
def system_overview():
    """Show what has been built in each system area."""
    systems = [
        {
            "name": "Admin System",
            "accent": "purple",
            "icon": "bi-shield-check",
            "status": "Working",
            "features": [
                "Admin dashboard with database statistics",
                "Student list, search, add, edit, deactivate",
                "Faculty list, search, add, edit, deactivate",
                "Course list, search, add, edit, deactivate",
                "Subject list, search, add, edit, deactivate",
                "Notification create, target, list, and deactivate",
                "CSV reports for student, faculty, attendance, marks, assignments, notifications",
                "Student website test scores and feedback review",
                "Duplicate validation for important fields",
            ],
        },
        {
            "name": "Faculty System",
            "accent": "orange",
            "icon": "bi-person-workspace",
            "status": "Working",
            "features": [
                "Faculty dashboard",
                "Profile view and edit",
                "Assigned subjects and assigned students",
                "Attendance marking and attendance report",
                "Marks entry and marks report",
                "Assignment create, submissions, grading, and notifications send/read",
                "Attendance and marks CSV report exports",
            ],
        },
        {
            "name": "Student System",
            "accent": "green",
            "icon": "bi-mortarboard",
            "status": "Working",
            "features": [
                "Student dashboard",
                "Profile view and edit",
                "Subjects, attendance summary, and marks summary",
                "Study materials list and search",
                "Assignment list, submit, marks, and feedback",
                "Targeted notifications with read tracking",
                "Printable student-facing report pages",
                "Public website test with instant score review",
            ],
        },
        {
            "name": "Security and Login",
            "accent": "blue",
            "icon": "bi-lock",
            "status": "Working",
            "features": [
                "Username/email login",
                "Password hashing",
                "Logout and session handling",
                "Role-based protected routes",
                "Inactive account login block",
                "CSRF protected forms",
                "POST-only logout and safe redirect validation",
                "Browser security headers and production secret checks",
            ],
        },
        {
            "name": "Database",
            "accent": "purple",
            "icon": "bi-database-check",
            "status": "Working",
            "features": [
                "SQLite database",
                "Users, students, faculty, courses, subjects",
                "Attendance, marks, materials, assignments",
                "Submissions, notifications, notification reads, activity logs",
                "Student website test responses and feedback",
                "Sample seed data",
                "Foreign keys and duplicate prevention constraints",
            ],
        },
        {
            "name": "Final Delivery",
            "accent": "green",
            "icon": "bi-check2-circle",
            "status": "Completed",
            "features": [
                "Automated test suite and security review",
                "Final report and role-wise user guide",
                "Production deployment configuration",
                "Viva questions and demonstration flow",
                "Public Student Test Form with Admin response review",
            ],
        },
    ]
    return render_template("core/system_overview.html", systems=systems)


@core_bp.get("/health")
def health():
    """Simple route used to confirm the app is running."""
    return {
        "app": current_app.config["PROJECT_NAME"],
        "phase": "Phase 15",
        "status": "ok",
    }
