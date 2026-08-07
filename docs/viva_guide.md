# PRAVA Viva Guide

## 60-Second Introduction

PRAVA is a Flask-based College Academic Management System with Admin, Faculty,
and Student roles. Admin manages master records and reports. Faculty manages
attendance, marks, materials, assignments, grading, and notices for assigned
subjects. Students view their academic information and submit assignments. The
system uses SQLAlchemy, Flask-Login, Flask-WTF, role guards, secure uploads,
automated tests, SQLite locally, and PostgreSQL for deployment.

## Demonstration Order

1. Login as Admin and show dashboard statistics.
2. Show Student, Faculty, Course, and Subject management.
3. Show Admin notifications and CSV reports.
4. Login as Faculty and show attendance, marks, materials, and assignments.
5. Show submission grading and notification sending.
6. Login as Student and show attendance, marks, downloads, submission, and feedback.
7. Show `/phase-summary`, `/health`, automated test output, and security behavior.

## Common Questions and Answers

### 1. What problem does PRAVA solve?

It centralizes academic records and communication that would otherwise be
spread across registers, spreadsheets, messages, and separate files.

### 2. Why did you choose Flask?

Flask is lightweight, easy to understand, and supports modular blueprints,
extensions, templates, forms, authentication, and ORM integration.

### 3. What is an application factory?

`create_app()` creates and configures the Flask application. It allows separate
development, testing, and production configurations.

### 4. What is a Blueprint?

A Blueprint groups related routes. PRAVA uses separate blueprints for auth,
Admin, Faculty, Student, and public core pages.

### 5. What is ORM?

Object-Relational Mapping lets Python classes represent database tables.
SQLAlchemy converts model queries and changes into SQL operations.

### 6. Why use separate User, Student, and Faculty tables?

User stores shared login data. Student and Faculty store role-specific academic
profile fields, avoiding many empty columns in one large table.

### 7. How is role-based access implemented?

Flask-Login identifies the current user and `roles_required()` verifies the
allowed role before executing a protected route.

### 8. How are passwords protected?

Werkzeug generates a one-way salted password hash. Login checks the supplied
password against that hash; plain passwords are not stored.

### 9. What is CSRF?

Cross-Site Request Forgery tricks a signed-in browser into submitting an
unwanted request. Flask-WTF tokens verify state-changing forms.

### 10. Why is logout POST-only?

Logout changes session state. POST plus CSRF protection prevents another site
from silently logging a user out through an image or link request.

### 11. How do you prevent unauthorized record access?

Routes check the role and service queries also restrict records by the current
Faculty, Student, assigned subject, course, or semester.

### 12. How do you prevent duplicate attendance and submissions?

Database unique constraints define valid combinations, and services update an
existing record instead of blindly inserting a duplicate.

### 13. How are file uploads secured?

The app validates extensions, uses `secure_filename`, adds a UUID name, limits
requests to 10 MB, and checks ownership before download.

### 14. Why use soft deactivation?

Academic records must remain available for history and reports. Setting
`is_active=false` preserves relationships while stopping future use.

### 15. How are grades calculated?

The service validates internal/external marks, calculates the total percentage,
and maps it to the configured grade scale.

### 16. How do notifications reach the right users?

Notifications store target role, optional course, semester, or user fields.
Queries filter active, unexpired notices for the signed-in user.

### 17. How are reports generated?

Service functions build structured rows and the routes return CSV responses.
HTML report pages also have print-friendly CSS.

### 18. What tests were written?

Tests cover authentication, authorization, CSRF, redirects, logout, security
headers, errors, uploads, grade limits, production configuration, PostgreSQL URL
handling, and Admin bootstrap using an in-memory database.

### 19. Why use an in-memory database for tests?

It is isolated and fast. Tests can create and destroy data without modifying the
development database.

### 20. What happens after an unexpected database error?

The transaction is rolled back and the user sees a friendly message or 500 page
instead of internal stack details.

### 21. Why SQLite locally and PostgreSQL in production?

SQLite is simple for learning and local demos. PostgreSQL supports persistent,
concurrent, server-based production workloads.

### 22. What is Gunicorn?

Gunicorn is a production WSGI server that runs the Flask application with worker
processes/threads. Flask's development server is not used for production.

### 23. What is the purpose of environment variables?

They keep secrets and deployment-specific values such as `SECRET_KEY`, database
URL, and Supabase keys outside source code.

### 24. What are the current limitations?

There is no public signup/approval, password-reset email, versioned database
migration, production object storage, login rate limiter, or malware scanner.

### 25. What would you build next?

Admin-approved registration, password reset, object storage, Alembic migrations,
backups, mobile notifications, analytics, and privacy-aware smart attendance.

## Final Viva Advice

- Explain the workflow in your own words instead of memorizing definitions.
- Demonstrate one complete record flow from Admin to Faculty to Student.
- Be honest about limitations and explain the next technical improvement.
- Keep the application, test command, database diagram, and report open before viva.
