# Changelog

## Phase 1 - 2026-07-29

- Created initial Flask project structure.
- Added application factory, core route, health route, base template, and starter styling.
- Added setup files: `requirements.txt`, `.env.example`, `.gitignore`, and `README.md`.
- Added Marathi learning notes and project progress tracker.
- Verified Python files with no-cache syntax parsing.

## Phase 2 - 2026-07-30

- Added Flask-SQLAlchemy extension setup.
- Added database models for users, students, faculty, courses, subjects, attendance, marks, materials, assignments, submissions, notifications, notification reads, and activity logs.
- Added model relationships, foreign keys, unique constraints, and timestamp helpers.
- Replaced `seed.py` with database initialization and development sample data.
- Added database design documentation with Mermaid ER diagram.
- Expanded Marathi learning notes for database models.
- Added browser-visible phase summary page at `/phase-summary`.
- Seeded the SQLite development database successfully.

## Phase 3 - 2026-07-30

- Added Flask-Login setup and user loader.
- Added login form with Flask-WTF validation and CSRF support.
- Added login/logout routes with password hash verification and inactive user blocking.
- Added role-based access decorator.
- Added protected Admin, Faculty, and Student dashboard placeholders.
- Added auth UI, dashboard shell component, navbar login/logout state, and flash messages.
- Updated phase summary and Marathi learning notes.
- Verified login success/failure, protected route redirect, role mismatch redirect, and logout.

## Phase 4 - 2026-07-30

- Added database-backed dashboard data service.
- Improved reusable dashboard shell with role sidebar, topbar, and stat cards.
- Added richer Admin, Faculty, and Student dashboard panels.
- Improved responsive dashboard CSS for desktop, tablet, and mobile layouts.
- Added UI design documentation and Marathi Phase 4 learning notes.
- Verified Phase Summary, login page, and all role dashboard pages.

## Phase 5 - 2026-07-30

- Added Admin CRUD forms for students, faculty, courses, and subjects.
- Added Admin routes for list, create, edit, search, and deactivate workflows.
- Added duplicate validation for important unique fields.
- Added Admin CRUD templates and shared Admin form field macros.
- Added Admin module documentation and Marathi learning notes.
- Verified Admin list pages, create actions, deactivate workflow, and duplicate course validation.

## Phase 6 - 2026-07-30

- Added Faculty profile form and profile update route.
- Added Faculty module routes for profile, subjects, students, assignments, and notifications.
- Added faculty-specific service helpers for assigned academic data.
- Added Faculty sidebar layout and module templates.
- Updated Phase Summary, docs, and Marathi learning notes for Faculty Module.
- Verified Faculty login, module pages, student search, profile edit, and role protection.

## Phase 7 - 2026-07-30

- Added Student profile form and profile update route.
- Added Student module routes for profile, subjects, attendance, marks, materials, assignments, and notifications.
- Added student-specific service helpers for academic summaries.
- Added Student sidebar layout and module templates.
- Added remaining roadmap documentation and Marathi Student Module notes.
- Verified Student login, module pages, materials search, profile edit, and role protection.

## Phase 8 - 2026-07-31

- Added attendance service helpers for faculty subject choices, student lists, duplicate-safe bulk save, and reports.
- Added Faculty attendance selection form.
- Added Faculty attendance marking and attendance report routes.
- Added attendance marking and report templates.
- Linked Faculty navigation to Attendance pages.
- Added Attendance Module documentation and Marathi learning notes.
- Verified attendance pages, bulk save, duplicate-safe update, filtered report, and student summary.

## Phase 9 - 2026-07-31

- Added marks service helpers for grade calculation, validation, duplicate-safe bulk save, and reports.
- Added Faculty marks selection form.
- Added Faculty marks entry and marks report routes.
- Added marks entry and report templates.
- Linked Faculty navigation to Marks pages.
- Added Marks Module documentation and Marathi learning notes.
- Verified marks pages, bulk save, duplicate-safe update, invalid marks validation, report, and student view.

## Phase 10 - 2026-07-31

- Added upload configuration and allowed material file extensions.
- Added Faculty material upload form.
- Added material service helpers for secure save, faculty access, student access, and download paths.
- Added Faculty material list, upload, download, and deactivate routes.
- Added Student material download route.
- Added Faculty material templates and updated Student material download actions.
- Added Study Materials Module documentation and Marathi learning notes.
- Made auth audit logging resilient so local demo login/logout is not blocked by a read-only SQLite file state.
- Verified Faculty upload/list/download/deactivate flow, Student material search/download, and invalid file type rejection.

## Phase 11 - 2026-07-31

- Added assignment and submission upload configuration.
- Added Faculty assignment create form, action form, and submission grading form.
- Added Student assignment submission form.
- Added assignment service helpers for secure uploads, role-based access, submissions, downloads, and grading.
- Added Faculty assignment create, list, search, attachment download, deactivate, submissions, submission download, and grade routes.
- Added Student assignment submit, assignment attachment download, and own submission download routes.
- Updated Faculty and Student assignment templates with live actions.
- Added Assignment Module documentation and Marathi learning notes.
- Updated phase summary, system overview, roadmap, progress tracker, and README.
- Verified Faculty create/download/deactivate, Student submit/download, Faculty submission list/download/grade, invalid file rejection, and over-maximum marks rejection.

## Phase 12 - 2026-07-31

- Added notification service helpers for targeting, read tracking, admin management, faculty subject notices, and expiry-aware filtering.
- Added Admin notification form, list/create/deactivate routes, and templates.
- Added Faculty notification form, list/create/read/deactivate routes, and templates.
- Added Student notification read action and updated Student notification template with read/unread badges.
- Linked Admin notification pages in Admin navigation and dashboard shell.
- Added Notifications Module documentation and Marathi learning notes.
- Updated phase summary, system overview, roadmap, progress tracker, and README.
- Verified Admin create/deactivate, Faculty subject-wise send/deactivate, Student receive/read, and Faculty/Student notification route smoke tests.

## Phase 13 - 2026-07-31

- Added report service helpers for CSV responses and report row builders.
- Added Admin Reports dashboard.
- Added Admin CSV exports for students, faculty, attendance, marks, assignments, and notifications.
- Added Faculty attendance report CSV export.
- Added Faculty marks report CSV export.
- Added print buttons to report pages and print-friendly CSS.
- Linked Reports in Admin navigation and dashboard shell.
- Added Reports Module documentation and Marathi learning notes.
- Updated phase summary, system overview, roadmap, progress tracker, and README.
- Verified Admin report routes, CSV downloads, Faculty report exports, core Phase 13 routes, and syntax parse.

## Phase 14 - 2026-08-03

- Added global CSRF protection and converted logout to a CSRF-protected POST action.
- Added safe local redirect validation after login.
- Added browser security headers and no-store caching for protected pages.
- Added production secret and Supabase configuration validation.
- Added friendly 400 and 413 pages and database rollback in the 500 handler.
- Hardened invalid session user IDs and negative assignment-grade validation.
- Replaced inline print handlers with CSP-compatible JavaScript events.
- Added 11 automated regression tests for authentication, authorization, errors, uploads, and security.
- Updated Phase Summary, health status, roadmap, README, documentation, and learning notes.

## Phase 15 - 2026-08-06

- Added a production WSGI entrypoint and ProxyFix support.
- Added PostgreSQL URL normalization and Psycopg 3 dependency.
- Added Gunicorn and pinned the deployment Python version.
- Added an idempotent first-Admin bootstrap CLI command.
- Added a Render demo blueprint with PostgreSQL, health check, generated secret, and Admin bootstrap.
- Added the final project report and role-wise user guide.
- Added a detailed deployment guide with persistence warnings and verification steps.
- Added a viva guide with demonstration order and 25 common questions and answers.
- Completed Phase 15 learning notes, roadmap, progress tracker, health status, and Phase Summary.

## Student Test Form - 2026-08-08

- Added a public, shareable Student Test Form with eight PRAVA website MCQs.
- Added server-side scoring, response confirmation, and question-wise score review.
- Added website rating and feedback collection.
- Added an Admin-only response list with scores and feedback.
- Added the `student_test_responses` database table, documentation, and four automated tests.
- Verified the full flow in desktop and mobile browser layouts.
- Updated the Render free-tier start command after Blueprint validation confirmed that free web services do not support `preDeployCommand`.
