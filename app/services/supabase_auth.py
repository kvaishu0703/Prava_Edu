"""Supabase Auth helpers used by Flask routes and access guards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import current_app


class SupabaseAuthError(RuntimeError):
    """Raised when Supabase Auth cannot complete a required operation."""


@dataclass(frozen=True)
class AuthenticatedSession:
    """Small, stable view of a Supabase Auth session."""

    user_id: str
    email: str
    access_token: str
    refresh_token: str


def auth_enabled() -> bool:
    """Return whether Supabase Auth should be enforced for this app."""
    return bool(current_app.config.get("SUPABASE_AUTH_ENABLED"))


def admin_auth_enabled() -> bool:
    """Return whether backend Supabase Auth admin operations can run."""
    return bool(
        current_app.config.get("SUPABASE_URL")
        and current_app.config.get("SUPABASE_SECRET_KEY")
    )


def sign_in_with_password(email: str, password: str) -> AuthenticatedSession:
    """Authenticate a user with Supabase email/password Auth."""
    client = _client()
    try:
        response = client.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )
    except Exception as exc:  # pragma: no cover - depends on Supabase client internals
        raise SupabaseAuthError("Supabase rejected these credentials.") from exc

    return _session_from_response(response)


def validate_session(access_token: str | None, refresh_token: str | None) -> AuthenticatedSession:
    """Validate and refresh a stored Supabase session."""
    if not access_token or not refresh_token:
        raise SupabaseAuthError("Missing Supabase session.")

    client = _client()
    try:
        response = client.auth.set_session(access_token, refresh_token)
        user_response = client.auth.get_user()
    except Exception as exc:  # pragma: no cover - depends on Supabase client internals
        raise SupabaseAuthError("Supabase session is no longer valid.") from exc

    auth_session = _session_from_response(response, require_email=False)
    user = getattr(user_response, "user", None)
    email = str(getattr(user, "email", "") or auth_session.email).lower()
    user_id = str(getattr(user, "id", "") or auth_session.user_id)
    if not email:
        raise SupabaseAuthError("Supabase did not return the session user.")
    return AuthenticatedSession(
        user_id=user_id,
        email=email,
        access_token=auth_session.access_token,
        refresh_token=auth_session.refresh_token,
    )


def sign_out(access_token: str | None, refresh_token: str | None) -> None:
    """Sign out the Supabase session best-effort."""
    if not access_token or not refresh_token:
        return

    client = _client()
    try:
        client.auth.set_session(access_token, refresh_token)
        client.auth.sign_out()
    except Exception:
        return


def upsert_auth_user(
    *,
    email: str,
    password: str | None,
    full_name: str,
    role: str,
    previous_email: str | None = None,
) -> None:
    """Create or update a Supabase Auth user from a local staff/student form."""
    if not auth_enabled():
        return
    if not admin_auth_enabled():
        raise SupabaseAuthError(
            "SUPABASE_SECRET_KEY is required to manage Supabase Auth users."
        )

    client = _client(admin=True)
    existing = _find_auth_user_by_email(client, previous_email or email)
    if existing is None and previous_email and previous_email.lower() != email.lower():
        existing = _find_auth_user_by_email(client, email)

    attributes: dict[str, Any] = {
        "email": email,
        "email_confirm": True,
        "user_metadata": {"full_name": full_name},
        "app_metadata": {"role": role},
    }
    if password:
        attributes["password"] = password

    try:
        if existing is None:
            if not password:
                raise SupabaseAuthError("A password is required for a new Supabase user.")
            client.auth.admin.create_user(attributes)
        else:
            client.auth.admin.update_user_by_id(str(getattr(existing, "id")), attributes)
    except SupabaseAuthError:
        raise
    except Exception as exc:  # pragma: no cover - depends on Supabase client internals
        raise SupabaseAuthError("Supabase Auth user could not be saved.") from exc


def _client(*, admin: bool = False):
    """Create a Supabase client using the configured app keys."""
    try:
        from supabase import create_client
    except ImportError as exc:
        raise SupabaseAuthError(
            "The supabase package is not installed. Run pip install -r requirements.txt."
        ) from exc

    url = current_app.config.get("SUPABASE_URL")
    key = current_app.config.get("SUPABASE_SECRET_KEY" if admin else "SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise SupabaseAuthError("Supabase URL or API key is missing.")
    return create_client(url, key)


def _session_from_response(response: Any, *, require_email: bool = True) -> AuthenticatedSession:
    """Normalize Supabase auth response shapes used by supabase-py."""
    auth_session = getattr(response, "session", None) or response
    user = getattr(response, "user", None) or getattr(auth_session, "user", None)
    access_token = str(getattr(auth_session, "access_token", "") or "")
    refresh_token = str(getattr(auth_session, "refresh_token", "") or "")
    email = str(getattr(user, "email", "") or "").lower()
    user_id = str(getattr(user, "id", "") or "")

    if not access_token or not refresh_token or (require_email and not email):
        raise SupabaseAuthError("Supabase did not return a complete session.")
    return AuthenticatedSession(
        user_id=user_id,
        email=email,
        access_token=access_token,
        refresh_token=refresh_token,
    )


def _find_auth_user_by_email(client: Any, email: str | None) -> Any | None:
    """Find a Supabase Auth user by email through the admin API."""
    if not email:
        return None
    target = email.lower()
    page = 1
    per_page = 1000

    while True:
        response = client.auth.admin.list_users(page=page, per_page=per_page)
        users = getattr(response, "users", response)
        if not users:
            return None
        for user in users:
            if str(getattr(user, "email", "") or "").lower() == target:
                return user
        if len(users) < per_page:
            return None
        page += 1
