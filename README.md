# PRAVA - College Academic Management System

PRAVA is a beginner-friendly Flask project for managing college academic work for three roles: Admin, Faculty, and Student.

## Project Status

Phases 1 through 15 are completed and tested. The application includes:

- Admin, Faculty, and Student role-based dashboards
- Student/faculty/course/subject management
- Attendance, marks, materials, assignments, notifications, and reports
- CSV exports and print-friendly reports
- Automated authentication, authorization, error, and security tests
- CSRF-protected forms, POST-only logout, secure headers, and production config checks
- Final report, user guide, viva preparation, and production deployment setup

The planned project phases are complete. Optional future work is listed in the final report.

## Local Setup

```powershell
cd D:\parava\prava-college-system
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
python run.py
```

Open `http://127.0.0.1:5000` in your browser.

## Automated Tests

```powershell
cd D:\parava\prava-college-system
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

The Phase 14 suite covers login, password hashing, inactive accounts, role access,
safe redirects, CSRF enforcement, POST-only logout, custom error pages, upload
validation, grading boundaries, security headers, production configuration,
PostgreSQL URL handling, and first-Admin bootstrap.

## Final Documentation

- `docs/final_project_report.md`
- `docs/user_guide.md`
- `docs/deployment_guide.md`
- `docs/viva_guide.md`

## Production Deployment

The repository includes `wsgi.py` and a Render demo blueprint in `render.yaml`.
Read `docs/deployment_guide.md` before deployment, especially the free-tier
database and uploaded-file persistence limitations.

Login page:

```text
http://127.0.0.1:5000/auth/login
```

Progress summary page:

```text
http://127.0.0.1:5000/phase-summary
```

Admin module pages:

```text
http://127.0.0.1:5000/admin/students
http://127.0.0.1:5000/admin/faculty
http://127.0.0.1:5000/admin/courses
http://127.0.0.1:5000/admin/subjects
http://127.0.0.1:5000/admin/notifications
http://127.0.0.1:5000/admin/notifications/new
http://127.0.0.1:5000/admin/reports
```

Faculty module pages:

```text
http://127.0.0.1:5000/faculty/profile
http://127.0.0.1:5000/faculty/subjects
http://127.0.0.1:5000/faculty/students
http://127.0.0.1:5000/faculty/attendance
http://127.0.0.1:5000/faculty/attendance/report
http://127.0.0.1:5000/faculty/attendance/report.csv
http://127.0.0.1:5000/faculty/marks
http://127.0.0.1:5000/faculty/marks/report
http://127.0.0.1:5000/faculty/marks/report.csv
http://127.0.0.1:5000/faculty/materials
http://127.0.0.1:5000/faculty/materials/upload
http://127.0.0.1:5000/faculty/assignments
http://127.0.0.1:5000/faculty/assignments/create
http://127.0.0.1:5000/faculty/notifications
http://127.0.0.1:5000/faculty/notifications/new
```

Student module pages:

```text
http://127.0.0.1:5000/student/profile
http://127.0.0.1:5000/student/subjects
http://127.0.0.1:5000/student/attendance
http://127.0.0.1:5000/student/marks
http://127.0.0.1:5000/student/materials
http://127.0.0.1:5000/student/assignments
http://127.0.0.1:5000/student/notifications
```

To reset the development database and recreate sample data:

```powershell
python seed.py --reset
```

## Supabase Auth Setup

The app can use Supabase Auth for password sign-in while keeping the local Flask database for roles and academic records.

1. In the Supabase dashboard for `Prava Edu`, open **Connect** or **Settings > API Keys**.
2. Copy `.env.example` to `.env`.
3. Set `SUPABASE_AUTH_ENABLED=true`.
4. Set `SUPABASE_URL=https://itrchfxhmapbbwipvrsu.supabase.co`.
5. Set `SUPABASE_PUBLISHABLE_KEY` to your publishable key.
6. Set `SUPABASE_SECRET_KEY` to a server-only secret key so Admin-created users and seeded demo users are also created in Supabase Auth.
7. Run `pip install -r requirements.txt`, then `python seed.py --reset` to create the local demo records and matching Supabase Auth users.

Do not expose `SUPABASE_SECRET_KEY` in browser code or commit a real `.env` file.

## Development Credentials

These accounts will be added in the sample data phase. They are for development only and must be changed before production use.

| Role | Username | Password |
| --- | --- | --- |
| Admin | admin | Admin@123 |
| Faculty | faculty | Faculty@123 |
| Student | student | Student@123 |
