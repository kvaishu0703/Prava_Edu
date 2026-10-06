"""Shared class-teacher cards use the same saved assignment in all portals."""
from flask import request
from flask_login import current_user
from app.services.campus import class_teacher_assignments, class_teacher_for_student


def register_campus_context(app):
    @app.context_processor
    def mentor_context():
        values = {'my_class_teacher': None, 'my_teacher_classes': []}
        if not current_user.is_authenticated:
            return values
        if current_user.role == 'student' and request.endpoint in {
            'student.dashboard', 'student.profile', 'student.timetable', 'student.attendance'}:
            values['my_class_teacher'] = class_teacher_for_student(current_user.student_profile)
        elif current_user.role == 'faculty' and current_user.faculty_profile and request.endpoint == 'faculty.dashboard':
            values['my_teacher_classes'] = class_teacher_assignments(current_user.faculty_profile.id)
        return values
