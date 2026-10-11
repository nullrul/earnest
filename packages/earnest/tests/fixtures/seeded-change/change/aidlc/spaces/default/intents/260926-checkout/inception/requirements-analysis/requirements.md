# Requirements

`req~rate-limit~2`

The system shall lock a member out for thirty minutes
after five failed logins in a window.

`req~lockout-notice~1`

When a member is locked out, the system shall tell the member
how long the lockout lasts.

`req~audit-log~1`

The system shall record each lockout in the audit log.
