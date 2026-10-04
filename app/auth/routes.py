"""Login and logout routes."""

from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import (
    abort,
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_user, logout_user
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from app.auth.forms import LoginForm, LogoutForm
from app.decorators import clear_supabase_session, dashboard_endpoint_for
from app.extensions import db
from app.models import ActivityLog, User
from app.services.college import department_for_course, DEPARTMENTS
from app.services.supabase_auth import (
    SupabaseAuthError,
    sign_in_with_password,
    sign_out as supabase_sign_out,
)

auth_bp = Blueprint("auth", __name__)

PORTALS = {
    "student": {
        "role": "student", "name": "Student", "icon": "bi-mortarboard",
        "tagline": "Student Academic Records",
        "description": "View your attendance, marks, subjects and assignments.",
        "features": ["Marks & attendance", "Subjects & study materials", "Assignments & student tests"],
    },
    "staff": {
        "role": "faculty", "name": "Staff", "icon": "bi-person-workspace",
        "tagline": "Staff Academic Workspace",
        "description": "Manage assigned subjects, attendance, marks and learning resources.",
        "features": ["Class attendance & marks", "Materials & assignments", "Student records & reports"],
    },
    "administration": {
        "role": "admin", "name": "Office / Administration", "icon": "bi-buildings",
        "tagline": "College Administration",
        "description": "Manage student records, staff accounts, registrations and college reports.",
        "features": ["Student & staff management", "Courses & subject allocation", "Reports, notices & inquiries"],
    },
}


@auth_bp.get("/login")
def portal():
    next_page = request.args.get("next")
    return render_template("auth/portal.html", portals=PORTALS,
                           next_page=next_page if is_safe_next_url(next_page) else None)


@auth_bp.route("/login/<string:role_slug>", methods=["GET", "POST"])
def role_login(role_slug):
    if role_slug not in PORTALS:
        abort(404)
    if role_slug == "student" and request.method == "GET":
        next_page = request.args.get("next")
        return render_template("auth/student_programmes.html", next_page=next_page if is_safe_next_url(next_page) else None)
    return login(role_slug)


@auth_bp.route("/login/student/<string:department>", methods=["GET", "POST"])
def student_login(department):
    if department not in DEPARTMENTS:
        abort(404)
    return login("student", department)


@auth_bp.route("/auth/login", methods=["GET", "POST"])
def login(role_slug=None, department=None):
    """Log in a user with username/email and password."""
    if role_slug is None and request.method == "GET":
        next_page = request.args.get("next")
        return redirect(url_for("auth.portal", next=next_page if is_safe_next_url(next_page) else None))
    form = LoginForm()
    selected_portal = PORTALS.get(role_slug)
    if department:
        selected_portal = {**PORTALS["student"], "name": DEPARTMENTS[department]["name"] + " Student"}

    def login_page():
        return render_template("auth/login.html", form=form, portal=selected_portal,
                               role_slug=role_slug, department=department)

    if form.validate_on_submit():
        login_id = form.username_or_email.data.strip().lower()
        user = User.query.filter(
            or_(User.username == login_id, User.email == login_id)
        ).first()

        if (not user or (selected_portal and user.role != selected_portal["role"])
                or (department and (not user.student_profile or department_for_course(user.student_profile.course) != department))):
            flash("Invalid username/email or password.", "danger")
            log_activity(None, "login_failed", "auth", f"Failed login for {login_id}")
            commit_auth_activity()
            return login_page()

        if user.is_demo and (not current_app.config.get('DEMO_MODE') or current_app.config.get('IS_PRODUCTION')):
            flash('Demo accounts are available only in local demo mode.', 'warning')
            return login_page()

        if not user.is_active:
            flash("This account is inactive. Please contact Admin.", "danger")
            log_activity(user, "login_blocked", "auth", "Inactive account tried to login")
            commit_auth_activity()
            return login_page()

        auth_session = None
        if current_app.config["SUPABASE_AUTH_ENABLED"]:
            try:
                auth_session = sign_in_with_password(user.email, form.password.data)
            except SupabaseAuthError:
                flash("Invalid username/email or password.", "danger")
                log_activity(None, "login_failed", "auth", f"Failed Supabase login for {login_id}")
                commit_auth_activity()
                return login_page()

            if auth_session.email != user.email.lower():
                flash("Invalid username/email or password.", "danger")
                log_activity(None, "login_failed", "auth", f"Mismatched Supabase login for {login_id}")
                commit_auth_activity()
                return login_page()

        elif not user.check_password(form.password.data):
            flash("Invalid username/email or password.", "danger")
            log_activity(None, "login_failed", "auth", f"Failed login for {login_id}")
            commit_auth_activity()
            return login_page()

        # A selected portal must authenticate its entered identity, even when another
        # account is open. Failed attempts leave that existing session untouched.
        if current_user.is_authenticated:
            log_activity(current_user, 'account_switch', 'auth', 'Switched to another verified account')
        if current_app.config['SUPABASE_AUTH_ENABLED'] and session.get('supabase_access_token'):
            supabase_sign_out(session.get('supabase_access_token'), session.get('supabase_refresh_token'))
        logout_user()
        clear_supabase_session()
        if auth_session:
            session['supabase_user_id'] = auth_session.user_id
            session['supabase_access_token'] = auth_session.access_token
            session['supabase_refresh_token'] = auth_session.refresh_token
        login_user(user, remember=form.remember_me.data)
        user.last_login = datetime.now(timezone.utc)
        log_activity(user, "login_success", "auth", "User logged in successfully")
        commit_auth_activity()

        next_page = request.args.get("next")
        if is_safe_next_url(next_page) and next_matches_role(next_page, user.role):
            return redirect(next_page)
        return redirect(url_for(dashboard_endpoint_for(user.role)))

    return login_page()


@auth_bp.post("/auth/logout")
def logout():
    """Log out the current user through a CSRF-protected POST request."""
    form = LogoutForm()
    if not form.validate_on_submit():
        return render_template("errors/400.html"), 400

    if current_user.is_authenticated:
        log_activity(current_user, "logout", "auth", "User logged out")
        commit_auth_activity()
    if current_app.config["SUPABASE_AUTH_ENABLED"]:
        supabase_sign_out(
            session.get("supabase_access_token"),
            session.get("supabase_refresh_token"),
        )
    clear_supabase_session()
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("core.index"))


def next_matches_role(target, role):
    path = urlsplit(target).path
    for prefix, required_role in [('/admin/', 'admin'), ('/faculty/', 'faculty'), ('/student/', 'student')]:
        if path.startswith(prefix):
            return required_role == role
    return not path.startswith(('/auth/logout', '/login', '/signup'))


def is_safe_next_url(target: str | None) -> bool:
    """Allow only local absolute paths as post-login redirect targets."""
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return False
    parts = urlsplit(target)
    return not parts.scheme and not parts.netloc


def log_activity(user, action: str, module: str, description: str) -> None:
    """Store a small audit log entry without exposing sensitive data."""
    db.session.add(
        ActivityLog(
            user_id=user.id if user else None,
            action=action,
            module=module,
            description=description,
            ip_address=request.remote_addr,
        )
    )


def commit_auth_activity() -> None:
    """Persist optional auth audit data without blocking login/logout."""
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
