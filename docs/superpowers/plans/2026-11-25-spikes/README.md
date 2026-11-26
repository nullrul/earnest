# Spike artifacts for the M6 plan

The spikes of 2026-11-25 ran in scratch copies of earnest at `ae4136c`, which do not survive. The M9 plan
([2026-11-25-openspec-host.md](../2026-11-25-openspec-host.md)) and the M6 plan
([2026-10-25-calibration-gate.md](../2026-10-25-calibration-gate.md)) inline the code that their tasks build on, so
this folder holds no diffs or patches. It keeps the one script that Task 7b of the M6 plan runs.

Content: synthetic fixtures and upstream OpenSpec behavior only. Nothing in these files comes from a private repository.

## Spike G, for the M6 plan

Task 7b of the M6 plan builds the `claude-code:` judge model on spike G, measured the same day in a scratch copy of
earnest at `ae4136c`. Spike G's backend and tests carry spike-only choices that Task 7b changes: `--restricted`
(replaced by `--setting-sources user`), an environment allowlist without the Bedrock variables, and no harness in the
cache key or the calibration slot. They also took the model name as `self.id.partition(":")[2]`, which Task 7b replaces
with a `model` field once the id carries the harness. Task 7b gives the code and the tests with those changes applied.

| File                    | What it holds                                                                                                                                                         |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `spike-g-live-check.sh` | the one-call live check that comes before the 20-call run, adapted from the spike's `drive.py`; run from `packages/earnest/` with `EARNEST_JUDGE=claude-code:<model>` |

The spike's two real calls both failed at the provider (a Bedrock 403 for the host's instance role, because
`--restricted` had dropped the user settings), so no answer, `modelUsage` key or token count was ever observed; Task 7b
lists what stays unverified until the live check has run.
