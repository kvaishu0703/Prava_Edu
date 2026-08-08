# Student Test Form - शिकण्याच्या नोंदी

## आपण काय तयार केले?

PRAVA website पाहिल्यानंतर studentला भरता येईल असा public test form तयार केला. Formमध्ये student details, आठ MCQ, website rating आणि feedback आहेत.

## Code Flow

1. Browser `/student-test` routeला request पाठवतो.
2. `StudentTestForm` input validation करते.
3. `grade_answers()` serverवर score calculate करते.
4. `StudentTestResponse` response databaseमध्ये save करते.
5. Browser confirmation pageवर redirect होतो.
6. `View score` question-wise result दाखवतो.
7. Admin protected pageमधून responses पाहतो.

## संबंधित Files

- `app/models/student_test.py`: response database model
- `app/services/student_test.py`: questions, correct answers आणि grading
- `app/student/forms.py`: WTForms validation
- `app/core/routes.py`: public form, confirmation आणि score routes
- `app/admin/routes.py`: Admin response list
- `app/templates/core/student_test_*.html`: student-facing pages
- `app/templates/admin/student_test_responses.html`: Admin results page
- `tests/test_student_test.py`: automated tests

## Security

CSRF token form submission सुरक्षित ठेवतो. Correct answers browserमध्ये पाठवले जात नाहीत. Result URLमध्ये random UUID वापरल्यामुळे response ID सहज guess करता येत नाही.

## Practice Task

एका नवीन MCQची भर घाला आणि `TEST_QUESTIONS`मधील correct answer बदलून automated test पुन्हा run करा.

## Viva Question

**Score browserऐवजी serverवर का calculate केला?**

Browserमधील code user बदलू शकतो. Server-side gradingमुळे score विश्वासार्ह राहतो.
