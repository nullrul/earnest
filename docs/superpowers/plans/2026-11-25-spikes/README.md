# Spike patches for the M8 and M9 plans

Reference diffs that the M9 plan
([2026-11-25-openspec-host.md](../2026-11-25-openspec-host.md)) builds Tasks 4 to
7 on. They were measured on 2026-11-25 in scratch copies of earnest at `ae4136c`
and copied here from `/tmp/earnest-swarm/`, which does not survive. The paths in
their headers are rewritten to be relative. Read them, and take only the hunks
that the task names: they carry spike-only choices (an approval environment
variable, a constant route, REMOVED handling) that the plan drops or defers.

| File | Task of the M9 plan | What it holds |
| --- | --- | --- |
| `spike-c-design-c.src.diff` | 4, 6, 10 | the archive skip, the layer overlay, REMOVED handling (Task 10) |
| `spike-c-design-c.tests.diff` | 4, 6, 10 | the 14 layer tests of spike C |
| `m9-delta-over-delta.diff` | 6 | the two-line stacked-change extension of answer 8 |
| `spike-d-prototype-src.patch` | 5, 7 | `openspec.py`, the change loader, the boxes, the two rules |
| `spike-d-prototype-tests.patch` | 5, 7 | the 25 tests of spike D |

Content: synthetic fixtures and upstream OpenSpec behavior only. Nothing in
these files comes from a private repository.

## Spike G, for the M6 plan

Task 7b of the M6 plan
([2026-10-25-calibration-gate.md](../2026-10-25-calibration-gate.md)) builds the
`claude-code:` judge model on spike G, measured the same day in a scratch copy
of earnest at `ae4136c`. The diffs apply to the checkout with `git apply -p1`
from the repository root (checked against `ae4136c`). They carry spike-only
choices that Task 7b changes: `--restricted` (replaced by `--setting-sources
user`), an environment allowlist without the Bedrock variables, and no harness
in the cache key or the calibration slot.

| File | What it holds |
| --- | --- |
| `spike-g-prototype-src.diff` | the +88 lines of `judge/__init__.py`: `ClaudeCode`, its constants and the `load_model` branch |
| `spike-g-prototype-tests.diff` | `tests/unit/test_judge_claude_code.py`, 29 tests against a fake `claude` on `PATH`; no login, no network |
| `spike-g-live-check.sh` | the one-call live check that comes before the 20-call run, adapted from the spike's `drive.py`; run from `packages/earnest/` with `EARNEST_JUDGE=claude-code:<model>` |

The spike's two real calls both failed at the provider (a Bedrock 403 for the
host's instance role, because `--restricted` had dropped the user settings), so
no answer, `modelUsage` key or token count was ever observed; Task 7b lists what
stays unverified until the live check has run.
