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
