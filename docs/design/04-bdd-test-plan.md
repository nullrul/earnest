# 04 — BDD Test Plan

Status: draft, derived from `03-implementation-plan.md`, September 2026.

This document holds the behavior that gates each milestone of
`03-implementation-plan.md`. Behavior is the primary gate
([[three-tier-testing-behavior-integration-unit-with-behavior-as-primary-gate]]):
a milestone exits when its Gherkin feature runs green, and its scenarios are
written here before its code ([[write-gherkin-before-code-not-after]]).
Scenarios speak the domain language of `01-logic-design.md`, its actors, items,
links and findings, and describe what the repo maintainer and the coding agent
observe at the command-line boundary
([[gherkin-scenarios-should-describe-behavior-not-ui-mechanics]]). Each scenario
asserts success criteria of `00-project-intent.md` and names them in its title.

## Tiers

| Tier | Where, under `packages/earnest/tests/` | What it proves |
| --- | --- | --- |
| Behavior | `features/<milestone>.feature`, bound by `steps/test_<milestone>.py` | the milestone's exit behavior at the command-line boundary, over a fixture repository |
| Integration | `integration/test_<flow>.py` | two or more modules wired over a committed repository, with real files and Git |
| Unit | `unit/test_<module>.py` and `unit/adapters/test_<language>.py` | one module behind its interface, with the edge cases its plan's Review Focus names |

- A milestone signs off when its feature runs green under its exit command,
  `uv run pytest tests/steps/test_<milestone>.py` in `packages/earnest/`, and
  the unit and integration tiers run green under `make test`.
- One runner, pytest, runs all three tiers; pytest-bdd binds each feature to the
  step module of the same snake_case slug (L5 of `02`).
- A fixture repository is plain files, and `tests/conftest.py` builds its Git
  history in a temporary directory at test time (L6 of `02`).
- `make test` reports coverage, and no coverage threshold applies for now.

## Scenarios, milestones and features

Each milestone of `03` exits on one feature, and each feature reads one fixture
repository. The success criteria column copies the Spec coverage line of each
milestone in `03`.

| Milestone | Feature | Step module | Fixture | Success criteria |
| --- | --- | --- | --- | --- |
| M1 `trace_check` | `trace_check.feature` | `test_trace_check.py` | `broken-links` | SC1, SC2, SC3 (untraced and traced), SC10 (message text) |
| M2 `stage_status` | `stage_status.feature` | `test_stage_status.py` | `seeded-change` | SC1, SC5, SC8 (stage and task status), SC9 (run header) |
| M2b `unit_status` | `unit_status.feature` | `test_unit_status.py` | `seeded-change` (units variant) | SC1, SC8 (unit and per-unit stage status), SC9 (per-unit run header) |
| M3 `task_change` | `task_change.feature` | `test_task_change.py` | `seeded-change` | SC6, SC7 |
| M4 `judge_check` | `judge_check.feature` | `test_judge_check.py` | `seeded-change` | SC3 (judged), SC4 (warning), SC11 |
| M5 `evidence_check` | `evidence_check.feature` | `test_evidence_check.py` | `seeded-change`, and its units variant | SC3 (in full), SC8 (done) |
| M6 `calibration_gate` | `calibration_gate.feature` | `test_calibration_gate.py` | `calibration` | SC4 |
| M7 `aidlc_fork` | `aidlc_fork.feature` | `test_aidlc_fork.py` | `seeded-change`, with a fork checkout | SC9 |
| M8 `typescript_evidence` | `typescript_evidence.feature` | `test_typescript_evidence.py` | a TypeScript fixture, named when M8 is next | SC3 for TypeScript |

The scenarios of M7 and M8 are added here when each milestone's plan is written; M6's section is below.

## How scenarios are written

- Before the code: the first task of a milestone's plan copies its scenarios
  from here into the feature file verbatim, and the exit command stays red until
  the plan's last task.
- Actors: steps name the actors of the Actors and use cases section of `01`, the
  repo maintainer and the coding agent.
- Behavior in the domain's words: a step says what an actor does or observes,
  such as "When the coding agent runs earnest check" or "Then the SARIF log
  holds exactly these findings". The SARIF log on stdout, the summary on stderr
  and the exit code are the command's contract (D13), so steps read them, and
  name no module, function or option parser.
- Exact tables: a table of expected findings lists every one, so a missing or an
  extra finding fails the scenario, and SC2's 100% reads as an equality.
- Known defects: a `Background` names the fixture repository and who shaped it,
  and the fixture seeds each defect its feature names at a known file and line
  ([[e2e-test-plan-uses-real-sample-mrs-with-known-defects-as-golden-fixtures]]).
- Fixed for the loop: once a milestone's loop starts, its scenarios change only
  through a revision of this document that the maintainer ratifies, as its goal
  does in `03` ([[goals-must-be-immutable-during-execution]]).

## M1 `trace_check`

- Feature: `packages/earnest/tests/features/trace_check.feature`, bound by
  `tests/steps/test_trace_check.py`.
- Fixture: `tests/fixtures/broken-links/`, one commit with a broken link of
  every kind across Markdown, Python, TypeScript and Gherkin, and no plan, so
  every finding reaches no stage.

### What `broken-links` seeds

| File | Line | Seeded text | Finding |
| --- | --- | --- | --- |
| `docs/plan.md` | 7 | `Delivers: req~Rate-Limit~1` | `near-miss`, a key-line id with an uppercase name |
| `docs/plan.md` | 8 | `Depends: task~set_up~1` | `near-miss`, a malformed id that fits no named pattern |
| `docs/plan.md` | 10 | `` `task~notify~1` Tell the member when to try again `` | `near-miss`, text after the id |
| `docs/plan.md` | 16 | `**Delivers:** req~audit-log~1` | `near-miss`, a key not written exactly |
| `docs/plan.md` | 17 | `Depends: task~wire-limiter~1,` | `near-miss`, an empty entry |
| `docs/plan.md` | 19 | `` `tsk~expire~1` `` | `near-miss`, an unknown type |
| `docs/requirements.md` | 11 | `req~lockout-notice~2`, with no `utest` | `gap` |
| `docs/requirements.md` | 18 | `req~session-expiry~1`, with no `Covers:` line | `orphaned`, an item that covers no parent |
| `docs/requirements.md` | 22 | `Needs: impl utest` | `near-miss`, a list separated by a space |
| `docs/requirements.md` | 24 | `` `req~remember-me` `` | `near-miss`, an id line without its revision |
| `docs/requirements.md` | 28 | `req~audit-log~1`, with no `utest` | `gap` |
| `docs/requirements.md` | 32 | `Covers: feat~sign-in~2, FR1.2` | `predated` for the first entry, `near-miss` for the AI-DLC id |
| `docs/requirements.md` | 34 | `req~audit-log~1` a second time | `duplicate` |
| `docs/scope.md` | 9 | `feat~password-reset~1`, with no `req` and no `stest` | two `gap` findings |
| `src/auth.py` | 16 | `[impl->req~rate-limt~1]` | `orphaned`, naming `req~rate-limit~1` as the closest id |
| `src/auth.py` | 19 | `[impl-req~audit-log~1]` | `near-miss`, the missing `>` |
| `tests/sign_in.feature` | 9 | `@stest feat~sign-in~1` | `near-miss`, an `@` tag without `:` |
| `tests/sign_in.feature` | 15 | `@stest:feat~Password-Reset~1` | `near-miss`, an uppercase name |
| `tests/test_auth.py` | 13 | `[itest->req~rate-limit~1]` | `unwanted`, at warning level |
| `web/login.ts` | 3 | `[impl->req~lockout-notice~1]` | `outdated`, as the item is at revision 2 |
| `web/login.ts` | 13 | `[impl->req~lockout-notice]` | `near-miss`, a tag without its revision |

Two requirements, `req~rate-limit~1` and `req~session-expiry~1`, each have an
`impl` and a `utest` cover at their current revision, so two of the four
requirements are traced, 50%. The `utest` cover of `req~session-expiry~1`, on
line 12 of `tests/test_auth.py`, is the spaced tag
`[ utest -> req~session-expiry~1 ]`, which OFT's whitespace rule makes valid.
The `//` inside a string on line 15 of `web/login.ts`, and the `@smoke` tag in
`tests/sign_in.feature`, raise nothing.

### Feature

```gherkin
Feature: Trace check
  Before it asks for approval, the coding agent runs earnest check and learns,
  from the output alone, every broken link in the chain with its file and line,
  and the trace level each requirement reached (UC1, UC2; SC1, SC2, SC3, SC10).

  Background:
    Given the repo maintainer's "broken-links" repository, with a broken link of every kind

  Scenario: Two checks of an unchanged repository write the same SARIF log (SC1)
    When the coding agent runs earnest check twice
    Then both runs write the same SARIF log

  Scenario: Every seeded broken link is a finding at its file and line (SC2)
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule              | file                  | line |
      | earnest/near-miss | docs/plan.md          | 7    |
      | earnest/near-miss | docs/plan.md          | 8    |
      | earnest/near-miss | docs/plan.md          | 10   |
      | earnest/near-miss | docs/plan.md          | 16   |
      | earnest/near-miss | docs/plan.md          | 17   |
      | earnest/near-miss | docs/plan.md          | 19   |
      | earnest/gap       | docs/requirements.md  | 11   |
      | earnest/orphaned  | docs/requirements.md  | 18   |
      | earnest/near-miss | docs/requirements.md  | 22   |
      | earnest/near-miss | docs/requirements.md  | 24   |
      | earnest/gap       | docs/requirements.md  | 28   |
      | earnest/near-miss | docs/requirements.md  | 32   |
      | earnest/predated  | docs/requirements.md  | 32   |
      | earnest/duplicate | docs/requirements.md  | 34   |
      | earnest/gap       | docs/scope.md         | 9    |
      | earnest/gap       | docs/scope.md         | 9    |
      | earnest/orphaned  | src/auth.py           | 16   |
      | earnest/near-miss | src/auth.py           | 19   |
      | earnest/near-miss | tests/sign_in.feature | 9    |
      | earnest/near-miss | tests/sign_in.feature | 15   |
      | earnest/unwanted  | tests/test_auth.py    | 13   |
      | earnest/outdated  | web/login.ts          | 3    |
      | earnest/near-miss | web/login.ts          | 13   |
    And every finding is in scope at position current, with no stage
    And every finding carries the trace observation behind it

  Scenario: Every finding names the change that fixes it (SC10)
    When the coding agent runs earnest check
    Then each finding at these places names its fix:
      | file                  | line | fix                                                                   |
      | docs/plan.md          | 7    | lower-case the name                                                   |
      | docs/plan.md          | 8    | rewrite it as `type~name~revision`                                    |
      | docs/plan.md          | 10   | put the id alone on its line and move the text into the body          |
      | docs/plan.md          | 16   | write the key exactly as `Delivers: `                                 |
      | docs/plan.md          | 17   | name at least one id, separated by `, `, with no empty entry          |
      | docs/plan.md          | 19   | use a known item type, such as `task`                                 |
      | docs/requirements.md  | 11   | tag a unit test that verifies it with `[utest->req~lockout-notice~2]` |
      | docs/requirements.md  | 18   | add a `Covers:` line naming the `feat` it derives from                |
      | docs/requirements.md  | 22   | name at least one id, separated by `, `, with no empty entry          |
      | docs/requirements.md  | 24   | append `~` and the item's current revision                            |
      | docs/requirements.md  | 28   | tag a unit test that verifies it with `[utest->req~audit-log~1]`      |
      | docs/requirements.md  | 32   | so `FR1.2` becomes `req~fr1-2~1`                                      |
      | docs/requirements.md  | 32   | write `feat~sign-in~1`, or bump the item                              |
      | docs/requirements.md  | 34   | already defined at docs/requirements.md:28                            |
      | docs/scope.md         | 9    | add a `req` item with `Covers: feat~password-reset~1`                 |
      | docs/scope.md         | 9    | tag a scenario that verifies it with `@stest:feat~password-reset~1`   |
      | src/auth.py           | 16   | did you mean `req~rate-limit~1`?                                      |
      | src/auth.py           | 19   | write `->` between the artifact type and the id                       |
      | tests/sign_in.feature | 9    | put `:` between the artifact type and the id                          |
      | tests/sign_in.feature | 15   | lower-case the name                                                   |
      | tests/test_auth.py    | 13   | use a type it needs, or add `itest` to its `Needs:` line              |
      | web/login.ts          | 3    | check the change, then write `req~lockout-notice~2`                   |
      | web/login.ts          | 13   | append `~` and the item's current revision                            |

  Scenario: Each requirement lands at exactly one trace level (SC3)
    When the coding agent runs earnest check
    Then the SARIF log gives each requirement one trace level:
      | requirement          | level    |
      | req~audit-log~1      | untraced |
      | req~lockout-notice~2 | untraced |
      | req~rate-limit~1     | traced   |
      | req~session-expiry~1 | traced   |
    And each untraced requirement has a located finding that names it
    And the SARIF log gives the traced percentage as 50
    And the summary leads with "traced 50%, judged 0%, evidenced 0%; requirements: 4"

  Scenario: An error-level finding in scope fails the check (SC2)
    When the coding agent runs earnest check
    Then the check exits non-zero, with the SARIF log on stdout
```

## M2 `stage_status`

- Feature: `packages/earnest/tests/features/stage_status.feature`, bound by
  `tests/steps/test_stage_status.py`.
- Fixture: `tests/fixtures/seeded-change/`, an AI-DLC-shaped repository. Its base
  commit holds an intent's record directory
  (`aidlc/spaces/default/intents/260926-checkout/`) with a state file, a sharded
  audit log, three requirements, two tasks, Python code and tests carrying tags,
  and one approval for the requirements stage. Its `change/` overlay is the
  second commit, on the branch `task/add-limiter-window`, named after an
  existing task: one revision bump and one silent edit. M2 passes no `--task`,
  the base state file names no current task, and Earnest never reads the
  branch, so the out-of-task check and impact of M3 add nothing to M2's
  scenarios (the Out-of-task rule of `01`).
- Success criteria asserted: SC1, SC5, SC8 (stage and task status), SC9 (run
  header).

Every scenario reads a route, a state file and audit rows from the fixture. Their
shapes follow upstream AI-DLC at commit `fe563195d827`; the `Assessment Hash`,
`Items` and `Approved By` fields of the approval rows are the fork's additions
(the Fork delta of `02`), and the fixture carries them.

### What `seeded-change` seeds

The profile is `bugfix`, a Greenfield record. The state file is abridged:
upstream lists every compiled stage and the template's other sections, and only
the Stage Progress rows are read. Its rows mark the three initialization stages
EXECUTE (outside the route, as they hold no gate); `reverse-engineering`,
`deployment-pipeline` and `deployment-execution` EXECUTE with the skipped mark
`[S]` and an audited `STAGE_SKIPPED` row each (runtime skips); and
`units-generation` SKIP (planned by scope). The route is the EXECUTE rows
outside the initialization phase, less the audited skips:
`inception/requirements-analysis`, `construction/code-generation`,
`construction/build-and-test`. The profile has no Ideation and no Units
Generation (Stages in `01`). The chain root is `req`, so no `Covers:` line is
needed.

Base commit, record directory `aidlc/spaces/default/intents/260926-checkout/`
(inside the sensor's `matches`):

| File | Line | Seeded text | Role |
| --- | --- | --- | --- |
| `aidlc/spaces/default/intents/260926-checkout/aidlc-state.md` | 6 | `- **Scope**: bugfix` | the profile; M2 parses it and does not display it |
| `aidlc/spaces/default/intents/260926-checkout/aidlc-state.md` | 11-14 | `### INITIALIZATION PHASE`, then `- [x] workspace-scaffold — EXECUTE: always`, `workspace-detection`, `state-init`, in that order | auto-proceeding stages with no gate, outside the route |
| `aidlc/spaces/default/intents/260926-checkout/aidlc-state.md` | 16-19 | `### INCEPTION PHASE`, then `- [S] reverse-engineering — EXECUTE: greenfield project`, `- [x] requirements-analysis — EXECUTE: always`, `- [S] units-generation — SKIP: not in bugfix scope` | a runtime skip, a route stage, a planned skip |
| `aidlc/spaces/default/intents/260926-checkout/aidlc-state.md` | 21-23 | `### CONSTRUCTION PHASE`, then `- [x] code-generation — EXECUTE: always`, `- [x] build-and-test — EXECUTE: always` | agent-written marks that Earnest never reads as status |
| `aidlc/spaces/default/intents/260926-checkout/aidlc-state.md` | 25-27 | `### OPERATION PHASE`, then `- [S] deployment-pipeline — EXECUTE: no pipeline change`, `- [S] deployment-execution — EXECUTE: no pipeline change` | runtime skips |
| `aidlc/spaces/default/intents/260926-checkout/audit/fixture-a1b2c3d4.md` | 1-6 | a `WORKFLOW_STARTED` block (Timestamp 2026-09-26T09:00:00Z, Scope bugfix, Request), closed by `---` on line 6 | the attempt boundary |
| `aidlc/spaces/default/intents/260926-checkout/audit/fixture-a1b2c3d4.md` | 7-13 | a `STAGE_SKIPPED` block (Timestamp 2026-09-26T09:10:00Z; Stage `reverse-engineering`; Reason; Skip Kind `conditional-runtime`), closed by `---` on line 13 | the audited skip |
| `aidlc/spaces/default/intents/260926-checkout/audit/fixture-a1b2c3d4.md` | 14-27 | two more `STAGE_SKIPPED` blocks, `deployment-pipeline` at 09:20:00Z (lines 14-20) and `deployment-execution` at 09:21:00Z (lines 21-27) | the audited skips; the order is synthetic and does not follow a real run |
| `aidlc/spaces/default/intents/260926-checkout/audit/fixture-a1b2c3d4.md` | 28-36 | a `GATE_APPROVED` block (Timestamp 2026-09-26T10:00:00Z; Stage `requirements-analysis`; User Input; Assessment Hash `sha256:` and 64 zeros; Items `req~audit-log~1, req~lockout-notice~1, req~rate-limit~1`; Approved By `human`), closed by `---` on line 36 | the requirements stage's approval. The hash is a placeholder because currentness reads the items alone; the last three fields are the fork's |
| `aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md` | 3 | `` `req~rate-limit~1` ``, body on lines 5-6 | traced; bumped by the overlay |
| `aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md` | 8 | `` `req~lockout-notice~1` ``, body on lines 10-11 (`...shall tell the member` / `when they may try again.`) | traced; edited without a bump by the overlay |
| `aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md` | 13 | `` `req~audit-log~1` ``, body on line 15 | traced, delivered by no task: `unplanned` |
| `aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md` | 3, 5 | `` `task~add-limiter~1` ``, body `Add a limiter that counts failed logins in a window.` | the plan |
| `aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md` | 7 | `Delivers: req~rate-limit~1` | the edge the bump leaves at the old revision |
| `aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md` | 9, 11 | `` `task~notify-lockout~1` ``, body `Tell the member when the lockout starts.` | the plan |
| `aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md` | 13-14 | `Delivers: req~lockout-notice~1` and `Depends: task~add-limiter~1` | the plan; the dependency a scenario closes into a cycle |
| `src/checkout/auth.py` | 4, 9, 14 | `# [impl->req~rate-limit~1]`, `# [impl->req~lockout-notice~1]`, `# [impl->req~audit-log~1]` | the `impl` covers; line 4 is the tag the bump leaves at the old revision |
| `tests/test_auth.py` | 4, 9, 14 | `# [utest->req~rate-limit~1]`, `# [utest->req~lockout-notice~1]`, `# [utest->req~audit-log~1]` | the `utest` covers; line 4 is the tag the bump leaves at the old revision |

At the base commit all three requirements are traced and one finding exists,
`unplanned` on line 13 of `requirements.md`. The requirements stage has a
current approval and no error, so it is done. The code-generation stage has no
approval and its tasks are not done (no requirement is at level evidenced before
M5), so it is the frontier. A requirement is unplanned when no task's
`Delivers:` names it, and a tag reaches a stage through the task that delivers
what it covers.

The `change/` overlay, the second commit on the branch
`task/add-limiter-window`, a name that is fixture mechanics only, as Earnest
reads no branch:

| File | Line | Change | Finding |
| --- | --- | --- | --- |
| `aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md` | 3, 5-6 | `req~rate-limit~1` becomes `req~rate-limit~2`, and the body now says thirty minutes | the bump: leaves the approval, the `Delivers:` edge and both tags at revision 1 |
| `aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md` | 11 | the line now reads `how long the lockout lasts.` and the id line stays `req~lockout-notice~1` | `unbumped-change`, given a record written before the change |

After the change the approval no longer matches the stage's items, so the
requirements stage is the frontier again. Findings in the code-generation stage
then sit ahead of the frontier and read as notes that name where the work is
expected. SC5 holds all the same: each place is flagged in the same run.

### Readings the scenarios pin

Each reading is a choice that the docs leave open or imply. A scenario that
rests on one inherits it.

| Reading | Basis |
| --- | --- |
| A task's `Delivers:` counts whatever the revision, so no `unplanned` fires for `req~rate-limit~2` after the bump | the Findings table of `01` says "delivered by no task" and does not mention revision; M1's `gap` lookup is revision-blind |
| A tag or edge at an old revision reaches the code-generation stage through a task that delivers the same type and name | Stages in `01` |
| `unbumped-change` is located at the item's id line | M1 locates item findings at the id line, and so do approval findings |
| The `outdated` findings that a bump in an approved earlier stage causes are position `ahead` (level note) until that stage is re-approved | Frontier and position and Revision lifecycle in `01`, read together |
| A stale stage approval is an `outdated` finding at level note, at its stage's position; the latest counting `GATE_APPROVED` row is the stage's approval | the Findings table and Frontier and position in `01` |
| A hash is held per id and revision, replaced until a counting approval row names it, then frozen; `unbumped-change` fires only when a counting row names the id and revision, and a held hash that no counting row names is no baseline | Revision lifecycle in `01` |

### Stage status feature

```gherkin
Feature: Stage status
  The coding agent and the repo maintainer read where the work stands from the
  command output alone: the route with each stage's computed status, its
  approval and the frontier; the assessment hash that a stage check prints and
  records; and, after a revision bump, every place left at the old revision
  (UC4, UC7, UC9; SC1, SC5, SC8, SC9).

  Background:
    Given the repo maintainer's "seeded-change" repository at its base commit, with the requirements stage approved

  Scenario: The plan prints the route, each stage's status, its approval and the frontier (SC8)
    When the coding agent runs earnest plan
    Then the plan lists these stages in route order:
      | stage                           | status   | approval       |
      | inception/requirements-analysis | done     | current, human |
      | construction/code-generation    | not done | none           |
      | construction/build-and-test     | not done | none           |
    And the frontier is "construction/code-generation"
    And the plan lists these tasks:
      | task                  | status   |
      | task~add-limiter~1    | not done |
      | task~notify-lockout~1 | not done |
    And the plan lists neither the initialization stages nor the stages skipped by scope or by an audited skip
    And the summary names each stage with its status and approval, and the frontier

  Scenario: A status someone typed is not read (SC8)
    When the coding agent runs earnest plan
    Then "construction/code-generation" is "not done" although the state file marks it complete

  Scenario: The plan changes nothing in the repository (SC8)
    When the coding agent runs earnest plan
    Then the repository is unchanged
    And no assessment record exists

  Scenario: Two plans of an unchanged repository write the same SARIF log (SC1)
    When the coding agent runs earnest plan twice
    Then both runs write the same SARIF log

  Scenario: A requirement that no task delivers is flagged in scope at the frontier (SC8)
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule              | file                                                                                         | line | level   | position | stage                        |
      | earnest/unplanned | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 13   | warning | current  | construction/code-generation |
    And the finding names "req~audit-log~1" and says that no task delivers it
    And the check exits zero

  Scenario: Tasks that wait on each other are a cycle in scope at the frontier (SC8)
    Given the repo maintainer makes "task~add-limiter~1" wait on "task~notify-lockout~1", which already waits on it
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule              | file                                                                                              | line | level   | position | stage                        |
      | earnest/cycle     | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 3    | error   | current  | construction/code-generation |
      | earnest/unplanned | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | warning | current  | construction/code-generation |
    And the cycle finding lists "task~add-limiter~1 -> task~notify-lockout~1 -> task~add-limiter~1"
    And the check exits non-zero

  Scenario: The stage check prints the assessment hash and writes the run header (SC9)
    When the coding agent runs earnest check --stage "construction/code-generation"
    Then the summary prints the assessment hash
    And the SARIF log gives the same hash and the stage status "not done"
    And the run header for "construction/code-generation" in the assessment record holds:
      | field  | value                                     |
      | commit | the repository's HEAD commit              |
      | dirty  | false                                     |
      | layers | trace                                     |
      | items  | task~add-limiter~1, task~notify-lockout~1 |
      | hash   | the hash the summary printed              |
    And Git lists no new file
    And the check exits zero

  Scenario: Two stage checks of an unchanged repository print the same hash (SC1)
    When the coding agent runs earnest check --stage "construction/code-generation" twice
    Then both runs print the same assessment hash
    And both runs write the same SARIF log

  Scenario: An uncommitted edit gives a new hash and is recorded as dirty (SC9)
    Given the coding agent has run earnest check --stage "construction/code-generation"
    And the coding agent has an uncommitted edit to "src/checkout/auth.py"
    When the coding agent runs earnest check --stage "construction/code-generation"
    Then the assessment hash differs from the first run's
    And the run header records the same commit as dirty

  Scenario: What the maintainer's approval adds to the audit log leaves the hash as it was (SC9)
    Given the coding agent has run earnest check --stage "construction/code-generation"
    And the repo maintainer approves "construction/code-generation" at the gate
    When the coding agent runs earnest check --stage "construction/code-generation"
    Then the assessment hash equals the first run's
    And the run header records the repository as not dirty

  Scenario: After a revision bump every place left at the old revision is flagged (SC5)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer's change is committed on a task branch
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule                    | file                                                                                              | line | level | position | stage                           |
      | earnest/unbumped-change | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | error | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note  | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note  | ahead    | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | note  | ahead    | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | note  | ahead    | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note  | ahead    | construction/code-generation    |
    And the finding at requirements.md line 3 names the approval of "inception/requirements-analysis" and the current revision 2
    And the check exits non-zero

  Scenario: After the bump the requirements stage waits for a fresh approval (SC5, SC8)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer's change is committed on a task branch
    When the coding agent runs earnest plan
    Then the plan lists these stages in route order:
      | stage                           | status   | approval |
      | inception/requirements-analysis | not done | outdated |
      | construction/code-generation    | not done | none     |
      | construction/build-and-test     | not done | none     |
    And the frontier is "inception/requirements-analysis"

  Scenario: The stage that awaits its fresh approval passes its own check (SC5, SC9)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer's change is committed on a task branch
    And the repo maintainer restores the approved text of "req~lockout-notice~1"
    When the coding agent runs earnest check --stage "inception/requirements-analysis"
    Then the SARIF log holds exactly these findings:
      | rule             | file                                                                                         | line | level | position | stage                           |
      | earnest/outdated | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 3    | note  | current  | inception/requirements-analysis |
    And the SARIF log gives the stage status "not done" with its approval "outdated"
    And the check exits zero

  Scenario: A fresh approval replaces the old one and the work list moves into scope (SC5, SC8)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer's change is committed on a task branch
    And the repo maintainer restores the approved text of "req~lockout-notice~1"
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    When the coding agent runs earnest plan
    Then the plan lists these stages in route order:
      | stage                           | status   | approval       |
      | inception/requirements-analysis | done     | current, human |
      | construction/code-generation    | not done | none           |
      | construction/build-and-test     | not done | none           |
    And the frontier is "construction/code-generation"

  Scenario: After a fresh approval the findings left at the old revision are in scope at the next stage (SC5)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer's change is committed on a task branch
    And the repo maintainer restores the approved text of "req~lockout-notice~1"
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule              | file                                                                                              | line | level   | position | stage                        |
      | earnest/outdated  | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | error   | current  | construction/code-generation |
      | earnest/outdated  | src/checkout/auth.py                                                                              | 4    | error   | current  | construction/code-generation |
      | earnest/outdated  | tests/test_auth.py                                                                                | 4    | error   | current  | construction/code-generation |
      | earnest/unplanned | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | warning | current  | construction/code-generation |
    And the check exits non-zero

  Scenario: A held hash that no approval names is no baseline (SC5)
    Given the coding agent has run earnest check --stage "construction/code-generation"
    And the coding agent has an uncommitted edit to the body of "task~notify-lockout~1"
    When the coding agent runs earnest check
    Then the SARIF log holds no earnest/unbumped-change finding

  Scenario: A stage check before the approval replaces the held hash (SC5)
    Given the coding agent has run earnest check --stage "construction/code-generation"
    And the coding agent has an uncommitted edit to the body of "task~notify-lockout~1"
    When the coding agent runs earnest check --stage "construction/code-generation"
    Then the SARIF log holds no earnest/unbumped-change finding
    And the record holds a different body hash for "task~notify-lockout~1" than the first run held

  Scenario: A missing record is stated, not silent (SC5)
    When the coding agent runs earnest check
    Then the summary states that the record is absent and the body-hash baseline is unavailable

  Scenario: A rejected gate after an approval reopens the stage (SC8)
    Given the audit log gains a GATE_REJECTED row for "requirements-analysis" after its approval
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "none"
    And the frontier is "inception/requirements-analysis"

  Scenario: An approval from before a workflow restart does not count (SC8)
    Given the audit log gains a WORKFLOW_STARTED row after the approval
    And the audit log gains a fresh STAGE_SKIPPED row after the restart for each stage the state file marks skipped
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "none"
    And the frontier is "inception/requirements-analysis"

  Scenario: The audit shards of two clones are read as one log (SC8)
    Given the requirements approval sits in a second shard "fixture-0000aaaa.md", which sorts before the first shard, written later than the first shard's WORKFLOW_STARTED row
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "current, human"

  Scenario: An approval row without the fork's fields counts and never goes stale (SC8)
    Given the approval row names no Assessment Hash, Items or Approved By
    And the repo maintainer's change is committed on a task branch
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "current"
    And the frontier is "construction/code-generation"

  Scenario: A stage marked skipped with no audited skip stays on the route and is flagged (SC8)
    Given the state file marks "deployment-pipeline" as skipped and the audit log holds no skip row for it
    When the coding agent runs earnest check
    Then the SARIF log holds exactly one earnest/route-mismatch finding, at the "deployment-pipeline" row of the state file, naming the audit row that is missing
    And the plan lists "operation/deployment-pipeline" among the stages
    And the check exits non-zero

  Scenario: A backward jump resets the approval of its target stage (SC8)
    Given the audit log gains a STAGE_JUMPED row with direction BACKWARD and target "requirements-analysis" after the approval
    And the state file resets the marks of every later stage marked EXECUTE to pending
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "none"
    And the frontier is "inception/requirements-analysis"
    And the plan lists "operation/deployment-pipeline" and "operation/deployment-execution" among the stages

  Scenario: A forward jump leaves approvals standing (SC8)
    Given the audit log gains a STAGE_JUMPED row with direction FORWARD and target "build-and-test" after the approval
    And the audit log gains a STAGE_SKIPPED row of kind jump for "code-generation", which the state file marks skipped
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "current, human"
    And the plan does not list "construction/code-generation"
    And the frontier is "construction/build-and-test"

  Scenario: A rejected approval freezes no body hash (SC5)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the audit log gains a GATE_REJECTED row for "requirements-analysis" after its approval
    And the coding agent has an uncommitted edit to the body of "req~lockout-notice~1"
    When the coding agent runs earnest check
    Then the SARIF log holds no earnest/unbumped-change finding
```

### Notes for the task plan

- Shared steps: "the SARIF log holds exactly these findings:" compares only the
  columns a table gives (M1 gives `rule`, `file`, `line`), and "both runs write
  the same SARIF log" and "the check exits non-zero" move to `tests/conftest.py`
  (`02` places steps that two features share there). The new `When` steps set
  the fixture name `runs` or `run` as M1's do. "The repo maintainer approves …
  at the gate" appends a `GATE_APPROVED` row whose `Items` are the header's.
- Builder: `conftest.py` builds the base commit on `main`, and a separate step
  commits the `change/` overlay on `task/add-limiter-window`, because scenarios
  run `check --stage` between the two commits to write the baseline.
- The summary prints `record: absent, body-hash baseline unavailable` whenever
  the record is missing and the index holds items; scenario "A missing record is
  stated, not silent" pins the line, and its wording is part of this section.
- Jumps: upstream voids no audit row, so the rule that a row counts only after
  the latest `WORKFLOW_STARTED` and every BACKWARD or REDO jump that resets its
  stage is Earnest's. Scenario "A forward jump leaves approvals standing" has
  `code-generation` off the route, so its task items belong to no route stage;
  the unit tier pins the position of their findings (stage-less, position
  current, as in a run with no plan for that stage).
- Intents: `plan.py` reads `aidlc-state.md` and `audit/*.md` by raw read,
  because the scanner skips them; `--stage` accepts the sensor's bare
  `stage_slug` or `<phase>/<slug>`, and `--intent` names the record. A `--stage`
  that names no stage on the route, or an ambiguous bare slug, exits 2 with one
  line (a unit-tier test).
- M3 and these tables: the out-of-task check and impact run only with a
  current task and a change baseline (the Out-of-task rule of `01`). The base
  state file names no current task and no scenario here passes `--task`, so
  no table of M2 holds an `out-of-task` or `impact-degraded` row, although
  `change/` edits prose on a branch named `task/add-limiter-window`. Earnest
  never reads that branch; it is fixture mechanics. An earlier revision of M3
  read the branch and added eleven rows to three of these tables; the
  maintainer's decision that no check runs against Git branches removed them.
- Messages carry the change to make (T6, SC10): the `outdated` note at
  `requirements.md` line 3 names the stage to re-approve; `unbumped-change` names
  "bump the revision to 2, or restore the text"; `unplanned` names "add a `task`
  that delivers it". The wording is the plan's to fix; the scenarios assert the
  places and the facts above.
- Unit and integration tiers cover what the feature leaves out: the Region rule
  over `Source.code_lines` (tag to next tag, stacked tags, repeated tags for one
  id), `Approved By: automatic` rows, a repository with several record
  directories, the record's `RecordError` for a corrupt or newer file with exit
  2, the record's atomic write, and the import check that `reporter` imports
  neither `structural` nor `plan`. Unit status and `Depends:` between units
  belong to M2b: the M2 route has no Units Generation.
- Regression guard: `broken-links` has no record directory, and M1's scenarios
  stay green only while every finding there keeps position `current` with no
  stage.

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

- Notes: "holds exactly these findings in the intent's record:" compares
  every result in the log; only the `file` column has the intent record prefix
  removed. A result outside the record keeps its full path and fails the step.
  `-` in an outline omits that field; table, unit-order, generation and rejection cases
  beyond the feature are unit-tier tests.

## M3 `task_change`

- Feature: `packages/earnest/tests/features/task_change.feature`, bound by
  `tests/steps/test_task_change.py`.
- Fixture: `tests/fixtures/seeded-change/`. The base commit of M2 gains the two
  base-file additions below. The task change is M2's `change/` overlay with
  the `task/` overlay committed on top of it. The `task/` overlay changes
  three lines of `src/checkout/auth.py`.
- Success criteria asserted: SC6, SC7. Readings: the Out-of-task rule and
  the Impact rule in `01`, with D11 and D12.

The out-of-task check and impact run only with a current task and a change
baseline. The current task comes from `--task`, or else from the state file's
`Current Task` line. The baseline is the commit of the last approved stage
check that the record holds. Earnest reads no Git branch, by the maintainer's
decision. M3's own cases have their own tables here. Without a current task,
or without a baseline, nothing of M3 appears beyond one summary line, so M2's
scenarios, whose state file names no current task, keep their tables. The
rules read changed Markdown prose as they read code, so with a current task
M2's `change/` overlay also raises out-of-task and `impact-degraded`
findings, and M3's tables hold the rows of both overlays.

### What `seeded-change` adds for M3

At the base commit the per-test coverage contexts give the known dependencies
of SC7. Each test calls the code its tag covers, and `test_audit_lockout` also
calls `count_failed_logins`, so the coverage map and the tags select different
tests for line 6.

| File | Line | Seeded text | Role |
| --- | --- | --- | --- |
| `pytest.ini` | 1-2 | `[pytest]`, `pythonpath = src` | lets the map run import `checkout`; raises no finding |
| `tests/test_auth.py` | 2 | `from checkout.auth import audit_lockout, count_failed_logins, lockout_message` | at collection, outside every test context |
| `tests/test_auth.py` | 6 | `assert count_failed_logins(3) == 3` | covers `src/checkout/auth.py` line 6 under `test_count_failed_logins` |
| `tests/test_auth.py` | 11 | `assert lockout_message().startswith("Try again")` | covers line 11 under `test_lockout_message` |
| `tests/test_auth.py` | 16 | `assert audit_lockout(str(count_failed_logins(1))) == "1"` | covers lines 6 and 16 under `test_audit_lockout` |

Code lines are shown without their indentation. The tag lines 4, 9 and 14 of
both files stay where M2 seeds them, and the base findings of M2 and M2b are
unchanged.

The `task/` overlay, `task/src/checkout/auth.py`, is committed on top of
`change/`. The current task in most scenarios is `task~add-limiter~1`
(`Delivers: req~rate-limit~1`, read on type and name):

| File | Line | Change | Finding |
| --- | --- | --- | --- |
| `src/checkout/auth.py` | 2 | the blank line becomes `LIMIT = 5`, before the first tag, in no tag region | `out-of-task`, and `impact-degraded`, reaching no stage |
| `src/checkout/auth.py` | 6 | `return min(window, LIMIT)`, in the region of the tag on line 4, which `change/` leaves at `req~rate-limit~1` | none: the region is already reported `outdated`, and lies inside the task; impact selects `test_count_failed_logins` and `test_audit_lockout` from the map |
| `src/checkout/auth.py` | 11 | `return "Try again in fifteen minutes."`, in the `req~lockout-notice~1` region | `out-of-task`; impact selects `test_lockout_message` |

The rows that `change/` adds with a current task and a baseline:

| File | Line | Change | Finding |
| --- | --- | --- | --- |
| `…/inception/requirements-analysis/requirements.md` | 3 | the id line `req~rate-limit~2` | `impact-degraded`; no `out-of-task`, as the stale-approval `outdated` note lies on the line |
| `…/inception/requirements-analysis/requirements.md` | 5 | the body says thirty minutes | `out-of-task` and `impact-degraded` |
| `…/inception/requirements-analysis/requirements.md` | 11 | the body says how long the lockout lasts | `out-of-task` and `impact-degraded` |

The prose `impact-degraded` findings count against
`inception/requirements-analysis`, the stage whose artifact holds the line.
A scenario records its baseline with a stage check of
`inception/requirements-analysis` on `main` and a fresh approval of it at the
gate, whose row copies the run header's hash; the seeded approval row's
placeholder hash matches no header. That stage check holds the requirements'
body hashes, and the approval freezes them, so the body edit of `change/`
raises M2's `unbumped-change` error at line 8 in M3's tables, and those checks
exit non-zero. The baseline is the base commit, so the diff and the coverage
map are those of the base.

### Readings the M3 scenarios pin

| Reading | Basis |
| --- | --- |
| The diff since the change baseline runs to the work tree, untracked files included, so uncommitted work counts, and the work tree may be on any branch or none | UC3 ("about to commit"), the Runtime and permission model, and the Out-of-task rule in `01` (the maintainer's decision: no check against Git branches) |
| The out-of-task check and impact read changed lines only in files the scanner reads, the evaluated tree. An appended audit row or a state-file edit raises nothing | a region exists only in a scanned source, and `02` keeps skipped files out of the evaluated tree (maintainer decision i) |
| A changed region is a tag region that holds a changed line, or one hunk of changed lines outside every tag region, Markdown prose included; its finding is located at its first changed line | the Region rule read strictly, with prose kept in scope as `01` stands (maintainer decisions a and R1h′) |
| A region is already reported `outdated` when an `outdated` finding is located on one of its lines, the stale-approval note included | D11 in `01` |
| An `out-of-task` finding counts against the stage that holds the current task, at position current, so its message opens `in scope at construction/code-generation` even while that stage is ahead | Frontier and position in `01`: "current: … the current task" |
| `impact-degraded` is one note per changed line in no tag region, blank lines included. A line in a stage artifact counts against that stage, taking that stage's position; a code or test line in no tag region reaches no stage | the Impact rule in `01`, read literally (maintainer decisions R1h′ and ii); M2's placement of a finding in a stage artifact |
| The first two exits clear the finding: a region whose tags a task item added in the diff delivers, on type and name, is not out-of-task, and the hunk that adds the task item raises none; the finding stands after a declared block | the Out-of-task rule in `01` (E1, as the maintainer re-derived it) |
| A modified line is seen through the base line its diff hunk pairs it with; an added line beyond the pairing is one the map never saw | the Impact rule and D12 in `01` |
| A test tag matches a requirement on type and name, so `[utest->req~rate-limit~1]` still selects its test after the bump | the Out-of-task rule's revision-blind matching, and M2's reading of `Delivers:` |
| The impacted requirements are those the tags of the changed tag regions name, at their current revision; the features are the `feat` items they cover, none on the `bugfix` route, whose chain root is `req` | the Impact rule and Stages in `01` (E2) |
| Tests are named by pytest node id, the per-test context with its phase suffix dropped | pytest-cov's `--cov-context=test` |
| The full suite is every test the coverage map holds a context for; when impact selects the full suite with no map, `properties.impact` records `tests` as `[]` with `degraded` true, and the summary says so explicitly, as `tests: the full suite` | D12 in `01` (Lead decision) |
| A change that only deletes lines forms no region and raises no `out-of-task`; deleting another requirement's code is a known limit | the Out-of-task rule in `01`, read literally (Lead decision) |
| A line deleted since the baseline selects the tests that covered it in the baseline's map; with no such data (no map for the baseline, or no context for the line in that map) it raises `impact-degraded` at the line the deletion follows, naming its baseline line, and selects the full suite. No table here deletes a line | the Impact rule in `01` (Manager decision) |
| A file deleted since the baseline, whose path the scanner would read, is read whole as deleted lines; its `impact-degraded` notes sit at line 1 of the deleted path, a deleted stage artifact counting against its stage and deleted code reaching no stage. A deleted audit shard or state file raises nothing, and no deleted file raises `out-of-task` | the Impact rule in `01` (Lead decision) |
| Only the hunk of a task item that delivers one of the changed regions' tags is the proposal; a hunk adding a task that delivers none is out-of-task | the Out-of-task rule in `01`: "the hunk that adds such a task item" |
| A line can lie in two tag regions, when the regions of one id merge across another tag's group; each changed region is then its own finding, read on its own tags | the Region rule in `01`, read literally |
| `out-of-task` and `impact-degraded` stay out of the assessment document, so the hash of a stage check is the same whether a current task, a baseline or a coverage map exists | the Assessment hash section of `01` |
| A stage check of a dirty work tree, or a map run that times out, ends with pytest exit code 2 to 5 or leaves no data, takes no map; the summary names the cause and the record's `coverage` stays as it was | the Impact rule in `01` |
| The current task is `--task`, else the one `- **Current Task**:` line of an intent's state file, under `## Project Information`, naming a task of that intent on type and name; no such line, several, or a value naming no task gives no current task and one summary line | the Out-of-task rule in `01`, a marker the maintainer ratified: AI-DLC's state file is the stage state Earnest already reads raw, outside the evaluated tree, so moving the task changes no hash and no diff |
| The change baseline is the `commit` of the run header of the stage, current or outdated in its approval, whose approval row's `Assessment Hash` equals its header's `hash`, taking the latest such row in audit order; the seeded approval row's placeholder hash matches no header, so a scenario records a baseline by a stage check and a fresh approval at the gate. No baseline, or a commit Git no longer holds, gives one summary line | the Out-of-task rule in `01` (the maintainer's decision), read through the record's run headers and the audit rows as M2 keeps them |
| Without a current task, or without a baseline, the check holds no `out-of-task` or `impact-degraded` finding, no `properties.impact` and no impact section, and the reason is a summary line, not a SARIF result | the Out-of-task and Impact rules in `01`: impact runs with the out-of-task check, as the baseline belongs to the current task's intent |

### Task change feature

```gherkin
Feature: Task change
  Working on its current task, the coding agent learns from the check alone
  which regions changed since the last approved stage check lie outside the
  task, with the three ways out of each, and which requirements, features and
  tests the change impacts, flagged when a changed line has no coverage data.
  Earnest reads no Git branch (UC3, UC6; SC6, SC7).

  Background:
    Given the repo maintainer's "seeded-change" repository at its base commit, with the requirements stage approved

  Scenario: The stage check takes the coverage map and leaves Git's listing as it was (SC7)
    When the coding agent runs earnest check --stage "construction/code-generation"
    Then the assessment record gives the repository's HEAD commit as the coverage map's commit
    And the coverage map for that commit is kept under ".earnest/coverage/"
    And the run header for "construction/code-generation" gives the layers "trace"
    And Git lists no new file

  Scenario: Each changed region since the approved stage check that lies outside the task is flagged, prose and code alike (SC6)
    Given the coding agent's state file names "task~add-limiter~1" as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coding agent's task change is committed
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule                    | file                                                                                              | line | level   | position | stage                           |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | note    | ahead    | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note    | ahead    | construction/code-generation    |
      | earnest/unbumped-change | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | error   | current  | inception/requirements-analysis |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | note    | current  | inception/requirements-analysis |
      | earnest/out-of-task     | src/checkout/auth.py                                                                              | 2    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | src/checkout/auth.py                                                                              | 11   | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | src/checkout/auth.py                                                                              | 2    | note    | current  | -                               |
    And the check exits non-zero

  Scenario: An out-of-task finding names the task and offers exactly three exits (SC6)
    Given the coding agent's state file names "task~add-limiter~1" as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coding agent's task change is committed
    When the coding agent runs earnest check
    Then each earnest/out-of-task finding names "task~add-limiter~1" and offers exactly these exits:
      | exit                                         |
      | tag it under a requirement the task delivers |
      | propose a task                               |
      | declare it blocked                           |
    And the summary lists every out-of-task finding with its exits

  Scenario: Tagging the region under a requirement the task delivers clears its finding (SC6)
    Given the coding agent's state file names "task~add-limiter~1" as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coding agent's task change is committed
    And the coding agent tags line 2 of "src/checkout/auth.py" under "req~rate-limit~2", uncommitted
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule                    | file                                                                                              | line | level   | position | stage                           |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | note    | ahead    | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note    | ahead    | construction/code-generation    |
      | earnest/unbumped-change | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | error   | current  | inception/requirements-analysis |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | note    | current  | inception/requirements-analysis |
      | earnest/out-of-task     | src/checkout/auth.py                                                                              | 11   | warning | current  | construction/code-generation    |
    And the check exits non-zero

  Scenario: Proposing a task that delivers the region's requirement clears its finding (SC6)
    Given the coding agent's state file names "task~add-limiter~1" as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coding agent's task change is committed
    And the coding agent proposes the task "task~tell-wait~1", delivering "req~lockout-notice~1", in the plan, uncommitted
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule                    | file                                                                                              | line | level   | position | stage                           |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | note    | ahead    | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note    | ahead    | construction/code-generation    |
      | earnest/unbumped-change | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | error   | current  | inception/requirements-analysis |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | note    | current  | inception/requirements-analysis |
      | earnest/out-of-task     | src/checkout/auth.py                                                                              | 2    | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | src/checkout/auth.py                                                                              | 2    | note    | current  | -                               |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 15   | note    | ahead    | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 16   | note    | ahead    | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 17   | note    | ahead    | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 18   | note    | ahead    | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 19   | note    | ahead    | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 20   | note    | ahead    | construction/code-generation    |
    And the SARIF log's plan lists "task~tell-wait~1" as "not done"

  Scenario: Declaring the change blocked leaves the repository and the finding as they were (SC6)
    Given the coding agent's state file names "task~add-limiter~1" as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coding agent's task change is committed
    And the coding agent declares the change at line 11 of "src/checkout/auth.py" blocked, in a message to the maintainer
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule                    | file                                                                                              | line | level   | position | stage                           |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | note    | ahead    | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note    | ahead    | construction/code-generation    |
      | earnest/unbumped-change | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | error   | current  | inception/requirements-analysis |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | note    | current  | inception/requirements-analysis |
      | earnest/out-of-task     | src/checkout/auth.py                                                                              | 2    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | src/checkout/auth.py                                                                              | 11   | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | src/checkout/auth.py                                                                              | 2    | note    | current  | -                               |
    And the repository is unchanged since the task change

  Scenario: The state file's current task is the task the check reads (SC6)
    Given the coding agent's state file names "task~notify-lockout~1" as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coding agent's task change is committed
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule                    | file                                                                                              | line | level   | position | stage                           |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | note    | ahead    | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note    | ahead    | construction/code-generation    |
      | earnest/unbumped-change | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | error   | current  | inception/requirements-analysis |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | note    | current  | inception/requirements-analysis |
      | earnest/out-of-task     | src/checkout/auth.py                                                                              | 2    | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | src/checkout/auth.py                                                                              | 2    | note    | current  | -                               |
    And each earnest/out-of-task finding names "task~notify-lockout~1"

  Scenario: The task named on the command line wins over the state file (SC6)
    Given the coding agent's state file names "task~add-limiter~1" as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coding agent's task change is committed
    When the coding agent runs earnest check --task "task~notify-lockout~1"
    Then the SARIF log holds exactly these findings:
      | rule                    | file                                                                                              | line | level   | position | stage                           |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | note    | ahead    | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note    | ahead    | construction/code-generation    |
      | earnest/unbumped-change | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | error   | current  | inception/requirements-analysis |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | note    | current  | inception/requirements-analysis |
      | earnest/out-of-task     | src/checkout/auth.py                                                                              | 2    | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | src/checkout/auth.py                                                                              | 2    | note    | current  | -                               |
    And each earnest/out-of-task finding names "task~notify-lockout~1"

  Scenario Outline: With no single current task the check reports nothing of the task change (SC6, SC7)
    Given the coding agent's state file names <marked> as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coding agent's task change is committed
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule                    | file                                                                                              | line | level | position | stage                           |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note  | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note  | ahead    | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | note  | ahead    | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | note  | ahead    | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note  | ahead    | construction/code-generation    |
      | earnest/unbumped-change | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | error | current  | inception/requirements-analysis |
    And the summary states once that there is no current task
    And the summary prints no impact section
    And the SARIF log carries no impact

    Examples:
      | marked                                                |
      | no task                                               |
      | both "task~add-limiter~1" and "task~notify-lockout~1" |

  Scenario: With no approved stage check recorded the check reports nothing of the task change (SC6, SC7)
    Given the coding agent's state file names "task~add-limiter~1" as the current task
    And the coding agent has run earnest check --stage "construction/code-generation"
    And the coding agent's task change is committed
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule              | file                                                                                              | line | level | position | stage                           |
      | earnest/outdated  | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note  | current  | inception/requirements-analysis |
      | earnest/outdated  | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note  | ahead    | construction/code-generation    |
      | earnest/outdated  | src/checkout/auth.py                                                                              | 4    | note  | ahead    | construction/code-generation    |
      | earnest/outdated  | tests/test_auth.py                                                                                | 4    | note  | ahead    | construction/code-generation    |
      | earnest/unplanned | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note  | ahead    | construction/code-generation    |
    And the summary states once that no approved stage check is recorded
    And the summary prints no impact section
    And the SARIF log carries no impact

  Scenario: An uncommitted change is diffed against the commit the approved stage check recorded (SC6)
    Given the coding agent's state file names "task~add-limiter~1" as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coding agent's task change is left uncommitted on main
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule                    | file                                                                                              | line | level   | position | stage                           |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | note    | ahead    | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note    | ahead    | construction/code-generation    |
      | earnest/unbumped-change | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | error   | current  | inception/requirements-analysis |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | note    | current  | inception/requirements-analysis |
      | earnest/out-of-task     | src/checkout/auth.py                                                                              | 2    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | src/checkout/auth.py                                                                              | 11   | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | src/checkout/auth.py                                                                              | 2    | note    | current  | -                               |
    And the check exits non-zero

  Scenario: The impact section names the requirements, features and tests to run, from the coverage map (SC7)
    Given the coding agent's state file names "task~add-limiter~1" as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coding agent's task change is committed
    And the coding agent restores the requirements, and lines 2 and 11 of "src/checkout/auth.py", to their base text, uncommitted
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule              | file                                                                                         | line | level   | position | stage                        |
      | earnest/unplanned | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 13   | warning | current  | construction/code-generation |
    And the summary's impact section reads:
      | field        | value                                                                                |
      | requirements | req~rate-limit~1                                                                     |
      | features     | none                                                                                 |
      | tests        | tests/test_auth.py::test_audit_lockout, tests/test_auth.py::test_count_failed_logins |
      | degraded     | no                                                                                   |
    And the SARIF log carries the same impact

  Scenario: A changed line with no coverage data selects the full suite and says so (SC7)
    Given the coding agent's state file names "task~add-limiter~1" as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coding agent's task change is committed
    When the coding agent runs earnest check
    Then the summary's impact section reads:
      | field        | value                                                                                                                          |
      | requirements | req~lockout-notice~1, req~rate-limit~2                                                                                         |
      | features     | none                                                                                                                           |
      | tests        | tests/test_auth.py::test_audit_lockout, tests/test_auth.py::test_count_failed_logins, tests/test_auth.py::test_lockout_message |
      | degraded     | yes                                                                                                                            |
    And the SARIF log carries the same impact
    And each earnest/impact-degraded finding says impact selected the full suite

  Scenario: Without a coverage map a changed line selects the tests tagged to its requirement (SC7)
    Given the coding agent's state file names "task~add-limiter~1" as the current task
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    And the coverage maps under ".earnest/coverage/" are gone
    And the coding agent's task change is committed
    And the coding agent restores the requirements, and lines 2 and 11 of "src/checkout/auth.py", to their base text, uncommitted
    When the coding agent runs earnest check
    Then the summary's impact section reads:
      | field        | value                                        |
      | requirements | req~rate-limit~1                             |
      | features     | none                                         |
      | tests        | tests/test_auth.py::test_count_failed_logins |
      | degraded     | no                                           |
    And the summary states that no coverage map exists for the baseline commit
```

### Notes for the M3 task plan

- Shared steps: "the SARIF log holds exactly these findings:" also reads a
  `stage` column of `-` as a finding that carries no `properties.stage`.
  "the coding agent has run earnest check --stage …", "the repo maintainer
  approves … at the gate" and "the check exits zero" and "non-zero" are
  already shared. The steps new to M3 live in `tests/steps/test_task_change.py`.
- The current task: "the coding agent's state file names `<id>` as the
  current task" writes `- **Current Task**: <id>` as the last line of the
  state file's `## Project Information` section, uncommitted; "names no task"
  writes none, and "names both …" writes two such lines. The state file is
  skipped by the scanner, so the edit is neither dirty nor in the diff.
- Overlays and branches:
  - "the coding agent's task change is committed" commits `change/` (through
    M2's `commit_overlay`), then `task/` as a second commit, on
    `task/add-limiter-window`. The branch is fixture mechanics; Earnest never
    reads it, and no assertion depends on its name.
  - "… left uncommitted on main" writes both overlays' files into the work
    tree of `main`.
  - The base builder leaves `task/` out, as it does `change/` and `units/`.
- Edits:
  - "tags line 2 … under `req~rate-limit~2`" rewrites line 2 as
    `LIMIT = 5  # [impl->req~rate-limit~2]`, a trailing tag, so no line moves.
  - "restores the requirements, and lines 2 and 11 …, to their base text"
    writes the base `requirements.md` and the base lines back.
  - "proposes the task" appends six lines 15-20 to `code-generation-plan.md`: a
    blank line, `` `task~tell-wait~1` ``, a blank line,
    `Tell the member how long to wait.`, a blank line and
    `Delivers: req~lockout-notice~1`.
  - "declares … blocked" writes nothing to the repository.
  - "the coverage maps under `.earnest/coverage/` are gone" deletes the files
    the scenario's own stage check wrote there, and nothing else.
- The map run:
  - `check --stage` runs the repository's tests with the interpreter that runs
    Earnest, under pytest-cov with `--cov-context=test`.
  - Its data file is `.earnest/coverage/<commit>`, and Earnest's own options
    write nothing outside `.earnest/`: no `.pytest_cache`, no `__pycache__`, no
    `.coverage`, no log file. The repository's tests run under the test-suite
    trust model.
  - A failing test still gives a map.
  - The record's `coverage` is the commit, and the run header's `layers` stays
    `trace`. Impact reads the map of the baseline commit alone.
- Messages (T6, SC10):
  - `out-of-task` names the current task, the region's tags or "no tag", and
    the three exits in the order of the Out-of-task rule.
  - `impact-degraded` says that impact selected the full suite.
  - The summary's impact section is one line each for requirements, features,
    tests and degraded. When impact selects the full suite with no map, the
    tests line reads `tests: the full suite`, while `properties.impact`
    records `tests: []` and `degraded: true`.
  - Without a current task or a baseline the summary gives one line naming
    which is missing; it is no SARIF result.
  - The wording is the plan's to fix, and the scenarios assert the places and
    the facts above.
- The unit and integration tiers cover what the feature leaves out: a
  `Current Task` value that names no task, several intents each naming a task,
  a baseline from a per-unit stage, a later stage check that replaces the
  approved header, an approval row without `Assessment Hash`, a baseline
  commit Git no longer holds, several hunks in one file, deleted lines and
  files, a changed skipped file such as an audit shard, the full suite with no
  map, and the parse of the pytest-cov contexts.
- Regression guard:
  - M1, M2 and M2b gain no row: their state files name no current task.
  - M2's tables are those of `main`.

## M4 `judge_check`

- Feature: `packages/earnest/tests/features/judge_check.feature`, bound by
  `tests/steps/test_judge_check.py`.
- Fixture: `tests/fixtures/seeded-change/`. The base commit of M2 and M3 is
  unchanged. Two new overlays stack on it as commits on `main`: `override/`
  writes two `Override:` lines and a requirement that is not EARS, and
  `override-change/` bumps one overridden requirement and changes the code
  under the other. The canned verdicts of the stub model are the file
  `judge-verdicts.json`, which no commit holds.
- Success criteria asserted: SC3 (judged), SC4 (warning), SC11. Readings: the
  Grammar, the Override rule, the Process vocabulary, the Region rule, D2, D3
  and D14 in `01`, and the stub model of its Runtime and permission model.

The judge runs only with `--judge`, and in every M4 scenario it is the stub
model: the step sets `EARNEST_JUDGE` to `stub:` and the absolute path of the
canned-verdict file, so no network is reached and no key is needed. No
scenario of M1 to M3 passes `--judge`, so their tables are unchanged. The
EARS parse runs on every check, but every requirement those milestones seed
is one EARS sentence, so they raise no `req-not-ears`. The record holds no
calibration until M6, so every judge run here raises `judge-uncalibrated`.
No scenario names a current task, so the out-of-task check and impact stay
silent, and none reads a Git branch.

### What `seeded-change` adds for M4

The `override/` overlay is one file,
`…/inception/requirements-analysis/requirements.md`, committed on `main` on
top of the base commit. The base commit's short sha is `89f3937`; the conftest
pins its author, committer and dates, so it is the same on every run.

| Line | Text | Role |
| --- | --- | --- |
| 1 | `# Requirements` | as in the base |
| 3, 5-6 | `` `req~rate-limit~1` `` and its base body | EARS: response only |
| 8 | `Override: req~rate-limit~1 implemented at 89f3937, the gateway enforces the lockout; this code only counts the window.` | replaces the judge's `implemented` question for `req~rate-limit~1` |
| 10, 12-13 | `` `req~lockout-notice~1` `` and its base body | EARS: trigger and response |
| 15 | `Override: req~lockout-notice~1 implemented at 89f3937, the support desk approved "Try again later." as the wording.` | replaces the judge's `implemented` question for `req~lockout-notice~1` |
| 17 | `` `req~audit-log~1` `` | the id, at its base revision |
| 19 | `Lockouts go into the audit log.` | not EARS: no `shall`; `req-not-ears` at line 17 |

Lines 2, 4, 7, 9, 11, 14, 16 and 18 are blank. The base tags in
`src/checkout/auth.py` and `tests/test_auth.py` are unchanged, so every
requirement stays traced. No stage check runs before the overlay, so the
record holds no body hash and the edit of line 19 raises no
`unbumped-change`.

The `override-change/` overlay, committed on `main` on top of `override/`:

| File | Line | Change | Finding |
| --- | --- | --- | --- |
| `…/inception/requirements-analysis/requirements.md` | 3 | `req~rate-limit~2`, the body of lines 5-6 saying thirty minutes, as in M2's `change/` | M2's stale-approval and `outdated` rows; `override-expired` at line 8, whose override stays at revision 1 |
| `src/checkout/auth.py` | 11 | `return "Try again shortly."`, in the `req~lockout-notice~1` region | `override-drift` at line 15: the region changed since `89f3937` |

`judge-verdicts.json`, at the fixture's root, answers three questions. It
holds no answer for `req~rate-limit~1 implemented`, so a judge that asked an
overridden question would exit 2.

| Requirement | Question | Result | Reasoning | Location |
| --- | --- | --- | --- | --- |
| `req~rate-limit~1` | `tested` | `not-satisfied` | `test_count_failed_logins counts three failed logins and never reaches the fifth, so no lockout is asserted.` | `tests/test_auth.py` line 6 |
| `req~lockout-notice~1` | `implemented` | `not-satisfied` | `lockout_message returns a fixed text that never says when the member may try again.` | `src/checkout/auth.py` line 11 |
| `req~lockout-notice~1` | `tested` | `satisfied` | `test_lockout_message asserts that the message tells the member to try again.` | `tests/test_auth.py` line 11 |

### Readings the M4 scenarios pin

| Reading | Basis |
| --- | --- |
| `--judge` takes its model from `EARNEST_JUDGE`; `stub:<path>` answers from the canned-verdict file, keyed by requirement id and revision, then by question, with `result`, `reasoning` and `location` | the Runtime and permission model in `01` (the maintainer's decision) |
| The judge asks two questions of each traced requirement that parses as EARS: `implemented` of its `impl` regions and `tested` of its test regions, with the question text built from the clause spans. An untraced or unparsed requirement is asked nothing | D14 and D2 in `01`; the two questions match the two override kinds of the Override rule |
| An overridden question is not asked. Its override is the observation of record: method `inspection`, author `maintainer`, result `satisfied`, the override's reason as reasoning, located at the `Override:` line | the Process vocabulary and the Override rule in `01`: an override replaces the judge's observation for one item, revision and kind |
| The observations of record, one per question of each judged requirement, travel under the run's `properties.observations`, sorted by requirement and question; each has `method`, `subject`, `question`, `author`, `result`, `reasoning` and `location` | the SARIF 2.1.0 section of `01`, whose result observations carry method, subject, result, reasoning and location; `author` separates the judge's from the maintainer's, as the Process vocabulary does |
| `req-not-ears` is raised on every check, judge or not, at the requirement's id line, as an error; the requirement can still be traced | D2 in `01`; `ears.py` sits in the Assessor beside the trace layer (`02`) |
| `judge-not-satisfied` is one warning per not-satisfied observation of record, at the verdict's location when that lies in a region the question asked about, else at the requirement's id line; the finding carries the observation | the findings table and the Process vocabulary in `01` |
| `judge-uncalibrated` is one warning per judge run, located at line 1 of `.earnest/assessment.json`, whose `calibration` slot holds no passing result; it reaches no stage, and its message names the model id and the prompt hash | the Command surface in `01`: "every judge run raises `judge-uncalibrated`" |
| The stub's model id is `stub:sha256:` and the SHA-256 of the canned-verdict file; it and the prompt hash go into the judge cache key | the Runtime and permission model and the Process vocabulary in `01` |
| A requirement is judged when it is traced and each of its two questions is satisfied or overridden; the judged percentage counts it among all requirements, rounded down | the Trace levels table in `01`; M1's percentages |
| An override is read from the requirement's own item, and its `at` commit resolves through Git; its region is the requirement's regions of its kind: `impl` regions for `implemented`, test regions for `tested` | the Override rule and the Region rule in `01` |
| An override whose revision is not the item's current one raises `override-expired` at its `Override:` line and drops out of the verdict, and is not checked for drift | the Override rule in `01` |
| An override whose region changed between its commit and the work tree raises `override-drift` at its `Override:` line; the judge reruns the question, the override stays the observation of record, and the finding carries both observations, the override's and the rerun's. The rerun raises no `judge-not-satisfied` of its own | the Override rule and D3 in `01`: the override stands while the code holds still, and surfaces the moment it moves |
| `override-expired`, `override-drift` and `req-not-ears` count against the stage whose artifact holds their line | M2's placement of a finding in a stage artifact |
| `--judge` writes the record's `judge` slot, the judge cache; a second run with an unchanged key reuses the observations, and writes the same SARIF log | the Runtime and permission model and the Process vocabulary in `01` |

### Judge check feature

```gherkin
Feature: Judge check
  Against the stub model, the coding agent learns from the check which
  requirements are not EARS, which judge verdicts are weak, with the judge's
  reasoning and location, that the judge is uncalibrated, and how many
  requirements are judged. An override stands as the maintainer's observation
  until its revision expires or its code drifts (UC2, UC5; SC3, SC4, SC11).

  Background:
    Given the repo maintainer's "seeded-change" repository at its base commit, with the requirements stage approved
    And the repo maintainer's overrides are committed
    And the judge is the stub model with the canned verdicts of "seeded-change"

  Scenario: Against the stub model the judge check reports its findings (SC3, SC4)
    When the coding agent runs earnest check --judge
    Then the SARIF log holds exactly these findings:
      | rule                        | file                                                                                         | line | level   | position | stage                           |
      | earnest/req-not-ears        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 17   | error   | behind   | inception/requirements-analysis |
      | earnest/unplanned           | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 17   | warning | current  | construction/code-generation    |
      | earnest/judge-not-satisfied | tests/test_auth.py                                                                           | 6    | warning | current  | construction/code-generation    |
      | earnest/judge-uncalibrated  | .earnest/assessment.json                                                                     | 1    | warning | current  | -                               |
    And the check exits non-zero

  Scenario: A requirement that is not one EARS sentence is flagged with the five templates and never judged
    When the coding agent runs earnest check --judge
    Then the earnest/req-not-ears finding names "req~audit-log~1" and lists these templates:
      | template                                      |
      | The system shall response.                    |
      | When trigger, the system shall response.      |
      | While state, the system shall response.       |
      | If condition, then the system shall response. |
      | Where feature, the system shall response.     |
    And the SARIF log holds no observation of record for "req~audit-log~1"

  Scenario: A not-satisfied verdict is a warning with the judge's reasoning and location (SC3)
    When the coding agent runs earnest check --judge
    Then the earnest/judge-not-satisfied finding carries this observation:
      | field     | value                                                                                                       |
      | subject   | req~rate-limit~1                                                                                            |
      | question  | tested                                                                                                      |
      | method    | inspection                                                                                                  |
      | author    | judge                                                                                                       |
      | result    | not-satisfied                                                                                               |
      | reasoning | test_count_failed_logins counts three failed logins and never reaches the fifth, so no lockout is asserted. |
      | location  | tests/test_auth.py:6                                                                                        |
    And the summary lists the finding with its reasoning

  Scenario: A judge run with no passing calibration says so (SC4)
    When the coding agent runs earnest check --judge
    Then the earnest/judge-uncalibrated finding names the stub model's id and the prompt hash
    And the SARIF log gives the stub model's id and the prompt hash in the run's invocation

  Scenario: The judged percentage counts the requirements whose every question is satisfied or overridden (SC3)
    When the coding agent runs earnest check --judge
    Then the SARIF log gives each requirement one trace level:
      | requirement          | level  |
      | req~audit-log~1      | traced |
      | req~lockout-notice~1 | judged |
      | req~rate-limit~1     | traced |
    And the SARIF log gives the judged percentage as 33
    And the summary leads with "traced 100%, judged 33%, evidenced 0%; requirements: 3"

  Scenario: An override is the observation of record, and the judge is not asked its question (SC11)
    When the coding agent runs earnest check --judge
    Then the SARIF log holds exactly these observations of record:
      | subject              | question    | author     | result        | location                                                                                        |
      | req~lockout-notice~1 | implemented | maintainer | satisfied     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md:15 |
      | req~lockout-notice~1 | tested      | judge      | satisfied     | tests/test_auth.py:11                                                                           |
      | req~rate-limit~1     | implemented | maintainer | satisfied     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md:8  |
      | req~rate-limit~1     | tested      | judge      | not-satisfied | tests/test_auth.py:6                                                                            |
    And the observation of record for "req~rate-limit~1" "implemented" gives the reasoning "the gateway enforces the lockout; this code only counts the window."
    And the judge cache holds exactly these questions:
      | subject              | question |
      | req~lockout-notice~1 | tested   |
      | req~rate-limit~1     | tested   |

  Scenario: The judge cache answers a second run with the same log
    When the coding agent runs earnest check --judge twice
    Then both runs write the same SARIF log
    And the judge cache holds exactly these questions:
      | subject              | question |
      | req~lockout-notice~1 | tested   |
      | req~rate-limit~1     | tested   |

  Scenario: After the change commit an override at the old revision expires (SC11)
    Given the repo maintainer's change under the overrides is committed
    When the coding agent runs earnest check --judge
    Then the SARIF log holds exactly these findings:
      | rule                       | file                                                                                              | line | level   | position | stage                           |
      | earnest/outdated           | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/outdated           | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note    | ahead    | construction/code-generation    |
      | earnest/outdated           | src/checkout/auth.py                                                                              | 4    | note    | ahead    | construction/code-generation    |
      | earnest/outdated           | tests/test_auth.py                                                                                | 4    | note    | ahead    | construction/code-generation    |
      | earnest/unplanned          | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 17   | note    | ahead    | construction/code-generation    |
      | earnest/req-not-ears       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 17   | error   | current  | inception/requirements-analysis |
      | earnest/override-expired   | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | warning | current  | inception/requirements-analysis |
      | earnest/override-drift     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 15   | warning | current  | inception/requirements-analysis |
      | earnest/judge-uncalibrated | .earnest/assessment.json                                                                          | 1    | warning | current  | -                               |
    And the earnest/override-expired finding names "req~rate-limit~1" and the current revision "req~rate-limit~2"
    And the SARIF log holds no observation of record for "req~rate-limit~2"
    And the check exits non-zero

  Scenario: After the change commit an override whose code moved drifts, and both verdicts show (SC11)
    Given the repo maintainer's change under the overrides is committed
    When the coding agent runs earnest check --judge
    Then the earnest/override-drift finding names "req~lockout-notice~1" and the commit "89f3937"
    And the earnest/override-drift finding carries these observations:
      | author     | result        | location                                                                                        |
      | maintainer | satisfied     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md:15 |
      | judge      | not-satisfied | src/checkout/auth.py:11                                                                         |
    And the SARIF log gives each requirement one trace level:
      | requirement          | level    |
      | req~audit-log~1      | traced   |
      | req~lockout-notice~1 | judged   |
      | req~rate-limit~2     | untraced |
    And the summary leads with "traced 66%, judged 33%, evidenced 0%; requirements: 3"

  Scenario: Without --judge the check asks no model
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule                 | file                                                                                         | line | level   | position | stage                           |
      | earnest/req-not-ears | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 17   | error   | behind   | inception/requirements-analysis |
      | earnest/unplanned    | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 17   | warning | current  | construction/code-generation    |
    And the summary leads with "traced 100%, judged 0%, evidenced 0%; requirements: 3"
    And no assessment record exists
```

### Notes for the M4 task plan

- Shared steps: "the SARIF log holds exactly these findings:", "the SARIF log
  gives each requirement one trace level:", "the summary leads with …", "both
  runs write the same SARIF log", "no assessment record exists" and "the
  check exits non-zero" are already shared. The steps new to M4 live in
  `tests/steps/test_judge_check.py`; "the SARIF log gives the judged
  percentage as …" sits beside M1's traced one.
- The stub model: "the judge is the stub model with the canned verdicts of
  `seeded-change`" sets `EARNEST_JUDGE` to `stub:` and the absolute path of
  `tests/fixtures/seeded-change/judge-verdicts.json`, through `monkeypatch`.
  The file stays in the package, outside the repository under check, so Git
  lists no new file and the base commit is unchanged.
- Overlays: the base builder leaves `override/`, `override-change/` and
  `judge-verdicts.json` out, as it does `change/`, `task/` and `units/`, so the
  base commit's sha stays `89f3937`. "the repo maintainer's overrides are
  committed" commits `override/` on `main`; "the repo maintainer's change under
  the overrides is committed" commits `override-change/` on `main` on top of
  it. No branch is made; Earnest reads none.
- Columns: a `location` cell is `<file>:<line>`, read from the observation's
  SARIF `physicalLocation`. The observations-of-record table compares only the
  columns it gives, as the findings table does.
- "the judge cache holds exactly these questions" reads the record's `judge`
  slot: one entry per question the judge was asked, keyed as the Process
  vocabulary gives.
- Messages (T6, SC10):
  - `req-not-ears` names the requirement and lists the five templates of D2
    in that order.
  - `judge-not-satisfied` names the requirement and the question, and gives
    the judge's reasoning.
  - `judge-uncalibrated` names the model id and the prompt hash and says no
    passing calibration exists for them.
  - `override-expired` names the override's revision and the current one.
  - `override-drift` names the override's commit and says the judge reran.
  - The wording, and the question text built from the spans, are the plan's to
    fix; the scenarios assert the places and the facts above.
- The unit and integration tiers cover what the feature leaves out: each EARS
  template and its spans, a body broken over lines, a malformed `Override:`
  line (near-miss), two overrides of one id and kind (`duplicate`), an
  override of kind `tested`, an `at` commit Git does not hold, every exit 2 of
  `--judge` (no `EARNEST_JUDGE`, an unknown value, an unreadable or malformed
  file, a question with no answer), the judge cache key's six parts, and a
  stub file edit that reruns every question.
- Regression guard:
  - M1, M2, M2b and M3 gain no row: they never pass `--judge` and every
    requirement they seed is EARS.
  - The base commit's sha is pinned in `test_seeded_change.py`, as the
    overrides name it.

## M5 `evidence_check`

Status: RATIFIED (2026-10-25) by the maintainer. It rests on the answers E1 and E2 of the [M5 task plan](../superpowers/plans/2026-10-25-evidence-check.md), approved on 2026-10-25.

- Feature: `packages/earnest/tests/features/evidence_check.feature`, bound by
  `tests/steps/test_evidence_check.py`.
- Fixture: `tests/fixtures/seeded-change/`. Two new overlays, each committed
  on `main` on top of one history: `evidence/` over the base commit of M2 and
  M3, and `evidence-units/` over the units variant of M2b. The canned
  verdicts are `evidence-verdicts.json`, which no commit holds.
- Success criteria asserted: SC3 (in full), SC8 (done). Readings: the
  Evidence rule, Trace levels, Computed status, Frontier and position and D4
  in `01`, and E1 of the task plan.

`--evidence` implies `--judge`, and the judge is the stub model of M4. No
scenario of M1 to M4 passes `--evidence`, so their tables are unchanged. The
record holds no calibration until M6, so every `--evidence` run
here raises `judge-uncalibrated`.

### What `seeded-change` adds for M5

The overlays, the mutmut 3.8 results and the canned verdicts are those of the
Fixture section of the task plan, from the spike of 2026-10-25. In short:
`tests/test_auth.py` gains a second assert for `count_failed_logins`, whose five mutants it kills, and `src/checkout/auth.py` gains `member_key`, above the first tag, whose
surviving mutant lies in no region, and `lockout_minutes`, inside the
`req~lockout-notice~1` region, which `lockout_message` calls and whose six
mutants survive with the second mutant of `lockout_message`.
`evidence-units/` also tags `dsn~window-counter~1` over a function of its own.

### Readings the M5 scenarios pin

| Reading | Basis |
| --- | --- |
| Surviving mutants raise one `evidence-failed`, an error, per line that holds one, against each requirement the region's tags cover | the Evidence rule and the findings table in `01` |
| A surviving mutant outside every tagged region raises nothing | the Evidence rule and D4 in `01`: Earnest filters the tool's results by region |
| `evidence-failed` counts against the Code Generation stage of the task that delivers the requirement; in the base history that stage is the frontier, so the finding is current | Frontier and position in `01`; `stage_status.feature` |
| Evidenced is judged with a passing result under a key that matches the tree; where no model runs (plain `check`, `plan`), the matching `passed` entry stands for judged | Trace levels in `01`; E1 |
| `earnest plan` reads the `evidence` slot and shows a task done when each delivered `req` is evidenced and each delivered `dsn` traced, and its unit done by Computed status | Computed status and the Command surface in `01`; E1 |

### Evidence check feature

```gherkin
Feature: Evidence check
  Against the stub model, the coding agent learns from the check which
  tagged regions hold a surviving mutant, which level each requirement
  reaches with three separate percentages, and, from the plan, which task
  and unit the evidence shows as done (SC3, SC8).

  Scenario: Against the stub model the evidence check reports a surviving mutant in a tagged region (SC3)
    Given the repo maintainer's "seeded-change" repository at its base commit, with the requirements stage approved
    And the repo maintainer's evidence overlay is committed
    And the judge is the stub model with the canned evidence verdicts of "seeded-change"
    When the coding agent runs earnest check --evidence
    Then the SARIF log holds exactly these findings:
      | rule                        | file                                                                                         | line | level   | position | stage                        |
      | earnest/unplanned           | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 13   | warning | current  | construction/code-generation |
      | earnest/judge-not-satisfied | tests/test_auth.py                                                                           | 17   | warning | current  | -                            |
      | earnest/judge-uncalibrated  | .earnest/assessment.json                                                                     | 1    | warning | current  | -                            |
      | earnest/evidence-failed     | src/checkout/auth.py                                                                         | 15   | error   | current  | construction/code-generation |
      | earnest/evidence-failed     | src/checkout/auth.py                                                                         | 19   | error   | current  | construction/code-generation |
    And the check exits non-zero

  Scenario: A surviving mutant outside every tagged region raises nothing (SC3)
    Given the repo maintainer's "seeded-change" repository at its base commit, with the requirements stage approved
    And the repo maintainer's evidence overlay is committed
    And the judge is the stub model with the canned evidence verdicts of "seeded-change"
    When the coding agent runs earnest check --evidence
    Then the SARIF log holds no finding at "src/checkout/auth.py" line 5
    And the SARIF log holds an earnest/evidence-failed finding at "src/checkout/auth.py" line 19

  Scenario: Each requirement lands at exactly one trace level, with three percentages (SC3)
    Given the repo maintainer's "seeded-change" repository at its base commit, with the requirements stage approved
    And the repo maintainer's evidence overlay is committed
    And the judge is the stub model with the canned evidence verdicts of "seeded-change"
    When the coding agent runs earnest check --evidence
    Then the SARIF log gives each requirement one trace level:
      | requirement          | level     |
      | req~audit-log~1      | traced    |
      | req~lockout-notice~1 | judged    |
      | req~rate-limit~1     | evidenced |
    And the summary leads with "traced 100%, judged 66%, evidenced 33%; requirements: 3"

  Scenario: After the evidence check, the plan shows the evidenced task and its unit as done (SC8)
    Given the repo maintainer's "seeded-change" repository in its future-format units variant, with the requirements, the units and the first unit's functional design approved
    And the repo maintainer's units evidence overlay is committed
    And the judge is the stub model with the canned evidence verdicts of "seeded-change"
    And the coding agent has run earnest check --evidence
    When the repo maintainer runs earnest plan
    Then the plan lists these tasks:
      | task                  | status   |
      | task~add-limiter~1    | done     |
      | task~notify-lockout~1 | not done |
    And the plan lists these units:
      | unit      | status   | directory  | frontier                                  |
      | unit~u1~1 | done     | u1-limiter | construction/u1-limiter/code-generation   |
      | unit~u2~1 | not done | u2-notice  | construction/u2-notice/functional-design  |
    And the repository is unchanged

  Scenario: An edit under an evidenced requirement drops it below evidenced until the check reruns (SC8)
    Given the repo maintainer's "seeded-change" repository in its future-format units variant, with the requirements, the units and the first unit's functional design approved
    And the repo maintainer's units evidence overlay is committed
    And the judge is the stub model with the canned evidence verdicts of "seeded-change"
    And the coding agent has run earnest check --evidence
    And the coding agent has an uncommitted edit to the test of "req~rate-limit~1"
    When the repo maintainer runs earnest plan
    Then the plan lists these tasks:
      | task                  | status   |
      | task~add-limiter~1    | not done |
      | task~notify-lockout~1 | not done |

  Scenario: Without --evidence the check runs no test and no mutant
    Given the repo maintainer's "seeded-change" repository at its base commit, with the requirements stage approved
    And the repo maintainer's evidence overlay is committed
    When the coding agent runs earnest check
    Then the SARIF log holds no earnest/evidence-failed finding
    And the summary leads with "traced 100%, judged 0%, evidenced 0%; requirements: 3"
```

### Notes for the M5 task plan

- The findings table of the first scenario is ratified as drafted: one
  `evidence-failed` per line that holds a surviving mutant, and the
  `judge-not-satisfied` verdict for `req~audit-log~1 tested` where the canned
  verdicts place it; Task 1's red run confirms the rest.
- The units scenarios sit on the units variant because only it has a unit;
  there `evidence-failed` against `req~lockout-notice~1` is ahead of
  `unit~u2~1`'s frontier, a note, so they assert the plan, not the exit code.
- New steps, bound in `tests/steps/test_evidence_check.py`:
  - `the coding agent runs earnest check --evidence`, and `the coding agent
    has run earnest check --evidence` (below).
  - `the repo maintainer's evidence overlay is committed` and `the repo
    maintainer's units evidence overlay is committed`: the two overlay commits
    on `main`.
  - `the SARIF log holds no finding at "<file>" line <n>`: no SARIF result is
    located at that file and line, whatever its rule.
  - `the SARIF log holds an <rule> finding at "<file>" line <n>`: one is, so
    the region-filter scenario stays red until a surviving mutant is reported.
  - `the SARIF log holds no <rule> finding`, for any rule; M2's binding is a
    literal for `unbumped-change`.
  - `the judge is the stub model with the canned evidence verdicts of "<name>"`:
    `EARNEST_JUDGE` names `evidence-verdicts.json`.
  - `the repo maintainer runs earnest plan`, as "the coding agent runs earnest
    plan" does, with the maintainer as actor.
  - `the coding agent has an uncommitted edit to the test of "<req>"`: an
    edit, left uncommitted, to the test that tags the requirement.
  - Steps reused from other step modules ("the repository is unchanged",
    "the plan lists these units:", "the SARIF log gives each requirement one
    trace level:", "the summary leads with …", and the base-commit and units-variant Givens) are imported
    or rebound in `test_evidence_check.py`; only `conftest.py` steps are
    shared.
  - "the repository is unchanged" is M2's: the `.gitignore` that Earnest
    writes in a new `.earnest/` keeps the record the check wrote out of
    `git status`.
- "the coding agent has run earnest check --evidence" asserts that the run
  wrote the record's `evidence` slot, so the two units scenarios stay red until
  Task 5 and the stale-key scenario cannot pass without one. The previous
  scenario shows `task~add-limiter~1` done from the same Givens; this one adds
  only an uncommitted edit inside `req~rate-limit~1`'s test region, a new
  step: the existing "uncommitted edit to …" step of `stage_status.feature`
  appends at the end of the file, which lies in `req~audit-log~1`'s region
  (D10). The edit changes the requirement's `tests` hash, so its stored key
  no longer matches and the entry is not counted.

## M6 `calibration_gate`

Status: the scenario titles below are PROPOSED. They rest on the gating
answers of the task plan
[2026-10-25-calibration-gate.md](../superpowers/plans/2026-10-25-calibration-gate.md),
which the maintainer approved on 2026-10-25. The Gherkin and its exact tables
follow once the maintainer has written the fixture's ten requirements and
verdicts.

- Feature: `packages/earnest/tests/features/calibration_gate.feature`, bound by
  `tests/steps/test_calibration_gate.py`.
- Fixture: `tests/fixtures/calibration/`, plain files committed once on `main`
  at test time. It holds ten hand-written requirements, their hand-tagged code
  and tests, and the maintainer's verdicts in `verdicts.json`, in the
  canned-verdict format of the Runtime and permission model of `01`.
- Success criteria asserted: SC4. Readings: UC8, G10, the Command surface row
  of `earnest calibrate`, and the record's `calibration` key in `01`.

The judge is the stub model in every M6 scenario, so no network is reached.
Its files are `stub-pass.json` and `stub-fail.json`, which sit beside
`verdicts.json` and are left out of the fixture's commit. They copy
`verdicts.json` with results flipped on two, and then three, requirements,
giving eight and seven matches. A requirement matches when both of its
questions agree. Every scenario runs with the built fixture as the working
directory, so `calibrate` and `check --judge` read and write one record.

### Proposed scenarios

All five titles are PROPOSED:

- "Calibration shows each verdict beside the maintainer's and passes at eight
  matches"
- "Calibration at seven matches fails and records the failure"
- "After a passing calibration the judge run is not uncalibrated"
- "A calibration of another model leaves the judge uncalibrated"
- "Calibrate cannot run without a model or a valid fixture"

## Scope (v1)

- One behavior feature per milestone of `03`, nine in all, with the scenarios
  of M1, M2, M2b, M3, M4 and M5 in full.
- Three test tiers under one runner, pytest, with pytest-bdd for the features.
- Three fixture repositories, `broken-links`, `seeded-change` and
  `calibration`, each plain files with its history built at test time, and a
  TypeScript fixture at M8.

## Future directions

- The scenarios of M7 and M8, each written here when its milestone's
  plan is written.
- A coverage threshold for the package, when the maintainer sets one.

## Open questions

| Question | Owner | Resolved by |
| --- | --- | --- |
| How M3's overlay changes meet the exact findings tables of M2's bump and fresh-approval scenarios | maintainer | resolved before M3. The out-of-task check and impact run only with a current task and a change baseline, and read no Git branch (the maintainer's decision), so M2's scenarios, whose state file names no current task, keep the tables of `main`. M3's code edits sit in the `task/` overlay stacked on `change/`, with their own tables in `task_change.feature`, where M3's steps name the current task and record an approved stage check |
