# check

`earnest check` reads the committed repo and its AI-DLC record, traces requirements to code and tests, and reports findings as SARIF 2.1.0 on stdout with a summary on stderr. Without `--judge` it asks no model.

## Sub-features

- `check-trace` reports each requirement's trace level in the stderr summary.
- `check-finding` reports a finding as a SARIF result with a `ruleId` and `level`.
- `check-exit` exits 0 when no error-level finding sits at plan position behind or current.
- `check-no-record` leaves no `.earnest/` in a repo it only checks.

## How to get to it (user POV)

- Run `uv run --quiet --project <repo>/packages/earnest earnest check` inside a committed repo that holds `aidlc/spaces/default/intents/<intent>/`.

## Driving it with run-earnest.sh

Preconditions: `build-fixture.sh base` repo at `89f3937`, `EARNEST_JUDGE` unset.

- **Run.** `run-earnest.sh "$REPO" "$EV" check check`. The helper prints `exit=0`, and `check.exit` holds `0`.
- **Summary.** `check.stderr` starts `traced 100%, judged 0%, evidenced 0%; requirements: 3`, has the lines `req~audit-log~1: traced`, `req~lockout-notice~1: traced`, `req~rate-limit~1: traced`, and ends `findings: 1, errors: 0`.
- **SARIF.** `check.stdout` has `version` `2.1.0` and one result: `earnest/unplanned`, level `warning`, at `requirements.md:13`, saying `req~audit-log~1` is delivered by no task.
- **No record.** `ls -a "$REPO"` shows no `.earnest/` and the stderr says `record: absent, body-hash baseline unavailable`.

## Gotchas

- The base fixture has a warning, not a clean slate: zero findings is a failure of this recipe.
- Exit 0 with a warning is correct; only an error at position behind or current exits 1.
- A repo with no commit, or no AI-DLC record, is not a valid target; build it with the helper.
