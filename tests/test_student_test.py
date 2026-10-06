"""Regression tests for the student-only Student Test Form."""

from unittest import TestCase
from sqlalchemy import text

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
        self.assertNotRegex(response.get_data(as_text=True), r"[\u0900-\u097f]")

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
        self.assertNotRegex(score_page.get_data(as_text=True), r"[\u0900-\u097f]")

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

    def test_response_identity_is_bound_to_login_and_other_students_cannot_read_it(self):
        self.login_student()
        payload = self.valid_payload()
        payload.update(full_name='Another Student', email='other@example.com', course_year='Other course')
        submitted = self.client.post('/student-test', data=payload)
        with self.app.app_context():
            saved = StudentTestResponse.query.one()
            student = User.query.filter_by(username='student').one()
            self.assertEqual(saved.user_id, student.id)
            self.assertEqual(saved.full_name, student.full_name)
            self.assertEqual(saved.email, student.email)
            self.assertEqual(saved.course_year, 'BCA - Semester 5')
            student.email = 'updated@example.com'
            other = User(username='other', email='other@example.com', full_name='Another Student', role='student')
            other.set_password('Other@123')
            db.session.add(other); db.session.commit()
        # Updating the profile email does not orphan the response.
        self.assertEqual(self.client.get(submitted.location).status_code, 200)
        self.client.post('/auth/logout')
        self.client.post('/auth/login', data={'username_or_email': 'other', 'password': 'Other@123'})
        self.assertEqual(self.client.get(submitted.location).status_code, 404)
        self.assertEqual(self.client.get(submitted.location+'/score').status_code, 404)
        self.client.post('/auth/logout')
        self.client.post('/auth/login', data={'username_or_email': 'admin', 'password': 'Admin@123'})
        self.assertEqual(self.client.get(submitted.location+'/score').status_code, 200)

    def test_legacy_ownership_migration_does_not_guess_owner_from_editable_email(self):
        from app.services.student_test_schema import upgrade_student_test_ownership
        with self.app.app_context():
            for name, email in [('ambiguous1', 'duplicate@example.com'), ('ambiguous2', 'DUPLICATE@example.com')]:
                user = User(username=name, email=email, full_name=name, role='student')
                user.set_password('Private@123'); db.session.add(user)
            db.session.commit()
            with db.engine.begin() as connection:
                connection.execute(text('DROP TABLE student_test_responses'))
                connection.execute(text('CREATE TABLE student_test_responses (id INTEGER PRIMARY KEY, email VARCHAR(120))'))
                for number, email in enumerate([' STUDENT@example.com ', 'duplicate@example.com', 'unknown@example.com', 'admin@example.com'], 1):
                    connection.execute(text('INSERT INTO student_test_responses (id,email) VALUES (:id,:email)'), {'id':number,'email':email})
            self.assertTrue(upgrade_student_test_ownership())
            rows = db.session.execute(text('SELECT user_id FROM student_test_responses ORDER BY id')).scalars().all()
            self.assertEqual(rows, [None, None, None, None])
            new_user = User(username='lateowner', email='unknown@example.com', full_name='New user', role='student')
            new_user.set_password('Private@123'); db.session.add(new_user); db.session.commit()
            self.assertFalse(upgrade_student_test_ownership())
            self.assertIsNone(db.session.execute(text('SELECT user_id FROM student_test_responses WHERE id=3')).scalar())

    def test_unmatched_legacy_response_is_admin_only(self):
        with self.app.app_context():
            saved = StudentTestResponse(full_name='Legacy response', email='unknown@example.com',
                course_year='BCA', answers_json='{}', score=0, total_questions=8, website_rating=3)
            db.session.add(saved); db.session.commit(); token = saved.public_token
        self.login_student()
        self.assertEqual(self.client.get(f'/student-test/response/{token}').status_code, 404)
        self.client.post('/auth/logout')
        self.client.post('/auth/login', data={'username_or_email': 'admin', 'password': 'Admin@123'})
        self.assertEqual(self.client.get(f'/student-test/response/{token}').status_code, 200)


if __name__ == "__main__":
    import unittest

    unittest.main()
