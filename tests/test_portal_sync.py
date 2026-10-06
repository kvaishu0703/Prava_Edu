"""A shared committed revision connects views without exposing another account."""
from datetime import date, datetime, timezone
from unittest import TestCase
from unittest.mock import patch
from flask import g

from app import create_app
from app.extensions import db
from app.models import Attendance, Course, Curriculum, Faculty, Student, Subject, User
from app.models.notification import ActivityLog
from app.services.attendance import save_bulk_attendance
from app.services.portal_sync import current_revision
from app.services.reports import attendance_report_rows


class PortalSyncTests(TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config.update(SUPABASE_AUTH_ENABLED=False, DEMO_MODE=True)
        # Tests keep a database app context; real browser requests each receive
        # their own app context and therefore a fresh Flask-Login user cache.
        @self.app.before_request
        def clear_test_user_cache():
            g.pop('_login_user', None)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.users = {}
        for role in ('admin', 'faculty', 'student'):
            user = User(username=role, full_name=f'{role.title()} Person', role=role,
                        email=f'{role}@example.test')
            user.set_password('TestPortal@123')
            self.users[role] = user
        self.course = Course(code='BCA', name='Computer Applications', duration='3 years', total_semesters=6)
        self.curriculum = Curriculum(course=self.course, pattern='2024 NEP', effective_year=2024)
        self.teacher = Faculty(user=self.users['faculty'], employee_id='EMP1', department='BCA')
        self.student = Student(user=self.users['student'], enrollment_number='ST1', course=self.course,
                               curriculum=self.curriculum, semester=1, admission_year=2026)
        self.subject = Subject(course=self.course, curriculum=self.curriculum, semester=1,
                               name='Programming', code='CS1', faculty=self.teacher)
        db.session.add_all([*self.users.values(), self.course, self.curriculum, self.teacher, self.student, self.subject])
        db.session.commit()
        self.clients = {role: self.app.test_client() for role in self.users}
        paths = {'student': '/login/student/bca', 'faculty': '/login/staff', 'admin': '/login/administration'}
        for role, client in self.clients.items():
            response = client.post(paths[role], data={'username_or_email': role, 'password': 'TestPortal@123'})
            self.assertEqual(response.status_code, 302)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def state(self, role='student'):
        response = self.clients[role].get('/api/portal-state')
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_committed_teacher_attendance_reaches_all_roles_with_same_revision(self):
        before = self.state()['version']
        save_bulk_attendance(self.teacher, self.subject, date(2026, 6, 15),
                             [{'student_id': self.student.id, 'status': 'Present'}])
        db.session.commit()
        states = [self.state(role) for role in ('admin', 'faculty', 'student')]
        self.assertGreater(states[0]['version'], before)
        self.assertEqual(len({state['version'] for state in states}), 1)
        self.assertTrue(all(set(state) == {'version', 'checked_at'} for state in states))
        page = self.clients['student'].get('/student/attendance?year=2026&month=2026-06')
        self.assertIn(b'100.0%', page.data)
        self.assertIn(b'By Faculty Person', page.data)

    def test_flushed_then_rolled_back_changes_do_not_advance_committed_revision(self):
        before = current_revision()
        original = self.subject.name
        self.subject.name = 'Uncommitted name'
        db.session.flush()
        db.session.rollback()
        db.session.expire_all()
        self.assertEqual(current_revision(), before)
        self.assertEqual(self.subject.name, original)

    def test_last_login_and_security_log_do_not_cause_other_views_to_refresh(self):
        before = current_revision()
        self.users['faculty'].last_login = datetime(2026, 10, 6, 7, 0, tzinfo=timezone.utc)
        db.session.add(ActivityLog(user=self.users['faculty'], action='login', module='auth'))
        db.session.commit()
        self.assertEqual(current_revision(), before)
        self.users['faculty'].full_name = 'Corrected Teacher Name'
        db.session.commit()
        self.assertGreater(current_revision(), before)

    def test_noop_save_does_not_advance_revision(self):
        before = current_revision()
        self.subject.name = self.subject.name
        db.session.commit()
        self.assertEqual(current_revision(), before)

    def test_reconfirming_attendance_publishes_the_new_actual_save_time(self):
        rows = [{'student_id': self.student.id, 'status': 'Present'}]
        # The second save already fills updated_by. A third confirmation then
        # changes only its explicit audit time and must reach the student's view.
        for hour in (6, 7):
            with patch('app.services.attendance.utc_now', return_value=datetime(2026, 10, 6, hour, 0, tzinfo=timezone.utc)):
                save_bulk_attendance(self.teacher, self.subject, date(2026, 6, 15), rows)
                db.session.commit()
        before = current_revision()
        with patch('app.services.attendance.utc_now', return_value=datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)):
            save_bulk_attendance(self.teacher, self.subject, date(2026, 6, 15), rows)
            db.session.commit()
        self.assertGreater(current_revision(), before)

    def test_unauthenticated_state_requires_login_and_contains_no_portal_data(self):
        response = self.app.test_client().get('/api/portal-state')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)
        self.assertIsNone(response.get_json())

    def test_safe_read_view_auto_refreshes_but_entry_form_does_not(self):
        safe = self.clients['student'].get('/student/attendance')
        self.assertIn(b'data-portal-live', safe.data)
        self.assertIn(b'data-auto-refresh="true"', safe.data)
        editing = self.clients['faculty'].get('/faculty/attendance')
        self.assertIn(b'data-portal-live', editing.data)
        self.assertIn(b'data-auto-refresh="false"', editing.data)
        self.assertIn('no-store', safe.headers['Cache-Control'])

    def test_admin_csv_includes_audit_times_without_claiming_imported_teacher_entry(self):
        imported = Attendance(student=self.student, subject=self.subject, faculty=self.teacher,
                              attendance_date=date(2026, 6, 15), status='Present',
                              created_at=datetime(2026, 10, 6, 6, 0, tzinfo=timezone.utc))
        db.session.add(imported)
        db.session.commit()
        headers, rows = attendance_report_rows([imported])
        values = dict(zip(headers, rows[0]))
        self.assertEqual(values['Day'], 'Monday')
        self.assertEqual(values['Entry Type'], 'Imported / earlier record')
        self.assertEqual(values['Recorded By'], 'Original recorder not recorded')
        self.assertIn('11:30:00 AM IST', values['Recorded / Imported At (IST)'])
        self.assertEqual(values['Last Updated At (IST)'], '')
        save_bulk_attendance(self.teacher, self.subject, date(2026, 6, 15),
                             [{'student_id': self.student.id, 'status': 'Late'}])
        db.session.commit()
        response = self.clients['admin'].get('/admin/reports/export/attendance')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Last Updated At (IST)', response.data)
        self.assertIn(b'Faculty Person', response.data)
        self.assertIn(b'Original recorder not recorded', response.data)
