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
| M2 `stage_status` | `stage_status.feature` | `test_stage_status.py` | `seeded-change` | SC1, SC5, SC8 (status), SC9 (run header) |
| M3 `task_change` | `task_change.feature` | `test_task_change.py` | `seeded-change` | SC6, SC7 |
| M4 `judge_check` | `judge_check.feature` | `test_judge_check.py` | `seeded-change` | SC3 (judged), SC4 (warning), SC11 |
| M5 `evidence_check` | `evidence_check.feature` | `test_evidence_check.py` | `seeded-change` | SC3 (in full), SC8 (done) |
| M6 `calibration_gate` | `calibration_gate.feature` | `test_calibration_gate.py` | `calibration` | SC4 |
| M7 `aidlc_fork` | `aidlc_fork.feature` | `test_aidlc_fork.py` | `seeded-change`, with a fork checkout | SC9 |

Each later milestone's scenarios are added here when that milestone's plan is written.

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

## Scope (v1)

- One behavior feature per milestone of `03`, seven in all, with the scenarios
  of M1 in full.
- Three test tiers under one runner, pytest, with pytest-bdd for the features.
- Three fixture repositories, `broken-links`, `seeded-change` and
  `calibration`, each plain files with its history built at test time.

## Future directions

- The scenarios of M2 to M7, each written here when its milestone's plan is
  written.
- A coverage threshold for the package, when the maintainer sets one.
