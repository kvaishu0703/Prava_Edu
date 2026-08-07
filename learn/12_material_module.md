# Study Material Module

## या module चे उद्दिष्ट

Phase 10 मध्ये Study Materials module तयार केला. Faculty notes/files upload करू शकतो, स्वतःचे uploaded materials पाहू शकतो, download करू शकतो आणि deactivate करू शकतो. Student आपल्या subjects चे materials search आणि download करू शकतो.

## वापरलेल्या technologies

- Flask file upload
- Flask-WTF `FileField`
- `secure_filename`
- `send_from_directory`
- SQLAlchemy
- Jinja2 templates

## महत्वाचे concepts

- File Upload: browser मधून server वर file पाठवणे.
- Secure Filename: dangerous file names safe बनवणे.
- Allowed Extensions: फक्त permitted file types accept करणे.
- Download Route: saved file user ला download म्हणून देणे.
- Soft Delete: material delete न करता inactive करणे.

## संबंधित files

- `config.py`: upload folder, allowed extensions, max file size
- `app/faculty/forms.py`: `MaterialUploadForm`
- `app/services/materials.py`: upload, validation, access helpers
- `app/faculty/routes.py`: faculty material routes
- `app/student/routes.py`: student material download route
- `app/templates/faculty/materials.html`: faculty materials list
- `app/templates/faculty/material_form.html`: upload form
- `app/templates/student/materials.html`: student material list/download

## Code flow

Faculty upload example:

1. Faculty `/faculty/materials/upload` page उघडतो.
2. Title, subject, description आणि file select करतो.
3. `MaterialUploadForm` file type validate करते.
4. `secure_filename()` filename safe बनवतो.
5. File `app/static/uploads/materials/` मध्ये save होते.
6. `StudyMaterial` database record create होतो.
7. Faculty materials list वर redirect होते.

## Database मध्ये काय होते?

`study_materials` table मध्ये title, description, subject, faculty, file name, file path, file type आणि active status save होतो.

## Validation कुठे होते?

Allowed extensions:

- PDF, DOC, DOCX
- PPT, PPTX
- XLS, XLSX
- TXT
- PNG, JPG, JPEG, GIF

Max file size: 10 MB.

## Security कुठे वापरली आहे?

- Faculty फक्त स्वतःच्या assigned subject साठी material upload करू शकतो.
- Student फक्त स्वतःच्या subjects चे active materials download करू शकतो.
- `secure_filename` वापरले आहे.
- Missing file असल्यास traceback न दाखवता friendly message येतो.

## Run commands

```powershell
cd D:\parava\prava-college-system
.\.venv\Scripts\Activate.ps1
python run.py
```

Browser मध्ये:

- Faculty upload: `http://127.0.0.1:5000/faculty/materials/upload`
- Faculty materials: `http://127.0.0.1:5000/faculty/materials`
- Student materials: `http://127.0.0.1:5000/student/materials`

## Expected output

Faculty upload केल्यानंतर material list मध्ये file दिसेल. Student login करून matching subject material download करू शकेल.

## Common errors

- This file type is not allowed: unsupported extension upload केली आहे.
- Material file is missing: database record आहे पण file disk वर नाही.
- No active subjects assigned: Faculty ला subject assign नाही.

## Practice task

Faculty login करून एक `.txt` material upload कर. मग Student login करून Materials page वर search करून download कर.

## Viva प्रश्न

Q: `secure_filename` का वापरतो?

A: user-provided filename safe बनवण्यासाठी, path traversal किंवा invalid characters टाळण्यासाठी.

Q: Student कोणते materials download करू शकतो?

A: Student फक्त स्वतःच्या course आणि semester मधील subjects चे active materials download करू शकतो.
