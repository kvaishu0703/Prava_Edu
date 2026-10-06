"""Explicit local presentation preparation; never run at application startup."""
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
import random
import secrets
from flask import current_app
from app.extensions import db
from app.models import (ActivityParticipation, Assignment, Attendance, CampusActivity, Course,
                        Curriculum, Marks, Student, StudyMaterial, Subject, Submission, User)
from app.models.academic_history import AcademicYearRecord
from app.models.base import utc_now
from app.services.academic_history import academic_year_plan, upsert_academic_history
from app.services.project_calendar import ORIGIN
from app.services.student import student_subjects
from app.services.timetable import student_slots, college_today

PROVENANCE = 'Owner-requested illustrative college-project data; not official college results or submitted student work.'
TARGETS = {'BCA': (25, 27, 28), 'BSC-FSN': (13, 14, 14), 'BSC-TEXTILE': (12, 13, 14)}
FIRST_NAMES = ('Aarohi Anvi Avani Ananya Advika Aaradhya Amruta Anushka Anuja Ankita Akanksha '
    'Asmita Ashwini Bhagyashree Bhavana Chaitali Charuta Deepali Dhanashri Dipti Disha Dnyanada '
    'Dnyaneshwari Durva Eesha Gauri Gayatri Geetanjali Harshada Harshita Isha Ishwari Janhavi '
    'Jui Juilee Kalyani Kanika Kashmira Kasturi Kavya Ketaki Kirti Komal Kranti Madhavi Madhura '
    'Maithili Manasi Mansi Mayuri Medha Megha Mihika Mrinal Mukta Namrata Nandini Neha Nikita '
    'Nishigandha Pallavi Prachi Prajakta Pranali Pranjali Prarthana Pratiksha Preeti Priya Purva '
    'Rachana Radhika Rajashri Raksha Rasika Revati Rucha Ruchira Rujuta Rupali Rutuparna Saee '
    'Sakshi Samiksha Sampada Samruddhi Sanika Sanjana Sanskruti Sarika Sayali Sejal Shalaka '
    'Sharvari Shivani Shreya Shraddha Shravani Shruti Siddhi Smita Sneha Sonali Spruha Srushti '
    'Supriya Surabhi Swara Swarali Tanaya Tanvi Tejaswini Trupti Urmila Vaidehi Vaishali Vallari '
    'Vasudha Vedika Vibha Vidya Vijaya Vinaya Vrinda Vrushali Yashashri Yukta Yashasvi').split()
FATHERS = 'Prakash Suresh Anil Rajendra Vijay Ashok Sunil Sachin Mahesh Sanjay Deepak Nitin Umesh Ramesh Ganesh Santosh Ravindra Ajay Vikas Shashikant Vilas Sudhir Arun Dattatray Pravin Dilip Shrikant Vinod Rajesh Madhukar'.split()
SURNAMES = 'Deshmukh Patil Jadhav Shinde Pawar More Gawade Gaikwad Kale Kadam Kulkarni Joshi Deshpande Ghodke Sonawane Dhumal Wagh Shirke Shelke Salunkhe Chavan Bhosale Shitole Thorat Magar Bhalerao Karale Gite Kshirsagar Lonkar Nimbalkar Phadke Ranade Raut Sawant Shirsath Tamboli Utekar Vaidya Wankhede Zende Apte Dandekar Godbole Inamdar Kamat Lele Oak Paranjape Pathak Pingle Sathe Talekar Wakchaure Borhade Dahale Gholap Jagtap Kendre Londhe'.split()


def _file(relative, content):
    path = Path(current_app.config['UPLOAD_FOLDER']) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding='utf8')
    return relative


def _scores(subject, seed):
    rng = random.Random(seed)
    scheme = subject.curriculum_subject
    verified = bool(scheme and scheme.is_verified and scheme.internal_max is not None and scheme.external_max is not None)
    internal_max = scheme.internal_max if verified else round(subject.maximum_marks * .4)
    external_max = scheme.external_max if verified else subject.maximum_marks - internal_max
    return (round(internal_max * rng.uniform(.70,.95)), round(external_max * rng.uniform(.69,.96)),
            'Semester Exam' if verified else 'Practice Assessment')


def prepare_project_cohort(accounts, year=2026, through=date(2026,10,6)):
    """Return newly generated credentials; caller saves manifest and commits."""
    if current_app.config.get('IS_PRODUCTION') or not current_app.config.get('DEMO_MODE'):
        raise ValueError('Presentation records can only be prepared in local project mode.')
    if through > college_today():
        raise ValueError('Presentation attendance cannot extend into the future.')
    if through < date(year,6,15):
        raise ValueError('Attendance end date must be on or after the academic start date.')
    used_names = {user.full_name.casefold() for user in User.query.all()}
    used_passwords = {item['password'] for item in accounts}
    new_accounts, new_students = [], []
    name_index = 0
    for code, targets in TARGETS.items():
        curriculum = Curriculum.query.join(Course).filter(Course.code == code, Curriculum.pattern == '2024 NEP').one()
        prefix = {'BCA':'bca','BSC-FSN':'fsn','BSC-TEXTILE':'tex'}[code]
        for study_year, target in enumerate(targets, 1):
            count = Student.query.filter(Student.course_id == curriculum.course_id,
                Student.semester.in_([study_year*2-1, study_year*2])).count()
            if count > target:
                raise ValueError(f'{code} year {study_year} already exceeds target; existing records are preserved.')
            for number in range(count + 1, target + 1):
                while True:
                    index = name_index
                    name_index += 1
                    name = f'{FIRST_NAMES[index % len(FIRST_NAMES)]} {FATHERS[(index*7+3) % len(FATHERS)]} {SURNAMES[(index*11+5) % len(SURNAMES)]}'
                    if name.casefold() not in used_names:
                        used_names.add(name.casefold())
                        break
                username = f'{prefix}.{("fy","sy","ty")[study_year-1]}{number:02d}'
                if User.query.filter_by(username=username).first():
                    raise ValueError(f'Account ID {username} already exists outside this cohort.')
                password = 'Pva@' + ''.join(secrets.choice('23456789') for _ in range(6))
                while password in used_passwords:
                    password = 'Pva@' + ''.join(secrets.choice('23456789') for _ in range(6))
                used_passwords.add(password)
                user = User(username=username,full_name=name,email=username+'@prava.example',role='student',
                            gender='Female',is_active=True,is_demo=True)
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
                admission = year-study_year+1
                enrollment_sequence = number
                enrollment = f'PRV-{code}-{admission}-{enrollment_sequence:03d}'
                while Student.query.filter_by(enrollment_number=enrollment).first():
                    enrollment_sequence += 1
                    enrollment = f'PRV-{code}-{admission}-{enrollment_sequence:03d}'
                student = Student(user=user,course=curriculum.course,curriculum=curriculum,
                    enrollment_number=enrollment,semester=study_year*2-1,
                    admission_year=admission,gender='Female',record_source='generated',
                    mobile_number=f'00000{user.id:05d}',date_of_birth=date(admission-18,1+index%12,1+index%27),
                    practical_batch='ABC'[(number-1)%3] if code=='BCA' and study_year==3 else 'A',
                    address=f'At/Post Loni, Taluka Rahata, Ahilyanagar, Maharashtra - 413713')
                db.session.add(student)
                db.session.flush()
                new_students.append(student)
                new_accounts.append({'id':user.id,'username':username,'full_name':name,'role':'student',
                    'admin_scope':'office','is_demo':True,'semester':student.semester,'programme':code,
                    'department':None,'password':password,'is_active':True,'was_active':False,
                    'login_path':'/login/student/bca' if code=='BCA' else '/login/student/home-science'})
    start = date(year,6,15)
    holidays = {date(year,8,15),date(year,10,2)}
    days = [start+timedelta(days=i) for i in range((through-start).days+1)
            if (start+timedelta(days=i)).weekday()<6 and start+timedelta(days=i) not in holidays]
    for student in new_students:
        timetable = defaultdict(list)
        for slot in student_slots(student,year):
            timetable[slot.weekday].append(slot)
        if any(len(timetable[d]) != 5 for d in range(6)):
            raise ValueError(f'Missing five-session timetable for student {student.id}.')
        plan = [(day,slot) for day in days for slot in timetable[day.weekday()]]
        target = 90 + student.id % 9
        shuffled = list(range(len(plan)))
        random.Random(f'cohort-attendance-{student.id}').shuffle(shuffled)
        absent = set(shuffled[:round(len(plan)*(100-target)/100)])
        db.session.execute(db.insert(Attendance),[{'student_id':student.id,'subject_id':slot.subject_id,
            'faculty_id':slot.faculty_id,'attendance_date':day,'session_number':slot.session_number,
            'session_type':slot.session_type,'starts_at':slot.starts_at,'ends_at':slot.ends_at,
            'timetable_slot_id':slot.id,'status':'Absent' if index in absent else 'Present','remarks':ORIGIN}
            for index,(day,slot) in enumerate(plan)])
    # Reuse existing current records and add only missing records/coursework.
    for student in Student.query.join(Student.user).filter(User.is_active.is_(True)).all():
        # Complete unknown presentation fields only; supplied values remain intact.
        if not student.mobile_number:
            student.mobile_number = f'00000{student.user_id:05d}'
        if not student.date_of_birth:
            student.date_of_birth = date(year - 17 - (student.semester+1)//2, 1+student.id%12, 1+student.id%27)
        if not student.address:
            student.address = 'At/Post Loni, Taluka Rahata, Ahilyanagar, Maharashtra - 413713'
        if not student.practical_batch:
            student.practical_batch = 'A'
        student.user.gender = student.gender
        for subject in student_subjects(student):
            if not Marks.query.filter_by(student_id=student.id,subject_id=subject.id).first():
                internal,external,exam = _scores(subject,f'marks-{student.id}-{subject.id}')
                db.session.add(Marks(student=student,subject=subject,entered_by=subject.faculty_id,
                    exam_type=exam,internal_marks=internal,external_marks=external,total_marks=internal+external,
                    grade=None,remarks=PROVENANCE))
            assignment = Assignment.query.filter_by(subject_id=subject.id,is_active=True).first()
            if not assignment:
                assignment = Assignment(title=('Applied Coursework: '+subject.name)[:150],
                    description='Explain the concepts, document a worked example, observations, conclusion and references.',
                    subject=subject,faculty=subject.faculty,due_date=datetime(year,10,16,11,30),maximum_marks=20)
                db.session.add(assignment)
                db.session.flush()
            if not StudyMaterial.query.filter_by(subject_id=subject.id,is_active=True).first():
                relative = _file(f'materials/prava-cohort-notes-{subject.id}.txt',
                    subject.name+'\n\nLearning outline\n1. Define the key concepts.\n2. Work through an example.\n'
                    '3. Record observations and applications.\n4. Summarise findings and references.\n\n'+PROVENANCE+'\n')
                db.session.add(StudyMaterial(title=('Learning Notes: '+subject.name)[:150],subject=subject,
                    faculty=subject.faculty,description='Concept review and coursework preparation.',
                    file_name=Path(relative).name,file_path=relative,file_type='txt'))
            for task in Assignment.query.filter_by(subject_id=subject.id,is_active=True).all():
                if Submission.query.filter_by(assignment_id=task.id,student_id=student.id).first():
                    continue
                relative = _file(f'submissions/prava-cohort-{student.id}-{task.id}.txt',
                    f'{student.user.full_name}\n{subject.name}\n\nCoursework record\n'
                    'Objective: apply the course concepts in a structured example.\nMethod: review the topic, '
                    'record the procedure and analyse the observations.\nConclusion: compare the outcomes with '
                    'the stated objective and identify improvements.\n\n'+PROVENANCE+'\n')
                prepared_at = utc_now()
                db.session.add(Submission(student=student,assignment=task,submitted_file=relative,
                    submitted_at=prepared_at,status='Graded',marks_obtained=round(task.maximum_marks*(.75+(student.id%5)*.04)),
                    faculty_feedback='Completed coursework with a clear method and conclusion. Continue improving references.',
                    graded_at=prepared_at))
        for planned in academic_year_plan(student,current_year=year):
            if planned['is_current'] or AcademicYearRecord.query.filter_by(student_id=student.id,academic_year=planned['academic_year']).first():
                continue
            terms=[]
            for semester in (planned['study_year']*2-1, planned['study_year']*2):
                subjects=Subject.query.filter_by(curriculum_id=student.curriculum_id,semester=semester,is_active=True).order_by(Subject.id).all()
                if not subjects:
                    raise ValueError('Past-year subject catalogue is incomplete.')
                rows=[]
                for index,subject in enumerate(subjects):
                    held=450//len(subjects)+(index < 450%len(subjects))
                    absent=round(held*(2+(student.id+index)%9)/100)
                    internal,external,exam=_scores(subject,f'history-{student.id}-{subject.id}-{planned["academic_year"]}')
                    event_year=planned['academic_year']+(semester%2==0)
                    month=10 if semester%2 else 3
                    rows.append({'code':subject.code,'name':subject.name,
                        'attendance':{'held':held,'present':held-absent,'late':0,'absent':absent},
                        'assessments':[{'exam_type':exam,'internal_marks':internal,'external_marks':external,
                            'maximum_marks':subject.maximum_marks,'passing_marks':None}],
                        'assignments':[{'title':('Coursework: '+subject.name)[:150],'status':'Graded','score':15+(student.id+index)%5,
                            'maximum':20,'due_date':date(event_year,month,20).isoformat(),
                            'submitted_date':date(event_year,month,15).isoformat()}]})
                terms.append({'semester':semester,'subjects':rows})
            upsert_academic_history(student,planned['academic_year'],planned['study_year'],{'semesters':terms},
                source_kind='project_prepared',provenance=PROVENANCE,current_year=year)
        eligible = CampusActivity.query.filter(CampusActivity.is_active.is_(True),
            CampusActivity.department.in_(['all','bca' if student.course.code=='BCA' else 'home-science'])).order_by(CampusActivity.starts_at).limit(2)
        for event in eligible:
            if not ActivityParticipation.query.filter_by(activity_id=event.id,student_id=student.id).first():
                db.session.add(ActivityParticipation(activity=event,student=student,status='Registered',evidence=PROVENANCE))
    db.session.flush()
    return {'accounts':new_accounts,'students_added':len(new_students),'target_students':160,
            'attendance_through':through.isoformat(),'sessions_per_new_student':len(days)*5}
