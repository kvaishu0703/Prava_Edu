"""Protect saved local work while making GitHub ZIP installs complete."""
import hashlib
import csv
import json
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import shutil
import tempfile
import unittest
from unittest.mock import patch
from werkzeug.security import check_password_hash, generate_password_hash

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

    def credential_bundle(self):
        """Stable profile IDs remain in the bundle; usable passwords do not."""
        self.placeholder = '!local-installation-required!'
        self.users = [
            (11, 'College Principal', 'principal', 'admin', self.placeholder, 1, 1),
            (42, 'Surekha Kale', 'teacher', 'faculty', self.placeholder, 1, 1),
            (87, 'Vaishnavi, Vijay Kale', 'vaishnavi', 'student', self.placeholder, 1, 1),
            (90, 'Rutuja Ashok Khobare', 'rutuja', 'student', self.placeholder, 0, 1),
        ]
        with closing(sqlite3.connect(self.source)) as connection:
            connection.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, full_name TEXT NOT NULL, username TEXT NOT NULL UNIQUE, role TEXT NOT NULL, password_hash TEXT NOT NULL, is_active INTEGER NOT NULL, is_demo INTEGER NOT NULL)')
            connection.executemany('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)',self.users)
            connection.commit()
        self.manifest['credential_mode'] = 'generate-on-first-start'
        self.refresh_database_checksum()

    def refresh_database_checksum(self):
        self.manifest['database_sha256'] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.write_manifest()

    def local_credentials(self, root=None):
        target = (root or self.root) / 'instance/PRAVA_Local_Login_Details.csv'
        with target.open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual({row['username'] for row in rows},{row[2] for row in self.users})
        return {row['username']:row for row in rows}

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

    def test_new_mode_generates_private_credentials_matching_local_hashes(self):
        self.credential_bundle()
        source_before = self.source.read_bytes()
        self.assertTrue(restore_project_data(self.root))
        credentials = self.local_credentials()
        passwords = [row['password'] for row in credentials.values()]
        self.assertEqual(len(set(passwords)),len(self.users))
        self.assertTrue(all(password and password != self.placeholder for password in passwords))
        with closing(sqlite3.connect(self.root / 'instance/prava.sqlite3')) as connection:
            rows = connection.execute('SELECT id, full_name, username, role, password_hash, is_active, is_demo FROM users ORDER BY id').fetchall()
        self.assertEqual(len(rows),len(self.users))
        for row, original in zip(rows,self.users):
            self.assertEqual(row[:4],original[:4])
            self.assertEqual(row[5:],original[5:])
            self.assertNotEqual(row[4],self.placeholder)
            self.assertTrue(check_password_hash(row[4],credentials[row[2]]['password']))
        handout=(self.root / 'instance/PRAVA_Local_Login_Details.txt').read_text(encoding='utf-8-sig')
        self.assertIn('vaishnavi',handout)
        self.assertIn(credentials['vaishnavi']['password'],handout)
        self.assertEqual(self.source.read_bytes(),source_before)

    def test_credentials_differ_between_installations_and_are_preserved_on_restart(self):
        self.credential_bundle()
        second = self.root / 'another-installation'
        shutil.copytree(self.bundle,second / 'project-data')
        self.assertTrue(restore_project_data(self.root))
        self.assertTrue(restore_project_data(second))
        first_passwords = {name:row['password'] for name,row in self.local_credentials().items()}
        second_passwords = {name:row['password'] for name,row in self.local_credentials(second).items()}
        self.assertTrue(all(first_passwords[name] != second_passwords[name] for name in first_passwords))
        files = [self.root / 'instance' / filename for filename in
                 ('prava.sqlite3','PRAVA_Local_Login_Details.csv','PRAVA_Local_Login_Details.txt')]
        before = {path:path.read_bytes() for path in files}
        self.assertFalse(restore_project_data(self.root))
        self.assertEqual({path:path.read_bytes() for path in files},before)

    def test_existing_local_database_and_changed_password_ignore_new_bundle_mode(self):
        self.credential_bundle()
        restore_project_data(self.root)
        database = self.root / 'instance/prava.sqlite3'
        changed_hash = generate_password_hash('UserChangedPrivate@2026')
        with closing(sqlite3.connect(database)) as connection:
            connection.execute('UPDATE users SET password_hash=? WHERE username=?',(changed_hash,'vaishnavi'))
            connection.commit()
        handout = self.root / 'instance/PRAVA_Local_Login_Details.txt'
        handout.write_text('Local handout note kept by the user',encoding='utf8')
        before=database.read_bytes()
        self.assertFalse(restore_project_data(self.root))
        self.assertEqual(database.read_bytes(),before)
        self.assertEqual(handout.read_text(encoding='utf8'),'Local handout note kept by the user')

    def test_invalid_credential_mode_is_rejected_before_database_creation(self):
        self.credential_bundle()
        self.manifest['credential_mode']='unsupported-credential-mode'
        self.write_manifest()
        with self.assertRaises(RuntimeError):
            restore_project_data(self.root)
        self.assertFalse((self.root / 'instance/prava.sqlite3').exists())

    def test_unredacted_hash_or_nonlocal_user_is_rejected_even_with_valid_checksum(self):
        self.credential_bundle()
        for password_hash, is_demo in [(generate_password_hash('OldPublishedPassword@2026'),1),
                                      ('published-plaintext-password',1),(self.placeholder,0)]:
            with self.subTest(is_demo=is_demo,redacted=password_hash==self.placeholder):
                with closing(sqlite3.connect(self.source)) as connection:
                    connection.execute('UPDATE users SET password_hash=?, is_demo=? WHERE id=11',(password_hash,is_demo))
                    connection.commit()
                self.refresh_database_checksum()
                with self.assertRaises(RuntimeError):
                    restore_project_data(self.root)
                self.assertFalse((self.root / 'instance/prava.sqlite3').exists())

    def test_credential_writer_failure_never_publishes_an_unusable_database(self):
        self.credential_bundle()
        with patch('project_data._prepare_local_credentials',side_effect=OSError('Injected credential file write failure')) as writer:
            with self.assertRaises((OSError,RuntimeError)):
                restore_project_data(self.root)
            writer.assert_called_once()
        self.assertFalse((self.root / 'instance/prava.sqlite3').exists())
        self.assertEqual(list((self.root / 'instance').glob('.project-data-*.sqlite3')),[])
        # A subsequent launcher run can finish after the file system recovers.
        self.assertTrue(restore_project_data(self.root))
        self.assertEqual(len(self.local_credentials()),len(self.users))

    def test_second_handout_file_failure_leaves_no_database_and_retry_matches_both_files(self):
        self.credential_bundle()
        original_replace = os.replace
        def fail_text_handout(source,destination):
            if Path(destination).name == 'PRAVA_Local_Login_Details.txt':
                raise OSError('Injected second handout file failure')
            return original_replace(source,destination)
        with patch('project_data.os.replace',side_effect=fail_text_handout):
            with self.assertRaises((OSError,RuntimeError)):
                restore_project_data(self.root)
        instance=self.root / 'instance'
        self.assertFalse((instance / 'prava.sqlite3').exists())
        self.assertEqual(list(instance.glob('.project-data-*.sqlite3')),[])
        self.assertEqual(list(instance.glob('.private-login-*')),[])
        self.assertTrue(restore_project_data(self.root))
        credentials=self.local_credentials()
        text=(instance / 'PRAVA_Local_Login_Details.txt').read_text(encoding='utf-8-sig')
        with closing(sqlite3.connect(instance / 'prava.sqlite3')) as connection:
            for username,password_hash in connection.execute('SELECT username,password_hash FROM users'):
                password=credentials[username]['password']
                self.assertIn(password,text)
                self.assertTrue(check_password_hash(password_hash,password))


if __name__ == '__main__':
    unittest.main()
