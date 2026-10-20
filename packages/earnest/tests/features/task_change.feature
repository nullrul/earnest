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
