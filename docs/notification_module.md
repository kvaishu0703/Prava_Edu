# Notification Module

Phase 12 adds targeted announcements and read tracking.

## Admin Features

- View all notifications.
- Search notifications.
- Send notifications by target role.
- Optionally filter by course and semester.
- Set optional expiry date/time.
- Deactivate notifications.

## Faculty Features

- View relevant notifications.
- Send notifications to students for an assigned subject.
- Targeting is derived from the selected subject's course and semester.
- Mark visible notifications as read.
- Deactivate notifications created by the same faculty user.

## Student Features

- View notifications targeted to all users, students, or the student's course/semester.
- See read/unread status.
- Mark notifications as read.

## Access Rules

- Admin can create and deactivate any notification.
- Faculty can create student notifications only for assigned subjects.
- Faculty can deactivate only notifications created by that faculty user.
- Student can only mark notifications visible to that student.

## Data Rules

- `notifications` stores the announcement, target, expiry, and active status.
- `notification_reads` stores one read receipt per notification and user.
- Inactive and expired notifications are hidden from user-facing lists.

## Tested Workflow

- Admin created course/semester targeted notification.
- Student received and marked it as read.
- Faculty created subject-wise notification.
- Student received and marked it as read.
- Faculty deactivated own notification.
- Admin deactivated Admin notification.
