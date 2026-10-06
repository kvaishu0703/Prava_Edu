"""Restore the versioned presentation dataset for a new local installation."""
from __future__ import annotations

import hashlib
import csv
import io
import json
import os
import secrets
import time
from contextlib import closing, contextmanager
from pathlib import Path
import shutil
import sqlite3
import tempfile

PASSWORD_MARKER = '!local-installation-required!'
CREDENTIAL_MODE = 'generate-on-first-start'


@contextmanager
def _installation_lock(instance: Path):
    """Serialise first-start DB and private handout creation across processes."""
    instance.mkdir(parents=True, exist_ok=True)
    with (instance / '.project-restore.lock').open('a+b') as lock:
        lock.seek(0, os.SEEK_END)
        if not lock.tell():
            lock.write(b'0')
            lock.flush()
        deadline = time.monotonic() + 120
        while True:
            try:
                lock.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError):
                if time.monotonic() >= deadline:
                    raise RuntimeError('Another PRAVA setup is running. Wait for it to finish, then start again.')
                time.sleep(.1)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == 'nt':
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _prepare_local_credentials(database: Path, instance: Path) -> None:
    """Create per-installation secrets locally; none are in the public bundle."""
    from werkzeug.security import generate_password_hash
    records = []
    with closing(sqlite3.connect(database)) as connection:
        for user_id, name, username, role in connection.execute(
                'SELECT id, full_name, username, role FROM users ORDER BY role, full_name'):
            password = 'Prava-' + secrets.token_urlsafe(12)
            connection.execute('UPDATE users SET password_hash=? WHERE id=?',
                               (generate_password_hash(password), user_id))
            records.append((name, username, password, role))
        connection.commit()
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['full_name', 'username', 'password', 'role'])
    # Names/IDs come from the roster; prevent spreadsheet formula execution.
    safe = lambda value: "'" + value if value.lstrip()[:1] in ('=', '+', '-', '@') or value[:1] in ('\t', '\r', '\n') else value
    writer.writerows([[safe(value) for value in row] for row in records])
    lines = ['PRAVA - PRIVATE LOCAL LOGIN DETAILS',
             'These passwords work only with this installation. Keep this file private.',
             'Existing passwords are preserved on restart. Give each user their own entry.', '']
    for name, username, password, role in records:
        lines += [f'{name} | {role}', f'Login ID: {username}', f'Password: {password}', '']
    temporary_files = []
    try:
        for suffix, content in [('csv', output.getvalue()), ('txt', '\n'.join(lines))]:
            descriptor, name = tempfile.mkstemp(prefix='.private-login-', dir=instance)
            temporary = Path(name)
            temporary_files.append((temporary, instance / f'PRAVA_Local_Login_Details.{suffix}'))
            with os.fdopen(descriptor, 'w', encoding='utf-8-sig', newline='') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        # Both files are complete before either is published. The database is
        # published afterwards, so failed setup cannot expose unusable accounts.
        for temporary, destination in temporary_files:
            os.replace(temporary, destination)
    finally:
        for temporary, _ in temporary_files:
            temporary.unlink(missing_ok=True)


def restore_project_data(root: Path) -> bool:
    """Copy the bundled database and files once, preserving existing local data."""
    root = Path(root).resolve()
    database = root / 'instance/prava.sqlite3'
    if database.exists():
        return False
    with _installation_lock(database.parent):
        if database.exists():
            return False
        return _restore_project_data(root)


def _restore_project_data(root: Path) -> bool:
    database = root / 'instance/prava.sqlite3'
    bundle = root / 'project-data'
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf8'))
    if manifest.get('version') != 1:
        raise RuntimeError('Unsupported project-data version. Download the complete latest ZIP.')
    credential_mode = manifest.get('credential_mode')
    if credential_mode not in (None, CREDENTIAL_MODE):
        raise RuntimeError('Unsupported project credential mode. Download the complete latest ZIP.')

    def checked_file(relative: str, digest: str) -> Path:
        path = (bundle / relative).resolve()
        if not path.is_relative_to(bundle.resolve()) or not path.is_file():
            raise RuntimeError(f'Project data file is missing or invalid: {relative}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'Project data file is damaged: {relative}. Extract the ZIP again.')
        return path

    source = checked_file('prava.sqlite3', manifest['database_sha256'])
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as connection:
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('The bundled project database failed its integrity check.')
        if connection.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('The bundled project database has incomplete relationships.')
        if credential_mode == CREDENTIAL_MODE:
            try:
                invalid = connection.execute('SELECT count(*) FROM users WHERE password_hash != ? OR password_hash IS NULL OR is_demo != 1 OR is_demo IS NULL', (PASSWORD_MARKER,)).fetchone()[0]
            except sqlite3.DatabaseError as error:
                raise RuntimeError('The bundled accounts are invalid.') from error
            if invalid:
                raise RuntimeError('The public bundle must contain only redacted local-project credentials.')

    uploads = (root / 'app/static/uploads').resolve()
    files = []
    for relative, digest in manifest['uploads'].items():
        origin = checked_file('uploads/' + relative, digest)
        destination = (uploads / relative).resolve()
        if not destination.is_relative_to(uploads):
            raise RuntimeError(f'Invalid upload path: {relative}')
        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Existing uploaded files differ from the project copy. Extract into a new folder to keep both sets.')
        files.append((origin, destination))

    # Validate the complete bundle before creating any local files. Copy files
    # first so an interrupted run can resume without leaving a half-ready DB.
    for origin, destination in files:
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as output, origin.open('rb') as input_file:
            shutil.copyfileobj(input_file, output)

    database.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix='.project-data-', suffix='.sqlite3', dir=database.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        if credential_mode == CREDENTIAL_MODE:
            _prepare_local_credentials(temporary, database.parent)
        # Windows rename refuses to overwrite a competing installation. A hard
        # link provides the same atomic, no-replacement behavior on Unix.
        if os.name == 'nt':
            temporary.rename(database)
        else:
            os.link(temporary, database)
    except FileExistsError:
        return False
    finally:
        temporary.unlink(missing_ok=True)
    return True
