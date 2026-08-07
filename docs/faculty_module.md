# Faculty Module

## Overview

The Faculty module gives teachers access to their own academic workspace. Phase 6 focuses on faculty profile management and read-only academic overview pages. Attendance, marks, material upload, and assignment creation will be expanded in later dedicated phases.

## Features Implemented

- Faculty dashboard with database-backed statistics
- Profile view and edit
- Assigned subjects list
- Assigned students list with search
- Assignments overview
- Notifications overview
- Role-protected Faculty routes
- Faculty sidebar navigation

## Security

All Faculty pages require the `faculty` role. Profile update forms use CSRF protection, and email uniqueness is checked before saving.

## Marathi Summary

या module मध्ये Faculty ला स्वतःचा profile, assigned subjects, assigned students, assignments आणि notifications पाहता येतात. Attendance, marks आणि upload workflows पुढच्या phases मध्ये detail मध्ये तयार केले जातील.
