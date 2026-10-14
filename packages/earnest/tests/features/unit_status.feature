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
