# Student Module

## या module चे उद्दिष्ट

Phase 7 मध्ये Student role साठी academic self-service pages तयार केले. Student आता profile पाहू/edit करू शकतो, subjects, attendance, marks, study materials, assignments आणि notifications पाहू शकतो.

## वापरलेल्या technologies

- Flask Blueprint: `/student` routes group करण्यासाठी
- Flask-Login: current student ओळखण्यासाठी
- Flask-WTF: profile edit form
- SQLAlchemy: student-related academic data read करण्यासाठी
- Jinja2 Templates: student pages render करण्यासाठी

## महत्वाचे concepts

- Self-Service Portal: student स्वतःची माहिती आणि academic status पाहू शकतो.
- Read-only Academic Views: attendance/marks/materials data student पाहतो, पण edit करत नाही.
- Subject-wise Summary: data subject नुसार group करून दाखवणे.
- Search Filter: materials list मध्ये title/subject/code ने search.

## संबंधित files

- `app/student/forms.py`: `StudentProfileForm`
- `app/student/routes.py`: Student dashboard, profile, subjects, attendance, marks, materials, assignments, notifications routes
- `app/services/student.py`: student data helper functions
- `app/templates/student/student_base.html`: Student sidebar layout
- `app/templates/student/profile.html`: profile view
- `app/templates/student/profile_form.html`: profile edit form
- `app/templates/student/subjects.html`: subjects table
- `app/templates/student/attendance.html`: attendance summary
- `app/templates/student/marks.html`: marks summary
- `app/templates/student/materials.html`: study materials
- `app/templates/student/assignments.html`: assignment status
- `app/templates/student/notifications.html`: notifications

## Code flow

Attendance page example:

1. Student `/student/attendance` URL उघडतो.
2. `roles_required("student")` login आणि role तपासतो.
3. `get_student_for_user(current_user)` linked student profile आणतो.
4. `student_attendance_summary()` प्रत्येक subject साठी total, present, absent आणि percentage calculate करते.
5. `student/attendance.html` table आणि progress bar render करते.

## Database मध्ये काय होते?

Profile edit केल्यावर `users` आणि `students` tables update होतात. Subjects, attendance, marks, materials, assignments आणि notifications pages database read करतात.

## Template कसा render होतो?

Student pages `student/student_base.html` extend करतात. त्यामुळे sidebar common राहतो. Dashboard reusable `dashboard_shell.html` वापरतो.

## Validation कुठे होते?

`StudentProfileForm` मध्ये required fields, email format आणि length validation आहे. Duplicate email route मध्ये तपासला जातो.

## Security कुठे वापरली आहे?

प्रत्येक Student route वर `@roles_required("student")` आहे. Student दुसऱ्या role चे pages पाहू शकत नाही. Profile form CSRF protected आहे.

## Run commands

```powershell
cd D:\parava\prava-college-system
.\.venv\Scripts\Activate.ps1
python seed.py --reset
python run.py
```

Browser मध्ये:

- `http://127.0.0.1:5000/auth/login`
- Student login: `student / Student@123`
- Profile: `http://127.0.0.1:5000/student/profile`
- Subjects: `http://127.0.0.1:5000/student/subjects`
- Attendance: `http://127.0.0.1:5000/student/attendance`
- Marks: `http://127.0.0.1:5000/student/marks`
- Materials: `http://127.0.0.1:5000/student/materials`
- Assignments: `http://127.0.0.1:5000/student/assignments`
- Notifications: `http://127.0.0.1:5000/student/notifications`

## Expected output

Student sidebar मधून academic pages उघडतील. Attendance progress bars, marks table, materials search आणि assignment status दिसेल.

## Common errors

- `Student profile is not linked`: user साठी student profile नाही; Admin मधून student record तयार कर.
- No attendance/marks found: sample data seed नाही किंवा त्या student साठी records नाहीत.
- Email already exists: profile edit करताना दुसऱ्या user चा email वापरला आहे.

## Practice task

Student login करून Materials page वर `Python` search कर आणि result note कर.

## Viva प्रश्न

Q: Student स्वतः marks edit करू शकतो का?

A: नाही. Student marks फक्त पाहू शकतो. Marks add/update करण्याची permission Faculty/Admin कडे असते.

Q: Attendance percentage कसा calculate होतो?

A: Present किंवा Late records / total records * 100.
