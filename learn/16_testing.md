# Testing

Status: Completed

Phase 14 madhye `unittest`, Flask test client ani in-memory SQLite vaprun
automated regression tests tayar kele.

Main test file: `tests/test_phase14.py`

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

Login, role access, CSRF, logout, errors, uploads, grading, production config,
PostgreSQL URL ani Admin bootstrap test kele jatat.
