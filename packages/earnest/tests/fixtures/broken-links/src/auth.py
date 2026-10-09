"""Sign-in checks for the auth service."""

FAILED_LIMIT = 5
IDLE_MINUTES = 30


# [impl->req~rate-limit~1]
def refuse(failures: int) -> bool:
    """Refuse an attempt after too many failures."""
    return failures >= FAILED_LIMIT


# [impl->req~session-expiry~1]
def expired(idle_minutes: int) -> bool:
    """End a session that sat idle too long."""
    return idle_minutes >= IDLE_MINUTES  # [impl->req~rate-limt~1]


# [impl-req~audit-log~1]
def record(member: str) -> str:
    """Record a sign-in."""
    return member
