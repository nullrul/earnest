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
