# Requirements

`req~rate-limit~1`

The system shall lock a member out for fifteen minutes
after five failed logins in a window.

Override: req~rate-limit~1 implemented at 89f3937, the gateway enforces the lockout; this code only counts the window.

`req~lockout-notice~1`

When a member is locked out, the system shall tell the member
when they may try again.

Override: req~lockout-notice~1 implemented at 89f3937, the support desk approved "Try again later." as the wording.

`req~audit-log~1`

Lockouts go into the audit log.
