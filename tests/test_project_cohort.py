"""Exercise cohort preparation in an isolated database and upload directory."""
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import (
    Assignment, Attendance, Course, Curriculum, Faculty, Marks, Student,
    StudyMaterial, Subject, Submission, TimetableSlot, User,
)
from app.models.academic_history import AcademicYearRecord
from app.services.academic_history import summarize_history, upsert_academic_history
from app.services.project_cohort import prepare_project_cohort


class ProjectCohortTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = create_app('testing')
        self.app.config.update(DEMO_MODE=True, IS_PRODUCTION=False, UPLOAD_FOLDER=self.directory.name)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.addCleanup(self.cleanup_database)
        self.targets = patch('app.services.project_cohort.TARGETS', {
            'BCA': (1, 1, 1), 'BSC-FSN': (1, 1, 1), 'BSC-TEXTILE': (1, 1, 1),
        })
        self.targets.start()
        self.addCleanup(self.targets.stop)
        self.today = patch('app.services.project_cohort.college_today', return_value=date(2026, 10, 6))
        self.today.start()
        self.addCleanup(self.today.stop)
        staff_user = User(username='teacher', full_name='Surekha Kale', email='teacher@example.test', role='faculty')
        staff_user.set_password('Teacher@123')
        self.faculty = Faculty(user=staff_user, employee_id='FAC-1', department='BCA')
        db.session.add(self.faculty)
        db.session.flush()
        self.subjects = {}
        self.curricula = {}
        for code in ('BCA', 'BSC-FSN', 'BSC-TEXTILE'):
            course = Course(code=code, name=code, duration='3 years', total_semesters=6)
            curriculum = Curriculum(course=course, pattern='2024 NEP', effective_year=2024)
            db.session.add(curriculum)
            db.session.flush()
            self.curricula[code] = curriculum
            for semester in range(1, 7):
                subject = Subject(course=course, curriculum=curriculum, semester=semester,
                    code=f'{code}-{semester}', name=f'{code} semester {semester}', faculty=self.faculty,
                    maximum_marks=100, passing_marks=40)
                db.session.add(subject)
                db.session.flush()
                self.subjects[(code, semester)] = subject
                if semester % 2:
                    for weekday in range(6):
                        for session in range(1, 6):
                            db.session.add(TimetableSlot(course=course, curriculum=curriculum,
                                semester=semester, academic_year=2026, weekday=weekday,
                                session_number=session, starts_at=time(8+session), ends_at=time(9+session),
                                subject=subject, faculty=self.faculty,
                                session_type='Theory' if session <= 3 else 'Practical', batch='All',
                                room='Classroom 1', source='Isolated test fixture'))
        self.user = User(username='supplied', full_name='Vaishnavi Vijay Kale',
            email='supplied@example.test', role='student', gender='Female')
        self.user.set_password('Existing@123')
        curriculum = self.curricula['BCA']
        self.student = Student(user=self.user, course=curriculum.course, curriculum=curriculum,
            enrollment_number='FORM-28', semester=5, admission_year=2026, gender='Female',
            mobile_number='0000000028', date_of_birth=date(2005, 2, 3),
            address='Supplied address', practical_batch='A', record_source='provided')
        db.session.add(self.student)
        db.session.flush()
        subject = self.subjects[('BCA', 5)]
        self.attendance = Attendance(student=self.student, subject=subject, faculty=self.faculty,
            attendance_date=date(2026, 6, 15), session_number=1, status='Late', remarks='Teacher entered',
            recorded_by_user_id=staff_user.id)
        self.marks = Marks(student=self.student, subject=subject, entered_by=self.faculty.id,
            exam_type='Internal', internal_marks=21, external_marks=30, total_marks=51, grade='C',
            remarks='Saved by the teacher')
        self.assignment = Assignment(subject=subject, faculty=self.faculty, title='Existing teacher task',
            description='Keep the teacher task', due_date=datetime(2026, 9, 30), maximum_marks=25,
            created_at=datetime(2026, 9, 1))
        self.submission = Submission(student=self.student, assignment=self.assignment,
            status='Submitted', submitted_at=datetime(2026, 9, 25), submitted_file='supplied.txt')
        (Path(self.directory.name) / 'supplied.txt').write_text('Original student work', encoding='utf8')
        self.material = StudyMaterial(subject=subject, faculty=self.faculty, title='Existing notes',
            file_name='supplied.txt', file_path='supplied.txt', file_type='txt')
        db.session.add_all([self.attendance, self.marks, self.assignment, self.submission, self.material])
        db.session.commit()
        self.accounts = [{'password': 'Existing@123'}]

    def cleanup_database(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def prepare(self):
        return prepare_project_cohort(self.accounts, year=2026, through=date(2026, 10, 6))

    def test_generation_preserves_current_work_and_is_repeatable(self):
        original = (self.user.password_hash, self.attendance.id, self.attendance.created_at,
                    self.attendance.status, self.marks.id, self.marks.total_marks, self.marks.grade,
                    self.marks.updated_at, self.submission.status, self.submission.submitted_at)
        summary = self.prepare()
        db.session.commit()
        self.assertEqual(summary['students_added'], 8)
        self.assertEqual(Student.query.count(), 9)
        self.assertEqual((self.user.password_hash, self.attendance.id, self.attendance.created_at,
                    self.attendance.status, self.marks.id, self.marks.total_marks, self.marks.grade,
                    self.marks.updated_at, self.submission.status, self.submission.submitted_at), original)
        self.assertEqual((self.student.admission_year, self.student.address, self.student.record_source),
                         (2026, 'Supplied address', 'provided'))
        self.assertEqual((Path(self.directory.name) / 'supplied.txt').read_text(), 'Original student work')
        generated = Student.query.filter(Student.id != self.student.id).all()
        self.assertTrue(all(row.gender == 'Female' and row.user.gender == 'Female' for row in generated))
        self.assertEqual(len({row.user.full_name for row in generated}), 8)
        passwords = [row['password'] for row in summary['accounts']]
        self.assertEqual(len(set(passwords)), 8)
        for account in summary['accounts']:
            self.assertTrue(db.session.get(User, account['id']).check_password(account['password']))
        before = tuple(model.query.count() for model in
            (User, Student, Attendance, Marks, Assignment, Submission, StudyMaterial, AcademicYearRecord))
        again = self.prepare()
        db.session.commit()
        after = tuple(model.query.count() for model in
            (User, Student, Attendance, Marks, Assignment, Submission, StudyMaterial, AcademicYearRecord))
        self.assertEqual(before, after)
        self.assertEqual((again['students_added'], again['accounts']), (0, []))

    def test_attendance_and_past_year_records_have_valid_scope_and_totals(self):
        self.prepare()
        generated = Student.query.filter(Student.id != self.student.id).all()
        for student in generated:
            records = Attendance.query.filter_by(student_id=student.id).all()
            per_day = Counter(row.attendance_date for row in records)
            self.assertTrue(records)
            self.assertTrue(all(count == 5 for count in per_day.values()))
            self.assertTrue(all(date(2026,6,15) <= day <= date(2026,10,6) and day.weekday() < 6
                                and day not in {date(2026,8,15), date(2026,10,2)} for day in per_day))
            rate = sum(row.status == 'Present' for row in records) * 100 / len(records)
            self.assertGreaterEqual(round(rate, 1), 90)
            self.assertLessEqual(round(rate, 1), 98)
            for row in records:
                self.assertEqual(row.subject.course_id, student.course_id)
                self.assertEqual(row.subject.semester, student.semester)
                self.assertIsNone(row.recorded_by_user_id)
                self.assertIsNone(row.updated_by_user_id)
            for marks in Marks.query.filter_by(student_id=student.id).all():
                self.assertGreaterEqual(marks.total_marks, 0)
                self.assertLessEqual(marks.total_marks, marks.subject.maximum_marks)
                self.assertIsNone(marks.grade)
                self.assertEqual(marks.result_status, 'Pending verification')
            for submission in Submission.query.filter_by(student_id=student.id).all():
                self.assertEqual(submission.status, 'Graded')
                self.assertLessEqual(submission.marks_obtained, submission.assignment.maximum_marks)
                self.assertLessEqual(submission.assignment.created_at.replace(tzinfo=None),
                                     submission.submitted_at.replace(tzinfo=None))
                self.assertLessEqual(submission.submitted_at.replace(tzinfo=None),
                                     submission.graded_at.replace(tzinfo=None))
                self.assertTrue((Path(self.directory.name) / submission.submitted_file).is_file())
        for student in Student.query.all():
            archives = AcademicYearRecord.query.filter_by(student_id=student.id).all()
            study_year = (student.semester+1)//2
            self.assertEqual(len(archives), study_year-1)
            for archive in archives:
                result = summarize_history(archive.snapshot)
                self.assertEqual(result['attendance']['held'], 900)
                self.assertGreaterEqual(result['attendance']['percentage'], 90)
                self.assertLessEqual(result['attendance']['percentage'], 98)
                self.assertEqual(result['assignments_completed'], result['assignments_total'])
                self.assertEqual(archive.source_kind, 'project_prepared')
                self.assertTrue(archive.provenance)
                self.assertNotIn('sgpa', archive.snapshot)
                for term in archive.snapshot['semesters']:
                    self.assertEqual(sum(row['attendance']['held'] for row in term['subjects']), 450)
                    for subject in term['subjects']:
                        for marks in subject['assessments']:
                            self.assertLessEqual(marks['internal_marks']+marks['external_marks'], marks['maximum_marks'])

    def test_unapproved_nep_history_does_not_claim_an_official_pass_result(self):
        self.prepare()
        for archive in AcademicYearRecord.query.all():
            for term in summarize_history(archive.snapshot)['snapshot']['semesters']:
                for subject in term['subjects']:
                    for assessment in subject['assessments']:
                        self.assertIsNone(assessment['passing_marks'])
                        self.assertEqual(assessment['result'], 'Pending assessment rules')
                        self.assertEqual(assessment['exam_type'], 'Practice Assessment')

    def test_existing_archive_is_preserved(self):
        existing = {'semesters':[{'semester':1, 'subjects':[{
            'code':'ARCHIVED-1', 'name':'Preserved college register',
            'attendance':{'held':12,'present':10,'late':1,'absent':1},
            'assessments':[], 'assignments':[]}]}]}
        archive = upsert_academic_history(self.student, 2024, 1, existing, current_year=2026)
        db.session.commit()
        original = (archive.id, deepcopy(archive.snapshot), archive.updated_at)
        self.prepare()
        self.assertEqual((archive.id, archive.snapshot, archive.updated_at), original)

    def test_future_and_nonlocal_generation_are_rejected_before_mutation(self):
        before = Student.query.count()
        for invalid_end in (date(2026,10,7), date(2026,6,14)):
            with self.assertRaises(ValueError):
                prepare_project_cohort(self.accounts, year=2026, through=invalid_end)
            self.assertEqual(Student.query.count(), before)
        for config in [{'IS_PRODUCTION':True}, {'IS_PRODUCTION':False, 'DEMO_MODE':False}]:
            self.app.config.update(config)
            with self.assertRaises(ValueError):
                self.prepare()
            self.assertEqual(Student.query.count(), before)
