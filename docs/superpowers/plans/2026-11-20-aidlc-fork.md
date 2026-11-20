# M7 `aidlc_fork` Implementation Plan

Status: PROPOSED, 2026-11-20. Every gating answer below is waiting on the maintainer. No task starts until Task 0 Step 1 records the decisions. This repository alone cannot turn the exit command green. It needs the Fork delta of `02`, built under the fork's own plan, merged in the fork's repository at the commit that Task 5 pins. The plan was written on `main` and is not committed; Task 0 commits it on the M7 branch.

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
  - the change, if gating answer 14 is approved, that joins `Unit` by unit directory in `plan.py`.
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

The fork checkout is `/Users/rc/Projects/workspace/aidlc-workflows`. Its branch `earnest/m7-base` is the same commit as `origin/main`, `f2acb53d`. No Earnest delta is applied: `git log main..HEAD` is empty. Paths below are relative to the fork. The feasibility runs used copies of the built fixtures in the session scratchpad. The fork's `git status --short` was the same before and after.

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
| F12 | Upstream tests pin what the delta changes: `t86-sensor-manifest-schema` (the six sensor ids and `GATE_SENSORS`), `t230-dispatcher-routes` (each manifest's help line, `TOOLS` targets), `t349-gate-sensor-reachability` (each gate glob accepts a deliverable), `t281-sensor-traceability` (a stage that emits `traceability.json` declares the sensor), `t48-audit-event-emitters` (the event set, not fields), `t28-audit-event-sync` and `t261-audit-authority-floor`. Tests run with `bun tests/run-tests.ts`. | `tests/unit/`, `tests/integration/`; `tests/README.md:3-9` |
| F13 | At HEAD, eight files under `core/tools/` read `source-manifest.json`: the seven that `02` names, plus `aidlc-lib.ts`. | `core/tools/aidlc-lib.ts:19275`, `:26538-26580` |
| F14 | The sibling sensor runs on its own against the built `seeded-change`, with no `node_modules` and no stage graph: `bun <fork>/core/tools/aidlc.ts engine sensor-traceability --stage <slug> --output-path <abs>`. It exits 0 and prints one JSON line. | feasibility run |
| F15 | Solo approve accepts the hand-written fixture intent, with no `intents.json`, engine state or `SENSOR_*` rows, once five conditions hold. (1) It is given a stage graph through `AIDLC_STAGE_GRAPH`, compiled by the fork's `compileStageGraph()`. This is needed because `bun scripts/package.ts` fails on Bun 1.3.8, and the fork's CI pins 1.4.2. (2) `AIDLC_ALLOW_DIRECT_STATE_TRANSITIONS=1` is set. (3) The stage row is at `[-]` and `engine state gate-start <slug>` runs. (4) The state file holds `- **Review Override**: none`. (5) A `HUMAN_TURN` row (`Timestamp` and `Event` only) follows gate-start. The approval lands in `audit/<hostname>-<clone id>.md`, and `aidlc/.aidlc-clone-id` pins the clone id. These runs used a scratch clone that had `bun install --frozen-lockfile`. | `core/tools/aidlc-graph.ts:2513`; `core/tools/aidlc-state.ts:867`, `:5892-5905`; `core/tools/aidlc-lib.ts:38409-38421`; `.github/workflows/ci.yml:59` |
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

## Gating open questions

The M7 entry of `03` names thirteen gating rows: three from `01`, seven from `02` and three from M2b. The Fork facts raise rows 14 to 17. Every answer is **PROPOSED** until the maintainer decides. A row marked *(fork plan)* is decided here and carried out in the fork's repository. No row is dropped.

### 1. A run header with `dirty` true (`01`)

Row as asked: "Whether the gate or the approve transition refuses a run header with `dirty` true", resolved before `aidlc_fork`.

**PROPOSED:** neither refuses. The gate shows `dirty` beside the hash, and approve records the hash as it stands.

- Source: `01`, Assessment hash, says "A work tree with uncommitted changes gets the hash of the bytes it holds". The hash binds the bytes the human read, whether or not they are committed.
- Why: AI-DLC writes a stage's artifacts before anything commits them. Refusing `dirty` would hold almost every gate until someone commits.
- Trade-off: an approval may bind bytes that never reach a commit. Earnest still marks it stale once its items change, because an approval is current by its `Items` (`01`, Frontier and position).

### 2. Where the gate reads the run header (`01`, *fork plan*)

Row as asked: "Which Fork-delta path holds the gate presentation that reads `status` and `hash` from the run header, and the path `.earnest/assessment.json` that the approve transition reads".

**PROPOSED:** both live in `core/tools/aidlc-state.ts`, through one reader of `runs["<record dir>/<stage>"]` in `<project dir>/.earnest/assessment.json`.

- gate-start adds `Assessment Hash`, `Stage Status` and `Dirty` to its `STAGE_AWAITING_APPROVAL` row. That row already carries `Sensor State` (`core/knowledge/aidlc-shared/audit-format.md:73`).
- `handleApprove` reads the same header.
- No new file is needed. The fork's plan confirms how the review brief (`core/tools/aidlc-review-brief.ts`) shows the new fields.
- Source: `02`, Fork delta, the `aidlc-state.ts` bullet.

### 3. An artifact that changes during a sensor run, and the check at approve (`01`, *fork plan*)

Row as asked: "Which Fork-delta path holds the hold on an artifact that changes during a sensor run, and the check in `approve` that artifacts are unchanged since the sensor ran".

**PROPOSED:**

- **The hold during the run needs no delta path.** Upstream's `fireGateSensors` already holds the gate of a blocking gate sensor when an artifact changes before dispatch or during evaluation (F4). The `earnest` manifest is `fire_on: gate` and `default_severity: blocking`, so it inherits that hold.
- **The check at approve goes in `handleApprove`, in `aidlc-state.ts`.** When the gate's `STAGE_AWAITING_APPROVAL` row carries an `Assessment Hash`, approve runs the `earnest` sensor's check for the stage again. It approves only when the new run header's `hash` equals that `Assessment Hash`. Otherwise it exits non-zero, writes no `GATE_APPROVED`, and names the stage whose gate must be reopened.
- This makes the row's `Assessment Hash` "the hash of the assessment the gate showed" (`01`, the approval entry of the vocabulary table, line 722).
- Trade-off: each approve costs one `earnest check --stage` run. The alternative is to persist upstream's in-memory fingerprints (`GateSensorEvaluation.fingerprints`, `aidlc-state.ts:3566`) so approve can compare them. That would be a larger change to upstream's state.

### 4. The fork repository's name and owner (`02`)

Row as asked: "The fork repository's name and owner; this repository is `nullrul/earnest`", resolved by "creating the fork".

**PROPOSED, for the maintainer to choose:**

- **A. Keep `nullrul/aidlc-workflows` (F1) and revise L3.**
  - Every clone sets `git remote set-url --push upstream no-push` and `gh repo set-default nullrul/aidlc-workflows`.
  - The repository stays public, because a fork of a public repository stays public.
  - `gh pr create` from a fresh clone targets `awslabs` until `set-default` runs.
- **B. Keep L3.** Mirror-push into a new standalone public repository, with the fetch-only `upstream` remote. The maintainer picks the name. `nullrul/aidlc-workflows` is taken by the network fork unless that fork is renamed or deleted.

Recommendation: B.

- L3's reason, that there is no pull-request path to upstream, still holds.
- The network fork has no Earnest work yet (`main..earnest/m7-base` is empty), so switching costs one mirror push.
- A public repository lets CI check it out with no credential. If the repository were private, CI would need a GitHub App token, never a personal access token.

Whichever is chosen, nothing in this plan pushes to the fork clone or opens a pull request from it.

### 5. How the sensor script finds `earnest` (`02`)

Row as asked: "How the fork's sensor script finds the `earnest` command: an installed tool on the path, or a pinned invocation".

**PROPOSED:** from `PATH`, as the command `earnest`.

- **When `earnest` cannot be started**, the script prints `{"pass": false, "findings_count": 0}` and exits 0. A missing engine then holds the blocking gate the way a failing check does (`01`: "a check that fails to run holds the gate like a failing one"; F5).
- **Install:** until there is a `publish` stage (`02`, Future directions), the maintainer installs `earnest` with `uv tool install --editable packages/earnest` from this repository.
- **In the gate:** every fork call puts the package's own venv `bin/` first on `PATH`.
- **Trade-off:** a pinned invocation, such as `uv run --project <path> earnest`, would bind a version, but it would put this repository's path into the fork.

### 6. Readers of `source-manifest.json` (`02`)

Row as asked: keep writing `source-manifest.json` "as AI-DLC input that Earnest never counts as evidence, or extend the Fork delta to those tools?"

**PROPOSED:** keep it as AI-DLC input that Earnest never counts as evidence.

- The delta leaves all eight readers (F13) unchanged.
- In `01`'s mapping table, its row changes from "replaced" to "kept, carries no weight as evidence (T2)".
- Source: L3 says "the delta keeps to what `01` changes".
- Trade-off: a unit's files are listed in two places, and only Earnest's out-of-task check counts.

### 7. Upstream artifacts the mapping table leaves unnamed (`02`)

Row as asked: NFR Requirements' `scalability-requirements`, `reliability-requirements` and `tech-stack-decisions`; NFR Design's `scalability-design`, `reliability-design` and `logical-components`; and Build and Test's agent-written `cross-unit-traceability.md`.

**PROPOSED:** all seven stay as AI-DLC writes them: prose with no items and no weight as evidence (T2).

- Each gains a "kept" row in `01`'s mapping table.
- Their stages still list `earnest`, because those stages' other artifacts carry items.
- Trade-off: scalability and reliability stay outside the trace until a later revision adapts them.

### 8. User Stories requirement ids (`02`, *fork plan*)

Row as asked: "Keep the AI-DLC id in each item's prose, or move User Stories to `earnest`?"

**PROPOSED:** keep the AI-DLC id in each `req` item's prose.

- The adapted `requirements.md` template writes `FR1.2` in the item's text, beside the name `req~fr1-2~1`.
- The kept `traceability` sensor's pattern, `FR\d+(?:\.\d+)?`, then still finds it.
- User Stories stays kept.
- Trade-off: the id appears twice.

### 9. The sensors-off switches (`02`)

Row as asked: "Whether the fork holds the `earnest` sensor on through the per-intent `/aidlc --sensors off` and the `AIDLC_DISABLE_SENSORS=1` kill switch".

**PROPOSED:** honour both switches. The delta adds no exemption for one sensor (F11).

- With sensors off, the gate fires no check and its `STAGE_AWAITING_APPROVAL` row carries no `Assessment Hash`.
- Approve then skips answer 3's second check and writes `Approved By` alone.
- Earnest counts that approval and never marks it stale. `04` pins this in the M2 scenario "An approval row without the fork's fields counts and never goes stale (SC8)".
- Why: both switches are explicit acts by the user. The delta already turns `express` on (`02`).
- Trade-off: the approvals of an intent with sensors switched off bind no assessment.

### 10. Upstream tests that pin sensor ids and routes (`02`, *fork plan*)

Row as asked: "Which upstream tests pin the bundled sensor ids, the dispatcher routes or a stage's `sensors:` list", resolved by "the first run of upstream's suite on the fork".

**PROPOSED:**

- The tests are the ones listed in F12. The fork's plan updates each one in the same commit as the change it pins.
- The fork's first run of `bun tests/run-tests.ts --all` with the delta confirms the list, as the row's "Resolved by" says.
- `t281` passes only while every stage that still produces `traceability.json` declares the `traceability` sensor. So the delta must drop the `traceability.json` output in the same change that drops the sensor, as `01` replaces it.

### 11. Authority to create and push the fork repository (M2b)

**PROPOSED:**

- The maintainer creates the repository, or keeps the existing one (answer 4), and pushes the delta under the fork's plan.
- Agents push only feature branches of the fork, after its pre-PR review, under the maintainer's standing rule. They never push to `upstream`.
- This plan pushes nothing to the fork.

### 12. A fork checkout with Bun (M2b)

**PROPOSED:**

- **Finding the checkout.** The gate reads it from `EARNEST_AIDLC_FORK`: an absolute path that holds `core/tools/aidlc.ts`. It reads `bun` from `PATH`. If either is missing, the gate fails with a message that names it (Task 1).
- **Locally.** The maintainer's checkout is `/Users/rc/Projects/workspace/aidlc-workflows`. Its Bun, 1.3.8, should be upgraded to the fork CI's 1.4.2 with `bun upgrade`. In the checkout, `bun install --frozen-lockfile` must run once. F14 ran without `node_modules`, but the approve runs of F15 had them.
- **How the gate runs the fork.** It runs from source, as `bun <fork>/core/tools/aidlc.ts …`. The stage graph is compiled into pytest's temporary directory by the fork's own `compileStageGraph()` and passed as `AIDLC_STAGE_GRAPH` (F15). The gate does not package the fork, and writes nothing in the checkout.
- **In CI:** see answer 15.

### 13. The per-unit fork work (`01`)

Row as asked: "how a `unit-end` gate checks each stage its `Gate Stages` lists while those stages read ahead of the unit's frontier; where upstream raises `Attempt Generation`; whether `STAGE_SKIPPED` or `STAGE_JUMPED` rows carry `Unit`".

**PROPOSED:**

- **`Attempt Generation`.** Upstream raises it when a unit is claimed and when it is released, in `aidlc-unit.ts` (F10). The team gate already writes it (F7), and the delta leaves it as it is.
- **`STAGE_SKIPPED` and `STAGE_JUMPED`.** Neither carries `Unit` (F10). `01`'s rule already expects that: "restarts and jumps void rows by slug for every unit". Earnest does not read `UNIT_SKIPPED` in v1.
- **`unit-end`, for the maintainer to choose:**
  - **(a) Root fix, in Earnest.** A `--stage` run reports at position current every stage that the same open `unit-end` gate lists, so each listed stage's errors fail the check. This changes `01`, lines 703-705, and needs a new Earnest task with its own scenario.
  - **(c) v1.** At a `unit-end` gate, the fork fires the `earnest` sensor once for each stage that `Gate Stages` lists, each as `<phase>/<unit directory>/<slug>`, and holds the gate if any of them fails. A listed stage that lies ahead of the unit's frontier then reports its errors as notes. This plan records that as a known limit, and adds a row to `01`'s Open questions to be settled before the first team-mode intent runs through Earnest.
- **Recommendation: (c) for M7.** Neither option can be reached from this gate, because the team path stops at a `UNIT_COMPLETED` receipt (F16). Option (a) is Earnest work that deserves its own scenario.

### 14. The value of `Unit` (new, from F8)

**PROPOSED:** Earnest joins a gate row's `Unit` to the unit whose construction directory it names, which is upstream's unit name. That replaces the id-rule name. The fork writes upstream's unit name at every emit site, including the new `Unit` on the solo path.

This changes, in this repository:

- `01`, lines 130-133, 167-169 and 671;
- `_gate_keys` and every other read of `Unit` in `plan.py`;
- the `Unit` rows of the `units/` overlay, and `units/FUTURE-FORMAT.md`;
- the `Unit` rows written by hand in the step modules (Task 2).

The alternative is for the fork to map upstream's name to the id-rule name at its emit sites. That changes a value upstream's own code already joins into paths (`aidlc-state.ts:6380`) and reads (`gateStagesFromBlock`, `aidlc-lib.ts:36460`).

### 15. The fork commit the gate pins, and CI (new, from F2 and F18)

**PROPOSED:**

- **The delta's base.** The delta is applied to the fork's `main` as it stands when the fork's plan starts, `f2acb53d` or later, not to `fe563195d827`. Task 0 updates two things in `02`'s Fork delta:
  - its base commit;
  - its tree: `tests/.coverage-registry.json` is replaced by `// covers:` headers on the two new tests (F2).
- **`make test` stays self-contained.** It passes `--ignore=tests/steps/test_aidlc_fork.py`, which keeps Bun and TypeScript out of the package's tests, as L5 of `02` does. A new target, `make test-aidlc-fork`, runs the exit command. The module itself never skips.
- **A new CI job, `test-aidlc-fork`,** does these steps:
  - checks out the fork at `AIDLC_FORK_REF`, a full sha on the fork's `main` that holds the delta;
  - installs Bun 1.4.2 with `oven-sh/setup-bun`, pinned by sha as the fork's own CI pins it;
  - runs `bun install --frozen-lockfile` in the checkout;
  - runs `make test-aidlc-fork` with `EARNEST_AIDLC_FORK` set.
- **Merge order:**
  1. The fork's plan merges the delta on the fork's `main`, at sha X.
  2. This repository's M7 branch sets `AIDLC_FORK_REF` to X.
  3. The branch merges once the job is green. Until step 1, the exit command stays red and the branch stays unmerged.

### 16. How the gate drives approve (new, from F15 and F16)

**PROPOSED:**

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

### 17. Where the solo path gets its unit (new, from F16)

`02` and `01` (line 169) have the delta write `Unit` on the solo approve path. On the units variant with solo ownership, though, upstream's solo approve covers the stage's single row, such as `functional-design — EXECUTE: per unit`, and knows no unit (F16). Upstream can also approve several per-unit stages at one solo gate (`Approves Together`, `audit-format.md:73`).

**PROPOSED, for the maintainer to choose:**

- **A. `--unit <unit name>`.** The delta adds this argument to gate-start and approve on the solo path. A solo gate for a per-unit stage then speaks for one unit, and writes one `GATE_APPROVED` with that `Unit`. When upstream approves per-unit stages together, the delta writes one `GATE_APPROVED` per unit stage, each with its own `Unit`, `Assessment Hash` and `Items`. That keeps `01`'s rule that one row speaks for one unit's stage.
- **B. No `Unit` on the solo path.** Per-unit approvals come only from team gates, and on a solo intent Earnest approves no per-unit stage, as `01` (lines 684-685) says holds before M7. Scenario 5 is dropped, and clause (d)'s "approve writes `Unit`" is met only by the fork's tests of the team gate.

Recommendation: A. Without it, a solo intent on a units route never reaches done in Earnest. Scenario 5 and the Interface contract assume A.

## Interface contract with the fork

This is what the gate calls. `<fork>` is `$EARNEST_AIDLC_FORK`. Every call runs with these settings:

- the working directory is the built fixture repository;
- the environment holds only:
  - `HOME`;
  - `PATH`, set to `<venv bin>:<bun dir>:/usr/bin:/bin`;
  - the `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`, `XDG_CONFIG_HOME` and `GIT_ATTR_NOSYSTEM` values that `_isolated_git` in `tests/conftest.py` sets;
  - `AIDLC_PROJECT_DIR=<repo>`;
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
- **The fork is read-only.** No task edits, commits, stashes or pushes a fork file, or switches the fork's branch. No `gh` command runs from the fork clone, which defaults to `awslabs` (F1).
- **The gate leaves the checkout clean.**
  - The graph and the fixture copies live in pytest's temporary directories, not in the checkout.
  - `git -C "$EARNEST_AIDLC_FORK" status --short` is identical before and after a gate run (Task 6).
  - The gate never runs `bun install`. That is a precondition (answer 12).
- **Fail, never skip.** A missing `EARNEST_AIDLC_FORK`, a path without `core/tools/aidlc.ts`, or no `bun` on `PATH` each call `pytest.fail` with a one-line message that names the cause. Neither the module nor its helper uses `pytest.skip`, `skipif` or `importorskip`.
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
- **The per-unit stage is named in full.** The per-unit sensor scenario asserts that the record holds a run header keyed `<record dir>/construction/u2-notice/functional-design`, and none keyed `<record dir>/functional-design`. A bare slug on the units variant makes `earnest check` exit 2, so a sensor that passed one would print `pass: false`.
- **Earnest reads the fork's row.** After each approve, `earnest plan` shows the stage's approval as `current, human`. This end-to-end check proves that the field names and the `Unit` join agree.
- **The second check at approve keeps the hash.** Before approve, gate-start rewrites `aidlc-state.md` and adds `<record dir>/.aidlc-engine/` and the shard. Answer 3's equality holds only if the hash leaves those paths out. `01` keeps the route and the approvals outside the hash. Task 5 Step 3 checks this on the real delta.
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
| 2 | `Unit` joined by unit directory in `plan.py`, with its fixture rows and steps (answer 14) | T0 | none new; M2b and M5 stay green |
| 3 | The gate overlays, the feature and the step module, red | T1, T2 | none |
| 4 | Make and CI: `make test` ignores the module; `make test-aidlc-fork`; the `test-aidlc-fork` job | T3 | none; `make test` stays green |
| 5 | Pin the fork commit that holds the delta, and run the exit command | T4, and the delta merged in the fork | all 5 |
| 6 | The full suite, lint, the clean-checkout check, and the pre-PR review | T5 | all 5, with M1 to M6 unchanged |

**Regression expectations:**

- For Tasks 1 to 4, the regression run is `uv run pytest --ignore=tests/steps/test_aidlc_fork.py` in `packages/earnest/`. It stays green at the count the M7 branch records at the start of Task 1, plus the tests each task adds.
- Every task records its exact count.

## File Structure

| Path | Responsibility | Task |
| --- | --- | --- |
| `docs/superpowers/plans/2026-11-20-aidlc-fork.md` | this plan | 0 |
| `docs/design/01-logic-design.md`, `02-structural-design.md`, `03-implementation-plan.md`, `04-bdd-test-plan.md` | the decisions, the resolved rows, `04`'s M7 section, the link | 0 |
| `packages/earnest/tests/fork.py` | `Fork`, `fork_checkout`, `compile_graph`, `run_fork`, `fork_shard`, `human_turn`, `gate_approvals` | 1 |
| `packages/earnest/tests/unit/test_fork.py` | fail-not-skip and scrubbed-environment tests | 1 |
| `packages/earnest/src/earnest/plan.py` | `Unit` joined by unit directory through one helper | 2 |
| `packages/earnest/tests/unit/test_plan.py` | the join tests | 2 |
| `packages/earnest/tests/fixtures/seeded-change/units/` (`aidlc/**/audit/*.md`, `FUTURE-FORMAT.md`) and `evidence-units/`, wherever a row writes `Unit` | `Unit: u1-limiter` in place of `Unit: u1` | 2 |
| `packages/earnest/tests/steps/test_unit_status.py`, and any step module that writes a `Unit` row | rows written by hand use the directory | 2 |
| `packages/earnest/tests/fixtures/seeded-change/fork/` | the solo gate overlay: the intent's `aidlc-state.md`, with `code-generation` at `[-]`, `build-and-test` at `[ ]` and `- **Review Override**: none`, plus `aidlc/.aidlc-clone-id` | 3 |
| `packages/earnest/tests/fixtures/seeded-change/fork-units/` | the units gate overlay: the units variant's `aidlc-state.md` without `Unit Ownership: team`, with `- **Review Override**: none` and the `functional-design` row reopened for `u2-notice`, plus `aidlc/.aidlc-clone-id` | 3 |
| `packages/earnest/tests/conftest.py` | `fork` and `fork-units` added to `_OVERLAYS`; `define_twice` moved here from `test_unit_status.py` | 3 |
| `packages/earnest/tests/features/aidlc_fork.feature` | M7's 5 scenarios, copied verbatim from `04` | 3 |
| `packages/earnest/tests/steps/test_aidlc_fork.py` | the steps; the exit command | 3 |
| `packages/earnest/Makefile`, `Makefile` | `--ignore` in `test`; the `test-aidlc-fork` target | 4 |
| `.github/workflows/ci.yml` | the `test-aidlc-fork` job | 4, 5 |
| `CLAUDE.md` | the Build section names `make test-aidlc-fork` and `EARNEST_AIDLC_FORK` | 4 |

Outside the package, only Task 0's docs, the Makefiles, `ci.yml` and `CLAUDE.md` change. No fork path appears in this table.

## Known limits

- **Source, not packaged.** The gate runs the fork from source with a compiled graph. The fork's own tests run the packaged tree (F15).
- **Direct transitions.** The gate drives approve through the direct transitions, with `AIDLC_ALLOW_DIRECT_STATE_TRANSITIONS=1`, a `HUMAN_TURN` row written by hand, and the reviewer gate turned off by `Review Override: none`. The orchestrated path and the session binding stay with the fork's tests.
- **Paths this gate does not drive** (F16): the team per-unit gates, `unit-end`, `unit-merge` and `Approved By: automatic`. The fork's `t-gate-approved-assessment.test.ts` covers their emit sites.
- **`unit-end` safety** depends on answer 13. Under option (c), a stage listed ahead of the unit's frontier reports its errors as notes.
- **Pins.**
  - Only CI pins `AIDLC_FORK_REF` and Bun 1.4.2. A local run uses whatever commit and Bun the maintainer has.
  - The per-unit approve scenario rests on answer 17's option A, and on the `--unit` form of the Interface contract until the fork's plan confirms it (Task 0 Step 4).
- **The approve check costs a run.** Under answer 3, each approve runs `earnest check --stage` once more.

---

## Tasks

### Task 0: The docs commit

**Files:** Create `docs/superpowers/plans/2026-11-20-aidlc-fork.md`. Modify `docs/design/01-logic-design.md`, `docs/design/02-structural-design.md`, `docs/design/03-implementation-plan.md` and `docs/design/04-bdd-test-plan.md`.

- [ ] **Step 1:** For each of the seventeen answers, replace PROPOSED with the maintainer's decision and its date. If answer 4, 13, 14, 15 or 17 has no decision, stop: Tasks 2 to 5 are built on them.
- [ ] **Step 2:** Write the M7 section of `04`, after M6's. It holds:
  - the feature path;
  - the fixture: `seeded-change` with the `fork` overlay, its units variant with the `fork-units` overlay, and a local fork checkout;
  - SC9;
  - the readings;
  - the Gherkin below, marked PROPOSED.

  Replace the sentence "The scenarios of M7 and M8 are added here when each milestone's plan is written" so that it names M8 alone.
- [ ] **Step 3:** Resolve the thirteen rows in `01` and `02` with the decisions, and add rows 14 to 17 as resolved. Then make the edits the decisions call for:
  - `01`, lines 130-133, 167-169 and 671, for answer 14;
  - `01`'s mapping table, for answers 6 and 7;
  - in `02`'s Fork delta, the base commit and the tree (answer 15), and the approve check in the `aidlc-state.ts` bullet (answer 3);
  - if answer 13 is option (c), the new row in `01`'s Open questions;
  - a link to this plan from M7's entry in `03`.
- [ ] **Step 4:** Once the fork's plan exists, compare its interface with the Interface contract above. Record any difference in this plan before Task 3 starts: the `--unit` form, the sensor's JSON, and the shard name.
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
    And the record holds a run header for "construction/u2-notice/functional-design" and none for "functional-design"

  Scenario: Approving a per-unit stage records its unit with the assessment (SC9)
    Given the repo maintainer's "seeded-change" units variant with the functional design of "u2-notice" at its gate
    When AI-DLC opens the gate of unit "u2-notice" for "functional-design"
    And the repo maintainer approves for unit "u2-notice" the stage "functional-design" at the fork's gate
    And the coding agent runs earnest plan
    Then the fork's audit holds one approval for unit "u2-notice" of "functional-design" with the hash and items of the run header for "construction/u2-notice/functional-design", approved by "human"
    And "construction/u2-notice/functional-design" has the approval "current, human"
```

### Task 1: The fork helper

**Files:** Create `packages/earnest/tests/fork.py`. Test `packages/earnest/tests/unit/test_fork.py`.

**Interfaces:**

- Consumes:
  - `EARNEST` and `RECORD` from `tests/sarif.py`;
  - `parse_audit(text: str, shard: str) -> list[Event]` from `earnest.plan`, where `Event.fields` is a `dict[str, str]`.
- Produces, all in `tests/fork.py`:
  - `FORK_ENV = "EARNEST_AIDLC_FORK"`, `ENTRY = "core/tools/aidlc.ts"`, and `CLONE_ID = "fixturecloneid01"`;
  - `@dataclass(frozen=True) class Fork: root: Path; bun: Path; graph: Path`;
  - `def fork_checkout() -> tuple[Path, Path]`;
  - `def fork_env(bun: Path, **extra: str) -> dict[str, str]`;
  - `def compile_graph(root: Path, bun: Path, out: Path) -> Fork`;
  - `def run_fork(repo: Path, fork: Fork, *args: str, direct: bool = False) -> subprocess.CompletedProcess[str]`;
  - `def fork_shard(repo: Path) -> Path`;
  - `def human_turn(repo: Path) -> None`;
  - `def gate_approvals(repo: Path) -> list[Event]`.

- [ ] **Step 1:** Record the regression count: run `uv run pytest --ignore=tests/steps/test_aidlc_fork.py -q` in `packages/earnest/`, and write the passed count into this task.
- [ ] **Step 2:** Write the failing tests in `tests/unit/test_fork.py`:

```python
"""The aidlc_fork gate's helper fails, never skips, and runs the fork in a scrubbed environment."""

from pathlib import Path

import pytest

from tests.fork import ENTRY, FORK_ENV, fork_checkout, fork_env
from tests.sarif import EARNEST


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
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "bun").write_text("#!/bin/sh\n")
    (bin_dir / "bun").chmod(0o755)
    monkeypatch.setenv(FORK_ENV, str(_checkout(tmp_path / "fork")))
    monkeypatch.setenv("PATH", str(bin_dir))
    assert fork_checkout() == (tmp_path / "fork", bin_dir / "bun")


def test_the_gate_never_skips():
    tests = Path(__file__).resolve().parents[1]
    for path in (tests / "fork.py", tests / "steps" / "test_aidlc_fork.py"):
        if path.exists():
            assert not re.search(r"pytest\.skip|skipif|importorskip", path.read_text()), path


def test_environment_is_scrubbed(monkeypatch):
    monkeypatch.setenv("CLAUDE_SESSION_ID", "leak")
    env = fork_env(Path("/opt/bun/bin/bun"), AIDLC_PROJECT_DIR="/repo")
    assert set(env) == {
        "HOME", "PATH", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM", "XDG_CONFIG_HOME", "GIT_ATTR_NOSYSTEM",
        "AIDLC_PROJECT_DIR",
    }
    assert env["PATH"].split(":")[:2] == [str(EARNEST.parent), "/opt/bun/bin"]
```

  `test_the_gate_never_skips` looks for skip calls, not the word, because the helper's docstrings say "never skip". The test file also needs `import re` at the top.

- [ ] **Step 3:** Run `uv run pytest tests/unit/test_fork.py`. Expected: collection fails with `ModuleNotFoundError: tests.fork`.
- [ ] **Step 4:** Write `tests/fork.py`:

```python
"""Find the AI-DLC fork checkout and run its tools against a built fixture, for the aidlc_fork gate."""

import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from earnest.plan import Event, parse_audit
from tests.sarif import EARNEST, RECORD

FORK_ENV = "EARNEST_AIDLC_FORK"
ENTRY = "core/tools/aidlc.ts"
CLONE_ID = "fixturecloneid01"  # the overlays pin aidlc/.aidlc-clone-id, so the fork's shard name ends in it
_GIT = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "XDG_CONFIG_HOME": "/dev/null",
    "GIT_ATTR_NOSYSTEM": "1",
}
_COMPILE = """\
import { writeFileSync } from "node:fs";
const [fork, out] = process.argv.slice(2);
const { compileStageGraph } = await import(`${fork}/core/tools/aidlc-graph.ts`);
writeFileSync(out, compileStageGraph().json);
"""


@dataclass(frozen=True)
class Fork:
    """A fork checkout, the bun that runs it, and the stage graph compiled from it."""

    root: Path
    bun: Path
    graph: Path


def fork_checkout() -> tuple[Path, Path]:
    """Return the fork checkout and bun; fail the test, never skip it, when either is missing."""
    value = os.environ.get(FORK_ENV, "")
    if not value:
        pytest.fail(f"set {FORK_ENV} to the absolute path of a local AI-DLC fork checkout", pytrace=False)
    root = Path(value)
    if not root.is_absolute() or not (root / ENTRY).is_file():
        pytest.fail(f"{FORK_ENV}={value} is not an AI-DLC fork checkout: it has no {ENTRY}", pytrace=False)
    bun = shutil.which("bun")
    if bun is None:
        pytest.fail("bun is not on PATH, and the aidlc_fork gate runs the fork with Bun", pytrace=False)
    return root, Path(bun)


def fork_env(bun: Path, **extra: str) -> dict[str, str]:
    """Return the only environment a fork call sees: no session, host setting or Git configuration leaks in."""
    path = os.pathsep.join([str(EARNEST.parent), str(bun.parent), "/usr/bin", "/bin"])
    return {"HOME": os.environ["HOME"], "PATH": path, **_GIT, **extra}


def compile_graph(root: Path, bun: Path, out: Path) -> Fork:
    """Compile the fork's stage graph with the fork's own compileStageGraph into out, and return the Fork."""
    script, graph = out / "compile-graph.ts", out / "stage-graph.json"
    script.write_text(_COMPILE)
    done = subprocess.run(
        [str(bun), str(script), str(root), str(graph)],
        cwd=out, env=fork_env(bun), capture_output=True, text=True, check=False,
    )
    if done.returncode != 0 or not graph.is_file():
        pytest.fail(f"the fork's stage graph did not compile: {done.stderr.strip()}", pytrace=False)
    return Fork(root, bun, graph)


def run_fork(repo: Path, fork: Fork, *args: str, direct: bool = False) -> subprocess.CompletedProcess[str]:
    """Run `bun <fork>/core/tools/aidlc.ts <args>` in repo; direct allows the gate-start and approve transitions."""
    extra = {"AIDLC_PROJECT_DIR": str(repo), "AIDLC_STAGE_GRAPH": str(fork.graph)}
    if direct:
        extra["AIDLC_ALLOW_DIRECT_STATE_TRANSITIONS"] = "1"
    return subprocess.run(
        [str(fork.bun), str(fork.root / ENTRY), *args],
        cwd=repo, env=fork_env(fork.bun, **extra), capture_output=True, text=True, check=False,
    )


def fork_shard(repo: Path) -> Path:
    """Return the one audit shard the fork writes in the seeded intent, named by the pinned clone id."""
    shards = sorted((repo / RECORD / "audit").glob(f"*-{CLONE_ID}.md"))
    assert len(shards) == 1, shards
    return shards[0]


def human_turn(repo: Path) -> None:
    """Append the human's answer at the open gate: a HUMAN_TURN row after gate-start's rows."""
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with fork_shard(repo).open("a") as shard:
        shard.write(f"\n## Human Turn\n**Timestamp**: {stamp}\n**Event**: HUMAN_TURN\n\n---\n")


def gate_approvals(repo: Path) -> list[Event]:
    """Return the GATE_APPROVED rows of the fork's shard, read as Earnest reads every shard."""
    shard = fork_shard(repo)
    return [event for event in parse_audit(shard.read_text(), shard.name) if event.fields["Event"] == "GATE_APPROVED"]
```

- [ ] **Step 5:** Run `uv run pytest tests/unit/test_fork.py` and the regression run. Expected: 7 passed, and the regression run is green at Step 1's count plus 7.
- [ ] **Step 6:** Check the graph compile against the real checkout, without changing it:
  - Run `git -C "$EARNEST_AIDLC_FORK" status --short` and save the output.
  - Run `uv run python -c 'from pathlib import Path; import tempfile; from tests.fork import compile_graph, fork_checkout; r, b = fork_checkout(); print(compile_graph(r, b, Path(tempfile.mkdtemp())).graph.stat().st_size)'` from `packages/earnest/`.
  - Expected: a size above zero, and a second `git status --short` identical to the first.
  - If the compile fails on a missing module, stop. Ask the maintainer to run `bun install --frozen-lockfile` in the checkout, which is answer 12's precondition. The agent does not run it. Then run the compile again.
- [ ] **Step 7:** Commit `test: aidlc_fork gate helper that fails without a fork checkout`.

### Task 2: `Unit` joins by unit directory

Run this task only if answer 14 is approved as proposed. If the maintainer chooses the alternative, delete it and note that here.

**Files:** Modify:

- `packages/earnest/src/earnest/plan.py`;
- `packages/earnest/tests/fixtures/seeded-change/units/aidlc/spaces/default/intents/260926-checkout/audit/fixture-a1b2c3d4.md` (line 30);
- `packages/earnest/tests/fixtures/seeded-change/units/FUTURE-FORMAT.md`;
- every file under `packages/earnest/tests/fixtures/seeded-change/evidence-units/` that writes a `Unit` row;
- `packages/earnest/tests/steps/test_unit_status.py` (lines 105-136);
- `packages/earnest/tests/integration/test_seeded_change.py`, including `UNITS_SHA = "4cdc2f5"` at line 287. That constant pins the units variant's commit, which moves when the overlay's audit shard changes.

Test `packages/earnest/tests/unit/test_plan.py`.

**Interfaces:**

- Consumes: the unit table's join, which gives each unit's name and directory (`01`, lines 640-647), and `_gate_keys(event, lanes)` (`plan.py:666-682`).
- Produces:
  - `def _unit_of(event: Event, names: Mapping[str, str]) -> str | None`. `names` maps a unit directory to its unit name, and the function returns `names.get(event.fields.get("Unit", ""))`.
  - Every read of `Unit` in `plan.py` goes through it: `_gate_keys`, the `Attempt Generation` maximum (`:685-702`), `_unit_approval` (`:718-750`), and the voiding by a rejection. `_gate_keys` gains a third parameter, `names`.

- [ ] **Step 1:** Run `grep -n '"Unit"' src/earnest/plan.py`, and list every read in this task.
- [ ] **Step 2:** Write the failing tests:
  - `test_gate_row_joins_unit_by_directory`: a per-stage row with `Unit: u1-limiter` approves `construction/u1-limiter/functional-design`.
  - `test_gate_row_with_the_id_rule_name_approves_nothing`: the same row with `Unit: u1` approves nothing.
  - `test_attempt_generation_counts_by_directory`: a row with `Unit: u1-limiter` and `Attempt Generation: 2` voids a generation-1 approval of `u1-limiter`.
  - `test_rejection_voids_by_directory`: a `GATE_REJECTED` row with `Unit: u2-notice` voids only `u2-notice`'s stage.
- [ ] **Step 3:** Run `uv run pytest tests/unit/test_plan.py -k "directory or id_rule"`. Expected: the four tests fail.
- [ ] **Step 4:** Implement `_unit_of`, and route each read listed in Step 1 through it. Build `names` once, where `lanes` is built, from the same joined rows.
- [ ] **Step 5:** Change the fixture and the rows written by hand:
  - `Unit: u1` becomes `Unit: u1-limiter`, and `Unit: u2` becomes `Unit: u2-notice`;
  - in `FUTURE-FORMAT.md`, the sentence that describes the value now reads "the unit's construction directory, upstream's unit name (`core/knowledge/aidlc-shared/verification.md:23` of the fork)".
  - If a Gherkin line in `04` or a `.feature` file carries a `Unit` value, change both. The maintainer's approval of answer 14 is the ratification that `04` "Fixed for the loop" asks for.
  - Update `UNITS_SHA` in `test_seeded_change.py` to the new short sha of the units variant, and grep `tests/` and `04` for `4cdc2f5` to find any other copy. The comment on that line says why the sha moved. Every other pinned sha stays as it is.
- [ ] **Step 6:** Run `uv run pytest tests/unit/test_plan.py tests/steps/test_unit_status.py tests/steps/test_evidence_check.py tests/integration/test_seeded_change.py` and the regression run. Expected: all pass, at Task 1's count plus 4.
- [ ] **Step 7:** Commit `fix: a gate row's Unit names the unit's construction directory, as upstream writes it`.

### Task 3: The `aidlc_fork` behavior gate, red

**Files:**

- Create:
  - everything under `packages/earnest/tests/fixtures/seeded-change/fork/` and `packages/earnest/tests/fixtures/seeded-change/fork-units/`;
  - `packages/earnest/tests/features/aidlc_fork.feature`;
  - `packages/earnest/tests/steps/test_aidlc_fork.py`.
- Modify: `packages/earnest/tests/conftest.py` and `packages/earnest/tests/steps/test_unit_status.py`.

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
  - `fork-units/aidlc/spaces/default/intents/260926-checkout/aidlc-state.md` is the units variant's state file with these changes: the `- **Unit Ownership**: team` line removed, `- **Review Override**: none` added, the `functional-design` row at `[-]`, and every later row at `[ ]`.
  - `fork-units/aidlc/.aidlc-clone-id` holds `fixturecloneid01`.
- [ ] **Step 3:** Add `"fork"` and `"fork-units"` to `_OVERLAYS` in `conftest.py`, in the same commit as the overlay files. Without that, the base copy takes them in, and the base commit's sha moves, which the sha pins in `test_seeded_change.py` catch.
- [ ] **Step 4:** Move `define_twice` (`test_unit_status.py:53-55`) into `conftest.py`, with its `REQUIREMENTS`, `read` and `write` imports, so that both features share it. `test_unit_status.py` drops the moved step and any import it no longer uses (ruff F401).
- [ ] **Step 5:** Check the readings on the built overlays with Earnest alone. In a scratch test, or with `uv run python`, build each overlay with `commit_on_main(fixture_repo("seeded-change"), "seeded-change", "fork")` and `commit_on_main(units_repo(), "seeded-change", "fork-units")`, then run:
  - `earnest check --stage requirements-analysis`. Expected: exit 0 and 0 results. After `define_twice`: exit 1 and 1 result.
  - `earnest check --stage code-generation`. Expected: exit 0.
  - `earnest check --stage construction/u2-notice/functional-design` on `fork-units`. Expected: exit 0 and 0 results.

  If a count differs, stop. The Gherkin's counts change only through Task 0 and the maintainer.
- [ ] **Step 6:** Copy the M7 Gherkin of `04` into `aidlc_fork.feature`, verbatim.
- [ ] **Step 7:** Write `tests/steps/test_aidlc_fork.py`. Every step asserts on a fork call's exit code, and its message is the call's stderr:

```python
"""Steps of the aidlc_fork feature: the fork's earnest sensor and approve transition, driven from this repository."""

import json

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import commit_on_main
from tests.fork import Fork, compile_graph, fork_checkout, gate_approvals, human_turn, run_fork
from tests.sarif import RECORD

scenarios("../features/aidlc_fork.feature")


@pytest.fixture(scope="session")
def fork(tmp_path_factory) -> Fork:
    root, bun = fork_checkout()
    return compile_graph(root, bun, tmp_path_factory.mktemp("fork-graph"))


def _runs(repo):
    return json.loads((repo / ".earnest" / "assessment.json").read_text())["runs"]


@given("a local AI-DLC fork checkout with Bun")
def checkout(fork):
    assert fork.graph.is_file()


@given(parsers.parse("the repo maintainer's \"seeded-change\" repository with \"code-generation\" at its gate"),
       target_fixture="repo")
def solo_gate(fixture_repo):
    return commit_on_main(fixture_repo("seeded-change"), "seeded-change", "fork")


@given(parsers.parse("the repo maintainer's \"seeded-change\" units variant with the functional design of "
                     "\"u2-notice\" at its gate"), target_fixture="repo")
def units_gate(units_repo):
    return commit_on_main(units_repo(), "seeded-change", "fork-units")


@when(parsers.parse('AI-DLC fires the earnest sensor for "{slug}" on "{path}"'), target_fixture="sensor")
def fire(repo, fork, slug, path):
    return run_fork(repo, fork, "engine", "sensor-earnest", "--stage", slug, "--output-path", str(repo / RECORD / path))


@then(parsers.parse("the sensor prints pass {verdict} with findings count {count:d}"))
def sensor_prints(sensor, verdict, count):
    out = json.loads(sensor.stdout)  # 01 lets the output carry more keys; the contract fixes these two
    assert (out["pass"], out["findings_count"]) == (verdict == "true", count), sensor.stderr


@then("the sensor exits zero")
def sensor_exits_zero(sensor):
    assert sensor.returncode == 0, sensor.stderr


@then(parsers.parse('the record holds a run header for "{stage}" and none for "{bare}"'))
def per_unit_header(repo, stage, bare):
    runs = _runs(repo)
    assert f"{RECORD}/{stage}" in runs, sorted(runs)
    assert f"{RECORD}/{bare}" not in runs, sorted(runs)


@when(parsers.parse('AI-DLC opens the gate of "{slug}"'))
def open_gate(repo, fork, slug):
    done = run_fork(repo, fork, "engine", "state", "gate-start", slug, direct=True)
    assert done.returncode == 0, done.stderr


@when(parsers.parse('AI-DLC opens the gate of unit "{unit}" for "{slug}"'))
def open_unit_gate(repo, fork, slug, unit):
    done = run_fork(repo, fork, "engine", "state", "gate-start", slug, "--unit", unit, direct=True)
    assert done.returncode == 0, done.stderr


@when(parsers.parse("the repo maintainer approves \"{slug}\" at the fork's gate"))
def approve(repo, fork, slug):
    human_turn(repo)
    done = run_fork(repo, fork, "engine", "state", "approve", slug, "--user-input", "Approve", direct=True)
    assert done.returncode == 0, done.stderr


@when(parsers.parse("the repo maintainer approves for unit \"{unit}\" the stage \"{slug}\" at the fork's gate"))
def approve_unit(repo, fork, slug, unit):
    human_turn(repo)
    done = run_fork(repo, fork, "engine", "state", "approve", slug, "--unit", unit, "--user-input", "Approve",
                    direct=True)
    assert done.returncode == 0, done.stderr


def _approval(repo, slug, stage, by, unit=None):
    header = _runs(repo)[f"{RECORD}/{stage}"]
    (row,) = [event for event in gate_approvals(repo) if event.fields.get("Stage") == slug]
    assert row.fields.get("Unit") == unit, row.fields
    assert row.fields["Assessment Hash"] == header["hash"], row.fields
    assert row.fields["Items"].split(", ") == header["items"], row.fields
    assert row.fields["Approved By"] == by, row.fields


@then(parsers.parse("the fork's audit holds one approval of \"{slug}\" with the hash and items of the run header "
                    "for \"{stage}\", approved by \"{by}\""))
def approval_row(repo, slug, stage, by):
    _approval(repo, slug, stage, by)


@then(parsers.parse("the fork's audit holds one approval for unit \"{unit}\" of \"{slug}\" with the hash and items "
                    "of the run header for \"{stage}\", approved by \"{by}\""))
def unit_approval_row(repo, slug, unit, stage, by):
    _approval(repo, slug, stage, by, unit)
```

  The `Items` comparison relies on the run header's `items` being sorted (`plan.header`, `plan.py:1362-1378`) and on the fork writing them in that order, joined by `", "`, as the fixture rows are. If the fork's plan settles a different order, compare sorted lists, and record that in Task 0 Step 4.

- [ ] **Step 8:** With `EARNEST_AIDLC_FORK` pointing at a checkout that has no delta (the maintainer's `earnest/m7-base`), run `uv run pytest tests/steps/test_aidlc_fork.py`. Expected: all 5 scenarios fail on `engine sensor-earnest` or on the missing fields, and none is skipped. Then run it once with `EARNEST_AIDLC_FORK` unset. Expected: all 5 fail with the message naming `EARNEST_AIDLC_FORK`. The regression run (`--ignore` of this module) is green at Task 2's count.
- [ ] **Step 9:** Commit `test: RED aidlc_fork behavior gate`.

### Task 4: Make and CI

**Files:** Modify `packages/earnest/Makefile`, `Makefile`, `.github/workflows/ci.yml` and `CLAUDE.md`.

- [ ] **Step 1:** Change the two Makefiles. In each recipe line below, the leading space stands for a tab; the Markdown linter rewrites tabs in this plan, but make needs them.

  - In `packages/earnest/Makefile`, add `test-aidlc-fork` to `.PHONY`. Change the `test` recipe to `uv run pytest --ignore=tests/steps/test_aidlc_fork.py --cov --cov-report=term-missing --cov-report=xml:coverage.xml`. Add this target after `test`:

```make
test-aidlc-fork: install
 uv run pytest tests/steps/test_aidlc_fork.py
```

- In the root `Makefile`, add `test-aidlc-fork` to `.PHONY`, and add this target after `package`, delegating as `package` does:

```make
test-aidlc-fork:
 $(MAKE) -C packages/earnest test-aidlc-fork
```

- [ ] **Step 2:** Add a job to `ci.yml` after `test-python`. It follows the existing jobs' style, including their tag pins (`actions/checkout@v4`, `astral-sh/setup-uv@v5`):

```yaml
  test-aidlc-fork:
    needs: lint-python
    runs-on: ubuntu-latest
    env:
      AIDLC_FORK_REPO: nullrul/aidlc-workflows  # answer 4 names the repository
      AIDLC_FORK_REF: 0000000000000000000000000000000000000000  # Task 5 sets the fork sha that holds the delta
    steps:
      - uses: actions/checkout@v4
      - uses: actions/checkout@v4
        with:
          repository: ${{ env.AIDLC_FORK_REPO }}
          ref: ${{ env.AIDLC_FORK_REF }}
          path: aidlc-fork
          persist-credentials: false
      - uses: oven-sh/setup-bun@v2
        with:
          bun-version: '1.4.2'  # the fork's CI pins this version
      - uses: astral-sh/setup-uv@v5
      - run: bun install --frozen-lockfile
        working-directory: aidlc-fork
      - run: make -C packages/earnest install test-aidlc-fork
        env:
          EARNEST_AIDLC_FORK: ${{ github.workspace }}/aidlc-fork
```

  Until Task 5, the all-zero `AIDLC_FORK_REF` makes the checkout fail. The job therefore stays red until the delta exists, and it cannot pass by accident.

- [ ] **Step 3:** In `CLAUDE.md`'s Build section, add one line: `make test-aidlc-fork` runs the M7 gate. It needs `EARNEST_AIDLC_FORK` set to a fork checkout and `bun` on `PATH`, and it fails, never skips, without them.
- [ ] **Step 4:** Run `rtk proxy make test; echo $?` from the repository root. Expected: `0`, with the module not collected. Run `LINT_FILE=.github/workflows/ci.yml make lint-file` and check its exit code with `rtk proxy`.
- [ ] **Step 5:** Commit `ci: aidlc_fork gate job against a pinned fork checkout`.

### Task 5: Pin the fork, and turn the gate green

Start this task only after the fork's plan has merged the delta on the fork's `main`.

**Files:** Modify `.github/workflows/ci.yml` (`AIDLC_FORK_REPO`, `AIDLC_FORK_REF`).

- [ ] **Step 1:** Set `AIDLC_FORK_REF` to the full sha of the fork's `main` that holds the delta, and `AIDLC_FORK_REPO` to the repository of answer 4. In the local checkout, run `git -C "$EARNEST_AIDLC_FORK" fetch` and `git -C "$EARNEST_AIDLC_FORK" switch --detach <sha>`. This is the one change this plan makes in the fork checkout, and the maintainer approves it at this step.
- [ ] **Step 2:** In `packages/earnest/`, run `rtk proxy uv run pytest tests/steps/test_aidlc_fork.py; echo $?`. Expected: `0`, with 5 passed.
- [ ] **Step 3:** Check that the hash holds through approve (Review Focus). In the third scenario's built repository, the `Assessment Hash` of the `STAGE_AWAITING_APPROVAL` row, of the `GATE_APPROVED` row, and of the final run header are equal. If they differ, stop. The hash takes in a path that gate-start writes, and that is a fault in the delta or in `01` for the maintainer, not something to fix in the test.
- [ ] **Step 4:** Commit `ci: pin the aidlc_fork gate to fork <short sha>`, and push the branch only under Task 6's review.

### Task 6: The full suite, lint, the clean checkout, and the pre-PR review

**Files:** none. This task only runs the checks.

- [ ] **Step 1:** Run `git -C "$EARNEST_AIDLC_FORK" status --short` and save the output. Then run `rtk proxy make test-aidlc-fork; echo $?`. Expected: `0`, and a second `git status --short` identical to the first.
- [ ] **Step 2:** From the repository root, run `rtk proxy make test; echo $?` and `rtk proxy make lint; echo $?`. Expected: both print `0`.
- [ ] **Step 3:** Run the `/pre-pr-review` skill on HEAD, and record its verdict. Push only under the maintainer's standing rule: three reviewers, every finding fixed, three fresh checkers PASS on the final sha. The PR waits for the CI job `test-aidlc-fork` to be green at the pinned sha.
