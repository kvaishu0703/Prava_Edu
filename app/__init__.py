"""Application factory for PRAVA."""

import os

import click

from flask import Flask, current_app, render_template, request
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

from app.extensions import csrf, db, login_manager
from config import get_config


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(get_config(config_name))
    validate_runtime_config(app)
    if app.config.get("IS_PRODUCTION"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from app.auth.routes import auth_bp
    from app.core.routes import core_bp
    from app.admin.routes import admin_bp
    from app.faculty.routes import faculty_bp
    from app.student.routes import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(core_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(student_bp)
    from app.academics.routes import academics_bp
    from app.activities.routes import activities_bp
    from app.services.college import register_college_context
    app.register_blueprint(academics_bp)
    app.register_blueprint(activities_bp)
    from app.office.routes import office_bp
    app.register_blueprint(office_bp)
    register_college_context(app)
    from app.registration.routes import registration_bp
    from app.services.navigation import register_navigation
    app.register_blueprint(registration_bp)
    register_navigation(app)
    register_commands(app)
    register_error_handlers(app)
    register_security_headers(app)

    return app


def register_commands(app: Flask) -> None:
    """Register database helper commands for development."""

    @app.cli.command('setup-demo')
    def setup_demo_command():
        from app.services.demo import setup_demo
        try:
            setup_demo()
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        click.echo('Four local demo accounts are ready. See README.md for credentials.')

    @app.cli.command('sync-college')
    def sync_college_command():
        from app.services.college_setup import sync_college
        sync_college()
        click.echo('College programmes and 2024 NEP source references are configured.')

    @app.cli.command("init-db")
    def init_db_command():
        from app import models  # noqa: F401

        db.create_all()
        print("Database tables created successfully.")

    @app.cli.command("upgrade-db")
    def upgrade_db_command():
        """Create new tables and apply small backward-compatible schema upgrades."""
        from app import models  # noqa: F401

        db.create_all()
        inspector = inspect(db.engine)
        course_columns = {column["name"] for column in inspector.get_columns("courses")}
        if "description" not in course_columns:
            db.session.execute(text("ALTER TABLE courses ADD COLUMN description TEXT"))
            db.session.commit()
            click.echo("Added courses.description column.")
        additions = {
            "students": {"curriculum_id": "INTEGER REFERENCES curricula(id)"},
            "subjects": {"curriculum_id": "INTEGER REFERENCES curricula(id)", "curriculum_subject_id": "INTEGER REFERENCES curriculum_subjects(id)"},
            "users": {"admin_scope": "VARCHAR(30) NOT NULL DEFAULT 'office'", "is_demo": "BOOLEAN NOT NULL DEFAULT false"},
        }
        for table, columns in additions.items():
            existing = {column["name"] for column in inspect(db.engine).get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
                    db.session.commit()
                    click.echo(f"Added {table}.{name}.")
        click.echo("Database schema upgraded successfully.")

    @app.cli.command("bootstrap-admin")
    def bootstrap_admin_command():
        """Create the first production Admin from environment variables."""
        from app.models import User
        from app.services.supabase_auth import SupabaseAuthError, upsert_auth_user

        if User.query.filter_by(role="admin").first():
            click.echo("An Admin account already exists; bootstrap skipped.")
            return

        username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "admin").strip().lower()
        full_name = os.environ.get("BOOTSTRAP_ADMIN_NAME", "System Admin").strip()
        email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
        if not email or len(password) < 8:
            raise click.ClickException(
                "Set BOOTSTRAP_ADMIN_EMAIL and a BOOTSTRAP_ADMIN_PASSWORD of at least 8 characters."
            )
        if User.query.filter((User.username == username) | (User.email == email)).first():
            raise click.ClickException("Bootstrap username or email is already in use.")

        user = User(
            username=username,
            full_name=full_name,
            email=email,
            role="admin",
            admin_scope="administrator",
            is_active=True,
        )
        user.set_password(password)
        try:
            upsert_auth_user(
                email=email,
                password=password,
                full_name=full_name,
                role="admin",
            )
            db.session.add(user)
            db.session.commit()
        except (SQLAlchemyError, SupabaseAuthError) as error:
            db.session.rollback()
            raise click.ClickException(f"Admin bootstrap failed: {error}") from error
        click.echo(f"Admin account created for {email}.")


@login_manager.user_loader
def load_user(user_id: str):
    """Load a user from the session id stored by Flask-Login."""
    from app.models import User

    try:
        user = db.session.get(User, int(user_id))
        if user and user.is_demo and (not current_app.config.get('DEMO_MODE') or current_app.config.get('IS_PRODUCTION')):
            return None
        return user
    except (TypeError, ValueError):
        return None


def validate_runtime_config(app: Flask) -> None:
    """Fail early when production starts with unsafe or incomplete secrets."""
    if not app.config.get("IS_PRODUCTION"):
        return

    if app.config.get('DEMO_MODE'):
        raise RuntimeError('Public demo credentials are for local use. Set PRAVA_DEMO_MODE=false in production.')

    secret_key = app.config.get("SECRET_KEY", "")
    if secret_key == "dev-change-this-secret-key" or len(secret_key) < 32:
        raise RuntimeError("Production SECRET_KEY must be a unique value of at least 32 characters.")

    if app.config.get("SUPABASE_AUTH_ENABLED"):
        required = ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_SECRET_KEY")
        missing = [key for key in required if not app.config.get(key)]
        if missing:
            raise RuntimeError(f"Missing production Supabase settings: {', '.join(missing)}")


def register_error_handlers(app: Flask) -> None:
    """Register beginner-friendly error pages."""

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("errors/400.html"), 400

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def request_too_large(error):
        return render_template("errors/413.html"), 413


def register_security_headers(app: Flask) -> None:
    """Add browser security headers and prevent caching authenticated pages."""

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net data:; "
            "img-src 'self' data:; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
        )
        if current_user.is_authenticated or request.path.startswith(("/auth/", "/login", "/signup", "/admin/", "/faculty/", "/student/")):
            response.headers.setdefault("Cache-Control", "no-store, private")
        if app.config.get("IS_PRODUCTION"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
