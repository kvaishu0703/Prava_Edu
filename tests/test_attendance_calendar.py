"""Attendance totals, session isolation and a lossless legacy upgrade."""
from datetime import date, time
from unittest import TestCase
from sqlalchemy import text
from app import create_app
from app.extensions import db
from app.models import Attendance, Course, Curriculum, Faculty, Student, Subject, TimetableSlot, User
from app.services.attendance import save_bulk_attendance
from app.services.attendance_schema import upgrade_attendance_sessions
from app.services.attendance_summary import build_attendance_overview
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

    def tearDown(self):
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
        response=self.client.post('/faculty/attendance',data={'subject_id':self.subject.id,'attendance_date':'2026-06-15','session_id':first.id,f'status_{self.student.id}':'Late'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Attendance.query.filter_by(session_number=1).one().status,'Late')
        self.assertEqual(Attendance.query.filter_by(session_number=2).one().status,'Absent')

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
        row=db.session.get(Attendance,42)
        self.assertEqual((row.id,row.status,row.remarks,row.session_number),(42,'Late','Keep this note',1))
        self.record(date(2026,6,15),'Present',2)
        db.session.commit()
        self.assertEqual(Attendance.query.count(),2)
