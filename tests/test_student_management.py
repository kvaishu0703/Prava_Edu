"""Principal account management, reversible removal and roster integration."""
from datetime import date, datetime
from unittest import TestCase
import re
from werkzeug.security import generate_password_hash
from sqlalchemy import event
from app import create_app
from app.extensions import db
from app.models import ActivityLog, Assignment, Attendance, Course, Faculty, Marks, Student, Subject, Submission, User
from app.services.attendance import students_for_subject
from app.services.faculty import assigned_students
from app.services.dashboard import get_admin_dashboard_data, get_faculty_dashboard_data
from app.services.homepage import public_homepage_data, course_detail_data
from app.services.reports import student_report_rows, admin_attendance_records
from app.services.student_management import lock_student_accounts, change_student_status


class StudentManagementTest(TestCase):
    password_hash = generate_password_hash('PrivateTest@123')

    def setUp(self):
        self.app = create_app('testing')
        self.app.config.update(SUPABASE_AUTH_ENABLED=False, DEMO_MODE=True)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            course = Course(code='BCA', name='Computer Applications', duration='3 years', total_semesters=6)
            home = Course(code='BSC-FSN', name='Home Science', duration='3 years', total_semesters=6)
            db.session.add_all([course, home])
            for name, role, scope in [('principal','admin','principal'), ('office','admin','office'),
                                      ('admin','admin','administrator'), ('teacher','faculty','office')]:
                db.session.add(User(username=name, full_name=name.title(), email=name+'@example.test',
                                    role=role, admin_scope=scope, password_hash=self.password_hash))
            db.session.flush()
            faculty = Faculty(user=User.query.filter_by(username='teacher').one(), employee_id='T001', department='BCA')
            db.session.add(faculty)
            for name, source, semester, gender, c in [('provided','provided',1,'Female',course),
                         ('generated','generated',1,'Male',course), ('imported','imported',5,'Female',home)]:
                user = User(username=name, full_name=name.title()+' Student', email=name+'@example.test',
                            role='student', password_hash=self.password_hash, is_demo=True)
                db.session.add(Student(user=user, course=c, enrollment_number='PRN-'+name,
                                       semester=semester, admission_year=2026, record_source=source, gender=gender))
            subject = Subject(code='BCA101', name='Programming', course=course, semester=1, faculty=faculty)
            db.session.add(subject)
            db.session.flush()
            student = Student.query.filter_by(record_source='generated').one()
            db.session.add_all([
                Attendance(student=student, subject=subject, faculty=faculty, attendance_date=date(2026,6,15), status='Present'),
                Marks(student=student, subject=subject, entered_by_user=faculty, exam_type='Internal', total_marks=80, grade='A'),
            ])
            db.session.commit()
            self.ids = {s.record_source:s.id for s in Student.query.all()}
            self.course_id = course.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, name, client=None):
        client = client or self.client
        client.post('/auth/logout')
        slug = 'student/home-science' if name == 'imported' else 'student/bca' if name in self.ids else 'staff' if name == 'teacher' else 'administration'
        response = client.post('/login/'+slug,data={'username_or_email':name,'password':'PrivateTest@123'})
        self.assertEqual(response.status_code,302)
        with client.session_transaction() as session:
            self.assertIn('_user_id',session)

    def student_form(self, username='newstudent', **updates):
        values = dict(full_name='New Student', username=username, email=username+'@example.test',
                      password='UniqueCollege@2026', enrollment_number='NEW-'+username,
                      course_id=self.course_id, curriculum_id=0, semester=1, admission_year=2026,
                      gender='Female', record_source='provided', practical_batch='B', is_active='y')
        values.update(updates)
        return values

    def change(self, action, ids=None, **updates):
        values = dict(action=action, student_ids=ids or [self.ids['generated']], selected_count=len(ids or [1]), confirmed='y', reason='College roster correction')
        values.update(updates)
        return self.client.post('/admin/students/bulk-action', data=values, follow_redirects=True)

    def edit_token(self, student_id, client=None):
        response = (client or self.client).get(f'/admin/students/{student_id}/edit')
        self.assertEqual(response.status_code,200)
        return re.search(rb'name="edit_version"[^>]*value="([^"]+)"',response.data).group(1).decode()

    def test_principal_creates_and_changes_login_credentials_without_privilege_escalation(self):
        self.login('principal')
        response = self.client.post('/admin/students/new', data=self.student_form(role='admin', admin_scope='administrator'))
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            user = User.query.filter_by(username='newstudent').one()
            student_id = user.student_profile.id
            self.assertEqual(user.role, 'student')
            self.assertTrue(user.check_password('UniqueCollege@2026'))
            self.assertEqual(user.student_profile.practical_batch, 'B')
        changed = self.student_form('changedlogin', password='ChangedCollege@2026')
        changed['edit_version'] = self.edit_token(student_id)
        self.assertEqual(self.client.post(f'/admin/students/{student_id}/edit',data=changed).status_code,302)
        with self.app.app_context():
            user = User.query.filter_by(username='changedlogin').one()
            self.assertTrue(user.check_password(changed['password']))
            self.assertFalse(user.check_password('UniqueCollege@2026'))
            self.assertEqual(ActivityLog.query.filter_by(module='students').count(),2)
        self.client.post('/auth/logout')
        response = self.client.post('/login/student/bca',data={'username_or_email':'changedlogin','password':changed['password']})
        self.assertEqual(response.status_code,302)
        with self.client.session_transaction() as session:
            self.assertIn('_user_id',session)

    def test_remove_and_restore_preserve_academic_records_and_update_rosters_and_sessions(self):
        student_client = self.app.test_client()
        self.login('generated',student_client)
        self.login('principal')
        response = self.change('archive', ids=[self.ids['provided'],self.ids['generated']])
        self.assertIn(b'2 student account(s) removed',response.data)
        with self.app.app_context():
            self.assertEqual(Student.query.count(),3)
            self.assertEqual(Attendance.query.count(),1)
            self.assertEqual(Marks.query.count(),1)
            self.assertEqual(students_for_subject(Subject.query.one()),[])
            self.assertEqual(assigned_students(Faculty.query.one()),[])
            self.assertTrue(db.session.get(Student,self.ids['generated']).archived_at)
            self.assertFalse(db.session.get(Student,self.ids['generated']).user.is_active)
            self.assertEqual(ActivityLog.query.filter_by(action='removed').count(),2)
        self.assertEqual(student_client.get('/student/dashboard').status_code,302)
        self.assertNotIn(b'data-name="Generated Student"',self.client.get('/admin/students').data)
        self.assertIn(b'data-name="Generated Student"',self.client.get('/admin/students?status=archived').data)
        result = self.change('restore',ids=[self.ids['provided'],self.ids['generated']])
        self.assertIn(b'2 student account(s) restored',result.data)
        with self.app.app_context():
            self.assertEqual(len(students_for_subject(Subject.query.one())),2)
            self.assertEqual(Marks.query.one().total_marks,80)
            self.assertIsNone(db.session.get(Student,self.ids['generated']).archived_at)
            self.assertTrue(db.session.get(Student,self.ids['generated']).user.is_active)
            self.assertEqual(ActivityLog.query.filter_by(action='restored').count(),2)

    def test_confirmation_invalid_mixed_stale_and_unknown_selections_are_atomic(self):
        self.login('principal')
        for updates in [dict(confirmed=''), dict(selected_count=2), dict(student_ids=['bad']),
                        dict(student_ids=[self.ids['generated'],9999], selected_count=2),
                        dict(student_ids=[self.ids['generated']]*2,selected_count=2),dict(reason='x'*501)]:
            self.change('archive',**updates)
            with self.app.app_context():
                self.assertFalse(Student.query.filter(Student.archived_at.isnot(None)).count())
        self.change('archive')
        response=self.change('archive',ids=[self.ids['provided'],self.ids['generated']])
        self.assertIn(b'already removed',response.data)
        with self.app.app_context():
            self.assertIsNone(db.session.get(Student,self.ids['provided']).archived_at)
        result=self.change('restore',ids=[self.ids['provided'],self.ids['generated']])
        self.assertIn(b'Only removed students',result.data)
        with self.app.app_context():
            self.assertIsNotNone(db.session.get(Student,self.ids['generated']).archived_at)

    def test_archived_edit_cannot_silently_reactivate_and_source_is_independent_of_local_mode(self):
        self.login('principal')
        data=self.client.get('/admin/students?source=generated&programme=BCA&year=1&gender=Male').data
        self.assertIn(b'data-name="Generated Student"',data)
        self.assertNotIn(b'data-name="Provided Student"',data)
        self.assertNotIn(b'data-name="Imported Student"',data)
        self.assertIn(b'>Year 3</option>',data)
        self.assertNotIn(b'>Year 4</option>',data)
        self.change('archive')
        response=self.client.post(f'/admin/students/{self.ids["generated"]}/edit', data=self.student_form('generated', edit_version=self.edit_token(self.ids['generated'])))
        self.assertIn(b'Restore this student',response.data)
        with self.app.app_context():
            self.assertFalse(db.session.get(Student,self.ids['generated']).user.is_active)
        for query in ['source=demo','status=bad','programme=UNKNOWN','year=99','gender=bad']:
            self.assertEqual(self.client.get('/admin/students?'+query).status_code,400)

    def test_permissions_csrf_duplicate_ids_and_blank_password(self):
        self.login('principal')
        for path in ['/admin/faculty/new','/admin/courses/new','/admin/access']:
            self.assertEqual(self.client.get(path).status_code,403)
        self.client.post('/admin/students/new',data=self.student_form(password=''))
        with self.app.app_context():self.assertIsNone(User.query.filter_by(username='newstudent').first())
        response=self.client.post('/admin/students/new',data=self.student_form('provided'))
        self.assertIn(b'Username already exists',response.data)
        for name in ['teacher','provided']:
            self.login(name)
            self.assertEqual(self.client.post('/admin/students/bulk-action',data={'action':'archive','confirmed':'y'}).status_code,302)
        self.login('principal')
        self.app.config['WTF_CSRF_ENABLED']=True
        self.assertEqual(self.client.post('/admin/students/bulk-action',data={'action':'archive','confirmed':'y'}).status_code,400)
        with self.app.app_context():
            self.assertFalse(Student.query.filter(Student.archived_at.isnot(None)).count())

    def test_removed_students_leave_live_counts_recent_lists_and_pending_reviews(self):
        with self.app.app_context():
            subject = Subject.query.one()
            task = Assignment(subject=subject, faculty=Faculty.query.one(), title='Programming assignment',
                              due_date=datetime(2026,10,20), is_active=True)
            db.session.add(task)
            db.session.flush()
            for source in ('provided','generated'):
                db.session.add(Submission(assignment=task, student_id=self.ids[source], status='Submitted',
                                          submitted_file='saved-work.txt'))
            db.session.commit()
            self.assertEqual(dict((s[0],s[1]) for s in get_faculty_dashboard_data(Faculty.query.one().user)['stats'])['Pending Reviews'],2)
        self.login('principal')
        self.change('archive',ids=[self.ids['provided'],self.ids['generated']])
        with self.app.app_context():
            data=get_admin_dashboard_data()
            self.assertEqual(dict((s[0],s[1]) for s in data['stats'])['Students'],1)
            self.assertEqual({s.id for s in data['recent_students']},{self.ids['imported']})
            self.assertEqual({d['slug']:d['students'] for d in data['departments_overview']},{'bca':0,'home-science':1})
            self.assertFalse(data['has_attendance'])
            self.assertEqual(data['attendance_percentage'],0)
            self.assertEqual(public_homepage_data()['summary_cards'][0][1],1)
            self.assertEqual(course_detail_data(db.session.get(Course,self.course_id))['student_count'],0)
            self.assertEqual(dict((s[0],s[1]) for s in get_faculty_dashboard_data(Faculty.query.one().user)['stats'])['Pending Reviews'],0)
            self.assertEqual(Submission.query.count(),2)
            self.assertEqual(len(student_report_rows()[1]),3)
            self.assertEqual(len(admin_attendance_records()),1)
        self.change('restore',ids=[self.ids['provided'],self.ids['generated']])
        with self.app.app_context():
            self.assertEqual(public_homepage_data()['summary_cards'][0][1],3)
            self.assertEqual(dict((s[0],s[1]) for s in get_faculty_dashboard_data(Faculty.query.one().user)['stats'])['Pending Reviews'],2)

    def test_two_edit_forms_reject_stale_draft_without_replacing_current_credentials(self):
        self.login('principal')
        office = self.app.test_client()
        self.login('office',office)
        student_id = self.ids['provided']
        first_token = self.edit_token(student_id)
        stale_token = self.edit_token(student_id,office)
        first = self.student_form('provided',full_name='Saved College Name',password='FirstSavedPassword@26',edit_version=first_token)
        self.assertEqual(self.client.post(f'/admin/students/{student_id}/edit',data=first).status_code,302)
        draft = self.student_form('provided',full_name='Office Unsaved Draft',password='StalePassword@26',edit_version=stale_token)
        response = office.post(f'/admin/students/{student_id}/edit',data=draft)
        self.assertEqual(response.status_code,409)
        self.assertIn(b'Office Unsaved Draft',response.data)
        self.assertIn(b'reload the latest student record',response.data)
        self.assertIn(stale_token.encode(),response.data)
        with self.app.app_context():
            user = db.session.get(Student,student_id).user
            self.assertEqual(user.full_name,'Saved College Name')
            self.assertTrue(user.check_password('FirstSavedPassword@26'))
            self.assertFalse(user.check_password('StalePassword@26'))

    def test_edit_opened_before_removal_cannot_reactivate_or_overwrite_the_archived_record(self):
        self.login('principal')
        student_id = self.ids['generated']
        token = self.edit_token(student_id)
        self.change('archive')
        draft = self.student_form('generated',full_name='Stale Active Profile',edit_version=token)
        response = self.client.post(f'/admin/students/{student_id}/edit',data=draft)
        self.assertEqual(response.status_code,409)
        self.assertIn(b'Stale Active Profile',response.data)
        with self.app.app_context():
            student = db.session.get(Student,student_id)
            self.assertTrue(student.archived_at)
            self.assertFalse(student.user.is_active)
            self.assertEqual(student.user.full_name,'Generated Student')
            self.assertTrue(student.user.check_password('PrivateTest@123'))

    def test_version_ignores_other_students_and_login_time_but_requires_the_loaded_token(self):
        self.login('principal')
        student_id = self.ids['provided']
        token = self.edit_token(student_id)
        with self.app.app_context():
            db.session.get(Student,self.ids['generated']).address = 'Another profile changed'
            db.session.get(Student,student_id).user.last_login = datetime(2026,10,6,14,10)
            db.session.commit()
        draft = self.student_form('provided',full_name='Valid Updated Name',password='',edit_version=token)
        self.assertEqual(self.client.post(f'/admin/students/{student_id}/edit',data=draft).status_code,302)
        draft.pop('edit_version')
        self.assertEqual(self.client.post(f'/admin/students/{student_id}/edit',data=draft).status_code,409)

    def test_edit_and_archive_lock_sqlite_before_the_target_profile_read(self):
        with self.app.app_context():
            statements=[]
            def capture(connection,cursor,statement,parameters,context,executemany):
                statements.append(statement.lower())
            event.listen(db.engine,'before_cursor_execute',capture)
            try:
                lock_student_accounts([self.ids['generated']])
                self.assertEqual(statements[0],'begin immediate')
                self.assertIn('from students',statements[1])
                db.session.rollback()
                actor=User.query.filter_by(username='principal').one()
                statements.clear()
                change_student_status(actor,[self.ids['generated']],'archive',selected_count=1)
                self.assertEqual(statements[0],'begin immediate')
                self.assertIn('from students',statements[1])
                db.session.rollback()
            finally:
                event.remove(db.engine,'before_cursor_execute',capture)
