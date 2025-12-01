from datetime import datetime, timezone

def get_utc_now():
    """Get the current time in UTC, timezone-aware."""
    return datetime.now(timezone.utc)
