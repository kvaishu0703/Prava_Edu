"""One-time roster handouts, encrypted at rest and bound to their creating officer."""
import csv
import io
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

from app.extensions import db
from app.models.record_import import RecordImport

HANDOUT_KIND = 'credential_handout'
LIFETIME = timedelta(hours=1)


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def purge_expired_imports():
    RecordImport.query.filter(RecordImport.created_at < utc_now() - LIFETIME).delete(synchronize_session=False)


def _cipher():
    """Use a private random key, never the public development session secret."""
    key = current_app.config.get('ROSTER_CREDENTIAL_KEY')
    if not key:
        path = Path(current_app.instance_path) / 'roster-credentials.key'
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Exclusive creation supports simultaneous worker startup.
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            # Another worker can see the exclusively created file before its
            # first write finishes. Read again briefly; never replace a key.
            for attempt in range(6):
                key = path.read_bytes()
                try:
                    return Fernet(key)
                except (ValueError, TypeError):
                    if attempt == 5:
                        raise ValueError('The private credential key is unavailable. Try again; no accounts were imported.') from None
                    time.sleep(0.05 * (attempt + 1))
        else:
            key = Fernet.generate_key()
            with os.fdopen(descriptor, 'wb') as handle:
                handle.write(key)
    if isinstance(key, str):
        key = key.encode('ascii')
    return Fernet(key)


def temporary_password():
    """Independent 128-bit random secret with upper/lower/digit/symbol characters."""
    return 'P!' + secrets.token_urlsafe(16) + '7a'


def create_handout(owner_id, kind, credentials):
    payload = json.dumps(credentials, ensure_ascii=False).encode('utf-8')
    handout = RecordImport(user_id=owner_id, kind=HANDOUT_KIND, payload={
        'ciphertext': _cipher().encrypt(payload).decode('ascii'),
        'record_kind': kind,
        'count': len(credentials),
    })
    db.session.add(handout)
    return handout


def _safe_csv_value(value):
    text = str(value if value is not None else '')
    # Neutralize spreadsheet formulas even for imported names beginning with +/@/-.
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text


def consume_handout(handout):
    if handout.kind != HANDOUT_KIND or handout.created_at < utc_now() - LIFETIME:
        raise ValueError('This credential handout has expired. Reset passwords from the account editor if needed.')
    try:
        rows = json.loads(_cipher().decrypt(handout.payload['ciphertext'].encode('ascii'), ttl=3600))
    except (InvalidToken, KeyError, ValueError) as exc:
        raise ValueError('This credential handout is unavailable. Reset passwords from the account editor if needed.') from exc
    buffer = io.StringIO(newline='')
    headers = ['full_name', 'role', 'programme_or_department', 'student_or_employee_id', 'login_id', 'temporary_password', 'login_path']
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_safe_csv_value(row.get(field, '')) for field in headers])
    # Delete with a predicate so concurrent requests cannot both consume one bundle.
    deleted = RecordImport.query.filter_by(id=handout.id, user_id=handout.user_id, kind=HANDOUT_KIND).delete(synchronize_session=False)
    if deleted != 1:
        raise ValueError('This credential handout was already downloaded.')
    return buffer.getvalue().encode('utf-8-sig')
