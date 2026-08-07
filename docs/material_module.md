# Study Materials Module

## Overview

The Study Materials module allows faculty members to upload subject-wise files and students to search and download active materials for their subjects.

## Features Implemented

- Faculty upload form
- Secure filename handling
- Allowed file extension validation
- Faculty material list and search
- Faculty material download
- Faculty material deactivate workflow
- Student material list and search
- Student material download with subject access control
- Missing-file friendly error messages

## Security

Faculty members can upload materials only for their assigned subjects. Students can download only active materials linked to their course and semester subjects. File names are sanitized using `secure_filename`, and file types are restricted.

## Marathi Summary

या module मध्ये Faculty subject-wise study material upload करू शकतो आणि Student स्वतःच्या subjects चे materials search/download करू शकतो. File upload सुरक्षित ठेवण्यासाठी allowed extensions आणि secure filename वापरले आहे.
