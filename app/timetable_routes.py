"""Staff and Office access to the same programme timetables as students."""
from flask import Blueprint, render_template, request
from flask_login import current_user
from app.decorators import roles_required
from app.models import TimetableSlot
from app.services.timetable import academic_year_for, college_today, timetable_days

timetable_bp = Blueprint('timetables', __name__)


@timetable_bp.get('/campus/timetable')
@roles_required('admin', 'faculty')
def index():
    year = academic_year_for(college_today())
    query = TimetableSlot.query.filter_by(academic_year=year)
    if current_user.role == 'faculty':
        faculty = current_user.faculty_profile
        query = query.filter(TimetableSlot.faculty_id == (faculty.id if faculty else -1))
    available = query.order_by(TimetableSlot.course_id, TimetableSlot.semester).all()
    choices = {}
    for slot in available:
        key = f'{slot.curriculum_id}-{slot.semester}'
        choices[key] = {'key':key, 'label':f'{slot.course.code} - Semester {slot.semester}', 'curriculum_id':slot.curriculum_id, 'semester':slot.semester}
    key = request.args.get('class', '')
    selection = choices.get(key) or next(iter(choices.values()), None)
    batch = request.args.get('batch', 'A')
    batch = batch if batch in {'A','B','C'} else 'A'
    slots = []
    if selection:
        slots = TimetableSlot.query.filter_by(curriculum_id=selection['curriculum_id'], semester=selection['semester'], academic_year=year).filter(TimetableSlot.batch.in_(['All',batch])).order_by(TimetableSlot.weekday, TimetableSlot.session_number).all()
    return render_template('timetable.html', choices=list(choices.values()), selection=selection, batch=batch, year=year, days=timetable_days(slots))
