# M2b `unit_status`: plan and BDD (approved, rev 3)

<!-- markdownlint-disable MD033 MD038 -->

- **Approval:** human plan approval, decision `decision-129991557aa0fadb4c3baa6fee1f31c9a0b40baa`, 2026-10-14T18:45:35.910Z, of the rev 3 coordination draft (sha256 `68d35f697438a5345171a180b71632394055f9df09ab7fbe7e4598491e355acf`). This committed copy differs from it only in replacing host paths with `<repo>` and review refs with their names; the exact revisions, BDD and Remedy B are unchanged.
- **Where:** worktree `<repo>`, branch `herdsman/work-f5c8264d`, base `266a2bb`.
- **Review:** the plan review of rev 1 returned NEEDS_REVISION on rev 1. Rev 2 answers items 1–23 (§7); the reviewer gives the verdict on rev 2.
- **Evidence:** every count and table here was derived by reading the code, not by running it.
- **Rev 3:** applies user decisions m09555 (2026-10-14, UD11–UD14) and the Manager's gate and size directions. Size exception accepted by the Manager; final bytes are in the handoff. A fresh delta review follows; nothing here approves implementation.

## 0. Decisions

Decided and not re-asked:

- **UD2:** Q10 = A. `change/` and the M3 tables stay untouched.
- **UD3a:** stage id is `<phase>/<unit directory>/<slug>`.
- **UD3b:** an explicit `Unit ID`→`Directory` table; no prefix inference.
- **UD3c:** one frontier per unit.
- **UD4:** earnest-only. Per-unit fork work is REQUIRED in M7.
- **UD5:** approval only through a valid `Unit`; the five `for_each` stages; future-format fixtures; no live integration claimed.
- **UD11 (m09555, was P2):** unit order is dependency order, ties by name; unresolved units follow by name (01(j)).
- **UD11 consequence (proposed canonical revision for formal approval):** the `gap` and `unplanned` fallbacks use the lowest lexical unit with a valid row, independent of `Depends:` order. The Manager chose this (Remedy B of the rev 3 delta review) to honor the user's premise that unit order is display only; Remedy A (narrowing that premise) is not adopted.
- **UD12 (m09555, was H1):** the ahead rule stays; M2b certifies no `unit-end` gate; M7 settles the 01 open row.
- **UD13 (m09555, was H3):** unit-table `route-mismatch` counts against Units Generation, revising 01:452.
- **UD14 (m09555, was P5, P6, H2):** accepted as proposed.

| ID | Proposal (canonical text: 01(j)) | Approval |
| --- | --- | --- |
| P1 | Join: first unfenced `Unit ID`/`Directory` table, raw read. These raise `route-mismatch` at Units Generation: bad rows; repeated rows (the later one); rows with no item; `unit` items with no row (table or not); a missing, symlinked or unreadable table (located at the state file's `units-generation` row) | plan |
| P2 | The five slugs expand in place once for each unit a row joins, in unit order: dependency order, ties by code-point name (u10 before u2); unresolved units (cycle, unknown dependency, or depending on one) follow by name and are not done. properties.plan lists units in unit order, tasks by id. Unit order changes no finding's stage or position: the `gap` and `unplanned` fallbacks pick the lowest lexical unit with a valid row, not the route-first unit | Decided UD11 (m09555); its fallback clause is the proposed UD11 consequence (plan) |
| P3 | The route rule reads the unexpanded route. Per-unit files under any directory stay in the evaluated tree (hash, `dirty`) | plan |
| P4 | A `per-stage` row (or one with no scope) whose `Gate Stages` is absent or equals `Stage` speaks for that stage. A `unit-end` row lists its `Stage`, every listed slug is on the unit's lane, and it is current on the union of the `Items`. Every other row, `unit-merge` included, approves nothing | plan |
| P5 | A unit's generation is the highest whole-number `Attempt Generation` on its counting gate rows of any scope (absent = 0). A lower or non-numeric approval approves nothing. A non-numeric value raises no maximum. Rejections are never discounted | Decided UD14 (m09555) |
| P6 | A rejection voids what it would approve. Failing that, it voids its `Stage` for its unit, or for every unit when `Unit` is missing or unknown | Decided UD14 (m09555) |
| P7 | Lanes. A per-unit finding takes its position from its unit's frontier, any other from the route's. Gap and unplanned placement as 01(j) states (fallback: lowest lexical unit with a valid row, not route order; a unit without a valid row owns none); with no such unit, both go to Units Generation | plan |
| P8 | A unit is done when it has a row, its dependencies are done (a cycle is not done), it has at least one task, and every task is done; an unresolved unit (UD11) is not done | plan |
| P9 | `units/` overlay: the base copy leaves out `change/`, `units/` and the base record directory, then adds `units/aidlc/`. No `rmtree`. `FUTURE-FORMAT.md` is never copied | plan |
| P10 | Remove M2's two refusal scenarios and the refusal code; their tests are re-pointed, not dropped (§2.5) | plan |
| P11 | Each unit in `properties.plan` is `{id,status,directory,frontier} in unit order (UD11)`; summary line `unit <id>: <status>, directory <dir or none>, frontier <stage or none>` | plan |
| P12 | 02:602 owner becomes `nullrul/earnest` | plan |
| H1 | 01's "ahead" rule stays: a `--stage` run ahead of its unit's frontier gives notes and can exit 0. M2b therefore certifies no `unit-end` gate; M7 settles it (01 open row) | Decided UD12 (m09555) |
| H2 | A `Directory` edit changes no item body, so it stales no Units Generation approval and raises no `unbumped-change`. Per-unit `Items` still catch swapped stages | Decided UD14 (m09555) |
| H3 | Unit-table route-mismatch counts against Units Generation, not no stage: before that stage is the frontier such findings are notes; missing-table needs stay. Revises M2-ratified 01:452 | Decided UD13 (m09555) |

P1, P3, P4 and P7–P12 still await formal plan approval, unchanged apart from the mechanical UD11 wording in P7 (via 01(j)), P8 and P11, and the UD11 consequence above (01(j) paragraph 4 and 01(o)).

## 1. Scope

These are the `scope.paths`, exactly; anything else is `needs_approval`.

- `.pi-herdsman/` stays untracked.
- Commits stage only these paths.
- Never `rm` a path the run did not create.

```json
[
"docs/design/01-logic-design.md",
"docs/design/02-structural-design.md",
"docs/design/03-implementation-plan.md",
"docs/design/04-bdd-test-plan.md",
"docs/superpowers/plans/2026-10-14-unit-status.md",
"packages/earnest/src/earnest/plan.py",
"packages/earnest/src/earnest/cli.py",
"packages/earnest/src/earnest/reporter.py",
"packages/earnest/tests/sarif.py",
"packages/earnest/tests/conftest.py",
"packages/earnest/tests/features/stage_status.feature",
"packages/earnest/tests/features/unit_status.feature",
"packages/earnest/tests/steps/test_stage_status.py",
"packages/earnest/tests/steps/test_unit_status.py",
"packages/earnest/tests/unit/test_plan.py",
"packages/earnest/tests/unit/test_cli.py",
"packages/earnest/tests/unit/test_reporter.py",
"packages/earnest/tests/integration/test_seeded_change.py",
"packages/earnest/tests/fixtures/seeded-change/units/FUTURE-FORMAT.md",
"packages/earnest/tests/fixtures/seeded-change/units/aidlc/spaces/default/intents/260926-checkout/aidlc-state.md",
"packages/earnest/tests/fixtures/seeded-change/units/aidlc/spaces/default/intents/260926-checkout/audit/fixture-a1b2c3d4.md",
"packages/earnest/tests/fixtures/seeded-change/units/aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md",
"packages/earnest/tests/fixtures/seeded-change/units/aidlc/spaces/default/intents/260926-checkout/inception/units-generation/unit-of-work.md",
"packages/earnest/tests/fixtures/seeded-change/units/aidlc/spaces/default/intents/260926-checkout/construction/u1-limiter/functional-design/functional-spec.md",
"packages/earnest/tests/fixtures/seeded-change/units/aidlc/spaces/default/intents/260926-checkout/construction/u1-limiter/code-generation/code-generation-plan.md",
"packages/earnest/tests/fixtures/seeded-change/units/aidlc/spaces/default/intents/260926-checkout/construction/u2-notice/functional-design/functional-spec.md",
"packages/earnest/tests/fixtures/seeded-change/units/aidlc/spaces/default/intents/260926-checkout/construction/u2-notice/code-generation/code-generation-plan.md"
]
```

## 2. Proposed canonical revisions (ratified only on plan approval)

- **Anchors:** line numbers are at base `266a2bb`, each with the line's opening words.
- **How to apply:** replace whole lines, and apply bottom-up within each file.
- **Tags:** `[UD#]` marks a decided change (UD11–UD14 cover former P2, P5, P6, H1–H3); `[P#]` marks a proposed one.

### 2.1 `01-logic-design.md`

- **(a) [UD4] 131-132** («no unit; M2b of») →

```text
no unit; M7 of `03` widens it to derive the unit directory from `output_path`
and pass `<phase>/<unit directory>/<slug>`, since a per-unit stage's bare slug
is ambiguous. Every
```

- **(b) [UD4, review 23]** Insert after 165 («the approve path, and AI-DLC's audit validator»):

```text
For per-unit stages M7 of `03` also writes the three fields and `Unit`, the
unit's name by the id rule, at the team gates' emit sites in `aidlc-state.ts`
and `core/tools/aidlc-unit.ts`, and `Unit` on the solo approve path, which
upstream writes without one.
```

- **(c) [P1, UD13] 452** (the `route-mismatch` row): replace `The finding reaches no stage |` with:

```text
On a units route it is also a unit table, table row or `unit` item that the join of Per-unit stages and units cannot use. A Stage Progress finding reaches no stage; a unit-table finding counts against Units Generation |
```

- **(d) [P8, UD11] 479** → `` | `unit` | a unit-table row gives its directory, it is resolved in unit order (see Per-unit stages and units), every unit it depends on is done, and its `code-generation-plan.md` holds a task and every task in it is done | ``
- **(e) [UD3a] 509-514** («slug, such as» … «leaves it out of») →

```text
slug, such as `inception/requirements-analysis`; a route that holds
`units-generation` also has per-unit stages (see Per-unit stages and units).
Earnest reads the route as configuration. It
```

- **(f) [UD5, P4] 547-548** («stage follows it») →

```text
stage follows it, which leaves the stage with none. On a stage that is not
per-unit, a row that carries `Unit`, `Gate Scope` or `Gate Stages` is not read.
```

- **(g) [UD3c] 564-565** («- **current**:») →

```text
- **current**: the finding lies in the frontier stage, its unit's frontier
  stage or the current task. It is in scope, and it is the agent's work now.
```

- **(h) [UD3a] 568-569** («"expected at construction/u1/») →

```text
  "expected at construction/u1-checkout/code-generation", and the agent takes
  no action on it.
```

- **(i) 588** («Progress gives a route, or the route is unsupported») → `Progress gives a route, and so no stage exists.`
- **(j) [UD3, UD5, UD11–UD14, P1, P3, P4, P7, P8]** Insert after 611 («waits for a fresh approval.»; the blank line 612 stays after the insert, so exactly one blank line separates it from the next content) a blank line, then:

```text
### Per-unit stages and units

On a route that holds `units-generation`, Earnest reads by raw read the first
table outside a code fence in `inception/units-generation/unit-of-work.md`
whose header holds `Unit ID` and `Directory`. A row's unit name is its
`Unit ID` by the id rule, a name of the grammar; its directory is one path
segment of lower-case letters, digits and hyphens that names no Stage Progress
slug. A row that cannot be read, repeats an earlier row's name or directory, or
names no `unit` item, and a `unit` item that no row names, raises
`earnest/route-mismatch` at its line, in the Units Generation stage; a table
that is missing, a symlink or unreadable raises it at the state file's
`units-generation` row. A row that raises one stands for no unit. Unit Progress
is never read.

Unit order ranks every `unit` item in the intent's record directory. A
`Depends:` entry of a unit counts when it names, by type and name, a `unit`
item there; any other entry is unknown, and an entry naming a task or another
intent's unit raises no finding of its own. Earnest repeatedly takes, among the
units not yet taken that have no unknown entry and depend only on taken units,
the one with the lowest name, compared by code point (`u10` before `u2`). A
unit Earnest never takes, one on a dependency cycle, with an unknown entry or
depending on such a unit, is unresolved; the unresolved units follow the taken
ones in name order, and none of them is done. `properties.plan` lists units in
unit order and tasks by id. Each EXECUTE row on the route whose slug is
`functional-design`, `nfr-requirements`, `nfr-design`, `infrastructure-design`
or `code-generation`, upstream's `for_each: unit-of-work` set, stands in place
once for each unit a row joins, in unit order, as
`<phase>/<unit directory>/<slug>`, and for no stage when no row joins a unit.
Unit order sets the order of the route's per-unit stages and of the unit list,
and so which per-unit stage the route's frontier names; each unit's lane is
unchanged by it, and no finding's stage or position depends on it, because the
`gap` and `unplanned` fallbacks choose by lowest lexical unit name, not by
route order. The route rule reads the route before this expansion, and
every file under `<phase>/<directory>/<slug>/` of such a row is in the
evaluated tree, so an unusable table drops no need and no file.

A gate row speaks for a per-unit stage only through a `Unit` equal to a unit's
name. With no `Gate Scope`, or `per-stage`, and a `Gate Stages` absent or equal
to its `Stage`, it speaks for that unit's stage of its `Stage`. A `unit-end` row
whose `Gate Stages`, split as `Items` is, lists its `Stage` and only per-unit
stages on that unit's route speaks for each of them, and is current when its
`Items` are the items of all of them. Any other row, `unit-merge` included,
approves nothing. A unit's generation is the highest `Attempt Generation`, a
whole number of at most nine digits and 0 when absent, on its structurally
counting approval and rejection rows (per-stage or unit-end; unit-merge and
non-counting scopes do not raise the maximum, and an unknown `Unit` has no
maximum unit); an approval below it, or whose value is no whole number,
approves nothing, and such a value raises no generation. A counting rejection
voids what it would approve, else its `Stage` for its unit, or for every unit
when its `Unit` names none; no generation discounts it. Upstream's solo approve
path writes no `Unit`, so before M7 of `03` it approves no per-unit stage. A
`STAGE_SKIPPED` row carrying `Unit`, `Gate Scope` or `Gate Stages` skips
nothing, and restarts and jumps void rows by slug for every unit.

A unit's lane is the route less the other units' per-unit stages; its frontier
is the first stage on its lane without a current approval. A finding in a
per-unit stage takes its position from its unit's frontier, any other from the
route's, so one unit's error never reads ahead because another unit's frontier
sits earlier, and a stage after the per-unit stages reads ahead until every
unit's are approved. A `gap` whose producing stage is per-unit counts against
that stage of the unit whose stage holds the item, else of the lowest-named
unit with a valid row that delivers it, else of the lowest-named unit with a
valid row; `unplanned` counts against the Code Generation of the lowest-named
unit with a valid row that delivers the requirement, else of the lowest-named
unit with a valid row. Names compare by code point. A unit with no row, or
whose row is invalid, owns no fallback. With no unit with a valid row both
count against Units Generation.

A `--stage` run of a stage ahead of its unit's frontier reports that unit's
errors there as notes and can exit 0, so a `unit-end` gate that fires its
sensor at its final stage is not shown safe before M7 of `03` (see Open
questions). A `Directory` edit changes no item body, so it neither stales the
Units Generation approval nor raises `unbumped-change`; per-unit approvals go
stale through their `Items`.
```

- **(k) 1224-1233** («none or more than one.» … «supported intents lists those») →

```text
none or more than one. `--stage` takes `<phase>/<slug>`,
`<phase>/<unit directory>/<slug>` for a per-unit stage, or a bare slug that is
unique on the route. `earnest plan` lists every intent.
```

- **(l) 1241-1242** («stage that is not on the route, or the selected») → `stage that is not on the route, or a reader of stdout or stderr goes away. A stage's computed status is information and sets no exit code. Agents`
- **(m) [P11, UD11] 1276-1277** («`tasks` and `units`, each sorted») →

```text
  `tasks`, sorted by the pair id and status, and `units`, in unit order (see
  Per-unit stages and units), with the `status` of each, and each unit's
  `directory` (null without a table row) and `frontier` (null when its lane has
  no stage without a current approval). A run with `--stage` also carries
  `properties.assessment`:
```

- **(n) [UD4, UD12] 1422** → `` | Per-unit fork work, milestone `aidlc_fork`: how a `unit-end` gate checks each stage its `Gate Stages` lists while those stages read ahead of the unit's frontier; where upstream raises `Attempt Generation`; whether `STAGE_SKIPPED` or `STAGE_JUMPED` rows carry `Unit` | maintainer | before milestone `aidlc_fork` of `03-implementation-plan.md` | ``

- **(o) [UD11 consequence; proposed for formal approval, not yet canonical] 573-576**
  («`earnest/unplanned` counts against the Code Generation stage» … «finding. The rule reads the route») →

```text
child's type. `earnest/unplanned` counts against the Code Generation stage
whose unit delivers the requirement, or against the first Code Generation stage
on the route when no unit does; on a route that holds `units-generation` it
counts instead against the Code Generation stage of the lowest-named unit with
a valid row of the unit table that delivers the requirement, else of the
lowest-named unit with a valid row, and against Units Generation when no unit
has a valid row (see Per-unit stages and units); a route without a Code
Generation stage, read before the per-unit expansion, holds no tasks, so it
raises no `earnest/unplanned` finding. The rule reads the route
```

  Routes without `units-generation` keep the existing first-on-the-route rule; the ordinary M2 rule is unchanged.

### 2.2 `02-structural-design.md`

- **(a)** After 94 (`          change/`), insert `          units/`.
- **(b) 100-102** («`seeded-change` that M2b») →

```text
`seeded-change` that M2b of `03` adds (a units route, a `Unit ID` and
`Directory` table, per-unit stages and future-format `Unit` rows) is a second
history of the same directory, from its `units/` overlay, so the tree lists
`seeded-change/` once.
```

- **(c) [UD4, review 23]**
  - After 143 (`    aidlc-state.ts … changed`), insert `    aidlc-unit.ts` padded with spaces so `changed` lines up in the same column.
  - Replace 188-189 («(`core/tools/aidlc-unit.ts`)») with:

```text
  (`core/tools/aidlc-unit.ts`) and the team gates of `aidlc-state.ts` join this
  delta with M7 of `03`, which also writes `Unit`, by the id rule, on the solo
  approve path's `GATE_APPROVED` row.
```

- **(d) 316-317** («position to read each stage's approval; refuses») →

```text
  position to read each stage's approval; reads the unit table and the
  unit-scoped rows of Per-unit stages and units in `01`; and raises
  `earnest/route-mismatch`. Computes
```

- **(e) [P9, review 22] 350-356** (the `conftest.py` and `sarif.py` bullets) →

```text
- `conftest.py`: shared fixtures and the steps two or more features share. It
  copies a fixture's files, less its `change/` and `units/` overlays, into
  `tmp_path` and commits them with `git` as a base commit on `main`, and a
  separate step commits the `change/` overlay on a `task/…` branch, because the
  record must be written between the two commits. The units variant leaves out
  the intent's record directory too and adds the `units/` overlay's in the same
  commit.
- `sarif.py`: the plain helpers shared by the step modules and the unit and
  integration tests.
```

- **(f) 549-550** («by `conftest.py` from the same files plus») →

```text
  by `conftest.py` from the same files with the intent's record directory taken
  from a `units/` overlay, so it adds no fixture directory.
```

- **(g) [P12] 602:** `cajias/earnest` → `nullrul/earnest`.
- **(h) 609:** delete the row (resolved by P9).

### 2.3 `03-implementation-plan.md`

- **(a) 27:** change `  class M1,M2 done` to `  class M1,M2,M2b done`. This is applied **only in T8**.
- **(b) 111:** change `  with exit 2.` to `  with exit 2; M2b replaces the refusal.`
- **(c) 141-167** (the M2b section body) →

```text
- Goal: report per-unit stages, units and team gates on routes with Units
  Generation, from this repository alone.
- Depends on: M2.
- Exit behavior: in the future-format units variant of `seeded-change`,
  `earnest plan` prints each per-unit stage as
  `<phase>/<unit directory>/<slug>` with its computed status and approval, and
  each unit, in unit order, with its status, directory and frontier; an
  error at one unit's frontier fails the check whatever another unit's
  frontier; an unusable unit table fails the check and drops no need; `check --stage` for a per-unit stage
  prints the assessment hash and writes the run header; a gate row approves a
  unit's stage only through a `Unit` that the unit table joins to its
  directory, at the unit's latest `Attempt Generation`.
- Exit command: `uv run pytest tests/steps/test_unit_status.py`.
- Deliverable: in `plan.py` the unit table, per-unit stages, unit frontiers,
  unit-scoped gate rows and unit status; in `cli.py` per-unit `--stage` and no
  unsupported-route refusal; the unit lines in `reporter.py`; the `units/`
  overlay of `seeded-change`; `unit_status.feature` and its step module. The
  fork's per-unit work is M7's.
- Spec coverage: UC7, UC9 (per-unit approvals); SC1, SC8 (unit and per-unit
  stage status), SC9 (per-unit run header); the Plan and stage status
  capability.
- Context to load: `01`: Stages, Frontier and position, Per-unit stages and
  units, Computed status, Command surface. `02`: `plan.py`, `conftest.py`,
  `fixtures/seeded-change/`, L6.
- Gating open questions: none.
- Task plan:
  [2026-10-14-unit-status.md](../superpowers/plans/2026-10-14-unit-status.md).
```

- **(d) [UD4] M7.** Insert after 271 («`GATE_APPROVED` with `Assessment Hash`»):

```text
  For a per-unit stage of the units variant the sensor passes
  `<phase>/<unit directory>/<slug>`, and approve writes `Unit` with them.
```

Replace 273-274 («- Deliverable: `aidlc_fork.feature`») with:

```text
- Deliverable: `aidlc_fork.feature` and its step module here; the Fork delta
  in the fork's repository, which must include the per-unit work M2b leaves to
  it: the sensor script deriving the unit directory from `output_path`, the
  three fields and `Unit` at the team gates' emit sites in `aidlc-state.ts` and
  `aidlc-unit.ts`, and `Unit` on the solo approve path.
```

Replace 287 («sensors-off switches;») with:

```text
  sensors-off switches; the upstream tests that pin sensor ids and routes.
  From M2b: authority to create and push the fork repository, a fork checkout
  with Bun, and the per-unit row of `01`.
```

### 2.4 `04-bdd-test-plan.md`

- **43:** the success-criteria cell becomes `SC1, SC8 (unit and per-unit stage status), SC9 (per-unit run header)`.
- **50:** becomes `The scenarios of M3 to M7 are added here when each milestone's plan is written.`
- **530-542:** delete the blank line and the scenarios «A route with per-unit stages is refused by the plan (SC8)» and «… by the stage check (SC9)».
- **570-574:** delete the bullet «- Unsupported intent:».
- **590-592:** becomes:

```text
  neither `structural` nor `plan`. Unit status and `Depends:` between units
  belong to M2b: the M2 route has no Units Generation.
```

- **Insert before 597 (`## Scope (v1)`):**

````text
## M2b `unit_status`

- Feature: `packages/earnest/tests/features/unit_status.feature`, bound by
  `tests/steps/test_unit_status.py`.
- Fixture: the units variant of `seeded-change` (L6 of `02`): the base files
  with the intent's record directory taken from the `units/` overlay, a
  `classic` route with Units Generation, units `u1` (`u1-limiter`) and `u2`
  (`u2-notice`), each with Functional Design and Code Generation, and
  approvals of the requirements, the units and `u1`'s Functional Design. Its
  unit-scoped rows use the future format of `units/FUTURE-FORMAT.md`; upstream
  at `fe563195d827` writes no `Unit` on a solo approval and none of the fork's
  three fields, so no live AI-DLC run is claimed.
- Success criteria asserted: SC1, SC8 (unit and per-unit stage status), SC9
  (per-unit run header). Readings: Per-unit stages and units in `01`.

### Unit status feature

```gherkin
<the Gherkin of the plan's §3.2, verbatim>
```

- Notes: "holds exactly these findings in the intent's record:" compares
  every result in the log; only the `file` column has the intent record prefix
  removed. A result outside the record keeps its full path and fails the step.
  `-` in an outline omits that field; table, unit-order, generation and rejection cases
  beyond the feature are unit-tier tests.
````

- **599-600:** «of M1 and M2 in full» → «of M1, M2 and M2b in full».
- **607:** «The scenarios of M2b and M3 to M7» → «The scenarios of M3 to M7».

### 2.5 M2 tests (P10, by exact name)

- **`stage_status.feature`:**
  - Delete the two refusal scenarios named in 2.4 and the blank line before them.
  - The other 26 scenarios and every exact table stay byte-identical.
- **`steps/test_stage_status.py`:**
  - Delete `UNSUPPORTED`, `execute_stage` and `stderr_names_unsupported_route`.
  - Move to `tests/sarif.py`: `HASH_LINE`, `read`, `block`, `append_block`, `intent_plan`, `approval_text`, `printed_hash`, `record`, `header`, `results`.
  - Move to `conftest.py`:
    - fixture `memory`;
    - steps `agent_has_run_stage_check`, `agent_runs_plan`, `agent_runs_check`, `agent_runs_stage_check`, `plan_lists_stages`, `frontier_is`, `plan_lists_tasks`, `plan_lists_stage`, `stage_has_approval`, `summary_prints_hash`, `sarif_gives_hash_and_status`, `run_header_holds`, `git_lists_no_new_file`, `exits_with_code_two`, `no_record`.
  - Bodies stay unchanged. Both modules import from `tests.sarif`, which imports nothing from `tests`, so there is no import cycle.
- **`unit/test_cli.py`** (each old test becomes the new one):

| Old | New |
| --- | --- |
| `test_plan_of_an_only_unsupported_intent_exits_two_with_empty_stdout` | `test_plan_of_a_units_intent_without_a_table_at_its_frontier_exits_nonzero` (the existing `UNITS` state has Units Generation first on the route, so it is the frontier and the finding is a current error: exit 1; the before-frontier note case belongs to H3) |
| `test_check_stage_of_an_unsupported_intent_exits_two_and_writes_nothing` | `test_check_stage_of_a_per_unit_stage_writes_its_run_header` |
| `test_plain_check_places_an_unsupported_intents_findings_without_a_plan` | `test_plain_check_of_a_units_intent_without_a_table_places_its_needs_at_units_generation` (errors, exit 1) |
| `test_plan_lists_the_supported_intents_when_another_is_unsupported` | `test_plan_lists_every_intent_including_a_units_intent` |
| `test_plan_of_several_intents_all_unsupported_exits_zero_with_skip_lines` | deleted: the row above covers it, and no skip line exists any more |
| `test_plain_check_of_an_unsupported_only_repository_keeps_the_m1_findings` | `test_plain_check_of_a_units_intent_without_a_table_is_no_silent_pass` (traced 0%, both gaps, exit 1) |

- **`unit/test_plan.py`:**
  - `UNSUPPORTED_STATE` becomes `UNITS_STATE`.
  - Renames:

| Old | New |
| --- | --- |
| `test_units_generation_on_the_route_is_unsupported` | `test_units_generation_on_the_route_expands_per_unit_stages` |
| `test_units_generation_off_the_route_is_supported` | `test_route_without_units_generation_is_unchanged` |
| `test_produces_is_none_when_no_intent_is_supported` | `test_produces_is_none_without_an_intent_and_keeps_a_units_routes_needs` |
| `test_in_tree_is_false_for_an_unsupported_intents_state_and_audit_files` | `test_in_tree_of_a_units_intent_drops_bookkeeping_and_keeps_per_unit_files` |
| `test_properties_leave_out_an_unsupported_intent` | `test_properties_list_a_units_intent` |
| `test_dirty_ignores_the_files_of_an_unsupported_intent_that_ai_dlc_writes` | `test_dirty_ignores_a_units_intents_bookkeeping_and_sees_its_per_unit_files` |

- `test_select_intent_unsupported_raises_the_unsupported_route_error` is deleted, because the refusal is gone.
- The five `test_select_intent_*` tests keep their bodies on `plan.find_intent` and are renamed `test_find_intent_*`.
- **`unit/test_reporter.py`:** in `test_summary_lists_tasks_and_units_with_their_status`, the unit entry gains `"directory": None, "frontier": None`. The expected line becomes `  unit unit~a~1: not done, directory none, frontier none`.
- **Must stay unchanged and green:** `test_a_renamed_stage_progress_heading_is_a_finding_not_a_silent_pass`, `test_an_unreadable_stage_progress_row_fails_every_command`, and every multi-intent test.

## 3. BDD

### 3.1 Fixture `packages/earnest/tests/fixtures/seeded-change/units/`

Below, `…/` is `aidlc/spaces/default/intents/260926-checkout/`. The scope list above spells every path in full.

**`FUTURE-FORMAT.md`** (never copied):

```text
# Future format

This overlay's unit-scoped audit rows use the format the AI-DLC fork writes
from milestone M7: `Unit` holds the unit's Earnest name by the id rule (`u1`
for `U1`), beside `Gate Scope`, `Gate Stages`, `Attempt Generation`,
`Assessment Hash`, `Items` and `Approved By`. Upstream at fe563195d827 writes no
`Unit` on solo approvals and none of the last three fields, and where it raises
`Attempt Generation` is unverified. The state file's Unit Progress table is
illustrative; Earnest never reads it. No live AI-DLC run is claimed.
```

**`…/aidlc-state.md`** (the `units-generation` row is line 20):

```text
# AI-DLC State Tracking

## Project Information
- **Project**: checkout
- **Project Type**: Greenfield
- **Scope**: classic
- **Unit Ownership**: team
- **Construction Iteration**: unit-major
- **Start Date**: 2026-09-26

## Stage Progress
<!-- Checkbox states: [ ] pending, [-] in-progress, [?] awaiting approval, [R] revising, [x] completed, [S] skipped -->
### INITIALIZATION PHASE
- [x] workspace-scaffold — EXECUTE: always
- [x] workspace-detection — EXECUTE: always
- [x] state-init — EXECUTE: always

### INCEPTION PHASE
- [x] requirements-analysis — EXECUTE: always
- [x] units-generation — EXECUTE: two units

### CONSTRUCTION PHASE
- [x] functional-design — EXECUTE: per unit
- [S] nfr-requirements — SKIP: no new quality attributes
- [S] nfr-design — SKIP: no new quality attributes
- [S] infrastructure-design — SKIP: no infrastructure change
- [x] code-generation — EXECUTE: always
- [ ] build-and-test — EXECUTE: always

## Unit Progress
| unit | owner | functional-design | code-generation | gate |
| --- | --- | --- | --- | --- |
| u1 | - | [x] | [x] | [x] |
| u2 | - | [x] | [-] | [ ] |
```

**`…/audit/fixture-a1b2c3d4.md`:** four blocks in M2's form (`## Title`, `**Timestamp**`, `**Event**`, then the fields in this order), each closed by `---`. `H` stands for `sha256:` followed by 64 zeros.

1. **09:00:00Z `WORKFLOW_STARTED`:** Scope `classic`; Request `Lock members out after repeated failed logins.`
2. **10:00:00Z `GATE_APPROVED`:** Stage `requirements-analysis`; User Input `Approve`; Assessment Hash `H`; Items `req~audit-log~1, req~lockout-notice~1, req~rate-limit~1`; Approved By `human`.
3. **10:30:00Z `GATE_APPROVED`:** Stage `units-generation`; User Input `Approve`; Assessment Hash `H`; Items `unit~u1~1, unit~u2~1`; Approved By `human`.
4. **11:00:00Z `GATE_APPROVED`:** Stage `functional-design`; User Input `Approve`; Unit `u1`; Gate Scope `per-stage`; Gate Stages `functional-design`; Attempt Generation `1`; Assessment Hash `H`; Items `dsn~window-counter~1`; Approved By `human`.

**`…/inception/requirements-analysis/requirements.md`:** a byte copy of the base file.

**`…/inception/units-generation/unit-of-work.md`:**

```text
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
```

**`…/construction/<dir>/functional-design/functional-spec.md`:** line 1 `# Functional design`, line 3 the id, line 5 the body, line 7 the key line.

- **u1-limiter:** `` `dsn~window-counter~1` ``; body `Count failed logins per member in a sliding fifteen-minute window.`; `Drivers: req~rate-limit~1`.
- **u2-notice:** `` `dsn~notice-text~1` ``; body `Show the time the lockout ends in the member's time zone.`; `Drivers: req~lockout-notice~1`.

**`…/construction/<dir>/code-generation/code-generation-plan.md`:** the same shape, with line 1 `# Code generation plan`.

- **u1-limiter:** `` `task~add-limiter~1` ``; body `Add a limiter that counts failed logins in a window.`; `Delivers: req~rate-limit~1, dsn~window-counter~1`.
- **u2-notice:** `` `task~notify-lockout~1` ``; body `Tell the member when the lockout starts.`; `Delivers: req~lockout-notice~1, dsn~notice-text~1`.

### 3.2 Gherkin (copied verbatim into `04` and `unit_status.feature`)

```gherkin
Feature: Unit status
  The coding agent and the repo maintainer read where each unit of a units
  intent stands from the command output alone: each per-unit stage under its
  unit directory with its status and approval, each unit's status, directory
  and frontier, and approvals that count only through a gate row that names
  the unit (UC7, UC9; SC1, SC8, SC9). The fixture's unit-scoped rows use the
  future format the fork writes from M7.

  Background:
    Given the repo maintainer's "seeded-change" repository in its future-format units variant, with the requirements, the units and the first unit's functional design approved

  Scenario: The plan prints each per-unit stage, each unit and each frontier (SC8)
    When the coding agent runs earnest plan
    Then the plan lists these stages in route order:
      | stage | status | approval |
      | inception/requirements-analysis | done | current, human |
      | inception/units-generation | done | current, human |
      | construction/u1-limiter/functional-design | done | current, human |
      | construction/u2-notice/functional-design | not done | none |
      | construction/u1-limiter/code-generation | not done | none |
      | construction/u2-notice/code-generation | not done | none |
      | construction/build-and-test | not done | none |
    And the frontier is "construction/u2-notice/functional-design"
    And the plan lists these units:
      | unit | status | directory | frontier |
      | unit~u1~1 | not done | u1-limiter | construction/u1-limiter/code-generation |
      | unit~u2~1 | not done | u2-notice | construction/u2-notice/functional-design |
    And the plan lists these tasks:
      | task | status |
      | task~add-limiter~1 | not done |
      | task~notify-lockout~1 | not done |
    And the summary names each unit with its status, directory and frontier
    And the plan exits zero and names no unsupported route

  Scenario: Marks someone typed in Stage Progress or Unit Progress are not read (SC8)
    When the coding agent runs earnest plan
    Then "construction/u1-limiter/code-generation" is "not done" although the state file marks it complete for its unit

  Scenario: Dropping Unit Progress leaves the plan's SARIF log as it was (SC1, SC8)
    When the coding agent runs earnest plan before and after an uncommitted edit drops the state file's Unit Progress
    Then both runs write the same SARIF log

  Scenario: An error at one unit's frontier fails the check while another unit's frontier sits earlier (SC8)
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings in the intent's record:
      | rule | file | line | level | position | stage |
      | earnest/gap | construction/u1-limiter/functional-design/functional-spec.md | 3 | error | current | construction/u1-limiter/code-generation |
      | earnest/gap | construction/u2-notice/functional-design/functional-spec.md | 3 | note | ahead | construction/u2-notice/code-generation |
      | earnest/unplanned | inception/requirements-analysis/requirements.md | 13 | warning | current | construction/u1-limiter/code-generation |
    And the check exits non-zero

  Scenario: An error in an approved shared stage is a regression whatever each unit's frontier (SC8)
    Given the coding agent defines "req~rate-limit~1" a second time at the end of the requirements
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings in the intent's record:
      | rule | file | line | level | position | stage |
      | earnest/duplicate | inception/requirements-analysis/requirements.md | 17 | error | behind | inception/requirements-analysis |
      | earnest/gap | construction/u1-limiter/functional-design/functional-spec.md | 3 | error | current | construction/u1-limiter/code-generation |
      | earnest/gap | construction/u2-notice/functional-design/functional-spec.md | 3 | note | ahead | construction/u2-notice/code-generation |
      | earnest/unplanned | inception/requirements-analysis/requirements.md | 13 | warning | current | construction/u1-limiter/code-generation |
    And the check exits non-zero

  Scenario Outline: A unit table that cannot be read fails the check and drops no per-unit need (SC8)
    Given the coding agent leaves the unit table <state>, uncommitted
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings in the intent's record:
      | rule | file | line | level | position | stage |
      | earnest/route-mismatch | aidlc-state.md | 20 | error | current | inception/units-generation |
      | earnest/gap | construction/u1-limiter/functional-design/functional-spec.md | 3 | error | current | inception/units-generation |
      | earnest/gap | construction/u2-notice/functional-design/functional-spec.md | 3 | error | current | inception/units-generation |
      | earnest/unplanned | inception/requirements-analysis/requirements.md | 13 | warning | current | inception/units-generation |
    And the check exits non-zero

    Examples:
      | state |
      | deleted |
      | a symlink to a copy outside the repository |

  Scenario: A unit table row that no unit item names is flagged at Units Generation (SC8)
    Given the repo maintainer adds the row "| U3 | u3-audit | Record each lockout |" after the unit table's last row
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings in the intent's record:
      | rule | file | line | level | position | stage |
      | earnest/route-mismatch | inception/units-generation/unit-of-work.md | 7 | error | behind | inception/units-generation |
      | earnest/gap | construction/u1-limiter/functional-design/functional-spec.md | 3 | error | current | construction/u1-limiter/code-generation |
      | earnest/gap | construction/u2-notice/functional-design/functional-spec.md | 3 | note | ahead | construction/u2-notice/code-generation |
      | earnest/unplanned | inception/requirements-analysis/requirements.md | 13 | warning | current | construction/u1-limiter/code-generation |
    And the check exits non-zero

  Scenario: A unit's directory comes from the unit table, not from its name (SC8)
    Given the repo maintainer moves the second unit to the directory "notice", in the unit table and on disk
    When the coding agent runs earnest plan
    Then the plan lists these units:
      | unit | status | directory | frontier |
      | unit~u1~1 | not done | u1-limiter | construction/u1-limiter/code-generation |
      | unit~u2~1 | not done | notice | construction/notice/functional-design |
    And the plan lists "construction/notice/code-generation" among the stages

  Scenario: Units follow their dependencies, not their names, on the route and in the unit list (SC8)
    Given the repo maintainer makes unit "u1" depend on "u2" and drops the dependency of "u2" on "u1"
    When the coding agent runs earnest plan
    Then the plan lists these stages in route order:
      | stage | status | approval |
      | inception/requirements-analysis | done | current, human |
      | inception/units-generation | done | current, human |
      | construction/u2-notice/functional-design | not done | none |
      | construction/u1-limiter/functional-design | done | current, human |
      | construction/u2-notice/code-generation | not done | none |
      | construction/u1-limiter/code-generation | not done | none |
      | construction/build-and-test | not done | none |
    And the frontier is "construction/u2-notice/functional-design"
    And the plan lists these units:
      | unit | status | directory | frontier |
      | unit~u2~1 | not done | u2-notice | construction/u2-notice/functional-design |
      | unit~u1~1 | not done | u1-limiter | construction/u1-limiter/code-generation |
    And the plan lists these tasks:
      | task | status |
      | task~add-limiter~1 | not done |
      | task~notify-lockout~1 | not done |

  Scenario: A unit's stage check fails on that unit's own error (SC8, SC9)
    When the coding agent runs earnest check --stage "construction/u1-limiter/code-generation"
    Then the SARIF log holds exactly these findings in the intent's record:
      | rule | file | line | level | position | stage |
      | earnest/gap | construction/u1-limiter/functional-design/functional-spec.md | 3 | error | current | construction/u1-limiter/code-generation |
      | earnest/unplanned | inception/requirements-analysis/requirements.md | 13 | warning | current | construction/u1-limiter/code-generation |
    And the check exits non-zero

  Scenario: Another unit's stage check passes, prints the assessment hash and writes the run header (SC9)
    When the coding agent runs earnest check --stage "construction/u2-notice/functional-design"
    Then the SARIF log holds no findings
    And the summary prints the assessment hash
    And the SARIF log gives the same hash and the stage status "not done"
    And the run header for "construction/u2-notice/functional-design" in the assessment record holds:
      | field | value |
      | commit | the repository's HEAD commit |
      | dirty | false |
      | layers | trace |
      | items | dsn~notice-text~1 |
      | hash | the hash the summary printed |
    And Git lists no new file
    And the check exits zero

  Scenario: A stage check ahead of its unit's frontier reports that unit's error as a note, so no unit-end gate is shown safe (SC9)
    When the coding agent runs earnest check --stage "construction/u2-notice/code-generation"
    Then the SARIF log holds exactly these findings in the intent's record:
      | rule | file | line | level | position | stage |
      | earnest/gap | construction/u2-notice/functional-design/functional-spec.md | 3 | note | ahead | construction/u2-notice/code-generation |
    And the check exits zero

  Scenario Outline: A stage check that names no single stage on the route is refused (SC9)
    When the coding agent runs earnest check --stage "<stage>"
    Then the check exits with code 2, with empty stdout
    And stderr is one line that names "<named>"
    And no assessment record exists

    Examples:
      | stage | named |
      | functional-design | construction/u2-notice/functional-design |
      | construction/u2/functional-design | is not a stage on the route |
      | construction/functional-design | is not a stage on the route |
      | construction/../u2-notice/functional-design | is not a stage on the route |

  Scenario: A team's per-stage gate approves its own unit's stage and moves that unit's frontier (SC8, SC9)
    Given the coding agent has run earnest check --stage "construction/u2-notice/functional-design"
    And the repo maintainer approves "construction/u2-notice/functional-design" at the per-stage gate of unit "u2"
    When the coding agent runs earnest plan
    Then "construction/u2-notice/functional-design" has the approval "current, human"
    And the plan lists these units:
      | unit | status | directory | frontier |
      | unit~u1~1 | not done | u1-limiter | construction/u1-limiter/code-generation |
      | unit~u2~1 | not done | u2-notice | construction/u2-notice/code-generation |
    And the frontier is "construction/u1-limiter/code-generation"

  Scenario Outline: A gate row approves a unit's stage only through a Unit and scope that name it (SC8)
    Given the audit log gains a GATE_APPROVED row for "functional-design" with Unit "<unit>", Gate Scope "<scope>" and Gate Stages "<stages>"
    When the coding agent runs earnest plan
    Then "construction/u2-notice/functional-design" has the approval "<approval>"

    Examples:
      | unit | scope | stages | approval |
      | u2 | per-stage | functional-design | current, human |
      | u2 | - | - | current, human |
      | - | - | - | none |
      | u2-notice | per-stage | functional-design | none |
      | U2 | per-stage | functional-design | none |
      | u9 | per-stage | functional-design | none |
      | u2 | per-stage | functional-design,code-generation | none |
      | u2 | unit-end | code-generation | none |
      | u2 | unit-merge | functional-design | none |

  Scenario: A team's unit-end gate approves every stage it lists for its unit (SC8)
    Given the coding agent has run earnest check --stage "construction/u2-notice/functional-design"
    And the coding agent has run earnest check --stage "construction/u2-notice/code-generation"
    And the repo maintainer approves unit "u2" at its unit-end gate, reported against "code-generation"
    When the coding agent runs earnest plan
    Then "construction/u2-notice/functional-design" has the approval "current, human"
    And "construction/u2-notice/code-generation" has the approval "current, human"
    And the frontier of unit "unit~u2~1" is "construction/build-and-test"

  Scenario Outline: Only a unit's latest Attempt Generation approves its stages (SC8)
    Given the audit log gains a per-stage GATE_APPROVED row for "code-generation" of unit "u1" at Attempt Generation "<generation>"
    When the coding agent runs earnest plan
    Then "construction/u1-limiter/functional-design" has the approval "<approval>"
    And the frontier of unit "unit~u1~1" is "<frontier>"

    Examples:
      | generation | approval | frontier |
      | 2 | none | construction/u1-limiter/functional-design |
      | 1 | current, human | construction/build-and-test |
      | x2 | current, human | construction/u1-limiter/code-generation |

  Scenario Outline: A rejection voids the approvals it names, and every unit's when its Unit names none (SC8)
    Given the audit log gains a GATE_REJECTED row for "functional-design" of unit "<unit>" after the approval
    When the coding agent runs earnest plan
    Then "construction/u1-limiter/functional-design" has the approval "<approval>"
    And the frontier of unit "unit~u1~1" is "<frontier>"

    Examples:
      | unit | approval | frontier |
      | u1 | none | construction/u1-limiter/functional-design |
      | u2 | current, human | construction/u1-limiter/code-generation |
      | - | none | construction/u1-limiter/functional-design |
      | u9 | none | construction/u1-limiter/functional-design |
```

### 3.3 New steps

Shared steps are in §2.5. Every edit a step makes is uncommitted. `-` means the field is omitted.

| Step | Does |
| --- | --- |
| Background | Builds `units_repo()` and asserts the shard holds `**Unit**: u1` |
| …exactly these findings in the intent's record: | The shared exact-set comparison (lives in `conftest.py`), with `file` taken relative to `aidlc/spaces/default/intents/260926-checkout/`. Every result in the log is compared; only the `file` column has the intent record prefix removed. A result outside the record keeps its full path and fails the step. |
| leaves the unit table `<state>` | Deletes `…/inception/units-generation/unit-of-work.md`, or replaces it with a symlink to a copy in `tmp_path`, outside the repository |
| defines … a second time | Appends ``"\n`req~rate-limit~1`\n\nDefined twice by mistake.\n"`` |
| adds the row … | Inserts the row after table line 6 |
| moves the second unit … | Rewrites `\| U2 \| u2-notice \|` and renames the directory |
| makes unit "u1" depend on "u2" … | In `unit-of-work.md`, first deletes the line `Depends: unit~u1~1`, then inserts `Depends: unit~u2~1` after the line `Delivers: req~rate-limit~1`; both are matched by content, so nothing depends on a shifted line number. These are key lines only, so no body or `Items` changes and the Units Generation approval stays current |
| plan before and after … | Runs `plan`, deletes the lines from `## Unit Progress` to the end of the file, runs `plan` again → `runs` |
| per-stage gate of unit | Writes Stage `<slug>`, Unit, Gate Scope `per-stage`, Gate Stages `<slug>`, Attempt Generation `1`, Items and Assessment Hash from the run header, Approved By `human`, at 12:00:00Z |
| unit-end gate | Writes Stage `code-generation`, Unit `u2`, Gate Scope `unit-end`, Gate Stages `functional-design,code-generation`, Attempt Generation `1`, Items = the sorted union of both run headers, Approved By `human` |
| GATE_APPROVED row … with Unit | Items `dsn~notice-text~1`, Approved By `human`, at 12:00:00Z; no Attempt Generation |
| per-stage … at Attempt Generation | Items `task~add-limiter~1`, Gate Stages `code-generation`, Approved By `human`, at 12:00:00Z |
| GATE_REJECTED … of unit | Unit, plus Gate Scope `per-stage` when a Unit is given; Feedback; at 11:30:00Z |
| …typed marks… | Asserts `- [x] code-generation — EXECUTE` and `\| u1 \| - \| [x] \| [x] \| [x] \|` are present, then reads the plan |
| units / summary / unit frontier | Read `properties.plan` and the P11 stderr line; the units table compares the ordered list, as the tasks table does |
| holds no findings; names "…"; exits zero and names no unsupported route | `results == []`; stderr is exactly one line containing the text; exit code 0 and no `unsupported route` on stderr |

### 3.4 RED (T1, before any `src/` change; predicted)

- **Exact gate argv** (§5 `bdd-unit-status`): expected exit 1, with 35 failed and 0 passed. That is 13 scenarios plus 22 outline examples. All counts and classes here are derived by reading, not observed.
- **Attribution argv** (evidence only): `uv run pytest tests/steps/test_unit_status.py --tb=long -l`. It must show exactly these failure classes:

| Class | n | Tests | Valid only when |
| --- | --- | --- | --- |
| `JSONDecodeError` | 24 | plan, typed marks, Unit Progress, rename, dependency order, the three `--stage` scenarios, the gate rows ×9, generation ×3, rejection ×4 | The frame's `run` (`runs` in the Unit Progress scenario) shows returncode 2, stdout `''`, and stderr exactly `earnest: unsupported route: units-generation is on the route, so per-unit stages` plus a trailing newline |
| `AssertionError` on `!= 2` in a Given | 2 | per-stage gate, unit-end | The same stderr |
| `AssertionError` on the findings set | 5 | check, shared regression, U3 row, unreadable table ×2 | The actual results carry no `stage` |
| `AssertionError` on stderr | 4 | refusal ×4 | stderr is the unsupported-route line |

- **What makes RED invalid:** an import, collection, missing-step or fixture error, or any count that differs from this table. If scenarios change before T1 lands, recount first.
- **Expected at the same point:**
  - `test_stage_status.py`: 26 passed.
  - `test_trace_check.py`: passes.
  - The new fixture tests: pass.

## 4. Tasks (RED test first in each; Herdsman implementers; one writer per file)

| Task | Code (`plan.py` unless noted) | Tests written red first |
| --- | --- | --- |
| T0 | §2, except 03(a); commit docs only | `docs-lint` |
| T1 | §3.1 fixture.<br>`sarif.py` helpers.<br>`conftest.py`: `_leave_out(root, *paths)` ignore, `fixture_repo` (leaves out `change`, `units`), `units_repo` (copytree with that ignore plus the base record directory, then copytree `units/aidlc` into the copy), the moved steps, and the record-relative exact step.<br>The feature and step module.<br>The §2.5 feature and step edits | `test_seeded_change.py`: `test_base_copy_leaves_the_units_directory_out`, `test_units_variant_replaces_only_the_record_directory` (no base `code-generation/`, one state file, base `src/` and `tests/`, no `FUTURE-FORMAT.md`), `test_units_requirements_are_a_byte_copy_of_the_base`, `test_units_bookkeeping_and_table_hold_no_item_tag_or_near_miss`, `test_units_fixture_lines_sit_where_the_scenarios_read_them` (also pins, before the edit, line 14 `Delivers: req~rate-limit~1` and line 21 `Depends: unit~u1~1` of `unit-of-work.md`); then RED (§3.4) |
| T2 | `parse_units` (fences via `adapters.markdown.scan`), raw read in `load` through `_read` (None = unusable), `_join_findings` | `test_parse_units_reads_the_first_unfenced_unit_id_and_directory_table`, `test_parse_units_flags_unreadable_repeated_and_unsafe_rows` (`..`, `a/b`, `` `u1` ``, `U 1`, a slug used as a directory, a repeated name or directory → the later row), `test_missing_symlinked_or_headerless_table_is_a_route_mismatch_at_units_generation`, `test_unit_item_without_row_is_flagged_with_or_without_a_table`, `test_row_without_unit_item_is_flagged_and_expands_nothing`, `test_table_is_read_only_with_units_generation_on_the_route` |
| T3 | Unexpanded route `executed`; `unit_order(directory, index)` (stdlib `heapq` ready set by name, unresolved units appended by name), shared by the expansion and `properties`; expansion, `_slug` (rpartition, replacing the seven `partition("/")` sites), `produces` from `executed`, the per-unit `in_tree` rule, `select_stage`.<br>Delete `_UNSUPPORTED`, `Intent.unsupported`, `UNSUPPORTED_ROUTE`, `select_intent`.<br>`cli.py`: `find_intent`; no skip notes; the stale `cli.main` and `PlanError` docstrings drop their per-unit refusal text | `test_each_for_each_slug_expands_once_per_unit[five slugs]`, `test_shared_slugs_stay_single`, `test_unit_order_is_dependency_order_with_ties_by_code_point` (units a, b, c with a depending on c → `b, c, a`; `u10` before `u2`), `test_unit_order_puts_a_cycle_last_by_name` (a↔b, plus a self-dependency x→x, plus a free unit d → `d, a, b, x`), `test_unit_order_puts_an_unknown_dependency_last_by_name` (entries that count as unknown: an id with no item, a `task`, a `unit` of another intent), `test_unit_order_puts_units_blocked_by_an_unresolved_unit_last_by_name` (a depends on unknown zz; c depends on a; b is free → `b, a, c`), `test_expansion_follows_unit_order_and_skips_units_without_a_row` (a unit with no row is still listed, with directory null), `test_unitless_audited_skip_removes_a_per_unit_slug_for_every_unit`, `test_unit_scoped_skip_skips_nothing`, `test_produces_reads_the_unexpanded_route`, `test_in_tree_keeps_per_unit_files_without_a_table`, `test_select_stage_takes_a_per_unit_id_and_refuses_a_unit_name`; the §2.5 re-points |
| T4 | `_gate_keys`, `_generation`, `_approval`, `_named` | `test_gate_keys_per_stage_unit_end_merge_and_unknown`, `test_gate_stages_split_like_items`, `test_unit_end_needs_every_listed_stage_on_the_units_lane_and_is_current_on_the_union`, `test_generation_is_the_highest_counting_row_per_unit_of_any_scope`, `test_missing_generation_is_zero_and_invalid_approves_nothing_and_raises_no_maximum`, `test_generation_two_on_another_stage_voids_generation_one`, `test_rejection_voids_its_key_else_its_slug_for_its_unit_or_every_unit`, `test_restart_and_jump_void_per_unit_rows_for_every_unit`, `test_named_items_follow_counting_per_unit_approvals`; M2 approval tests unchanged |
| T5 | `Plan.frontiers`, `_lane`, `_position`, `_gap_stage`, `_unplanned` | `test_each_unit_has_its_own_frontier`, `test_a_units_error_is_not_ahead_because_another_units_frontier_is_earlier`, `test_shared_stage_after_units_is_ahead_until_every_unit_is_approved`, `test_gap_placement_holding_then_lowest_lexical_valid_delivering_then_lowest_lexical_valid_unit`, `test_needs_with_no_unit_count_against_units_generation`, `test_unplanned_lowest_lexical_valid_delivering_unit_then_lowest_lexical_valid_unit_code_generation`; both reverse `Depends:` and assert the same stage and position as the name-ordered fixture, and both include an invalid-row or no-row unit that must own no fallback |
| T6 | `unit_done`, units in `properties` in unit order (tasks stay sorted by id), `reporter._intent_lines` | `test_unit_done_needs_a_row_dependencies_a_task_and_every_task_done`, `test_unresolved_unit_is_not_done` (cycle, unknown entry, blocked), `test_properties_list_units_in_unit_order_and_tasks_by_id`; the §2.5 reporter test |
| T7 | Every §5 gate green on the implementation SHA, then an independent review in the Manager's confirmed project-local harness, not built-in standalone review sessions. The Manager's assignment confirms UD6 is in effect; the PENDING status in `decisions.md` is historical. The harness receipt must be supplied before execution; the gates schema is as §5 cites it. Repairs stay within §6 | — |
| T8 | Only after T7's review verdict: apply 03(a) and commit, run every §5 gate on that final SHA, and record the SHA | — |

Before committing `docs/superpowers/plans/2026-10-14-unit-status.md`, replace machine-specific absolute paths with repository-relative or project-root placeholders and `result:` refs with durable local evidence references; the harness resolves gate cwd values to the actual one. The untracked coordination draft keeps its absolute paths and result refs unchanged.

Traceability from scenarios to requirements, code and tasks:

| Scenarios | Requirements | Code | Tasks |
| --- | --- | --- | --- |
| plan, typed marks, Unit Progress, rename | UC7; SC1, SC8 | `parse_units`, `intent`, `build`, `properties`, `_intent_lines` | T2, T3, T6 |
| dependency order | UC7; SC8 | `unit_order`, the expansion, `properties`, `_intent_lines` | T3, T6 |
| check, shared regression, ahead stage check | UC7; SC8 | `_lane`, `_position`, `_gap_stage`, `_unplanned` | T5 |
| unreadable table, U3 row | SC8 | `load`, `_join_findings`, `produces`, `in_tree` | T2, T3 |
| u1 and u2 stage checks, refusal | SC8, SC9 | `select_stage`, `cli._stage`, `header` | T3 |
| per-stage gate, gate rows, unit-end, generation, rejection | UC9; SC8, SC9 | `_gate_keys`, `_generation`, `_approval`, `_named` | T4 |

## 5. Gates (WT = `<repo>`)

The JSON below is the value of the harness input `gates`.

```json
{"bdd":[
{"id":"bdd-unit-status","argv":["uv","run","pytest","tests/steps/test_unit_status.py"],"cwd":"<repo>/packages/earnest"}
],"checks":[
{"id":"test","argv":["make","-C","packages/earnest","test"],"cwd":"<repo>","kind":"regression"},
{"id":"bdd-stage-status","argv":["uv","run","pytest","tests/steps/test_stage_status.py"],"cwd":"<repo>/packages/earnest","kind":"regression"},
{"id":"bdd-trace-check","argv":["uv","run","pytest","tests/steps/test_trace_check.py"],"cwd":"<repo>/packages/earnest","kind":"regression"},
{"id":"lint","argv":["make","-C","packages/earnest","lint"],"cwd":"<repo>","kind":"lint"},
{"id":"docs-lint","argv":["pnpm","dlx","markdownlint-cli2","docs/design/01-logic-design.md","docs/design/02-structural-design.md","docs/design/03-implementation-plan.md","docs/design/04-bdd-test-plan.md","docs/superpowers/plans/2026-10-14-unit-status.md"],"cwd":"<repo>","kind":"lint"},
{"id":"build","argv":["make","-C","packages/earnest","build"],"cwd":"<repo>","kind":"build"}
]}
```

- **Schema:** `{bdd:[{id,argv,cwd}],checks:[{id,argv,cwd,kind}]}`, as the Manager cites from `milestone.workflow.ts:36,187–194` on another branch; not independently read. `bdd` entries carry no `kind`.
- **Sources:** the argv, cwd and targets come from the package `Makefile` and `ci.yml`, both read only.
- **Order:**
  - The `test` check's `install` prerequisite, `uv sync --all-extras` from `uv.lock`, puts the `dev` extra into `.venv`. It, or a harness preflight that confirms the extra, must precede `bdd` and every `uv run pytest` check; the harness's order between `bdd` and `checks` is not independently known.
  - Run before that sync, a bare `uv run pytest` does an inexact sync without that extra and could resolve a system `pytest`.
  - A harness preflight may confirm the existing deps instead, then run the exact BDD gate. The BDD gate is never dropped or replaced.
- **Network, tools and side effects:**
  - `uv sync` may download locked packages, and `pnpm dlx` fetches markdownlint-cli2, as CI does. That approves no tool install, provider change, settings change or new spend.
  - Missing network or tools → the gate is `blocked`, never substituted.
  - The gates write `.venv`, `.pytest_cache`, `coverage.xml`, `dist/` and the pnpm cache.
- **Evidence rules:**
  - The Manager's harness checks §1 `scope.paths`, a clean tree and the final SHA, so the former `clean`, `scope` and `head` gates are dropped.
  - Every gate runs on the final (T8) SHA.
  - No gate result is claimed before approval.
- **Exit capture:**
  - If the harness executes `argv` itself, it records that process's exit code and nothing wraps it.
  - If a managed agent runs a gate in a shell, it runs `rtk proxy <argv>` when `rtk` is on PATH (otherwise the bare argv) and records the gate argv, the wrapper argv and the wrapper's own `$?`.
  - Never a pipeline's exit code. The wrapper doesn't replace the gate.

## 6. Harness limits

`{"maxRepairs":3,"maxInvalidReports":3}`. Three is enough for one mechanical repair and one design repair; more than that means the plan is wrong. The run stops in these cases:

| Condition | Status |
| --- | --- |
| The repair or invalid-report limit is used up | `exhausted` |
| A path outside §1 is touched, or a semantic change is unapproved | `needs_approval` |
| A gate cannot run | `blocked` |

Status names as the Manager cites them from the harness; not independently read. There are no silent retries. Publication happens only under UD1 with `merge:false`, and is never inferred.

## 7. Review dispositions (the plan review of rev 1)

| # | Disposition | Where |
| --- | --- | --- |
| 1 | fixed | P1, P3, P7; 01(j); unreadable-table outline; T2/T3; `test_cli` re-points |
| 2 | adopted, H | P5; generation outline; T4 |
| 3 | fixed | 01(j) gate paragraph; P4, P6 |
| 4 | fixed | §1 JSON, with `sarif.py` |
| 5 | fixed | §2 title and tags |
| 6 | fixed (disclosed) | §5 kinds; §6 names unverified |
| 7 | fixed | §3.4, recounted for 34 |
| 8 | fixed | T3: the five slugs, single slugs, skips |
| 9 | fixed | §2.5 exact names and re-points |
| 10 | not met; size needs Manager acceptance (actual final byte count in handoff) | writer reports `wc -c`; the Manager decides |
| 11 | fixed | Unit Progress scenario edit is uncommitted (same SHA) |
| 12 | proposed, H | P2: name order; positions independent of it |
| 13 | fixed | P1; 01(j); T2, T5 |
| 14 | adopted, H | P6; rejection outline |
| 15 | proposed, H | H1; 01(j), 01(n); ahead stage-check scenario; 03 M7 |
| 16 | fixed | §2 line anchors, pre-wrapped |
| 17 | fixed | 04 text cites 01 sections only |
| 18 | fixed | P9; T1 drift and no-item tests |
| 19 | fixed | §5 order and dependency note |
| 20 | fixed | §5 exit capture |
| 21 | proposed risk, H | H2; 01(j) |
| 22 | fixed | helpers including `HASH_LINE` in `sarif.py`; only steps in `conftest.py` |
| 23 | fixed | `FUTURE-FORMAT.md`; 01(b); 02(c) |

Round 2 NEEDS_REVISION (the plan review of rev 2). B1–B4 fixed per reviewer; listed optional text fixes adopted. Reviewer stated semantics hold and the artifact is approvable for human decision after these fixes and the Manager's size acceptance, without another semantic review. Size aim remains unmet; no implementation approval.

### Rev 3 amendment (2026-10-14)

| Change | Source | Where |
| --- | --- | --- |
| P2 → UD11: dependency order, code-point ties, unresolved units last by name; reversed-dependency scenario; order unit tests | m09555 | §0; 01(d), (j), (m); 03(c); §3.2–3.4; T3, T5, T6; traceability |
| H1 → UD12; H3 → UD13; P5, P6, H2 → UD14, as proposed | m09555 | §0; §2 tags |
| Gates split into `bdd` and `checks`; `clean`, `scope`, `head` moved to the harness; statuses `exhausted`, `needs_approval`, `blocked` | Manager | §5, §6 |
| Size about 57.5 KB accepted | Manager | header |

Superseded: the "H" markers in rows 2, 12, 14, 15 and 21 (now UD14, UD11, UD14, UD12, UD14); row 10's "size needs Manager acceptance" and the round-2 "Size aim remains unmet" (accepted); the rev 2 gate list and exit names. Other dispositions stand. A fresh delta review of rev 3 follows.

### Rev 3 delta review (2026-10-14)

Delta review of rev 3 (the rev 3 delta review): NEEDS_REVISION, text only; a focused confirmation of the fixes follows and nothing is approved. Checked by reading, not running: the UD11 unit order and its T3 cases; the reversed-dependency scenario (no cycle; stages, approvals, units and tasks as tabled); fixture lines 14 and 21; the RED recount, 35 = 13 + 22 split 24/2/5/4 (derived, not run); and the §5/§6 schema, kinds, statuses and limits.

Fixed after it: F1, the Manager chose Remedy B (Remedy A not adopted): the `gap` and `unplanned` fallbacks pick the lowest-named unit with a valid row, 01:573-576 is revised to match (01(o), proposed for formal approval), and T5 is renamed; F2, T7 cites the §5 schema; F3, 01(j) notes that a task or cross-intent `Depends:` entry raises no finding of its own; F4, the reversed-dependency step matches lines by content and T1 pins lines 14 and 21 before the edit; F5, wording in 03(c) and §5. Other dispositions stand. Size exception accepted by the Manager (57.5 KB earlier; the rev 3 actual size is reported in the handoff). Nothing implemented or approved.

### Rev 3 final confirmation (2026-10-14)

Focused confirmation (the rev 3 final confirmation) of Remedy B and F2–F5, by
reading only; nothing run. NEEDS_REVISION, text only. Fixed after it,
verbatim from the review: G1, 01(o) applies on a route that holds
`units-generation`, names the Code Generation stage of the lowest-named unit
with a valid row, and reads the route without a Code Generation stage before
the per-unit expansion, so the unreadable-table `unplanned` row at Units
Generation holds and M2 routes are unchanged; G2, the P2 approval cell marks
its fallback clause as the proposed UD11 consequence. Confirmed: the 01(o)
anchor 573–576 (577 continues unchanged); B placement is independent of
`Depends:` order, and units with no row or an invalid row own no fallback;
no exact BDD table changes; F2–F5 applied; counts unchanged at 35 = 13 + 22,
split 24/2/5/4 (derived, not run). With G1 and G2 applied verbatim the plan
is approvable for human plan approval without another review. Remedy B
remains a proposed consequence for formal approval, not a user decision.
Limits: harness schema and statuses as the Manager cites them, not
independently read; nothing implemented or approved.
