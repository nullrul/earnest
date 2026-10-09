# Requirements

`req~rate-limit~1`

When a client fails to sign in five times in one minute, the auth service
shall refuse further attempts for fifteen minutes.

Needs: impl, utest
Covers: feat~sign-in~1

`req~lockout-notice~2`

When the auth service refuses an attempt, the auth service shall tell the
member when to try again.

Covers: feat~sign-in~1

`req~session-expiry~1`

While a session is idle for thirty minutes, the auth service shall end it.

Needs: impl utest

`req~remember-me`

Where remember-me is on, the auth service shall keep the session for a week.

`req~audit-log~1`

When a member signs in, the auth service shall record the time.

Covers: feat~sign-in~2, FR1.2

`req~audit-log~1`

When a member signs out, the auth service shall record the time.
