"""Preserve old attendance while allowing two sessions of a subject per day."""
from sqlalchemy import inspect, text
from app.extensions import db


def upgrade_attendance_sessions():
    columns = {row['name'] for row in inspect(db.engine).get_columns('attendance')}
    if 'session_number' in columns:
        return
    if db.engine.dialect.name == 'sqlite':
        # No other table references attendance. The copy/drop/rename runs in a
        # single transaction and retains every original ID and recorded value.
        with db.engine.begin() as connection:
            connection.execute(text('SAVEPOINT attendance_upgrade'))
            connection.execute(text('''CREATE TABLE attendance_sessions_upgrade (
                id INTEGER NOT NULL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id),
                subject_id INTEGER NOT NULL REFERENCES subjects(id),
                faculty_id INTEGER NOT NULL REFERENCES faculty(id),
                attendance_date DATE NOT NULL, status VARCHAR(20) NOT NULL,
                remarks VARCHAR(255), created_at DATETIME NOT NULL,
                session_number INTEGER NOT NULL DEFAULT 1,
                session_type VARCHAR(20) NOT NULL DEFAULT 'Theory',
                starts_at TIME, ends_at TIME,
                timetable_slot_id INTEGER REFERENCES timetable_slots(id),
                CONSTRAINT uq_attendance_student_subject_date_session
                UNIQUE (student_id, subject_id, attendance_date, session_number))'''))
            connection.execute(text('''INSERT INTO attendance_sessions_upgrade
                (id, student_id, subject_id, faculty_id, attendance_date, status, remarks, created_at)
                SELECT id, student_id, subject_id, faculty_id, attendance_date, status, remarks, created_at FROM attendance'''))
            connection.execute(text('DROP TABLE attendance'))
            connection.execute(text('ALTER TABLE attendance_sessions_upgrade RENAME TO attendance'))
            connection.execute(text('CREATE INDEX ix_attendance_attendance_date ON attendance (attendance_date)'))
            connection.execute(text('RELEASE SAVEPOINT attendance_upgrade'))
    elif db.engine.dialect.name == 'postgresql':
        with db.engine.begin() as connection:
            for definition in ["session_number INTEGER NOT NULL DEFAULT 1", "session_type VARCHAR(20) NOT NULL DEFAULT 'Theory'", 'starts_at TIME', 'ends_at TIME', 'timetable_slot_id INTEGER REFERENCES timetable_slots(id)']:
                connection.execute(text('ALTER TABLE attendance ADD COLUMN ' + definition))
            connection.execute(text('ALTER TABLE attendance DROP CONSTRAINT IF EXISTS uq_attendance_student_subject_date'))
            connection.execute(text('ALTER TABLE attendance ADD CONSTRAINT uq_attendance_student_subject_date_session UNIQUE (student_id, subject_id, attendance_date, session_number)'))
    else:
        raise RuntimeError('Attendance session upgrade supports SQLite and PostgreSQL.')


def upgrade_attendance_audit():
    """Add audit columns without backfilling invented historical actor/time."""
    columns = {row['name'] for row in inspect(db.engine).get_columns('attendance')}
    timestamp_type = 'TIMESTAMP WITH TIME ZONE' if db.engine.dialect.name == 'postgresql' else 'DATETIME'
    definitions = {
        'recorded_by_user_id': 'INTEGER REFERENCES users(id)',
        'updated_at': timestamp_type,
        'updated_by_user_id': 'INTEGER REFERENCES users(id)',
    }
    with db.engine.begin() as connection:
        for name, definition in definitions.items():
            if name not in columns:
                connection.execute(text(f'ALTER TABLE attendance ADD COLUMN {name} {definition}'))
