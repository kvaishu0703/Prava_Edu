# Attendance and Class Timetable

The Student workspace includes **My Attendance** and **Class Timetable**. Staff and Office have **Class timetables**; Staff can view their assigned classes, and Office can view every programme and semester.

## Attendance views

- Academic-year overview: attended sessions, absences, teaching days and weighted percentage.
- Current week, current month and current semester summary cards.
- Twelve monthly cards (June-May); clicking a month opens its daily register.
- Weekly, semester, subject and Theory / Practical / Activity totals.
- Expandable dates showing the time, subject, session type and Present / Absent / Late status.

Percentage is `(Present + Late) / recorded sessions × 100`. Future dates, breaks and unrecorded sessions are excluded. Monthly percentages are not averaged to produce the annual percentage. A period without records displays a dash rather than a fabricated zero or full attendance. Historical attendance remains associated with its subject's semester.

## Project data prepared on 6 October 2026

The project owner requested illustrative attendance from **15 June through 6 October 2026**, five sessions per teaching day, with student percentages between 90% and 98%. The dataset contains **96 teaching days × 5 sessions × 21 students = 10,080 records**. Sundays, 15 August and 2 October are excluded. This is a presentation calendar, not a verified list of all college holidays. Future months are not filled.

Existing generated attendance was replaced; the three manually entered records from 5 October were preserved, including their status and notes. Marks, account passwords and personal profiles remain unchanged, apart from the practical-batch field. Generated attendance is explicitly identified in record provenance; it is not an official attendance register.

Preparation is an explicit operation in `app/services/project_calendar.py`, never automatic on startup. Re-running the launcher preserves later attendance edits. The updated GitHub dataset restores only in a fresh installation, as explained in the main README.

## Timetable source and counting rule

The supplied image is transcribed in `app/data/ty_sem5_timetable.json`: **TY B.Sc. (CA), Hall No. 3, Semester V**, Monday-Saturday, 09:10-16:00. Both breaks and all six original teaching slots remain visible in the reference table. Teacher codes **GRA, WST, MSM, GKL, GAS, TRR and JSM** are retained; their full-name mapping has not been supplied. No identity has been inferred from these initials.

For attendance, the identical **14:00-15:00 and 15:00-16:00 practical rows are combined into one 14:00-16:00 session**, giving five counted sessions. The four morning periods remain separate. TY uses the supplied subject/batch combinations, so its Theory/Practical mix follows the image rather than the illustrative FY/SY mix. Where the photo does not allocate a subject to a particular batch, the project batch view uses **Library / independent project work**, linked to Field Project. These additional activity allocations and A/B/C student assignments are for the presentation and can be replaced with confirmed college allocations.

IOT is present in the supplied timetable but absent from the existing Semester V teaching subjects. It has been added as **TT-IOT-V**, separate from the verified university curriculum catalogue. Existing subject allocations provide the internal Staff account association; the TY displayed teacher code continues to follow the image pending full-name confirmation.

Other programme/semester timetables are illustrative schedules built from saved subjects and allocated staff. They normally use two/three theory periods and two/three practical periods, with a Saturday department activity. All eighteen programme/semester combinations are available. They are class schedules, not a college-wide room or teacher conflict-checked master timetable.

## Staff workflow and data compatibility

Staff → Attendance → select subject and date → **Load** → select the class session/batch → **Load** → record statuses → Save Attendance. A subject taught twice on the same day has separate records for the selected session. Students in other practical batches are excluded from that session's register. Future attendance cannot be submitted.

`upgrade-db` preserves old attendance IDs, values and notes while replacing the old subject/date uniqueness constraint with subject/date/session uniqueness. SQLite migration is transactional; PostgreSQL uses a transactional constraint migration. The local launcher backs up the database before schema upgrades. Both the migration and project preparation have been checked on a separate copy before applying them locally.

## Connected college workflows

Attendance entry follows **select date → load class/session → review saved register → Record/Edit attendance → Save**. Present/Absent (and other applicable statuses) are selected directly in the roster. The register reopens in read mode after saving, with a dated success message and the recorder's actual IST time. Teacher lists are limited to students in the selected teaching subject and practical batch.

Teachers, Principal and Office can enter or correct **today and yesterday** (India dates). Earlier dates are read-only. The main Administrator can correct older staff entries with a reason, or open **Student attendance → select date/student → Correct record** for an older student record. A correction retains the original creation/recorder, adds the actual editor/time, and logs the reason with previous and new values. Future attendance is blocked for every role.

Student attendance now stores the first recorder, actual UTC save timestamp, last editor and last edit timestamp. The interface and CSV convert these timestamps to IST, including the weekday and seconds. Editing attendance never changes its original saved timestamp. Imported historical records retain an unknown original recorder instead of attributing them to the currently allocated teacher; their import time is labelled accordingly.

Principal, Office and Administrator accounts share a staff register under **Staff attendance**. Staff can view only their own register. Actual check-in/out are optional and distinct from the save timestamp. Status/time validation rejects future attendance and invalid time ranges. Each correction retains a before/after audit record. No staff attendance is assumed merely because the module has been enabled.

Class teacher assignments are keyed by programme, curriculum, semester and academic year. The same assignment powers the Admin list, teacher's class roster and student's dashboard/profile. Existing assignments are preserved during subsequent startup. Initial 2026 assignments are project allocations based on the current subject teachers and may be changed by the Admin.

A transaction revision powers connected views. A successful academic/profile change advances this revision; a rollback does not. Authenticated pages poll every 15 seconds and only read-only views refresh automatically. Dirty forms remain in place until the user saves or navigates away. Student attendance, staff attendance and marks forms check the selected register before writing: a stale form preserves its entered values and asks the user to review the latest saved record instead of overwriting another person's changes. The revision endpoint exposes no student names, contact data, marks or staff records. All actual pages still enforce role and record scope.

Marks, materials, assignments, submissions and activity review workflows send scoped in-app notices in the same transaction as their saved changes. Assignment replacement clears the prior evaluation for a fresh review. Pending official NEP results remain pending consistently in both screens and CSV exports.

Official college sports, NSS and department references are linked with their original reporting periods on College Activities. Archived achievements are not inserted as new 2026 events. Portal events continue through registration, staff review, student portfolio and eligible certificate access.

Live refresh connects accounts on the **same server/database**. Independent ZIP installations are separate databases; publishing the GitHub snapshot does not merge later changes from different laptops.
