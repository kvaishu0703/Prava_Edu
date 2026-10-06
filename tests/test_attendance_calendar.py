"""Attendance totals, session isolation and a lossless legacy upgrade."""
from datetime import date, datetime, time, timezone
from unittest import TestCase
from unittest.mock import patch
import re
from sqlalchemy import text
from app import create_app
from app.extensions import db
from app.models import Attendance, Course, Curriculum, Faculty, Student, Subject, TimetableSlot, User
from app.services.attendance import save_bulk_attendance, attendance_register_version
from app.services.attendance_schema import upgrade_attendance_sessions, upgrade_attendance_audit
from app.services.attendance_summary import build_attendance_overview
from app.services.audit_time import college_timestamp
from app.services.timetable import student_slots


class AttendanceCalendarTests(TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config.update(SUPABASE_AUTH_ENABLED=False, DEMO_MODE=True)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.teacher_user = User(username='teacher', full_name='Teacher', email='teacher@example.test', role='faculty')
        self.student_user = User(username='learner', full_name='Learner', email='learner@example.test', role='student')
        self.other_user = User(username='second', full_name='Second learner', email='second@example.test', role='student')
        for user in [self.teacher_user,self.student_user,self.other_user]:
            user.set_password('PrivateTest@123')
        self.course = Course(code='BCA', name='Computer Applications', duration='3 years', total_semesters=6)
        self.curriculum = Curriculum(course=self.course, pattern='2024 NEP', effective_year=2024)
        self.teacher = Faculty(user=self.teacher_user, employee_id='T1', department='BCA')
        self.student = Student(user=self.student_user, enrollment_number='S1', course=self.course, curriculum=self.curriculum, semester=1, admission_year=2026, practical_batch='A')
        self.other = Student(user=self.other_user, enrollment_number='S2', course=self.course, curriculum=self.curriculum, semester=1, admission_year=2026, practical_batch='B')
        self.subject = Subject(course=self.course, curriculum=self.curriculum, semester=1, name='Programming', code='CS1', faculty=self.teacher)
        db.session.add_all([self.teacher,self.student,self.other,self.subject])
        db.session.commit()
        self.client = self.app.test_client()
        # Historical fixture dates are yesterday for the faculty HTTP entry
        # window; summary tests continue to pass their independent report date.
        self.policy_clock = patch('app.services.attendance_policy.college_today', return_value=date(2026,6,16))
        self.policy_clock.start()

    def tearDown(self):
        self.policy_clock.stop()
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def record(self, day, status='Present', number=1, student=None):
        row = Attendance(student=student or self.student, subject=self.subject, faculty=self.teacher,
                         attendance_date=day, status=status, session_number=number)
        db.session.add(row)
        return row

    def slot(self, number=1, batch='All'):
        row = TimetableSlot(course_id=self.course.id, curriculum_id=self.curriculum.id, semester=1,
            academic_year=2026, weekday=0, session_number=number, starts_at=time(9+number,10), ends_at=time(10+number,10),
            subject_id=self.subject.id, faculty_id=self.teacher.id, session_type='Practical', batch=batch, room='Lab', source='test')
        db.session.add(row)
        db.session.commit()
        return row

    def login(self, role='student'):
        path = '/login/student/bca' if role=='student' else '/login/staff'
        response = self.client.post(path, data={'username_or_email':'learner' if role=='student' else 'teacher', 'password':'PrivateTest@123'})
        self.assertEqual(response.status_code,302)

    def test_totals_are_weighted_and_future_dates_are_excluded(self):
        self.record(date(2026,6,15))
        self.record(date(2026,9,30))
        self.record(date(2026,9,30),'Absent',2)
        self.record(date(2026,10,5),'Late')
        self.record(date(2026,10,7),'Absent')
        self.record(date(2026,5,31),'Absent')
        self.record(date(2026,6,15),'Absent',student=self.other)
        db.session.commit()
        result=build_attendance_overview(self.student,2026,today=date(2026,10,6))
        self.assertEqual(result['overall'], {'total':4,'present':2,'late':1,'attended':3,'absent':1,'percentage':75.0,'days':3})
        self.assertEqual(sum(row['total'] for row in result['months']),4)
        self.assertEqual(sum(row['total'] for row in result['weeks']),4)
        self.assertEqual(sum(row['total'] for row in result['semesters']),4)
        self.assertEqual(next(row for row in result['months'] if row['key']=='2026-09')['percentage'],50.0)
        self.assertEqual(result['current_week']['percentage'],100.0)

    def test_empty_and_future_months_have_no_fabricated_percentage(self):
        result=build_attendance_overview(self.student,2026,today=date(2026,10,6))
        self.assertIsNone(result['overall']['percentage'])
        self.assertEqual(len(result['months']),12)
        self.assertTrue(next(row for row in result['months'] if row['key']=='2027-01')['future'])

    def test_month_filter_only_changes_the_daily_register(self):
        self.record(date(2026,6,15))
        self.record(date(2026,9,30),'Absent')
        db.session.commit()
        result=build_attendance_overview(self.student,2026,month='2026-06',today=date(2026,10,6))
        self.assertEqual(result['overall']['total'],2)
        self.assertEqual([row['date'] for row in result['days']],[date(2026,6,15)])

    def test_student_sees_only_their_own_batch_and_curriculum(self):
        a=self.slot(1,'A')
        self.slot(1,'B')
        all_batches=self.slot(2)
        self.assertEqual([slot.id for slot in student_slots(self.student,2026)],[a.id,all_batches.id])

    def test_two_sessions_of_same_subject_are_saved_separately(self):
        first=self.slot(1)
        second=self.slot(2)
        for slot,status in [(first,'Present'),(second,'Absent')]:
            save_bulk_attendance(self.teacher,self.subject,date(2026,6,15),[{'student_id':self.student.id,'status':status}],slot=slot)
            db.session.commit()
        save_bulk_attendance(self.teacher,self.subject,date(2026,6,15),[{'student_id':self.student.id,'status':'Late'}],slot=first)
        db.session.commit()
        self.assertEqual([(r.session_number,r.status) for r in Attendance.query.order_by(Attendance.session_number)],[(1,'Late'),(2,'Absent')])

    def test_wrong_batch_and_future_attendance_are_rejected(self):
        slot=self.slot(1,'A')
        with self.assertRaisesRegex(ValueError,'batch'):
            save_bulk_attendance(self.teacher,self.subject,date(2026,6,15),[{'student_id':self.other.id,'status':'Present'}],slot=slot)
        with self.assertRaisesRegex(ValueError,'future'):
            save_bulk_attendance(self.teacher,self.subject,date(2099,6,15),[{'student_id':self.student.id,'status':'Present'}])
        self.assertEqual(Attendance.query.count(),0)

    def test_faculty_form_updates_only_selected_session(self):
        first=self.slot(1,'A')
        second=self.slot(2,'A')
        self.record(date(2026,6,15),'Present',1)
        self.record(date(2026,6,15),'Absent',2)
        db.session.commit()
        self.login('faculty')
        response=self.client.post('/faculty/attendance',data={'subject_id':self.subject.id,'attendance_date':'2026-06-15','session_id':first.id,
            'register_version': attendance_register_version(self.subject,date(2026,6,15),first), f'status_{self.student.id}':'Late'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Attendance.query.filter_by(session_number=1).one().status,'Late')
        self.assertEqual(Attendance.query.filter_by(session_number=2).one().status,'Absent')

    def test_teacher_entry_and_edit_keep_distinct_audit_times_and_session_metadata(self):
        first = self.slot(1)
        second = self.slot(2)
        recorded_at = datetime(2026, 10, 6, 6, 15, 20, tzinfo=timezone.utc)
        updated_at = datetime(2026, 10, 6, 7, 20, 30, tzinfo=timezone.utc)
        with patch('app.services.attendance.utc_now', return_value=recorded_at):
            for slot in [first, second]:
                save_bulk_attendance(self.teacher, self.subject, date(2026, 6, 15),
                                     [{'student_id': self.student.id, 'status': 'Present'}], slot=slot)
            db.session.commit()
        initial = Attendance.query.filter_by(session_number=1).one()
        original_created_at = initial.created_at
        self.assertEqual(initial.recorded_by_user_id, self.teacher_user.id)
        self.assertIsNone(initial.updated_at)
        replacement_user = User(username='replacement', full_name='New Subject Teacher',
                                email='replacement@example.test', role='faculty')
        replacement_user.set_password('PrivateTest@123')
        replacement = Faculty(user=replacement_user, employee_id='T2', department='BCA')
        db.session.add(replacement)
        db.session.flush()
        self.subject.faculty_id = replacement.id
        first.faculty_id = replacement.id
        first.starts_at, first.ends_at = time(11, 20), time(12, 20)
        first.session_type = 'Theory'
        db.session.commit()
        with patch('app.services.attendance.utc_now', return_value=updated_at):
            save_bulk_attendance(replacement, self.subject, date(2026, 6, 15),
                                 [{'student_id': self.student.id, 'status': 'Absent'}], slot=first)
            db.session.commit()
        self.assertEqual(initial.created_at, original_created_at)
        self.assertEqual(initial.recorded_by_user_id, self.teacher_user.id)
        self.assertEqual(initial.updated_by_user_id, replacement_user.id)
        self.assertEqual(initial.faculty_id, replacement.id)
        self.assertEqual((initial.starts_at, initial.ends_at, initial.session_type, initial.timetable_slot_id),
                         (time(11, 20), time(12, 20), 'Theory', first.id))
        self.assertIn('11:45:20 AM IST', initial.recorded_time_display)
        self.assertIn('12:50:30 PM IST', initial.updated_time_display)
        untouched = Attendance.query.filter_by(session_number=2).one()
        self.assertEqual(untouched.status, 'Present')
        self.assertIsNone(untouched.updated_at)
        self.assertIsNone(untouched.updated_by_user_id)

    def test_imported_row_keeps_unknown_original_recorder_when_teacher_updates_it(self):
        slot = self.slot(1)
        imported = self.record(date(2026, 6, 15))
        imported.created_at = datetime(2026, 10, 6, 5, 0, tzinfo=timezone.utc)
        db.session.commit()
        self.login('faculty')
        with patch('app.services.attendance.utc_now', return_value=datetime(2026, 10, 6, 7, 1, 2, tzinfo=timezone.utc)):
            response = self.client.post('/faculty/attendance', data={
                'subject_id': self.subject.id, 'attendance_date': '2026-06-15', 'session_id': slot.id,
                'register_version': attendance_register_version(self.subject, date(2026,6,15), slot),
                f'status_{self.student.id}': 'Absent', f'status_{self.other.id}': 'Present',
                f'remarks_{self.student.id}': 'Corrected from class register'})
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(imported.recorded_by_user_id)
        self.assertEqual(imported.updated_by_user_id, self.teacher_user.id)
        faculty_page = self.client.get(response.location)
        self.assertIn(b'12:31:02 PM IST', faculty_page.data)
        self.assertIn(b'By Teacher', faculty_page.data)
        self.client.get('/logout')
        self.login()
        student_page = self.client.get('/student/attendance?year=2026&month=2026-06')
        self.assertEqual(student_page.status_code, 200)
        self.assertIn(b'12:31:02 PM IST', student_page.data)
        self.assertIn(b'Original entry time and recorder not recorded.', student_page.data)
        self.assertIn(b'Subject teacher: Teacher', student_page.data)
        self.assertIn(b'0.0%', student_page.data)

    def test_ist_formatter_handles_utc_date_rollover_and_naive_sqlite_values(self):
        value = datetime(2026, 10, 5, 20, 0, 5, tzinfo=timezone.utc)
        expected = 'Tue, 06 Oct 2026 · 01:30:05 AM IST'
        self.assertEqual(college_timestamp(value), expected)
        self.assertEqual(college_timestamp(value.replace(tzinfo=None)), expected)
        self.assertEqual(college_timestamp(None), 'Not recorded')

    def load_register_version(self, slot):
        response = self.client.get(f'/faculty/attendance?subject_id={self.subject.id}&attendance_date=2026-06-15&session_id={slot.id}')
        self.assertEqual(response.status_code, 200)
        return re.search(rb'name="register_version" value="([^"]+)"', response.data).group(1).decode()

    def test_stale_bulk_form_cannot_overwrite_latest_attendance_and_keeps_draft(self):
        slot = self.slot(1)
        self.record(date(2026,6,15), 'Present', student=self.student)
        self.record(date(2026,6,15), 'Present', student=self.other)
        db.session.commit()
        self.login('faculty')
        old_version = self.load_register_version(slot)
        save_bulk_attendance(self.teacher, self.subject, date(2026,6,15), [
            {'student_id': self.student.id, 'status': 'Present'},
            {'student_id': self.other.id, 'status': 'Absent', 'remarks': 'Saved in another tab'}],
            slot=slot, expected_version=old_version)
        db.session.commit()
        latest_saved_at = Attendance.query.filter_by(student_id=self.other.id).one().updated_at
        response = self.client.post('/faculty/attendance', data={
            'subject_id': self.subject.id, 'attendance_date': '2026-06-15', 'session_id': slot.id,
            'register_version': old_version, f'status_{self.student.id}': 'Late',
            f'remarks_{self.student.id}': 'Keep my draft', f'status_{self.other.id}': 'Present'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Attendance.query.filter_by(student_id=self.student.id).one().status, 'Present')
        other = Attendance.query.filter_by(student_id=self.other.id).one()
        self.assertEqual((other.status, other.remarks, other.updated_at), ('Absent', 'Saved in another tab', latest_saved_at))
        self.assertIn(b'Keep my draft', response.data)
        self.assertIn(b'value="Late" checked', response.data)
        self.assertIn(b'Latest saved: Absent', response.data)
        self.assertIn(b'Reload latest register', response.data)
        self.assertIn(b'data-attendance-save disabled', response.data)

    def test_other_session_update_does_not_invalidate_this_register(self):
        first, second = self.slot(1, 'A'), self.slot(2, 'A')
        self.login('faculty')
        version = self.load_register_version(first)
        save_bulk_attendance(self.teacher, self.subject, date(2026,6,15),
                             [{'student_id': self.student.id, 'status': 'Absent'}], slot=second)
        db.session.commit()
        response = self.client.post('/faculty/attendance', data={
            'subject_id': self.subject.id, 'attendance_date': '2026-06-15', 'session_id': first.id,
            'register_version': version, f'status_{self.student.id}': 'Late'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Attendance.query.filter_by(session_number=1).one().status, 'Late')
        self.assertEqual(Attendance.query.filter_by(session_number=2).one().status, 'Absent')

    def test_missing_register_version_cannot_blindly_save_attendance(self):
        slot = self.slot(1, 'A')
        self.login('faculty')
        response = self.client.post('/faculty/attendance', data={
            'subject_id': self.subject.id, 'attendance_date': '2026-06-15', 'session_id': slot.id,
            f'status_{self.student.id}': 'Present'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Attendance.query.count(), 0)

    def test_saved_register_requires_explicit_edit_and_returns_to_read_mode_after_save(self):
        slot = self.slot(1, 'A')
        self.record(date(2026,6,15), 'Present')
        db.session.commit()
        self.login('faculty')
        path = f'/faculty/attendance?subject_id={self.subject.id}&attendance_date=2026-06-15&session_id={slot.id}'
        saved_page = self.client.get(path)
        self.assertIn(b'Edit attendance', saved_page.data)
        self.assertNotIn(b'type="radio"', saved_page.data)
        editing_page = self.client.get(path+'&edit=1')
        self.assertIn(b'aria-label="Present', editing_page.data)
        self.assertIn(b'value="Present" checked', editing_page.data)
        self.assertIn(b'data-all-present', editing_page.data)
        self.assertIn(b'data-attendance-search', editing_page.data)
        version = re.search(rb'name="register_version" value="([^"]+)"', editing_page.data).group(1).decode()
        with patch('app.services.attendance.utc_now', return_value=datetime(2026,6,16,9,0,5,tzinfo=timezone.utc)):
            result = self.client.post('/faculty/attendance', data={
                'subject_id': self.subject.id, 'attendance_date': '2026-06-15', 'session_id': slot.id,
                'register_version': version, f'status_{self.student.id}': 'Absent'}, follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b'Attendance saved for Monday, 15 Jun 2026.', result.data)
        self.assertIn(b'02:30:05 PM IST by Teacher.', result.data)
        self.assertIn(b'Saved register', result.data)
        self.assertNotIn(b'type="radio"', result.data)

    def test_closed_date_stays_read_only_even_with_edit_parameter_or_post(self):
        slot = self.slot(1, 'A')
        self.record(date(2026,6,8), 'Present')
        db.session.commit()
        self.login('faculty')
        response = self.client.get(f'/faculty/attendance?subject_id={self.subject.id}&attendance_date=2026-06-08&session_id={slot.id}&edit=1')
        self.assertIn(b'This date is closed for editing', response.data)
        self.assertNotIn(b'type="radio"', response.data)
        self.assertNotIn(b'>Edit attendance</a>', response.data)
        version = attendance_register_version(self.subject, date(2026,6,8), slot)
        denied = self.client.post('/faculty/attendance', data={
            'subject_id': self.subject.id, 'attendance_date': '2026-06-08', 'session_id': slot.id,
            'register_version': version, f'status_{self.student.id}': 'Absent'})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(Attendance.query.one().status, 'Present')

    def test_unmarked_students_are_not_silently_saved_absent(self):
        slot = self.slot(1)
        self.login('faculty')
        response = self.client.post('/faculty/attendance', data={
            'subject_id': self.subject.id, 'attendance_date': '2026-06-15', 'session_id': slot.id,
            'register_version': self.load_register_version(slot), f'status_{self.student.id}': 'Present'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Choose Present, Absent or Late for every student', response.data)
        self.assertIn(b'value="Present" checked', response.data)
        self.assertEqual(Attendance.query.count(), 0)

    def test_day_picker_starts_with_first_scheduled_own_lecture_and_batch_roster(self):
        slot = self.slot(1, 'A')
        self.login('faculty')
        response = self.client.get('/faculty/attendance?attendance_date=2026-06-15')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your lectures on Monday', response.data)
        self.assertIn(b'1 students', response.data)
        self.assertIn(b'Batch A', response.data)
        self.assertIn(f'name="session_id" value="{slot.id}"'.encode(), response.data)
        self.assertNotIn(b'Second learner', response.data)

    def test_attendance_page_and_timetable_remain_student_scoped(self):
        self.record(date(2026,6,15))
        self.record(date(2026,6,15),'Absent',student=self.other)
        db.session.commit()
        self.login()
        page=self.client.get(f'/student/attendance?student_id={self.other.id}&year=2026&month=invalid')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'100.0%',page.data)
        self.assertIn(b'Monthly Attendance',page.data)
        self.assertEqual(self.client.get('/student/timetable').status_code,200)
        self.assertEqual(self.client.get('/campus/timetable').status_code,302)

    def test_legacy_schema_upgrade_preserves_records_and_is_repeatable(self):
        db.session.remove()
        with db.engine.begin() as connection:
            connection.execute(text('DROP TABLE attendance'))
            connection.execute(text('''CREATE TABLE attendance (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL, faculty_id INTEGER NOT NULL, attendance_date DATE NOT NULL,
                status VARCHAR(20) NOT NULL, remarks VARCHAR(255), created_at DATETIME NOT NULL,
                CONSTRAINT uq_attendance_student_subject_date UNIQUE(student_id,subject_id,attendance_date))'''))
            connection.execute(text("INSERT INTO attendance VALUES (42,1,1,1,'2026-06-15','Late','Keep this note','2026-06-15 12:00:00')"))
        upgrade_attendance_sessions()
        upgrade_attendance_sessions()
        upgrade_attendance_audit()
        upgrade_attendance_audit()
        row=db.session.get(Attendance,42)
        self.assertEqual((row.id,row.status,row.remarks,row.session_number),(42,'Late','Keep this note',1))
        self.assertEqual(row.created_at, datetime(2026,6,15,12,0))
        self.assertIsNone(row.recorded_by_user_id)
        self.assertIsNone(row.updated_at)
        self.assertIsNone(row.updated_by_user_id)
        self.record(date(2026,6,15),'Present',2)
        db.session.commit()
        self.assertEqual(Attendance.query.count(),2)
