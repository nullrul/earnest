# M7 `aidlc_fork` Implementation Plan

Status: APPROVED-ready, 2026-11-25. The maintainer decided all 17 gating answers on 2026-11-25 (DECIDED (user, 2026-11-25) in each row, and recorded in Task 0 Step 1); row 4 is option A, keep `nullrul/aidlc-workflows`, against Spike F's recommendation, so L3 of `02` is revised and the fork needs an upstream sync first. Spike F (2026-11-25) checked the answers against the fork's code and Earnest's behavior and added an evidence block to each row; it recommended and decided nothing. This repository alone cannot turn the exit command green. It needs the Fork delta of `02`, built under the fork's own plan, merged in the fork's repository at the commit that Task 5 pins. The plan was reviewed on the branch `docs/m7-aidlc-fork-plan` and merged by PR #18 on 2026-11-21 (`ae4136c`); Task 0 records the decisions in it.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** this repository gates the AI-DLC fork. Run `uv run pytest tests/steps/test_aidlc_fork.py` in `packages/earnest/`. It drives a local fork checkout with Bun against `seeded-change` and asserts these things:

- The fork's `earnest` sensor prints `{"pass", "findings_count"}` and exits 0 for a stage. `pass` is false while an error sits at position behind or current.
- The fork's approve transition writes `GATE_APPROVED` with `Assessment Hash`, `Items` and `Approved By`, and `earnest plan` then reads that approval as current.
- For a per-unit stage of the units variant, the sensor runs `earnest check --stage <phase>/<unit directory>/<slug>`. Approve then writes `Unit` with the three fields.
- When the fork checkout or Bun is missing, the gate fails. It never skips.

**Architecture:**

- This repository holds only the gate. That gate is:
  - `tests/fork.py`, which finds the checkout and runs the fork's tools in a scrubbed environment;
  - two fixture overlays, each of which puts one stage at its gate;
  - `aidlc_fork.feature` and its step module;
  - a make target and a CI job, which check out the pinned fork commit and install Bun;
  - the change, gating answer 14 being decided, that joins `Unit` by unit directory in `plan.py`.
- The fork's repository holds the Fork delta of `02`, under the fork's own plan. This plan fixes only what the gate calls (Interface contract, below). No task here edits, commits or pushes a fork file.
- The two meet at the Command surface of `01` (L3 of `02`). The fork's sensor runs `earnest check --stage`. Earnest reads the fork's `GATE_APPROVED` rows from the intent's `audit/*.md`, as it reads every shard.

**Tech Stack:**

- Python 3.12, pytest-bdd and `subprocess`.
- Bun 1.4.2 and the fork's TypeScript, run from source. They run only inside the gate's subprocesses.
- GitHub Actions `actions/checkout` and `oven-sh/setup-bun`.

**Spec:**

- `docs/design/03-implementation-plan.md`, milestone M7.
- `01`, these sections:
  - Adopting AI-DLC, and "The `earnest` sensor and the approval gate", lines 115-192
  - UC9
  - Per-unit stages and units, lines 640-708
  - the run header and the Assessment hash, lines 1600-1611
  - Command surface
  - Runtime and permission model
  - Open questions
- `02`: Fork delta, L3, L5, L6, Open questions.
- `04`: the M7 row of the milestone table, and the M7 section that Task 0 writes.
- The Fork facts below, collected on 2026-11-20 from the fork at `f2acb53d` with Bun 1.3.8. Each fact cites its file and line, so the maintainer can check it.

## Fork facts (2026-11-20)

The facts come from the maintainer's checkout of the fork; its path is the maintainer's machine, so answer 12 leaves it out. Its branch `earnest/m7-base` is the same commit as `origin/main`, `f2acb53d`. No Earnest delta is applied: `git log main..HEAD` is empty. Paths below are relative to the fork. The feasibility runs used copies of the built fixtures in the session scratchpad. The fork's `git status --short --ignored` was the same before and after.

| # | Fact | Evidence |
| --- | --- | --- |
| F1 | `nullrul/aidlc-workflows` sits in GitHub's fork network, with `isFork: true` and parent `awslabs/aidlc-workflows`. Its `upstream` remote has a working push URL. | `gh repo view nullrul/aidlc-workflows --json isFork,parent`; `git remote -v` |
| F2 | The fork's `main` is 1029 commits past the Fork delta's base, `fe563195d827`. Every changed path in the delta still exists, with one exception: `tests/.coverage-registry.json` is no longer committed. `tests/gen-coverage-registry.ts` now regenerates it, git-ignored, from the `// covers:` headers of the tests, and CI ratchets it with `--check --base`. | `git rev-list --count fe563195d827..HEAD`; `git cat-file -e`; commit `10113463b` |
| F3 | The five sensor registration points that `02` names all exist: `TOOLS`, `SENSOR_WORKERS`, the `__sensor-script` table of `resolveAlias`, the lazy-import map, and `BUNDLED_SENSOR_IDS`. | `core/tools/aidlc.ts:128`, `:164`, `:1924`, `:2450`; `core/tools/aidlc-sensor.ts:375` |
| F4 | `fireGateSensors` fires gate sensors once for each matching deliverable. It runs at gate-start, at the approve revision backstop, and at revise. For a blocking sensor, it already holds the gate in all of these cases: an artifact changes before dispatch or during evaluation; a timeout; a non-zero exit; a bad verdict; findings. The plain approve path compares no fingerprints. Only the backstop checks them again. | `core/tools/aidlc-state.ts:3755`, `:6591`, `:6916`, `:7621`, `:3812`, `:3843`, `:7089` |
| F5 | The sibling `traceability` sensor is fired on write and is advisory: it has no `fire_on` field, and the parser default is `write`. The sensors fired at the gate are `required-sections`, `upstream-coverage` and `claim-sources`. No shipped sensor is blocking. The dispatcher counts a script's non-zero exit as `PASSED` with `script-error`. So the `earnest` script has to exit 0 with `pass: false`. On exit 0, `FAILED` or `PASSED` follows `pass` alone. `findings_count` is only recorded, so a stage with warnings and `pass: true` opens its gate. | `core/tools/aidlc-sensor-schema.ts:82`; `core/tools/aidlc-sensor.ts:23-31`, `:983`, `:1046-1057`; `core/tools/aidlc-state.ts:3907` |
| F6 | A sensor script receives only `--stage <slug> --output-path <abs>`, never `--unit`. It runs in the project directory. | `core/tools/aidlc-sensor.ts:548-554`, `:622-627` |
| F7 | `GATE_APPROVED` has these emit sites. Solo approve builds its fields at `:7161-7179` and writes no `Unit`. The team unit gate goes through `teamGateFields`, which writes `Unit`, `Gate Scope`, `Gate Stages` and `Attempt Generation`. `aidlc-unit.ts:2159` is the `unit-merge` gate, and `aidlc-swarm-checkpoints.ts:427` is a checkpoint gate. | `core/tools/aidlc-state.ts:7180`, `:6988`, `:6519-6529` |
| F8 | Upstream's unit name is the unit's construction directory: "`u{n}-{description}` … Unit name (its construction directory)". `teamGateFields` writes `Unit: context.unit`, which is that name, and `aidlc-state.ts:6380` joins it into `construction/<unit>/`. `01` instead joins `Unit` to the name the id rule gives (`u1`). | `core/knowledge/aidlc-shared/verification.md:23`; `core/aidlc-common/stages/inception/units-generation.md:104`; `01` lines 167-169, 671 |
| F9 | `validateAuditEntry` keeps no per-event list of fields. `Assessment Hash`, `Items`, `Approved By` and `Unit` all pass `AUDIT_FIELD_KEY_PATTERN`. | `core/tools/aidlc-audit.ts:680`, `:682` |
| F10 | `Attempt Generation` is raised when a unit is claimed and when it is released. `STAGE_SKIPPED` and `STAGE_JUMPED` carry no `Unit`. Upstream's skip of one unit is `UNIT_SKIPPED`, which does carry it. | `core/tools/aidlc-unit.ts:3406-3409`, `:3593`; `core/tools/aidlc-state.ts:7806-7819`, `:7848` |
| F11 | Sensors are switched off in this order: `AIDLC_DISABLE_SENSORS=1` first, then the intent's `Sensors` field, then the scope's default. No sensor is exempt. An explicit `aidlc-sensor fire` ignores the switch. Only `core/scopes/aidlc-express.md` has `sensors: off`. | `core/tools/aidlc-lib.ts:41289-41318`; `core/hooks/aidlc-run-sensors.ts:140-141` |
| F12 | Upstream tests pin what the delta changes: `t86-sensor-manifest-schema` (the six sensor ids and `GATE_SENSORS`), `t230-dispatcher-routes` (each manifest's help line, `TOOLS` targets), `t349-gate-sensor-reachability` (each gate glob accepts a deliverable), `t281-sensor-traceability` (a stage that emits `traceability.json` declares the sensor), `t48-audit-event-emitters` (the event set, not fields), `t28-audit-event-sync` and `t261-audit-authority-floor`. This list is a lower bound: answer 10 adds three tests and a wider reading of `t281`. Tests run with `bun tests/run-tests.ts`. | `tests/unit/`, `tests/integration/`; `tests/README.md:3-9` |
| F13 | At HEAD, eight files under `core/tools/` read `source-manifest.json`: the seven that `02` names, plus `aidlc-lib.ts`. | `core/tools/aidlc-lib.ts:19275`, `:26538-26580` |
| F14 | The sibling sensor runs on its own against the built `seeded-change`, with no `node_modules` and no stage graph: `bun <fork>/core/tools/aidlc.ts engine sensor-traceability --stage <slug> --output-path <abs>`. It exits 0 and prints one JSON line. | feasibility run |
| F15 | Solo approve accepts the hand-written fixture intent, with no `intents.json`, engine state or `SENSOR_*` rows, once five conditions hold. (1) It is given a stage graph through `AIDLC_STAGE_GRAPH`, compiled by the fork's `compileStageGraph()`. This is needed because `bun scripts/package.ts` fails on Bun 1.3.8, and the fork's CI pins 1.4.2. (2) `AIDLC_ALLOW_DIRECT_STATE_TRANSITIONS=1` is set. (3) The stage row is at `[-]` and `engine state gate-start <slug>` runs. (4) The state file holds `- **Review Override**: none`. (5) A `HUMAN_TURN` row (`Timestamp` and `Event` only) follows gate-start. The approval lands in `audit/<hostname>-<clone id>.md`, and `aidlc/.aidlc-clone-id` pins the clone id. These runs used a scratch clone that had `bun install --frozen-lockfile`, which Spike F found unneeded (answer 12). | `core/tools/aidlc-graph.ts:2513`; `core/tools/aidlc-state.ts:867`, `:5892-5905`; `core/tools/aidlc-lib.ts:38409-38421`; `.github/workflows/ci.yml:59` |
| F16 | The team per-unit gate stops at "no current `UNIT_COMPLETED` receipt", after it has also demanded `runtime-graph.json` and stub artifacts. `unit-merge` needs a pinned merge transaction. Solo approve on the units variant, with `Unit Ownership: team` removed, is accepted. It approves the stage's single row and writes no `Unit`. | feasibility run; `core/tools/aidlc-unit.ts:2098-2175` |
| F17 | The fork's rows carry wall-clock timestamps. A call to the fork rewrites `aidlc-state.md` and adds untracked files: `<record>/.aidlc-engine/`, the shard, and `aidlc/.aidlc-clone-id`. An unscrubbed run also bound the caller's own session, in `aidlc/.aidlc-sessions/<session>.binding.json`. | `core/tools/aidlc-lib.ts:40105`; feasibility run |
| F18 | `make test` runs every test (`testpaths = ["tests"]`, no markers). CI `test-python` has no fork and no Bun. A module that fails without the fork would turn both red. | `packages/earnest/pyproject.toml:78-88`; `.github/workflows/ci.yml:34-40` |

Earnest's side, on the built fixtures, without the overlays of Task 3:

- **Solo:**
  - `earnest check --stage requirements-analysis` exits 0 with no results.
  - After `req~rate-limit~1` is defined a second time at the end of `requirements.md`, the same command exits 1 with one result: `earnest/duplicate`, level error, position behind.
  - With `code-generation` at `[-]`, `earnest check --stage code-generation` exits 0 with one result: `earnest/unplanned`, level warning, position current.
- **Units:** `earnest check --stage construction/u2-notice/functional-design` exits 0 with no results. A bare `functional-design` exits 2: "functional-design names several stages" (`plan.py:1551-1567`).
- **Scope of a `--stage` run:** it reports only the named stage's findings, plus the findings that reach no stage. That is why the failing-sensor scenario checks `requirements-analysis`, not `code-generation`.
- **The run header:** its key is `<record dir>/<stage>`, for example `aidlc/spaces/default/intents/260926-checkout/construction/code-generation`. It holds `commit`, `dirty`, `hash`, `intent`, `items`, `layers`, `model`, `prompt`, `reasons`, `stage`, `status` and `timestamp` (`reporter.py:498-512`).

## Spike F evidence (2026-11-25)

Spike F checked the 17 gating answers against the fork's code and against Earnest's behavior. It decided nothing; the maintainer then decided every answer on 2026-11-25, and rows 1, 4, 11, 13 and 17 were his own to make. Each row below ends in an evidence block: its class, its evidence and a recommended answer.

- **Pins.** The fork is `nullrul/aidlc-workflows` at `f2acb53d`, read-only. Earnest is at `ae4136c`. The experiments ran in a copy of this repository on Linux, on fixtures that `.claude/skills/verify-earnest/scripts/build-fixture.sh` builds.
- **No fork code ran.** The host has no Bun. Every claim about the fork is read from its code, with a file and line. Every claim about Earnest was run, and its exit code is in the table below.
- **Classes.**
  - *Settled by code*: a file and line decide it. Rows 2, 3, 5, 6, 9, 12, 14 and 16.
  - *Settled by experiment*: a run decided it. Rows 7, 8 and 15. Row 10 needs an experiment that has not run, because it needs Bun and the delta.
  - *Maintainer-only*: a policy or a design choice that evidence can price but cannot make. Rows 1, 4, 11, 13 and 17.
- **Raw output.** `evidence/` and `exp/` under `/tmp/earnest-swarm/spike-f/` hold the logs and the scripts, including the prototype diff of answer 14, on the machine that ran the spike. They are not committed.

| Id | What ran | Exit | Result |
| --- | --- | --- | --- |
| E1 | `earnest plan` on the units fixture, with the gate row's `Unit` as `u1` (a, the id rule) and as `u1-limiter` (b, the directory) | 0, 0 | (a) approves `u1-limiter/functional-design`; (b) approves nothing and prints no finding about it |
| E2 | A solo row with no `Unit` (a), with only `Unit: u1` (b), and with only `Unit: u1-limiter` (c) | 0, 0, 0 | (a) approves no per-unit stage; (b) approves `u1-limiter/functional-design`; (c) approves nothing |
| P-E1, P-E2 | The same five runs with spike F's prototype, which translated the id-rule name and so took both spellings; it is not the directory-keyed `_expand` of Task 2 | 0 x5 | `u1` and `u1-limiter` both approved, alone or with only `Unit` in the row; the row with no `Unit` still approved nothing. Task 2's `_expand` takes the directory alone, so `Unit: u1` approves nothing there (P-E1a is dropped); no run has measured that |
| E3 | `check --stage requirements-analysis` five times: clean (a); a stage file added and left uncommitted (b); the same bytes committed (c); the fork's gate-start bookkeeping imitated by hand (d); a second stage file added (e) | 0 x5 | (b) `dirty` true, `commit` 89f3937; (c) `dirty` false, `commit` 38c6ea2, the hash of (b); (d) the hash of (c); (e) a new hash |
| E5 | `check --stage requirements-analysis` with `FR1.2` absent (a), as a suffix `(FR1.2).` (b), as a prefix `FR1.2:` (c) and inside a clause (d) | 1 x4 | Each carries the same two `earnest/orphaned` errors, which fix the code at 1; only (c) adds `earnest/req-not-ears` |
| E6 | `check --stage construction/u2-notice/functional-design` before and after a prose file with `NFR3.1`, `NFR3.2` and `FR1.2` is added there | 0, 0 | No results either time |
| E7 | `pytest --collect-only` on pytest 9.1.1 with `addopts = ["--ignore=tests/steps/test_aidlc_fork.py"]`: bare (a), the module's path (b), `tests/steps` (c), the module's node (d) | 0 x4 | (a) and (c) leave the module out; (b) and (d) collect it |
| E8 | `check --stage construction/u1-limiter/code-generation` with an error in it: the unit's frontier is that stage (a); the frontier is `functional-design`, so the stage lies ahead (b); `check --stage` of `functional-design` at that frontier (c) | 1, 0, 0 | (a) the errors at position current; (b) the same findings as notes at position ahead; (c) no results |
| E9 | `check --stage requirements-analysis` twice on a clean tree | 0, 0 | The coverage map file is rewritten on each run |

**Moot or wrong in the plan.** Each is corrected in place, in the row it names:

- Issue #30 asks to merge PR #18. PR #18 merged on 2026-11-21, so the issue's open work is the 17 decisions and Task 0.
- Answer 12 requires `bun install --frozen-lockfile` and names a macOS path. The first is not needed; the second is the maintainer's machine, not a fact of the repository.
- Answer 13's option (c) says the fork holds the gate if any listed stage fails. A listed stage ahead of the unit's frontier never fails (E8b).
- Answer 10's list of pinned tests (F12) is a lower bound.
- Answer 17's option A needs two pieces of fork work that the plan does not list.
- Answers 3 and 5 leave out the cost of a run: on a clean tree, each `check --stage` runs the target's tests.
- The fork's `main` is 911 commits behind `awslabs` main (answers 4 and 15).

**Left to the maintainer, decided 2026-11-25.** The evidence priced these rows and could not decide them:

- Row 1: an approval may bind uncommitted bytes (neither refuses).
- Row 4: option A, keep `nullrul/aidlc-workflows` (Spike F recommended B).
- Row 11: agents push feature branches and open pull requests on the fork, never to main, `--force-with-lease` only; the user merges.
- Row 13: option (c) for `unit-end`.
- Row 17: option A, `--unit <name>` on the solo path.

## Gating open questions

The M7 entry of `03` names thirteen gating rows: three from `01`, seven from `02` and three from M2b. The Fork facts raise rows 14 to 17. Every answer is DECIDED (user, 2026-11-25); the rows that follow a Spike F recommendation say "as recommended". A row marked *(fork plan)* is decided here and carried out in the fork's repository. No row is dropped. Each row ends in an evidence block from Spike F, above.

### 1. A run header with `dirty` true (`01`)

Row as asked: "Whether the gate or the approve transition refuses a run header with `dirty` true", resolved before `aidlc_fork`.

**DECIDED (user, 2026-11-25):** neither the gate nor approve refuses a dirty tree. The gate shows `dirty` beside the hash, and approve records the hash as it stands. The baseline cost below becomes a known limit (Known limits).

- Source: `01`, Assessment hash, says "A work tree with uncommitted changes gets the hash of the bytes it holds". The hash binds the bytes the human read, whether or not they are committed.
- Why: AI-DLC writes a stage's artifacts before anything commits them. Refusing `dirty` would hold almost every gate until someone commits.
- Trade-off: an approval may bind bytes that never reach a commit. Earnest still marks it stale once its items change, because an approval is current by its `Items` (`01`, Frontier and position).

**Evidence (Spike F):**

- **Class:** maintainer-only. The evidence cannot choose between refusing and recording, but it prices the choice.
- **Evidence:** E3b against E3c: the same bytes give the same `Assessment Hash` whether the tree is dirty or committed, so the hash ignores `dirty` and `commit`. Both runs exit 0.
- **Unlisted cost:** a dirty header's `commit` is HEAD, which lacks the approved bytes (E3b: 89f3937, the commit before them; E3c: 38c6ea2 once committed). `change_baseline` takes that `commit` as the change baseline when the approval carries the header's hash (`plan.py:1435-1449`, read at `cli.py:281-292`). By that definition, the approved bytes then count as changed since the baseline. A dirty run also takes no coverage map (`cli.py:424`).
- **Recommended answer:** neither refuses, with the cost above recorded as a known limit. Accepted as recommended (DECIDED, user, 2026-11-25).

### 2. Where the gate reads the run header (`01`, *fork plan*)

Row as asked: "Which Fork-delta path holds the gate presentation that reads `status` and `hash` from the run header, and the path `.earnest/assessment.json` that the approve transition reads".

**DECIDED (user, 2026-11-25), as recommended:** both live in `core/tools/aidlc-state.ts`, through one reader of `runs["<record dir>/<stage>"]` in `<project dir>/.earnest/assessment.json`.

- gate-start adds `Assessment Hash`, `Stage Status` and `Dirty` to its `STAGE_AWAITING_APPROVAL` row. That row already carries `Sensor State` (`core/knowledge/aidlc-shared/audit-format.md:73`).
- `handleApprove` reads the same header.
- No new file is needed. The fork's plan confirms how the review brief (`core/tools/aidlc-review-brief.ts`) shows the new fields.
- Source: `02`, Fork delta, the `aidlc-state.ts` bullet.

**Evidence (Spike F):**

- **Class:** settled by code.
- **Evidence:** `gateAskFields` (`aidlc-state.ts:6278`) builds the gate-open fields at six sites: the team gate-open row (`:6655`), the revalidation row (`:6683`), the solo gate-open row (`:6715`) and the three re-entry rows (`:7108`, `:7668`, `:7697`). One edit in it adds `Assessment Hash`, `Stage Status` and `Dirty` to all six. The `GATE_APPROVED` fields are built elsewhere (F7, `:7161-7179`), so approve's edit is a second one.
- **Recommended answer:** accepted (DECIDED, user, 2026-11-25).

### 3. An artifact that changes during a sensor run, and the check at approve (`01`, *fork plan*)

Row as asked: "Which Fork-delta path holds the hold on an artifact that changes during a sensor run, and the check in `approve` that artifacts are unchanged since the sensor ran".

**DECIDED (user, 2026-11-25), as recommended:**

- **The hold during the run needs no delta path.** Upstream's `fireGateSensors` already holds the gate of a blocking gate sensor when an artifact changes before dispatch or during evaluation (F4). The `earnest` manifest is `fire_on: gate` and `default_severity: blocking`, so it inherits that hold.
- **The check at approve goes in `handleApprove`, in `aidlc-state.ts`.** When the gate's `STAGE_AWAITING_APPROVAL` row carries an `Assessment Hash`, approve runs the `earnest` sensor's check for the stage again. It approves only when the new run header's `hash` equals that `Assessment Hash`. Otherwise it exits non-zero, writes no `GATE_APPROVED`, and names the stage whose gate must be reopened.
- This makes the row's `Assessment Hash` "the hash of the assessment the gate showed" (`01`, the approval entry of the vocabulary table, line 722).
- Trade-off: each approve costs one `earnest check --stage` run, which on a clean tree is a full run of the target's tests (below). The alternative is to persist upstream's in-memory fingerprints (`GateSensorEvaluation.fingerprints`, `aidlc-state.ts:3566`) so approve can compare them. That would be a larger change to upstream's state.

**Evidence (Spike F):**

- **Class:** settled by code. E3 and E9 measured Earnest's side.
- **Evidence:** upstream's fingerprints cover declared artifacts only (`aidlc-state.ts:3735-3845`, through `existingDeclaredArtifactPaths`). Earnest's hash covers the whole evaluated tree (`plan.py:1264-1313`), so the re-run at approve is needed. E3d: with gate-start's bookkeeping imitated by hand (a rewritten state file, a new shard, `.aidlc-engine/`), the hash and `dirty` did not move; E3e: one more stage file changed the hash. All five E3 runs exit 0. Task 5 Step 3 still checks what the fork really writes.
- **Unlisted cost:** a clean `check --stage` takes a coverage map, which runs the target repository's tests under pytest-cov with a 900 s limit (`cli.py:424`, `impact.py:33`, `:64`). E9 shows it runs again each time: the map file is rewritten between two runs, both exit 0. So approve's second check costs a full test run, and gate-start's fire runs one for each matching deliverable (F4). A dirty tree takes no map. The sibling manifests set `timeout_seconds: 300` (`core/sensors/aidlc-traceability.md:22`), so the `earnest` manifest needs a limit above the map's, or a slow suite ends as `BUDGET_OVERRIDE` (`aidlc-sensor.ts:24`). This last point comes from reading, outside the spike's report.
- **Recommended answer:** accepted (DECIDED, user, 2026-11-25), with the run cost stated beside the trade-off.

### 4. The fork repository's name and owner (`02`)

Row as asked: "The fork repository's name and owner; this repository is `nullrul/earnest`", resolved by "creating the fork".

**DECIDED (user, 2026-11-25): A. Keep `nullrul/aidlc-workflows` (F1) and revise L3.** This goes against Spike F's recommendation of B, a mirror-push into a new standalone repository, so every place that assumed B is changed below.

- Every clone sets `git remote set-url --push upstream no-push` and `gh repo set-default nullrul/aidlc-workflows`.
- The repository stays public, because a fork of a public repository stays public. CI checks it out with no credential.
- `gh pr create` from a fresh clone targets `awslabs` until `set-default` runs, so every agent call names `-R nullrul/aidlc-workflows` as well (answer 11).
- **L3 is revised** in `02` (Task 0 Step 3): the fork is the GitHub fork `nullrul/aidlc-workflows` of `awslabs/aidlc-workflows`, not a standalone mirror. "Downstream only" now rests on the per-clone `no-push` and `set-default` settings, not on the repository's shape. L3's old reason, that there is no pull-request path to upstream, no longer holds structurally; the two settings and answer 11 replace it.
- **The upstream sync is a precondition.** The fork's `main` is 911 commits behind `awslabs` main (Spike F), and A keeps that history. Before the delta, the fork's plan syncs `main` with `awslabs/aidlc-workflows` main, and records the synced sha. Tasks 3 to 5 and the delta's base (answer 15) start from that sha. The sync is fork-side work: this plan pushes nothing to the fork (answer 11), and Task 0 Step 4 and Task 5 name it as a precondition.

Whichever sha the sync lands on, the delta's base in `02`'s Fork delta changes with it (answer 15).

**Evidence (Spike F):**

- **Class:** maintainer-only. The evidence was neutral between A and B.
- **Evidence:** `nullrul/aidlc-workflows` is public and a fork of `awslabs/aidlc-workflows`, and an anonymous `git ls-remote` returns `f2acb53d`, so CI needs no token under either option (`gh api` and `git ls-remote`, 2026-11-25). The fork is 0 commits ahead of and 911 behind `awslabs` main.
- **Unlisted cost, now a task:** under A the delta would start on a `main` that is 911 commits stale. The sync above removes that cost.
- **Spike F recommended B; the maintainer chose A.**

### 5. How the sensor script finds `earnest` (`02`)

Row as asked: "How the fork's sensor script finds the `earnest` command: an installed tool on the path, or a pinned invocation".

**DECIDED (user, 2026-11-25), as recommended:** from `PATH`, as the command `earnest`.

- **When `earnest` cannot be started**, the script prints `{"pass": false, "findings_count": 0}` and exits 0. A missing engine then holds the blocking gate the way a failing check does (`01`: "a check that fails to run holds the gate like a failing one"; F5).
- **Install:** until there is a `publish` stage (`02`, Future directions), the maintainer installs `earnest` with `uv tool install --editable packages/earnest` from this repository.
- **In the gate:** every fork call puts the package's own venv `bin/` first on `PATH`.
- **Trade-off:** a pinned invocation, such as `uv run --project <path> earnest`, would bind a version, but it would put this repository's path into the fork.

**Evidence (Spike F):**

- **Class:** settled by code.
- **Evidence:** the dispatcher's truth table (`aidlc-sensor.ts:20-31`) reads exit 0 with `pass: false` as `FAILED`, and a non-zero exit (branch e) or exit 127 (branch b) as `PASSED`. So printing `pass: false` and exiting 0 is the only way a missing engine holds the gate.
- **Unlisted cost:** each run of the `earnest` sensor is a `check --stage`, which on a clean tree runs the target's tests (answer 3).
- **Recommended answer:** accepted (DECIDED, user, 2026-11-25).

### 6. Readers of `source-manifest.json` (`02`)

Row as asked: keep writing `source-manifest.json` "as AI-DLC input that Earnest never counts as evidence, or extend the Fork delta to those tools?"

**DECIDED (user, 2026-11-25), as recommended:** keep it as AI-DLC input that Earnest never counts as evidence.

- The delta leaves all eight readers (F13) unchanged.
- In `01`'s mapping table, its row changes from "replaced" to "kept, carries no weight as evidence (T2)".
- Source: L3 says "the delta keeps to what `01` changes".
- Trade-off: a unit's files are listed in two places, and only Earnest's out-of-task check counts.

**Evidence (Spike F):**

- **Class:** settled by code.
- **Evidence:** `readUnitSourceManifest` (`aidlc-lib.ts:26539`) is one of the readers F13 counts, and none changes under the delta. Earnest's `src/` names `source-manifest` in no file.
- **Recommended answer:** accepted (DECIDED, user, 2026-11-25).

### 7. Upstream artifacts the mapping table leaves unnamed (`02`)

Row as asked: NFR Requirements' `scalability-requirements`, `reliability-requirements` and `tech-stack-decisions`; NFR Design's `scalability-design`, `reliability-design` and `logical-components`; and Build and Test's agent-written `cross-unit-traceability.md`.

**DECIDED (user, 2026-11-25), as recommended:** all seven stay as AI-DLC writes them: prose with no items and no weight as evidence (T2).

- Each gains a "kept" row in `01`'s mapping table.
- Their stages still list `earnest`, because those stages' other artifacts carry items.
- Trade-off: scalability and reliability stay outside the trace until a later revision adapts them.

**Evidence (Spike F):**

- **Class:** settled by experiment.
- **Evidence:** E6: a prose file with `NFR3.1`, `NFR3.2` and `FR1.2` in `construction/u2-notice/functional-design/` leaves `check --stage` at exit 0 with no results, before and after (0, 0). One stage directory was tried. Earnest reads items, not prose.
- **Recommended answer:** accepted (DECIDED, user, 2026-11-25). Write it in `01`'s mapping table as one rule, "a prose artifact with no Earnest item carries no weight (T2)", not as a "kept" row for each of the seven.

### 8. User Stories requirement ids (`02`, *fork plan*)

Row as asked: "Keep the AI-DLC id in each item's prose, or move User Stories to `earnest`?"

**DECIDED (user, 2026-11-25), as recommended:** keep the AI-DLC id in each `req` item's prose.

- The adapted `requirements.md` template writes `FR1.2` in the item's text, beside the name `req~fr1-2~1`.
- The kept `traceability` sensor's pattern, `FR\d+(?:\.\d+)?`, then still finds it.
- User Stories stays kept.
- Trade-off: the id appears twice.

**Evidence (Spike F):**

- **Class:** settled by experiment.
- **Evidence:** E5: the traceability sensor's pattern (`aidlc-sensor-traceability.ts:63`) finds `FR1.2` in the suffix form `(FR1.2).`, in the prefix form `FR1.2:` and inside a clause. Earnest's `check` exits 1 in all four variants, on the same two `earnest/orphaned` errors, so the code says nothing and the rule list does. The prefix form adds `earnest/req-not-ears` at error level. The suffix and in-clause forms add nothing.
- **Recommended answer:** accepted (DECIDED, user, 2026-11-25), with a placement rule for the adapted template: write the id as a `(FR1.2)` suffix or inside a clause, never as a `FR1.2:` prefix.

### 9. The sensors-off switches (`02`)

Row as asked: "Whether the fork holds the `earnest` sensor on through the per-intent `/aidlc --sensors off` and the `AIDLC_DISABLE_SENSORS=1` kill switch".

**DECIDED (user, 2026-11-25), as recommended:** honour both switches. The delta adds no exemption for one sensor (F11).

- With sensors off, the gate fires no check and its `STAGE_AWAITING_APPROVAL` row carries no `Assessment Hash`.
- Approve then skips answer 3's second check and writes `Approved By` alone.
- Earnest counts that approval and never marks it stale. `04` pins this in the M2 scenario "An approval row without the fork's fields counts and never goes stale (SC8)".
- Why: both switches are explicit acts by the user. The delta already turns `express` on (`02`).
- Trade-off: the approvals of an intent with sensors switched off bind no assessment.

**Evidence (Spike F):**

- **Class:** settled by code.
- **Evidence:** `resolveCeremony` (`aidlc-lib.ts:41289-41318`) turns the ceremony `off` for the kill switch, with no exemption for one sensor (F11).
- **Unlisted cost:** an approval without an `Assessment Hash` has no digest, so `change_baseline` skips it (`plan.py:1447`). An intent approved only that way has no change baseline, and the task-change check says "no approved stage check is recorded" (`cli.py:287-288`).
- **Recommended answer:** accepted (DECIDED, user, 2026-11-25), with that cost in the trade-off.

### 10. Upstream tests that pin sensor ids and routes (`02`, *fork plan*)

Row as asked: "Which upstream tests pin the bundled sensor ids, the dispatcher routes or a stage's `sensors:` list", resolved by "the first run of upstream's suite on the fork".

**DECIDED (user, 2026-11-25), as recommended:**

- The tests are the ones listed in F12 and the three more that the evidence block below adds. The fork's plan updates each one in the same commit as the change it pins.
- The fork's first run of `bun tests/run-tests.ts --all` with the delta confirms the list, as the row's "Resolved by" says.
- `t281` passes only while every stage that still produces `traceability.json` declares the `traceability` sensor. So the delta must drop the `traceability.json` output in the same change that drops the sensor, as `01` replaces it.

**Evidence (Spike F):**

- **Class:** experiment, not run, because it needs Bun and the delta. The list below is read from code.
- **Evidence:** F12 is a lower bound. It leaves out these tests, which name `traceability` or `traceability.json`:
  - `tests/integration/t89.test.ts:196`, the resolved sensor ids of `functional-design`, and `:339`, the loaded sensor ids, both from the `basic-import` fixture directory;
  - `tests/unit/t-approval-says-what-was-left-out.test.ts`, which lists items left out as `Deferred` in a unit's `traceability.json`;
  - `tests/unit/t314-source-freshness-receipts.test.ts`, with `traceability.json` at `:220`, `:226` and `:2302`.

  F12 names `t281` but does not size it. `tests/unit/t281-sensor-traceability.test.ts:148-187` pins eight stages on `produces`, `sensors` and `outputs` together: user-stories, domain-design, units-generation, functional-design, nfr-requirements, nfr-design, infrastructure-design and code-generation.
- **Unlisted seam:** `01` replaces `traceability` with `earnest`, so every test above may move. Keeping `traceability` beside `earnest` (add-only) would leave the eight-stage contract in place, by reading. The fork's plan weighs the two.
- **Recommended answer:** keep "the first full run confirms". The fork's plan starts from F12 and the tests above.

### 11. Authority to create and push the fork repository (M2b)

**DECIDED (user, 2026-11-25):**

- The repository exists (answer 4, option A). The maintainer merges.
- Agents may push feature branches of the fork and open pull requests on the fork, after the pre-PR review passes (the maintainer's standing rule: three reviewers, every finding fixed). Every call names `-R nullrul/aidlc-workflows`, since `gh` targets `awslabs` by default (answer 4).
- Never to the fork's `main`, and never to `upstream`. On a rebased feature branch, `git push --force-with-lease` only, never `--force`. The user merges every pull request.
- This plan pushes nothing to the fork. The fork's plan does, under these rules.

**Evidence (Spike F):**

- **Class:** maintainer-only. It is policy.
- **Evidence:** the `gh` login has admin on `nullrul/aidlc-workflows` (`gh api`, 2026-11-25), so the capability exists. The maintainer's rule above decides whether an agent may use it.

### 12. A fork checkout with Bun (M2b)

**DECIDED (user, 2026-11-25), as recommended:**

- **Finding the checkout.** The gate reads it from `EARNEST_AIDLC_FORK`: an absolute path that holds `core/tools/aidlc.ts`. It reads `bun` from `PATH`. If either is missing, the gate fails with a message that names it (Task 1).
- **Locally.** The gate takes the checkout only from `EARNEST_AIDLC_FORK`, so this plan names no machine's path. Bun should be the fork CI's 1.4.2 (`bun upgrade` from 1.3.8). No `bun install` is needed: nothing under the fork's `core/` imports a package outside `node:` and `bun:`, and F14 ran without `node_modules`.
- **How the gate runs the fork.** It runs from source, as `bun <fork>/core/tools/aidlc.ts …`. The stage graph is compiled into pytest's temporary directory by the fork's own `compileStageGraph()` and passed as `AIDLC_STAGE_GRAPH` (F15). The gate does not package the fork, and writes nothing in the checkout.
- **In CI:** see answer 15.

**Evidence (Spike F):**

- **Class:** settled by code.
- **Evidence:** a search of `core/` for imports outside `node:` and `bun:` finds none, and the fork's `package.json` holds only `devDependencies` (typecheck, lint and the fork's own tests). The fork's `ci.yml:57-59` pins Bun 1.4.2 and `oven-sh/setup-bun@0c5077e51419868618aeaa5fe8019c62421857d6`.
- **Correction:** the `bun install --frozen-lockfile` precondition is dropped here, from answer 15, from Global Constraints, from Task 1 Step 6 and from Task 4 Step 2. The macOS checkout path is dropped; the spike's host is Linux and has no Bun.
- **Recommended answer:** accepted (DECIDED, user, 2026-11-25), with those corrections.

### 13. The per-unit fork work (`01`)

Row as asked: "how a `unit-end` gate checks each stage its `Gate Stages` lists while those stages read ahead of the unit's frontier; where upstream raises `Attempt Generation`; whether `STAGE_SKIPPED` or `STAGE_JUMPED` rows carry `Unit`".

**DECIDED (user, 2026-11-25), as recommended:**

- **`Attempt Generation`.** Upstream raises it when a unit is claimed and when it is released, in `aidlc-unit.ts` (F10). The team gate already writes it (F7), and the delta leaves it as it is.
- **`STAGE_SKIPPED` and `STAGE_JUMPED`.** Neither carries `Unit` (F10). `01`'s rule already expects that: "restarts and jumps void rows by slug for every unit". Earnest does not read `UNIT_SKIPPED` in v1.
- **`unit-end`: DECIDED (user, 2026-11-25), option (c), v1.** At a `unit-end` gate, the fork fires the `earnest` sensor once for each stage that `Gate Stages` lists, each as `<phase>/<unit directory>/<slug>`, and holds the gate if a listed stage at or behind the unit's frontier fails. A listed stage that lies ahead of the frontier reports its errors as notes, exits 0 and so passes: it never holds the gate (E8b). This is the weaker guard, and it goes into Known limits. Task 0 adds a row to `01`'s Open questions, to be settled before the first team-mode intent runs through Earnest. The root fix, a `--stage` run in Earnest that reports at position current every stage the same open `unit-end` gate lists, is not part of M7; it is a later Earnest task with its own scenario, because `01`, lines 703-705, would change.
- Neither option can be reached from this gate, because the team path stops at a `UNIT_COMPLETED` receipt (F16).

**Evidence (Spike F):**

- **Class:** maintainer-only. The evidence prices (c) and shows it is weaker than the first wording said.
- **Evidence:** E8: with an error in `u1-limiter`'s code-generation, `check --stage` of that stage exits 1 with the errors at position current when it is the unit's frontier (E8a), and exits 0 with the same findings as notes at position ahead when the frontier is `functional-design` (E8b). E8b models a `unit-end` gate by dropping the unit's `functional-design` approval, as no stage of the unit has its approval yet at that gate. The sensor then prints `pass: true` for the later stages.
- **Unlisted seam:** firing once for each listed stage is new fork work. `fireGateSensors` fires for each matching deliverable and takes no unit (`aidlc-state.ts:3755-3760`). `STAGE_SKIPPED` carries no `Unit` (`:7848`), where `UNIT_SKIPPED` does (`:7806`).
- **Recommended answer:** (c) for M7, with the weaker guard written into Known limits. Only (a) guards a stage ahead of the frontier. Accepted as recommended (DECIDED, user, 2026-11-25).

### 14. The value of `Unit` (new, from F8)

**DECIDED (user, 2026-11-25), as recommended:** Earnest joins a gate row's `Unit` to the unit whose construction directory it names, which is upstream's unit name. That replaces the id-rule name. The fork writes upstream's unit name at every emit site, including the new `Unit` on the solo path.

This changes, in this repository:

- `01`, lines 167-169 and 671, and `02`, line 200, which say a gate row's `Unit` is the unit's name by the id rule;
- the keys of `stage_ids` and `lanes` in `plan.py`, which every read of `Unit` compares against;
- the `Unit` rows of the `units/` overlay, and `units/FUTURE-FORMAT.md`;
- the unit names in `04`'s and `unit_status.feature`'s Gherkin that steps write into `Unit` rows, and the test rows and assertions that carry the old names (Task 2).

The alternative is for the fork to map upstream's name to the id-rule name at its emit sites. That changes a value upstream's own code already joins into paths (`aidlc-state.ts:6380`) and reads (`gateStagesFromBlock`, `aidlc-lib.ts:36460`).

**Evidence (Spike F):**

- **Class:** settled by code. E1 and E2 ran Earnest's side as it stands; spike F's prototype (P-E1, P-E2) is not Task 2's `_expand`.
- **Evidence:** upstream's unit name is the construction directory: `core/knowledge/aidlc-shared/verification.md:23` ("Unit name (its construction directory)"), `core/aidlc-common/stages/inception/units-generation.md:104`, and `aidlc-state.ts:6380`, which joins it into `construction/<unit>/`. `teamGateFields` writes it as `Unit` (`:6525`). E1b: a gate row with `Unit: u1-limiter` approves nothing today. The run exits 0, `u1-limiter/functional-design` stays "not done, approval none", and no finding names the row, so the failure is silent. E1a, the id-rule spelling, approves it.
- **Starting code:** `_expand` (`plan.py:622`) with three statements changed to the directory join, as Task 2 gives them. Unmeasured: spike F's five runs of P-E1 and P-E2 used its translation prototype, so Task 2's tests are this code's first run.
- **Recommended answer:** accepted (DECIDED, user, 2026-11-25).

### 15. The fork commit the gate pins, and CI (new, from F2 and F18)

**DECIDED (user, 2026-11-25), as recommended:**

- **The delta's base.** The delta is applied to the fork's `main` after the upstream sync of answer 4 (the fork is 911 commits behind `awslabs` main), at the synced sha that the fork's plan records, not to `f2acb53d` or `fe563195d827`. Task 0 updates two things in `02`'s Fork delta:
  - its base commit;
  - its tree: `tests/.coverage-registry.json` is replaced by `// covers:` headers on the two new tests (F2).
- **`make test` stays self-contained.** pytest's `addopts` in `pyproject.toml` (a list, and it has no `addopts` today) carries `--ignore=tests/steps/test_aidlc_fork.py`, so a bare `uv run pytest` and `make test` keep Bun and TypeScript out of the package's tests, as L5 of `02` does. Naming the module's path still runs it (checked on pytest 9.1.1). The M9 plan adds its own list entries to the same key (`--ignore=tests/steps/test_openspec_host.py` and `--ignore=tests/integration/test_openspec_ids.py`), so whichever of M7 and M9 lands second merges the key, never overwrites it; the merged form is `addopts = ["--ignore=tests/steps/test_aidlc_fork.py", "--ignore=tests/steps/test_openspec_host.py", "--ignore=tests/integration/test_openspec_ids.py"]`, and M9 removes its two entries at its exit while M7's stay. A new target, `make test-aidlc-fork`, runs the exit command. The module itself never skips.
- **A new CI job, `test-aidlc-fork`,** does these steps:
  - checks out the fork at `AIDLC_FORK_REF`, a full sha on the fork's `main` that holds the delta;
  - installs Bun 1.4.2 with `oven-sh/setup-bun`, pinned by sha as the fork's own CI pins it;
  - runs `make test-aidlc-fork` with `EARNEST_AIDLC_FORK` set. It runs no `bun install` (answer 12).
- **Merge order:**
  0. The fork's plan syncs the fork's `main` with `awslabs/aidlc-workflows` main (answer 4, option A), and records the synced sha.
  1. The fork's plan merges the delta on the fork's `main`, at sha X.
  2. This repository's M7 branch sets `AIDLC_FORK_REF` to X.
  3. The branch merges once the job is green. Until step 1, the exit command stays red and the branch stays unmerged.

**Evidence (Spike F):**

- **Class:** settled by experiment.
- **Evidence:** E7, pytest 9.1.1, with `addopts = ["--ignore=tests/steps/test_aidlc_fork.py"]`: a bare run collects 1054 tests, not the module (exit 0); the module's path and its node each collect it (exit 0, 0); a directory argument, `tests/steps`, leaves it out (exit 0). So only a named module path or node runs the gate. The fork's `ci.yml:57-59` pins the same `oven-sh/setup-bun` sha and Bun 1.4.2.
- **Correction:** the job drops `bun install --frozen-lockfile`, as answer 12 says. The delta's base, `f2acb53d`, is 911 commits behind `awslabs` main, so answer 4's sync comes first.
- **Recommended answer:** accepted (DECIDED, user, 2026-11-25).

### 16. How the gate drives approve (new, from F15 and F16)

**DECIDED (user, 2026-11-25), as recommended:**

- **The calls.** The gate calls the fork's direct transitions:
  - `engine state gate-start <slug>` and then `engine state approve <slug> --user-input Approve`;
  - both with `AIDLC_ALLOW_DIRECT_STATE_TRANSITIONS=1`;
  - with a hand-written `HUMAN_TURN` row between them, which stands for the human's answer;
  - with `- **Review Override**: none` in the overlay's state file.
- **A per-unit stage.** The gate uses the solo path on the units variant, with `Unit Ownership: team` removed, and names the unit as answer 17 settles: under its option A, `--unit <unit name>` on both calls.
- **Left to the fork's own tests (`t-gate-approved-assessment.test.ts`):**
  - the orchestrated path, `engine orchestrate report --result approved`, which needs a session join and `State Version: 8`;
  - the team gates and `unit-merge`;
  - `Approved By: automatic`.
- **The `--unit` form** belongs to the Interface contract. Task 0 Step 4 records the form the fork's plan settles on.

**Evidence (Spike F):**

- **Class:** settled by code.
- **Evidence:** F15 and F16 stand. The guard that wants a human reply after gate-start has an upstream off-switch, `AIDLC_SKIP_HUMAN_PRESENCE_GUARD=1` (`aidlc-lib.ts:31144`).
- **Unlisted seam:** 127 upstream test files under `tests/` set that switch, so it is the fork's own way to drive approve in a test. The gate could set it instead of writing a `HUMAN_TURN` row. That would turn the guard off rather than satisfy it, so the gate would no longer exercise "the human replied".
- **Recommended answer:** accepted (DECIDED, user, 2026-11-25). Keep the hand-written `HUMAN_TURN` row, and keep the switch as the fallback if the row's format drifts.

### 17. Where the solo path gets its unit (new, from F16)

`02` and `01` (line 169) have the delta write `Unit` on the solo approve path. On the units variant with solo ownership, though, upstream's solo approve covers the stage's single row, such as `functional-design — EXECUTE: per unit`, and knows no unit (F16). Upstream can also approve several per-unit stages at one solo gate (`Approves Together`, `audit-format.md:73`).

**DECIDED (user, 2026-11-25): A. `--unit <unit name>`** on the solo `gate-start` and `approve`, including the two pieces of fork work below.

- The delta adds this argument to gate-start and approve on the solo path. A solo gate for a per-unit stage then speaks for one unit, and writes one `GATE_APPROVED` with that `Unit`. When upstream approves per-unit stages together, the delta writes one `GATE_APPROVED` per unit stage, each with its own `Unit`, `Assessment Hash` and `Items`. That keeps `01`'s rule that one row speaks for one unit's stage.
- **Fork work it adds**, which the delta lists nowhere yet, so Task 0 Step 3 adds both to `02`'s Fork delta and Task 0 Step 4 compares them with the fork's plan:
  1. `teamGateContext` must stop rejecting `--unit` outside team mode (`aidlc-state.ts:5913-5925`).
  2. Sensor firing must be scoped to the unit, because `fireGateSensors` takes no unit (`:3755-3760`).
- Scenario 5 and the Interface contract rest on A. Without it, a solo intent on a units route never reaches done in Earnest.

**Evidence (Spike F):**

- **Class:** maintainer-only. The evidence prices A and adds a third option.
- **Evidence:** E2 on Earnest's side: a solo row with no `Unit` approves no per-unit stage (E2a). A solo row with only `Unit` joins, with no `Gate Scope`, `Gate Stages` or `Attempt Generation`: E2b with the id-rule spelling today, and E2c with the directory spelling once answer 14 lands (P-E2c, run on spike F's prototype, not on Task 2's `_expand`). So option A's rows need only the `Unit` field on top of what the solo path writes.
- **Unlisted fork work under A:** the two pieces named in A above, the `--unit` rejection outside team mode and the unscoped sensor firing. Neither is in the plan's Interface contract or in `02`'s Fork delta.
- **Recommended answer:** A, with its fork work priced. Accepted as recommended (DECIDED, user, 2026-11-25).

## Interface contract with the fork

This is what the gate calls. `<fork>` is `$EARNEST_AIDLC_FORK`. Every call except the graph compile runs with these settings; the compile runs in its temporary directory, with only `HOME`, `PATH` and `ISOLATED_GIT`:

- the working directory is the built fixture repository;
- the environment holds only:
  - `HOME`, set to an empty directory in pytest's temporary space, so no per-user configuration under `~` reaches the fork;
  - `PATH`, set to `<venv bin>:<bun dir>:/usr/bin:/bin`;
  - `ISOLATED_GIT` from `tests/sarif.py`: the `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`, `XDG_CONFIG_HOME` and `GIT_ATTR_NOSYSTEM` values, which `_isolated_git` in `tests/conftest.py` also sets from it;
  - `AIDLC_PROJECT_DIR=<repo>` and `AIDLC_RUNTIME_PROJECT_DIR=<repo>`. Without the second, a write the fork marks mutable falls back to `<fork>/core` when the fork runs from source (`core/tools/aidlc-runtime-paths.ts:352-360`, `:515-523`, `:697-705`);
  - `AIDLC_STAGE_GRAPH=<graph>`.

The calls, in order:

1. **Compile the graph** (upstream already has this): run `bun <tmp>/compile-graph.ts <fork> <tmp>/stage-graph.json`. The script imports `compileStageGraph` from `<fork>/core/tools/aidlc-graph.ts` and writes its `.json`. It runs once per test session.
2. **Run the sensor** (the delta): `bun <fork>/core/tools/aidlc.ts engine sensor-earnest --stage <slug> --output-path <abs path of a deliverable>`.
   - It exits 0, and its stdout is one JSON object with `pass` (a boolean) and `findings_count` (an integer).
   - `pass` is true exactly when `earnest check --stage <stage> --intent <record dir>` exits 0.
   - `<stage>` is the bare slug for a solo stage. When the output path lies under `<record dir>/<phase>/<unit directory>/<slug>/`, it is `<phase>/<unit directory>/<slug>`.
   - `findings_count` is the number of results in that run's SARIF log.
3. **Open the gate** (upstream, plus the delta's added fields): `bun <fork>/core/tools/aidlc.ts engine state gate-start <slug> [--unit <unit name>]`, with `AIDLC_ALLOW_DIRECT_STATE_TRANSITIONS=1`.
   - It exits 0 once the `earnest` sensor has fired and passed. That sensor's run writes the stage's run header.
   - Its `STAGE_AWAITING_APPROVAL` row carries `Assessment Hash` (answer 2).
4. **Approve** (upstream, plus the delta's added fields): `bun <fork>/core/tools/aidlc.ts engine state approve <slug> [--unit <unit name>] --user-input Approve`, with the same variable. It exits 0 and appends one `GATE_APPROVED` block to `<record dir>/audit/<hostname>-<clone id>.md`. The block holds:
   - `Stage: <slug>`;
   - `Assessment Hash`: the run header's `hash`, verbatim;
   - `Items`: the run header's `items`, in the form `plan._items` reads (the form the `seeded-change` rows use);
   - `Approved By: human`;
   - for a per-unit stage, `Unit: <unit directory>` (answer 14).

## Global Constraints

- **Layout and lint.** M2's bar applies: ruff (line length 120, complexity 10, five arguments, Google docstrings), `ruff format`, `mypy --strict`, and vulture at 80.
- **The fork is read-only.** No task edits, commits, stashes or pushes a fork file, or switches the fork's branch, except Task 5 Step 1, which fetches and detaches the checkout at the pinned sha once the maintainer approves. No `gh` command runs from the fork clone, which defaults to `awslabs` (F1).
- **The gate leaves the checkout clean.**
  - The graph and the fixture copies live in pytest's temporary directories, not in the checkout.
  - `git -C "$EARNEST_AIDLC_FORK" status --short --ignored` is identical before and after a gate run (Task 6).
  - The gate never runs `bun install`, and needs none (answer 12).
- **Fail, never skip.** A missing `EARNEST_AIDLC_FORK`, a path without `core/tools/aidlc.ts`, or no `bun` on `PATH` each call `pytest.fail` with a one-line message that names the cause; a missing `bun` goes through `tests/tools.py`'s `require`, the one "missing tool" helper that M8's `require_tools` shares. Neither the module nor its helpers use `pytest.skip`, `skipif` or `importorskip`, and one guard in `tests/unit/test_tools.py` scans for them.
- **A scrubbed environment for every fork call** (F17). The fork never sees the caller's session, host settings or Git configuration.
- **Read the fork's rows by content.** Never read them by order or timestamp: the fork writes wall-clock times, and the fixture's rows are dated 2026-09-26 (F17).
- **Git steps after a fork call.** Once the fork has run, the work tree holds its untracked files (F17). No "Git lists no new file" step follows a fork call.
- **Process.**
  - No agent `rm`s a path it did not create.
  - Each commit stages its task's paths by name, with no `--no-verify`.
  - `.pi-herdsman/` stays untracked.

## Review Focus

- **Fail, not skip.** `tests/unit/test_fork.py` asserts `pytest.fail.Exception` for each missing precondition, never `pytest.skip.Exception`.
- **The hash binds.** The approve scenarios assert that `Assessment Hash` equals the run header's `hash` byte for byte, and that `Items` lists the header's `items`. Checking only that the fields exist is not enough.
- **`pass: false` arrives with exit 0.** A script that exits 1 would be read by AI-DLC as `PASSED script-error` (F5). The failing-sensor scenario asserts both the exit code and the value.
- **The per-unit stage is named in full.** The per-unit sensor scenario asserts that the record holds a run header keyed `<record dir>/construction/u2-notice/functional-design`. A bare slug on the units variant makes `earnest check` exit 2, so a sensor that passed one would print `pass: false`, which the scenario's `pass true` catches. Run headers always carry a phase, so no header keyed by a bare slug can exist to check against.
- **Earnest reads the fork's row.** After each approve, `earnest plan` shows the stage's approval as `current, human`. This end-to-end check proves that the field names and the `Unit` join agree.
- **The second check at approve keeps the hash.** Before approve, gate-start rewrites `aidlc-state.md` and adds `<record dir>/.aidlc-engine/` and the shard. Answer 3's equality holds only if the hash leaves those paths out. `01` keeps the route and the approvals outside the hash. E3d shows the hash leaves out a rewritten state file, a new shard and `.aidlc-engine/`, written by hand; Task 5 Step 3 checks this on the real delta.
- **The fork checkout stays clean** (Task 6).

## Task order and the scenarios each turns green

The scenario titles are PROPOSED, and Task 0 writes them into `04`. The clause column maps each scenario to the M7 exit behavior of `03`:

- (a) the sensor prints `{pass, findings_count}` and exits 0 for a `seeded-change` stage;
- (b) `pass` is false while an error sits behind or current;
- (c) approve writes `GATE_APPROVED` with `Assessment Hash`, `Items` and `Approved By`;
- (d) for a per-unit stage, the sensor passes `<phase>/<unit directory>/<slug>`, and approve writes `Unit` with those fields.

The guard "fails rather than skips" is tested at the unit tier, in `tests/unit/test_fork.py`, because a scenario cannot remove its own Background.

| Scenario | Clause |
| --- | --- |
| "The earnest sensor passes a stage with no error behind or current" | (a) |
| "The earnest sensor fails a stage while an error sits behind" | (a), (b) |
| "Approving a stage at the gate records the assessment it rests on" | (c) |
| "The earnest sensor names a per-unit stage by its unit directory" | (a), (d) |
| "Approving a per-unit stage records its unit with the assessment" | (c), (d) |

| Task | Content | Depends on | Scenarios green after it |
| --- | --- | --- | --- |
| 0 | The docs commit: the decisions, `04`'s M7 section, the rows of `01` and `02`, the Fork delta's base, the link in `03` | the maintainer's decisions | none |
| 1 | `tests/fork.py`: locate the checkout, compile the graph, run the fork, write the human's turn; unit tests | T0 | none (unit tier) |
| 2 | `Unit` joined by unit directory in `plan.py`, with its fixture rows, tests and M5 Gherkin (answer 14) | T0 | none new; M2b and M5 stay green |
| 3 | The gate overlays, the feature, the step module, and the `addopts` that keeps it out of a bare run, red | T1, T2 | none |
| 4 | Make and CI: `make test-aidlc-fork` and the `test-aidlc-fork` job | T3 | none; `make test` stays green |
| 5 | Pin the fork commit that holds the delta, and run the exit command | T4, and the delta merged in the fork | all 5 |
| 6 | The full suite, lint, the clean-checkout check, and the pre-PR review | T5 | all 5, with M1 to M6 unchanged |

**Regression expectations:**

- For Tasks 1 to 4, the regression run is `rtk proxy uv run pytest; echo $?` in `packages/earnest/`, and its evidence is the printed code. From Task 3 on, `addopts` leaves the fork module out of it. It stays green at the count the M7 branch records at the start of Task 1, plus the tests each task adds.
- Tasks 1 to 5 each record their exact count in this plan.

## File Structure

| Path | Responsibility | Task |
| --- | --- | --- |
| `docs/superpowers/plans/2026-11-20-aidlc-fork.md` | this plan: the decisions (Task 0), then each task's counts and notes | 0-5 |
| `docs/design/01-logic-design.md`, `02-structural-design.md`, `03-implementation-plan.md`, `04-bdd-test-plan.md` | the decisions, the resolved rows, `04`'s M7 section, the link | 0 |
| `packages/earnest/tests/fork.py` | `Fork`, `fork_checkout`, `compile_graph`, `run_fork`, `fork_shard`, `human_turn`, `gate_approvals` | 1 |
| `packages/earnest/tests/unit/test_fork.py` | fail-not-skip and scrubbed-environment tests | 1 |
| `packages/earnest/tests/tools.py`, `tests/unit/test_tools.py` | `require(name, hint, path=None)`, the one fail-never-skip lookup of a tool, and the one never-skips guard; M8 shares both. Made by whichever of M7 and M8 lands first | 1 |
| `packages/earnest/src/earnest/plan.py` | `Unit` joined by unit directory through one helper | 2 |
| `packages/earnest/tests/unit/test_plan.py` | the join tests | 2 |
| `packages/earnest/tests/fixtures/seeded-change/units/` (the audit shard `fixture-a1b2c3d4.md`, `FUTURE-FORMAT.md`) | `**Unit**: u1-limiter` in place of `**Unit**: u1`; the value described as the construction directory | 2 |
| `packages/earnest/tests/unit/test_plan.py`, `tests/integration/test_task_change.py`, `tests/integration/test_seeded_change.py`, `tests/features/unit_status.feature` | gate rows name the unit's directory; `UNITS_SHA` moves | 2 |
| `packages/earnest/tests/steps/test_unit_status.py` | the guard at line 49 and the assertion at line 124 name `u1-limiter` and `u2-notice` (Task 2); `define_twice` moves to `conftest.py` (Task 3) | 2, 3 |
| `packages/earnest/tests/fixtures/seeded-change/fork/` | the solo gate overlay: the intent's `aidlc-state.md`, with `code-generation` at `[-]`, `build-and-test` at `[ ]` and `- **Review Override**: none`, plus `aidlc/.aidlc-clone-id` | 3 |
| `packages/earnest/tests/fixtures/seeded-change/fork-units/` | the units gate overlay: the units variant's `aidlc-state.md` without `Unit Ownership: team`, with `- **Review Override**: none` and `functional-design` reopened for `u2-notice` (Task 3 Step 2), plus `aidlc/.aidlc-clone-id` | 3 |
| `packages/earnest/tests/sarif.py` | `ISOLATED_GIT`, the Git isolation values shared by `_isolated_git` and the fork's environment; `append_block` takes an optional shard path | 1 |
| `packages/earnest/tests/conftest.py` | `fake_executable(directory, name, script)`, hoisted from `fake_python` of `tests/unit/test_impact.py` (Task 1; the first of M7 and M8 to land hoists it); `_isolated_git` sets `ISOLATED_GIT` (Task 1); `fork` and `fork-units` added to `_OVERLAYS`; `define_twice` moved here from `test_unit_status.py` (Task 3) | 1, 3 |
| `packages/earnest/tests/features/aidlc_fork.feature` | M7's 5 scenarios, copied verbatim from `04` | 3 |
| `packages/earnest/tests/steps/test_aidlc_fork.py` | the steps; the exit command | 3 |
| `packages/earnest/pyproject.toml` | `--ignore` of the fork module in pytest's `addopts` | 3 |
| `packages/earnest/Makefile`, `Makefile` | the `test-aidlc-fork` target | 4 |
| `.github/workflows/ci.yml` | the `test-aidlc-fork` job | 4, 5 |
| `CLAUDE.md` | the Build section names `make test-aidlc-fork` and `EARNEST_AIDLC_FORK` | 4 |

Outside the package, only Task 0's docs, the Makefiles, `ci.yml` and `CLAUDE.md` change. No fork path appears in this table.

## Known limits

- **Source, not packaged.** The gate runs the fork from source with a compiled graph. The fork's own tests run the packaged tree (F15).
- **Direct transitions.** The gate drives approve through the direct transitions, with `AIDLC_ALLOW_DIRECT_STATE_TRANSITIONS=1`, a `HUMAN_TURN` row written by hand, and the reviewer gate turned off by `Review Override: none`. The orchestrated path and the session binding stay with the fork's tests.
- **Paths this gate does not drive** (F16): the team per-unit gates, `unit-end`, `unit-merge` and `Approved By: automatic`. The fork's `t-gate-approved-assessment.test.ts` covers their emit sites.
- **`unit-end` safety** (answer 13, option (c), decided). A stage listed ahead of the unit's frontier reports its errors as notes, passes, and never holds the gate (E8b).
- **A dirty run header** (answer 1, decided). Neither the gate nor approve refuses it. A dirty header's `commit` is HEAD, which lacks the approved bytes, and `change_baseline` takes that `commit` as the baseline when the approval carries the header's hash (`plan.py:1435-1449`, `cli.py:281-292`), so the approved bytes then count as changed since the baseline. A dirty run also takes no coverage map (`cli.py:424`). The gate shows `dirty` beside the hash so the human sees it.
- **Pins.**
  - Only CI pins `AIDLC_FORK_REF` and Bun 1.4.2. A local run uses whatever commit and Bun the maintainer has.
  - The per-unit approve scenario rests on answer 17's option A (decided), which needs fork work beyond the `--unit` argument, and on the `--unit` form of the Interface contract until the fork's plan confirms it (Task 0 Step 4).
- **The approve check costs a run.** Under answer 3, each approve runs `earnest check --stage` once more. On a clean tree that run takes a coverage map: the target's tests under pytest-cov, up to 900 s (E9).
- **Follow-up, not in this diff: reuse one coverage map across sensor firings.** Each `earnest` firing of a `unit-end` gate, and each approve, takes its own map. Sharing one across firings is a change to earnest's design, not to this gate.

---

## Tasks

### Task 0: The docs commit

**Files:** Modify `docs/superpowers/plans/2026-11-20-aidlc-fork.md`, `docs/design/01-logic-design.md`, `docs/design/02-structural-design.md`, `docs/design/03-implementation-plan.md` and `docs/design/04-bdd-test-plan.md`.

- [x] **Step 1:** Record the seventeen decisions (DECIDED (user, 2026-11-25), each in its row above). Row 4 is option A and the rest follow:
  - Row 1: neither the gate nor approve refuses a dirty tree; `dirty` shows beside the hash; the baseline cost is a known limit.
  - Row 4: A, KEEP `nullrul/aidlc-workflows` and revise L3 in `02`. This goes against Spike F's recommendation of B and needs the 911-commit upstream sync first.
  - Row 11: agents push feature branches and open pull requests on the fork after the pre-PR review, never to main, `--force-with-lease` only; the user merges.
  - Row 13: (c), the fork fires `earnest` once per listed stage; the weaker guard is in Known limits.
  - Row 17: A, `--unit <name>` on solo gate-start and approve, with the two pieces of fork work it needs.
  - Rows 2, 3, 5 to 10, 12, 14 to 16: accepted as recommended.
- [ ] **Step 2:** Write the M7 section of `04`, after M6's. It holds:
  - the feature path;
  - the fixture: `seeded-change` with the `fork` overlay, its units variant with the `fork-units` overlay, and a local fork checkout;
  - SC9;
  - the readings;
  - the Gherkin below, marked PROPOSED.

  The two places that said M7's and M8's scenarios come "when each milestone's plan is written" were already reworded on this branch (M8 and M9 now have sections, so they name M7 alone): the sentence under the milestone table and the Future directions bullet, both found by `grep -n 'scenarios of M7'`. Line numbers have moved. When this section lands, reword both to say that M7's section is here. The milestone table's M7 row stays as it is.
- [ ] **Step 3:** Resolve the thirteen rows with the decisions, each where it is written (`01`'s and `02`'s Open questions; an M2b row that only `03`'s M7 entry names is resolved there), and add rows 14 to 17 as resolved. Then make the edits the decisions call for:
  - `01`, lines 167-169 and 671, and `02`, line 200, for answer 14: each says a gate row's `Unit` is the unit's name by the id rule, and comes to say the unit's construction directory;
  - `04`'s unit Gherkin, for answer 14. Lines 766, 795 and 802 name the unit's directory (`u2-notice`, `u1-limiter`). In SC8's Examples (lines 782-790), the `unit` column's `u2` becomes `u2-notice`, `u2-notice` becomes `u2`, and `U2` becomes `U2-notice`; each row keeps its approval. In the rejection outline's Examples (lines 821-824), `u1` becomes `u1-limiter` and `u2` becomes `u2-notice`; `-` and `u9` stay. Line 700's `unit "u1"` is a unit-table id and stays. The maintainer's approval of answer 14 is the ratification `04`'s "Fixed for the loop" asks for;
  - `01`'s mapping table, for answers 6 and 7;
  - in `02`'s Fork delta, the base commit and the tree (answer 15), and the approve check in the `aidlc-state.ts` bullet (answer 3);
  - for answer 13, option (c): the new row in `01`'s Open questions;
  - for answer 4, option A: revise L3 in `02` ("The AI-DLC fork is its own repository, downstream only") to say the fork is the GitHub fork `nullrul/aidlc-workflows`, downstream only through the per-clone `no-push` and `set-default` settings, and update the fork's name in `02`'s Fork delta and Future directions where they say standalone or mirror-pushed (`grep -n 'mirror\|standalone' docs/design/02-structural-design.md`);
  - for answer 17, option A: add the two pieces of fork work to `02`'s Fork delta (`--unit` accepted outside team mode in `teamGateContext`, and unit-scoped sensor firing), and per-listed-stage firing for answer 13;
  - a link to this plan from M7's entry in `03`.
- [ ] **Step 4:** Once the fork's plan exists, and the upstream sync of answer 4 has landed, record the synced sha and compare the plan's interface with the Interface contract above. Record any difference in this plan before Task 3 starts: the `--unit` form, the sensor's JSON, and the shard name.
- [ ] **Step 5:** Run `LINT_FILE=<path> make lint-file` on each changed file and check the exit code with `rtk proxy`. Commit `docs: M7 aidlc_fork plan and gating answers`.

The Gherkin for `04`, PROPOSED. Every finding count comes from Earnest's side of the Fork facts. The two last lines of each approve scenario reuse the shared steps `the coding agent runs earnest plan` and `"{stage}" has the approval "{approval}"` from `tests/conftest.py`.

```gherkin
Feature: AI-DLC fork
  The repo maintainer approves an AI-DLC stage at the fork's gate. The fork's
  earnest sensor shows Earnest's check there, and the fork's approve transition
  writes into AI-DLC's audit trail the assessment the approval rests on (UC9;
  SC9). The feature drives a local fork checkout with Bun, and fails when
  either is missing.

  Background:
    Given a local AI-DLC fork checkout with Bun

  Scenario: The earnest sensor passes a stage with no error behind or current (SC9)
    Given the repo maintainer's "seeded-change" repository with "code-generation" at its gate
    When AI-DLC fires the earnest sensor for "requirements-analysis" on "inception/requirements-analysis/requirements.md"
    Then the sensor prints pass true with findings count 0
    And the sensor exits zero

  Scenario: The earnest sensor fails a stage while an error sits behind (SC9)
    Given the repo maintainer's "seeded-change" repository with "code-generation" at its gate
    And the coding agent defines "req~rate-limit~1" a second time at the end of the requirements
    When AI-DLC fires the earnest sensor for "requirements-analysis" on "inception/requirements-analysis/requirements.md"
    Then the sensor prints pass false with findings count 1
    And the sensor exits zero

  Scenario: Approving a stage at the gate records the assessment it rests on (SC9)
    Given the repo maintainer's "seeded-change" repository with "code-generation" at its gate
    When AI-DLC opens the gate of "code-generation"
    And the repo maintainer approves "code-generation" at the fork's gate
    And the coding agent runs earnest plan
    Then the fork's audit holds one approval of "code-generation" with the hash and items of the run header for "construction/code-generation", approved by "human"
    And "construction/code-generation" has the approval "current, human"

  Scenario: The earnest sensor names a per-unit stage by its unit directory (SC9)
    Given the repo maintainer's "seeded-change" units variant with the functional design of "u2-notice" at its gate
    When AI-DLC fires the earnest sensor for "functional-design" on "construction/u2-notice/functional-design/functional-spec.md"
    Then the sensor prints pass true with findings count 0
    And the sensor exits zero
    And the record holds a run header for "construction/u2-notice/functional-design"

  Scenario: Approving a per-unit stage records its unit with the assessment (SC9)
    Given the repo maintainer's "seeded-change" units variant with the functional design of "u2-notice" at its gate
    When AI-DLC opens the gate of unit "u2-notice" for "functional-design"
    And the repo maintainer approves for unit "u2-notice" the stage "functional-design" at the fork's gate
    And the coding agent runs earnest plan
    Then the fork's audit holds one approval for unit "u2-notice" of "functional-design" with the hash and items of the run header for "construction/u2-notice/functional-design", approved by "human"
    And "construction/u2-notice/functional-design" has the approval "current, human"
```

### Task 1: The fork helper

**Files:** Create `packages/earnest/tests/fork.py`, and, unless M8 landed first and made them, `packages/earnest/tests/tools.py` and `tests/unit/test_tools.py`. Modify `packages/earnest/tests/sarif.py`, `packages/earnest/tests/conftest.py`, `packages/earnest/tests/unit/test_impact.py` (the `fake_executable` hoist, unless M8 did it), and this plan, where the task records its counts. Test `packages/earnest/tests/unit/test_fork.py`.

**Interfaces:**

- Consumes:
  - `EARNEST` and `RECORD` from `tests/sarif.py`;
  - `parse_audit(text: str, shard: str) -> list[Event]` from `earnest.plan`, where `Event.fields` is a `dict[str, str]`;
  - `append_block(repo, event, timestamp, fields=(), shard=SHARD)` from `tests/sarif.py`, given the optional `shard` path of Step 4;
  - `require(name, hint, path=None) -> Path` from `tests/tools.py` (Step 4) and `fake_executable(directory, name, script) -> Path` from `tests/conftest.py` (Step 4).
- Produces, all in `tests/fork.py`:
  - `FORK_ENV = "EARNEST_AIDLC_FORK"`, `ENTRY = "core/tools/aidlc.ts"`, and `CLONE_ID = "fixturecloneid01"`;
  - `@dataclass(frozen=True) class Fork: root: Path; bun: Path; graph: Path; home: Path`;
  - `def fork_checkout() -> tuple[Path, Path]`;
  - `def fork_env(bun: Path, home: Path, **extra: str) -> dict[str, str]`;
  - `def compile_graph(root: Path, bun: Path, out: Path) -> Fork`;
  - `def run_fork(repo: Path, fork: Fork, *args: str, direct: bool = False) -> subprocess.CompletedProcess[str]`;
  - `def fork_shard(repo: Path) -> Path`;
  - `def human_turn(repo: Path) -> None`, which calls `append_block` of `tests/sarif.py` with the fork's shard;
  - `def gate_approvals(repo: Path) -> list[Event]`.

- [ ] **Step 1:** Record the regression count: run `rtk proxy uv run pytest -q; echo $?` in `packages/earnest/`, and write the passed count into this task.
- [ ] **Step 2:** Write the failing tests in `tests/unit/test_fork.py`:

```python
"""The aidlc_fork gate's helper fails, never skips, and runs the fork in a scrubbed environment."""

from pathlib import Path

import pytest

from tests.conftest import fake_executable
from tests.fork import ENTRY, FORK_ENV, Fork, fork_checkout, fork_env, run_fork
from tests.sarif import EARNEST, ISOLATED_GIT


def _checkout(tmp_path: Path) -> Path:
    (tmp_path / ENTRY).parent.mkdir(parents=True)
    (tmp_path / ENTRY).write_text("")
    return tmp_path


def test_missing_variable_fails(monkeypatch):
    monkeypatch.delenv(FORK_ENV, raising=False)
    with pytest.raises(pytest.fail.Exception, match=FORK_ENV):
        fork_checkout()


def test_relative_path_fails(monkeypatch):
    monkeypatch.setenv(FORK_ENV, "aidlc-workflows")
    with pytest.raises(pytest.fail.Exception, match="not an AI-DLC fork checkout"):
        fork_checkout()


def test_path_without_the_entry_fails(monkeypatch, tmp_path):
    monkeypatch.setenv(FORK_ENV, str(tmp_path))
    with pytest.raises(pytest.fail.Exception, match="not an AI-DLC fork checkout"):
        fork_checkout()


def test_missing_bun_fails(monkeypatch, tmp_path):
    monkeypatch.setenv(FORK_ENV, str(_checkout(tmp_path / "fork")))
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    with pytest.raises(pytest.fail.Exception, match="bun"):
        fork_checkout()


def test_found_checkout_and_bun(monkeypatch, tmp_path):
    bun = fake_executable(tmp_path / "bin", "bun", "")
    monkeypatch.setenv(FORK_ENV, str(_checkout(tmp_path / "fork")))
    monkeypatch.setenv("PATH", str(bun.parent))
    assert fork_checkout() == (tmp_path / "fork", bun)


def test_environment_is_scrubbed(monkeypatch):
    monkeypatch.setenv("CLAUDE_SESSION_ID", "leak")
    env = fork_env(Path("/opt/bun/bin/bun"), Path("/tmp/home"), AIDLC_PROJECT_DIR="/repo")
    assert set(env) == {"HOME", "PATH", "AIDLC_PROJECT_DIR", *ISOLATED_GIT}
    assert env["PATH"].split(":")[:2] == [str(EARNEST.parent), "/opt/bun/bin"]
    assert env["HOME"] == "/tmp/home"


def test_run_fork_scrubs_and_names_the_repo(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_SESSION_ID", "leak")
    bun = fake_executable(tmp_path, "bun", "env")
    fork = Fork(tmp_path, bun, tmp_path / "stage-graph.json", tmp_path / "home")
    seen = dict(line.split("=", 1) for line in run_fork(tmp_path, fork, "engine").stdout.splitlines())
    assert seen["AIDLC_PROJECT_DIR"] == seen["AIDLC_RUNTIME_PROJECT_DIR"] == str(tmp_path)
    assert seen["HOME"] == str(tmp_path / "home")
    assert "CLAUDE_SESSION_ID" not in seen
```

  The one never-skips guard is not here: it is `test_the_gate_never_skips` of `tests/unit/test_tools.py`, which M8 shares. It looks for skip calls, skip and xfail marks, and `@skip` tags, not the word, because the helpers' docstrings say "never skip". It scans `tests/tools.py`, `tests/fork.py`, `tests/steps/test_aidlc_fork.py` and `tests/features/aidlc_fork.feature` (a Gherkin `@skip` tag becomes a skip mark, so the feature is scanned too), each when it exists, and M8's files in their turn; this plan adds its files to the list and writes no second guard. `tests/unit/test_tools.py` also holds the tests of `require`: found, it returns the path; missing, it raises `pytest.fail.Exception` naming the tool and the hint.

- [ ] **Step 3:** Run `rtk proxy uv run pytest tests/unit/test_fork.py; echo $?`. Expected: a non-zero code; collection fails with `ModuleNotFoundError: tests.fork`.
- [ ] **Step 4:** Share the helpers.
  - `fake_executable`: in `tests/conftest.py`, hoist `fake_python` of `tests/unit/test_impact.py` (lines 91-95) into `def fake_executable(directory: Path, name: str, script: str) -> Path`, which makes `directory`, writes `#!/bin/sh` and `script` to `directory/name`, marks it `0o755` and returns it. `fake_python(tmp_path, script)` becomes `str(fake_executable(tmp_path, "python", script))` and `test_impact.py` imports it from `tests.conftest`. If M8 landed first, it is already there.
  - `tests/tools.py` and its tests, unless M8 made them: `def require(name: str, hint: str, path: str | None = None) -> Path`, which returns `Path(shutil.which(name, path=path))` and calls `pytest.fail(f"{name} is missing: {hint}", pytrace=False)` when there is none; and `tests/unit/test_tools.py` with the tests of the paragraph above.
  - `append_block` in `tests/sarif.py` gains an optional last parameter, `shard: str | Path = SHARD`, in place of its hard-coded `SHARD`: `write(repo, shard, read(repo, shard) + block(event, timestamp, fields))`. Every existing call is unchanged. `fork_shard` is not changed: it finds the fork's shard, and appends nothing.
  - The Git isolation values. Add `import os` to the imports of `tests/sarif.py`, and this constant after them:

```python
ISOLATED_GIT = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "XDG_CONFIG_HOME": os.devnull,  # keeps the default core.excludesFile and core.attributesFile out
    "GIT_ATTR_NOSYSTEM": "1",
}
```

  In `tests/conftest.py`, import it and replace the four `monkeypatch.setenv` lines of `_isolated_git` (lines 80-83) with `for name, value in ISOLATED_GIT.items(): monkeypatch.setenv(name, value)`, on two lines. Then write `tests/fork.py`:

```python
"""Find the AI-DLC fork checkout and run its tools against a built fixture, for the aidlc_fork gate."""

import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from earnest.plan import Event, parse_audit
from tests.sarif import EARNEST, ISOLATED_GIT, RECORD, append_block
from tests.tools import require


FORK_ENV = "EARNEST_AIDLC_FORK"
ENTRY = "core/tools/aidlc.ts"
CLONE_ID = "fixturecloneid01"  # the overlays pin aidlc/.aidlc-clone-id, so the fork's shard name ends in it
_COMPILE = """\
import { writeFileSync } from "node:fs";
const [fork, out] = process.argv.slice(2);
const { compileStageGraph } = await import(`${fork}/core/tools/aidlc-graph.ts`);
writeFileSync(out, compileStageGraph().json);
"""


@dataclass(frozen=True)
class Fork:
    """A fork checkout, the bun that runs it, the stage graph compiled from it, and the empty HOME its calls see."""

    root: Path
    bun: Path
    graph: Path
    home: Path


def fork_checkout() -> tuple[Path, Path]:
    """Return the fork checkout and bun; fail the test, never skip it, when either is missing."""
    value = os.environ.get(FORK_ENV, "")
    if not value:
        pytest.fail(f"set {FORK_ENV} to the absolute path of a local AI-DLC fork checkout", pytrace=False)
    root = Path(value)
    if not root.is_absolute() or not (root / ENTRY).is_file():
        pytest.fail(f"{FORK_ENV}={value} is not an AI-DLC fork checkout: it has no {ENTRY}", pytrace=False)
    return root, require("bun", "the aidlc_fork gate runs the fork with Bun")


def fork_env(bun: Path, home: Path, **extra: str) -> dict[str, str]:
    """Return the only environment a fork call sees: no session, host setting or Git configuration leaks in."""
    path = os.pathsep.join([str(EARNEST.parent), str(bun.parent), "/usr/bin", "/bin"])
    return {"HOME": str(home), "PATH": path, **ISOLATED_GIT, **extra}


def compile_graph(root: Path, bun: Path, out: Path) -> Fork:
    """Compile the fork's stage graph with the fork's own compileStageGraph into out, and return the Fork."""
    script, graph, home = out / "compile-graph.ts", out / "stage-graph.json", out / "home"
    script.write_text(_COMPILE)
    home.mkdir()
    done = subprocess.run(
        [str(bun), str(script), str(root), str(graph)],
        cwd=out, env=fork_env(bun, home), capture_output=True, text=True, check=False,
    )
    if done.returncode != 0 or not graph.is_file():
        pytest.fail(f"the fork's stage graph did not compile: {done.stderr.strip()}", pytrace=False)
    return Fork(root, bun, graph, home)


def run_fork(repo: Path, fork: Fork, *args: str, direct: bool = False) -> subprocess.CompletedProcess[str]:
    """Run `bun <fork>/core/tools/aidlc.ts <args>` in repo; direct allows the gate-start and approve transitions."""
    extra = {
        "AIDLC_PROJECT_DIR": str(repo),
        "AIDLC_RUNTIME_PROJECT_DIR": str(repo),  # else mutable writes land in <fork>/core
        "AIDLC_STAGE_GRAPH": str(fork.graph),
    }
    if direct:
        extra["AIDLC_ALLOW_DIRECT_STATE_TRANSITIONS"] = "1"
    return subprocess.run(
        [str(fork.bun), str(fork.root / ENTRY), *args],
        cwd=repo, env=fork_env(fork.bun, fork.home, **extra), capture_output=True, text=True, check=False,
    )


def fork_shard(repo: Path) -> Path:
    """Return the one audit shard the fork writes in the seeded intent, named by the pinned clone id."""
    shards = sorted((repo / RECORD / "audit").glob(f"*-{CLONE_ID}.md"))
    assert len(shards) == 1, shards
    return shards[0]


def human_turn(repo: Path) -> None:
    """Append the human's answer at the open gate: a HUMAN_TURN row after gate-start's rows."""
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    append_block(repo, "HUMAN_TURN", stamp, shard=fork_shard(repo))


def gate_approvals(repo: Path) -> list[Event]:
    """Return the GATE_APPROVED rows of the fork's shard, read as Earnest reads every shard."""
    shard = fork_shard(repo)
    return [event for event in parse_audit(shard.read_text(), shard.name) if event.fields["Event"] == "GATE_APPROVED"]
```

- [ ] **Step 5:** Run `rtk proxy uv run pytest tests/unit/test_fork.py tests/unit/test_tools.py; echo $?` and the regression run. Expected: 7 passed in `test_fork.py`, plus the tests of `test_tools.py` (3 when this plan makes the file: found, missing, the guard; none new when M8 did) and `0`, and the regression run is green at Step 1's count plus those.
- [ ] **Step 6:** Check the graph compile against the real checkout, without changing it:
  - Run `git -C "$EARNEST_AIDLC_FORK" status --short --ignored` and save the output.
  - Run `uv run python -c 'from pathlib import Path; import tempfile; from tests.fork import compile_graph, fork_checkout; r, b = fork_checkout(); print(compile_graph(r, b, Path(tempfile.mkdtemp())).graph.stat().st_size)'` from `packages/earnest/`.
  - Expected: a size above zero, and a second `git status --short --ignored` identical to the first.
  - If the compile fails on a missing module, stop and record it: Spike F found no import outside `node:` and `bun:` under the fork's `core/`, so that would contradict answer 12. The agent does not run `bun install`; the maintainer decides whether to.
- [ ] **Step 7:** Commit `test: aidlc_fork gate helper that fails without a fork checkout`.

### Task 2: `Unit` joins by unit directory

Answer 14 is decided as proposed (DECIDED, user, 2026-11-25), so this task runs.

**Files:** Modify:

- this plan, where the task records its grep hits and counts;
- `packages/earnest/src/earnest/plan.py`: the keys at lines 637-642, the `floors` comprehension at line 644, the `Unit` docstring and field at lines 336-343, and the parameters and docstrings of `_gate_keys`, `_generation`, `_voids`, `_unit_approval` and `_unit_named` (lines 666-775);
- `packages/earnest/tests/fixtures/seeded-change/units/aidlc/spaces/default/intents/260926-checkout/audit/fixture-a1b2c3d4.md` (line 30);
- `packages/earnest/tests/fixtures/seeded-change/units/FUTURE-FORMAT.md`;
- `packages/earnest/tests/features/unit_status.feature`: lines 166, 195 and 202, SC8's Examples (lines 182-190) and the rejection outline's Examples (lines 221-224), so they read as `04` does after Task 0 Step 3. Line 100's `unit "u1"` is a unit-table id and stays;
- `packages/earnest/tests/steps/test_unit_status.py`: the guard at line 49 becomes the exact field `"**Unit**: u1-limiter\n"`, so a substring cannot pass it, and the assertion at line 124 becomes `(unit, slug) == ("u2-notice", "code-generation")`. The other steps write `Unit` as the Gherkin gives it, so they stay;
- `packages/earnest/tests/unit/test_plan.py`: every gate row that `units_plan` (line 1632) joins through a unit table takes that unit's directory from the table it joins: `TABLE` (lines 1616-1618: `A` to `a-dir`, `B` to `b-dir`), `FALLBACK_TABLE` (line 2367) or the table at line 2479. For example `Unit="a"` becomes `Unit="a-dir"`. That includes unit names fed in as data: the parametrize list at lines 2055-2058 and the enumerated list at lines 2331-2334. The direct `_gate_keys` tests through `keys()` (line 1861) pass their own `LANES` and stay;
- `packages/earnest/tests/integration/test_task_change.py` (line 121): `("Unit", "u1")` becomes `("Unit", "u1-limiter")`, since the test runs on `units_repo()`;
- `packages/earnest/tests/integration/test_seeded_change.py`: the shard literal at line 215, whose `**Unit**: u1\n` becomes `**Unit**: u1-limiter\n`, and `UNITS_SHA = "4cdc2f5"` at line 287. That constant pins the units variant's commit, which moves when the overlay's audit shard changes.

**Interfaces:**

- Consumes: the unit table's join, which gives each unit's name and directory (`01`, lines 640-647).
- Produces: no new function or parameter. `stage_ids` and `lanes` (`plan.py:637-642`) key by `unit.directory` instead of `unit.name`, and `floors` follows `lanes`. `_gate_keys`, `_generation`, `_voids`, `_unit_approval` and `_unit_named` then compare a row's `Unit` with a directory, unchanged. No signature grows: `_unit_approval` already takes five parameters, the `max-args` ruff allows in `src/`. `_gate_keys`, `_generation` and `_voids` name the key `directory`, and all five docstrings say unit directory.

**Starting code (unmeasured).** Spike F prototyped a translation in `_expand` (`plan.py:622`) that took both spellings of `Unit`; it did not run the code below, which joins by directory alone. Three statements of `_expand` change, and the rest of the function stays as it is: the keys of `stage_ids` and `lanes`, and the comprehension of `floors`. The two `if unit.directory` guards narrow `Unit.directory` from `str | None` to `str`, which `_unit_approval` and `_unit_named` take (on a scratch copy of 2026-11-26, `mypy --strict` reported seven errors without them and none with them); `joined` already holds only units that have one.

```python
    stage_ids = {
        (unit.directory, _slug(stage)): f"{_phase_of(stage)}/{unit.directory}/{_slug(stage)}"
        for unit in joined
        if unit.directory
        for stage in per_unit
    }
    lanes = {unit.directory: frozenset(_slug(stage) for stage in per_unit) for unit in joined if unit.directory}
    floors = {directory: _generation(gates, directory) for directory in lanes}
```

Starting code keys `stage_ids`, `lanes` and `floors` by directory, because answer 14 says the directory replaces the id-rule name, so a row with the id-rule spelling joins nothing (P-E1a is dropped). Spike F's five runs of P-E1 and P-E2 ran the translation prototype, not this code, so Step 4 is its first run of the new tests. A scratch copy has type-checked these statements (`mypy --strict` clean) and run the old `test_plan.py` against them: 27 of its 278 tests fail, all of them gate rows and tables of units, which Step 1's grep and Step 5 must reach.

- [ ] **Step 1:** From `packages/earnest/`, run `grep -rn 'Unit' src/earnest/plan.py tests/ --include='*.py' --include='*.md' --include='*.feature'`. List in this task every hit that reads or writes a gate row's `Unit`; skip `Unit Progress`, `Unit Ownership` and unit-table ids. Correct the Files list if it misses one.
- [ ] **Step 2:** Write the failing tests in `test_plan.py`:
  - `test_gate_row_joins_unit_by_directory`: a per-stage row with `Unit: u1-limiter` approves `construction/u1-limiter/functional-design`.
  - `test_gate_row_with_the_id_rule_name_approves_nothing`: the same row with `Unit: u1` approves nothing.
  - `test_attempt_generation_counts_by_directory`: a generation-1 row with `Unit: u1-limiter` approves `u1-limiter`'s stage, and once a row with `Unit: u1-limiter` and `Attempt Generation: 2` follows, that approval no longer counts. The first half fails before Step 4.
  - `test_rejection_voids_by_directory`: a `GATE_REJECTED` row with `Unit: u2-notice` voids only `u2-notice`'s stage.
- [ ] **Step 3:** Run `rtk proxy uv run pytest tests/unit/test_plan.py -k "directory or id_rule"; echo $?`. Expected: the four tests fail, and a non-zero code.
- [ ] **Step 4:** Change the three statements of `_expand` as Starting code gives them, then run Step 3's command again: expect every Step 2 test to pass, the id-rule test included, since Starting code already joins by unit directory. Then rename `name` to `directory` in the parameters and locals of `_gate_keys`, `_generation` and `_voids`. Make their docstrings, and those of `_unit_approval` and `_unit_named`, say unit directory where they say unit name (for example `_gate_keys`, line 667). `Unit.name`'s docstring (line 343) drops the gate row's `Unit`, and the `directory` field gets the comment `# the unit table's directory, which a gate row's Unit carries`. No logic changes beyond `_expand`.

- [ ] **Step 5:** Change every row Step 1 listed:
  - in the fixture shard, line 30's `**Unit**: u1` becomes `**Unit**: u1-limiter`;
  - in `test_plan.py`, `test_task_change.py`, `test_unit_status.py`, `unit_status.feature` and line 215 of `test_seeded_change.py`, the edits the Files list names;
  - in `FUTURE-FORMAT.md`, the sentence that describes the value now reads "the unit's construction directory, upstream's unit name (`core/knowledge/aidlc-shared/verification.md:23` of the fork)";
  - update `UNITS_SHA` in `test_seeded_change.py` to the new short sha of the units variant, and grep `tests/` and `04` for `4cdc2f5` to find any other copy. The comment on that line says why the sha moved. Every other pinned sha stays as it is.
- [ ] **Step 6:** Run `rtk proxy uv run pytest tests/unit/test_plan.py tests/steps/test_unit_status.py tests/steps/test_evidence_check.py tests/integration/test_seeded_change.py tests/integration/test_task_change.py; echo $?`, `rtk proxy uv run mypy --strict src/; echo $?` and the regression run. Expected: `0` from each, all pass, at Task 1's count plus 4.
- [ ] **Step 7:** Commit `fix: a gate row's Unit names the unit's construction directory, as upstream writes it`.

### Task 3: The `aidlc_fork` behavior gate, red

**Files:**

- Create:
  - everything under `packages/earnest/tests/fixtures/seeded-change/fork/` and `packages/earnest/tests/fixtures/seeded-change/fork-units/`;
  - `packages/earnest/tests/features/aidlc_fork.feature`;
  - `packages/earnest/tests/steps/test_aidlc_fork.py`.
- Modify: `packages/earnest/tests/conftest.py`, `packages/earnest/tests/steps/test_unit_status.py`, `packages/earnest/pyproject.toml`, and this plan, where the task records its readings and counts.

**Interfaces:**

- Consumes:
  - from Task 1: `fork_checkout`, `compile_graph`, `run_fork`, `human_turn`, `gate_approvals` and `Fork`;
  - from `conftest.py`: `fixture_repo`, `units_repo`, `commit_on_main`, and the shared steps `the coding agent runs earnest plan` and `"{stage}" has the approval "{approval}"`;
  - from `tests/sarif.py`: `RECORD`.
- Produces: the `aidlc_fork` exit command, red until Task 5.

- [ ] **Step 1:** Write the solo overlay `fork/`:
  - `fork/aidlc/spaces/default/intents/260926-checkout/aidlc-state.md` is the base state file with three changes: `- [x] code-generation` becomes `- [-] code-generation`, `- [x] build-and-test` becomes `- [ ] build-and-test`, and `- **Review Override**: none` goes on the line after `- **Start Date**: 2026-09-26`.
  - `fork/aidlc/.aidlc-clone-id` holds the line `fixturecloneid01`.
- [ ] **Step 2:** Write the units overlay `fork-units/`:
  - `fork-units/aidlc/spaces/default/intents/260926-checkout/aidlc-state.md` is the units variant's state file with these changes: the `- **Unit Ownership**: team` line removed; `- **Review Override**: none` added on the line after `- **Start Date**: 2026-09-26`; `- [x] functional-design` becomes `- [-] functional-design` and `- [x] code-generation` becomes `- [ ] code-generation`, while the three `[S]` rows and `build-and-test` stay; and in Unit Progress, `| u2 | - | [x] | [-] | [ ] |` becomes `| u2 | - | [-] | [ ] | [ ] |`, which reopens `functional-design` for `u2-notice`. The `u1` row stays. The readings in the Fork facts were taken on the units variant before these edits, so Step 5 measures them again.
  - `fork-units/aidlc/.aidlc-clone-id` holds `fixturecloneid01`.
- [ ] **Step 3:** Add `"fork"` and `"fork-units"` to `_OVERLAYS` in `conftest.py`, in the same commit as the overlay files. Without that, the base copy takes them in, and the base commit's sha moves, which the sha pins in `test_seeded_change.py` catch.
- [ ] **Step 4:** Move `define_twice` (`test_unit_status.py:53-55`) into `conftest.py`, with its `REQUIREMENTS`, `read` and `write` imports, so that both features share it. `test_unit_status.py` drops the moved step and any import it no longer uses (ruff F401).
- [ ] **Step 5:** Check the readings on the built overlays with Earnest alone. In a scratch test, build each overlay with `commit_on_main(fixture_repo("seeded-change"), "seeded-change", "fork")` and `commit_on_main(units_repo(), "seeded-change", "fork-units")`, then run each command below as `rtk proxy <command>; echo $?`, since the exit code is the reading:
  - `earnest check --stage requirements-analysis`. Expected: exit 0 and 0 results. After `define_twice`: exit 1 and 1 result.
  - `earnest check --stage code-generation`. Expected: exit 0.
  - `earnest check --stage construction/u2-notice/functional-design` on `fork-units`. Expected: exit 0 and 0 results.

  If a count differs, stop. The Gherkin's counts change only through Task 0 and the maintainer.
- [ ] **Step 6:** Copy the M7 Gherkin of `04` into `aidlc_fork.feature`, verbatim. Add `addopts = ["--ignore=tests/steps/test_aidlc_fork.py"]` to `[tool.pytest.ini_options]` in `packages/earnest/pyproject.toml`, so a bare run leaves the module out; naming its path still runs it. If M9's Task 3 landed first, `addopts` exists as a list: append this entry to it (the merged form is in answer 15's "`make test` stays self-contained" bullet) rather than writing a second key.
- [ ] **Step 7:** Write `tests/steps/test_aidlc_fork.py`. Every step asserts on a fork call's exit code, and its message is the call's stderr:

```python
"""Steps of the aidlc_fork feature: the fork's earnest sensor and approve transition, driven from this repository."""

import json

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import commit_on_main
from tests.fork import Fork, compile_graph, fork_checkout, gate_approvals, human_turn, run_fork
from tests.sarif import RECORD, header, record


scenarios("aidlc_fork.feature")


@pytest.fixture(scope="session")
def fork(tmp_path_factory) -> Fork:
    root, bun = fork_checkout()
    return compile_graph(root, bun, tmp_path_factory.mktemp("fork-graph"))


@given("a local AI-DLC fork checkout with Bun")
def checkout(fork):
    assert fork.graph.is_file()


@given(parsers.parse("the repo maintainer's \"seeded-change\" repository with \"code-generation\" at its gate"),
       target_fixture="repo")
def solo_gate(fixture_repo):
    return commit_on_main(fixture_repo("seeded-change"), "seeded-change", "fork")


@given(parsers.parse("the repo maintainer's \"seeded-change\" units variant with the functional design of "
                     '"u2-notice" at its gate'), target_fixture="repo")
def units_gate(units_repo):
    return commit_on_main(units_repo(), "seeded-change", "fork-units")


@when(parsers.parse('AI-DLC fires the earnest sensor for "{slug}" on "{path}"'), target_fixture="sensor")
def fire(repo, fork, slug, path):
    return run_fork(repo, fork, "engine", "sensor-earnest", "--stage", slug, "--output-path", str(repo / RECORD / path))


@then(parsers.parse("the sensor prints pass {verdict} with findings count {count:d}"))
def sensor_prints(sensor, verdict, count):
    assert sensor.stdout.strip(), sensor.stderr  # a fork without the sensor prints nothing; show why
    out = json.loads(sensor.stdout)  # 01 lets the output carry more keys; the contract fixes these two
    assert (out["pass"], out["findings_count"]) == (verdict == "true", count), sensor.stderr


@then("the sensor exits zero")
def sensor_exits_zero(sensor):
    assert sensor.returncode == 0, sensor.stderr


@then(parsers.parse('the record holds a run header for "{stage}"'))
def per_unit_header(repo, stage):
    runs = record(repo)["runs"]
    assert f"{RECORD}/{stage}" in runs, sorted(runs)


def _state(repo, fork, verb, slug, unit, *tail):
    """Run one direct state transition of the fork for a stage, of one unit when `unit` is set."""
    done = run_fork(repo, fork, "engine", "state", verb, slug, *(("--unit", unit) if unit else ()), *tail, direct=True)
    assert done.returncode == 0, done.stderr


@when(parsers.parse('AI-DLC opens the gate of "{slug}"'))
def open_gate(repo, fork, slug):
    _state(repo, fork, "gate-start", slug, None)


@when(parsers.parse('AI-DLC opens the gate of unit "{unit}" for "{slug}"'))
def open_unit_gate(repo, fork, slug, unit):
    _state(repo, fork, "gate-start", slug, unit)


@when(parsers.parse("the repo maintainer approves \"{slug}\" at the fork's gate"))
def approve(repo, fork, slug):
    human_turn(repo)
    _state(repo, fork, "approve", slug, None, "--user-input", "Approve")


@when(parsers.parse("the repo maintainer approves for unit \"{unit}\" the stage \"{slug}\" at the fork's gate"))
def approve_unit(repo, fork, slug, unit):
    human_turn(repo)
    _state(repo, fork, "approve", slug, unit, "--user-input", "Approve")


def _approval(repo, slug, stage, by, unit=None):
    run = header(repo, stage)
    (row,) = [event for event in gate_approvals(repo) if event.fields.get("Stage") == slug]
    assert row.fields.get("Unit") == unit, row.fields
    assert row.fields["Assessment Hash"] == run["hash"], row.fields
    assert row.fields["Items"].split(", ") == run["items"], row.fields
    assert row.fields["Approved By"] == by, row.fields


@then(parsers.parse("the fork's audit holds one approval of \"{slug}\" with the hash and items of the run header "
                    'for "{stage}", approved by "{by}"'))
def approval_row(repo, slug, stage, by):
    _approval(repo, slug, stage, by)


@then(parsers.parse("the fork's audit holds one approval for unit \"{unit}\" of \"{slug}\" with the hash and items "
                    'of the run header for "{stage}", approved by "{by}"'))
def unit_approval_row(repo, slug, unit, stage, by):
    _approval(repo, slug, stage, by, unit)
```

  The `Items` comparison relies on the run header's `items` being sorted (`plan.header`, `plan.py:1362-1378`) and on the fork writing them in that order, joined by `", "`, as the fixture rows are. If the fork's plan settles a different order, compare sorted lists, and record that in Task 0 Step 4.

- [ ] **Step 8:** With `EARNEST_AIDLC_FORK` pointing at a checkout that has no delta (the maintainer's `earnest/m7-base`), run `rtk proxy uv run pytest tests/steps/test_aidlc_fork.py; echo $?`. Expected: a non-zero code; all 5 scenarios fail on `engine sensor-earnest` or on the missing fields, and none is skipped. Then run it once with `EARNEST_AIDLC_FORK` unset. Expected: a non-zero code, and all 5 failed, each with the message naming `EARNEST_AIDLC_FORK`. pytest-bdd resolves the `fork` fixture inside each scenario's call, so none is an error or a skip. The regression run, which `addopts` now keeps this module out of, is green at Task 2's count.
- [ ] **Step 9:** Commit `test: RED aidlc_fork behavior gate`.

### Task 4: Make and CI

**Files:** Modify `packages/earnest/Makefile`, `Makefile`, `.github/workflows/ci.yml`, `CLAUDE.md`, and this plan, where the task records its counts.

- [ ] **Step 1:** Change the two Makefiles. In each recipe line below, the leading space stands for a tab; the Markdown linter rewrites tabs in this plan, but make needs them.

  - In `packages/earnest/Makefile`, add `test-aidlc-fork` to `.PHONY`. Add this target after `test`:

```make
test-aidlc-fork: install
 uv run pytest tests/steps/test_aidlc_fork.py
```

- In the root `Makefile`, add `test-aidlc-fork` to `.PHONY`, and add this target after `package`, delegating as `package` does:

```make
test-aidlc-fork:
 $(MAKE) -C packages/earnest test-aidlc-fork
```

- [ ] **Step 2:** Add a job to `ci.yml` after `test-python`. It follows the existing jobs' style, including their tag pins (`actions/checkout@v4`, `astral-sh/setup-uv@v5`), and pins `oven-sh/setup-bun` by the sha the fork's CI uses (answer 15):

```yaml
  test-aidlc-fork:
    needs: lint-python
    runs-on: ubuntu-latest
    env:
      AIDLC_FORK_REPO: nullrul/aidlc-workflows  # answer 4, option A: the GitHub fork is kept
      AIDLC_FORK_REF: 0000000000000000000000000000000000000000  # Task 5 sets the fork sha that holds the delta
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false  # the fork's code and lifecycle scripts run in this job
      - uses: actions/checkout@v4
        with:
          repository: ${{ env.AIDLC_FORK_REPO }}
          ref: ${{ env.AIDLC_FORK_REF }}
          path: aidlc-fork
          persist-credentials: false
      - uses: oven-sh/setup-bun@0c5077e51419868618aeaa5fe8019c62421857d6  # v2.2.0, the sha the fork's CI pins
        with:
          bun-version: '1.4.2'  # the fork's CI pins this version
      - uses: astral-sh/setup-uv@v5
      - run: make -C packages/earnest install test-aidlc-fork
        env:
          EARNEST_AIDLC_FORK: ${{ github.workspace }}/aidlc-fork
```

  Until Task 5, the all-zero `AIDLC_FORK_REF` makes the checkout fail. The job therefore stays red until the delta exists, and it cannot pass by accident.

- [ ] **Step 3:** In `CLAUDE.md`'s Build section, add one line: `make test-aidlc-fork` runs the M7 gate. It needs `EARNEST_AIDLC_FORK` set to a fork checkout and `bun` on `PATH`, and it fails, never skips, without them.
- [ ] **Step 4:** Run `rtk proxy make test; echo $?` from the repository root. Expected: `0`, with the module not collected. Run `LINT_FILE=.github/workflows/ci.yml make lint-file` and check its exit code with `rtk proxy`.
- [ ] **Step 5:** Commit `ci: aidlc_fork gate job against a pinned fork checkout`.

### Task 5: Pin the fork, and turn the gate green

Start this task only after the fork's plan has synced the fork's `main` with `awslabs/aidlc-workflows` main (answer 4, option A) and merged the delta on the fork's `main`.

**Files:** Modify `.github/workflows/ci.yml` (`AIDLC_FORK_REPO`, `AIDLC_FORK_REF`), and this plan, where the task records the pinned sha and its counts.

- [ ] **Step 1:** Set `AIDLC_FORK_REF` to the full sha of the fork's `main` that holds the delta, and `AIDLC_FORK_REPO` to `nullrul/aidlc-workflows` (answer 4). In the local checkout, run `git -C "$EARNEST_AIDLC_FORK" fetch` and `git -C "$EARNEST_AIDLC_FORK" switch --detach <sha>`. This is the one change this plan makes in the fork checkout, and the maintainer approves it at this step.
- [ ] **Step 2:** In `packages/earnest/`, run `rtk proxy uv run pytest tests/steps/test_aidlc_fork.py; echo $?`. Expected: `0`, with 5 passed.
- [ ] **Step 3:** Check that the hash holds through approve (Review Focus). In the third scenario's built repository, the `Assessment Hash` of the `STAGE_AWAITING_APPROVAL` row, of the `GATE_APPROVED` row, and of the final run header are equal. If they differ, stop. The hash takes in a path that gate-start writes, and that is a fault in the delta or in `01` for the maintainer, not something to fix in the test.
- [ ] **Step 4:** Commit `ci: pin the aidlc_fork gate to fork <short sha>`, and push the branch only under Task 6's review.

### Task 6: The full suite, lint, the clean checkout, and the pre-PR review

**Files:** none. This task only runs the checks.

- [ ] **Step 1:** Run `git -C "$EARNEST_AIDLC_FORK" status --short --ignored` and save the output. Then run `rtk proxy make test-aidlc-fork; echo $?`. Expected: `0`, and a second `git status --short --ignored` identical to the first.
- [ ] **Step 2:** From the repository root, run `rtk proxy make test; echo $?` and `rtk proxy make lint; echo $?`. Expected: both print `0`.
- [ ] **Step 3:** Run the `/pre-pr-review` skill on HEAD, and report its verdict. Push only under the maintainer's standing rule: three reviewers, every finding fixed, three fresh checkers PASS on the final sha. The PR waits for the CI job `test-aidlc-fork` to be green at the pinned sha.
