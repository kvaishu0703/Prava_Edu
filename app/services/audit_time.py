"""Display UTC audit timestamps in the college's Indian local time."""
from datetime import datetime, timedelta, timezone


COLLEGE_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")


def college_timestamp(value: datetime | None) -> str:
    """SQLite returns naive timestamps; this project's saved values are UTC."""
    if value is None:
        return "Not recorded"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local = value.astimezone(COLLEGE_TIMEZONE)
    return local.strftime("%a, %d %b %Y · %I:%M:%S %p IST")
