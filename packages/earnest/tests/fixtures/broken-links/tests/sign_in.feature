Feature: Sign in

  @stest:feat~sign-in~1
  Scenario: A member signs in with the right password
    Given a member with a password
    When the member signs in with that password
    Then the member is signed in

  @stest feat~sign-in~1
  Scenario: A member is refused after five failures
    Given a member who failed to sign in five times in one minute
    When the member signs in again
    Then the attempt is refused

  @smoke @stest:feat~Password-Reset~1
  Scenario: A member resets a forgotten password
    Given a member who forgot the password
    When the member asks for a reset
    Then a reset link is sent
