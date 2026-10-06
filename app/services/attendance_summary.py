"""Compute every attendance view from the same saved session records."""
from collections import defaultdict
from datetime import date, timedelta
from sqlalchemy.orm import joinedload
from app.models import Attendance
from app.services.timetable import academic_year_for, college_today, year_bounds


def totals(records):
    present = sum(record.status == 'Present' for record in records)
    late = sum(record.status == 'Late' for record in records)
    absent = sum(record.status == 'Absent' for record in records)
    total = present + late + absent
    return {'total': total, 'present': present, 'late': late, 'attended': present + late,
            'absent': absent, 'percentage': round((present + late) * 100 / total, 1) if total else None,
            'days': len({record.attendance_date for record in records})}


def build_attendance_overview(student, year=None, month=None, today=None):
    today = today or college_today()
    year = year if year is not None else academic_year_for(today)
    start, end = year_bounds(year)
    records = Attendance.query.options(joinedload(Attendance.subject), joinedload(Attendance.timetable_slot)).filter(
        Attendance.student_id == student.id, Attendance.attendance_date >= start,
        Attendance.attendance_date <= min(end, today),
    ).order_by(Attendance.attendance_date, Attendance.session_number, Attendance.id).all()
    monthly, weekly, semesters, subjects, days = (defaultdict(list) for _ in range(5))
    for record in records:
        day = record.attendance_date
        monthly[day.strftime('%Y-%m')].append(record)
        weekly[day - timedelta(days=day.weekday())].append(record)
        semesters[record.subject.semester].append(record)
        subjects[record.subject_id].append(record)
        days[day].append(record)
    current_month = today.strftime('%Y-%m')
    selected_month = month or (current_month if start <= today <= end else (max(monthly) if monthly else f'{year}-06'))
    months = []
    for index in range(12):
        number = (index + 5) % 12 + 1
        month_year = year if number >= 6 else year + 1
        month_date = date(month_year, number, 1)
        key = month_date.strftime('%Y-%m')
        months.append({'key': key, 'name': month_date.strftime('%B %Y'), 'future': month_date > today, **totals(monthly[key])})
    week_start = today - timedelta(days=today.weekday())
    known_years = {academic_year_for(row[0]) for row in Attendance.query.with_entities(Attendance.attendance_date).filter_by(student_id=student.id).distinct().all()}
    known_years.update([academic_year_for(today), year])
    return {
        'year': year, 'year_options': sorted(known_years, reverse=True), 'year_label': f'{year}-{year+1}',
        'today': today, 'start': min(days) if days else start, 'end': max(days) if days else None,
        'overall': totals(records), 'current_week': totals(weekly[week_start]),
        'week_label': week_start.strftime('%d %b') + ' - ' + min(week_start + timedelta(days=5), today).strftime('%d %b'),
        'current_month': totals(monthly[current_month]), 'month_label': today.strftime('%B %Y'),
        'current_semester': totals(semesters[student.semester]),
        'months': months,
        'weeks': [{'start': key, 'end': min(key+timedelta(days=5), today), **totals(value)} for key, value in sorted(weekly.items(), reverse=True) if value],
        'semesters': [{'semester': key, **totals(value)} for key, value in sorted(semesters.items()) if value],
        'subjects': [{'subject': value[0].subject, **totals(value)} for _, value in sorted(subjects.items(), key=lambda item: item[1][0].subject.name)],
        'session_types': [{'name': kind, **totals([r for r in records if r.session_type == kind])} for kind in ['Theory', 'Practical', 'Activity']],
        'selected_month': selected_month,
        'days': [{'date': key, 'records': sorted(value, key=lambda r: r.session_number), **totals(value)} for key, value in sorted(days.items(), reverse=True) if key.strftime('%Y-%m') == selected_month],
    }
