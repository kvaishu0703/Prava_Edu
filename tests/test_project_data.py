"""Protect saved local work while making GitHub ZIP installs complete."""
import hashlib
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from project_data import restore_project_data


class ProjectDataTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.bundle = self.root / 'project-data'
        (self.bundle / 'uploads/materials').mkdir(parents=True)
        self.source = self.bundle / 'prava.sqlite3'
        with closing(sqlite3.connect(self.source)) as connection:
            connection.execute('CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT)')
            connection.execute("INSERT INTO students VALUES (1, 'Saved Student')")
            connection.commit()
        self.material = self.bundle / 'uploads/materials/lesson.txt'
        self.material.write_text('Saved learning file', encoding='utf8')
        self.manifest = {
            'version': 1,
            'database_sha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
            'uploads': {'materials/lesson.txt': hashlib.sha256(self.material.read_bytes()).hexdigest()},
        }
        self.write_manifest()

    def write_manifest(self):
        (self.bundle / 'manifest.json').write_text(json.dumps(self.manifest), encoding='utf8')

    def test_new_install_restores_database_and_files(self):
        self.assertTrue(restore_project_data(self.root))
        database = self.root / 'instance/prava.sqlite3'
        self.assertEqual(database.read_bytes(), self.source.read_bytes())
        with closing(sqlite3.connect(database)) as connection:
            self.assertEqual(connection.execute('SELECT name FROM students').fetchone()[0], 'Saved Student')
        self.assertEqual((self.root / 'app/static/uploads/materials/lesson.txt').read_bytes(), self.material.read_bytes())

    def test_existing_database_and_changed_upload_are_preserved(self):
        restore_project_data(self.root)
        database = self.root / 'instance/prava.sqlite3'
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("UPDATE students SET name='Edited locally'")
            connection.commit()
        upload = self.root / 'app/static/uploads/materials/lesson.txt'
        upload.write_text('Edited locally', encoding='utf8')
        before = database.read_bytes()
        self.assertFalse(restore_project_data(self.root))
        self.assertEqual(database.read_bytes(), before)
        self.assertEqual(upload.read_text(), 'Edited locally')

    def test_damaged_upload_does_not_create_database(self):
        self.material.write_text('Incomplete download', encoding='utf8')
        with self.assertRaisesRegex(RuntimeError, 'damaged'):
            restore_project_data(self.root)
        self.assertFalse((self.root / 'instance/prava.sqlite3').exists())

    def test_damaged_database_is_rejected(self):
        self.source.write_bytes(b'incomplete download')
        with self.assertRaisesRegex(RuntimeError, 'damaged'):
            restore_project_data(self.root)
        self.assertFalse((self.root / 'instance/prava.sqlite3').exists())

    def test_existing_upload_conflict_preserves_both_copies(self):
        destination = self.root / 'app/static/uploads/materials/lesson.txt'
        destination.parent.mkdir(parents=True)
        destination.write_text('Local work', encoding='utf8')
        with self.assertRaisesRegex(RuntimeError, 'new folder'):
            restore_project_data(self.root)
        self.assertEqual(destination.read_text(), 'Local work')
        self.assertFalse((self.root / 'instance/prava.sqlite3').exists())

    def test_upload_path_cannot_escape_upload_folder(self):
        self.manifest['uploads'] = {'../../outside.txt': '0' * 64}
        self.write_manifest()
        with self.assertRaises(RuntimeError):
            restore_project_data(self.root)
        self.assertFalse((self.root / 'instance/prava.sqlite3').exists())


if __name__ == '__main__':
    unittest.main()
