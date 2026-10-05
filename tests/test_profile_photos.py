"""Profile photo persistence, gender selection and role isolation."""
import io
import tempfile
from pathlib import Path
from unittest import TestCase
from app import create_app
from app.extensions import db
from app.models import Course, Faculty, Student, User


class ProfilePhotosTestCase(TestCase):
    def setUp(self):
        self.uploads=tempfile.TemporaryDirectory()
        self.app=create_app('testing')
        self.app.config.update(UPLOAD_FOLDER=self.uploads.name, SUPABASE_AUTH_ENABLED=False)
        self.client=self.app.test_client()
        with self.app.app_context():
            db.create_all()
            course=Course(name='BCA',code='BCA',duration='3 years',total_semesters=6)
            for role in ('admin','faculty','student'):
                user=User(username=role,full_name='Account '+role,email=role+'@example.com',role=role,is_active=True)
                user.set_password('Account@123')
                db.session.add(user)
                if role=='faculty':db.session.add(Faculty(user=user,employee_id='F001',department='BCA'))
                elif role=='student':db.session.add(Student(user=user,course=course,enrollment_number='S001',semester=5,admission_year=2024,gender='Female'))
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.uploads.cleanup()

    def login(self,role):
        return self.client.post('/auth/login',data={'username_or_email':role,'password':'Account@123'})

    def test_avatars_follow_saved_gender_and_preserve_uploaded_photo(self):
        with self.app.app_context():
            user=User.query.filter_by(role='student').one()
            self.assertEqual(user.profile_photo_path,'img/profile-female.png')
            user.student_profile.gender='Male'
            self.assertEqual(user.profile_photo_path,'img/profile-male.png')
            user.student_profile.gender=None
            self.assertEqual(user.profile_photo_path,'img/prava-mark.svg')
            user.student_profile.profile_image='uploads/profiles/own.png'
            user.student_profile.gender='Female'
            self.assertEqual(user.profile_photo_path,'uploads/profiles/own.png')

    def test_each_role_can_save_photo_and_gender_without_changing_other_accounts(self):
        image=Path(self.app.static_folder)/'img/profile-female.png'
        for role in ('admin','faculty','student'):
            with self.subTest(role=role):
                self.login(role)
                payload={'full_name':'Account '+role,'email':role+'@example.com','gender':'Female','department':'BCA',
                         'profile_image':(io.BytesIO(image.read_bytes()),'photo.png')}
                result=self.client.post(f'/{role}/profile/edit',data=payload,content_type='multipart/form-data')
                self.assertEqual(result.status_code,302)
                with self.app.app_context():
                    user=User.query.filter_by(role=role).one()
                    self.assertEqual(user.profile_gender,'Female')
                    path=user.profile_photo_path
                    self.assertTrue(path.startswith('uploads/profiles/'))
                    self.assertTrue((Path(self.uploads.name)/path.removeprefix('uploads/')).is_file())
                    self.assertEqual(User.query.count(),3)
                page=self.client.get(f'/{role}/profile')
                self.assertEqual(page.status_code,200)
                self.assertIn(path.encode(),page.data)
                self.client.post('/auth/logout')

    def test_invalid_admin_photo_rolls_back_profile_changes(self):
        self.login('admin')
        result=self.client.post('/admin/profile/edit',data={'full_name':'Changed','email':'changed@example.com','gender':'Male',
            'profile_image':(io.BytesIO(b'not an image'),'photo.exe')},content_type='multipart/form-data')
        self.assertEqual(result.status_code,200)
        self.assertIn(b'Please upload a JPG',result.data)
        with self.app.app_context():
            user=User.query.filter_by(role='admin').one()
            self.assertEqual(user.full_name,'Account admin')
            self.assertIsNone(user.profile_image)
            self.assertIsNone(user.gender)

    def test_student_cannot_edit_admin_photo(self):
        self.login('student')
        result=self.client.post('/admin/profile/edit',data={'full_name':'Changed','email':'changed@example.com','gender':'Male'})
        self.assertEqual(result.status_code,302)
        self.assertTrue(result.location.endswith('/student/dashboard'))
        with self.app.app_context():
            self.assertIsNone(User.query.filter_by(role='admin').one().gender)
