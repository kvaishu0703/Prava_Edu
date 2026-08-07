# Marks Module

## या module चे उद्दिष्ट

Phase 9 मध्ये Faculty साठी marks entry system तयार केले. Faculty subject आणि exam type select करून students चे internal आणि external marks save करू शकतो. System total marks आणि grade calculate करते.

## वापरलेल्या technologies

- Flask GET/POST routes
- Flask-WTF selection form
- SQLAlchemy create/update queries
- Jinja2 templates
- Bootstrap tables

## महत्वाचे concepts

- Marks Validation: total marks subject maximum marks पेक्षा जास्त नसावेत.
- Grade Calculation: marks percentage नुसार grade calculate करणे.
- Duplicate Prevention: same student + same subject + same exam type साठी duplicate row न बनवता update करणे.
- Bulk Marks Entry: अनेक students चे marks एकाच form मधून save करणे.

## Grade scale

- 90 किंवा अधिक = A+
- 80 ते 89 = A
- 70 ते 79 = B+
- 60 ते 69 = B
- 50 ते 59 = C
- 40 ते 49 = D
- 40 पेक्षा कमी = F

## संबंधित files

- `app/faculty/forms.py`: `MarksSelectionForm`
- `app/services/marks.py`: validation, grade calculation, bulk save, report helpers
- `app/faculty/routes.py`: `/faculty/marks` आणि `/faculty/marks/report`
- `app/templates/faculty/marks.html`: marks entry page
- `app/templates/faculty/marks_report.html`: marks report page
- `app/templates/student/marks.html`: student marks view

## Code flow

Marks save example:

1. Faculty `/faculty/marks` page उघडतो.
2. Subject आणि exam type select करतो.
3. Students list load होते.
4. Faculty internal आणि external marks enter करतो.
5. `save_bulk_marks()` प्रत्येक row validate करते.
6. Total marks calculate होतात.
7. `calculate_grade()` grade देते.
8. Existing marks असतील तर update, नसतील तर create.
9. `db.session.commit()` save करते.

## Database मध्ये काय होते?

`marks` table मध्ये records save होतात:

- `student_id`
- `subject_id`
- `exam_type`
- `internal_marks`
- `external_marks`
- `total_marks`
- `grade`
- `entered_by`

Unique constraint आहे: `student_id + subject_id + exam_type`. त्यामुळे duplicate marks थांबतात.

## Template कसा render होतो?

Faculty marks page subject/exam filter दाखवते. Existing marks असतील तर internal/external marks pre-filled दिसतात. Report page marks, grade आणि pass/fail status दाखवते.

## Validation कुठे होते?

`app/services/marks.py` मधील `validate_marks()` total marks maximum marks पेक्षा जास्त आहेत का तपासते.

## Security कुठे वापरली आहे?

- `@roles_required("faculty")` मुळे फक्त Faculty marks enter करू शकतो.
- Faculty फक्त स्वतःला assigned subject चे marks enter करू शकतो.
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
- Enter Marks: `http://127.0.0.1:5000/faculty/marks`
- Marks Report: `http://127.0.0.1:5000/faculty/marks/report`
- Student view: `http://127.0.0.1:5000/student/marks`

## Expected output

Faculty marks page वर students table दिसेल. Marks save केल्यावर created/updated message दिसेल. Report page वर grade आणि pass/fail दिसेल. Student login करून marks page वर marks दिसतील.

## Common errors

- Total marks cannot be greater: internal + external marks subject maximum marks पेक्षा जास्त आहेत.
- Selected subject is not assigned: Faculty दुसऱ्या subject चे marks enter करण्याचा प्रयत्न करत आहे.
- Invalid marks: numeric value ऐवजी text enter झाले आहे.

## Practice task

Faculty login करून एका subject साठी `Internal Test` marks enter कर. मग त्याच exam type साठी marks बदलून save कर आणि updated count पाहा.

## Viva प्रश्न

Q: Grade calculation कुठे ठेवले आहे?

A: `app/services/marks.py` मधील `calculate_grade()` function मध्ये.

Q: Duplicate marks कसे prevent केले?

A: Database unique constraint आणि service logic वापरले. Same student, subject आणि exam type असेल तर row update होते.
