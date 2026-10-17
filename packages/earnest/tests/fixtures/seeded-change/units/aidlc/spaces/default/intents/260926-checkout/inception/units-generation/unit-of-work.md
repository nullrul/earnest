# Units of work

| Unit ID | Directory | Responsibility |
| --- | --- | --- |
| U1 | u1-limiter | Count failed logins and lock the member out |
| U2 | u2-notice | Tell a locked-out member when to try again |

## Units

`unit~u1~1`

Count failed logins in a window and lock the member out.

Delivers: req~rate-limit~1

`unit~u2~1`

Tell a locked-out member when they may try again.

Delivers: req~lockout-notice~1
Depends: unit~u1~1
