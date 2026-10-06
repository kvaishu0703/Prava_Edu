"""Closed-date correction authority, ownership and audit preservation."""
from datetime import timedelta
from types import SimpleNamespace
import re
from unittest import TestCase
from app import create_app
from app.extensions import db
from app.models import Attendance, ActivityLog, Course, Faculty, Student, Subject, User
from app.services.attendance_policy import attendance_edit_policy, require_attendance_edit
from app.services.timetable import college_today


class AttendancePolicyTests(TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config.update(SUPABASE_AUTH_ENABLED=False, DEMO_MODE=True)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.admin = User(username='main',full_name='Main Administrator',email='main@example.test',role='admin',admin_scope='administrator')
        self.principal = User(username='principal',full_name='Principal',email='principal@example.test',role='admin',admin_scope='principal')
        self.teacher_user = User(username='teacher',full_name='Teacher',email='teacher@example.test',role='faculty')
        self.learner = User(username='learner',full_name='Learner',email='learner@example.test',role='student')
        for person in (self.admin,self.principal,self.teacher_user,self.learner):
            person.set_password('TestOnly@123')
        course = Course(code='BCA',name='BCA',duration='3 years',total_semesters=6)
        teacher = Faculty(user=self.teacher_user,employee_id='F1',department='BCA')
        student = Student(user=self.learner,enrollment_number='S1',course=course,semester=1,admission_year=2026)
        subject = Subject(name='Programming',code='CA1',course=course,semester=1,faculty=teacher)
        self.row = Attendance(student=student,subject=subject,faculty=teacher,
            attendance_date=college_today()-timedelta(days=7),status='Present',session_number=1,
            recorded_by=self.teacher_user)
        db.session.add_all([self.admin,self.principal,self.row])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def login(self, user):
        self.client.post('/auth/login',data={'username_or_email':user.username,'password':'TestOnly@123'})

    def draft(self):
        path=f'/campus/student-attendance/{self.row.id}/correct'
        html=self.client.get(path).get_data(as_text=True)
        token=re.search(r'name="register_version"[^>]*value="([^"]+)"',html).group(1)
        return path,dict(register_version=token,status='Absent',remarks='Corrected register',reason='Verified classroom register')

    def test_today_yesterday_and_closed_policy(self):
        today=college_today()
        for actor in (self.principal,self.teacher_user):
            self.assertTrue(attendance_edit_policy(actor,today)['can_edit'])
            self.assertTrue(attendance_edit_policy(actor,today-timedelta(days=1))['can_edit'])
            self.assertFalse(attendance_edit_policy(actor,today-timedelta(days=2))['can_edit'])
        self.assertTrue(attendance_edit_policy(self.admin,today-timedelta(days=2))['requires_reason'])
        for actor in (self.admin,self.principal,self.teacher_user):
            self.assertFalse(attendance_edit_policy(actor,today+timedelta(days=1))['can_edit'])
        with self.assertRaises(ValueError):
            require_attendance_edit(self.admin,today-timedelta(days=2),'')

    def test_principal_can_review_but_cannot_override(self):
        self.login(self.principal)
        self.assertEqual(self.client.get('/campus/student-attendance').status_code,200)
        self.assertEqual(self.client.get(f'/campus/student-attendance/{self.row.id}/correct').status_code,403)
        self.assertEqual(self.client.post(f'/campus/student-attendance/{self.row.id}/correct',data={'status':'Absent'}).status_code,403)

    def test_correction_keeps_original_and_records_admin_reason(self):
        self.login(self.admin)
        path,data=self.draft()
        original=self.row.created_at
        response=self.client.post(path,data=data)
        self.assertEqual(response.status_code,302)
        db.session.refresh(self.row)
        self.assertEqual(self.row.status,'Absent')
        self.assertEqual(self.row.created_at,original)
        self.assertEqual(self.row.recorded_by_user_id,self.teacher_user.id)
        self.assertEqual(self.row.updated_by_user_id,self.admin.id)
        self.assertIsNotNone(self.row.updated_at)
        log=ActivityLog.query.filter_by(action='administrator_correction').one()
        self.assertIn('Verified classroom register',log.description)
        self.assertIn('"before": {"status": "Present"',log.description)

    def test_stale_correction_does_not_overwrite(self):
        self.login(self.admin)
        path,data=self.draft()
        self.row.status='Late'
        db.session.commit()
        response=self.client.post(path,data=data)
        self.assertEqual(response.status_code,409)
        db.session.refresh(self.row)
        self.assertEqual(self.row.status,'Late')
        self.assertIn('Verified classroom register',response.get_data(as_text=True))
        self.assertEqual(ActivityLog.query.filter_by(action='administrator_correction').count(),0)

    def test_blank_reason_rejected(self):
        self.login(self.admin)
        path,data=self.draft()
        data['reason']=''
        self.assertEqual(self.client.post(path,data=data).status_code,400)
        self.assertEqual(self.row.status,'Present')

    def test_student_cannot_review_administrative_register(self):
        self.login(self.learner)
        response=self.client.get('/campus/student-attendance')
        self.assertEqual(response.status_code,302)
        self.assertIn('/student/dashboard',response.location)
