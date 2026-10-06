"""Shared, role-checked staff register and class-teacher operations."""
import calendar
import hashlib
import hmac
import json
from datetime import date, datetime, time

from app.extensions import db
from app.models import ActivityParticipation, Attendance, CampusActivity, Course, Curriculum, Faculty, Marks, Student, Subject, User
from app.models.base import utc_now
from app.models.class_teacher import ClassTeacherAssignment
from app.models.staff_attendance import StaffAttendance, StaffAttendanceChange
from app.services.audit_time import college_timestamp
from app.services.attendance_summary import totals
from app.services.student import student_assignments
from app.services.timetable import academic_year_for, college_today, year_bounds

STAFF_ATTENDANCE_STATUSES = ("Present", "Absent", "Leave", "Holiday")


class StaleStaffRegisterError(ValueError):
    """Another administrator has saved this date since the form was opened."""


def staff_register_version(day):
    rows = StaffAttendance.query.filter_by(attendance_date=day).order_by(StaffAttendance.faculty_id).all()
    snapshot = [{"id": row.id, "faculty_id": row.faculty_id, **_values(row),
                 "updated_at": row.updated_at.isoformat(), "updated_by_id": row.updated_by_id} for row in rows]
    raw = json.dumps({"date": day.isoformat(), "rows": snapshot}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _lock_staff_register_write():
    """Keep version comparison and writes atomic for concurrent form saves."""
    connection = db.session.connection()
    if connection.dialect.name == "sqlite":
        driver = connection.connection.driver_connection
        # A prior write in this transaction already holds the SQLite write lock.
        if not driver.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
    else:
        # A stable existing row serializes this short write transaction, including
        # the first entries for a date where no attendance rows exist to lock yet.
        User.query.filter_by(role="admin").order_by(User.id).with_for_update().first()


def month_bounds(month):
    try:
        year, number = map(int, month.split("-"))
        if len(month) != 7 or not 2000 <= year <= 2100:
            raise ValueError
        first = date(year, number, 1)
        return first, date(year, number, calendar.monthrange(year, number)[1])
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Choose a valid month.") from None


def _require_admin(actor):
    if not actor or actor.role != "admin" or not actor.is_active:
        raise PermissionError("Only active administrators or the Principal may update this register.")


def _parse_time(value):
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (ValueError, TypeError):
        raise ValueError("Enter check-in and check-out in HH:MM format.") from None


def _values(row):
    return {"status": row.status, "check_in": row.check_in.isoformat(timespec="minutes") if row.check_in else None,
            "check_out": row.check_out.isoformat(timespec="minutes") if row.check_out else None,
            "remarks": row.remarks or None}


def save_staff_attendance(actor, day, entries, today=None, expected_version=None, correction_reason=""):
    """Validate the complete batch before changing rows; caller commits once."""
    _require_admin(actor)
    today = today or college_today()
    if not isinstance(day, date) or not 2000 <= day.year <= 2100:
        raise ValueError("Choose a valid attendance date.")
    if day > today:
        raise ValueError("Future staff attendance cannot be recorded.")
    correction_reason = (correction_reason or "").strip()
    if len(correction_reason) > 500:
        raise ValueError("Keep the correction reason within 500 characters.")
    if expected_version is not None:
        _lock_staff_register_write()
        # Expire cached register rows so comparison sees the committed state after
        # acquiring the lock, even if this request read the register beforehand.
        for cached in list(db.session.identity_map.values()):
            if isinstance(cached, StaffAttendance) and cached not in db.session.dirty:
                db.session.expire(cached)
        if not isinstance(expected_version, str) or not hmac.compare_digest(staff_register_version(day), expected_version):
            raise StaleStaffRegisterError(
                "Another administrator updated this date. Your unsaved entries are still shown. "
                "Click Reload saved register to review the latest attendance, then enter your changes again.")
    prepared, seen = [], set()
    for entry in entries:
        faculty_id = entry.get("faculty_id")
        if faculty_id in seen:
            raise ValueError("A staff member may only appear once per attendance date.")
        seen.add(faculty_id)
        member = db.session.get(Faculty, faculty_id)
        if not member or not member.user.is_active or member.user.role != "faculty":
            raise ValueError("Choose an active staff member.")
        status = entry.get("status")
        if status not in STAFF_ATTENDANCE_STATUSES:
            raise ValueError("Choose Present, Absent, Leave or Holiday for each selected staff member.")
        check_in, check_out = _parse_time(entry.get("check_in")), _parse_time(entry.get("check_out"))
        if check_out and not check_in:
            raise ValueError(f"Enter check-in before check-out for {member.user.display_name}.")
        if check_in and check_out and check_out <= check_in:
            raise ValueError(f"Check-out must be after check-in for {member.user.display_name}.")
        if status != "Present" and (check_in or check_out):
            raise ValueError(f"Check-in and check-out apply to Present staff only: {member.user.display_name}.")
        remarks = (entry.get("remarks") or "").strip()
        if len(remarks) > 255:
            raise ValueError("Remarks must be 255 characters or fewer.")
        prepared.append((member, status, check_in, check_out, remarks or None))
    changed = 0
    for member, status, check_in, check_out, remarks in prepared:
        row = StaffAttendance.query.filter_by(faculty_id=member.id, attendance_date=day).first()
        previous = _values(row) if row else None
        proposed = {"status": status, "check_in": check_in.isoformat(timespec="minutes") if check_in else None,
                    "check_out": check_out.isoformat(timespec="minutes") if check_out else None, "remarks": remarks}
        if previous == proposed:
            continue
        now = utc_now()
        if row is None:
            row = StaffAttendance(faculty_id=member.id, attendance_date=day, recorded_by_id=actor.id, recorded_at=now)
            db.session.add(row)
        row.status, row.check_in, row.check_out, row.remarks = status, check_in, check_out, remarks
        row.updated_by_id, row.updated_at = actor.id, now
        db.session.add(StaffAttendanceChange(attendance=row, changed_by_id=actor.id, changed_at=now,
                                            previous_values=previous,
                                            current_values={**proposed, **({"correction_reason":correction_reason} if correction_reason else {})}))
        changed += 1
    return changed


def staff_attendance_summary(records):
    counts = {status.lower(): sum(row.status == status for row in records) for status in STAFF_ATTENDANCE_STATUSES}
    working_days = counts["present"] + counts["absent"] + counts["leave"]
    return {**counts, "recorded": len(records), "working_days": working_days,
            "percentage": round(counts["present"] * 100 / working_days, 1) if working_days else None}


def class_teacher_for_student(student, year=None):
    if not student or not student.curriculum_id:
        return None
    year = year if year is not None else academic_year_for(college_today())
    return ClassTeacherAssignment.query.join(Faculty).join(User, Faculty.user_id == User.id).filter(
        ClassTeacherAssignment.course_id == student.course_id,
        ClassTeacherAssignment.curriculum_id == student.curriculum_id,
        ClassTeacherAssignment.semester == student.semester,
        ClassTeacherAssignment.academic_year == year,
        ClassTeacherAssignment.is_active.is_(True), User.is_active.is_(True), User.role == "faculty",
    ).first()


def class_teacher_assignments(faculty_id, year=None):
    year = year if year is not None else academic_year_for(college_today())
    return ClassTeacherAssignment.query.join(Faculty).join(User, Faculty.user_id == User.id).filter(
        ClassTeacherAssignment.faculty_id == faculty_id, ClassTeacherAssignment.academic_year == year,
        ClassTeacherAssignment.is_active.is_(True), User.is_active.is_(True), User.role == "faculty",
    ).order_by(ClassTeacherAssignment.course_id, ClassTeacherAssignment.semester).all()


def students_for_assignment(assignment):
    return Student.query.join(User).filter(
        Student.course_id == assignment.course_id, Student.curriculum_id == assignment.curriculum_id,
        Student.semester == assignment.semester, User.is_active.is_(True), User.role == "student",
    ).order_by(User.full_name).all()


def class_teacher_students(faculty_id, year=None):
    students = {}
    for assignment in class_teacher_assignments(faculty_id, year):
        students.update({student.id: student for student in students_for_assignment(assignment)})
    return sorted(students.values(), key=lambda student: student.user.full_name.casefold())


def save_class_teacher(actor, curriculum_id, semester, academic_year, faculty_id):
    _require_admin(actor)
    curriculum = db.session.get(Curriculum, curriculum_id)
    faculty = db.session.get(Faculty, faculty_id)
    if not curriculum or not curriculum.course.is_active:
        raise ValueError("Choose an active programme and curriculum.")
    if not faculty or not faculty.user.is_active or faculty.user.role != "faculty":
        raise ValueError("Choose an active staff member.")
    if not isinstance(semester, int) or not 1 <= semester <= curriculum.course.total_semesters:
        raise ValueError("Choose a semester available for this programme.")
    if not isinstance(academic_year, int) or not 2000 <= academic_year <= 2100:
        raise ValueError("Enter an academic start year between 2000 and 2100.")
    row = ClassTeacherAssignment.query.filter_by(course_id=curriculum.course_id, curriculum_id=curriculum.id,
        semester=semester, academic_year=academic_year).first()
    if row is None:
        row = ClassTeacherAssignment(course_id=curriculum.course_id, curriculum_id=curriculum.id,
                                      semester=semester, academic_year=academic_year)
        db.session.add(row)
    row.faculty_id, row.assigned_by_id, row.is_active = faculty.id, actor.id, True
    return row


def student_record_scope(actor, student, year=None):
    """Class teachers/Office review all records; subject teachers only their subjects."""
    if not actor or not actor.is_active or actor.role not in {"admin", "faculty"}:
        raise PermissionError("This student record is not available to this account.")
    # A past assignment must not grant access to the current class cohort.
    mentor = class_teacher_for_student(student, academic_year_for(college_today()))
    if actor.role == "admin":
        return {"full_access":True, "subject_ids":None, "mentor":mentor}
    faculty = actor.faculty_profile
    if not faculty:
        raise PermissionError("A faculty profile is required.")
    if mentor and mentor.faculty_id == faculty.id:
        return {"full_access":True, "subject_ids":None, "mentor":mentor}
    subject_ids = [row[0] for row in Subject.query.with_entities(Subject.id).filter_by(
        course_id=student.course_id, curriculum_id=student.curriculum_id, semester=student.semester,
        faculty_id=faculty.id, is_active=True).all()]
    if not subject_ids:
        raise PermissionError("This student is outside your assigned classes and subjects.")
    return {"full_access":False, "subject_ids":subject_ids, "mentor":mentor}


def student_academic_record(actor, student, year=None):
    year = year if year is not None else academic_year_for(college_today())
    scope = student_record_scope(actor, student, year)
    first, last = year_bounds(year)
    attendance_query = Attendance.query.filter(Attendance.student_id == student.id,
        Attendance.attendance_date >= first, Attendance.attendance_date <= min(last, college_today()))
    marks_query = Marks.query.filter_by(student_id=student.id)
    assignments = student_assignments(student)
    if not scope["full_access"]:
        attendance_query = attendance_query.filter(Attendance.subject_id.in_(scope["subject_ids"]))
        marks_query = marks_query.filter(Marks.subject_id.in_(scope["subject_ids"]))
        assignments = [row for row in assignments if row["assignment"].subject_id in scope["subject_ids"]]
    attendance = attendance_query.order_by(Attendance.attendance_date.desc(), Attendance.session_number).all()
    marks = marks_query.join(Marks.subject).order_by(Subject.semester.desc(), Subject.name, Marks.exam_type).all()
    maximum = sum(row.subject.maximum_marks for row in marks)
    participations = []
    if scope["full_access"]:
        participations = ActivityParticipation.query.join(ActivityParticipation.activity).filter(
            ActivityParticipation.student_id == student.id, CampusActivity.is_active.is_(True),
        ).order_by(CampusActivity.starts_at.desc()).limit(10).all()
    return {**scope, "student":student, "year":year, "attendance_summary":totals(attendance),
        "attendance_records":attendance[:20], "marks":marks,
        "marks_percentage":round(sum(row.total_marks for row in marks) * 100 / maximum, 1) if maximum else None,
        "assignments":assignments, "pending_assignments":sum(row["submission"] is None or row["submission"].status == "Pending" for row in assignments),
        "participations":participations}
