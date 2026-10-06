"""Staff register audit, Principal authority and class-teacher isolation."""
from datetime import date, datetime, time
import re
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import ActivityLog, Assignment, Attendance, Course, Curriculum, Faculty, Marks, Student, Subject, Submission, TimetableSlot, User
from app.models.class_teacher import ClassTeacherAssignment
from app.models.staff_attendance import StaffAttendance, StaffAttendanceChange
from app.services.campus import class_teacher_for_student, class_teacher_students, save_class_teacher, save_staff_attendance, staff_attendance_summary, staff_register_version
from app.services.timetable import academic_year_for, college_today


class CampusManagementTests(TestCase):
    def setUp(self):
        self.clock_patch = patch('app.campus.routes.college_today', return_value=date(2026,6,15))
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)
        self.app = create_app("testing")
        self.app.config.update(SUPABASE_AUTH_ENABLED=False, DEMO_MODE=True)
        if "campus" not in self.app.blueprints:
            from app.campus.routes import campus_bp
            self.app.register_blueprint(campus_bp)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.admin = self.user("office", "admin")
        self.principal = self.user("principal", "admin", "principal")
        self.teacher_user = self.user("teacher", "faculty")
        self.other_teacher_user = self.user("other_teacher", "faculty")
        self.student_user = self.user("learner", "student")
        self.other_student_user = self.user("other_learner", "student")
        self.teacher = Faculty(user=self.teacher_user, employee_id="F1", department="BCA")
        self.other_teacher = Faculty(user=self.other_teacher_user, employee_id="F2", department="Home Science")
        self.course = Course(code="BCA", name="Computer Applications", duration="3 years", total_semesters=6)
        self.curriculum = Curriculum(course=self.course, pattern="2024 NEP", effective_year=2024)
        self.other_curriculum = Curriculum(course=self.course, pattern="2019", effective_year=2019)
        self.student = Student(user=self.student_user, enrollment_number="S1", course=self.course,
            curriculum=self.curriculum, semester=1, admission_year=2026)
        self.other_student = Student(user=self.other_student_user, enrollment_number="S2", course=self.course,
            curriculum=self.other_curriculum, semester=1, admission_year=2026)
        db.session.add_all([self.admin, self.principal, self.teacher, self.other_teacher, self.student, self.other_student])
        db.session.commit()
        self.client = self.app.test_client()

    def user(self, username, role, scope="office"):
        user = User(username=username, full_name=username.replace("_", " ").title(), email=f"{username}@example.test",
                    role=role, admin_scope=scope)
        user.set_password("SecureTest@123")
        return user

    def login(self, user):
        response = self.client.post("/auth/login", data={"username_or_email":user.username, "password":"SecureTest@123"})
        self.assertEqual(response.status_code, 302)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def entry(self, member=None, status="Present", **kwargs):
        return {"faculty_id": (member or self.teacher).id, "status": status, **kwargs}

    def assign(self, faculty=None, curriculum=None, year=2026):
        row = save_class_teacher(self.admin, (curriculum or self.curriculum).id, 1, year, (faculty or self.teacher).id)
        db.session.commit()
        return row

    def test_principal_saves_and_correction_preserves_original_recorder(self):
        count = save_staff_attendance(self.principal, date(2026,6,15), [self.entry(check_in="09:00", check_out="16:00")])
        db.session.commit()
        self.assertEqual(count, 1)
        row = StaffAttendance.query.one()
        recorded_at = row.recorded_at
        self.assertEqual(row.check_in, time(9))
        save_staff_attendance(self.admin, date(2026,6,15), [self.entry(status="Leave", remarks="Approved leave")])
        db.session.commit()
        self.assertEqual(row.recorded_by_id, self.principal.id)
        self.assertEqual(row.updated_by_id, self.admin.id)
        self.assertEqual(row.recorded_at, recorded_at)
        self.assertEqual(row.status, "Leave")
        self.assertIsNone(row.check_in)
        self.assertEqual(StaffAttendanceChange.query.count(), 2)
        change = StaffAttendanceChange.query.order_by(StaffAttendanceChange.id.desc()).first()
        self.assertEqual(change.previous_values["status"], "Present")
        self.assertEqual(change.current_values["status"], "Leave")
        self.assertEqual(save_staff_attendance(self.admin, date(2026,6,15), [self.entry(status="Leave", remarks="Approved leave")]), 0)
        db.session.commit()
        self.assertEqual(StaffAttendanceChange.query.count(), 2)

    def test_invalid_rows_future_dates_and_nonadmin_cannot_mutate(self):
        with self.assertRaises(PermissionError):
            save_staff_attendance(self.teacher_user, date(2026,6,15), [self.entry()])
        with self.assertRaisesRegex(ValueError, "Future"):
            save_staff_attendance(self.admin, date(2099,6,15), [self.entry()])
        for bad in [self.entry(status="Invalid"), self.entry(check_out="08:30"),
                    self.entry(check_in="18:00", check_out="08:00"), self.entry(status="Absent", check_in="09:00"),
                    self.entry(check_in="bad"), self.entry(remarks="x"*256)]:
            with self.assertRaises(ValueError):
                save_staff_attendance(self.admin, date(2026,6,15), [self.entry(self.other_teacher), bad])
            self.assertEqual(StaffAttendance.query.count(), 0)

    def test_register_requires_selection_and_principal_post_reaches_staff(self):
        self.login(self.principal)
        self.assertEqual(self.client.get("/campus/staff-attendance").status_code, 200)
        response = self.client.post("/campus/staff-attendance", data={"attendance_date":"2026-06-15"})
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/campus/staff-attendance", data={"attendance_date":"2026-06-15",
            "register_version":staff_register_version(date(2026,6,15)),
            f"status_{self.teacher.id}":"Present", f"check_in_{self.teacher.id}":"09:05", f"check_out_{self.teacher.id}":"16:00"})
        self.assertEqual(response.status_code, 302)
        self.login(self.teacher_user)
        page = self.client.get(f"/campus/my-attendance?month=2026-06&staff={self.other_teacher.id}")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"09:05 AM", page.data)
        self.assertIn(b"Principal", page.data)
        self.assertIn(b"IST", page.data)
        self.assertEqual(self.client.post("/campus/staff-attendance", data={"attendance_date":"2026-06-15"}).status_code, 302)
        self.assertEqual(StaffAttendance.query.count(), 1)

    def test_staff_cannot_read_another_staff_or_student_register(self):
        save_staff_attendance(self.admin, date(2026,6,15), [self.entry(), self.entry(self.other_teacher, "Absent", remarks="Private second record")])
        db.session.commit()
        self.login(self.teacher_user)
        page = self.client.get(f"/campus/my-attendance?month=2026-06&faculty_id={self.other_teacher.id}")
        self.assertNotIn(b"Private second record", page.data)
        self.login(self.student_user)
        self.assertEqual(self.client.get("/campus/my-attendance").status_code, 302)
        self.assertEqual(self.client.get("/campus/staff-attendance").status_code, 302)

    def test_summary_excludes_holiday_and_does_not_invent_absent_days(self):
        for number, status in enumerate(["Present", "Absent", "Leave", "Holiday"], start=15):
            save_staff_attendance(self.admin, date(2026,6,number), [self.entry(status=status)])
        db.session.commit()
        summary = staff_attendance_summary(StaffAttendance.query.all())
        self.assertEqual(summary["working_days"], 3)
        self.assertEqual(summary["percentage"], 33.3)
        self.assertEqual(summary["recorded"], 4)
        self.assertIsNone(staff_attendance_summary([])["percentage"])

    def test_class_teacher_upsert_changes_all_lookup_views_and_isolates_curriculum(self):
        original = self.assign()
        self.assertEqual(class_teacher_for_student(self.student, 2026).id, original.id)
        self.assertIsNone(class_teacher_for_student(self.other_student, 2026))
        self.assertEqual([s.id for s in class_teacher_students(self.teacher.id, 2026)], [self.student.id])
        replaced = self.assign(self.other_teacher)
        self.assertEqual(replaced.id, original.id)
        self.assertEqual(ClassTeacherAssignment.query.count(), 1)
        self.assertEqual(class_teacher_students(self.teacher.id, 2026), [])
        self.assertEqual(class_teacher_for_student(self.student, 2026).faculty_id, self.other_teacher.id)
        self.other_teacher_user.is_active = False
        db.session.commit()
        self.assertIsNone(class_teacher_for_student(self.student, 2026))

    def test_invalid_class_assignments_and_cross_teacher_roster_are_blocked(self):
        assignment = self.assign()
        with self.assertRaises(PermissionError):
            save_class_teacher(self.teacher_user, self.curriculum.id, 1, 2026, self.teacher.id)
        with self.assertRaises(ValueError):
            save_class_teacher(self.admin, self.curriculum.id, 7, 2026, self.teacher.id)
        self.login(self.other_teacher_user)
        self.assertEqual(self.client.get(f"/campus/class-teachers/{assignment.id}/students").status_code, 403)
        self.assertEqual(self.client.post("/campus/class-teachers", data={}).status_code, 403)
        self.login(self.teacher_user)
        page = self.client.get(f"/campus/class-teachers/{assignment.id}/students")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Learner", page.data)
        self.assertNotIn(b"Other Learner", page.data)
        self.login(self.student_user)
        self.assertEqual(self.client.get("/campus/class-teachers").status_code, 302)

    def test_principal_can_assign_and_remove_class_teacher(self):
        self.login(self.principal)
        data = {"curriculum_id":self.curriculum.id, "semester":1, "academic_year":2026, "faculty_id":self.teacher.id}
        self.assertEqual(self.client.post("/campus/class-teachers", data=data).status_code, 302)
        assignment = ClassTeacherAssignment.query.one()
        self.assertEqual(self.client.post(f"/campus/class-teachers/{assignment.id}/remove", data={}).status_code, 302)
        self.assertIsNone(class_teacher_for_student(self.student, 2026))
        self.assertEqual(self.client.get(f"/campus/class-teachers/{assignment.id}/students").status_code, 404)

    def test_csrf_is_required_for_administrative_mutations(self):
        self.login(self.admin)
        self.app.config["WTF_CSRF_ENABLED"] = True
        response = self.client.post("/campus/staff-attendance", data={"attendance_date":"2026-06-15", f"status_{self.teacher.id}":"Present"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StaffAttendance.query.count(), 0)

    def test_subject_teacher_academic_review_is_limited_to_owned_subjects(self):
        own = Subject(course=self.course, curriculum=self.curriculum, semester=1, faculty=self.teacher,
                      code="OWN", name="Owned assessment", maximum_marks=100)
        other = Subject(course=self.course, curriculum=self.curriculum, semester=1, faculty=self.other_teacher,
                        code="OTHER", name="Other private assessment", maximum_marks=100)
        db.session.add_all([own, other])
        db.session.flush()
        db.session.add_all([
            Marks(student=self.student, subject=own, exam_type="Internal", total_marks=75, internal_marks=25,
                  external_marks=50, entered_by=self.teacher.id),
            Marks(student=self.student, subject=other, exam_type="Internal", total_marks=80, internal_marks=30,
                  external_marks=50, entered_by=self.other_teacher.id),
            Attendance(student=self.student, subject=own, faculty=self.teacher, attendance_date=date(2026,6,15), status="Present"),
            Attendance(student=self.student, subject=other, faculty=self.other_teacher, attendance_date=date(2026,6,15), status="Absent", session_number=2),
        ])
        db.session.commit()
        self.login(self.teacher_user)
        page = self.client.get(f"/campus/students/{self.student.id}?year=2026")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Owned assessment", page.data)
        self.assertNotIn(b"Other private assessment", page.data)
        self.assertIn(b"100.0%", page.data)
        self.assertIn(b"75.0%", page.data)
        self.assertEqual(self.client.get(f"/campus/students/{self.other_student.id}").status_code, 403)
        self.assign()
        page = self.client.get(f"/campus/students/{self.student.id}?year=2026")
        self.assertIn(b"Other private assessment", page.data)
        self.assertIn(b"50.0%", page.data)
        self.assertIn(b"Pending verification", page.data)

    def test_old_mentor_assignment_does_not_grant_access_to_current_cohort(self):
        self.assign(year=2025)
        self.login(self.teacher_user)
        self.assertEqual(self.client.get(f"/campus/students/{self.student.id}?year=2025").status_code, 403)
        self.assertEqual(self.client.get(f"/campus/class-teachers/{ClassTeacherAssignment.query.one().id}/students").status_code, 403)
        self.login(self.admin)
        self.assertEqual(self.client.get(f"/campus/students/{self.student.id}?year=2025").status_code, 200)

    def test_student_cannot_request_another_academic_record(self):
        self.login(self.student_user)
        self.assertEqual(self.client.get(f"/campus/students/{self.other_student.id}").status_code, 302)

    def test_academic_record_shows_the_saved_assignment_score_and_feedback(self):
        subject = Subject(course=self.course, curriculum=self.curriculum, semester=1, faculty=self.teacher,
                          code="LAB", name="Programming lab")
        assignment = Assignment(subject=subject, faculty=self.teacher, title="Lab report", due_date=datetime(2026,10,1), maximum_marks=20)
        submission = Submission(assignment=assignment, student=self.student, status="Graded",
                                marks_obtained=18, faculty_feedback="All exercises completed.")
        db.session.add(submission)
        db.session.commit()
        self.login(self.teacher_user)
        response = self.client.get(f"/campus/students/{self.student.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"All exercises completed.", response.data)
        self.assertIn(b"Graded", response.data)
        self.assertIn(b"18", response.data)

    def timetable_slot(self, curriculum, title):
        subject = Subject(course=self.course, curriculum=curriculum, semester=1, faculty=self.other_teacher,
                          code=f"TT-{curriculum.id}", name=title)
        db.session.add(subject)
        db.session.flush()
        row = TimetableSlot(course_id=self.course.id, curriculum_id=curriculum.id, semester=1,
            academic_year=academic_year_for(college_today()), weekday=0, session_number=1,
            starts_at=time(9,10), ends_at=time(10,10), subject_id=subject.id, faculty_id=self.other_teacher.id,
            session_type="Theory", batch="All", room="Hall 1", source="test")
        db.session.add(row)
        db.session.commit()
        return row

    def test_current_class_teacher_can_view_timetable_without_teaching_its_subject(self):
        self.timetable_slot(self.curriculum, "Mentored class lecture")
        self.timetable_slot(self.other_curriculum, "Restricted other curriculum lecture")
        self.assign(year=academic_year_for(college_today()))
        self.assertEqual(Subject.query.filter_by(faculty_id=self.teacher.id).count(), 0)
        self.login(self.teacher_user)
        page = self.client.get(f"/campus/timetable?class={self.curriculum.id}-1")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Mentored class lecture", page.data)
        self.assertNotIn(b"Restricted other curriculum lecture", page.data)
        forged = self.client.get(f"/campus/timetable?class={self.other_curriculum.id}-1")
        self.assertNotIn(b"Restricted other curriculum lecture", forged.data)

    def test_inactive_or_past_class_teacher_assignment_does_not_grant_timetable_access(self):
        self.timetable_slot(self.curriculum, "Protected current class lecture")
        year = academic_year_for(college_today())
        assignment = self.assign(year=year)
        self.login(self.teacher_user)
        assignment.is_active = False
        db.session.commit()
        page = self.client.get(f"/campus/timetable?class={self.curriculum.id}-1")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn(b"Protected current class lecture", page.data)
        assignment.is_active = True
        assignment.academic_year = year - 1
        db.session.commit()
        page = self.client.get(f"/campus/timetable?class={self.curriculum.id}-1")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn(b"Protected current class lecture", page.data)

    def test_stale_principal_office_register_is_rejected_without_overwriting(self):
        day = date(2026,6,15)
        save_staff_attendance(self.admin, day, [self.entry(), self.entry(self.other_teacher)])
        db.session.commit()
        self.login(self.admin)
        office_page = self.client.get("/campus/staff-attendance?date=2026-06-15&edit=1")
        office_token = re.search(rb'name="register_version"[^>]*value="([^"]+)"', office_page.data).group(1).decode()
        principal_client = self.app.test_client()
        principal_client.post("/auth/login", data={"username_or_email":self.principal.username, "password":"SecureTest@123"})
        principal_page = principal_client.get("/campus/staff-attendance?date=2026-06-15&edit=1")
        principal_token = re.search(rb'name="register_version"[^>]*value="([^"]+)"', principal_page.data).group(1).decode()
        self.assertEqual(office_token, principal_token)
        response = principal_client.post("/campus/staff-attendance", data={"attendance_date":day.isoformat(),
            "register_version":principal_token, f"status_{self.teacher.id}":"Present", f"status_{self.other_teacher.id}":"Leave"})
        self.assertEqual(response.status_code, 302)
        response = self.client.post("/campus/staff-attendance", data={"attendance_date":day.isoformat(),
            "register_version":office_token, f"status_{self.teacher.id}":"Absent", f"status_{self.other_teacher.id}":"Present"})
        self.assertEqual(response.status_code, 409)
        self.assertIn(b"Another administrator updated this date", response.data)
        self.assertIn(b'value="Absent" checked', response.data)
        self.assertEqual(StaffAttendance.query.filter_by(faculty_id=self.teacher.id, attendance_date=day).one().status, "Present")
        self.assertEqual(StaffAttendance.query.filter_by(faculty_id=self.other_teacher.id, attendance_date=day).one().status, "Leave")
        self.assertEqual(StaffAttendanceChange.query.count(), 3)

    def test_register_version_ignores_changes_to_a_different_date(self):
        day = date(2026,6,15)
        save_staff_attendance(self.admin, day, [self.entry()])
        db.session.commit()
        original_token = staff_register_version(day)
        save_staff_attendance(self.principal, date(2026,6,16), [self.entry(status="Leave")])
        db.session.commit()
        self.assertEqual(original_token, staff_register_version(day))
        self.login(self.admin)
        response = self.client.post("/campus/staff-attendance", data={"attendance_date":day.isoformat(),
            "register_version":original_token, f"status_{self.teacher.id}":"Absent"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StaffAttendance.query.filter_by(faculty_id=self.teacher.id, attendance_date=day).one().status, "Absent")

    def test_register_requires_version_token(self):
        self.login(self.admin)
        response = self.client.post("/campus/staff-attendance", data={"attendance_date":"2026-06-15",
            f"status_{self.teacher.id}":"Present"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Reload the staff register before saving", response.data)
        self.assertEqual(StaffAttendance.query.count(), 0)

    def test_staff_register_opens_saved_read_view_and_edit_is_explicit(self):
        day = date(2026,6,15)
        save_staff_attendance(self.principal, day, [self.entry(), self.entry(self.other_teacher, "Leave")])
        db.session.commit()
        self.login(self.principal)
        read = self.client.get("/campus/staff-attendance?date=2026-06-15")
        self.assertEqual(read.status_code, 200)
        self.assertIn(b"data-staff-read-register", read.data)
        self.assertIn(b"Attendance saved", read.data)
        self.assertIn(b"2 of 2 staff", read.data)
        self.assertIn(b"Edit attendance", read.data)
        self.assertIn(b">Yesterday</a>", read.data)
        self.assertNotIn(b'type="radio"', read.data)
        editing = self.client.get("/campus/staff-attendance?date=2026-06-15&edit=1")
        self.assertEqual(editing.status_code, 200)
        self.assertIn(b"Editing attendance", editing.data)
        self.assertEqual(editing.data.count(b'type="radio"'), 8)
        self.assertIn(b'value="Present" checked', editing.data)
        self.assertIn(b'value="Leave" checked', editing.data)
        self.assertNotIn(b'<select class="form-select" name="status_', editing.data)

    def test_principal_yesterday_edit_allowed_and_older_write_denied(self):
        self.login(self.principal)
        yesterday = self.client.get("/campus/staff-attendance?date=2026-06-14&edit=1")
        self.assertIn(b'data-staff-register ', yesterday.data)
        old = self.client.get("/campus/staff-attendance?date=2026-06-13&edit=1")
        self.assertIn(b"This date is closed for editing", old.data)
        self.assertNotIn(b'data-staff-register ', old.data)
        response = self.client.post("/campus/staff-attendance", data={"attendance_date":"2026-06-13",
            "register_version":staff_register_version(date(2026,6,13)), f"status_{self.teacher.id}":"Absent"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StaffAttendance.query.count(), 0)

    def test_main_administrator_older_correction_requires_and_records_reason(self):
        day = date(2026,6,13)
        save_staff_attendance(self.principal, day, [self.entry(check_in="09:00", check_out="16:00")])
        self.admin.admin_scope = "administrator"
        db.session.commit()
        self.login(self.admin)
        version = staff_register_version(day)
        values = {"attendance_date":day.isoformat(), "register_version":version,
            f"status_{self.teacher.id}":"Absent", f"check_in_{self.teacher.id}":"09:00", f"check_out_{self.teacher.id}":"16:00"}
        response = self.client.post("/campus/staff-attendance", data=values)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StaffAttendance.query.one().status, "Present")
        values["correction_reason"] = "Corrected after checking the signed register."
        response = self.client.post("/campus/staff-attendance", data=values, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Attendance for Saturday, 13 June 2026 saved at", response.data)
        self.assertIn(b"data-staff-read-register", response.data)
        row = StaffAttendance.query.one()
        self.assertEqual(row.status, "Absent")
        self.assertIsNone(row.check_in)
        self.assertIsNone(row.check_out)
        change = StaffAttendanceChange.query.order_by(StaffAttendanceChange.id.desc()).first()
        self.assertEqual(change.current_values["correction_reason"], values["correction_reason"])
        self.assertEqual(change.previous_values["check_in"], "09:00")
        audit = ActivityLog.query.filter_by(module="staff_attendance", action="corrected").one()
        self.assertIn(values["correction_reason"], audit.description)
