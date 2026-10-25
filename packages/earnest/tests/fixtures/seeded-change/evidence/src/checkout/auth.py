"""Checkout authentication."""


def member_key(member: str) -> str:
    return member.strip().lower()


# [impl->req~rate-limit~1]
def count_failed_logins(window: int) -> int:
    return max(window, 0)


# [impl->req~lockout-notice~1]
def lockout_message() -> str:
    return f"Try again in {lockout_minutes(5)} minutes."


def lockout_minutes(failures: int) -> int:
    return 15 if failures >= 5 else 0


# [impl->req~audit-log~1]
def audit_lockout(member: str) -> str:
    return member_key(member)
