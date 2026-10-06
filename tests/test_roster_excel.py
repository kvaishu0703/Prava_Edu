"""Registration must be atomic, directly usable and private across offices."""
import csv
import io
import json
from datetime import timedelta
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import User, Student, Faculty, RecordImport, Course, Curriculum
from app.services.college_setup import sync_college
from app.services.roster import HEADERS, BASE_HEADERS, encode_roster, validate_roster
from app.services.roster_credentials import HANDOUT_KIND, _cipher

TEMPLATES = Path(__file__).resolve().parents[1] / 'app/data/roster_templates'
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def filled_excel(rows, kind='students', formula=None):
    """Fill the shipped fixture XML, retaining its actual workbook structure."""
    buffer = io.BytesIO()
    with ZipFile(TEMPLATES / f'prava-{kind}-template.xlsx') as source, ZipFile(buffer, 'w', ZIP_DEFLATED) as target:
        for entry in source.infolist():
            value = source.read(entry.filename)
            if entry.filename == 'xl/worksheets/sheet1.xml':
                root = ET.fromstring(value)
                data = root.find(f'{{{NS}}}sheetData')
                data.clear()
                all_rows = [HEADERS[kind]] + [[row.get(field, '') for field in HEADERS[kind]] for row in rows]
                for row_number, values in enumerate(all_rows, 1):
                    element = ET.SubElement(data, f'{{{NS}}}row', r=str(row_number))
                    for index, cell_value in enumerate(values):
                        coordinate = f'{chr(65+index)}{row_number}'
                        cell = ET.SubElement(element, f'{{{NS}}}c', r=coordinate, t='inlineStr')
                        if coordinate == formula:
                            cell.attrib.pop('t')
                            ET.SubElement(cell, f'{{{NS}}}f').text = '1+1'
                            ET.SubElement(cell, f'{{{NS}}}v').text = '2'
                        else:
                            inline = ET.SubElement(cell, f'{{{NS}}}is')
                            ET.SubElement(inline, f'{{{NS}}}t').text = str(cell_value)
                dimension = root.find(f'{{{NS}}}dimension')
                if dimension is not None:
                    dimension.set('ref', f'A1:{chr(64+len(HEADERS[kind]))}{len(all_rows)}')
                value = ET.tostring(root)
            target.writestr(entry, value)
    return buffer.getvalue()


class RosterExcelTest(TestCase):
    password_hash = generate_password_hash('OfficerPassword!123')

    def setUp(self):
        self.app = create_app('testing')
        self.app.config.update(SUPABASE_AUTH_ENABLED=False, ROSTER_CREDENTIAL_KEY=Fernet.generate_key())
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            sync_college()
            for name, role, scope in [('principal','admin','principal'),('office','admin','office'),('staff','faculty','office')]:
                db.session.add(User(username=name, full_name=name.title(), email=name+'@example.test', role=role,
                                    admin_scope=scope, password_hash=self.password_hash))
            db.session.commit()
            self.users = {user.username: user.id for user in User.query.all()}
        self.login('principal')

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, name):
        self.client.post('/auth/logout')
        portal = 'staff' if name == 'staff' else 'administration'
        response = self.client.post('/login/' + portal, data={'username_or_email':name, 'password':'OfficerPassword!123'})
        self.assertEqual(response.status_code, 302)

    def row(self, index=1, **kwargs):
        return dict(full_name='Vaishnavi Kale', username='', email=f'student{index}@example.test', enrollment_number='',
                    programme='BCA', pattern='2024 NEP', semester='5', admission_year='2024', mobile_number='',
                    gender='Female', date_of_birth='2005-07-21', address='Loni', practical_batch='A', **kwargs)

    def upload(self, rows, kind='students', excel=True):
        raw = filled_excel(rows, kind) if excel else encode_roster(rows, kind)
        return self.client.post('/admin/records/import', data={'kind':kind, 'file':(io.BytesIO(raw),'roster.xlsx' if excel else 'roster.csv')})

    def test_principal_excel_creates_active_accounts_and_private_one_time_handout(self):
        response = self.upload([self.row(1), self.row(2)])
        self.assertEqual(response.status_code, 302)
        preview = response.location
        self.assertIn(b'Create accounts and generate passwords', self.client.get(preview).data)
        with self.app.app_context():
            self.assertEqual(Student.query.count(), 0)
            payload = RecordImport.query.one().payload
            self.assertEqual(len({row['username'] for row in payload}), 2)
            self.assertEqual(len({row['enrollment_number'] for row in payload}), 2)
        committed = self.client.post(preview)
        self.assertEqual(committed.status_code, 302)
        handout_path = committed.location
        page = self.client.get(handout_path)
        self.assertEqual(page.status_code, 200)
        self.assertIn('no-store', page.headers['Cache-Control'])
        self.login('office')
        self.assertEqual(self.client.get(handout_path).status_code, 404)
        self.assertEqual(self.client.post(handout_path).status_code, 404)
        self.login('principal')
        downloaded = self.client.post(handout_path)
        self.assertEqual(downloaded.status_code, 200)
        credentials = list(csv.DictReader(io.StringIO(downloaded.data.decode('utf-8-sig'))))
        self.assertEqual(len(credentials), 2)
        self.assertNotEqual(credentials[0]['temporary_password'], credentials[1]['temporary_password'])
        with self.app.app_context():
            students = Student.query.all()
            self.assertEqual(len(students), 2)
            for credential in credentials:
                user = User.query.filter_by(username=credential['login_id']).one()
                self.assertTrue(user.is_active)
                self.assertFalse(user.is_demo)
                self.assertTrue(user.check_password(credential['temporary_password']))
                self.assertGreaterEqual(len(credential['temporary_password']), 20)
                self.assertEqual(user.student_profile.record_source, 'imported')
                self.assertEqual(user.student_profile.semester, 5)
                self.assertEqual(user.student_profile.practical_batch, 'A')
                self.assertEqual(str(user.student_profile.date_of_birth), '2005-07-21')
            self.assertEqual(RecordImport.query.count(), 0)
        self.assertEqual(self.client.post(handout_path).status_code, 404)
        self.assertEqual(self.client.post(preview).status_code, 404)
        with self.client.session_transaction() as session:
            self.assertNotIn(credentials[0]['temporary_password'], json.dumps(dict(session)))
        self.client.post('/auth/logout')
        actual_login = self.client.post(credentials[0]['login_path'], data={'username_or_email':credentials[0]['login_id'], 'password':credentials[0]['temporary_password']})
        self.assertEqual(actual_login.status_code, 302)
        self.assertIn('/student/dashboard', actual_login.location)

    def test_encrypted_storage_expiry_and_rollback_when_handout_cannot_be_saved(self):
        preview = self.upload([self.row()]).location
        with patch('app.office.routes.create_handout', side_effect=OSError('Disk unavailable')):
            self.assertEqual(self.client.post(preview).status_code, 302)
        with self.app.app_context():
            self.assertEqual(Student.query.count(), 0)
        path = self.client.post(preview).location
        with self.app.app_context():
            bundle = RecordImport.query.filter_by(kind=HANDOUT_KIND).one()
            serialized = json.dumps(bundle.payload)
            self.assertNotIn('student1@example.test', serialized)
            self.assertNotIn('Vaishnavi', serialized)
            self.assertNotIn('temporary_password', serialized)
            cipher = Fernet(self.app.config['ROSTER_CREDENTIAL_KEY'])
            plaintext = cipher.decrypt(bundle.payload['ciphertext'].encode())
            self.assertIn(b'temporary_password', plaintext)
            bundle.created_at -= timedelta(hours=2)
            db.session.commit()
        self.assertEqual(self.client.post(path).status_code, 302)
        with self.app.app_context():
            self.assertEqual(RecordImport.query.filter_by(kind=HANDOUT_KIND).count(), 0)
            self.assertEqual(Student.query.count(), 1)

    def test_160_excel_students_all_saved_once_with_unique_ids(self):
        rows = [dict(self.row(index), full_name=f'Student {index}') for index in range(160)]
        preview = self.upload(rows)
        self.assertEqual(preview.status_code, 302)
        commit = self.client.post(preview.location)
        self.assertEqual(commit.status_code, 302)
        download = self.client.post(commit.location)
        credentials = list(csv.DictReader(io.StringIO(download.data.decode('utf-8-sig'))))
        self.assertEqual(len(credentials), 160)
        self.assertEqual(len({row['login_id'] for row in credentials}), 160)
        self.assertEqual(len({row['temporary_password'] for row in credentials}), 160)
        self.assertEqual(len({row['student_or_employee_id'] for row in credentials}), 160)
        repeat = self.upload(rows)
        self.assertIn(b'already exists', repeat.data)
        with self.app.app_context():
            self.assertEqual(Student.query.count(), 160)

    def test_staff_csv_generation_profile_fields_and_csv_formula_protection(self):
        row = dict(full_name='+Patil Teacher', username='', email='teacher@example.test', employee_id='', department='Home Science',
                   qualification='M.Sc.', gender='Female', mobile_number='+919876543210', joining_date='2024-06-15')
        preview = self.upload([row], 'staff', excel=False).location
        path = self.client.post(preview).location
        handout = self.client.post(path)
        credentials = list(csv.DictReader(io.StringIO(handout.data.decode('utf-8-sig'))))
        self.assertEqual(credentials[0]['full_name'], "'+Patil Teacher")
        self.assertEqual(credentials[0]['login_path'], '/login/staff')
        with self.app.app_context():
            teacher = Faculty.query.one()
            self.assertEqual(teacher.mobile_number, '+919876543210')
            self.assertEqual(str(teacher.joining_date), '2024-06-15')
            self.assertEqual(teacher.user.gender, 'Female')
            self.assertTrue(teacher.user.is_active)

    def test_validation_rejects_formula_duplicates_invalid_profiles_and_oversize(self):
        with self.app.app_context():
            with self.assertRaisesRegex(ValueError, 'paste values'):
                validate_roster(filled_excel([self.row()], formula='A2'), 'students', 'roster.xlsx')
            for row, error in [(dict(self.row(), gender='Unknown'), 'Gender'), (dict(self.row(), date_of_birth='2099-10-01'), 'future'),
                               (dict(self.row(), mobile_number='123'), 'Mobile'), (dict(self.row(), semester='9'), 'semester')]:
                with self.assertRaisesRegex(ValueError, error):
                    validate_roster(encode_roster([row], 'students'), 'students')
            with self.assertRaisesRegex(ValueError, 'Duplicate email'):
                validate_roster(encode_roster([self.row(), self.row()], 'students'), 'students')
            with self.assertRaisesRegex(ValueError, 'smaller than'):
                validate_roster(b'x' * (1024*1024+1), 'students')
            with self.assertRaisesRegex(ValueError, '200'):
                validate_roster(encode_roster([self.row(i) for i in range(201)], 'students'), 'students')
            self.assertEqual(Student.query.count(), 0)

    def test_revalidation_collision_preserves_existing_account_and_imports_nothing(self):
        preview = self.upload([self.row(1), self.row(2)]).location
        with self.app.app_context():
            rows = RecordImport.query.one().payload
            db.session.add(User(username=rows[1]['username'], email='competing@example.test', full_name='Existing User', role='student', password_hash=self.password_hash))
            db.session.commit()
        self.assertEqual(self.client.post(preview).status_code, 302)
        with self.app.app_context():
            self.assertEqual(Student.query.count(), 0)
            self.assertEqual(User.query.filter_by(full_name='Existing User').count(), 1)
            self.assertEqual(RecordImport.query.filter_by(kind=HANDOUT_KIND).count(), 0)

    def test_templates_permissions_external_auth_and_csrf(self):
        principal_page = self.client.get('/admin/records/import').data
        self.assertIn(b'Import college records</a>', principal_page)
        self.assertNotIn(b'Office &amp; Principal access', principal_page)
        self.assertNotIn(b'href="/admin/access"', principal_page)
        for kind in ['students', 'staff']:
            response = self.client.get(f'/admin/records/template/{kind}.xlsx')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data.startswith(b'PK'))
            response.close()
        self.assertEqual(self.client.get('/admin/access').status_code, 403)
        self.login('staff')
        self.assertIn('/faculty/dashboard', self.client.get('/admin/records/import').location)
        self.login('principal')
        self.app.config['SUPABASE_AUTH_ENABLED'] = True
        with patch('app.decorators.has_valid_supabase_session', return_value=True):
            response = self.upload([self.row()])
        self.assertIn(b'external authentication', response.data)
        self.app.config['SUPABASE_AUTH_ENABLED'] = False
        preview = self.upload([self.row()]).location
        self.app.config['WTF_CSRF_ENABLED'] = True
        self.assertEqual(self.client.post(preview).status_code, 400)
        with self.app.app_context():
            self.assertEqual(Student.query.count(), 0)

    def test_legacy_csv_and_explicit_id_reservation(self):
        rows = [self.row(1), dict(self.row(2), username='student.vaishnavi.kale', enrollment_number='PRV-STU-2026')]
        with self.app.app_context():
            normalized = validate_roster(encode_roster(rows, 'students'), 'students')
            self.assertNotEqual(normalized[0]['username'], normalized[1]['username'])
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=BASE_HEADERS['students'])
            writer.writeheader()
            writer.writerow({field:self.row()[field] for field in BASE_HEADERS['students']})
            legacy = validate_roster(output.getvalue().encode(), 'students')
            self.assertEqual(legacy[0]['gender'], '')
            self.assertTrue(legacy[0]['username'])

    def test_import_ids_match_manual_editor_canonicalization_and_duplicates(self):
        student_row = dict(self.row(), enrollment_number='prn-mixed-001')
        preview = self.upload([student_row]).location
        with self.app.app_context():
            self.assertEqual(RecordImport.query.one().payload[0]['enrollment_number'], 'PRN-MIXED-001')
        self.assertEqual(self.client.post(preview).status_code, 302)
        with self.app.app_context():
            self.assertEqual(Student.query.one().enrollment_number, 'PRN-MIXED-001')
            course = Course.query.filter_by(code='BCA').one()
            curriculum = Curriculum.query.filter_by(course_id=course.id).one()
            manual = dict(full_name='Another Student', username='another.student', email='another@example.test',
                          password='AccountPassword!2026', enrollment_number='Prn-Mixed-001', course_id=course.id,
                          curriculum_id=curriculum.id, semester=5, admission_year=2024, gender='Female',
                          practical_batch='A', record_source='provided', is_active='y')
        response = self.client.post('/admin/students/new', data=manual)
        self.assertIn(b'Enrollment number already exists', response.data)
        with self.app.app_context():
            self.assertEqual(Student.query.count(), 1)
            with self.assertRaisesRegex(ValueError, 'enrollment / employee number already exists'):
                validate_roster(encode_roster([dict(self.row(2), enrollment_number='prn-mixed-001')], 'students'), 'students')

        staff = dict(full_name='College Teacher', username='', email='newstaff@example.test', employee_id='emp-mixed-001',
                     department='BCA', qualification='M.Sc.')
        preview = self.upload([staff], 'staff', excel=False).location
        with self.app.app_context():
            self.assertEqual(RecordImport.query.filter_by(kind='staff').one().payload[0]['employee_id'], 'EMP-MIXED-001')
        self.assertEqual(self.client.post(preview).status_code, 302)
        self.login('office')
        response = self.client.post('/admin/faculty/new', data=dict(full_name='Another Teacher', username='another.teacher',
            email='another.teacher@example.test', password='AccountPassword!2026', employee_id='emp-mixed-001', department='BCA', is_active='y'))
        self.assertIn(b'Employee ID already exists', response.data)
        with self.app.app_context():
            self.assertEqual(Faculty.query.one().employee_id, 'EMP-MIXED-001')

    def test_initial_key_creation_race_retries_without_replacing_existing_key(self):
        key = Fernet.generate_key()
        with self.app.app_context():
            self.app.config.pop('ROSTER_CREDENTIAL_KEY')
            with patch('app.services.roster_credentials.os.open', side_effect=FileExistsError), \
                 patch('app.services.roster_credentials.Path.mkdir'), \
                 patch('app.services.roster_credentials.Path.read_bytes', side_effect=[b'', b'incomplete', key]) as read, \
                 patch('app.services.roster_credentials.time.sleep') as wait, \
                 patch('app.services.roster_credentials.Fernet.generate_key') as generate:
                cipher = _cipher()
                self.assertEqual(Fernet(key).decrypt(cipher.encrypt(b'private handout')), b'private handout')
                self.assertEqual(read.call_count, 3)
                self.assertEqual(wait.call_count, 2)
                generate.assert_not_called()
            with patch('app.services.roster_credentials.os.open', side_effect=FileExistsError), \
                 patch('app.services.roster_credentials.Path.mkdir'), \
                 patch('app.services.roster_credentials.Path.read_bytes', return_value=b'invalid key') as read, \
                 patch('app.services.roster_credentials.time.sleep'), \
                 patch('app.services.roster_credentials.Fernet.generate_key') as generate:
                with self.assertRaisesRegex(ValueError, 'private credential key is unavailable'):
                    _cipher()
                self.assertEqual(read.call_count, 6)
                generate.assert_not_called()
