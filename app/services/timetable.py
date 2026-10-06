"""Shared calendar and class-timetable queries."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from app.models import Subject, TimetableSlot

DAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')
SESSION_TYPES = ('Theory', 'Practical', 'Activity')


def college_today():
    return datetime.now(ZoneInfo('Asia/Kolkata')).date()


def academic_year_for(day):
    return day.year if day.month >= 6 else day.year - 1


def year_bounds(year):
    return date(year, 6, 1), date(year + 1, 5, 31)


def student_slots(student, year=None):
    year = year if year is not None else academic_year_for(college_today())
    return TimetableSlot.query.join(TimetableSlot.subject).filter(
        Subject.is_active.is_(True),
        TimetableSlot.course_id == student.course_id,
        TimetableSlot.curriculum_id == student.curriculum_id,
        TimetableSlot.semester == student.semester,
        TimetableSlot.academic_year == year,
        TimetableSlot.batch.in_(['All', student.practical_batch or 'A']),
    ).order_by(TimetableSlot.weekday, TimetableSlot.session_number).all()


def timetable_days(slots):
    return [{'number': index, 'name': name, 'slots': [slot for slot in slots if slot.weekday == index]}
            for index, name in enumerate(DAYS)]


def slots_for_subject(subject, day):
    return TimetableSlot.query.join(TimetableSlot.subject).filter(
        TimetableSlot.subject_id == subject.id, TimetableSlot.weekday == day.weekday(),
        TimetableSlot.academic_year == academic_year_for(day), Subject.is_active.is_(True),
    ).order_by(TimetableSlot.session_number, TimetableSlot.batch).all()
