"""Owner-authorised timetable and attendance data for the local presentation.

Never invoked by normal startup. Existing manually entered attendance is kept.
"""
from collections import defaultdict
from datetime import date, time, timedelta
import json
from pathlib import Path
import random
from flask import current_app
from app.extensions import db
from app.models import Attendance, Course, Curriculum, Faculty, Student, Subject, TimetableSlot
from app.services.timetable import college_today, student_slots

ORIGIN = 'PRAVA presentation calendar 2026: generated attendance, not official college records.'
OLD_GENERATED_REMARKS = (
    'Recorded in class', 'Register reviewed',
    'User-authorised local college-project presentation data; not official academic results or student submissions.',
    ORIGIN,
)
TIMES = ((time(9,10),time(10,10)), (time(10,10),time(11,10)), (time(11,20),time(12,20)), (time(12,20),time(13,20)), (time(14),time(16)))


def is_practical(subject):
    return any(word in subject.name.lower() for word in ['laboratory', 'practical', 'practice', 'project']) or subject.code.endswith('-P')


def build_project_timetables(year=2026):
    """Create all programme/semester timetables once; preserve later edits."""
    reference = json.loads((Path(current_app.root_path)/'data/ty_sem5_timetable.json').read_text(encoding='utf8'))
    teaching_rows = [row for row in reference['rows'] if not row.get('break')][:5]
    # The two identical afternoon practical rows form one attendance session.
    for curriculum in Curriculum.query.order_by(Curriculum.id).all():
        for semester in range(1, 7):
            if TimetableSlot.query.filter_by(curriculum_id=curriculum.id, semester=semester, academic_year=year).first():
                continue
            subjects = Subject.query.filter_by(curriculum_id=curriculum.id, semester=semester, is_active=True).order_by(Subject.id).all()
            if not subjects:
                continue
            ty = curriculum.course.code == 'BCA' and semester == 5
            if ty:
                by_code = {subject.code: subject for subject in subjects}
                iot = Subject.query.filter_by(course_id=curriculum.course_id, semester=5, code='TT-IOT-V').first()
                if not iot:
                    iot = Subject(course_id=curriculum.course_id, curriculum_id=curriculum.id, semester=5,
                                  code='TT-IOT-V', name='Internet of Things (IOT)',
                                  faculty_id=by_code['CA-301-MJ'].faculty_id, maximum_marks=100, passing_marks=40)
                    db.session.add(iot)
                    db.session.flush()
                theory_map = {'DSc': by_code['CA-304-MJ'], 'AI': by_code['CA-302-MJ'], 'SE': by_code['CA-301-MJ'], 'CC': by_code['CA-312-MJP'], 'IOT': iot}
                lab_map = {'Java': by_code['CA-321-VSC'], 'CC': by_code['CA-313-MJP'], 'AI': by_code['CA-303-MJP'], 'DSc': by_code['CA-305-MJP'], 'FP': by_code['CA-331-FP']}
            theory = [s for s in subjects if not is_practical(s)] or subjects
            practical = [s for s in subjects if is_practical(s)] or subjects
            for weekday in range(6):
                for batch in (('A','B','C') if ty else ('All',)):
                    theory_index = weekday * 3
                    practical_index = weekday * 2
                    for index, (starts, ends) in enumerate(TIMES):
                        teacher_code = None
                        label = None
                        source = 'project-class-schedule'
                        if ty:
                            lines = teaching_rows[index]['cells'][weekday].splitlines()
                            if len(lines) == 2:
                                subject = theory_map[lines[0]]
                                kind, teacher_code, source = 'Theory', lines[1], 'college-photo'
                            else:
                                batches = lines[1].split('/')
                                if batch in batches:
                                    offset = batches.index(batch)
                                    code = lines[0].split('/')[offset]
                                    subject = lab_map[code]
                                    kind = 'Activity' if code == 'FP' else 'Practical'
                                    teacher_code, source = lines[2].split('/')[offset], 'college-photo'
                                else:
                                    subject, kind, label = lab_map['FP'], 'Activity', 'Library / independent project work'
                        else:
                            kind = ('Theory','Practical','Theory','Practical','Theory')[index] if weekday % 2 == 0 else ('Practical','Theory','Practical','Theory','Practical')[index]
                            if kind == 'Theory':
                                subject = theory[theory_index % len(theory)]
                                theory_index += 1
                            else:
                                subject = practical[practical_index % len(practical)]
                                practical_index += 1
                            if weekday == 5 and index == 4:
                                kind, label = 'Activity', 'Department activity / project mentoring'
                        if not subject.faculty_id:
                            raise ValueError(f'Assign a teacher to {subject.code} before creating the timetable.')
                        if ty and kind == 'Theory' and batch != 'A':
                            continue
                        slot_batch = 'All' if ty and kind == 'Theory' else batch
                        db.session.add(TimetableSlot(course_id=curriculum.course_id, curriculum_id=curriculum.id,
                            semester=semester, academic_year=year, weekday=weekday, session_number=index+1,
                            starts_at=starts, ends_at=ends, subject_id=subject.id, faculty_id=subject.faculty_id,
                            session_type=kind, batch=slot_batch, subject_label=label, teacher_code=teacher_code,
                            room=('Hall No. 3' if ty else f'{curriculum.course.code} - Year {(semester+1)//2}') if kind == 'Theory' else ('Computer Laboratory' if curriculum.course.code == 'BCA' else 'Department Laboratory') if kind == 'Practical' else 'Department / Library', source=source))
    ty_students = Student.query.join(Student.course).filter(Course.code=='BCA', Student.semester==5).order_by(Student.id).all()
    for index, student in enumerate(ty_students):
        if not student.practical_batch:
            student.practical_batch = 'ABC'[index % 3]
    db.session.flush()


def populate_project_attendance(start=date(2026,6,15), end=None):
    """Replace only previous generated rows and fill five sessions per teaching day."""
    if current_app.config.get('IS_PRODUCTION') or not current_app.config.get('DEMO_MODE'):
        raise ValueError('Project attendance can only be prepared in local project mode.')
    end = end or college_today()
    if end < start or end > college_today():
        raise ValueError('Choose a date range ending on or before today.')
    build_project_timetables(start.year)
    holidays = {date(2026,8,15), date(2026,10,2)}
    dates = [start+timedelta(days=i) for i in range((end-start).days+1) if (start+timedelta(days=i)).weekday()<6 and start+timedelta(days=i) not in holidays]
    result = []
    for student in Student.query.join(Student.user).filter_by(is_active=True).order_by(Student.id).all():
        slots = student_slots(student, start.year)
        if not slots:
            raise ValueError(f'No timetable for student {student.id}.')
        days = defaultdict(list)
        for slot in slots:
            days[slot.weekday].append(slot)
        if any(len(days[d]) != 5 for d in range(6)):
            raise ValueError('Every weekday must have exactly five sessions for this batch.')
        manual = Attendance.query.filter(Attendance.student_id==student.id,
            Attendance.attendance_date>=start, Attendance.attendance_date<=end,
            db.or_(Attendance.remarks.is_(None), Attendance.remarks.notin_(OLD_GENERATED_REMARKS))).all()
        generated = Attendance.query.filter(Attendance.student_id==student.id,
            Attendance.attendance_date>=start, Attendance.attendance_date<=end,
            Attendance.remarks.in_(OLD_GENERATED_REMARKS)).all()
        for row in generated:
            db.session.delete(row)
        db.session.flush()
        plan = [(day,slot) for day in dates for slot in days[day.weekday()]]
        # Match manually entered subject/date rows once, preserving their status.
        preserved = {}
        for record in manual:
            candidates = [(index,slot) for index,(day,slot) in enumerate(plan)
                          if day==record.attendance_date and slot.subject_id==record.subject_id and index not in preserved]
            if not candidates:
                raise ValueError(f'Manual attendance {record.id} needs a matching timetable session; no changes committed.')
            index,slot = next(((i,s) for i,s in candidates if s.session_number==record.session_number), candidates[0])
            preserved[index] = record
            record.session_number, record.session_type = slot.session_number, slot.session_type
            record.starts_at, record.ends_at, record.timetable_slot_id = slot.starts_at, slot.ends_at, slot.id
        target = 90 + ((student.id - 1) % 9)
        desired_absent = round(len(plan) * (100-target) / 100)
        manual_absent = sum(record.status=='Absent' for record in preserved.values())
        candidates = [index for index in range(len(plan)) if index not in preserved]
        random.Random(f'prava-attendance-2026-{student.id}').shuffle(candidates)
        absent = set(candidates[:max(0, desired_absent-manual_absent)])
        rows = []
        for index,(day,slot) in enumerate(plan):
            if index in preserved:
                continue
            rows.append({'student_id':student.id, 'subject_id':slot.subject_id, 'faculty_id':slot.faculty_id,
                'attendance_date':day, 'status':'Absent' if index in absent else 'Present', 'remarks':ORIGIN,
                'session_number':slot.session_number, 'session_type':slot.session_type, 'starts_at':slot.starts_at,
                'ends_at':slot.ends_at, 'timetable_slot_id':slot.id})
        db.session.execute(db.insert(Attendance), rows)
        result.append({'student_id':student.id, 'sessions':len(plan), 'target_percentage':target,
                       'manual_records_preserved':len(manual)})
    db.session.commit()
    return {'from':start.isoformat(), 'through':end.isoformat(), 'teaching_days':len(dates),
            'sessions_per_day':5, 'excluded_dates':sorted(day.isoformat() for day in holidays), 'students':result}
