"""Reproducible local demo identities without resetting college data."""
from flask import current_app
from sqlalchemy import or_
from app.extensions import db
from app.models import Course, Curriculum, User, Student, Faculty

DEMO_ACCOUNTS = [
    ('bca', 'bca123', 'BCA Student', 'student', 'BCA'),
    ('home', 'home123', 'Home Science Student', 'student', 'BSC-FSN'),
    ('staff', 'staff123', 'Faculty', 'faculty', None),
    ('office', 'office123', 'College Administration', 'admin', None),
]

LEGACY_NAMES = {
    'bca': 'BCA Demo Student', 'home': 'Home Science Demo Student',
    'staff': 'Demo Staff', 'office': 'Demo Administrator',
}


def setup_demo():
    if not current_app.config.get('DEMO_MODE') or current_app.config.get('IS_PRODUCTION'):
        raise ValueError('Set PRAVA_DEMO_MODE=true in a local development environment to create demo accounts.')
    if current_app.config.get('SUPABASE_AUTH_ENABLED'):
        raise ValueError('Local demo setup requires SUPABASE_AUTH_ENABLED=false.')
    existing = {}
    for username, _, _, _, _ in DEMO_ACCOUNTS:
        user = User.query.filter(or_(User.username == username, User.email == username+'@demo.prava.test')).first()
        if user and (not user.is_demo or user.username != username or user.email != username+'@demo.prava.test'):
            raise ValueError(f'{username} conflicts with an existing account. No accounts were changed.')
        existing[username] = user
    for programme, enrollment in [('BCA', 'DEMO-BCA-001'), ('BSC-FSN', 'DEMO-HS-001')]:
        if not Curriculum.query.join(Course).filter(Course.code == programme, Curriculum.pattern == '2024 NEP').first():
            raise ValueError('Run sync-college before setup-demo.')
        student = Student.query.filter_by(enrollment_number=enrollment).first()
        if student and not student.user.is_demo:
            raise ValueError('A reserved demo enrollment conflicts with college records.')
    faculty = Faculty.query.filter_by(employee_id='DEMO-STAFF-001').first()
    if faculty and not faculty.user.is_demo:
        raise ValueError('The demo employee ID conflicts with college records.')
    try:
        for username, password, full_name, role, programme in DEMO_ACCOUNTS:
            if existing[username]:
                # Only migrate untouched setup labels; preserve names entered by the office.
                user = existing[username]
                if user.full_name == LEGACY_NAMES[username]:
                    user.full_name = full_name
                if user.faculty_profile and user.faculty_profile.qualification == 'Local demonstration account':
                    user.faculty_profile.qualification = None
                continue
            user = User(username=username, email=username+'@demo.prava.test', full_name=full_name,
                        role=role, is_demo=True, is_active=True,
                        admin_scope='administrator' if role == 'admin' else 'office')
            user.set_password(password)
            db.session.add(user)
            if programme:
                curriculum = Curriculum.query.join(Course).filter(Course.code == programme, Curriculum.pattern == '2024 NEP').one()
                db.session.add(Student(user=user, enrollment_number='DEMO-BCA-001' if programme == 'BCA' else 'DEMO-HS-001',
                                       course=curriculum.course, curriculum=curriculum, semester=1, admission_year=2026))
            elif role == 'faculty':
                db.session.add(Faculty(user=user, employee_id='DEMO-STAFF-001', department='BCA / Home Science'))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
