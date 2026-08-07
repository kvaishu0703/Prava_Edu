# Phase 14 - Testing, Error Handling, and Security

Status: Tested

Ya phase madhye application che important login, role access, error pages ani
security rules automated tests madhun verify kele.

## Kay Shiklo

- Password plain text madhye store karaycha nahi; hash verify karaycha.
- State change karanari logout action GET nasun CSRF-protected POST asavi.
- Login nantar external URL var redirect hou naye mhanun `next` value validate karavi.
- Unexpected database error nantar session rollback karavi.
- File size mothi asel tar user-la friendly 413 page dakhavavi.
- Production madhye default secret key vaprun app start hou deu naye.
- Security headers browser-la framing, MIME sniffing ani unsafe content pasun protect kartat.

## Test Command

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

Tests in-memory SQLite database vapartat, mhanun local development database madhil
sample data badalat nahi.
