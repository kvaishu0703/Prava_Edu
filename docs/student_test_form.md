# Student Test Form

## Purpose

The Student Test Form is a public, shareable PRAVA website quiz. A student can submit basic identity details, answer eight multiple-choice questions about the system, rate the website, and leave feedback without signing in.

## Workflow

1. Open `/student-test`.
2. Enter student details and answer every question.
3. The server calculates the score and stores the response.
4. A confirmation page displays the recorded-response message.
5. `View score` opens a question-wise review with explanations.
6. Admin users can review all submissions at `/admin/student-test-responses`.

## Database

The `student_test_responses` table stores a random public token, student details, serialized answers, score, website rating, feedback, and timestamps. The random UUID prevents predictable result URLs.

## Validation and Security

- Flask-WTF validates required fields, email format, field lengths, question answers, and rating range.
- Global CSRF protection covers the public POST request.
- Correct answers and scoring stay on the server.
- Database errors roll back the transaction.
- The Admin response list remains role-protected.

## Marathi Summary

हा public form studentला login न करता PRAVA websiteवरील आठ MCQ सोडवू देतो. Submit झाल्यावर response databaseमध्ये save होतो, score serverवर calculate होतो आणि Google Formsसारखी confirmation screen दिसते. Adminला सर्व responses आणि feedback स्वतंत्र pageवर पाहता येतात.
