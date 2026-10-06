"""Validate, prepare and scope prior-year academic snapshots."""
from copy import deepcopy
from datetime import date
import math
from flask import current_app
from app.extensions import db
from app.models import Subject
from app.models.academic_history import AcademicYearRecord
from app.services.timetable import academic_year_for, college_today, year_bounds

SOURCE_KINDS = {'project_prepared', 'college_register'}
ASSIGNMENT_STATUSES = {'Pending', 'Submitted', 'Graded', 'Completed'}
YEAR_NAMES = {1: 'First Year', 2: 'Second Year', 3: 'Third Year'}


def academic_year_plan(student, current_year=None):
    """Use current semester progression; preserve the supplied admission year."""
    current_year = current_year if current_year is not None else academic_year_for(college_today())
    if not isinstance(student.semester, int) or not 1 <= student.semester <= 6:
        raise ValueError('Academic history supports semesters 1 through 6.')
    study_year = (student.semester + 1) // 2
    return [{'academic_year': current_year - (study_year - year), 'study_year': year,
             'name': YEAR_NAMES[year], 'is_current': year == study_year,
             'label': f'{current_year - (study_year - year)}–{current_year - (study_year - year) + 1}'}
            for year in range(study_year, 0, -1)]


def _text(value, label, maximum=180):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValueError(f'{label} must be non-empty text of up to {maximum} characters.')
    return value.strip()


def _integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f'{label} must be a non-negative integer.')
    return value


def _score(value, label, allow_none=False):
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{label} must be a finite non-negative number.')
    return round(value, 2)


def _archive_date(value, label, first, last):
    if value in (None, ''):
        return None
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f'{label} must use YYYY-MM-DD.') from None
    if not first <= parsed <= last:
        raise ValueError(f'{label} must belong to the archived academic year.')
    return parsed.isoformat()


def normalize_history_snapshot(snapshot, academic_year, study_year):
    """Keep only supported fields and check subject totals and score ranges."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('semesters'), list):
        raise ValueError('History must contain a semesters list.')
    semesters = snapshot['semesters']
    if not 1 <= len(semesters) <= 2:
        raise ValueError('Provide one or two completed semesters for this year.')
    valid_semesters = {study_year * 2 - 1, study_year * 2}
    seen_semesters = set()
    normalized = {'schema_version': 1, 'semesters': []}
    first, last = year_bounds(academic_year)
    for term in semesters:
        if not isinstance(term, dict) or term.get('semester') not in valid_semesters or isinstance(term.get('semester'), bool):
            raise ValueError('The archived semester must belong to its study year.')
        semester = term['semester']
        if semester in seen_semesters:
            raise ValueError('A semester can appear only once in an archive.')
        seen_semesters.add(semester)
        subjects = term.get('subjects')
        if not isinstance(subjects, list) or not 1 <= len(subjects) <= 60:
            raise ValueError('Each semester needs between 1 and 60 subjects.')
        normalized_term = {'semester': semester, 'subjects': []}
        seen_codes = set()
        for item in subjects:
            if not isinstance(item, dict):
                raise ValueError('Each archived subject must be an object.')
            code = _text(item.get('code'), 'Subject code', 80).upper()
            if code in seen_codes:
                raise ValueError('Subject codes must be unique within each semester.')
            seen_codes.add(code)
            name = _text(item.get('name'), 'Subject name')
            attendance = item.get('attendance', {})
            if not isinstance(attendance, dict):
                raise ValueError('Subject attendance must contain session counts.')
            counts = {key: _integer(attendance.get(key, 0), f'Attendance {key}') for key in ['held', 'present', 'late', 'absent']}
            if counts['held'] != counts['present'] + counts['late'] + counts['absent']:
                raise ValueError('Held sessions must equal present, late and absent sessions.')
            assessments = item.get('assessments', [])
            assignments = item.get('assignments', [])
            if not isinstance(assessments, list) or len(assessments) > 20 or not isinstance(assignments, list) or len(assignments) > 100:
                raise ValueError('Provide assessment and assignment lists within the archive limits.')
            result = {'code': code, 'name': name, 'attendance': counts, 'assessments': [], 'assignments': []}
            seen_exams = set()
            for marks in assessments:
                if not isinstance(marks, dict):
                    raise ValueError('Each assessment must be an object.')
                exam = _text(marks.get('exam_type'), 'Exam type', 80)
                if exam.casefold() in seen_exams:
                    raise ValueError('An exam can appear only once per subject.')
                seen_exams.add(exam.casefold())
                internal = _score(marks.get('internal_marks'), 'Internal marks')
                external = _score(marks.get('external_marks'), 'External marks')
                maximum = _score(marks.get('maximum_marks'), 'Maximum marks')
                passing = _score(marks.get('passing_marks'), 'Passing marks', allow_none=True)
                if maximum <= 0 or internal + external > maximum or (passing is not None and passing > maximum):
                    raise ValueError('Assessment scores and passing marks must stay within the maximum.')
                result['assessments'].append({'exam_type': exam, 'internal_marks': internal,
                    'external_marks': external, 'maximum_marks': maximum, 'passing_marks': passing})
            for assignment in assignments:
                if not isinstance(assignment, dict) or assignment.get('status') not in ASSIGNMENT_STATUSES:
                    raise ValueError('Choose a valid archived assignment status.')
                score = _score(assignment.get('score'), 'Assignment score', allow_none=True)
                maximum = _score(assignment.get('maximum'), 'Assignment maximum', allow_none=True)
                if score is not None and (maximum is None or score > maximum):
                    raise ValueError('An assignment score requires a matching maximum.')
                if assignment['status'] == 'Pending' and score is not None:
                    raise ValueError('A pending assignment cannot have awarded marks.')
                result['assignments'].append({'title': _text(assignment.get('title'), 'Assignment title'),
                    'status': assignment['status'], 'score': score, 'maximum': maximum,
                    'due_date': _archive_date(assignment.get('due_date'), 'Assignment due date', first, last),
                    'submitted_date': _archive_date(assignment.get('submitted_date'), 'Assignment submitted date', first, last)})
            normalized_term['subjects'].append(result)
        normalized['semesters'].append(normalized_term)
    normalized['semesters'].sort(key=lambda row: row['semester'])
    return normalized


def upsert_academic_history(student, academic_year, study_year, snapshot, *, source_kind='project_prepared',
                            provenance='Prepared for the college academic project; not an official university transcript.',
                            actor=None, current_year=None):
    """Validate and stage an archive; the caller owns commit/rollback."""
    if actor is not None and (not actor.is_active or actor.role != 'admin'):
        raise PermissionError('Only college administration can prepare academic archives.')
    if source_kind not in SOURCE_KINDS:
        raise ValueError('Choose a supported academic record source.')
    if source_kind == 'project_prepared' and (current_app.config.get('IS_PRODUCTION') or not current_app.config.get('DEMO_MODE')):
        raise ValueError('Project-prepared history is available only in local project mode.')
    if source_kind == 'college_register' and actor is None:
        raise PermissionError('A college-register archive requires an identified administrator.')
    valid = {(row['academic_year'], row['study_year']) for row in academic_year_plan(student, current_year) if not row['is_current']}
    if isinstance(academic_year, bool) or isinstance(study_year, bool) or (academic_year, study_year) not in valid:
        raise ValueError('Archive only a completed year in this student\'s current programme progression.')
    normalized = normalize_history_snapshot(snapshot, academic_year, study_year)
    note = _text(provenance, 'Record provenance', 500)
    record = AcademicYearRecord.query.filter_by(student_id=student.id, academic_year=academic_year).first()
    if record is None:
        record = AcademicYearRecord(student_id=student.id, academic_year=academic_year, study_year=study_year)
        db.session.add(record)
    record.study_year, record.snapshot = study_year, normalized
    record.source_kind, record.provenance = source_kind, note
    record.updated_by_user_id = actor.id if actor else None
    db.session.flush()
    return record


def history_access_scope(actor, student):
    if not actor or not actor.is_active:
        raise PermissionError('Sign in with an active account to view academic history.')
    if actor.role == 'student':
        if actor.id != student.user_id:
            raise PermissionError('Only your own academic history is available.')
        return {'full_access': True, 'allowed_codes': None}
    from app.services.campus import student_record_scope
    scope = student_record_scope(actor, student)
    codes = None if scope['full_access'] else {
        row[0].upper() for row in Subject.query.with_entities(Subject.code).filter(Subject.id.in_(scope['subject_ids'])).all()}
    return {'full_access': scope['full_access'], 'allowed_codes': codes}


def summarize_history(snapshot, allowed_codes=None):
    """Calculate totals only from the subjects this viewer may read."""
    data = deepcopy(snapshot)
    attendance = {'held': 0, 'present': 0, 'late': 0, 'absent': 0}
    score, maximum, assigned, completed = 0, 0, 0, 0
    subject_count = 0
    for semester in data['semesters']:
        if allowed_codes is not None:
            semester['subjects'] = [item for item in semester['subjects'] if item['code'] in allowed_codes]
        for subject in semester['subjects']:
            subject_count += 1
            for key in attendance:
                attendance[key] += subject['attendance'][key]
            held = subject['attendance']['held']
            subject['attendance_percentage'] = round((subject['attendance']['present'] + subject['attendance']['late']) * 100 / held, 1) if held else None
            for assessment in subject['assessments']:
                assessment['total_marks'] = round(assessment['internal_marks'] + assessment['external_marks'], 2)
                assessment['result'] = ('Pass' if assessment['total_marks'] >= assessment['passing_marks'] else 'Needs improvement') if assessment['passing_marks'] is not None else 'Pending assessment rules'
                score += assessment['total_marks']
                maximum += assessment['maximum_marks']
            assigned += len(subject['assignments'])
            completed += sum(row['status'] in {'Submitted', 'Graded', 'Completed'} for row in subject['assignments'])
    data['semesters'] = [row for row in data['semesters'] if row['subjects']]
    attendance['percentage'] = round((attendance['present'] + attendance['late']) * 100 / attendance['held'], 1) if attendance['held'] else None
    return {'snapshot': data, 'attendance': attendance, 'marks_percentage': round(score * 100 / maximum, 1) if maximum else None,
            'total_marks': round(score, 2), 'maximum_marks': maximum, 'assignments_total': assigned,
            'assignments_completed': completed, 'subject_count': subject_count}


def academic_history_view(actor, student, selected_year=None, current_year=None):
    scope = history_access_scope(actor, student)
    plan = academic_year_plan(student, current_year)
    selected = next((year for year in plan if year['academic_year'] == selected_year), None) if selected_year is not None else plan[0]
    if selected is None:
        raise ValueError('Choose an academic year available for this student.')
    record = None
    summary = None
    if not selected['is_current']:
        record = AcademicYearRecord.query.filter_by(student_id=student.id, academic_year=selected['academic_year']).first()
        if record:
            summary = summarize_history(record.snapshot, scope['allowed_codes'])
    return {'student': student, 'years': plan, 'selected': selected, 'archive': record, 'summary': summary, **scope}
