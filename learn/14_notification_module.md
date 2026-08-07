# Phase 12 - Notification Module

Status: Tested

या phase मध्ये Admin आणि Faculty notifications पाठवू शकतात. Student आणि Faculty notifications read/unread status सह पाहू शकतात.

## काय तयार केले

- Admin notification center
- Admin send notification form
- Target role, course, and semester filtering
- Admin notification deactivate action
- Faculty subject-wise notification send form
- Faculty own notification deactivate action
- Student notification list
- Faculty notification list
- Read/unread badge
- Mark as read action
- NotificationRead table वापरून read receipt tracking
- Expired/inactive notifications hide करण्याची logic

## Important Files

- `app/services/notifications.py`
- `app/admin/forms.py`
- `app/admin/routes.py`
- `app/faculty/forms.py`
- `app/faculty/routes.py`
- `app/student/forms.py`
- `app/student/routes.py`
- `app/templates/admin/notifications.html`
- `app/templates/admin/notification_form.html`
- `app/templates/faculty/notifications.html`
- `app/templates/faculty/notification_form.html`
- `app/templates/student/notifications.html`

## Workflow

1. Admin logs in and creates a notification.
2. Admin can target all users, students, faculty, or admin.
3. Admin can optionally target a course and semester.
4. Faculty logs in and sends a notification for an assigned subject.
5. Students from that subject's course and semester see the notification.
6. Student marks notification as read.
7. Faculty can also mark visible notifications as read.
8. Admin or creator can deactivate notifications.

## Testing

Verified:

- Admin notification create
- Student receives Admin targeted notice
- Student mark read creates read receipt
- Faculty subject-wise notification create
- Student receives Faculty subject notice
- Faculty own notification deactivate
- Admin notification deactivate
- Notification route smoke tests
