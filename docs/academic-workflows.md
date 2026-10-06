# PRAVA academic workflows

Reviewed 6 October 2026. Admin, Staff and Student screens read the same records in the running PRAVA database. A saved change updates the relevant role views; a separate laptop installation has its own database until it connects to the same deployed server.

## Connected screens

| Record | Admin / Principal / Office | Staff | Student |
|---|---|---|---|
| Profile and enrolment | Students: approve sign-up or import; assign programme, 2024 NEP curriculum, semester and practical batch | My students: teaching roster; My classes: class-teacher roster | My profile: account and enrolment; editable personal details and photo |
| Curriculum and teaching subjects | NEP curriculum: source, units and component maxima; Subjects & syllabus: link a verified catalogue subject and allocate teacher | My subjects: links to that subject's syllabus, attendance and marks | Subjects & syllabus: allocated teacher and verified subject outline; My NEP syllabus opens the enrolled semester |
| Class timetable | Class timetables: programme / semester / batch schedules | Class timetables: assigned classes and teaching sessions | Class timetable: own programme, curriculum, semester and practical batch |
| Student attendance | Student attendance: inspect records; main Administrator can correct closed dates with a reason | Attendance: select subject, date and session; fetch eligible students, edit and save | My attendance: daily register plus weekly, monthly, semester and annual summaries; original save and latest update details |
| Staff attendance | Staff attendance: Principal / Office maintain the staff register within the date policy; older corrections require main Administrator and a reason | My staff attendance: own status and recording details | No access to staff attendance records |
| Exam marks and results | Subjects define assessment maxima; Reports & exports includes marks and result status | Marks & grades: select assigned subject and assessment, save scores; Marks reports: matching results and CSV | My marks: own scores, teacher and update time; personal notice links back to results |
| Study materials | Reports & exports includes the material register | Study materials: upload for an assigned subject | Study materials: eligible subject files and download links; new-material notice |
| Assignments | Reports & exports includes assignment/submission counts | Create assignment with IST deadline; review uploaded work and enter score/feedback | Submit work; view submission time, review time and feedback; replacements await fresh review |
| College activities | Publish activities; Principal can inspect participation and verified certificates | Coordinator maintains event details and reviews participation evidence/hours | Register for an eligible event, submit evidence, view My activities and verified participation record |
| Student test | Student tests: inspect responses, including preserved historical responses | Academic assignment reviews remain in Assignments | Test identity comes from the signed-in account; confirmation/score is visible only to its owner and Admin |
| Announcements | Target notices by role, course or semester | Send assigned-subject notices; receive work-submission notices | Receive relevant announcements and personal workflow notices; mark read |

## Operating order

1. Confirm the student's programme, curriculum, semester and batch in **Students**. Subject teaching rosters and student resources use this allocation.
2. Review the official source in **NEP curriculum**, then link the source subject and teacher in **Subjects & syllabus**. Source verification and teaching allocation are separate records.
3. Assign a **Class teacher** for the programme/semester. The class teacher can inspect their class and each student's consolidated academic record; subject attendance and marks entry remain with the allocated teaching faculty.
4. Use **Class timetables** to check the selected subject/session, then record attendance. The same saved rows feed student summaries and office reports.
5. Publish files, assignments, assessment scores and event reviews through their existing staff screens. The related student pages read those records directly.

## Excel registration and account handout

Principal, Office and the main Administrator can use **Import College Records** (`/admin/records/import`). Download the Student or Staff Excel template, fill the **Roster** sheet, upload, inspect the preview and confirm. UTF-8 CSV and the original shorter CSV columns remain supported. Each batch accepts 1–200 people, up to 1 MB.

Blank usernames and college IDs generate unique values shown in the preview; supplied IDs are retained. Names, email and academic/department fields are validated before any account is written. Duplicate usernames, emails or college IDs stop the entire batch. Confirmation revalidates against current database records. An unsuccessful transaction creates no accounts or password handout.

Confirmed accounts are active, with independent random passwords. The importing officer can download a CSV handout once within one hour. The download is a CSRF-protected POST, owner checked and marked `no-store`. Temporary passwords are encrypted in `record_imports` using a private random key at `instance/roster-credentials.key`; no plaintext password is stored in Flask session cookies or logs. Account password hashes remain after the one-time handout is deleted. Expired bundles are unavailable and purged on subsequent imports. Do not include `record_imports` or the private key in a project/database distribution.

Imported students retain `record_source=imported` and their programme/curriculum/semester/batch allocation. New staff require subject or class-teacher allocation. Account creation does not invent academic records. Existing account editors support password resets; this flow does not enforce a first-login password change. External Supabase authentication requires a separate provisioning workflow; the local-account importer rejects that configuration before writing data.

## Dates, saving and concurrent edits

- Attendance is editable for today and yesterday by the authorized register operator. Future attendance is blocked. Only the main Administrator can correct an older date, with an audit reason.
- Audit timestamps are stored in UTC and displayed with weekday, date and time in India Standard Time. Activity start times and assignment deadlines are college-local IST wall times.
- Attendance and marks forms carry a version of the selected register. If another session changes that register, the old form is rejected with **409**, its typed values remain visible, and the operator opens the latest register before re-entering the intended changes.
- Read views check for committed updates every 15 seconds. Entry forms are protected from automatic refresh while work is being entered. A failed/rolled-back save does not publish a workflow notice.
- Assignment marks can be **0**. A blank score is still unentered. Uploading replacement work clears the earlier score/feedback; the teacher reviews the new file.

## Assessment and published-source boundaries

**Marks & grades** is the existing exam-result workflow. Exam dates, venues and instructions can be published as an **Exam** announcement targeted to the relevant class. Weekly lecture slots are class timetable records, not an examination calendar.

NEP internal/external scores use the linked verified maxima. Final grades, pass/fail and SGPA remain pending until the applicable approved grading/component rules are configured; student pages, staff reports and office exports use the same status.

The college activity page distinguishes published portal events from historical college-source references. Historical AQAR reporting years do not create new event dates or student participation. Participation hours do not automatically become academic credits.

New Student Test responses have an immutable account owner. Older responses used editable identity fields; they stay available to Admin with no inferred student owner. A matching typed email alone does not establish ownership.

## ERP workflow references

Frappe Education is a workflow reference, not a runtime dependency. Its [Student Group](https://docs.frappe.io/education/student-group) documentation connects enrolment, group membership and instructors. PRAVA applies the equivalent existing programme/curriculum/semester/batch allocation to its rosters.

Frappe's [Student Attendance Tool](https://docs.frappe.io/education/student-attendance-tool) fetches a group's students for attendance, while [Course Schedule](https://docs.frappe.io/education/course-schedule) connects instructor, subject, room and session. PRAVA uses its teaching subjects and timetable slots for this flow.

The [Student Portal](https://docs.frappe.io/education/student-portal) connects profile, timetable, results and attendance to the signed-in student. PRAVA follows this shared-record approach through its existing role screens and access checks.
