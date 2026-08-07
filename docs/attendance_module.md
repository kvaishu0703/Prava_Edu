# Attendance Module

## Overview

The Attendance module allows faculty members to mark attendance for students in their assigned subjects. It supports marking attendance by subject and date, editing existing attendance, and viewing student-wise percentage reports.

## Features Implemented

- Faculty subject/date selection
- Bulk attendance save
- Present, Absent, and Late statuses
- Existing attendance pre-fill for editing
- Duplicate attendance prevention
- Subject-wise attendance report
- Optional month filter
- Low attendance warning below 75%
- Student attendance summary integration

## Security

Attendance routes require the `faculty` role. Faculty members can mark attendance only for subjects assigned to them. Forms are CSRF protected.

## Marathi Summary

या module मध्ये Faculty subject आणि date निवडून students ची attendance mark करू शकतो. Same date साठी पुन्हा save केल्यास duplicate row तयार होत नाही; existing attendance update होते. Report page वर attendance percentage आणि 75% पेक्षा कमी असल्यास warning दिसते.
