# Phase 11 - Assignment Module

Status: Tested

या phase मध्ये Faculty assignment create करू शकतो, Student assignment submit करू शकतो, आणि Faculty submitted work ला marks/feedback देऊ शकतो.

## काय तयार केले

- Faculty assignment list, search, attachment download, and deactivate
- Faculty add assignment form
- Student assignment list
- Student assignment submit/resubmit form
- Faculty submission list
- Faculty submission download
- Faculty grade and feedback form
- Student grade and feedback display
- Secure upload path handling for assignment attachments and submissions

## Important Files

- `app/services/assignments.py`
- `app/faculty/forms.py`
- `app/faculty/routes.py`
- `app/student/forms.py`
- `app/student/routes.py`
- `app/templates/faculty/assignments.html`
- `app/templates/faculty/assignment_form.html`
- `app/templates/faculty/assignment_submissions.html`
- `app/templates/faculty/submission_grade_form.html`
- `app/templates/student/assignments.html`
- `app/templates/student/assignment_submit_form.html`

## Workflow

1. Faculty logs in.
2. Faculty creates assignment for assigned subject.
3. Student sees assignment in My Assignments.
4. Student uploads submission file.
5. Faculty opens submissions page.
6. Faculty downloads submission and gives marks/feedback.
7. Student sees graded marks and feedback.

## Testing

Verified:

- Faculty assignment create with attachment
- Faculty and Student attachment download
- Student submission upload and download
- Faculty submission list and download
- Faculty grading with feedback
- Student grade/feedback visibility
- Invalid file extension rejection
- Marks greater than maximum marks rejection
- Assignment deactivate workflow
