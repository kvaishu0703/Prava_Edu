"""Login and logout routes."""

from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import (
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
from app.services.supabase_auth import (
    SupabaseAuthError,
    sign_in_with_password,
    sign_out as supabase_sign_out,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Log in a user with username/email and password."""
    if current_user.is_authenticated:
        return redirect(url_for(dashboard_endpoint_for(current_user.role)))

    form = LoginForm()
    if form.validate_on_submit():
        login_id = form.username_or_email.data.strip().lower()
        user = User.query.filter(
            or_(User.username == login_id, User.email == login_id)
        ).first()

        if not user:
            flash("Invalid username/email or password.", "danger")
            log_activity(None, "login_failed", "auth", f"Failed login for {login_id}")
            commit_auth_activity()
            return render_template("auth/login.html", form=form)

        if not user.is_active:
            flash("This account is inactive. Please contact Admin.", "danger")
            log_activity(user, "login_blocked", "auth", "Inactive account tried to login")
            commit_auth_activity()
            return render_template("auth/login.html", form=form)

        if current_app.config["SUPABASE_AUTH_ENABLED"]:
            try:
                auth_session = sign_in_with_password(user.email, form.password.data)
            except SupabaseAuthError:
                flash("Invalid username/email or password.", "danger")
                log_activity(None, "login_failed", "auth", f"Failed Supabase login for {login_id}")
                commit_auth_activity()
                return render_template("auth/login.html", form=form)

            if auth_session.email != user.email.lower():
                flash("Invalid username/email or password.", "danger")
                log_activity(None, "login_failed", "auth", f"Mismatched Supabase login for {login_id}")
                commit_auth_activity()
                return render_template("auth/login.html", form=form)

            session["supabase_user_id"] = auth_session.user_id
            session["supabase_access_token"] = auth_session.access_token
            session["supabase_refresh_token"] = auth_session.refresh_token
        elif not user.check_password(form.password.data):
            flash("Invalid username/email or password.", "danger")
            log_activity(None, "login_failed", "auth", f"Failed login for {login_id}")
            commit_auth_activity()
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        user.last_login = datetime.now(timezone.utc)
        log_activity(user, "login_success", "auth", "User logged in successfully")
        commit_auth_activity()

        next_page = request.args.get("next")
        if is_safe_next_url(next_page):
            return redirect(next_page)
        return redirect(url_for(dashboard_endpoint_for(user.role)))

    return render_template("auth/login.html", form=form)


@auth_bp.post("/logout")
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
    return redirect(url_for("auth.login"))


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
