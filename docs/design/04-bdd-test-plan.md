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
- Every run reports coverage, and no coverage threshold applies for now.

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
| M5 `evidence_check` | `evidence_check.feature` | `test_evidence_check.py` | `seeded-change` | SC3 (in full), SC8 (done) |
| M6 `calibration_gate` | `calibration_gate.feature` | `test_calibration_gate.py` | `calibration` | SC4 |
| M7 `aidlc_fork` | `aidlc_fork.feature` | `test_aidlc_fork.py` | `seeded-change`, with a fork checkout | SC9 |

The scenarios of M3 to M7 are added here when each milestone's plan is written.

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
  existing task: one revision bump and one silent edit. M2 passes no `--task`
  and reads no branch name; the split of `task/<name>-…` for a hyphenated name
  is an open question of `01` that M3 closes.
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
`task/add-limiter-window` (`01` names the convention `task/<name>-…`, and
`add-limiter` is the task the base commit holds):

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
- M3 additions to the overlay (code changed inside and outside the task, a
  region under an override) add out-of-task and `impact-degraded` rows to plain
  `check` after the overlay, which changes the exact tables of the bump and
  fresh-approval scenarios; the Open questions section below carries the
  decision.
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

## Scope (v1)

- One behavior feature per milestone of `03`, eight in all, with the scenarios
  of M1, M2 and M2b in full.
- Three test tiers under one runner, pytest, with pytest-bdd for the features.
- Three fixture repositories, `broken-links`, `seeded-change` and
  `calibration`, each plain files with its history built at test time.

## Future directions

- The scenarios of M3 to M7, each written here when its milestone's
  plan is written.
- A coverage threshold for the package, when the maintainer sets one.

## Open questions

| Question | Owner | Resolved by |
| --- | --- | --- |
| How M3's overlay changes (code changed inside and outside the task, a region under an override) meet the exact findings tables of M2's bump and fresh-approval scenarios: a ratified revision of those tables, or a second overlay for M3 | maintainer | before milestone `task_change` of `03-implementation-plan.md` |
