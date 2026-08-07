# Attendance Module

## या module चे उद्दिष्ट

Phase 8 मध्ये Faculty साठी attendance marking system तयार केले. Faculty subject आणि date select करून त्या subject च्या students ची attendance save करू शकतो. Same date साठी attendance पुन्हा save केल्यास duplicate record तयार होत नाही; existing record update होतो.

## वापरलेल्या technologies

- Flask route GET/POST
- Flask-WTF CSRF protected form
- SQLAlchemy queries आणि transactions
- Jinja2 templates
- Bootstrap table आणि progress bar

## महत्वाचे concepts

- Bulk Save: अनेक students ची attendance एकाच submit मध्ये save करणे.
- Duplicate Prevention: same student + same subject + same date एकदाच save होतो.
- Update Existing Record: duplicate create करण्याऐवजी existing attendance update करणे.
- Attendance Percentage: Present/Late count / total count * 100.
- Low Attendance Warning: 75% पेक्षा कमी attendance असल्यास warning.

## संबंधित files

- `app/faculty/forms.py`: `AttendanceSelectionForm`
- `app/services/attendance.py`: attendance helper functions
- `app/faculty/routes.py`: `/faculty/attendance` आणि `/faculty/attendance/report`
- `app/templates/faculty/attendance.html`: mark/edit attendance page
- `app/templates/faculty/attendance_report.html`: report page
- `app/templates/student/attendance.html`: student summary page

## Code flow

Attendance save example:

1. Faculty `/faculty/attendance` page उघडतो.
2. Subject आणि date select करतो.
3. Students list load होते.
4. Faculty प्रत्येक student साठी Present/Absent/Late select करतो.
5. Form submit झाल्यावर `save_bulk_attendance()` चालते.
6. Existing record असेल तर update होतो, नसेल तर create होतो.
7. `db.session.commit()` changes save करते.
8. Success message मध्ये किती created आणि किती updated ते दिसते.

## Database मध्ये काय होते?

`attendance` table मध्ये records save होतात:

- `student_id`
- `subject_id`
- `faculty_id`
- `attendance_date`
- `status`
- `remarks`

Table मध्ये unique constraint आहे: `student_id + subject_id + attendance_date`. त्यामुळे duplicate attendance थांबते.

## Template कसा render होतो?

Faculty attendance template subject/date filter दाखवते. Selected subject साठी students table render होते. Existing attendance असेल तर status pre-selected दिसतो.

## Validation कुठे होते?

Subject आणि date form मध्ये required आहेत. Route मध्ये selected subject current faculty ला assign आहे का तपासले जाते.

## Security कुठे वापरली आहे?

- `@roles_required("faculty")` मुळे फक्त Faculty attendance mark करू शकतो.
- Faculty फक्त स्वतःच्या assigned subject साठी attendance mark करू शकतो.
- CSRF token form मध्ये आहे.

## Run commands

```powershell
cd D:\parava\prava-college-system
.\.venv\Scripts\Activate.ps1
python seed.py --reset
python run.py
```

Browser मध्ये:

- Faculty login: `faculty / Faculty@123`
- Mark Attendance: `http://127.0.0.1:5000/faculty/attendance`
- Attendance Report: `http://127.0.0.1:5000/faculty/attendance/report`
- Student view: `http://127.0.0.1:5000/student/attendance`

## Expected output

Faculty page वर subject/date select करता येईल. Students table दिसेल. Save केल्यावर success message येईल. Report page वर percentage आणि below 75% warning दिसेल.

## Common errors

- No active subjects assigned: Admin ने faculty ला subject assign केलेला नाही.
- Selected subject is not assigned: URL मध्ये दुसऱ्या faculty चा subject id दिला आहे.
- Database error: duplicate/constraint problem किंवा database locked असू शकते; app restart करून पुन्हा try कर.

## Practice task

Faculty login करून Data Structures subject साठी आजची attendance mark कर. मग त्याच date साठी पुन्हा status बदलून save कर आणि message मध्ये updated count पाहा.

## Viva प्रश्न

Q: Duplicate attendance कशी prevent केली?

A: Database unique constraint आणि service logic वापरले. Same student, subject आणि date असेल तर new row create न करता existing row update होते.

Q: Attendance percentage formula काय आहे?

A: `(Present + Late) / Total attendance records * 100`.
