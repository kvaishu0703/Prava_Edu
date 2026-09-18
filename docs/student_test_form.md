# Student Test Form

## Purpose

The Student Test Form is a Student-only PRAVA quiz available after student login. A student can submit basic identity details, answer eight multiple-choice questions about the system, rate the student experience, and leave feedback.

## Workflow

1. Log in as a Student.
2. Open `/student-test` from the Student sidebar.
3. Enter student details and answer every question.
4. The server calculates the score and stores the response.
5. A confirmation page displays the recorded-response message.
6. `View score` opens a question-wise review with explanations.
7. Admin users can review all submissions at `/admin/student-test-responses`.

## Database

The `student_test_responses` table stores a random token, student details, serialized answers, score, experience rating, feedback, and timestamps. The random UUID prevents predictable result URLs.

## Validation and Security

- Flask-WTF validates required fields, email format, field lengths, question answers, and rating range.
- Global CSRF protection covers the Student POST request.
- Correct answers and scoring stay on the server.
- Database errors roll back the transaction.
- The form is Student-protected and the Admin response list remains Admin-protected.

## Marathi Summary

हा form फक्त Student login नंतर उपलब्ध आहे. Student आठ MCQ सोडवतो, response databaseमध्ये save होतो, score serverवर calculate होतो आणि confirmation screen दिसते. Adminला सर्व responses आणि feedback स्वतंत्र pageवर पाहता येतात.
