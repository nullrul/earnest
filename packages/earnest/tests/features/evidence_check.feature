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
