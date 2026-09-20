"""Deterministic back links never rely on an external referrer or browser history."""
from flask import request, url_for
from flask_login import current_user


def register_navigation(app):
    @app.context_processor
    def navigation_context():
        endpoint = request.endpoint or ''
        path = request.path
        target, label = url_for('core.index'), 'Back to Home'
        if endpoint == 'auth.student_login':
            target, label = url_for('auth.role_login', role_slug='student'), 'Back to programmes'
        elif endpoint == 'auth.role_login' or endpoint.startswith('registration.signup'):
            target, label = url_for('auth.portal'), 'Back to Login'
        elif path.startswith('/academics/'):
            target, label = url_for('core.courses'), 'Back to Academics'
        elif path.startswith('/about/'):
            target, label = url_for('core.about'), 'Back to About'
        elif current_user.is_authenticated and path.startswith(('/admin/', '/faculty/', '/student/', '/student-test', '/campus/')):
            dashboard = url_for(current_user.role+'.dashboard')
            if path != dashboard:
                target, label = dashboard, 'Back to dashboard'
                for segment in ['students', 'faculty', 'courses', 'subjects', 'notifications', 'assignments', 'materials', 'curriculum', 'registrations']:
                    parent = '/'+current_user.role+'/'+segment
                    if path.startswith(parent+'/'):
                        target, label = parent, 'Back to '+segment.replace('faculty', 'staff')
                        break
        role_label = None
        if current_user.is_authenticated:
            role_label = ('Principal' if current_user.role == 'admin' and current_user.admin_scope == 'principal'
                          else {'student':'Student', 'faculty':'Staff', 'admin':'Administration'}[current_user.role])
        return {'back_url': target, 'back_label': label, 'show_back': path != '/', 'account_role_label': role_label}
