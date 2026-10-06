"""Add an account owner for new test responses; preserve old records for office review."""
from sqlalchemy import inspect, text
from app.extensions import db


def upgrade_student_test_ownership():
    columns = {column['name'] for column in inspect(db.engine).get_columns('student_test_responses')}
    if 'user_id' in columns:
        return False
    with db.engine.begin() as connection:
        connection.execute(text('ALTER TABLE student_test_responses ADD COLUMN user_id INTEGER REFERENCES users(id)'))
        # Old forms allowed an arbitrary typed email, so even a unique matching
        # address is not evidence of who submitted it. Keep those owners NULL
        # and their records admin-only. Later upgrades never claim such rows.
    return True
