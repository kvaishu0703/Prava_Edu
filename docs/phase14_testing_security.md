# Phase 14 - Testing, Error Handling, and Security Review

Phase 14 adds automated regression coverage and strengthens the application's
security and failure behavior before final documentation and deployment work.

## Completed Work

- Global CSRF protection for POST requests
- CSRF-protected, POST-only logout
- Local-only validation for post-login `next` redirects
- Strong Flask-Login session protection
- HttpOnly and SameSite cookie defaults
- Secure cookies and HSTS in production mode
- Content Security Policy, frame, MIME, referrer, and permissions headers
- No-store browser caching for authentication and protected pages
- Friendly 400, 403, 404, 413, and 500 pages
- Database session rollback after unexpected server errors
- Production secret and Supabase setting validation
- Invalid session ID and assignment-grade boundary hardening

## Running Tests

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

The suite uses an in-memory SQLite database and does not modify the development
database. It covers login, password hashing, inactive accounts, role access,
safe redirects, logout, CSRF, error pages, upload extensions, grade bounds,
security headers, and production configuration.

## Deployment Security Checklist

- Set a unique `SECRET_KEY` with at least 32 characters.
- Use HTTPS so secure cookies and HSTS are effective.
- Keep `.env`, database files, and uploaded private files out of Git.
- Replace all development passwords before deployment.
- Store uploaded files outside the public static directory for production.
- Add server-side rate limiting for login attempts.
- Add MIME/content scanning when untrusted public uploads are enabled.
- Back up the database and uploaded files regularly.
- Run dependency vulnerability scanning before each release.
