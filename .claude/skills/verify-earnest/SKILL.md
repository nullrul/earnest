---
name: verify-earnest
description: "Drive the earnest CLI (`earnest check`, `plan`) against a committed fixture repo and capture proof of its behavior, meaning exit code, SARIF on stdout, summary on stderr, and the `.earnest/assessment.json` record. Use to confirm a change to packages/earnest works in the real CLI, not just in pytest."
---

# Verify earnest

earnest is a CLI with no server. A verification run builds a throwaway committed git repo from a fixture, runs `earnest` inside it, and keeps the output as evidence. Every run gets its own temp repo, so runs can go side by side.

The judge's only model is the stub: `EARNEST_JUDGE=stub:<verdicts.json>`. Never set `anthropic:...`.

Paths below use `$SK` for this skill directory (`.claude/skills/verify-earnest`) and `$PKG` for `<repo root>/packages/earnest`. Run from the repo root or worktree root.

## Launch

Launch means build one fixture repo; the CLI starts per command. `uv` installs the package on first use (`uv run --project`).

```bash
SK=.claude/skills/verify-earnest
REPO=$($SK/scripts/build-fixture.sh base)          # prints the repo path
```

`build-fixture.sh <base|units> [overlay ...]` makes `${TMPDIR:-/tmp}/verify-earnest/scratch.XXXXXX/seeded-change`, mirroring `packages/earnest/tests/conftest.py` (pinned identity and date, `GIT_*` isolation, overlays and bytecode left out), commits it as `fixture` on `main`, then commits each named overlay on top, on `main`. Only `base`, `units` and `base override` have been built and checked; the other overlays (`override-change`, `evidence`, `evidence-units`) are unverified. `change` and `task` are not mirrored: `packages/earnest/tests/conftest.py` commits them on a new branch (`commit_overlay`, `commit_task_change`), and the builder commits on `main`.

| Need | Build |
| --- | --- |
| Approved requirements, no judge | `build-fixture.sh base` |
| Judge with the canned verdicts (`judge-verdicts.json`) | `build-fixture.sh base override` |
| Units variant | `build-fixture.sh units` |

Ready means `git rev-parse --short=7 HEAD` matches the doctor table below.

## Doctor

Read-only. Run first, and whenever anything looks off:

```bash
( cd "$REPO" && git rev-parse --short=7 HEAD && git status --porcelain | wc -l && git log --format=%s )
```

| Build | Expected short sha | Expected `git log` subjects |
| --- | --- | --- |
| `base` | `89f3937` | `fixture` |
| `base override` | differs (override commit on top; base is its parent) | `override`, `fixture` |
| `units` | `4cdc2f5` | `fixture` |

The status count must be `0` (before the first run; a run adds an untracked `.earnest/`, itself ignored by its own `.gitignore`). Also `uv run --quiet --project packages/earnest earnest --help` must exit 0. A wrong sha has two causes: the fixture files changed, or conftest's `_OVERLAYS` gained an entry that `build-fixture.sh`'s exclude list (`EXCL`) lacks. For the first, `packages/earnest/tests/integration/test_seeded_change.py` pins `BASE_SHA` and `UNITS_SHA`, so update those, not this table, only on purpose.

## Drive

Use the capture helper so the exit code comes straight from `$?`:

```bash
EV=${TMPDIR:-/tmp}/verify-earnest/evidence/$(date +%Y%m%dT%H%M%S)
$SK/scripts/run-earnest.sh "$REPO" "$EV" <label> <earnest args...>
```

It runs `uv run --quiet --project $PKG earnest <args>` inside `$REPO` and writes `<label>.cmd`, `.stdout` (SARIF 2.1.0), `.stderr` (summary), `.exit`, and `.record.json` (copy of `.earnest/assessment.json` as it stands after the run). It exits with earnest's own code.

Exit codes: `0` clean; `1` an error-level finding at plan position behind or current; `2` earnest could not run (bad flag value, no judge model, unknown stage). Features, one file each:

- [check](features/check.md): `earnest check`, whole intent.
- [check-stage](features/check-stage.md): `check --stage`, `--intent`, and the bad-input exits.
- [plan](features/plan.md): `earnest plan`.
- [judge](features/judge.md): `check --judge` with the stub model.

`check --evidence` runs tests and mutmut: heavy, and not verified here (its overlays are unverified; see Launch).

## Evidence

A proof is: the real CLI path (`earnest ...` inside a committed fixture repo, not a Python call or a test-only hook), the exact command (`.cmd`), the exit code captured directly with `$?` by the helper (never through `rtk`, which can mask exit codes; if you run earnest by hand, use `rtk proxy` and `echo $?`), the SARIF on stdout, the summary on stderr, and the record file `.earnest/assessment.json` as a side effect (read it: a `check --stage` run writes a header under `runs`, keyed `<record dir>/<stage>` with `hash` and `items`, while other runs leave `runs` empty; `judge.cache` holds judge answers). Assert on ruleIds and levels in `runs[0].results`, not on prose. Where a feature says the run must leave no record, verify the absence in the repo.

Evidence goes to `${TMPDIR:-/tmp}/verify-earnest/evidence/<timestamp>/`. Cleanup never touches it.

## Cleanup

Removes only a scratch directory the builder created. It resolves symlinks and `..` on both the repo's parent and the scratch root, requires the parent to be a `scratch.*` directory directly under `.../verify-earnest/` that holds the marker file `.verify-earnest-scratch`, else refuses:

```bash
$SK/scripts/build-fixture.sh --clean "$REPO"
```

Run it after every attempt, failed ones included. Never `rm` anything else, and never the evidence directory.

## Helpers

- `scripts/build-fixture.sh base|units [overlay ...]` prints the repo path; `--clean <repo-path>` removes it.
- `scripts/run-earnest.sh <repo> <evidence-dir> <label> <earnest args...>` runs and records one command.
