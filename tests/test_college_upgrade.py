"""Programme isolation, verified curricula and real-record workflows."""
from datetime import timedelta
from io import BytesIO
from unittest import TestCase
from werkzeug.security import generate_password_hash
from app import create_app
from app.extensions import db
from app.models import (User, Student, Faculty, Course, Curriculum, CurriculumSubject,
                        SyllabusDocument, Subject, Marks, Notification, CampusActivity,
                        ActivityParticipation, RecordImport)
from app.activities.routes import now_ist
from app.services.college_setup import sync_college
from app.services.roster import encode_roster
from app.services.faculty import assigned_students
from app.services.student import student_subjects
from app.services.marks import validate_marks, save_bulk_marks
from app.services.dashboard import average_marks
from app.services.notifications import visible_notifications_for_user


class CollegeUpgradeTest(TestCase):
    password_hash = generate_password_hash('PrivateTest@123')

    def setUp(self):
        self.app = create_app('testing')
        self.app.config['SUPABASE_AUTH_ENABLED'] = False
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            sync_college()
            for name, role, scope in [('admin','admin','administrator'), ('principal','admin','principal'),
                                      ('office','admin','office'), ('teacher','faculty','office'),
                                      ('otherteacher','faculty','office'), ('bca','student','office'),
                                      ('hs','student','office'), ('otherbca','student','office')]:
                db.session.add(User(username=name, email=name+'@example.test', full_name=name.title(), role=role,
                                    admin_scope=scope, password_hash=self.password_hash))
            db.session.flush()
            for name in ['teacher', 'otherteacher']:
                db.session.add(Faculty(user=User.query.filter_by(username=name).one(), employee_id=name, department='BCA'))
            for name,code,semester in [('bca','BCA',1),('hs','BSC-FSN',1),('otherbca','BCA',2)]:
                c=Course.query.filter_by(code=code).one()
                curriculum=Curriculum.query.filter_by(course_id=c.id).one()
                db.session.add(Student(user=User.query.filter_by(username=name).one(), enrollment_number=name,
                                       course=c,curriculum=curriculum,semester=semester,admission_year=2024))
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, name):
        self.client.post('/auth/logout')
        slug = 'student/bca' if name in ('bca','otherbca') else 'student/home-science' if name=='hs' else 'staff' if name.endswith('teacher') else 'administration'
        response=self.client.post('/login/'+slug,data={'username_or_email':name+'@example.test','password':'PrivateTest@123'})
        self.assertEqual(response.status_code,302)

    def test_department_login_rejects_other_programme_and_preserves_destination(self):
        chooser=self.client.get('/login/student?next=/student/marks')
        self.assertIn(b'/login/student/bca?next=/student/marks',chooser.data)
        for name, slug in [('hs','bca'),('bca','home-science')]:
            response=self.client.post('/login/student/'+slug,data={'username_or_email':name+'@example.test','password':'PrivateTest@123'})
            self.assertIn(b'Invalid username/email or password',response.data)
            with self.client.session_transaction() as session:self.assertNotIn('_user_id',session)
        self.assertEqual(self.client.get('/login/student/invalid').status_code,404)
        self.login('hs')
        redirect=self.client.get('/student/syllabus')
        self.assertIn('/academics/home-science',redirect.location)
        self.assertIn('programme=BSC-FSN',redirect.location)

    def test_public_catalogue_sources_drafts_and_year_validation(self):
        for path in ['/','/about','/about/faculty','/contact','/academics','/academics/bca','/academics/home-science','/activities','/login/student']:
            self.assertEqual(self.client.get(path).status_code,200,path)
        with self.app.app_context():
            draft=CurriculumSubject.query.filter_by(is_verified=False).first()
            self.assertEqual(self.client.get(f'/academics/subject/{draft.id}').status_code,404)
            item=CurriculumSubject.query.filter_by(code='CA-101-T').one()
            self.assertIn(b'Internal maximum',self.client.get(f'/academics/subject/{item.id}').data)
        self.assertIn(b'Published structure',self.client.get('/academics/bca?year=3').data)
        self.assertIn(b'awaiting',self.client.get('/academics/home-science?year=3').data)
        for query in ['year=4','year=hello','year=1&semester=6','programme=UNKNOWN']:
            self.assertIn(self.client.get('/academics/bca?'+query).status_code,[400,404])
        self.assertEqual(self.client.get('/admin/missing-page').status_code,404)

    def test_sync_is_idempotent_and_preserves_office_edits(self):
        with self.app.app_context():
            n=CurriculumSubject.query.count()
            doc=SyllabusDocument.query.first();doc.notes='Office verified revised document'
            item=CurriculumSubject.query.first();item.units='Office learning outline'
            db.session.commit();sync_college()
            self.assertEqual(CurriculumSubject.query.count(),n)
            self.assertEqual(doc.notes,'Office verified revised document')
            self.assertEqual(item.units,'Office learning outline')
            self.assertEqual(Curriculum.query.count(),3)
            self.assertEqual(SyllabusDocument.query.count(),9)

    def test_reviewed_document_requires_a_source_url(self):
        self.login('office')
        with self.app.app_context():
            doc_id = SyllabusDocument.query.filter_by(year=3, status='pending').first().id
        path = f'/admin/curriculum/document/{doc_id}'
        data = {'title': 'College syllabus', 'source_url': '', 'notes': 'Awaiting college PDF'}
        for status in ['reference', 'structure', 'verified']:
            response = self.client.post(path, data={**data, 'status': status})
            self.assertIn(b'Add the source URL', response.data)
            with self.app.app_context():
                self.assertEqual(db.session.get(SyllabusDocument, doc_id).status, 'pending')
        self.assertEqual(self.client.post(path, data={**data, 'status': 'pending'}).status_code, 302)

    def test_principal_read_only_and_office_cannot_create_privileged_accounts(self):
        self.login('principal')
        for path in ['/admin/dashboard','/admin/curriculum','/admin/students','/admin/reports']:
            self.assertEqual(self.client.get(path).status_code,200,path)
        for path in ['/admin/students/new','/admin/courses/new','/admin/records/import','/admin/access','/campus/activities/new']:
            self.assertEqual(self.client.get(path).status_code,403,path)
        with self.app.app_context():
            doc_id=SyllabusDocument.query.first().id
        self.assertEqual(self.client.post(f'/admin/curriculum/document/{doc_id}',data={}).status_code,403)
        self.login('office')
        self.assertEqual(self.client.get('/admin/access').status_code,403)
        self.assertEqual(self.client.get('/admin/records/import').status_code,200)

    def test_access_form_creates_correct_scope_and_rejects_escalation(self):
        self.login('admin')
        data={'full_name':'College Principal','username':'newprincipal','email':'new@example.test','password':'PrivateTest@123','admin_scope':'administrator'}
        self.client.post('/admin/access',data=data)
        with self.app.app_context():self.assertIsNone(User.query.filter_by(username='newprincipal').first())
        data['admin_scope']='principal'
        self.assertEqual(self.client.post('/admin/access',data=data).status_code,302)
        with self.app.app_context():
            user=User.query.filter_by(username='newprincipal').one()
            self.assertEqual(user.admin_scope,'principal');self.assertTrue(user.check_password(data['password']))

    def test_roster_preview_owner_atomic_duplicates_and_activation(self):
        self.login('office')
        row={'full_name':'Official Student','username':'official','email':'official@example.test','enrollment_number':'REAL001','programme':'BSC-FSN','pattern':'2024 NEP','semester':'1','admission_year':'2024'}
        raw=encode_roster([row], 'students')
        response=self.client.post('/admin/records/import',data={'kind':'students','file':(BytesIO(raw),'roster.csv')})
        self.assertEqual(response.status_code,302)
        preview=response.location
        with self.app.app_context():
            self.assertIsNone(User.query.filter_by(username='official').first())
            self.assertEqual(RecordImport.query.count(),1)
        self.assertIn(b'Official Student',self.client.get(preview).data)
        self.login('admin');self.assertEqual(self.client.get(preview).status_code,404)
        self.login('office');self.assertEqual(self.client.post(preview).status_code,302)
        with self.app.app_context():
            user=User.query.filter_by(username='official').one()
            self.assertFalse(user.is_active)
            self.assertEqual(user.student_profile.curriculum.pattern,'2024 NEP')
            self.assertEqual(RecordImport.query.count(),0)
        self.assertEqual(self.client.post(preview).status_code,404)
        valid=dict(row,username='second',email='second@example.test',enrollment_number='REAL002')
        response=self.client.post('/admin/records/import',data={'kind':'students','file':(BytesIO(encode_roster([valid,row],'students')),'duplicate.csv')})
        self.assertIn(b'already exists',response.data)
        with self.app.app_context():self.assertIsNone(User.query.filter_by(username='second').first())

    def test_roster_revalidation_catches_race_without_partial_writes(self):
        self.login('office')
        row={'full_name':'Teacher','username':'newstaff','email':'staff@example.test','employee_id':'T001','department':'Home Science','qualification':'M.Sc.'}
        preview=self.client.post('/admin/records/import',data={'kind':'staff','file':(BytesIO(encode_roster([row],'staff')),'staff.csv')}).location
        with self.app.app_context():
            db.session.add(User(username='newstaff',email='different@example.test',full_name='Existing',role='faculty',password_hash=self.password_hash));db.session.commit()
        self.client.post(preview)
        with self.app.app_context():self.assertIsNone(Faculty.query.filter_by(employee_id='T001').first())

    def test_faculty_exact_assignment_and_curriculum_isolation(self):
        with self.app.app_context():
            teacher=Faculty.query.filter_by(employee_id='teacher').one()
            bca=Student.query.filter_by(enrollment_number='bca').one();hs=Student.query.filter_by(enrollment_number='hs').one()
            other=Student.query.filter_by(enrollment_number='otherbca').one()
            db.session.add_all([Subject(code='FIRST',name='First',course_id=bca.course_id,curriculum_id=bca.curriculum_id,semester=1,faculty=teacher),
                                Subject(code='SECOND',name='Second',course_id=hs.course_id,curriculum_id=hs.curriculum_id,semester=2,faculty=teacher)])
            db.session.commit()
            self.assertEqual([s.id for s in assigned_students(teacher)],[bca.id])
            self.assertEqual([s.code for s in student_subjects(bca)],['FIRST'])
            self.assertEqual(student_subjects(other),[])
            bca.curriculum_id=None;db.session.commit()
            self.assertEqual(assigned_students(teacher),[])

    def test_nep_assessment_bounds_ownership_and_weighted_average(self):
        with self.app.app_context():
            bca=Student.query.filter_by(enrollment_number='bca').one();hs=Student.query.filter_by(enrollment_number='hs').one()
            teacher=Faculty.query.filter_by(employee_id='teacher').one()
            item=CurriculumSubject.query.filter_by(code='CA-101-T').one()
            subject=Subject(code=item.code,name=item.name,course=bca.course,curriculum=bca.curriculum,curriculum_subject=item,semester=1,maximum_marks=50,passing_marks=20,faculty=teacher)
            db.session.add(subject);db.session.commit()
            self.assertFalse(validate_marks(16,10,subject)[0])
            self.assertFalse(validate_marks(10,36,subject)[0])
            created,_,errors=save_bulk_marks(teacher,subject,'Semester Exam',[{'student_id':hs.id,'internal_marks':10,'external_marks':30}])
            self.assertEqual(created,0);self.assertTrue(errors)
            self.assertIsNone(average_marks(bca.id))
            save_bulk_marks(teacher,subject,'Semester Exam',[{'student_id':bca.id,'internal_marks':10,'external_marks':30}]);db.session.commit()
            self.assertEqual(average_marks(bca.id),80)
            self.assertIsNone(Marks.query.one().grade)

    def test_notification_target_user_and_public_scope(self):
        with self.app.app_context():
            admin=User.query.filter_by(username='admin').one();bca=User.query.filter_by(username='bca').one();hs=User.query.filter_by(username='hs').one()
            db.session.add(Notification(title='PRIVATE NOTICE',message='Private',notification_type='General',creator=admin,target_role='all',target_user_id=hs.id))
            db.session.commit()
            self.assertEqual(visible_notifications_for_user(bca,bca.student_profile),[])
            self.assertEqual(len(visible_notifications_for_user(hs,hs.student_profile)),1)
        self.assertNotIn(b'PRIVATE NOTICE',self.client.get('/').data)

    def test_activity_registration_review_and_certificate_ownership(self):
        with self.app.app_context():
            teacher=User.query.filter_by(username='teacher').one()
            item=CampusActivity(title='College workshop',description='Verified workshop',category='Workshop',department='bca',starts_at=now_ist()+timedelta(days=1),venue='College lab',coordinator_id=teacher.id)
            db.session.add(item);db.session.commit();activity_id=item.id
        self.login('hs');self.assertEqual(self.client.post(f'/activities/{activity_id}/register').status_code,403)
        self.login('bca')
        self.assertEqual(self.client.post(f'/activities/{activity_id}/register').status_code,302)
        self.client.post(f'/activities/{activity_id}/register')
        with self.app.app_context():
            self.assertEqual(ActivityParticipation.query.count(),1);row_id=ActivityParticipation.query.one().id
        cert=f'/activities/participation/{row_id}/certificate'
        self.assertEqual(self.client.get(cert).status_code,404)
        self.client.post(f'/activities/{activity_id}/evidence',data={'evidence':'Completed practical work'})
        self.login('otherteacher')
        self.assertEqual(self.client.get(f'/campus/activities/{activity_id}/participants').status_code,403)
        self.login('teacher')
        payload={'participation_id':row_id,'status':'Completed','hours':'2'}
        self.client.post(f'/campus/activities/{activity_id}/participants',data=payload)
        with self.app.app_context():
            self.assertEqual(db.session.get(ActivityParticipation,row_id).status,'Registered')
            db.session.get(CampusActivity,activity_id).starts_at=now_ist()-timedelta(days=1);db.session.commit()
        self.assertEqual(self.client.post(f'/campus/activities/{activity_id}/participants',data=payload).status_code,302)
        self.login('bca');self.assertEqual(self.client.get(cert).status_code,200)
        self.assertEqual(self.client.post(f'/activities/{activity_id}/evidence',data={'evidence':'Changed'}).status_code,400)
        self.login('otherbca');self.assertEqual(self.client.get(cert).status_code,403)

    def test_new_forms_csrf_and_inactive_session(self):
        self.login('admin')
        self.app.config['WTF_CSRF_ENABLED']=True
        self.assertEqual(self.client.post('/admin/access',data={}).status_code,400)
        self.assertEqual(self.client.post('/admin/records/import',data={}).status_code,400)
        self.app.config['WTF_CSRF_ENABLED']=False
        with self.app.app_context():
            User.query.filter_by(username='admin').one().is_active=False;db.session.commit()
        response=self.client.get('/admin/records/import')
        self.assertEqual(response.status_code,302)
        with self.client.session_transaction() as session:self.assertNotIn('_user_id',session)

    def test_teaching_subject_setup_and_marks_form_keep_unknown_scores_pending(self):
        self.login('admin')
        with self.app.app_context():
            item=CurriculumSubject.query.filter_by(code='CA-101-T').one()
            teacher=Faculty.query.filter_by(employee_id='teacher').one()
            student=Student.query.filter_by(enrollment_number='bca').one()
            student_id=student.id
            data={'name':item.name,'code':item.code,'course_id':item.curriculum.course_id,
                  'curriculum_id':item.curriculum_id,'curriculum_subject_id':item.id,'semester':'1',
                  'faculty_id':teacher.id,'maximum_marks':'50','passing_marks':'20','is_active':'y'}
            home_curr=Curriculum.query.join(Curriculum.course).filter(Course.code=='BSC-FSN').one().id
            catalogue_id=item.id
        self.assertEqual(self.client.get(f'/admin/subjects/new?catalogue={catalogue_id}').status_code,200)
        wrong=dict(data,curriculum_id=home_curr)
        self.assertEqual(self.client.post('/admin/subjects/new',data=wrong).status_code,200)
        with self.app.app_context():self.assertEqual(Subject.query.count(),0)
        self.assertEqual(self.client.post('/admin/subjects/new',data=data).status_code,302)
        with self.app.app_context():subject_id=Subject.query.one().id
        self.login('teacher')
        page=self.client.get(f'/faculty/marks?subject_id={subject_id}')
        self.assertIn(b'placeholder="Pending"',page.data)
        base={'subject_id':subject_id,'exam_type':'Semester Exam'}
        self.client.post('/faculty/marks',data=base)
        with self.app.app_context():self.assertEqual(Marks.query.count(),0)
        self.client.post('/faculty/marks',data=dict(base,**{f'internal_{student_id}':'10',f'external_{student_id}':'30'}))
        with self.app.app_context():self.assertEqual(Marks.query.one().total_marks,40)
        self.client.post('/faculty/marks',data=dict(base,**{f'internal_{student_id}':'16',f'external_{student_id}':'20'}))
        with self.app.app_context():self.assertEqual(Marks.query.one().total_marks,40)

    def test_faculty_notifications_match_the_assigned_department(self):
        with self.app.app_context():
            teacher=User.query.filter_by(username='teacher').one();admin=User.query.filter_by(username='admin').one()
            bca=Course.query.filter_by(code='BCA').one();hs=Course.query.filter_by(code='BSC-FSN').one()
            db.session.add(Subject(name='Assigned',code='NOTICE',course=bca,semester=1,faculty=teacher.faculty_profile))
            db.session.add_all([Notification(title='BCA team',message='Notice',notification_type='General',creator=admin,target_role='faculty',target_course_id=bca.id),
                                Notification(title='Home Science team',message='Notice',notification_type='General',creator=admin,target_role='faculty',target_course_id=hs.id)])
            db.session.commit()
            self.assertEqual([x['notification'].title for x in visible_notifications_for_user(teacher,teacher.faculty_profile)],['BCA team'])
