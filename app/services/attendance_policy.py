"""College attendance entry window shared by both registers."""
from datetime import timedelta
from app.services.timetable import college_today


def attendance_edit_policy(actor, day, today=None):
    today = today or college_today()
    is_administrator = bool(actor and actor.is_active and actor.role == 'admin'
                            and actor.admin_scope == 'administrator')
    if day > today:
        return {'can_edit': False, 'requires_reason': False,
                'message': 'Future attendance cannot be recorded.'}
    old = day < today - timedelta(days=1)
    if old and not is_administrator:
        return {'can_edit': False, 'requires_reason': False,
                'message': 'This date is closed for editing. Today and yesterday can be updated. Ask the main Administrator for an older correction.'}
    if old:
        return {'can_edit': True, 'requires_reason': True,
                'message': 'Administrator correction: enter a reason to change this closed date. Your name, time and reason are recorded.'}
    return {'can_edit': True, 'requires_reason': False,
            'message': 'Today and yesterday can be updated. The actual save time and your name are recorded automatically.'}


def require_attendance_edit(actor, day, reason='', today=None):
    policy = attendance_edit_policy(actor, day, today)
    if not policy['can_edit']:
        raise ValueError(policy['message'])
    reason = (reason or '').strip()
    if policy['requires_reason'] and len(reason) < 5:
        raise ValueError('Enter a correction reason of at least 5 characters for this closed date.')
    if len(reason) > 500:
        raise ValueError('Keep the correction reason within 500 characters.')
    return reason
