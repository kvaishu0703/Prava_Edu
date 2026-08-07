"""Automated regression tests for Phase 14 security and error handling."""

import re
import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from flask import Flask

from app import create_app, validate_runtime_config
from app.auth.routes import is_safe_next_url
from app.extensions import db
from app.models import User
from app.services.assignments import grade_submission
from app.services.materials import is_allowed_material
from config import database_url


class Phase14TestCase(TestCase):
    """Exercise authentication, authorization, errors, and security defaults."""

    def setUp(self):
        self.app = create_app("testing")
        self.app.config.update(
            PROPAGATE_EXCEPTIONS=False,
            SUPABASE_AUTH_ENABLED=False,
        )

        @self.app.get("/_test/server-error")
        def server_error():
            raise RuntimeError("Intentional test error")

        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            self._create_user("admin", "admin@example.com", "Admin@123", "admin")
            self._create_user("student", "student@example.com", "Student@123", "student")
            self._create_user("inactive", "inactive@example.com", "Inactive@123", "student", False)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @staticmethod
    def _create_user(username, email, password, role, is_active=True):
        user = User(
            username=username,
            email=email,
            full_name=username.title(),
            role=role,
            is_active=is_active,
        )
        user.set_password(password)
        db.session.add(user)
        return user

    def login(self, username="admin", password="Admin@123", query_string=None):
        return self.client.post(
            "/auth/login",
            data={"username_or_email": username, "password": password},
            query_string=query_string,
        )

    def test_health_and_security_headers(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["phase"], "Phase 15")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_password_is_hashed_and_login_works(self):
        with self.app.app_context():
            user = User.query.filter_by(username="admin").one()
            self.assertNotEqual(user.password_hash, "Admin@123")
            self.assertTrue(user.check_password("Admin@123"))

        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/admin/dashboard"))
        dashboard = self.client.get("/admin/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b'name="csrf_token"', dashboard.data)

    def test_invalid_and_inactive_logins_are_blocked(self):
        invalid = self.login(password="wrong-password")
        self.assertEqual(invalid.status_code, 200)
        self.assertIn(b"Invalid username/email or password", invalid.data)

        inactive = self.login(username="inactive", password="Inactive@123")
        self.assertEqual(inactive.status_code, 200)
        self.assertIn(b"This account is inactive", inactive.data)

    def test_protected_routes_and_role_redirect(self):
        anonymous = self.client.get("/admin/students")
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/auth/login", anonymous.location)

        self.login("student", "Student@123")
        denied = self.client.get("/admin/students")
        self.assertEqual(denied.status_code, 302)
        self.assertTrue(denied.location.endswith("/student/dashboard"))

    def test_safe_and_unsafe_next_redirects(self):
        safe = self.login(query_string={"next": "/phase-summary"})
        self.assertTrue(safe.location.endswith("/phase-summary"))

        self.client.post("/auth/logout")
        unsafe = self.login(query_string={"next": "//example.com/steal"})
        self.assertTrue(unsafe.location.endswith("/admin/dashboard"))

        self.assertTrue(is_safe_next_url("/student/profile"))
        self.assertFalse(is_safe_next_url("https://example.com"))
        self.assertFalse(is_safe_next_url("/\\example.com"))

    def test_logout_is_post_only_and_clears_session(self):
        self.login()
        self.assertEqual(self.client.get("/auth/logout").status_code, 405)
        response = self.client.post("/auth/logout")
        self.assertEqual(response.status_code, 302)
        protected = self.client.get("/admin/dashboard")
        self.assertIn("/auth/login", protected.location)

    def test_global_csrf_rejects_unverified_post(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        rejected = self.client.post(
            "/auth/login",
            data={"username_or_email": "admin", "password": "Admin@123"},
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertIn(b"request could not be verified", rejected.data)

        login_page = self.client.get("/auth/login")
        login_token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', login_page.data)
        self.assertIsNotNone(login_token)
        logged_in = self.client.post(
            "/auth/login",
            data={
                "username_or_email": "admin",
                "password": "Admin@123",
                "csrf_token": login_token.group(1).decode(),
            },
        )
        self.assertEqual(logged_in.status_code, 302)

        dashboard = self.client.get("/admin/dashboard")
        logout_token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', dashboard.data)
        self.assertIsNotNone(logout_token)
        self.assertEqual(self.client.post("/auth/logout").status_code, 400)
        logged_out = self.client.post(
            "/auth/logout",
            data={"csrf_token": logout_token.group(1).decode()},
        )
        self.assertEqual(logged_out.status_code, 302)

    def test_friendly_error_pages(self):
        missing = self.client.get("/missing-page")
        self.assertEqual(missing.status_code, 404)
        self.assertIn(b"page you are looking for", missing.data)

        failure = self.client.get("/_test/server-error")
        self.assertEqual(failure.status_code, 500)
        self.assertIn(b"Something went wrong", failure.data)

        original_limit = self.app.config["MAX_CONTENT_LENGTH"]
        self.app.config["MAX_CONTENT_LENGTH"] = 64
        too_large = self.client.post(
            "/auth/login",
            data={"username_or_email": "x" * 512, "password": "password"},
        )
        self.app.config["MAX_CONTENT_LENGTH"] = original_limit
        self.assertEqual(too_large.status_code, 413)
        self.assertIn(b"larger than the allowed", too_large.data)

    def test_invalid_session_user_id_is_treated_as_anonymous(self):
        with self.client.session_transaction() as session:
            session["_user_id"] = "not-an-integer"
            session["_fresh"] = True
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.location)

    def test_upload_extensions_and_grade_bounds(self):
        with self.app.app_context():
            self.assertTrue(is_allowed_material("notes.PDF"))
            self.assertFalse(is_allowed_material("payload.exe"))

        submission = SimpleNamespace(
            assignment=SimpleNamespace(maximum_marks=100),
            marks_obtained=None,
            faculty_feedback=None,
            status="Submitted",
            graded_at=None,
        )
        with self.assertRaisesRegex(ValueError, "negative"):
            grade_submission(submission, -1, None)
        with self.assertRaisesRegex(ValueError, "maximum"):
            grade_submission(submission, 101, None)

    def test_production_requires_a_strong_secret(self):
        app = Flask("production-config-test")
        app.config.update(IS_PRODUCTION=True, SECRET_KEY="short", SUPABASE_AUTH_ENABLED=False)
        with self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
            validate_runtime_config(app)

        app.config["SECRET_KEY"] = "a-unique-production-secret-that-is-long-enough"
        validate_runtime_config(app)

    def test_deployment_database_url_and_admin_bootstrap(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@db/prava"}):
            self.assertEqual(
                database_url(),
                "postgresql+psycopg://user:pass@db/prava",
            )

        with self.app.app_context():
            User.query.filter_by(role="admin").delete()
            db.session.commit()

        environment = {
            "BOOTSTRAP_ADMIN_USERNAME": "principal",
            "BOOTSTRAP_ADMIN_NAME": "College Principal",
            "BOOTSTRAP_ADMIN_EMAIL": "principal@example.com",
            "BOOTSTRAP_ADMIN_PASSWORD": "SecureAdmin@123",
        }
        with patch.dict(os.environ, environment):
            result = self.app.test_cli_runner().invoke(args=["bootstrap-admin"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Admin account created", result.output)

        with self.app.app_context():
            admin = User.query.filter_by(username="principal").one()
            self.assertTrue(admin.check_password("SecureAdmin@123"))


if __name__ == "__main__":
    import unittest

    unittest.main()
