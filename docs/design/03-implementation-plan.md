# 03 — Implementation Plan

Status: draft, derived from `02-structural-design.md`, September 2026.

This document orders the build of the `earnest` package that
`02-structural-design.md` lays out, as a graph of milestones in the shape of
[[structure-implementation-plans-as-sequential-foundation-then-parallel-branches]]:
a sequential foundation that freezes the contracts the rest reads, then
branches that run in parallel once it holds. The `iterative-build-loop` skill
executes it one milestone per loop, with context cleared between loops, so each
milestone names everything a fresh session loads.

## Milestone DAG

```mermaid
flowchart LR
  M1["M1 trace_check"] --> M2["M2 stage_status"]
  M2 --> M3["M3 task_change"]
  M2 --> M4["M4 judge_check"]
  M2 --> M7["M7 aidlc_fork"]
  M3 --> M5["M5 evidence_check"]
  M4 --> M5
  M4 --> M6["M6 calibration_gate"]
  classDef done fill:#d4edda,stroke:#2e7d32
```

M1 and M2 are the foundation. M1 fixes the index and the SARIF output that
every later milestone reads, and M2 adds the assessment record, the contract
that revision checks, the judge cache, the coverage-map commit, calibration and
the run header share. M3, M4 and M7 then run in parallel. M5 joins M3 and M4:
evidence runs in `impact.py` beside impact, and `--evidence` implies `--judge`.
M6 continues the judge branch. Evidence has its own milestone so that M6 waits
on the judge alone, and the out-of-task check and impact have theirs so that M2
carries only the record and the stage engine.

M1 is the first runnable milestone, and no open question gates it. The
record-location row of the Open questions section of `02` gates M2, and through
M2 every milestone from M3 to M7, so it is the first open question to close.
When a milestone's exit command runs green, its node gains the `done` class,
and the graph doubles as the loop's progress board.

## How a milestone runs

- Exit command: each milestone exits on one behavior feature,
  `tests/features/<slug>.feature`, bound by the pytest-bdd step module
  `tests/steps/test_<slug>.py`, as the Tests section and decision L5 of `02`
  fix. The exit command is `uv run pytest tests/steps/test_<slug>.py`, run in
  `packages/earnest/`; the milestone is done when it runs green. No coverage
  threshold applies for now.
- Scenarios: `04` writes each feature's scenarios before its code
  ([[write-gherkin-before-code-not-after]]).
- Task plans: task-level detail is written just in time, one plan per
  milestone, with the superpowers `writing-plans` skill when the milestone is
  next, at `docs/superpowers/plans/<date>-<slug-with-hyphens>.md`.
- Gating open questions: the rows of the Open questions sections of `01` and
  `02` that a milestone cannot exit without. Each closes by the resolution its
  row names.
- Goals: a milestone's goal and exit behavior hold for the whole loop, and
  change only through a revision of this document that the maintainer ratifies
  ([[goals-must-be-immutable-during-execution]]).

## Milestones

### M1 `trace_check`

- Goal: build the trace spine end to end over `broken-links`. It detects and
  reports orphaned and near-miss tags, and a finding that reaches no stage
  takes position `current`. The assessment record arrives with M2.
- Depends on: none.
- Exit behavior: two `earnest check` runs in `broken-links` give identical
  SARIF. The SARIF shows every seeded missing link, orphan, stale revision,
  malformed id and near-miss at file and line, each `req` at untraced or
  traced, the traced percentage, and a non-zero exit.
- Exit command: `uv run pytest tests/steps/test_trace_check.py`.
- Deliverable: `earnest check` through `cli.py`, `git.py`, the four
  `adapters/`, `index.py`, the link rules of `structural.py`, and the SARIF
  output and summary of `reporter.py`; `tests/conftest.py`,
  `tests/fixtures/broken-links/`, `trace_check.feature` and its step module;
  the `earnest` script (L4), pytest-bdd and the fixture excludes (L5, L6).
- Spec coverage: UC1 and UC2 (links); SC1, SC2, SC3 (untraced and traced),
  SC10 (message text only); the Trace and Report capabilities.
- Context to load: `00`: Success criteria. `01`: Grammar, Near-miss, Item
  types, Edges, Default Needs, Findings, Trace levels, Frontier and position,
  Region rule, Reference resolution, Command surface, SARIF 2.1.0, D1, D10,
  D13, D16. `02`: the File and directory tree; Package, Scanner, Index,
  `structural.py`, Reporter and Tests in Module boundaries; L4 to L6.
- Gating open questions: none.
- Task plan:
  [2026-09-26-trace-check.md](../superpowers/plans/2026-09-26-trace-check.md).

### M2 `stage_status`

- Goal: add the assessment record's writer, the route, approvals, frontier and
  position, computed status with `unplanned` and `cycle`, `earnest plan`,
  `--stage`, `unbumped-change` and outdated approvals.
- Depends on: M1.
- Exit behavior: in `seeded-change`, `earnest plan` prints the route, each
  stage's computed status, its approval and the frontier. `check --stage`
  prints the assessment hash and writes the run header. After the change
  commit, a check flags the tag, edge and approval left at the old revision,
  and a body edited without a bump.
- Exit command: `uv run pytest tests/steps/test_stage_status.py`.
- Deliverable: `plan.py` with the route, stages, approvals, frontier and
  position, and computed status; the record's reader and writer in
  `reporter.py`; the Revision lifecycle in `structural.py`; `earnest plan` and
  `--stage` in `cli.py`; `tests/fixtures/seeded-change/` with its `change/`
  overlay; `stage_status.feature` and its step module.
- Spec coverage: UC4, UC7, UC9 (engine); SC1, SC5, SC8 (status), SC9 (run
  header); the Revision propagation, Plan and stage status, and Stage approval
  capabilities.
- Context to load: `01`: Adopting AI-DLC, Stages, Frontier and position,
  Computed status, Process vocabulary, Revision lifecycle, Command surface,
  Assessment record, Runtime and permission model, D6, D9, D15. `02`: `plan.py`,
  `structural.py`, `reporter.py`, `conftest.py` and `fixtures/seeded-change/`
  in Module boundaries.
- Gating open questions: where the assessment record sits and its file format
  (`02`); assessment hash contents (`01`).
- Task plan: `docs/superpowers/plans/<date>-stage-status.md`, written when M2
  is next.

### M3 `task_change`

- Goal: add the out-of-task check in `plan.py` and impact in `impact.py`.
- Depends on: M2.
- Exit behavior: on a `task/…` branch, `earnest check` reports each changed
  region outside the task with the three exits. It also prints an impact
  section of requirements, features and tests to run, with `impact-degraded`
  for a line that has no coverage data.
- Exit command: `uv run pytest tests/steps/test_task_change.py`.
- Deliverable: the Out-of-task rule in `plan.py`; the Impact rule in
  `impact.py`, over pytest-cov's per-test contexts; the `seeded-change` cases
  its feature reads; `task_change.feature` and its step module.
- Spec coverage: UC3, UC6; SC6, SC7; the Out-of-task check and Impact
  capabilities.
- Context to load: `01`: Out-of-task rule, Impact rule, Region rule, D11, D12.
  `02`: `git.py`, `plan.py`, `impact.py` and `fixtures/seeded-change/change/`
  in Module boundaries.
- Gating open questions: task base commit, and coverage map timing (`01`).
- Task plan: `docs/superpowers/plans/<date>-task-change.md`, written when M3
  is next.

### M4 `judge_check`

- Goal: add the EARS parse, judge questions from its spans, the judge cache
  and the Override rule.
- Depends on: M2.
- Exit behavior: against a stub model, `check --judge` reports `req-not-ears`,
  a `judge-not-satisfied` verdict with reasoning and location,
  `judge-uncalibrated`, the judged percentage, and an override as the
  observation of record. After the change commit it reports `override-expired`
  and `override-drift`.
- Exit command: `uv run pytest tests/steps/test_judge_check.py`.
- Deliverable: `ears.py`; `judge/__init__.py` and `judge/prompt.txt` with the
  questions, the cache and the Override rule; `--judge` in `cli.py`; the
  `seeded-change` cases its feature reads; `judge_check.feature` and its step
  module.
- Spec coverage: UC2 (weak verdicts), UC5; SC3 (judged), SC4 (warning), SC11;
  the Judge and Overrides capabilities.
- Context to load: `01`: Grammar, Override rule, Process vocabulary, D2, D3,
  D14. `02`: `ears.py` and `judge/` in Module boundaries; L4.
- Gating open questions: stub judge model (`01`). The judge model choice and
  prompt row of `01` settles at M6.
- Task plan: `docs/superpowers/plans/<date>-judge-check.md`, written when M4
  is next.

### M5 `evidence_check`

- Goal: run the tagged tests and mutmut, with results filtered to tagged
  regions.
- Depends on: M3 and M4.
- Exit behavior: `check --evidence` raises `evidence-failed` for a surviving
  mutant in a tagged region, puts every requirement at exactly one of the four
  levels with three separate percentages, and shows the evidenced task and its
  unit as done.
- Exit command: `uv run pytest tests/steps/test_evidence_check.py`.
- Deliverable: the Evidence rule in `impact.py`; `--evidence` in `cli.py`; the
  `seeded-change` cases its feature reads; `evidence_check.feature` and its
  step module.
- Spec coverage: SC3 (in full), SC8 (done); the Evidence capability.
- Context to load: `01`: Evidence rule, Trace levels, Computed status, D4.
  `02`: `impact.py` in Module boundaries; L4.
- Gating open questions: evidence result in the record, and TypeScript
  evidence fixture (`01`).
- Task plan: `docs/superpowers/plans/<date>-evidence-check.md`, written when
  M5 is next.

### M6 `calibration_gate`

- Goal: add `earnest calibrate` and the calibration fixture.
- Depends on: M4.
- Exit behavior: `earnest calibrate tests/fixtures/calibration` shows the
  judge's ten verdicts beside the maintainer's, the match count, and a pass at
  eight or more written to the record. After that, `--judge` stops raising
  `judge-uncalibrated`. The feature uses the stub model; the real-model run is
  the SC4 gate itself.
- Exit command: `uv run pytest tests/steps/test_calibration_gate.py`.
- Deliverable: `earnest calibrate` in `cli.py`; calibration in `judge/`;
  `tests/fixtures/calibration/`; `calibration_gate.feature` and its step
  module.
- Spec coverage: UC8; SC4; the Calibration capability.
- Context to load: `00`: SC4. `01`: UC8, G10, Process vocabulary, Command
  surface. `02`: `judge/` and `fixtures/calibration/` in Module boundaries.
- Gating open questions: the file format of `tests/fixtures/calibration/`
  (`02`); calibration source repository, and judge model choice and prompt
  (`01`).
- Task plan: `docs/superpowers/plans/<date>-calibration-gate.md`, written when
  M6 is next.

### M7 `aidlc_fork`

- Goal: gate the AI-DLC fork from this repository. The fork applies the Fork
  delta of `02` under its own plan, in its own repository; this milestone is
  the integration gate.
- Depends on: M2.
- Exit behavior: the feature runs against a local fork checkout with Bun on
  the PATH, and fails rather than skips if either is missing. The fork's
  sensor prints `{pass, findings_count}` with exit 0 for a `seeded-change`
  stage, with pass false while an error sits behind or current. Approve writes
  `GATE_APPROVED` with `Assessment Hash`, `Items` and `Approved By`.
- Exit command: `uv run pytest tests/steps/test_aidlc_fork.py`.
- Deliverable: `aidlc_fork.feature` and its step module here; the Fork delta
  in the fork's repository.
- Spec coverage: UC9; SC9; the Stage approval capability; G13.
- Context to load: `01`: Adopting AI-DLC, including "The `earnest` sensor and
  the approval gate"; Command surface; Runtime and permission model. `02`: Fork
  delta; L3. The fork's own plan.
- Gating open questions, all from `02`: the fork repository's name and owner;
  how the sensor script finds the `earnest` command; the upstream tools that
  read `source-manifest.json`; the upstream artifacts the mapping table leaves
  unnamed; the User Stories requirement ids; holding the sensor on through the
  sensors-off switches; the upstream tests that pin sensor ids and routes.
- Task plan: the integration gate at
  `docs/superpowers/plans/<date>-aidlc-fork.md`, written when M7 is next; the
  delta's plan lives in the fork's repository.

## Scope (v1)

- Seven milestones that build the `earnest` package of `02`, each exiting on
  one behavior feature.
- M7, the integration gate for the AI-DLC fork; the fork plans and builds its
  delta in its own repository.
- The calibration command proven against a stub model; the maintainer's
  real-model run on the calibration fixture is the SC4 gate itself.

## Future directions

- A coverage threshold for the package, when the maintainer sets one.
- Milestones for the Future directions of `02`: an editor language server,
  further host adapters, and a `publish` stage so the fork installs a released
  `earnest`.
