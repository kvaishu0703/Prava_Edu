"""Regression tests for the student-only Student Test Form."""

from unittest import TestCase

from app import create_app
from app.extensions import db
from app.models import Course, Student, StudentTestResponse, User
from app.services.student_test import TEST_QUESTIONS


class StudentTestFormTestCase(TestCase):
    """Exercise student submission, scoring, and Admin result access."""

    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            course = Course(name="Bachelor of Computer Applications", code="BCA", duration="3 Years", total_semesters=6)
            db.session.add(course)
            admin = User(
                username="admin",
                full_name="System Admin",
                email="admin@example.com",
                role="admin",
                is_active=True,
            )
            admin.set_password("Admin@123")
            student_user = User(
                username="student",
                full_name="Test Student",
                email="student@example.com",
                role="student",
                is_active=True,
            )
            student_user.set_password("Student@123")
            student = Student(
                user=student_user,
                enrollment_number="BCA2026001",
                course=course,
                semester=5,
                admission_year=2024,
            )
            db.session.add_all([admin, student_user, student])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @staticmethod
    def valid_payload():
        payload = {
            "full_name": "Test Student",
            "email": "student@example.com",
            "college_name": "PRAVA College",
            "course_year": "BCA Third Year",
            "website_rating": "5",
            "feedback": "The student dashboard is easy to use.",
        }
        payload.update({question["key"]: question["correct"] for question in TEST_QUESTIONS})
        return payload

    def login_student(self):
        return self.client.post(
            "/auth/login",
            data={"username_or_email": "student", "password": "Student@123"},
        )

    def test_form_requires_student_login(self):
        response = self.client.get("/student-test")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/student", response.location)

    def test_student_form_is_available_after_login(self):
        self.login_student()

        response = self.client.get("/student-test")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student Test Form", response.data)
        self.assertIn(b"Submit Test", response.data)

    def test_incomplete_form_is_not_saved(self):
        self.login_student()

        response = self.client.post("/student-test", data={"full_name": "Only Name"})

        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(StudentTestResponse.query.count(), 0)

    def test_valid_response_is_scored_and_reviewed(self):
        self.login_student()

        response = self.client.post("/student-test", data=self.valid_payload())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/student-test/response/", response.location)

        confirmation = self.client.get(response.location)
        self.assertEqual(confirmation.status_code, 200)
        self.assertIn(b"Your response has been recorded", confirmation.data)

        with self.app.app_context():
            saved = StudentTestResponse.query.one()
            self.assertEqual(saved.score, len(TEST_QUESTIONS))
            self.assertEqual(saved.total_questions, len(TEST_QUESTIONS))
            score_url = f"/student-test/response/{saved.public_token}/score"

        score_page = self.client.get(score_url)
        self.assertEqual(score_page.status_code, 200)
        self.assertIn(b"8/8", score_page.data)
        self.assertIn(b"100%", score_page.data)

    def test_admin_can_view_responses(self):
        self.login_student()
        self.client.post("/student-test", data=self.valid_payload())
        self.client.post("/auth/logout")
        anonymous = self.client.get("/admin/student-test-responses")
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/login/administration", anonymous.location)

        self.client.post(
            "/auth/login",
            data={"username_or_email": "admin", "password": "Admin@123"},
        )
        admin_page = self.client.get("/admin/student-test-responses")
        self.assertEqual(admin_page.status_code, 200)
        self.assertIn(b"Test Student", admin_page.data)
        self.assertIn(b"8/8", admin_page.data)


if __name__ == "__main__":
    import unittest

    unittest.main()
