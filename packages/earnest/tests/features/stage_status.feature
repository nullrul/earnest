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
      | rule                    | file                                                                                              | line | level   | position | stage                           |
      | earnest/unbumped-change | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | error   | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | note    | ahead    | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | note    | ahead    | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note    | ahead    | construction/code-generation    |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | note    | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 11   | note    | current  | inception/requirements-analysis |
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
      | rule                    | file                                                                                         | line | level | position | stage                           |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 3    | note  | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 3    | note  | current  | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 5    | note  | current  | inception/requirements-analysis |
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
      | rule                    | file                                                                                              | line | level   | position | stage                           |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | error   | current  | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | error   | current  | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | error   | current  | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | warning | current  | construction/code-generation    |
      | earnest/out-of-task     | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | warning | current  | construction/code-generation    |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note    | behind   | inception/requirements-analysis |
      | earnest/impact-degraded | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 5    | note    | behind   | inception/requirements-analysis |
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
