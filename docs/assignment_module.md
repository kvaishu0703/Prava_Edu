# Assignment and Submission Module

Phase 11 adds a working assignment workflow for Faculty and Student roles.

## Faculty Features

- Create assignments for assigned subjects.
- Upload an optional assignment attachment.
- Search assignment list.
- Download assignment attachment.
- Deactivate assignments.
- View all expected student submissions for an assignment.
- Download submitted files.
- Grade submissions with marks and feedback.

## Student Features

- View assignments for the student's course and semester.
- Download assignment attachments.
- Submit or replace a submission file.
- Download own submitted file.
- View marks and faculty feedback after grading.

## Access Rules

- Faculty can only manage assignments for subjects assigned to that faculty member.
- Student can only see assignments for subjects in their course and semester.
- Student can only download their own submitted file.
- Faculty can only download and grade submissions for their own assignments.

## Upload Rules

- Files are saved under the configured upload folder.
- Assignment attachments use the `assignments` upload subfolder.
- Student submissions use the `submissions` upload subfolder.
- Filenames are sanitized and prefixed with a UUID.
- Unsupported file extensions are rejected.
- Upload size is limited by the app's 10 MB limit.

## Tested Workflow

- Faculty assignment creation with attachment.
- Faculty and Student attachment downloads.
- Student assignment submission.
- Student own submission download.
- Faculty submission list and submission download.
- Faculty grading and feedback.
- Student grade/feedback view.
- Invalid file type rejection.
- Over-maximum marks rejection.
- Assignment deactivate action.
