# Future format

This overlay's unit-scoped audit rows use the format the AI-DLC fork writes
from milestone M7: `Unit` holds the unit's Earnest name by the id rule (`u1`
for `U1`), beside `Gate Scope`, `Gate Stages`, `Attempt Generation`,
`Assessment Hash`, `Items` and `Approved By`. Upstream at fe563195d827 writes no
`Unit` on solo approvals and none of the last three fields, and where it raises
`Attempt Generation` is unverified. The state file's Unit Progress table is
illustrative; Earnest never reads it. No live AI-DLC run is claimed.
