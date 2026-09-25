from datetime import datetime, timezone

def utc_now_iso() -> str:
    """
    Returns a standard ISO 8601 UTC timestamp string: YYYY-MM-DDTHH:MM:SSZ
    Guaranteed valid for standard JavaScript / ECMAScript Date parsers.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
