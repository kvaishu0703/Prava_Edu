# Database Models

## या module चे उद्दिष्ट

Phase 2 मध्ये आपण PRAVA साठी database foundation तयार केला. Database models म्हणजे Python classes ज्या database tables represent करतात.

## वापरलेल्या technologies

- Flask-SQLAlchemy: Flask app मध्ये ORM वापरण्यासाठी
- SQLite: development database
- Werkzeug Password Hashing: sample users चे passwords hash करण्यासाठी

## महत्वाचे concepts

- Model: database table साठी Python class
- Column: table मधील field
- Primary Key: प्रत्येक record ची unique id
- Foreign Key: एका table चा दुसऱ्या table शी संबंध
- Relationship: SQLAlchemy मध्ये linked records सहज access करण्याची पद्धत
- Unique Constraint: duplicate records थांबवण्यासाठी rule
- Seed Data: testing साठी आधीपासून तयार केलेला sample data

## संबंधित folders आणि files

- `app/extensions.py`: `db = SQLAlchemy()` इथे तयार केला आहे.
- `app/__init__.py`: `db.init_app(app)` करून database Flask app सोबत जोडला आहे.
- `app/models/*.py`: प्रत्येक table साठी स्वतंत्र model file आहे.
- `seed.py`: database tables आणि sample data तयार करण्यासाठी script.
- `docs/database_design.md`: ER diagram आणि database explanation.

## Code flow

`python seed.py` command दिल्यावर:

1. `create_app()` Flask app तयार करते.
2. `app.app_context()` database operations साठी context देते.
3. `db.create_all()` models पाहून tables तयार करते.
4. `create_user()` users तयार करते आणि password hash करते.
5. Course, faculty, students, subjects, attendance, marks, materials, assignments, submissions आणि notifications insert होतात.
6. `db.session.commit()` सर्व changes database मध्ये save करते.

## Database मध्ये काय होते?

SQLite file `instance/prava.sqlite3` मध्ये तयार होईल. त्यात `users`, `students`, `faculty`, `courses`, `subjects`, `attendance`, `marks`, `study_materials`, `assignments`, `submissions`, `notifications`, `notification_reads`, आणि `activity_logs` tables तयार होतील.

## Validation आणि constraints कुठे आहेत?

- Username आणि email duplicate होऊ नयेत म्हणून `unique=True`.
- Same student + same subject + same date attendance duplicate होऊ नये म्हणून `UniqueConstraint`.
- Same assignment साठी same student ची duplicate submission होऊ नये म्हणून `UniqueConstraint`.

## Security कुठे वापरली आहे?

`seed.py` मध्ये passwords plain text म्हणून database मध्ये save केलेले नाहीत. `user.set_password()` password hash करून `password_hash` column मध्ये save करते.

## Run commands

```powershell
cd D:\parava\prava-college-system
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
python run.py
```

Database reset करून sample data पुन्हा तयार करायचा असेल:

```powershell
python seed.py --reset
```

## Expected output

Terminal मध्ये `Database tables and sample data created successfully.` दिसेल. Login accounts:

- Admin: `admin / Admin@123`
- Faculty: `faculty / Faculty@123`
- Student: `student / Student@123`

## Common errors

- `No module named flask_sqlalchemy`: `pip install -r requirements.txt` run कर.
- `UNIQUE constraint failed`: sample data आधीच आहे. `python seed.py --reset` वापर.
- `database is locked`: app बंद करून seed command पुन्हा run कर.

## Practice task

`app/models/student.py` उघड आणि `Student` model मध्ये `course_id` का आहे ते स्वतः समजावून लिही.

## Viva प्रश्न

Q: ORM म्हणजे काय?

A: ORM म्हणजे Object Relational Mapper. आपण Python class वापरून database table सोबत काम करू शकतो, त्यामुळे raw SQL कमी लिहावे लागते.

Q: Foreign key का वापरतो?

A: दोन tables मधील संबंध सुरक्षित ठेवण्यासाठी. उदाहरण: student कोणत्या course मध्ये आहे हे `course_id` foreign key ने समजते.
