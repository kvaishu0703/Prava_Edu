"""Account switching, sign-up approval, and reproducible local demo identities."""
from unittest import TestCase
from werkzeug.security import check_password_hash, generate_password_hash
from app import create_app, validate_runtime_config
from app.extensions import db
from app.models import User, Student, StudentRegistration, Course, Curriculum
from app.services.college_setup import sync_college
from app.services.demo import setup_demo


class OnboardingTest(TestCase):
    password_hash = generate_password_hash('PrivateTest@123')

    def setUp(self):
        self.app = create_app('testing')
        self.app.config.update(DEMO_MODE=True, SUPABASE_AUTH_ENABLED=False, STUDENT_SIGNUP_ENABLED=True)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            sync_college()
            setup_demo()
            db.session.add(User(username='admin', email='admin@example.test', full_name='System Admin', role='admin', admin_scope='administrator', password_hash=self.password_hash))
            db.session.add(User(username='principal', email='principal@example.test', full_name='Principal', role='admin', admin_scope='principal', password_hash=self.password_hash))
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username, password='PrivateTest@123', slug='administration', remember=False):
        return self.client.post('/login/'+slug, data={'username_or_email':username, 'password':password, 'remember_me':'y' if remember else ''})

    def signup_data(self, **overrides):
        return dict(full_name='New Student', username='newstudent', email='newstudent@example.test', enrollment_number='COL2026001',
                    programme='BCA', semester='1', admission_year='2026', password='Student@123', confirm_password='Student@123', **overrides)

    def pending(self):
        response = self.client.post('/signup/bca', data=self.signup_data())
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            return StudentRegistration.query.one().id

    def test_selecting_another_portal_authenticates_that_account(self):
        self.login('admin', remember=True)
        page = self.client.get('/login/student/bca')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Enter the account for this portal below to switch', page.data)
        self.assertIn(b'Sign in as BCA Student', page.data)
        result = self.login('bca', 'bca123', 'student/bca')
        self.assertEqual(result.location, '/student/dashboard')
        page = self.client.get(result.location)
        self.assertIn(b'BCA Student', page.data)
        self.assertNotIn(b'System Admin', page.data)
        self.assertIn(b'Logout', page.data)
        self.assertIn(b'Back to Home', page.data)
        # The earlier administrator's remember cookie must not restore its identity.
        self.client.delete_cookie('session')
        self.assertEqual(self.client.get('/admin/dashboard').status_code, 302)
        self.assertIn('/login', self.client.get('/student/dashboard').location)

    def test_failed_switch_preserves_existing_identity_and_wrong_next_is_ignored(self):
        self.login('admin')
        response = self.login('home', 'home123', 'student/bca')
        self.assertIn(b'Invalid username/email or password', response.data)
        self.assertIn(b'System Admin', self.client.get('/admin/dashboard').data)
        result = self.client.post('/login/student/bca?next=/admin/students', data={'username_or_email':'bca','password':'bca123'})
        self.assertEqual(result.location, '/student/dashboard')

    def test_demo_setup_is_idempotent_and_keeps_password_edits(self):
        with self.app.app_context():
            student = User.query.filter_by(username='bca').one()
            student.set_password('NewPrivate@123')
            db.session.commit()
            setup_demo()
            self.assertEqual(User.query.filter_by(is_demo=True).count(), 4)
            self.assertEqual(Student.query.count(), 2)
            self.assertTrue(student.check_password('NewPrivate@123'))
            self.assertFalse(User.query.filter_by(username='admin').one().is_demo)

    def test_setup_migrates_only_legacy_labels_and_preserves_account_data(self):
        with self.app.app_context():
            student = User.query.filter_by(username='bca').one()
            staff = User.query.filter_by(username='staff').one()
            student.full_name = 'BCA Demo Student'
            staff.full_name = 'Verified Faculty Name'
            staff.faculty_profile.qualification = 'Local demonstration account'
            original = (student.id, student.password_hash, student.email,
                        student.student_profile.enrollment_number, student.is_active)
            db.session.commit()
            setup_demo()
            self.assertEqual(student.full_name, 'BCA Student')
            self.assertEqual(staff.full_name, 'Verified Faculty Name')
            self.assertIsNone(staff.faculty_profile.qualification)
            self.assertEqual(original, (student.id, student.password_hash, student.email,
                                       student.student_profile.enrollment_number, student.is_active))
            self.assertEqual(student.display_email, 'Not recorded')
            self.assertEqual(student.student_profile.display_enrollment, 'Not recorded')
            # Verified profile fields are shown verbatim, even on a local account.
            student.full_name = 'Vaishnavi Vijay Kale'
            student.email = 'vaishnavi@example.test'
            student.student_profile.enrollment_number = 'COL2026-028'
            self.assertEqual(student.display_name, student.full_name)
            self.assertEqual(student.display_email, student.email)
            self.assertEqual(student.student_profile.display_enrollment, 'COL2026-028')
            student.is_demo = False
            student.full_name = 'BCA Demo Student'
            self.assertEqual(student.display_name, student.full_name)

    def test_demo_setup_refuses_real_account_collision_and_production(self):
        with self.app.app_context():
            User.query.filter_by(username='staff').one().is_demo = False
            db.session.commit()
            with self.assertRaises(ValueError):
                setup_demo()
            self.app.config['IS_PRODUCTION'] = True
            with self.assertRaises(ValueError):
                setup_demo()
            self.app.config['SECRET_KEY'] = 'a'*64
            with self.assertRaisesRegex(RuntimeError, 'PRAVA_DEMO_MODE'):
                validate_runtime_config(self.app)

    def test_demo_disabled_revokes_login_and_existing_session(self):
        self.login('bca','bca123','student/bca')
        self.app.config['DEMO_MODE'] = False
        self.assertEqual(self.client.get('/student/dashboard').status_code,302)
        response = self.login('bca','bca123','student/bca')
        self.assertIn(b'Demo accounts are available only',response.data)

    def test_signup_awaits_office_review_and_saves_only_a_password_hash(self):
        item_id = self.pending()
        with self.app.app_context():
            item = db.session.get(StudentRegistration,item_id)
            self.assertTrue(check_password_hash(item.password_hash,'Student@123'))
            self.assertNotEqual(item.password_hash,'Student@123')
            self.assertEqual(item.status,'Pending')
            self.assertIsNone(User.query.filter_by(username='newstudent').first())
        self.assertIn(b'Invalid username/email or password',self.login('newstudent','Student@123','student/bca').data)
        self.login('office','office123')
        self.assertEqual(self.client.post(f'/admin/registrations/{item_id}',data={'decision':'Approved','note':'Enrollment checked'}).status_code,302)
        with self.app.app_context():
            user=User.query.filter_by(username='newstudent').one()
            self.assertEqual(user.role,'student');self.assertFalse(user.is_demo)
            self.assertTrue(user.check_password('Student@123'))
            self.assertEqual(user.student_profile.curriculum.pattern,'2024 NEP')
            self.assertEqual(user.student_profile.course.code,'BCA')
            self.assertIsNone(db.session.get(StudentRegistration,item_id).password_hash)
        self.assertEqual(self.login('newstudent','Student@123','student/bca').location,'/student/dashboard')

    def test_signup_cannot_inject_roles_or_wrong_department_or_duplicate_records(self):
        data=self.signup_data();data.update(role='admin',admin_scope='administrator',is_active='true')
        data['programme']='BSC-FSN'
        self.assertEqual(self.client.post('/signup/bca',data=data).status_code,200)
        with self.app.app_context():self.assertEqual(StudentRegistration.query.count(),0)
        data['programme']='BCA'
        self.assertEqual(self.client.post('/signup/bca',data=data).status_code,302)
        self.assertEqual(self.client.post('/signup/bca',data=data).status_code,200)
        with self.app.app_context():self.assertEqual(StudentRegistration.query.count(),1)
        for field,value in [('semester','7'),('programme','UNKNOWN'),('admission_year','2100'),('confirm_password','mismatch'),('website','bot')]:
            wrong=self.signup_data();wrong[field]=value
            self.assertEqual(self.client.post('/signup',data=wrong).status_code,200)

    def test_review_permissions_rejection_and_repeated_approval(self):
        item_id=self.pending()
        self.login('staff','staff123','staff')
        self.assertNotEqual(self.client.post(f'/admin/registrations/{item_id}',data={'decision':'Approved'}).status_code,200)
        self.login('principal')
        self.assertEqual(self.client.get('/admin/registrations').status_code,200)
        self.assertEqual(self.client.post(f'/admin/registrations/{item_id}',data={'decision':'Approved'}).status_code,403)
        self.login('office','office123')
        self.client.post(f'/admin/registrations/{item_id}',data={'decision':'Rejected','note':'Enrollment needs correction'})
        self.client.post(f'/admin/registrations/{item_id}',data={'decision':'Approved'})
        with self.app.app_context():
            self.assertEqual(db.session.get(StudentRegistration,item_id).status,'Rejected')
            self.assertIsNone(User.query.filter_by(username='newstudent').first())

    def test_conflicting_record_during_approval_rolls_back_everything(self):
        item_id=self.pending()
        with self.app.app_context():
            db.session.add(User(username='newstudent',email='office-created@example.test',full_name='Office record',role='student',password_hash=self.password_hash))
            db.session.commit()
        self.login('office','office123')
        response=self.client.post(f'/admin/registrations/{item_id}',data={'decision':'Approved'})
        self.assertIn(b'Nothing was changed',response.data)
        with self.app.app_context():
            self.assertEqual(db.session.get(StudentRegistration,item_id).status,'Pending')
            self.assertIsNone(Student.query.filter_by(enrollment_number='COL2026001').first())

    def test_signup_and_approval_require_csrf_and_disabled_signup_creates_nothing(self):
        self.app.config['STUDENT_SIGNUP_ENABLED']=False
        self.client.post('/signup/bca',data=self.signup_data())
        with self.app.app_context():self.assertEqual(StudentRegistration.query.count(),0)
        self.app.config.update(STUDENT_SIGNUP_ENABLED=True,WTF_CSRF_ENABLED=True)
        self.assertEqual(self.client.post('/signup/bca',data=self.signup_data()).status_code,400)
        page=self.client.get('/signup/bca')
        self.assertIn(b'csrf_token',page.data)
        self.assertIn('no-store',page.headers['Cache-Control'])
