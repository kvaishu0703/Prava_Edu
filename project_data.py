"""Restore the versioned presentation dataset for a new local installation."""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import tempfile


def restore_project_data(root: Path) -> bool:
    """Copy the bundled database and files once, preserving existing local data."""
    root = Path(root).resolve()
    database = root / 'instance/prava.sqlite3'
    if database.exists():
        return False
    bundle = root / 'project-data'
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf8'))
    if manifest.get('version') != 1:
        raise RuntimeError('Unsupported project-data version. Download the complete latest ZIP.')

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
