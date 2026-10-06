# Academic portal comparison and PRAVA integration

Reviewed on 7 October 2026 using public institutional documentation. No third-party account was used. Findings describe documented workflows, not a claim of testing those institutions' private systems.

| Public source | Relevant documented workflow | Application in PRAVA |
|---|---|---|
| [Tilak Maharashtra Vidyapeeth, Pune — College ERP Manual](https://www.tmv.edu.in/SiteStaticDocs/TMV%20ERP_Vidyapeeth%20Manual.pdf), printed pages 20–22 | Programme/semester divisions, student batches, class-teacher allocation, teacher subject allocation, class and teacher timetables, and promotion into another academic year/semester. | Keep course, curriculum, semester, batch and class teacher connected. Preserve earlier-year records when a student's current semester advances. |
| [D. Y. Patil Agriculture and Technical University, Kolhapur — ERP Manuals](https://dyp-atu.edu.in/manuals/) | Separate public manuals are offered for students, faculty, academic administrators, parents, attendance and lecture/practical delegation. | Distinct role workspaces and lecture-specific student rosters. A faculty assignment controls access; a class teacher can review their class across academic records. |
| [Frappe Education — Student Portal](https://docs.frappe.io/education/student-portal) | Student timetable, current/previous programme results, attendance and profile views read the corresponding academic records. | Current-year links open the live registers. A separate year selector presents previous academic records without duplicating or overwriting current marks. |
| [Frappe Education — Academic Year](https://docs.frappe.io/education/academic-year) | Academic years have dates, contain terms, and connect student groups, enrolment, assessment and course schedules. | Label every archived record by academic year and study year, with semester sections and a consistent June–May local project calendar. |
| [Frappe Education — Student Attendance](https://docs.frappe.io/education/student-attendance) | Attendance is selected by student, course schedule, group and date; the attendance tool supports bulk entry. | Teacher entry selects date and lecture, loads the eligible class/batch, and saves explicit statuses with audit times and conflict protection. |

These comparisons support the implementation choices above. The Today/Yesterday edit limit and main-administrator correction workflow are PRAVA's selected policy; they are not asserted to be rules of the referenced institutions.

## Academic-history behaviour

- First Year shows the current academic year.
- Second Year adds the preceding First Year archive.
- Third Year adds First and Second Year archives.
- Class progression comes from the student's current semester. Existing admission-year information is preserved, including values awaiting college correction.
- Previous years contain subject attendance counts, assessment totals and assignment completion records. The archive is read-only in the browser.
- Existing live attendance, marks, assignment and submission rows are preserved. Archives use `academic_year_records`, not the current marks uniqueness key.
- Students read only their own history. Administration and the current class teacher can read the full record. Other assigned faculty see only currently assigned subject codes, with totals recomputed from that subset.
- Source metadata distinguishes college-register imports from locally prepared project records. Project preparation is blocked outside local project mode. Grades and SGPA remain pending approved assessment rules; the archive does not manufacture them.

## Import contract

Call `app.services.academic_history.upsert_academic_history(student, academic_year, study_year, snapshot, source_kind=..., provenance=..., actor=..., current_year=...)`. It validates and flushes; the caller commits or rolls back. Repeating the same student/year replaces that archive only.

`academic_year_plan(student, current_year)` returns the allowed current and previous year labels. Only previous years can be passed to the archive writer.

```json
{
  "semesters": [{
    "semester": 1,
    "subjects": [{
      "code": "CA-101",
      "name": "Programming Fundamentals",
      "attendance": {"held": 100, "present": 94, "late": 1, "absent": 5},
      "assessments": [{"exam_type": "Semester", "internal_marks": 25, "external_marks": 58, "maximum_marks": 100, "passing_marks": 40}],
      "assignments": [{"title": "Programming assignment", "status": "Graded", "score": 18, "maximum": 20, "due_date": "2024-09-01", "submitted_date": "2024-08-30"}]
    }]
  }]
}
```

Held attendance must equal Present + Late + Absent. Marks cannot exceed the declared maximum. Assignment dates must belong to that academic year. Unsupported JSON fields, including invented grades/SGPA, are not copied into the stored snapshot.
