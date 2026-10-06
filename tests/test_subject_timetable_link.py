"""Admin allocation changes reach timetables while recorded attendance stays intact."""
from datetime import date, time
from unittest import TestCase
from flask import g
from app import create_app
from app.extensions import db
from app.models import Attendance, Course, Curriculum, Faculty, Student, Subject, TimetableSlot, User
from app.services.timetable import student_slots


class SubjectTimetableLinkTests(TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config.update(SUPABASE_AUTH_ENABLED=False, DEMO_MODE=True)
        @self.app.before_request
        def reset_test_user_cache():
            g.pop('_login_user', None)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.users = {}
        for username, role in [('office', 'admin'), ('original', 'faculty'), ('replacement', 'faculty'), ('learner', 'student')]:
            user = User(username=username, full_name=username.title() + ' Person', role=role, email=username+'@example.test')
            user.set_password('TestLink@123')
            self.users[username] = user
        self.course = Course(code='BCA', name='Computer Applications', duration='3 years', total_semesters=6)
        self.curriculum = Curriculum(course=self.course, pattern='2024 NEP', effective_year=2024)
        self.original = Faculty(user=self.users['original'], employee_id='T1', department='BCA')
        self.replacement = Faculty(user=self.users['replacement'], employee_id='T2', department='BCA')
        self.student = Student(user=self.users['learner'], enrollment_number='S1', course=self.course,
                               curriculum=self.curriculum, semester=5, admission_year=2024)
        # Existing timetable-only teaching allocation without a claimed verified
        # catalogue link must still allow a teacher to be assigned safely.
        self.subject = Subject(course=self.course, curriculum=self.curriculum, semester=5,
                               code='IOT', name='Internet of Things', faculty=self.original,
                               maximum_marks=100, passing_marks=40)
        db.session.add_all([*self.users.values(), self.original, self.replacement, self.student, self.subject])
        db.session.flush()
        self.slot = TimetableSlot(course_id=self.course.id, curriculum_id=self.curriculum.id, semester=5,
                                  academic_year=2026, weekday=0, session_number=1, starts_at=time(9,10), ends_at=time(10,10),
                                  subject_id=self.subject.id, faculty_id=self.original.id, session_type='Theory',
                                  batch='All', room='Hall 3', teacher_code='OLD', source='college-photo')
        db.session.add(self.slot)
        db.session.commit()
        self.client = self.app.test_client()
        self.login('office')

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def login(self, username):
        role = self.users[username].role
        path = {'admin': '/login/administration', 'faculty': '/login/staff', 'student': '/login/student/bca'}[role]
        response = self.client.post(path, data={'username_or_email': username, 'password': 'TestLink@123'})
        self.assertEqual(response.status_code, 302)

    def edit(self, **changes):
        data = {'name': self.subject.name, 'code': self.subject.code, 'course_id': self.course.id,
                'curriculum_id': self.curriculum.id, 'curriculum_subject_id': 0, 'semester': 5,
                'faculty_id': self.replacement.id, 'maximum_marks': 100, 'passing_marks': 40, 'is_active': 'y'}
        data.update(changes)
        return self.client.post(f'/admin/subjects/{self.subject.id}/edit', data=data)

    def test_reassignment_updates_staff_and_student_timetables_without_rewriting_history(self):
        record = Attendance(student=self.student, subject=self.subject, faculty=self.original,
                            attendance_date=date(2026,6,15), status='Present', timetable_slot=self.slot,
                            recorded_by_user_id=self.original.user_id)
        db.session.add(record)
        db.session.commit()
        response = self.edit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.subject.faculty_id, self.replacement.id)
        self.assertEqual(self.slot.faculty_id, self.replacement.id)
        self.assertIsNone(self.slot.teacher_code)
        self.assertEqual(self.slot.teacher_label, 'Replacement Person')
        self.assertEqual((record.faculty_id, record.recorded_by_user_id), (self.original.id, self.original.user_id))
        self.assertEqual(student_slots(self.student, 2026)[0].teacher_label, 'Replacement Person')
        self.login('replacement')
        self.assertIn(b'Replacement Person', self.client.get('/campus/timetable').data)
        self.login('original')
        self.assertIn(b'No classes assigned', self.client.get('/campus/timetable').data)

    def test_scheduled_subject_cannot_lose_its_teacher(self):
        response = self.edit(faculty_id=0)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Select a replacement teacher', response.data)
        self.assertEqual(self.subject.faculty_id, self.original.id)
        self.assertEqual(self.slot.faculty_id, self.original.id)

    def test_scheduled_subject_cannot_move_to_another_semester(self):
        response = self.edit(semester=3)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Update its timetable before changing', response.data)
        self.assertEqual(self.subject.semester, 5)
        self.assertEqual(self.slot.semester, 5)

    def test_deactivated_subject_is_removed_from_current_schedule_not_history(self):
        response = self.edit(is_active='')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(student_slots(self.student, 2026), [])
        self.assertEqual(TimetableSlot.query.count(), 1)
        self.assertIn(b'No classes assigned', self.client.get('/campus/timetable').data)
