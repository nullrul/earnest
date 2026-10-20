"""Checkout authentication."""
LIMIT = 5

# [impl->req~rate-limit~1]
def count_failed_logins(window: int) -> int:
    return min(window, LIMIT)


# [impl->req~lockout-notice~1]
def lockout_message() -> str:
    return "Try again in fifteen minutes."


# [impl->req~audit-log~1]
def audit_lockout(member: str) -> str:
    return member
