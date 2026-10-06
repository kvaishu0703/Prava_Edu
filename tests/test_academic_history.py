"""Academic-year archives stay separate and respect student/class scope."""
from copy import deepcopy
from datetime import date
from unittest import TestCase
from flask import g
from app import create_app
from app.extensions import db
from app.models import Attendance, Course, Curriculum, Faculty, Marks, Student, Subject, User
from app.models.academic_history import AcademicYearRecord
from app.models.class_teacher import ClassTeacherAssignment
from app.services.academic_history import (
    academic_history_view, academic_year_plan, normalize_history_snapshot,
    summarize_history, upsert_academic_history,
)
from app.services.academic_history_schema import upgrade_academic_history_schema


class AcademicHistoryTests(TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config.update(SUPABASE_AUTH_ENABLED=False, DEMO_MODE=True)
        @self.app.before_request
        def reset_user_cache():
            g.pop('_login_user', None)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.users = {}
        for username, role in [('admin', 'admin'), ('mentor', 'faculty'), ('subject', 'faculty'), ('outsider', 'faculty'), ('student', 'student'), ('other', 'student')]:
            user = User(username=username, full_name=username.title()+' Account', email=username+'@example.test', role=role)
            user.set_password('History@123')
            self.users[username] = user
        self.course = Course(code='BCA', name='Computer Applications', duration='3 years', total_semesters=6)
        self.curriculum = Curriculum(course=self.course, pattern='2024 NEP', effective_year=2024)
        self.faculty = {key: Faculty(user=self.users[key], employee_id=key, department='BCA') for key in ['mentor','subject','outsider']}
        self.student = Student(user=self.users['student'], enrollment_number='TY28', course=self.course,
            curriculum=self.curriculum, semester=5, admission_year=2026)
        self.other = Student(user=self.users['other'], enrollment_number='FY11', course=self.course,
            curriculum=self.curriculum, semester=1, admission_year=2026)
        self.subject = Subject(course=self.course, curriculum=self.curriculum, semester=5,
            name='Assigned subject', code='PUBLIC', faculty=self.faculty['subject'])
        db.session.add_all([*self.users.values(), *self.faculty.values(), self.student, self.other, self.subject])
        db.session.flush()
        self.assignment = ClassTeacherAssignment(course_id=self.course.id, curriculum_id=self.curriculum.id,
            semester=5, academic_year=2026, faculty_id=self.faculty['mentor'].id, assigned_by_id=self.users['admin'].id)
        db.session.add(self.assignment)
        db.session.commit()
        self.client = self.app.test_client()
        self.snapshot = {'semesters': [{'semester':1, 'subjects': [
            {'code':'PUBLIC', 'name':'Visible archived subject',
             'attendance': {'held':100,'present':90,'late':5,'absent':5},
             'assessments': [{'exam_type':'Semester','internal_marks':25,'external_marks':50,'maximum_marks':100,'passing_marks':40}],
             'assignments': [{'title':'Coursework completed','status':'Graded','score':18,'maximum':20,
                              'due_date':'2024-09-05','submitted_date':'2024-09-01'}]},
            {'code':'PRIVATE', 'name':'Other teacher confidential subject',
             'attendance': {'held':50,'present':30,'late':0,'absent':20},
             'assessments': [{'exam_type':'Semester','internal_marks':10,'external_marks':20,'maximum_marks':100,'passing_marks':40}],
             'assignments': [{'title':'Restricted assignment','status':'Pending','score':None,'maximum':20}]}]}]}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def archive(self):
        record = upsert_academic_history(self.student, 2024, 1, self.snapshot, actor=self.users['admin'], current_year=2026)
        db.session.commit()
        return record

    def login(self, username):
        role = self.users[username].role
        path = {'student':'/login/student/bca', 'faculty':'/login/staff', 'admin':'/login/administration'}[role]
        self.assertEqual(self.client.post(path, data={'username_or_email':username, 'password':'History@123'}).status_code,302)

    def test_year_plan_follows_semester_without_changing_supplied_admission_year(self):
        self.assertEqual([row['academic_year'] for row in academic_year_plan(self.student,2026)], [2026,2025,2024])
        self.student.semester = 3
        self.assertEqual([row['academic_year'] for row in academic_year_plan(self.student,2026)], [2026,2025])
        self.student.semester = 1
        self.assertEqual([row['academic_year'] for row in academic_year_plan(self.student,2026)], [2026])
        self.assertEqual(self.student.admission_year,2026)

    def test_upsert_is_repeatable_and_preserves_current_attendance_and_marks(self):
        attendance = Attendance(student=self.student, subject=self.subject, faculty=self.faculty['subject'],
                                attendance_date=date(2026,10,6), status='Present')
        db.session.add(attendance)
        marks = Marks(student=self.student, subject=self.subject, entered_by=self.faculty['subject'].id,
                      exam_type='Internal', internal_marks=25, external_marks=0, total_marks=25)
        db.session.add_all([attendance,marks])
        db.session.commit()
        original = (attendance.id, attendance.created_at, marks.id, marks.updated_at)
        first = self.archive()
        again = self.archive()
        self.assertEqual(first.id,again.id)
        self.assertEqual(AcademicYearRecord.query.count(),1)
        self.assertEqual((Attendance.query.count(), Marks.query.count()),(1,1))
        self.assertEqual((attendance.id, attendance.created_at, marks.id, marks.updated_at),original)
        self.assertEqual((marks.total_marks,attendance.status),(25,'Present'))

    def test_current_year_and_unrelated_previous_year_cannot_be_archived(self):
        for year, study in [(2026,3),(2023,1),(2025,1)]:
            with self.assertRaises(ValueError):
                upsert_academic_history(self.student,year,study,self.snapshot,current_year=2026)
        self.assertEqual(AcademicYearRecord.query.count(),0)

    def test_counts_scores_dates_and_semesters_are_validated(self):
        changes = [
            lambda row: row['semesters'][0]['subjects'][0]['attendance'].update(held=101),
            lambda row: row['semesters'][0]['subjects'][0]['assessments'][0].update(external_marks=100),
            lambda row: row['semesters'][0]['subjects'][0]['assessments'][0].update(internal_marks=float('nan')),
            lambda row: row['semesters'][0]['subjects'][0]['assignments'][0].update(due_date='2026-09-01'),
            lambda row: row['semesters'][0].update(semester=5),
        ]
        for change in changes:
            bad = deepcopy(self.snapshot)
            change(bad)
            with self.assertRaises(ValueError):
                normalize_history_snapshot(bad,2024,1)

    def test_weighted_history_totals_and_no_fabricated_grade_or_sgpa(self):
        source = deepcopy(self.snapshot)
        source['sgpa'] = 9.5
        source['semesters'][0]['subjects'][0]['assessments'][0]['grade'] = 'A+'
        normalized = normalize_history_snapshot(source,2024,1)
        result = summarize_history(normalized)
        self.assertEqual(result['attendance']['percentage'],83.3)
        self.assertEqual(result['marks_percentage'],52.5)
        self.assertEqual((result['assignments_completed'],result['assignments_total']),(1,2))
        self.assertNotIn('sgpa',normalized)
        self.assertNotIn('grade',normalized['semesters'][0]['subjects'][0]['assessments'][0])

    def test_history_is_student_owned_and_subject_faculty_totals_are_filtered(self):
        self.archive()
        own = academic_history_view(self.users['student'],self.student,2024,2026)
        self.assertEqual(own['summary']['subject_count'],2)
        with self.assertRaises(PermissionError):
            academic_history_view(self.users['other'],self.student,2024,2026)
        teacher = academic_history_view(self.users['subject'],self.student,2024,2026)
        self.assertEqual(teacher['summary']['subject_count'],1)
        self.assertEqual(teacher['summary']['attendance']['percentage'],95.0)
        self.assertEqual(teacher['summary']['marks_percentage'],75.0)
        self.assertNotIn('Other teacher confidential subject',str(teacher['summary']))
        with self.assertRaises(PermissionError):
            academic_history_view(self.users['outsider'],self.student,2024,2026)

    def test_current_mentor_can_read_history_but_old_or_revoked_assignment_cannot(self):
        self.archive()
        self.assertEqual(academic_history_view(self.users['mentor'],self.student,2024,2026)['summary']['subject_count'],2)
        self.assignment.academic_year = 2025
        db.session.commit()
        with self.assertRaises(PermissionError):
            academic_history_view(self.users['mentor'],self.student,2024,2026)

    def test_archive_source_requires_permission_and_local_generated_history_stays_local(self):
        with self.assertRaises(PermissionError):
            upsert_academic_history(self.student,2024,1,self.snapshot,actor=self.users['student'],current_year=2026)
        with self.assertRaises(PermissionError):
            upsert_academic_history(self.student,2024,1,self.snapshot,source_kind='college_register',current_year=2026)
        self.app.config['IS_PRODUCTION'] = True
        with self.assertRaises(ValueError):
            upsert_academic_history(self.student,2024,1,self.snapshot,actor=self.users['admin'],current_year=2026)

    def test_schema_upgrade_is_additive_and_repeatable(self):
        self.archive()
        upgrade_academic_history_schema()
        upgrade_academic_history_schema()
        self.assertEqual(AcademicYearRecord.query.count(),1)
        self.assertEqual(Student.query.count(),2)

    def test_history_routes_are_read_only_and_current_year_links_to_live_records(self):
        self.archive()
        self.login('student')
        current = self.client.get('/student/academic-history')
        self.assertEqual(current.status_code,200)
        self.assertIn(b'/student/attendance?year=2026',current.data)
        self.assertIn(b'/student/marks',current.data)
        old = self.client.get('/student/academic-history?year=2024')
        self.assertEqual(old.status_code,200)
        self.assertIn(b'Visible archived subject',old.data)
        self.assertIn(b'Coursework completed',old.data)
        self.assertNotIn(b'Record source and audit',old.data)
        self.assertEqual(self.client.post('/student/academic-history?year=2024').status_code,405)
        self.assertEqual(self.client.get('/student/academic-history?year=2023').status_code,404)
        self.login('subject')
        scoped = self.client.get(f'/campus/students/{self.student.id}/history?year=2024')
        self.assertEqual(scoped.status_code,200)
        self.assertNotIn(b'Other teacher confidential subject',scoped.data)
        self.login('outsider')
        self.assertEqual(self.client.get(f'/campus/students/{self.student.id}/history?year=2024').status_code,403)
        self.login('admin')
        admin = self.client.get(f'/campus/students/{self.student.id}/history?year=2024')
        self.assertEqual(admin.status_code,200)
        self.assertIn(b'Record source and audit',admin.data)
