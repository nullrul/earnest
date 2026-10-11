"""Tests for the sign-in checks."""

from src.auth import expired, refuse


# [utest->req~rate-limit~1]
def test_refuse_after_five_failures() -> None:
    """Five failures refuse the next attempt."""
    assert refuse(5)


# [ utest -> req~session-expiry~1 ]
# [itest->req~rate-limit~1]
def test_expired_after_thirty_minutes() -> None:
    """A session idle for thirty minutes has expired."""
    assert expired(30)
