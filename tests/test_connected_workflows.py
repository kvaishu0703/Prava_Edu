"""Academic writes remain consistent across staff, student and office views."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest import TestCase
import re

from werkzeug.datastructures import FileStorage
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import (User, Course, Curriculum, CurriculumSubject, Faculty, Student,
                        Subject, Marks, Notification, Assignment, Submission,
                        StudyMaterial, CampusActivity, ActivityParticipation)
from app.models.base import utc_now
from app.services.college_setup import sync_college
from app.services.marks import save_bulk_marks
from app.services.assignments import create_assignment, submit_assignment, grade_submission
from app.services.materials import create_material, material_for_student
from app.services.notifications import visible_notifications_for_user
from app.services.student import student_notifications
from app.services.faculty import faculty_notifications
from app.services.reports import marks_report_rows
from app.activities.routes import now_ist


class ConnectedWorkflowsTest(TestCase):
    password_hash = generate_password_hash('Workflow@123')

    def setUp(self):
        self.app = create_app('testing')
        self.uploads = TemporaryDirectory()
        self.app.config.update(SUPABASE_AUTH_ENABLED=False, UPLOAD_FOLDER=self.uploads.name)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            sync_college()
            for name, role in [('teacher', 'faculty'), ('otherteacher', 'faculty'),
                               ('bca', 'student'), ('hs', 'student'), ('oldpattern', 'student'),
                               ('principal', 'admin')]:
                user = User(username=name, email=name+'@workflow.test', full_name=name.title(),
                            role=role, password_hash=self.password_hash,
                            admin_scope='principal' if name == 'principal' else 'office')
                db.session.add(user)
                if role == 'faculty':
                    db.session.add(Faculty(user=user, employee_id=name, department='BCA'))
                if role == 'student':
                    course = Course.query.filter_by(code='BSC-FSN' if name == 'hs' else 'BCA').one()
                    curriculum = Curriculum.query.filter_by(course_id=course.id).one()
                    db.session.add(Student(user=user, course=course,
                        curriculum=curriculum if name != 'oldpattern' else None,
                        enrollment_number=name, semester=1, admission_year=2026))
            db.session.flush()
            catalogue = CurriculumSubject.query.filter_by(code='CA-101-T').one()
            faculty = User.query.filter_by(username='teacher').one().faculty_profile
            subject = Subject(code='FLOW-1', name='Connected workflow subject', course=catalogue.curriculum.course,
                              curriculum=catalogue.curriculum, curriculum_subject=catalogue,
                              semester=1, faculty=faculty, maximum_marks=50, passing_marks=20)
            db.session.add(subject)
            db.session.commit()
            self.subject_id = subject.id
            self.student_id = User.query.filter_by(username='bca').one().student_profile.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.uploads.cleanup()

    def login(self, name):
        self.client.post('/auth/logout')
        portal = 'student/home-science' if name == 'hs' else 'student/bca' if name in ('bca', 'oldpattern') else 'administration' if name == 'principal' else 'staff'
        response = self.client.post('/login/'+portal, data={'username_or_email': name+'@workflow.test', 'password': 'Workflow@123'})
        self.assertEqual(response.status_code, 302)

    def test_staff_marks_student_view_and_admin_export_agree(self):
        self.login('teacher')
        page = self.client.get(f'/faculty/marks?subject_id={self.subject_id}')
        version = re.search(rb'name="register_version" value="([^"]+)"', page.data).group(1).decode()
        response = self.client.post('/faculty/marks', data={'subject_id': self.subject_id,
             'register_version': version,
             'exam_type': 'Semester Exam', f'internal_{self.student_id}': 12,
             f'external_{self.student_id}': 30})
        self.assertEqual(response.status_code, 302)
        staff_report = self.client.get(f'/faculty/marks/report?subject_id={self.subject_id}')
        self.assertIn(b'Pending verification', staff_report.data)
        self.assertIn(b'IST', staff_report.data)
        with self.app.app_context():
            mark = Marks.query.one()
            headers, rows = marks_report_rows([mark])
            self.assertEqual(rows[0][headers.index('Result')], 'Pending verification')
            self.assertEqual(rows[0][headers.index('Total')], 42)
            self.assertIn('IST', rows[0][headers.index('Updated (IST)')])
            self.assertIsNone(mark.grade)
            self.assertEqual(Notification.query.count(), 1)
        self.login('bca')
        page = self.client.get('/student/marks')
        self.assertIn(b'Pending verification', page.data)
        self.assertIn(b'Teacher', page.data)
        self.assertIn(b'IST', page.data)
        notices = self.client.get('/student/notifications')
        self.assertIn(b'href="/student/marks"', notices.data)
        self.login('hs')
        self.assertNotIn(b'Marks updated: FLOW-1', self.client.get('/student/notifications').data)

    def test_unchanged_or_rolled_back_marks_do_not_send_new_notices(self):
        with self.app.app_context():
            subject = db.session.get(Subject, self.subject_id)
            row = {'student_id': self.student_id, 'internal_marks': 10, 'external_marks': 30}
            save_bulk_marks(subject.faculty, subject, 'Semester Exam', [row])
            db.session.rollback()
            self.assertEqual(Marks.query.count(), 0)
            self.assertEqual(Notification.query.count(), 0)
            save_bulk_marks(subject.faculty, subject, 'Semester Exam', [row]); db.session.commit()
            self.assertEqual(save_bulk_marks(subject.faculty, subject, 'Semester Exam', [row]), (0, 0, []))
            db.session.commit()
            self.assertEqual(Notification.query.count(), 1)

    def test_material_and_assignment_notices_target_exact_enrolled_curriculum(self):
        with self.app.app_context():
            subject = db.session.get(Subject, self.subject_id)
            material = create_material(subject.faculty, subject.id, 'Class notes', None,
                                       FileStorage(BytesIO(b'Learning notes'), filename='notes.txt'))
            assignment = create_assignment(subject.faculty, subject.id, 'Class work', None,
                                           now_ist()+timedelta(days=1), 20, None)
            db.session.add_all([material, assignment]); db.session.commit()
            expected = User.query.filter_by(username='bca').one()
            notices = Notification.query.all()
            self.assertEqual(len(notices), 2)
            self.assertEqual({n.target_user_id for n in notices}, {expected.id})
            self.assertIsNotNone(material_for_student(expected.student_profile, material.id))
            for name in ['hs', 'oldpattern']:
                user = User.query.filter_by(username=name).one()
                self.assertEqual(visible_notifications_for_user(user, user.student_profile), [])
                self.assertIsNone(material_for_student(user.student_profile, material.id))

    def test_resubmitted_work_clears_old_grade_and_roundtrip_updates_student(self):
        with self.app.app_context():
            subject = db.session.get(Subject, self.subject_id)
            assignment = create_assignment(subject.faculty, subject.id, 'Roundtrip assignment', None,
                                           now_ist()+timedelta(days=1), 20, None)
            db.session.add(assignment); db.session.commit(); assignment_id = assignment.id
        self.login('bca')
        path = f'/student/assignments/{assignment_id}/submit'
        self.assertEqual(self.client.post(path, data={'file': (BytesIO(b'First work'), 'first.txt')}).status_code, 302)
        with self.app.app_context():
            submission_id = Submission.query.one().id
        self.login('teacher')
        self.assertEqual(self.client.post(f'/faculty/submissions/{submission_id}/grade',
             data={'marks_obtained': 18, 'faculty_feedback': 'Correct reasoning'}).status_code, 302)
        self.login('bca')
        page = self.client.get('/student/assignments')
        self.assertIn(b'Correct reasoning', page.data)
        self.assertIn(b'Reviewed', page.data)
        self.assertIn(b'IST', page.data)
        self.client.post(path, data={'file': (BytesIO(b'Revised work'), 'revised.txt')})
        with self.app.app_context():
            submission = db.session.get(Submission, submission_id)
            self.assertEqual(submission.status, 'Submitted')
            self.assertIsNone(submission.marks_obtained)
            self.assertIsNone(submission.faculty_feedback)
            self.assertIsNone(submission.graded_at)
        self.assertNotIn(b'Correct reasoning', self.client.get('/student/assignments').data)

    def test_late_submission_uses_ist_deadline_and_rejects_other_student(self):
        with self.app.app_context():
            subject = db.session.get(Subject, self.subject_id)
            assignment = create_assignment(subject.faculty, subject.id, 'Past due', None,
                                           now_ist()-timedelta(minutes=1), 20, None)
            db.session.add(assignment); db.session.commit()
            student = db.session.get(Student, self.student_id)
            submission = submit_assignment(student, assignment, FileStorage(BytesIO(b'work'), filename='work.txt'))
            db.session.add(submission); db.session.commit()
            self.assertEqual(submission.status, 'Late')
            wrong = User.query.filter_by(username='hs').one().student_profile
            with self.assertRaisesRegex(ValueError, 'enrolled subjects'):
                submit_assignment(wrong, assignment, FileStorage(BytesIO(b'other'), filename='other.txt'))

    def test_legacy_notification_helpers_follow_private_scope_and_expiry(self):
        with self.app.app_context():
            admin = User.query.filter_by(username='principal').one()
            hs = User.query.filter_by(username='hs').one()
            bca = User.query.filter_by(username='bca').one()
            teacher = User.query.filter_by(username='teacher').one()
            db.session.add_all([
                Notification(title='Private', message='Private', creator=admin, target_role='all', target_user=hs),
                Notification(title='Expired', message='Expired', creator=admin, target_role='all', expires_at=utc_now()-timedelta(days=1)),
            ])
            db.session.commit()
            self.assertEqual(student_notifications(bca, bca.student_profile), [])
            self.assertEqual(faculty_notifications(teacher, teacher.faculty_profile), [])
            self.assertEqual([n.title for n in student_notifications(hs, hs.student_profile)], ['Private'])

    def test_activity_review_principal_access_and_revocation_clear_hours(self):
        with self.app.app_context():
            teacher = User.query.filter_by(username='teacher').one()
            item = CampusActivity(title='Campus workshop', description='Learning workshop', category='Workshop',
                department='bca', starts_at=now_ist()+timedelta(days=1), venue='Room 3', coordinator=teacher)
            db.session.add(item); db.session.commit(); activity_id = item.id
        self.login('bca')
        self.client.post(f'/activities/{activity_id}/register')
        with self.app.app_context():
            item = db.session.get(CampusActivity, activity_id); item.starts_at = now_ist()-timedelta(days=1)
            db.session.commit(); participation_id = ActivityParticipation.query.one().id
        path = f'/campus/activities/{activity_id}/participants'
        self.login('teacher')
        self.assertEqual(self.client.post(path, data={'participation_id': participation_id,
                         'status': 'Completed', 'hours': '2'}).status_code, 302)
        self.login('bca')
        self.assertIn(b'Completed', self.client.get('/student/activities').data)
        self.assertIn(b'IST', self.client.get('/student/activities').data)
        self.login('principal')
        self.assertEqual(self.client.get(path).status_code, 200)
        self.assertNotIn(b'Save review', self.client.get(path).data)
        self.assertEqual(self.client.post(path, data={'participation_id': participation_id,
                         'status': 'Not attended'}).status_code, 403)
        self.assertEqual(self.client.get(f'/activities/participation/{participation_id}/certificate').status_code, 200)
        self.login('otherteacher'); self.assertEqual(self.client.get(path).status_code, 403)
        self.login('teacher')
        self.client.post(path, data={'participation_id': participation_id, 'status': 'Not attended', 'hours': '2'})
        with self.app.app_context():
            self.assertIsNone(db.session.get(ActivityParticipation, participation_id).hours)
        self.login('bca')
        self.assertEqual(self.client.get(f'/activities/participation/{participation_id}/certificate').status_code, 404)

    def test_official_activity_references_are_not_created_as_current_events(self):
        page = self.client.get('/activities')
        self.assertIn(b'From the college website', page.data)
        self.assertIn(b'2021', page.data)
        self.assertIn(b'AQAR%202022-23.pdf', page.data)
        with self.app.app_context():
            self.assertEqual(CampusActivity.query.count(), 0)

    def test_stale_bulk_marks_cannot_replace_newer_scores_and_preserves_draft(self):
        self.login('teacher')
        page = self.client.get(f'/faculty/marks?subject_id={self.subject_id}')
        version = re.search(rb'name="register_version" value="([^"]+)"', page.data).group(1).decode()
        first = {'subject_id': self.subject_id, 'exam_type': 'Semester Exam', 'register_version': version,
                 f'internal_{self.student_id}': '12', f'external_{self.student_id}': '30'}
        self.assertEqual(self.client.post('/faculty/marks', data=first).status_code, 302)
        stale = dict(first, **{f'internal_{self.student_id}': '13', f'external_{self.student_id}': '32',
                             f'remarks_{self.student_id}': 'My unsaved correction'})
        rejected = self.client.post('/faculty/marks', data=stale)
        self.assertEqual(rejected.status_code, 409)
        self.assertIn(b'Unsaved entries preserved', rejected.data)
        self.assertIn(f'name="internal_{self.student_id}" value="13"'.encode(), rejected.data)
        self.assertIn(b'My unsaved correction', rejected.data)
        self.assertIn(b'Saved: 12', rejected.data)
        self.assertIn(b'Open latest register', rejected.data)
        self.assertIn(f'name="register_version" value="{version}"'.encode(), rejected.data)
        with self.app.app_context():
            self.assertEqual(Marks.query.one().total_marks, 42)
            self.assertEqual(Notification.query.count(), 1)
        latest = self.client.get(f'/faculty/marks?subject_id={self.subject_id}')
        stale['register_version'] = re.search(rb'name="register_version" value="([^"]+)"', latest.data).group(1).decode()
        self.assertEqual(self.client.post('/faculty/marks', data=stale).status_code, 302)
        with self.app.app_context():
            self.assertEqual(Marks.query.one().total_marks, 45)

    def test_marks_register_version_ignores_other_assessments_but_checks_roster(self):
        self.login('teacher')
        page = self.client.get(f'/faculty/marks?subject_id={self.subject_id}')
        version = re.search(rb'name="register_version" value="([^"]+)"', page.data).group(1).decode()
        with self.app.app_context():
            subject = db.session.get(Subject, self.subject_id)
            db.session.add(Marks(student_id=self.student_id, subject=subject, exam_type='Previous Exam',
                internal_marks=1, external_marks=1, total_marks=2, entered_by=subject.faculty_id))
            db.session.commit()
        payload = {'subject_id': self.subject_id, 'exam_type': 'Semester Exam', 'register_version': version,
                   f'internal_{self.student_id}': '10', f'external_{self.student_id}': '30'}
        self.assertEqual(self.client.post('/faculty/marks', data=payload).status_code, 302)
        page = self.client.get(f'/faculty/marks?subject_id={self.subject_id}')
        payload['register_version'] = re.search(rb'name="register_version" value="([^"]+)"', page.data).group(1).decode()
        with self.app.app_context():
            older = User.query.filter_by(username='oldpattern').one().student_profile
            older.curriculum_id = db.session.get(Subject, self.subject_id).curriculum_id
            db.session.commit()
        self.assertEqual(self.client.post('/faculty/marks', data=payload).status_code, 409)

    def test_missing_register_version_does_not_write_marks(self):
        self.login('teacher')
        response = self.client.post('/faculty/marks', data={'subject_id': self.subject_id,
            'exam_type': 'Semester Exam', f'internal_{self.student_id}': '10',
            f'external_{self.student_id}': '30'})
        self.assertEqual(response.status_code, 409)
        with self.app.app_context():
            self.assertEqual(Marks.query.count(), 0)

    def test_invalid_draft_keeps_original_version_until_conflict_is_resolved(self):
        self.login('teacher')
        page = self.client.get(f'/faculty/marks?subject_id={self.subject_id}')
        version = re.search(rb'name="register_version" value="([^"]+)"', page.data).group(1).decode()
        saved = {'subject_id': self.subject_id, 'exam_type': 'Semester Exam', 'register_version': version,
                 f'internal_{self.student_id}': '12', f'external_{self.student_id}': '30'}
        self.assertEqual(self.client.post('/faculty/marks', data=saved).status_code, 302)
        draft = dict(saved, **{f'internal_{self.student_id}': 'invalid'})
        invalid = self.client.post('/faculty/marks', data=draft)
        self.assertEqual(invalid.status_code, 400)
        retained = re.search(rb'name="register_version" value="([^"]+)"', invalid.data).group(1).decode()
        self.assertEqual(retained, version)
        draft[f'internal_{self.student_id}'] = '13'
        draft['register_version'] = retained
        self.assertEqual(self.client.post('/faculty/marks', data=draft).status_code, 409)
        with self.app.app_context():
            self.assertEqual(Marks.query.one().internal_marks, 12)

    def test_assignment_zero_is_a_valid_grade_and_blank_is_not(self):
        with self.app.app_context():
            subject = db.session.get(Subject, self.subject_id)
            assignment = create_assignment(subject.faculty, subject.id, 'Zero grade check', None,
                                           now_ist()+timedelta(days=1), 20, None)
            submission = Submission(assignment=assignment, student_id=self.student_id,
                                    submitted_file='submissions/work.txt', status='Submitted', submitted_at=utc_now())
            db.session.add_all([assignment, submission]); db.session.commit()
            submission_id = submission.id
        self.login('teacher')
        path = f'/faculty/submissions/{submission_id}/grade'
        self.assertEqual(self.client.post(path, data={'marks_obtained': '0', 'faculty_feedback': 'Needs revision'}).status_code, 302)
        with self.app.app_context():
            saved = db.session.get(Submission, submission_id)
            self.assertEqual(saved.marks_obtained, 0)
            self.assertEqual(saved.status, 'Graded')
        self.assertEqual(self.client.post(path, data={'marks_obtained': '', 'faculty_feedback': 'Blank'}).status_code, 200)
        with self.app.app_context():
            self.assertEqual(db.session.get(Submission, submission_id).faculty_feedback, 'Needs revision')

    def test_subject_workspace_links_use_verified_catalogue_and_enrolled_semester(self):
        self.login('bca')
        with self.app.app_context():
            subject = db.session.get(Subject, self.subject_id)
            catalogue_id = subject.curriculum_subject_id
        page = self.client.get('/student/subjects')
        self.assertIn(b'href="/student/syllabus"', page.data)
        self.assertIn(f'href="/academics/subject/{catalogue_id}"'.encode(), page.data)
        self.assertNotIn(b'href="/courses/BCA"', page.data)
        with self.app.app_context():
            db.session.get(Student, self.student_id).semester = 5
            db.session.commit()
        syllabus = self.client.get('/student/syllabus')
        self.assertIn('year=3', syllabus.location)
        self.assertIn('semester=5', syllabus.location)
        self.login('teacher')
        staff = self.client.get('/faculty/subjects')
        self.assertIn(f'/faculty/attendance?subject_id={self.subject_id}'.encode(), staff.data)
        self.assertIn(f'/faculty/marks?subject_id={self.subject_id}'.encode(), staff.data)
        self.assertIn(f'/academics/subject/{catalogue_id}'.encode(), staff.data)
