# earnest verification map

This directory is the maintained source for verifying the user-facing behavior of the earnest CLI. Read the index, then use the matching feature file as the recipe.

## Baseline preconditions

- `uv` is on `PATH`; run from the repo or worktree root.
- Build a fixture with `scripts/build-fixture.sh` (see `SKILL.md`, Launch): `base` for most features, `base override` for the judge.
- Doctor passes: `base` is `89f3937`, `units` is `4cdc2f5`, status is clean.
- Drive through `scripts/run-earnest.sh <repo> <evidence-dir> <label> <earnest args>`; it captures the exit code from `$?`.
- `EARNEST_JUDGE` is unset except `stub:<verdicts.json>`. Never an `anthropic:` model.
- Never drive a repo this run did not build.

## Driving conventions

- Start every recipe from a freshly built fixture unless its preconditions say otherwise (a run writes `.earnest/`).
- Assert on exit code, `ruleId` and `level` in `runs[0].results`, summary lines on stderr, and record keys, not on message prose.
- Treat each command literally.
- Cleanup removes scratch repos, never the evidence directory.

## Proof and skip reporting

- Proof per run: `.cmd`, `.exit`, `.stdout` (SARIF 2.1.0), `.stderr` (summary), and `.record.json` when the run leaves a record.
- Record the feature ID and fixture build with every artifact.
- Report an unreachable path with the attempted command and the unmet precondition. Do not report a skipped path as verified through another.

## Feature entry contract

Each feature file has an H1, one paragraph, then the H2s `Sub-features`, `How to get to it (user POV)`, `Driving it with run-earnest.sh`, `Gotchas`.

## Features

- [check](./check.md): `earnest check` over the whole intent, with no judge.
- [check-stage](./check-stage.md): `check --stage` and `--intent`, the record header, and the exit-2 input errors.
- [plan](./plan.md): `earnest plan`, the route, stage status and the frontier.
- [judge](./judge.md): `check --judge` with the stub model, its cache and its exit codes.

Not mapped: `calibrate <fixture>` (see `docs/demo/m6-calibrate.sh`, which drives the `calibration-dev` fixture) and `check --evidence` (runs tests and mutmut; heavy).
