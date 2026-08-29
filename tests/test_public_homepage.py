"""Regression tests for the professional public homepage."""

from io import BytesIO
from tempfile import TemporaryDirectory
from unittest import TestCase

from app import create_app
from app.extensions import db
from app.models import ContactInquiry, Course, Faculty, Notification, Student, Subject, User


class PublicHomepageTestCase(TestCase):
    """Exercise dynamic homepage data and contact form storage."""

    def setUp(self):
        self.uploads = TemporaryDirectory()
        self.app = create_app("testing")
        self.app.config["UPLOAD_FOLDER"] = self.uploads.name
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            admin = self._user("admin", "admin@example.com", "admin")
            faculty_user = self._user("faculty", "faculty@example.com", "faculty")
            student_user = self._user("student", "student@example.com", "student")
            course = Course(name="Bachelor of Computer Applications", code="BCA", duration="3 Years", total_semesters=6)
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
        self.assertIn(b"PRAVA College", response.data)
        self.assertIn(b"Total Students", response.data)
        self.assertIn(b"Bachelor of Computer Applications", response.data)
        self.assertIn(b"Exam Notice", response.data)
        self.assertIn(b"Student Login", response.data)
        self.assertIn(b"Contact Us", response.data)

    def test_public_course_detail_page_shows_subjects(self):
        response = self.client.get("/courses/BCA")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Bachelor of Computer Applications", response.data)
        self.assertIn(b"Semester 5", response.data)
        self.assertIn(b"Web Technology", response.data)

    def test_contact_form_saves_public_inquiry(self):
        response = self.client.post(
            "/",
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
        self.client.post("/", data={
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

    def test_admin_can_update_contact_inquiry_status(self):
        self.client.post("/", data={
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
