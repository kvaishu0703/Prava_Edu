# Marks Module

## Overview

The Marks module allows faculty members to enter and update marks for students in their assigned subjects. It calculates total marks and grades automatically and provides a faculty report and student view.

## Features Implemented

- Faculty subject and exam type selection
- Bulk marks entry
- Internal and external marks
- Total marks calculation
- Grade calculation
- Maximum marks validation
- Duplicate-safe update workflow
- Faculty marks report
- Student marks view integration

## Security

Marks routes require the `faculty` role. Faculty members can enter marks only for subjects assigned to them. Forms are CSRF protected.

## Marathi Summary

या module मध्ये Faculty students चे marks enter/update करू शकतो. Total marks आणि grade system calculate करते. Same student, subject आणि exam type साठी duplicate marks row तयार होत नाही; existing marks update होतात.
