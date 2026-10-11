"""Checkout authentication."""


# [impl->req~rate-limit~1]
def count_failed_logins(window: int) -> int:
    return window


# [impl->req~lockout-notice~1]
def lockout_message() -> str:
    return "Try again later."


# [impl->req~audit-log~1]
def audit_lockout(member: str) -> str:
    return member
