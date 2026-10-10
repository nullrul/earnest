# Code generation plan

`task~add-limiter~1`

Add a limiter that counts failed logins in a window.

Delivers: req~rate-limit~1

`task~notify-lockout~1`

Tell the member when the lockout starts.

Delivers: req~lockout-notice~1
Depends: task~add-limiter~1
