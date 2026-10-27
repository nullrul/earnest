Feature: Calibration gate
  Against the stub model, the repo maintainer learns from earnest calibrate
  how the judge's verdicts on ten hand-tagged requirements compare with their
  own, how many match, and whether the judge passes at eight or more. A
  passing calibration for the current model id and prompt hash stops the judge
  run raising judge-uncalibrated (UC8, SC4). The fixture is the synthetic
  development fixture, never SC4 evidence.

  Background:
    Given the repo maintainer's "calibration-dev" repository committed on main

  Scenario: Calibration shows each verdict beside the maintainer's and passes at eight matches
    Given the judge is the stub model with the canned verdicts "stub-pass.json" of "calibration-dev"
    When the repo maintainer runs earnest calibrate
    Then the calibration lists these requirements:
      | requirement         | judge                   | maintainer              | agreement |
      | req~card-refusal~1  | satisfied/satisfied     | satisfied/satisfied     | match     |
      | req~daily-cap~1     | satisfied/satisfied     | not-satisfied/satisfied | differs   |
      | req~entry-time~1    | satisfied/satisfied     | satisfied/satisfied     | match     |
      | req~ev-discount~1   | not-satisfied/satisfied | not-satisfied/satisfied | match     |
      | req~fare-rounding~1 | satisfied/not-satisfied | satisfied/satisfied     | differs   |
      | req~full-sign~1     | satisfied/satisfied     | satisfied/satisfied     | match     |
      | req~grace-period~1  | satisfied/satisfied     | satisfied/satisfied     | match     |
      | req~lost-ticket~1   | satisfied/not-satisfied | satisfied/not-satisfied | match     |
      | req~night-rate~1    | satisfied/satisfied     | satisfied/satisfied     | match     |
      | req~receipt-total~1 | satisfied/satisfied     | satisfied/satisfied     | match     |
    And the calibration ends with "matches: 8/10" and "pass"
    And the calibrate exits with code 0
    And the record's calibration slot holds the model of "stub-pass.json", the prompt hash, 8 matches of 10 and a pass

  Scenario: Calibration at seven matches fails and records the failure
    Given the judge is the stub model with the canned verdicts "stub-fail.json" of "calibration-dev"
    When the repo maintainer runs earnest calibrate
    Then the calibration lists "req~daily-cap~1", "req~fare-rounding~1" and "req~grace-period~1" as differing
    And the calibration ends with "matches: 7/10" and "fail"
    And the calibrate exits with code 1
    And the record's calibration slot holds the model of "stub-fail.json", the prompt hash, 7 matches of 10 and no pass

  Scenario: After a passing calibration the judge run is not uncalibrated
    Given the judge is the stub model with the canned verdicts "stub-pass.json" of "calibration-dev"
    And the repo maintainer has run earnest calibrate
    When the coding agent runs earnest check --judge
    Then the SARIF log holds no earnest/judge-uncalibrated finding
    And the SARIF log gives the model of "stub-pass.json" and the prompt hash in the run's invocation

  Scenario: A calibration of another model leaves the judge uncalibrated
    Given the judge is the stub model with the canned verdicts "stub-pass.json" of "calibration-dev"
    And the repo maintainer has run earnest calibrate
    And the judge is the stub model with the canned verdicts "stub-fail.json" of "calibration-dev"
    When the coding agent runs earnest check --judge
    Then the earnest/judge-uncalibrated finding names the model of "stub-fail.json" and the prompt hash

  Scenario Outline: Calibrate cannot run without a model or a valid fixture
    Given the judge is the stub model with the canned verdicts "stub-pass.json" of "calibration-dev"
    And <fault>
    When the repo maintainer runs earnest calibrate
    Then the calibrate exits with code 2, with empty stdout and one line on stderr naming "<cause>"
    And the record holds no calibration

    Examples:
      | fault                                     | cause         |
      | EARNEST_JUDGE is unset                    | EARNEST_JUDGE |
      | the fixture's verdicts.json is deleted    | verdicts.json |
      | the fixture's last requirement is deleted | exactly ten   |
