"""Regression tests for the professional public homepage."""

from io import BytesIO
import re
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import ContactInquiry, Course, Faculty, Notification, Student, Subject, User


class PublicHomepageTestCase(TestCase):
    """Exercise dynamic homepage data and contact form storage."""

    def setUp(self):
        self.uploads = TemporaryDirectory()
        self.app = create_app("testing")
        self.app.config["UPLOAD_FOLDER"] = self.uploads.name
        self.app.config["SUPABASE_AUTH_ENABLED"] = False
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            admin = self._user("admin", "admin@example.com", "admin")
            faculty_user = self._user("faculty", "faculty@example.com", "faculty")
            student_user = self._user("student", "student@example.com", "student")
            course = Course(
                name="Bachelor of Computer Applications",
                code="BCA",
                description="Computer applications and web technology program.",
                duration="3 Years",
                total_semesters=6,
            )
            db.session.add(course)
            db.session.flush()
            db.session.add(Faculty(user=faculty_user, employee_id="FAC100", department="Computer Applications"))
            db.session.add(Subject(name="Web Technology", code="BCA505", course=course, semester=5, maximum_marks=100, passing_marks=40))
            db.session.add(
                Student(
                    user=student_user,
                    enrollment_number="BCA2026001",
                    course=course,
                    semester=5,
                    admission_year=2024,
                )
            )
            db.session.add(
                Notification(
                    title="Exam Notice",
                    message="Mid-term exam schedule is published.",
                    notification_type="Exam",
                    creator=admin,
                    target_role="all",
                )
            )
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.uploads.cleanup()

    @staticmethod
    def _user(username: str, email: str, role: str) -> User:
        user = User(username=username, full_name=username.title(), email=email, role=role)
        user.set_password("Password@123")
        db.session.add(user)
        return user

    def test_homepage_uses_database_backed_public_sections(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your college life.", response.data)
        self.assertNotIn(b"Total Students", response.data)
        self.assertIn(b"BCA", response.data)
        self.assertIn(b"Exam Notice", response.data)
        self.assertIn(b"Access your portal", response.data)
        self.assertIn(b"Contact Us", response.data)

    def test_public_course_detail_page_shows_subjects(self):
        response = self.client.get("/courses/BCA")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Bachelor of Computer Applications", response.data)
        self.assertIn(b"Computer applications and web technology program.", response.data)
        self.assertIn(b"Semester 5", response.data)
        self.assertIn(b"Web Technology", response.data)
        self.assertIn(b"Course Academic Workflow", response.data)

    def test_public_pages_are_separate_and_home_stays_public(self):
        home = self.client.get("/")
        self.assertNotIn(b'name="message"', home.data)
        self.assertNotIn(b"THE IDEA BEHIND THE PROJECT", home.data)
        for path, content in [("/about", b"THE IDEA BEHIND THE PROJECT"),
                              ("/contact", b'name="message"'),
                              ("/courses", b"Bachelor of Computer Applications")]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn(content, response.data)
        self.client.post("/login/administration", data={"username_or_email": "admin", "password": "Password@123"})
        self.assertIn(b"Your college life.", self.client.get("/").data)
        logout = self.client.post("/auth/logout")
        self.assertEqual(logout.location, "/")

    def test_college_identity_and_contact_address(self):
        for path in ["/", "/about", "/contact"]:
            response = self.client.get(path)
            self.assertIn(b"College of Home Science and BCA", response.data)
        self.assertIn(b"PKVM Campus, Babhaleshwar Road, Loni-413713", self.client.get("/contact").data)

    def test_unlinked_student_dashboard_shows_help(self):
        with self.app.app_context():
            self._user("newstudent", "newstudent@example.com", "student")
            db.session.commit()
        response = self.client.post("/login/student", data={"username_or_email": "newstudent", "password": "Password@123"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student profile is not linked yet.", response.data)

    def test_three_portals_and_matching_dashboard_redirects(self):
        page = self.client.get("/login")
        self.assertEqual(page.status_code, 200)
        for slug, username in [("student", "student"), ("staff", "faculty"), ("administration", "admin")]:
            with self.subTest(slug=slug):
                self.assertIn(f'/login/{slug}'.encode(), page.data)
                login_path = "/login/student/bca" if slug == "student" else f"/login/{slug}"
                form = self.client.get(login_path)
                self.assertIn(b'name="password"', form.data)
                response = self.client.post(login_path, data={"username_or_email": username, "password": "Password@123"})
                self.assertEqual(response.location, f"/{username}/dashboard")
                self.assertEqual(self.client.get(response.location).status_code, 200)
                self.client.post("/auth/logout")
        self.assertEqual(self.client.get("/login/unknown").status_code, 404)
        self.assertEqual(self.client.get("/auth/login").location, "/login")

    def test_portals_reject_all_mismatched_roles(self):
        for slug, allowed in [("student", "student"), ("staff", "faculty"), ("administration", "admin")]:
            for username in {"student", "faculty", "admin"} - {allowed}:
                with self.subTest(slug=slug, username=username):
                    response = self.client.post(f"/login/{slug}", data={"username_or_email": username, "password": "Password@123", "role": allowed})
                    self.assertIn(b"Invalid username/email or password.", response.data)
                    with self.client.session_transaction() as session:
                        self.assertNotIn("_user_id", session)

    def test_portal_wrong_password_inactive_account_and_csrf(self):
        wrong = self.client.post("/login/student", data={"username_or_email": "student", "password": "Incorrect@123"})
        self.assertIn(b"Invalid username/email or password.", wrong.data)
        with self.app.app_context():
            User.query.filter_by(username="student").one().is_active = False
            db.session.commit()
        inactive = self.client.post("/login/student", data={"username_or_email": "student", "password": "Password@123"})
        self.assertIn(b"This account is inactive", inactive.data)
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.assertEqual(self.client.post("/login/staff", data={"username_or_email": "faculty", "password": "Password@123"}).status_code, 400)
        page = self.client.get("/login/staff")
        token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', page.data).group(1).decode()
        response = self.client.post("/login/staff", data={"username_or_email": "faculty", "password": "Password@123", "csrf_token": token})
        self.assertEqual(response.location, "/faculty/dashboard")

    def test_protected_link_preserved_and_external_redirect_rejected(self):
        redirect = self.client.get("/student/marks")
        self.assertEqual(redirect.location, "/login/student?next=/student/marks")
        response = self.client.post(redirect.location, data={"username_or_email": "student", "password": "Password@123"})
        self.assertEqual(response.location, "/student/marks")
        self.client.post("/auth/logout")
        response = self.client.post("/login/student?next=//example.com", data={"username_or_email": "student", "password": "Password@123"})
        self.assertEqual(response.location, "/student/dashboard")

    def test_supabase_role_validation_and_session_flow(self):
        self.app.config["SUPABASE_AUTH_ENABLED"] = True
        auth_session = SimpleNamespace(email="student@example.com", user_id="test-id", access_token="test-access", refresh_token="test-refresh")
        with patch("app.auth.routes.sign_in_with_password", return_value=auth_session) as sign_in:
            denied = self.client.post("/login/staff", data={"username_or_email": "student", "password": "Password@123"})
            self.assertEqual(denied.status_code, 200)
            sign_in.assert_not_called()
            response = self.client.post("/login/student", data={"username_or_email": "student", "password": "Password@123"})
            self.assertEqual(response.location, "/student/dashboard")
            sign_in.assert_called_once_with("student@example.com", "Password@123")
            with self.client.session_transaction() as session:
                self.assertEqual(session["supabase_access_token"], "test-access")
                self.assertIn("_user_id", session)

    def test_contact_invalid_submission_and_csrf_do_not_save(self):
        response = self.client.post("/contact", data={"full_name": "Incomplete", "email": "invalid"})
        self.assertIn(b"Enter a valid email address.", response.data)
        with self.app.app_context():
            self.assertEqual(ContactInquiry.query.count(), 0)
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.assertEqual(self.client.post("/contact", data={"full_name": "Blocked"}).status_code, 400)

    def test_home_only_shows_public_notices(self):
        with self.app.app_context():
            admin = User.query.filter_by(username="admin").one()
            db.session.add(Notification(title="Staff only notice", message="Private message", notification_type="General", creator=admin, target_role="faculty"))
            db.session.commit()
        home = self.client.get("/")
        self.assertIn(b"Exam Notice", home.data)
        self.assertNotIn(b"Staff only notice", home.data)

    def test_workspace_pages_render_with_active_navigation(self):
        paths = {"student": ["profile", "subjects", "marks", "attendance", "materials", "assignments", "notifications"],
                 "faculty": ["profile", "subjects", "students", "attendance", "marks", "materials", "assignments", "notifications"],
                 "admin": ["profile", "students", "faculty", "courses", "subjects", "notifications", "reports", "contact-inquiries"]}
        for username, sections in paths.items():
            slug = {"faculty": "staff", "admin": "administration"}.get(username, username)
            self.client.post(f"/login/{slug}", data={"username_or_email": username, "password": "Password@123"})
            for section in sections:
                with self.subTest(role=username, section=section):
                    response = self.client.get(f"/{username}/{section}")
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(b'aria-label="Workspace navigation"', response.data)
                    self.assertIn(b'class="active" aria-current="page"', response.data)
            self.client.post("/auth/logout")

    def test_contact_form_saves_public_inquiry(self):
        response = self.client.post(
            "/contact",
            data={
                "full_name": "Vaishnavi Kale",
                "email": "vaishnavi@example.com",
                "phone": "9876543210",
                "subject": "Admission inquiry",
                "message": "Please share admission details.",
            },
        )

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            inquiry = ContactInquiry.query.one()
            self.assertEqual(inquiry.full_name, "Vaishnavi Kale")
            self.assertEqual(inquiry.email, "vaishnavi@example.com")
            self.assertEqual(inquiry.status, "New")

    def test_admin_can_review_contact_inquiries(self):
        self.client.post("/contact", data={
            "full_name": "Parent User",
            "email": "parent@example.com",
            "phone": "9876543210",
            "subject": "Fees",
            "message": "Please share fees details.",
        })
        self.client.post("/auth/login", data={"username_or_email": "admin", "password": "Password@123"})

        response = self.client.get("/admin/contact-inquiries")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Parent User", response.data)
        self.assertIn(b"Please share fees details.", response.data)

    def test_admin_dashboard_shows_recent_inquiries(self):
        self.client.post("/contact", data={
            "full_name": "Parent User",
            "email": "parent@example.com",
            "phone": "9876543210",
            "subject": "Fees",
            "message": "Please share fees details.",
        })
        self.client.post("/auth/login", data={"username_or_email": "admin", "password": "Password@123"})

        response = self.client.get("/admin/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"New Inquiries", response.data)
        self.assertIn(b"Recent Inquiries", response.data)
        self.assertIn(b"Parent User", response.data)

    def test_admin_can_update_contact_inquiry_status(self):
        self.client.post("/contact", data={
            "full_name": "Parent User",
            "email": "parent@example.com",
            "phone": "9876543210",
            "subject": "Fees",
            "message": "Please share fees details.",
        })
        self.client.post("/auth/login", data={"username_or_email": "admin", "password": "Password@123"})
        with self.app.app_context():
            inquiry_id = ContactInquiry.query.one().id

        response = self.client.post(f"/admin/contact-inquiries/{inquiry_id}/status", data={"status": "Closed"})

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            inquiry = db.session.get(ContactInquiry, inquiry_id)
            self.assertEqual(inquiry.status, "Closed")

    def test_admin_can_view_and_edit_own_profile(self):
        self.client.post("/auth/login", data={"username_or_email": "admin", "password": "Password@123"})

        profile = self.client.get("/admin/profile")
        self.assertEqual(profile.status_code, 200)
        self.assertIn(b"Admin Module", profile.data)

        response = self.client.post(
            "/admin/profile/edit",
            data={"full_name": "Principal Admin", "email": "principal@example.com"},
        )

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            admin = User.query.filter_by(username="admin").one()
            self.assertEqual(admin.full_name, "Principal Admin")
            self.assertEqual(admin.email, "principal@example.com")

    def test_student_can_upload_profile_photo(self):
        self.client.post("/auth/login", data={"username_or_email": "student", "password": "Password@123"})

        response = self.client.post(
            "/student/profile/edit",
            data={
                "full_name": "Student",
                "email": "student@example.com",
                "mobile_number": "9876543210",
                "date_of_birth": "",
                "gender": "",
                "address": "Updated address",
                "profile_image": (BytesIO(b"fake image bytes"), "profile.png"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            student = Student.query.join(User).filter(User.username == "student").one()
            self.assertTrue(student.profile_image.startswith("uploads/profiles/"))
            self.assertTrue(student.profile_image.endswith(".png"))

    def test_faculty_can_upload_profile_photo(self):
        self.client.post("/auth/login", data={"username_or_email": "faculty", "password": "Password@123"})

        response = self.client.post(
            "/faculty/profile/edit",
            data={
                "full_name": "Faculty",
                "email": "faculty@example.com",
                "mobile_number": "9876543210",
                "qualification": "MCA",
                "department": "Computer Applications",
                "joining_date": "",
                "profile_image": (BytesIO(b"fake image bytes"), "profile.jpg"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            faculty = Faculty.query.join(User).filter(User.username == "faculty").one()
            self.assertTrue(faculty.profile_image.startswith("uploads/profiles/"))
            self.assertTrue(faculty.profile_image.endswith(".jpg"))
