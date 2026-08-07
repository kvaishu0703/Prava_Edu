# Admin Module

## या module चे उद्दिष्ट

Phase 5 मध्ये Admin साठी master data management तयार केले. Admin आता Students, Faculty, Courses आणि Subjects list करू शकतो, new record add करू शकतो, edit करू शकतो आणि deactivate करू शकतो.

## वापरलेल्या technologies

- Flask Blueprint: `/admin` routes group करण्यासाठी
- Flask-WTF: forms आणि CSRF token साठी
- WTForms Validation: required fields, length, number range तपासण्यासाठी
- Flask-SQLAlchemy: database read/write करण्यासाठी
- Jinja2 Templates: list pages आणि forms render करण्यासाठी

## महत्वाचे concepts

- CRUD: Create, Read, Update, Delete. आपल्या project मध्ये Delete ऐवजी Deactivate वापरले आहे.
- Soft Delete: record delete न करता inactive करणे.
- Duplicate Validation: same username/email/code पुन्हा save होऊ नये म्हणून तपासणी.
- Transaction: database changes commit करणे किंवा error आल्यास rollback करणे.

## संबंधित folders आणि files

- `app/admin/forms.py`: Admin CRUD forms
- `app/admin/routes.py`: Admin list/create/edit/deactivate routes
- `app/templates/admin/admin_base.html`: Admin sidebar layout
- `app/templates/admin/students.html`: Students list
- `app/templates/admin/student_form.html`: Student create/edit form
- `app/templates/admin/faculty.html`: Faculty list
- `app/templates/admin/faculty_form.html`: Faculty create/edit form
- `app/templates/admin/courses.html`: Courses list
- `app/templates/admin/course_form.html`: Course create/edit form
- `app/templates/admin/subjects.html`: Subjects list
- `app/templates/admin/subject_form.html`: Subject create/edit form
- `app/static/css/app.css`: Admin forms, search आणि action button styling

## Code flow

Student create example:

1. Admin `/admin/students/new` page उघडतो.
2. `new_student()` route `StudentForm` तयार करतो.
3. Course choices database मधून load होतात.
4. Form submit झाल्यावर WTForms validation चालते.
5. Duplicate username/email/enrollment तपासले जाते.
6. `User` आणि `Student` objects तयार होतात.
7. Password hash करून save केला जातो.
8. `db.session.commit()` database मध्ये record save करतो.
9. Success flash message दाखवून students list वर redirect होते.

## Request कशी येते?

Browser GET request केल्यावर list किंवा form page render होतो. Browser POST request केल्यावर form data route मध्ये येतो आणि database update होतो.

## Database मध्ये काय होते?

- Student add करताना `users` आणि `students` दोन्ही tables मध्ये record तयार होतो.
- Faculty add करताना `users` आणि `faculty` tables update होतात.
- Course add करताना `courses` table update होतो.
- Subject add करताना `subjects` table update होतो.
- Deactivate करताना `is_active = False` save होते.

## Template कसा render होतो?

Admin CRUD templates `admin/admin_base.html` extend करतात. त्यामुळे sidebar आणि page layout common राहतो. Forms मध्ये `_field.html` macros वापरले आहेत.

## Validation कुठे होते?

Basic field validation `app/admin/forms.py` मध्ये आहे. Duplicate validation `app/admin/routes.py` मधील helper functions मध्ये आहे.

## Security कुठे वापरली आहे?

- सर्व Admin routes वर `@roles_required("admin")` आहे.
- Form submit मध्ये CSRF token आहे.
- Password hash करून save होतो.
- Delete ऐवजी deactivate वापरले आहे.

## Run commands

```powershell
cd D:\parava\prava-college-system
.\.venv\Scripts\Activate.ps1
python seed.py --reset
python run.py
```

Browser मध्ये:

- `http://127.0.0.1:5000/auth/login`
- Admin login: `admin / Admin@123`
- Students: `http://127.0.0.1:5000/admin/students`
- Faculty: `http://127.0.0.1:5000/admin/faculty`
- Courses: `http://127.0.0.1:5000/admin/courses`
- Subjects: `http://127.0.0.1:5000/admin/subjects`

## Expected output

Admin sidebar मधून Students, Faculty, Courses आणि Subjects pages उघडतील. प्रत्येक page वर list, search, add, edit आणि deactivate actions दिसतील.

## Common errors

- `No choices could be validated`: Course seed data नाही. `python seed.py --reset` run कर.
- Duplicate email/username error: आधीच त्या value चा user आहे.
- Password error: new student/faculty तयार करताना password required आहे.

## Practice task

Admin login करून एक new course add कर: Code `MCA`, Name `Master of Computer Applications`, Duration `2 Years`, Semesters `4`.

## Viva प्रश्न

Q: Soft delete का वापरले?

A: Academic records reports साठी नंतर लागतात. Permanent delete केल्यास जुना data हरवू शकतो.

Q: CRUD म्हणजे काय?

A: Create, Read, Update, Delete. म्हणजे record add करणे, पाहणे, edit करणे आणि remove/deactivate करणे.
