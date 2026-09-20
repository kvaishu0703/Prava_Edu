"""Validate complete college rosters before a single account is written."""
import csv
import io
import re
from datetime import date
from app.models import User, Student, Faculty, Course, Curriculum

HEADERS = {
    'students': ['full_name', 'username', 'email', 'enrollment_number', 'programme', 'pattern', 'semester', 'admission_year'],
    'staff': ['full_name', 'username', 'email', 'employee_id', 'department', 'qualification'],
}


def validate_roster(raw, kind):
    if kind not in HEADERS:
        raise ValueError('Choose Students or Staff.')
    if len(raw) > 1024 * 1024:
        raise ValueError('The CSV must be smaller than 1 MB.')
    try:
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if reader.fieldnames != HEADERS[kind]:
            raise ValueError('Use the exact columns and order in the downloadable template.')
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error):
        raise ValueError('Upload a valid UTF-8 CSV file.')
    if not 1 <= len(rows) <= 200:
        raise ValueError('Each import must contain between 1 and 200 records.')
    seen = {'username': set(), 'email': set(), 'identity': set()}
    for number, row in enumerate(rows, 2):
        prefix = f'Row {number}: '
        if None in row or any(v is None for v in row.values()):
            raise ValueError(prefix + 'The number of columns does not match the template.')
        for key in row:
            row[key] = row[key].strip()
            if not row[key] and key != 'qualification':
                raise ValueError(prefix + f'{key} is required.')
        row['username'] = row['username'].lower()
        row['email'] = row['email'].lower()
        if not re.fullmatch(r'[a-z0-9_.-]{3,80}', row['username']):
            raise ValueError(prefix + 'Username must contain 3–80 letters, digits, dots, hyphens or underscores.')
        if len(row['full_name']) > 120 or len(row['email']) > 120 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', row['email']):
            raise ValueError(prefix + 'Check the name and email address.')
        identity_key = 'enrollment_number' if kind == 'students' else 'employee_id'
        identity = row[identity_key]
        if len(identity) > 50:
            raise ValueError(prefix + 'Enrollment / employee number is too long.')
        for key, value in [('username', row['username']), ('email', row['email']), ('identity', identity)]:
            if value in seen[key]:
                raise ValueError(prefix + f'Duplicate {key} in this file.')
            seen[key].add(value)
        if User.query.filter((User.username == row['username']) | (User.email == row['email'])).first():
            raise ValueError(prefix + 'This username or email already exists. Edit the existing account.')
        model = Student if kind == 'students' else Faculty
        if model.query.filter(getattr(model, identity_key) == identity).first():
            raise ValueError(prefix + 'This enrollment / employee number already exists.')
        if kind == 'students':
            course = Course.query.filter_by(code=row['programme'].upper(), is_active=True).first()
            curriculum = Curriculum.query.filter_by(course_id=course.id, pattern=row['pattern']).first() if course else None
            if not curriculum:
                raise ValueError(prefix + 'Programme and pattern must match a configured curriculum.')
            try:
                semester, year = int(row['semester']), int(row['admission_year'])
                if not (1 <= semester <= course.total_semesters and 1997 <= year <= date.today().year + 1):
                    raise ValueError()
            except ValueError:
                raise ValueError(prefix + 'Check the semester and admission year.')
            row['programme'] = course.code
        elif len(row['department']) > 120 or len(row['qualification']) > 120:
            raise ValueError(prefix + 'Department and qualification must be at most 120 characters.')
    return rows


def encode_roster(rows, kind):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=HEADERS[kind])
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode('utf-8')
