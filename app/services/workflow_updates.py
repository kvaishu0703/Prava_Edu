"""Transactional, personal portal notices for academic workflow changes."""
from app.extensions import db
from app.models import ActivityLog, Notification


def notify_user(actor, recipient, notification_type, title, message):
    """Queue with the academic write so rollbacks never publish stale notices."""
    db.session.add(Notification(
        creator=actor, target_user=recipient, target_role=recipient.role,
        notification_type=notification_type, title=title[:150], message=message,
    ))


def record_update(actor, module, action, description):
    db.session.add(ActivityLog(user_id=actor.id, module=module,
                              action=action, description=description))


def notify_subject_students(faculty, subject, notification_type, title, message):
    from app.services.attendance import students_for_subject
    for student in students_for_subject(subject):
        notify_user(faculty.user, student.user, notification_type, title, message)
