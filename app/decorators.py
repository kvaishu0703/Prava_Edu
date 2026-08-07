"""Role and access-control decorators."""

from functools import wraps

from flask import flash, redirect, request, session, url_for
from flask_login import current_user, logout_user

from app.services.supabase_auth import SupabaseAuthError, auth_enabled, validate_session


ROLE_DASHBOARD_ENDPOINTS = {
    "admin": "admin.dashboard",
    "faculty": "faculty.dashboard",
    "student": "student.dashboard",
}


def dashboard_endpoint_for(role: str) -> str:
    """Return the dashboard endpoint for a role."""
    return ROLE_DASHBOARD_ENDPOINTS.get(role, "core.index")


def redirect_to_user_dashboard():
    """Redirect a logged-in user to their own dashboard."""
    return redirect(url_for(dashboard_endpoint_for(current_user.role)))


def roles_required(*allowed_roles: str):
    """Allow a route only for selected roles."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.url))

            if not has_valid_supabase_session():
                flash("Your session has expired. Please log in again.", "warning")
                return redirect(url_for("auth.login", next=request.url))

            if current_user.role not in allowed_roles:
                flash("You are not allowed to open that page.", "danger")
                return redirect_to_user_dashboard()

            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


def has_valid_supabase_session() -> bool:
    """Validate the Supabase session backing the Flask-Login session."""
    if not auth_enabled():
        return True

    try:
        auth_session = validate_session(
            session.get("supabase_access_token"),
            session.get("supabase_refresh_token"),
        )
    except SupabaseAuthError:
        clear_supabase_session()
        logout_user()
        return False

    if auth_session.email != current_user.email.lower():
        clear_supabase_session()
        logout_user()
        return False

    session["supabase_user_id"] = auth_session.user_id
    session["supabase_access_token"] = auth_session.access_token
    session["supabase_refresh_token"] = auth_session.refresh_token
    return True


def clear_supabase_session() -> None:
    """Remove Supabase Auth state from the Flask session."""
    session.pop("supabase_user_id", None)
    session.pop("supabase_access_token", None)
    session.pop("supabase_refresh_token", None)
