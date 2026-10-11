# Plan

`task~wire-limiter~1`

Wire the rate limiter into the sign-in handler.

Delivers: req~Rate-Limit~1
Depends: task~set_up~1

`task~notify~1` Tell the member when to try again

`task~audit~1`

Record each sign-in.

**Delivers:** req~audit-log~1
Depends: task~wire-limiter~1,

`tsk~expire~1`

End idle sessions.
