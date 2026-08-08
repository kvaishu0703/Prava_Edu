# PRAVA Deployment Guide

This guide uses Render as a concrete deployment example. The project includes
`wsgi.py`, `.python-version`, production dependencies, and `render.yaml`.

## Before Deployment

1. Run the automated tests.
2. Confirm `.env`, SQLite files, and uploaded files are not committed.
3. Push the complete project to a GitHub repository.
4. Choose whether the deployment is a temporary demo or will store real data.
5. Replace all development passwords.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

## Render Blueprint Deployment

1. Sign in to Render and choose **New > Blueprint**.
2. Connect the GitHub repository containing `render.yaml`.
3. Enter a private first-Admin email and strong password when prompted.
4. Review the web service and PostgreSQL resources before confirming.
5. Wait for dependency installation, table creation, Admin bootstrap, and
   Gunicorn startup.
6. Open `/health`; it should return `status: ok` and `Phase 15`.
7. Open `/auth/login` and sign in with the bootstrap Admin account.
8. Remove `BOOTSTRAP_ADMIN_PASSWORD` after the first successful login. Future
   deploys skip bootstrap because an Admin already exists.

The blueprint uses:

- Build: `pip install -r requirements.txt`
- Pre-deploy: create tables and bootstrap the first Admin
- Start: Gunicorn bound to Render's `$PORT`
- Health check: `/health`
- Database: Render PostgreSQL through `DATABASE_URL`

## Important Free-Tier Limitation

The included blueprint is intended for a demonstration deployment. A free web
service has an ephemeral local filesystem, so uploaded materials and submissions
can disappear after a restart, spin-down, or redeploy. A free Render PostgreSQL
database also has time and backup limitations.

For real college usage, use one of these storage designs:

- Paid web service with a persistent disk and `UPLOAD_FOLDER` set to its mount
  path, such as `/var/data/prava-uploads`.
- Object storage such as Supabase Storage or S3, followed by a code update so
  uploaded files are not stored on the web service filesystem.

Do not place real academic records on an expiring demo database.

## Optional Supabase Auth

The default blueprint keeps `SUPABASE_AUTH_ENABLED=false`. To enable it, add
these secrets in the Render dashboard:

```text
SUPABASE_AUTH_ENABLED=true
SUPABASE_URL=your-project-url
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
SUPABASE_SECRET_KEY=your-server-only-secret
```

Never put the secret key in browser code, `render.yaml`, or Git.

## Manual Deployment Settings

When deploying without the blueprint, use:

| Setting | Value |
| --- | --- |
| Runtime | Python |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn --workers 2 --threads 4 --bind 0.0.0.0:$PORT wsgi:app` |
| Health path | `/health` |
| Environment | `FLASK_ENV=production` |

Required secrets are `SECRET_KEY` and `DATABASE_URL`. The production secret must
be unique and at least 32 characters.

Create tables and the first Admin before opening the system to users:

```bash
flask --app wsgi:app init-db
flask --app wsgi:app bootstrap-admin
```

The free Render web-service plan does not support a separate pre-deploy command. The included `render.yaml` therefore runs `init-db` and the idempotent `bootstrap-admin` command immediately before Gunicorn in `startCommand`. Existing tables and an existing Admin account are preserved on later restarts.

The bootstrap command reads `BOOTSTRAP_ADMIN_EMAIL`,
`BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_USERNAME`, and
`BOOTSTRAP_ADMIN_NAME`.

## Verification Checklist

- `/health` returns HTTP 200.
- Admin login works and demo passwords do not.
- Secure cookies and HTTPS are active.
- Student and Faculty role restrictions work.
- Database records remain after a redeploy.
- Uploads remain after a redeploy or are stored in object storage.
- 400, 404, 413, and 500 pages do not expose stack traces.
- Database and file backups are configured.

## Troubleshooting

- **Production SECRET_KEY error:** set a unique secret of at least 32 characters.
- **Database driver error:** confirm `psycopg[binary]` installed successfully.
- **Database connection error:** verify `DATABASE_URL` and database availability.
- **No Admin account:** set bootstrap variables and rerun `bootstrap-admin`.
- **Uploads disappear:** configure persistent disk/object storage.
- **Service cannot bind:** ensure Gunicorn binds to `0.0.0.0:$PORT`.

## Official References

- Flask Gunicorn deployment: https://flask.palletsprojects.com/en/stable/deploying/gunicorn/
- Render Flask quickstart: https://render.com/docs/deploy-flask
- Render web services: https://render.com/docs/web-services
- Render Blueprint specification: https://render.com/docs/blueprint-spec
- Render free-tier limitations: https://render.com/docs/free
