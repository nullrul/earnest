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
