# Admin Module

## Overview

The Admin module manages the academic master data required by the rest of PRAVA. In Phase 5, Admin can manage students, faculty, courses, and subjects.

## Features Implemented

- Student list, search, create, edit, deactivate
- Faculty list, search, create, edit, deactivate
- Course list, search, create, edit, deactivate
- Subject list, search, create, edit, deactivate
- Duplicate validation for usernames, emails, enrollment numbers, employee IDs, course codes, and subject codes
- Password hashing for newly created user accounts
- Role-protected Admin routes
- Soft delete style deactivation

## Security

Every Admin page uses role-based access control. Only users with the `admin` role can open these routes. Forms use Flask-WTF CSRF protection, and new passwords are stored as hashes.

## Marathi Summary

या module मध्ये Admin ला Students, Faculty, Courses आणि Subjects manage करता येतात. Delete ऐवजी deactivate वापरले आहे, त्यामुळे जुना academic data सुरक्षित राहतो. Duplicate validation आणि password hashing वापरले आहे.
