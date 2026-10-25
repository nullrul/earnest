"""Checkout authentication tests."""
from checkout.auth import audit_lockout, count_failed_logins, lockout_message

# [utest->req~rate-limit~1]
def test_count_failed_logins() -> None:
    assert count_failed_logins(3) == 3
    assert count_failed_logins(-1) == 0


# [utest->req~lockout-notice~1]
def test_lockout_message() -> None:
    assert lockout_message().startswith("Try again")


# [utest->req~audit-log~1]
def test_audit_lockout() -> None:
    assert audit_lockout(str(count_failed_logins(1))) == "1"
