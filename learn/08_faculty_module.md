# Faculty Module

## या module चे उद्दिष्ट

Phase 6 मध्ये Faculty role साठी main module pages तयार केले. Faculty आता स्वतःचा profile पाहू आणि edit करू शकतो, assigned subjects पाहू शकतो, assigned students search करू शकतो, assignments overview पाहू शकतो आणि notifications पाहू शकतो.

## वापरलेल्या technologies

- Flask Blueprint: `/faculty` routes group करण्यासाठी
- Flask-Login: current faculty user ओळखण्यासाठी
- Flask-WTF: profile edit form आणि CSRF protection
- SQLAlchemy: assigned data database मधून आणण्यासाठी
- Jinja2 Templates: faculty pages render करण्यासाठी

## महत्वाचे concepts

- Profile Management: user स्वतःची basic माहिती update करू शकतो.
- Assigned Data: faculty ला फक्त त्याला assign केलेले subjects/students दाखवणे.
- Search Filter: students list मध्ये नाव, email, enrollment number ने search करणे.
- Service Layer: faculty-specific queries `app/services/faculty.py` मध्ये ठेवणे.

## संबंधित folders आणि files

- `app/faculty/forms.py`: `FacultyProfileForm`
- `app/faculty/routes.py`: Faculty dashboard, profile, subjects, students, assignments, notifications routes
- `app/services/faculty.py`: faculty data helper functions
- `app/templates/faculty/faculty_base.html`: Faculty sidebar layout
- `app/templates/faculty/profile.html`: profile view
- `app/templates/faculty/profile_form.html`: profile edit form
- `app/templates/faculty/subjects.html`: assigned subjects
- `app/templates/faculty/students.html`: assigned students
- `app/templates/faculty/assignments.html`: assignments overview
- `app/templates/faculty/notifications.html`: notifications list

## Code flow

Assigned students example:

1. Faculty browser मधून `/faculty/students` request करतो.
2. `roles_required("faculty")` login आणि role तपासतो.
3. `get_faculty_for_user(current_user)` faculty profile शोधतो.
4. `assigned_students()` faculty च्या subjects मधून course आणि semester काढतो.
5. त्या course/semester मधील active students database मधून येतात.
6. `faculty/students.html` template table render करते.

## Database मध्ये काय होते?

Profile edit केल्यावर `users` आणि `faculty` tables update होतात. बाकी pages database मधून data read करतात.

## Template कसा render होतो?

Faculty pages `faculty/faculty_base.html` extend करतात. त्यामुळे sidebar common राहतो. Dashboard अजून reusable `dashboard_shell.html` वापरतो.

## Validation कुठे होते?

`FacultyProfileForm` मध्ये required fields, email pattern आणि length validation आहे. Email duplicate आहे का हे route helper function तपासतो.

## Security कुठे वापरली आहे?

प्रत्येक Faculty route वर `@roles_required("faculty")` आहे. त्यामुळे Admin किंवा Student ला Faculty protected pages दिसत नाहीत. Profile edit form मध्ये CSRF token आहे.

## Run commands

```powershell
cd D:\parava\prava-college-system
.\.venv\Scripts\Activate.ps1
python seed.py --reset
python run.py
```

Browser मध्ये:

- `http://127.0.0.1:5000/auth/login`
- Faculty login: `faculty / Faculty@123`
- Profile: `http://127.0.0.1:5000/faculty/profile`
- Subjects: `http://127.0.0.1:5000/faculty/subjects`
- Students: `http://127.0.0.1:5000/faculty/students`
- Assignments: `http://127.0.0.1:5000/faculty/assignments`
- Notifications: `http://127.0.0.1:5000/faculty/notifications`

## Expected output

Faculty login केल्यावर dashboard दिसेल. Sidebar मधून Profile, Subjects, Students, Assignments आणि Notifications pages उघडतील.

## Common errors

- `Faculty profile is not linked`: user ला faculty profile नाही; Admin मधून faculty record तयार कर.
- No students found: faculty च्या subjects च्या course/semester मध्ये active students नाहीत.
- Email already exists: profile edit करताना दुसऱ्या user चा email वापरला आहे.

## Practice task

Faculty login करून Students page वर search box मध्ये `Vaishnavi` search कर आणि result note कर.

## Viva प्रश्न

Q: Faculty ला assigned students कसे मिळतात?

A: Faculty ला assign झालेले subjects घेतो. त्या subjects मधील course आणि semester घेऊन students table मधून matching students आणतो.

Q: Profile edit मध्ये email duplicate का तपासतो?

A: Login identity unique राहावी म्हणून. दोन users चा same email असेल तर authentication मध्ये गोंधळ होऊ शकतो.
