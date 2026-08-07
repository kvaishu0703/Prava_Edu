# PRAVA User Guide

## Open the Application

Local login URL: `http://127.0.0.1:5000/auth/login`

Enter the username or email and password supplied by the Admin. The system
automatically opens the dashboard for the account's role.

## Admin Workflow

1. Open the Admin dashboard and review system totals.
2. Create courses before creating students and subjects.
3. Create Faculty accounts and enter employee details.
4. Create subjects and assign each subject to a Faculty member.
5. Create Student accounts with course, semester, and enrollment details.
6. Use Notifications to send role/course/semester announcements.
7. Use Reports to download CSV files or print report pages.
8. Deactivate accounts or records that should no longer be used.

Admin creates login accounts; Student and Faculty self-signup is not currently
available. Share only the login URL and the individual user's credentials.

## Faculty Workflow

1. Review the dashboard and assigned subjects.
2. Update the Faculty profile if required.
3. Open Students to see learners connected to assigned subjects.
4. Mark attendance by subject and date, then save.
5. Enter marks by subject and exam type, then review the report.
6. Upload study materials using an allowed file format.
7. Create assignments with due dates and optional attachments.
8. Review Student submissions, enter marks, and provide feedback.
9. Send subject-related notifications to Students.

Faculty can work only with subjects assigned to their account.

## Student Workflow

1. Review attendance, marks, assignments, and notifications on the dashboard.
2. Open Profile to view or update allowed personal information.
3. Open Subjects to see the current semester subjects.
4. Open Attendance and Marks to review academic progress.
5. Download available study materials.
6. Open Assignments, download instructions, and submit an allowed file.
7. Review submission status, marks, and Faculty feedback.
8. Mark notifications as read.

## Common Actions

- Use search boxes to filter long lists.
- Use the sidebar to move between modules.
- Use Logout when work is complete, especially on a shared computer.
- Contact Admin if an account is inactive or academic details are incorrect.

## Common Errors

| Error | Meaning and action |
| --- | --- |
| 400 | Request/CSRF token expired; refresh and submit again |
| 403 | Account does not have permission for that action |
| 404 | URL or record was not found |
| 413 | Uploaded file exceeds the 10 MB limit |
| 500 | Unexpected server/database error; retry and contact Admin |

## Allowed Uploads

PDF, Word, PowerPoint, Excel, text, PNG, JPEG, and GIF files are accepted.
Executable files are rejected. Do not upload passwords or sensitive personal
documents unless the deployment has approved secure storage.
