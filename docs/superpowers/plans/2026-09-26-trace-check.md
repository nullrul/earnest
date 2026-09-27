# M1 `trace_check` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the trace spine end to end: `earnest check` reads a repository's Markdown items and its Python, TypeScript and Gherkin tags, reports every broken link at file and line as a SARIF 2.1.0 log on stdout with a summary on stderr, places each `req` at untraced or traced, and exits non-zero on an error-level finding.

**Architecture:** One pass along the Container pipeline of `01`: `git.py` lists the files Git lists for the work tree, the `adapters/` hand each file's Markdown, comment or tag lines to `index.py`, whose grammar builds the items, links and near-misses and resolves each written id; `structural.py` turns the index into link findings and trace levels, and `reporter.py` writes SARIF and the summary; `cli.py` wires the pipeline and sets the exit code. No plan exists yet, so every finding reaches no stage and sits at position `current` with no `properties.stage`. The behavior feature over the `broken-links` fixture is written first and stays red until the last task.

**Tech Stack:** Python 3.12 standard library at runtime (`argparse`, `tokenize`, `re`, `json`, `difflib`, `subprocess`, `functools`, `urllib.parse`, `os`); pytest 9 with pytest-bdd 8.1 and pytest-cov; uv with hatchling; ruff, `mypy --strict`, vulture.

**Spec:** `docs/design/03-implementation-plan.md`, milestone M1 `trace_check`, and the sections its Context to load names in `docs/design/00-project-intent.md`, `docs/design/01-logic-design.md` and `docs/design/02-structural-design.md`; the scenarios are those of M1 in `docs/design/04-bdd-test-plan.md`.

## Global Constraints

- Every path matches the File and directory tree of `02` verbatim: modules under `packages/earnest/src/earnest/`, tests under `packages/earnest/tests/`.
- The runtime is the standard library alone (L4); the one new dependency is pytest-bdd, added to the `dev` extra with `uv add --optional dev pytest-bdd "pytest>=9,<10"` in `packages/earnest`, which also pins pytest 9 (L5).
- Lint bar (L1): ruff at "line length 120, complexity 10, five arguments, Google docstrings", `ruff format`, `mypy --strict` over `src/`, and vulture at `min_confidence = 80`; `make lint` runs all four.
- Platforms: macOS and Linux only.
- `earnest check` reads "the files Git lists for the work tree: tracked files plus untracked files that are not ignored", which is `git ls-files -z --cached --others --exclude-standard`.
- `earnest check` writes "the SARIF 2.1.0 log on stdout, and on stderr a human summary" (Command surface).
- "The exit code is 0 when no error-level finding sits at position behind or current, 1 when one does, and 2 when the check cannot run: Git cannot answer or a file cannot be read."
- "A finding that reaches no stage has `properties.position` `current`, omits `properties.stage`, and its message opens with `in scope`"; with no plan yet, every M1 finding is one.
- "The observations behind a finding travel under the result's `properties`": each M1 finding carries one, whose method is `trace`.
- "Each requirement's trace level and the three percentages travel under the run's `properties`"; the commit and the layers run travel under the run's `invocations`.
- SC1: two runs over an unchanged repository give the same SARIF bytes, so the log holds no timestamp, and its keys and results are sorted.
- Coverage (L1): "every test run reports coverage with no threshold and passes or fails on its tests alone".
- L6: fixtures are plain files whose Git history `tests/conftest.py` builds at test time; `tests/fixtures` stays out of ruff, pytest collection (`collect_ignore` in `tests/conftest.py`) and markdownlint.
- Run every command in `packages/earnest/` unless a step names the repository root, and start each task with `make install`.
- Commit messages take the form `<type>: <description>`; before each commit, `git status --short` lists only the task's files.

## Review Focus

- A design doc that quotes an item in a code fence, such as `` `req~login-rate-limit~2` `` or `Covers: FR1.2` in an example, or opens a body line with a backticked path such as `` `~/.config/app` ``: fenced lines start, end and key no item and raise no near-miss, and the path line stays body text (Tasks 3 and 6).
- A regular expression literal in TypeScript, such as `` s.replace(/`/g, "") `` or `/\/*$/`: it opens no template literal and no comment, so the tags below it still count; a `/` that divides, as in `i++ / 2`, or closes a JSX tag, as in `</p>`, opens no regular expression; and `//` or tag-shaped text inside a string or template literal stays text (Task 5).
- A Python file that stops tokenizing halfway through an agent's edit: the tags above the error still count, and the check never crashes (Task 5).
- `earnest check` run from a subdirectory, over names with spaces or accents, files not yet staged, and a line holding a lone `\r`: the whole work tree is read, every path is relative to its root and percent-encoded in the SARIF `uri`, every line number is the one Git counts, and a Python comment after the `\r` still counts (Tasks 2, 5, 7 and 9).
- `earnest check` over a binary file or text that is not UTF-8, outside a Git work tree, or piped into a reader that quits early on stdout or stderr, as `head` does: the binary file is skipped and the text read with replacement characters, so its ids still count; the other two exit 2 with at most one line on stderr and no traceback (Tasks 6 and 9).

## File Structure

| Path under `packages/earnest/` | Responsibility | Task |
| --- | --- | --- |
| `pyproject.toml`, `uv.lock` | pytest-bdd and the pytest pin, the fixture exclude, then the `earnest` script | 1, 9 |
| `tests/conftest.py` | fixture repositories committed in `tmp_path`; every test's Git shut off from the user's; the fixture collection ignore | 1, 2 |
| `tests/sarif.py` | the SARIF helpers the tests share | 1 |
| `tests/fixtures/broken-links/` | one seeded broken link of every kind, across four languages | 1 |
| `tests/features/trace_check.feature` | M1's scenarios, verbatim from `04` | 1 |
| `tests/steps/test_trace_check.py` | pytest-bdd steps; the exit command | 1 |
| `src/earnest/git.py` | the files Git lists for the work tree, its root and commit | 2 |
| `src/earnest/index.py` | the grammar: items, key lines, tags, the Near-miss table, Reference resolution | 3, 4 |
| `src/earnest/adapters/python.py`, `typescript.py` | the comment lines of each language | 5 |
| `src/earnest/adapters/markdown.py`, `gherkin.py`, `__init__.py` | Markdown lines and fences, Gherkin tag lines, the adapter by suffix | 6 |
| `src/earnest/reporter.py` | `Finding`, percentages, SARIF 2.1.0 with observations, the summary | 7 |
| `src/earnest/structural.py` | the link rules and each requirement's trace level | 8 |
| `src/earnest/cli.py` | `earnest check` and its exit code | 9 |

Outside the package, Task 1 changes the repository root's `.markdownlint-cli2.jsonc` and the `lint-file` target of its `Makefile`, and Task 9 marks M1 done on the milestone DAG of `docs/design/03-implementation-plan.md`. Each module's unit test sits at `tests/unit/test_<module>.py`, each adapter's at `tests/unit/adapters/test_<language>.py`, and the end-to-end flow at `tests/integration/test_check.py`.

---

## Tasks

### Task 1: The `trace_check` behavior gate, red

**Files:**

- Modify: `packages/earnest/pyproject.toml` (the `dev` list of `[project.optional-dependencies]` from `uv add`, `[tool.ruff]`, `[tool.pytest.ini_options]`)
- Modify: `packages/earnest/uv.lock` (written by `uv add`)
- Modify: `.markdownlint-cli2.jsonc`
- Modify: `Makefile` (the `*.py)` line of `lint-file`)
- Move: `packages/earnest/tests/test_init.py` to `packages/earnest/tests/unit/test_init.py`
- Create: `packages/earnest/tests/unit/__init__.py`, `packages/earnest/tests/steps/__init__.py`
- Create: `packages/earnest/tests/conftest.py`, `packages/earnest/tests/sarif.py`
- Create: `packages/earnest/tests/fixtures/broken-links/` with `docs/intent.md`, `docs/scope.md`, `docs/requirements.md`, `docs/plan.md`, `src/auth.py`, `tests/test_auth.py`, `tests/sign_in.feature`, `web/login.ts`
- Create: `packages/earnest/tests/features/trace_check.feature`
- Test: `packages/earnest/tests/steps/test_trace_check.py`

**Interfaces:**

- Consumes: nothing; the package holds only `earnest.__version__`.
- Produces, in `tests/conftest.py`: `collect_ignore = ["fixtures"]`; an autouse fixture that shuts every Git a test runs, `earnest`'s own included, off from the user's Git configuration and from inherited `GIT_` variables; the pytest fixture `fixture_repo`, a `Callable[[str], Path]` that copies `tests/fixtures/<name>` to `tmp_path / name`, commits it on `main` with pinned names and dates and returns the repository; and the helper `_commit(repo: Path) -> Path`, which Task 2 reuses.
- Produces, in `tests/sarif.py`, the SARIF helpers every tier reads a log through: `sarif_run(text: str) -> dict`, the one run of the log in `text`, and `located(result: dict) -> tuple[str, int]`, a result's `uri` as written and its line.
- Produces the exit command `uv run pytest tests/steps/test_trace_check.py`, which runs the console script `earnest` beside `sys.executable` and stays red until Task 9 declares that script.

- [ ] **Step 1: Add pytest-bdd, pin pytest, and keep the fixtures out of ruff**

Run:

```bash
cd packages/earnest
make install
uv add --optional dev pytest-bdd "pytest>=9,<10"
```

Expected: `uv add` resolves pytest-bdd 8.1.0 and a pytest 9, turns `"pytest"` in the `dev` list of `pyproject.toml` into `"pytest>=9,<10"`, appends `"pytest-bdd>=8.1.0"` to the list's end, and adds pytest-bdd, gherkin-official, Mako, parse and parse-type to `uv.lock`.

pytest-bdd 8.1.0 calls two fixture APIs that pytest 9 deprecates and pytest 10 removes. The filter added below matches pytest 9's warning, and the pin keeps the run on pytest 9; a comment ties the two together. In `packages/earnest/pyproject.toml`, replace:

```toml
    "pytest>=9,<10",
```

with:

```toml
    # pytest-bdd 8.1 calls pytest APIs that pytest 9 deprecates and pytest 10 removes: the
    # "Passing (nodeid|baseid) to" warning filter below matches pytest 9, and this pin keeps the run on pytest 9.
    "pytest>=9,<10",
```

`[tool.ruff]` gains the fixture exclude. In the same file, replace:

```toml
src = ["src", "tests"]
```

with:

```toml
src = ["src", "tests"]
extend-exclude = ["tests/fixtures"]
```

`[tool.pytest.ini_options]` gains the features directory and the warning filter, since the `"error"` filter would turn pytest 9's deprecation warnings into failures. The fixtures stay out of pytest's collection through `collect_ignore` in `tests/conftest.py` (Step 5). In the same file, replace:

```toml
addopts = "--cov=earnest --cov-report=term-missing"
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:hypothesis.*",
    "ignore::DeprecationWarning:pytest_asyncio.*",
]
```

with:

```toml
addopts = "--cov=earnest --cov-report=term-missing"
bdd_features_base_dir = "tests/features"
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:hypothesis.*",
    "ignore::DeprecationWarning:pytest_asyncio.*",
    "ignore:Passing (nodeid|baseid) to:pytest.PytestRemovedIn10Warning",
]
```

- [ ] **Step 2: Keep the fixtures out of markdownlint and the edit hook**

Replace the whole of `.markdownlint-cli2.jsonc`, at the repository root, with:

```jsonc
{
  "config": { "MD013": false },
  "ignores": [".claude/**", "node_modules/**", "**/.venv/**", "packages/earnest/tests/fixtures/**"]
}
```

The edit hook runs the root `Makefile`'s `lint-file` target from the repository root, and ruff applies `extend-exclude` to a path named on its command line only under `--force-exclude`. Add the flag to both ruff calls on the target's `*.py)` line, from the repository root:

```bash
perl -pi -e 's/ruff format -- /ruff format --force-exclude -- /; s/ruff check --fix -- /ruff check --force-exclude --fix -- /' Makefile
grep -cF 'ruff format --force-exclude -- ' Makefile
grep -cF 'ruff check --force-exclude --fix -- ' Makefile
```

Expected: `1`, then `1`: the `*.py)` line now carries `--force-exclude` in both calls.

- [ ] **Step 3: Move the version test into the unit tier**

```bash
cd packages/earnest
mkdir -p tests/unit tests/steps tests/features
touch tests/unit/__init__.py tests/steps/__init__.py
git mv tests/test_init.py tests/unit/test_init.py
```

- [ ] **Step 4: Write the `broken-links` fixture**

Every file is data, written exactly as shown; the feature pins its line numbers. The Python files are already in `ruff format` style.

Create `packages/earnest/tests/fixtures/broken-links/docs/intent.md`:

```markdown
# Intent

`tenet~trust~1`

Every link in the chain comes from the work itself.

`goal~safe-sign-in~1`

Members sign in without an attacker guessing their way in.

Covers: tenet~trust~1
```

Create `packages/earnest/tests/fixtures/broken-links/docs/scope.md`:

```markdown
# Scope

`feat~sign-in~1`

A member signs in with a password.

Covers: goal~safe-sign-in~1

`feat~password-reset~1`

A member resets a forgotten password.

Covers: goal~safe-sign-in~1
```

Create `packages/earnest/tests/fixtures/broken-links/docs/requirements.md`:

```markdown
# Requirements

`req~rate-limit~1`

When a client fails to sign in five times in one minute, the auth service
shall refuse further attempts for fifteen minutes.

Needs: impl, utest
Covers: feat~sign-in~1

`req~lockout-notice~2`

When the auth service refuses an attempt, the auth service shall tell the
member when to try again.

Covers: feat~sign-in~1

`req~session-expiry~1`

While a session is idle for thirty minutes, the auth service shall end it.

Needs: impl utest

`req~remember-me`

Where remember-me is on, the auth service shall keep the session for a week.

`req~audit-log~1`

When a member signs in, the auth service shall record the time.

Covers: feat~sign-in~2, FR1.2

`req~audit-log~1`

When a member signs out, the auth service shall record the time.
```

Create `packages/earnest/tests/fixtures/broken-links/docs/plan.md`:

```markdown
# Plan

`task~wire-limiter~1`

Wire the rate limiter into the sign-in handler.

Delivers: req~Rate-Limit~1
Depends: task~set_up~1

`task~notify~1` Tell the member when to try again

`task~audit~1`

Record each sign-in.

**Delivers:** req~audit-log~1
Depends: task~wire-limiter~1,

`tsk~expire~1`

End idle sessions.
```

Create `packages/earnest/tests/fixtures/broken-links/src/auth.py`:

```python
"""Sign-in checks for the auth service."""

FAILED_LIMIT = 5
IDLE_MINUTES = 30


# [impl->req~rate-limit~1]
def refuse(failures: int) -> bool:
    """Refuse an attempt after too many failures."""
    return failures >= FAILED_LIMIT


# [impl->req~session-expiry~1]
def expired(idle_minutes: int) -> bool:
    """End a session that sat idle too long."""
    return idle_minutes >= IDLE_MINUTES  # [impl->req~rate-limt~1]


# [impl-req~audit-log~1]
def record(member: str) -> str:
    """Record a sign-in."""
    return member
```

Create `packages/earnest/tests/fixtures/broken-links/tests/test_auth.py`:

```python
"""Tests for the sign-in checks."""

from src.auth import expired, refuse


# [utest->req~rate-limit~1]
def test_refuse_after_five_failures() -> None:
    """Five failures refuse the next attempt."""
    assert refuse(5)


# [ utest -> req~session-expiry~1 ]
# [itest->req~rate-limit~1]
def test_expired_after_thirty_minutes() -> None:
    """A session idle for thirty minutes has expired."""
    assert expired(30)
```

Create `packages/earnest/tests/fixtures/broken-links/tests/sign_in.feature`:

```gherkin
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
```

Create `packages/earnest/tests/fixtures/broken-links/web/login.ts`:

```typescript
// Sign-in messages for the auth service.

// [impl->req~lockout-notice~1]
export function notice(minutes: number): string {
  return `Try again in ${minutes} minutes.`;
}

/* [impl->req~audit-log~1] */
export function audit(member: string): string {
  return `${member} signed in.`;
}

// [impl->req~lockout-notice]
export function banner(): string {
  return "Too many attempts // wait a minute.";
}
```

- [ ] **Step 5: Write the fixture builder and the SARIF helpers**

`collect_ignore` keeps pytest from collecting the fixtures' own test files, such as `broken-links/tests/test_auth.py`. The autouse fixture edits `os.environ` itself, so the Git that `earnest` runs, in the test's process or in a child, is shut off from the user's configuration as well as the Git that commits a fixture; `_git` adds only the pinned identity. Create `packages/earnest/tests/conftest.py`:

```python
"""Shared fixtures: every test's Git shut off from the user's, and fixture repositories committed in tmp_path."""

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest


collect_ignore = ["fixtures"]  # fixture repositories are data, and their tests are not this package's

FIXTURES = Path(__file__).parent / "fixtures"
# Pinned names and dates give a fixture commit the same sha on every run, and M4's overrides name that sha.
_IDENTITY = {
    "GIT_AUTHOR_NAME": "Earnest Fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.com",
    "GIT_AUTHOR_DATE": "2026-09-26T12:00:00+00:00",
    "GIT_COMMITTER_NAME": "Earnest Fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.com",
    "GIT_COMMITTER_DATE": "2026-09-26T12:00:00+00:00",
}


@pytest.fixture(autouse=True)
def _isolated_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shut every Git a test runs, earnest's own included, off from the user's configuration and GIT_ variables."""
    # a Git hook that runs the tests sets GIT_DIR and GIT_INDEX_FILE; GIT_EXEC_PATH only says where Git's helpers live
    for name in list(os.environ):
        if name.startswith("GIT_") and name != "GIT_EXEC_PATH":
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _git(repo: Path, *args: str) -> None:
    """Run git in repo as the fixture's pinned author and committer."""
    subprocess.run(["git", *args], cwd=repo, env=os.environ | _IDENTITY, capture_output=True, check=True)


def _commit(repo: Path) -> Path:
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "fixture")
    return repo


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Callable[[str], Path]:
    """Return a builder that copies tests/fixtures/<name> into tmp_path and commits it on main."""

    def build(name: str) -> Path:
        repo = tmp_path / name
        shutil.copytree(FIXTURES / name, repo)
        return _commit(repo)

    return build
```

The step module, the reporter's unit test and the integration test all read a SARIF log; its helpers live in one place. Create `packages/earnest/tests/sarif.py`:

```python
"""SARIF helpers the tests share: the one run in a log, and where a result sits."""

import json


def sarif_run(text):
    """Return the one run of the SARIF log in text."""
    (run,) = json.loads(text)["runs"]
    return run


def located(result):
    """Return a result's file, as its percent-encoded uri, and its line."""
    location = result["locations"][0]["physicalLocation"]
    return location["artifactLocation"]["uri"], location["region"]["startLine"]
```

- [ ] **Step 6: Write the feature, verbatim from the M1 section of `04`**

Create `packages/earnest/tests/features/trace_check.feature`:

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

- [ ] **Step 7: Write the step module**

Create `packages/earnest/tests/steps/test_trace_check.py`:

```python
"""Steps for tests/features/trace_check.feature: `earnest check` over the broken-links fixture."""

import json
import subprocess
import sys
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from tests.sarif import located, sarif_run


scenarios("trace_check.feature")

EARNEST = Path(sys.executable).with_name("earnest")


def run_check(repo):
    """Run `earnest check` in repo, as the coding agent does."""
    return subprocess.run([str(EARNEST), "check"], cwd=repo, capture_output=True, text=True, check=False)


def rows(datatable):
    """Return a data table's rows as dicts keyed by its header."""
    header, *body = datatable
    return [dict(zip(header, row, strict=True)) for row in body]


@given(
    parsers.parse('the repo maintainer\'s "{name}" repository, with a broken link of every kind'),
    target_fixture="repo",
)
def maintainer_repository(fixture_repo, name):
    return fixture_repo(name)


@when("the coding agent runs earnest check", target_fixture="run")
def agent_runs_check(repo):
    return run_check(repo)


@when("the coding agent runs earnest check twice", target_fixture="runs")
def agent_runs_check_twice(repo):
    return [run_check(repo), run_check(repo)]


@then("both runs write the same SARIF log")
def same_log(runs):
    first, second = runs
    assert json.loads(first.stdout)["version"] == "2.1.0"
    assert first.stdout == second.stdout


@then("the SARIF log holds exactly these findings:")
def exact_findings(run, datatable):
    expected = sorted((row["rule"], row["file"], int(row["line"])) for row in rows(datatable))
    actual = sorted((result["ruleId"], *located(result)) for result in sarif_run(run.stdout)["results"])
    assert actual == expected


@then("every finding is in scope at position current, with no stage")
def all_current(run):
    for result in sarif_run(run.stdout)["results"]:
        assert result["properties"]["position"] == "current"
        assert "stage" not in result["properties"]
        assert result["message"]["text"].startswith("in scope: ")


@then("every finding carries the trace observation behind it")
def observations(run):
    for result in sarif_run(run.stdout)["results"]:
        (observation,) = result["properties"]["observations"]
        assert observation["method"] == "trace"
        assert observation["result"] == result["ruleId"].removeprefix("earnest/")
        assert observation["location"] == result["locations"][0]["physicalLocation"]
        assert f"`{observation['subject']}`" in result["message"]["text"]


@then("each finding at these places names its fix:")
def findings_name_fix(run, datatable):
    results = sarif_run(run.stdout)["results"]
    for row in rows(datatable):
        texts = [r["message"]["text"] for r in results if located(r) == (row["file"], int(row["line"]))]
        assert any(row["fix"] in text for text in texts), (row, texts)


@then("the SARIF log gives each requirement one trace level:")
def trace_levels(run, datatable):
    expected = {row["requirement"]: row["level"] for row in rows(datatable)}
    assert sarif_run(run.stdout)["properties"]["traceLevels"] == expected


@then("each untraced requirement has a located finding that names it")
def untraced_have_reasons(run):
    run_log = sarif_run(run.stdout)
    for requirement, level in run_log["properties"]["traceLevels"].items():
        if level == "untraced":
            assert any(f"`{requirement}`" in result["message"]["text"] for result in run_log["results"]), requirement


@then(parsers.parse("the SARIF log gives the traced percentage as {percent:d}"))
def traced_percentage(run, percent):
    assert sarif_run(run.stdout)["properties"]["percentages"]["traced"] == percent


@then(parsers.parse('the summary leads with "{text}"'))
def summary_leads(run, text):
    assert run.stderr.splitlines()[0] == text


@then("the check exits non-zero, with the SARIF log on stdout")
def exits_non_zero(run):
    assert run.returncode != 0
    assert sarif_run(run.stdout)["results"]
```

- [ ] **Step 8: Run the exit command and watch it fail**

Run: `uv run pytest tests/steps/test_trace_check.py`

Expected: FAIL, `5 failed`, each at its first `When` step with `FileNotFoundError: [Errno 2] No such file or directory: '…/packages/earnest/.venv/bin/earnest'`. It stays red until Task 9 declares the `earnest` script.

- [ ] **Step 9: Check that the rest of the suite and the linters pass**

Run: `uv run pytest tests/unit && make lint`

Expected: `1 passed` (the moved version test; nothing under `tests/fixtures` is collected), then `make lint` exits 0.

- [ ] **Step 10: Commit**

```bash
cd ../..
git add .markdownlint-cli2.jsonc Makefile packages/earnest/pyproject.toml packages/earnest/uv.lock packages/earnest/tests
git status --short
git commit -m "test: add the trace_check feature and the broken-links fixture"
```

### Task 2: The repository reader, `git.py`

**Files:**

- Create: `packages/earnest/src/earnest/git.py`
- Modify: `packages/earnest/tests/conftest.py` (append the `files_repo` fixture)
- Test: `packages/earnest/tests/unit/test_git.py`

**Interfaces:**

- Consumes: `_commit(repo: Path) -> Path` from `tests/conftest.py` (Task 1).
- Produces, in `earnest.git`:
  - `class GitError(Exception)`, raised when Git cannot answer; its message is Git's first non-empty stderr line.
  - `repo_root(cwd: Path) -> Path`: the top of the work tree that holds `cwd`.
  - `work_tree_files(root: Path) -> list[str]`: the files Git lists for the work tree, tracked files plus untracked files that are not ignored, each relative to `root` with forward slashes, sorted, and each once.
  - `head_commit(root: Path) -> str`: the full sha of `HEAD`.
- Produces, in `tests/conftest.py`: the fixture `files_repo`, a `Callable[[dict[str, str]], Path]` that writes the given files under `tmp_path / "repo"`, commits them on `main` and returns the repository.

- [ ] **Step 1: Write the failing tests**

Append to `packages/earnest/tests/conftest.py`:

```python


@pytest.fixture
def files_repo(tmp_path: Path) -> Callable[[dict[str, str]], Path]:
    """Return a builder that writes the given files into tmp_path / "repo" and commits them on main."""

    def build(files: dict[str, str]) -> Path:
        repo = tmp_path / "repo"
        for path, text in files.items():
            (repo / path).parent.mkdir(parents=True, exist_ok=True)
            (repo / path).write_text(text, encoding="utf-8")
        return _commit(repo)

    return build
```

Create `packages/earnest/tests/unit/test_git.py`. Git's own messages depend on the locale, so the test that reads one runs Git with `LC_ALL=C`:

```python
"""Tests for earnest.git: the work tree's root, the files Git lists for it, and its commit."""

import re

import pytest

from earnest import git


def test_work_tree_files_are_relative_to_the_root_even_with_spaces_and_accents(files_repo):
    repo = files_repo({"docs/a b.md": "a\n", "src/né.py": "x = 1\n", "top.ts": "let y = 2;\n"})
    assert git.work_tree_files(repo) == ["docs/a b.md", "src/né.py", "top.ts"]


def test_untracked_files_count_and_ignored_ones_do_not(files_repo):
    repo = files_repo({".gitignore": "build/\n", "a.md": "a\n"})
    (repo / "b.md").write_text("b\n", encoding="utf-8")
    (repo / "build").mkdir()
    (repo / "build" / "c.md").write_text("c\n", encoding="utf-8")
    assert git.work_tree_files(repo) == [".gitignore", "a.md", "b.md"]


def test_the_root_of_a_subdirectory_is_the_top_of_the_work_tree(files_repo):
    repo = files_repo({"packages/app/a.py": "x = 1\n"})
    assert git.repo_root(repo / "packages" / "app") == repo.resolve()


def test_the_head_commit_is_a_full_sha(files_repo):
    repo = files_repo({"a.md": "a\n"})
    assert re.fullmatch(r"[0-9a-f]{40}", git.head_commit(repo))


def test_a_directory_outside_any_work_tree_raises_git_errors_first_line(tmp_path, monkeypatch):
    monkeypatch.setenv("LC_ALL", "C")
    with pytest.raises(git.GitError) as error:
        git.repo_root(tmp_path)
    assert str(error.value).startswith("fatal: not a git repository")
    assert "\n" not in str(error.value)


def test_a_missing_git_raises_git_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(git.GitError, match="git is not on the PATH"):
        git.repo_root(tmp_path)
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/test_git.py -v`

Expected: FAIL at collection with `ImportError: cannot import name 'git' from 'earnest'`.

- [ ] **Step 3: Write `git.py`**

Create `packages/earnest/src/earnest/git.py`. `ls-files` lists the files the shared decision names: `--cached` the tracked files and `--others --exclude-standard` the untracked files that are not ignored. `-z` keeps names with spaces and accents unquoted, and `--show-toplevel` makes a check from a subdirectory read the whole work tree. A failure keeps only Git's first non-empty stderr line, since Git adds a second line when discovery stops at a mount point. `shutil.which` gives the absolute path ruff's S607 asks for; S603 stays, with its `noqa`, because every argument is a fixed Git subcommand:

```python
"""Repository reader: the work tree's root, the files Git lists for it, and its commit, read through Git."""

import shutil
import subprocess
from pathlib import Path


class GitError(Exception):
    """Git could not answer: no work tree, no commit, or no `git` on the PATH; the message is Git's first line."""


def repo_root(cwd: Path) -> Path:
    """Return the top of the work tree that holds cwd, so a check run in a subdirectory reads the whole repository."""
    return Path(_git(cwd, "rev-parse", "--show-toplevel").removesuffix("\n"))


def work_tree_files(root: Path) -> list[str]:
    """Return the files Git lists for the work tree: tracked files plus untracked files that are not ignored.

    Each path is relative to root, with forward slashes, sorted, and listed once, even a file in a merge conflict,
    which the index holds three times.
    """
    listed = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return sorted({path for path in listed.split("\0") if path})


def head_commit(root: Path) -> str:
    """Return the full sha of the commit HEAD names."""
    return _git(root, "rev-parse", "HEAD").strip()


def _git(cwd: Path, *args: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        msg = "git is not on the PATH"
        raise GitError(msg)
    done = subprocess.run([executable, *args], cwd=cwd, capture_output=True, check=False)  # noqa: S603
    if done.returncode != 0:
        lines = done.stderr.decode(errors="replace").splitlines()
        msg = next((line.strip() for line in lines if line.strip()), f"git {args[0]} failed")
        raise GitError(msg)
    # decoded from bytes, so no newline is translated, and a name that is not UTF-8 reaches the file system intact
    return done.stdout.decode("utf-8", "surrogateescape")
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/test_git.py -v && make lint`

Expected: `6 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/git.py tests/conftest.py tests/unit/test_git.py
git commit -m "feat: read the work tree's files, root and commit through git"
```

### Task 3: The Markdown grammar and the Near-miss table, `index.py`

**Files:**

- Create: `packages/earnest/src/earnest/index.py`
- Test: `packages/earnest/tests/unit/test_index.py`

**Interfaces:**

- Consumes: nothing from earlier tasks.
- Produces, in `earnest.index`; later tasks use exactly these names and fields:
  - Surface names `MARKDOWN = "markdown"`, `COMMENT = "comment"`, `GHERKIN = "gherkin"`; `TYPES`, the eleven item types of the Item types table; and `KEYS`, the six keys a key line opens with.
  - `Line(number: int, text: str)`, frozen.
  - `split_lines(text: str) -> tuple[Line, ...]`: text's lines numbered from 1, split at each newline alone, as Git counts them. Every adapter that splits text itself uses it.
  - `Source(path: str, surface: str, lines: tuple[Line, ...], fenced: frozenset[int] = frozenset())`, frozen. For Markdown, `lines` holds every line and `fenced` the fenced ones; for the comment and Gherkin surfaces, `lines` holds the comment or tag lines.
  - `Id(type: str, name: str, revision: int)`, frozen; `str(id)` gives `type~name~revision`, and `id.key -> tuple[str, str]` gives the type and name, which pick the item an id names.
  - `Item(id: Id, path: str, line: int, needs: tuple[str, ...] | None = None)`, frozen; `needs` is None without a valid `Needs:` line.
  - `Link(key: str, type: str, target: Id, path: str, line: int, owner: Id | None = None)`, frozen; `key` is `Covers`, `Drivers`, `Delivers` or `Depends`, `type` the naming item's type or the tag's artifact type, `owner` the item whose key line names `target`.
  - `NearMiss(path: str, line: int, text: str, fix: str)`, frozen.
  - `Index(items: tuple[Item, ...], links: tuple[Link, ...], near_misses: tuple[NearMiss, ...])`, frozen, whose `defined` is a `functools.cached_property`, `dict[tuple[str, str], Item]`: the first item of each `Id.key`.
  - `build_index(sources: Iterable[Source]) -> Index`; this task reads Markdown sources, and Task 4 adds the tag surfaces.

- [ ] **Step 1: Write the failing tests**

Create `packages/earnest/tests/unit/test_index.py`:

```python
"""Tests for earnest.index: the grammar, the Near-miss table and Reference resolution."""

import pytest

from earnest.index import MARKDOWN, Id, Item, Line, Source, build_index, split_lines


def markdown(text, fenced=frozenset()):
    return Source("docs/a.md", MARKDOWN, split_lines(text), fenced)


def test_lines_split_at_each_newline_alone_as_git_counts_them():
    assert split_lines("a\rb\x0bc\x0cd\x1ce\x85f\ng\n") == (Line(1, "a\rb\x0bc\x0cd\x1ce\x85f"), Line(2, "g"))
    assert split_lines("a\n\nb") == (Line(1, "a"), Line(2, ""), Line(3, "b"))
    assert split_lines("") == ()


def test_an_item_runs_from_its_id_line_to_the_next_id_line_or_heading():
    text = (
        "`req~a~2`\n\nWhen x, the s shall y.\n\nNeeds: impl, itest\nCovers: feat~f~1, feat~g~1\n"
        "### `req~b~1`\n\nCovers: feat~f~1\n   ## Notes\n\nCovers: feat~h~1\n"
    )
    index = build_index([markdown(text)])
    assert index.items == (
        Item(Id("req", "a", 2), "docs/a.md", 1, ("impl", "itest")),
        Item(Id("req", "b", 1), "docs/a.md", 7),
    )
    assert [(link.owner, str(link.target), link.line) for link in index.links] == [
        (Id("req", "a", 2), "feat~f~1", 6),
        (Id("req", "a", 2), "feat~g~1", 6),
        (Id("req", "b", 1), "feat~f~1", 9),
    ]
    assert index.near_misses == ()


@pytest.mark.parametrize("line", ["`req~b~1`", "## `req~b~1`", "   ## `req~b~1`", "#\t`req~b~1`", "## `req~b~1` ##"])
def test_an_id_line_stands_alone_or_in_an_atx_heading_whose_closing_run_is_no_text(line):
    index = build_index([markdown(f"{line}\nCovers: feat~f~1\n")])
    assert [str(link.owner) for link in index.links] == ["req~b~1"]
    assert index.near_misses == ()


def test_text_after_a_backticked_token_that_is_no_id_is_body():
    index = build_index([markdown("`req~a~1`\n`~/.config/app` holds the cache\nCovers: feat~f~1\n")])
    assert [str(link.target) for link in index.links] == ["feat~f~1"]
    assert index.near_misses == ()


def test_a_lone_backticked_token_that_is_no_id_is_body():
    index = build_index([markdown("`req~a~1`\n`~/.config`\nCovers: feat~f~1\n")])
    assert [str(link.target) for link in index.links] == ["feat~f~1"]
    assert index.near_misses == ()


@pytest.mark.parametrize(
    ("line", "fix"),
    [
        ("`req~x`", "append `~` and the item's current revision"),
        ("### `req~Login~1`", "lower-case the name"),
        ("`req~login_rate~1`", "rewrite it as `type~name~revision` in backticks"),
        ("`req~b~1` Login rate limit", "put the id alone on its line and move the text into the body"),
        ("## `req~b~1` Login rate limit", "put the id alone on its line and move the text into the body"),
        ("`rq~rate-limit~1`", "use a known item type, such as `req`"),
        ("`Req~a~1`", "rewrite it as `type~name~revision` in backticks"),
        ("`rq~x~1` text", "use a known item type, such as `req`"),
    ],
)
def test_a_malformed_id_line_is_a_near_miss_that_ends_the_item_above(line, fix):
    index = build_index([markdown(f"`req~a~1`\n{line}\nCovers: feat~f~1\n")])
    assert [str(item.id) for item in index.items] == ["req~a~1"]
    (miss,) = index.near_misses
    assert miss.line == 2
    assert miss.fix.startswith(fix)
    assert index.links == ()


@pytest.mark.parametrize(
    ("line", "text", "fix"),
    [
        ("Covers: feat~f~1, FR1.2", "FR1.2", "lower-case it, turn dots into hyphens"),
        ("Covers: feat~x", "feat~x", "append `~`"),
        ("Delivers: req~Login~1", "req~Login~1", "lower-case the name"),
        ("Depends: task~set_up~1", "task~set_up~1", "rewrite it as `type~name~revision`"),
        ("Covers: fet~f~1", "fet~f~1", "use a known item type, such as `feat`"),
        ("Covers: @stest:feat~f~1", "@stest:feat~f~1", "rewrite it as `type~name~revision`"),
        ("Needs: impl, utst", "utst", "use a known item type, such as `utest`"),
        ("Needs: Impl", "Impl", "rewrite it as item types"),
        ("Override: req~a~1 implemented 3f9c2a1, why", "req~a~1 implemented 3f9c2a1, why", "rewrite it as `type~"),
        ("Covers:", "Covers:", "name at least one id, separated by `, `, with no empty entry"),
        ("Covers: feat~f~1,", "Covers: feat~f~1,", "name at least one id"),
        ("Covers: , feat~f~1", "Covers: , feat~f~1", "name at least one id"),
        ("Covers: feat~f~1,feat~g~1", "Covers: feat~f~1,feat~g~1", "name at least one id"),
        ("Needs: impl,utest", "Needs: impl,utest", "name at least one id"),
        ("Needs: impl utest", "Needs: impl utest", "name at least one id"),
    ],
)
def test_a_key_line_value_that_fails_its_grammar_is_a_near_miss(line, text, fix):
    index = build_index([markdown(f"`req~a~1`\n{line}\n")])
    (miss,) = index.near_misses
    assert (miss.line, miss.text) == (2, text)
    assert miss.fix.startswith(fix)


@pytest.mark.parametrize(
    ("line", "key"),
    [
        ("**Covers:** feat~f~1", "Covers"),
        ("covers: feat~f~1", "Covers"),
        ("Covers:feat~f~1", "Covers"),
        ("_Needs_: impl", "Needs"),
        ("Delivers :  req~a~1", "Delivers"),
        ("- Covers: feat~f~1", "Covers"),
        ("  Depends: task~t~1", "Depends"),
        ("> Needs: impl", "Needs"),
    ],
)
def test_a_key_not_written_exactly_is_a_near_miss_that_names_the_key(line, key):
    index = build_index([markdown(f"`req~a~1`\n{line}\n")])
    (miss,) = index.near_misses
    assert miss.text == line
    assert miss.fix == (
        f"write the key exactly as `{key}: `, with a capital, no formatting and one space after the colon"
    )
    assert index.links == ()


def test_a_key_that_only_unicode_case_folding_would_match_is_body():
    index = build_index([markdown("`req~a~1`\nNeed\u017f: impl\n")])  # U+017F, the long s
    assert index.items[0].needs is None
    assert index.near_misses == ()


def test_the_entries_beside_an_empty_one_still_link():
    index = build_index([markdown("`req~a~1`\nCovers: feat~f~1,\n")])
    assert [str(link.target) for link in index.links] == ["feat~f~1"]


def test_a_valid_needs_line_and_an_override_line_parse_cleanly():
    text = "`req~a~1`\nNeeds: impl, utest\nOverride: req~a~1 implemented at 3f9c2a1, lives in the gateway\n"
    index = build_index([markdown(text)])
    assert index.items[0].needs == ("impl", "utest")
    assert index.near_misses == ()


def test_fenced_lines_never_start_end_or_key_an_item():
    text = "`req~a~1`\n~~~\n# heading\n`req~b~1`\nCovers: FR1.2\n~~~\nCovers: feat~f~1\n"
    index = build_index([markdown(text, frozenset({2, 3, 4, 5, 6}))])
    assert [str(item.id) for item in index.items] == ["req~a~1"]
    assert [str(link.target) for link in index.links] == ["feat~f~1"]
    assert index.near_misses == ()


def test_defined_keeps_the_first_item_of_each_type_and_name():
    index = build_index([markdown("`req~a~1`\n`req~a~2`\n")])
    assert len(index.items) == 2
    assert index.defined[Id("req", "a", 2).key].line == 1
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/test_index.py -v`

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'earnest.index'`.

- [ ] **Step 3: Write `index.py` with the Markdown grammar**

The Grammar section of `01` gives the rules this step writes down: the item span, ATX headings, key lines and their decoration, lists separated by a comma and one space, and the `Override:` value; the comments and docstrings below carry each rule. `_ID` takes its type from `TYPES`, so an unknown type fails the grammar like any other mismatch. `split_lines` splits at each newline alone: `str.splitlines` also splits at a form feed or a line separator, which would shift every line number below it. Every pattern splits each run at a single point, so no line makes one backtrack more than linearly.

Create `packages/earnest/src/earnest/index.py`:

```python
"""Grammar and index: items, links and near-misses from the lines the host adapters hand over."""

import difflib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property


MARKDOWN = "markdown"
COMMENT = "comment"
GHERKIN = "gherkin"
TYPES = ("tenet", "goal", "feat", "req", "dsn", "unit", "task", "impl", "utest", "itest", "stest")
KEYS = ("Needs", "Covers", "Drivers", "Delivers", "Depends", "Override")

_TYPE = f"({'|'.join(TYPES)})"
_ID = rf"{_TYPE}~([a-z0-9-]+)~([1-9][0-9]*)"
_ID_ENTRY = re.compile(_ID)
_TYPE_ENTRY = re.compile(_TYPE)
_ATX = r"#{1,6}(?:[ \t]+|$)"  # the marks that open an ATX heading, after up to three spaces
_HEADING = re.compile(rf" {{0,3}}{_ATX}")
# An id-line candidate: a backticked token that opens with a word of letters and a `~`, alone on its line or after
# heading marks, with text after it or none, where a heading's closing run of `#` is no text. Any other backticked
# token, such as `~/.config`, is body text.
_ID_LINE = re.compile(rf" {{0,3}}({_ATX})?`([A-Za-z]+~[^`]*)`(?(1)(?:[ \t]+#+$)?)(.*)")
_KEY_NAME = f"({'|'.join(KEYS)})"
# A key line as written, or decorated: indentation, list and quote markers and emphasis may come before its key. Its
# letters fold case in ASCII alone, so a letter such as the long s, which Unicode folds to `s`, stands in for none.
_KEY = re.compile(rf"[ \t]*(?:(?:[-*+]|[0-9]+\.)[ \t]+|>[ \t]*)*[*_]*{_KEY_NAME}[*_]*[ \t]*:", re.IGNORECASE | re.ASCII)
_KEY_LINE = re.compile(rf"{_KEY_NAME}:(?: (\S.*))?")
_OVERRIDE = re.compile(rf"{_ID} (?:implemented|tested) at [0-9a-f]+,.+")
_SEPARATORS = re.compile(r"[\s,]+")
_TYPE_SLOT = re.compile(r"(?:^|[\[@:>]\s*)([a-z]+)(?=\s*(?:->|[:~]|$))")

# The Near-miss table of the logic design, in order, for text that fails the grammar of its place: the first row that
# applies at that place (None for every place) and whose pattern fits gives the canned fix. `_keys` checks the key and
# empty-value rows on a whole key line before its entries reach this table, and `_fix` the unknown-type row after it.
_FIXES: tuple[tuple[str | None, re.Pattern[str], str], ...] = (
    (None, re.compile(r"\[\s*[a-z]+\s*-[^>]"), "write `->` between the artifact type and the id"),
    (None, re.compile(r"(?:^|->|:)\s*[A-Za-z]+~[^~\s\]]+\s*\]?$"), "append `~` and the item's current revision"),
    (None, re.compile(r"(?<![a-z])[a-z]+~[^~\sA-Z]*[A-Z][^~\s]*~"), "lower-case the name"),
    (GHERKIN, re.compile(r"^@[a-z]+[ \t]+[a-z]+~"), "put `:` between the artifact type and the id"),
    (
        None,
        re.compile(r"^[A-Z]+-?[0-9]+(?:\.[0-9]+)*$"),
        "lower-case it, turn dots into hyphens, and add the type and the revision, so `FR1.2` becomes `req~fr1-2~1`",
    ),
    ("id line", re.compile(rf"^{_ID}[ \t]"), "put the id alone on its line and move the text into the body"),
)
_KEY_FIX = "write the key exactly as `{}: `, with a capital, no formatting and one space after the colon"
_EMPTY_FIX = "name at least one id, separated by `, `, with no empty entry"
_NAME_RULE = "a name of lower-case letters, digits and hyphens, and a revision from 1"
_FORMS = {
    "id line": f"`type~name~revision` in backticks, alone on its line or after heading marks, with {_NAME_RULE}",
    "id": f"`type~name~revision`, with {_NAME_RULE}",
    "Needs": "item types separated by a comma and a space, such as `impl, utest`",
    "Override": f"`type~name~revision implemented at commit, reason`, or `tested` for tests, with {_NAME_RULE}",
}


@dataclass(frozen=True)
class Line:
    """One line a host adapter hands to the grammar, numbered from 1."""

    number: int
    text: str


@dataclass(frozen=True)
class Source:
    """One listed file as its host adapter saw it.

    For Markdown, `lines` holds every line and `fenced` the lines inside code fences. For the comment and Gherkin
    surfaces, `lines` holds the comment or tag lines.
    """

    path: str
    surface: str
    lines: tuple[Line, ...]
    fenced: frozenset[int] = frozenset()


@dataclass(frozen=True)
class Id:
    """An item id: type, name and revision."""

    type: str
    name: str
    revision: int

    @property
    def key(self) -> tuple[str, str]:
        """Return the type and name, which pick the item an id names whatever its revision."""
        return self.type, self.name

    def __str__(self) -> str:
        """Return the id as it is written, `type~name~revision`."""
        return f"{self.type}~{self.name}~{self.revision}"


@dataclass(frozen=True)
class Item:
    """A Markdown item: its id, where its id line sits, and the types on its `Needs:` line."""

    id: Id
    path: str
    line: int
    needs: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Link:
    """An id named by a key line or a tag, and where it was written.

    `type` is the naming item's type, or the tag's artifact type. `owner` is the item whose key line names the
    target, and is None for a tag.
    """

    key: str
    type: str
    target: Id
    path: str
    line: int
    owner: Id | None = None


@dataclass(frozen=True)
class NearMiss:
    """Text that nearly parses as a tag, an id line or a key line, with its canned fix."""

    path: str
    line: int
    text: str
    fix: str


@dataclass(frozen=True)
class Index:
    """The graph that the check and the judge share."""

    items: tuple[Item, ...]
    links: tuple[Link, ...]
    near_misses: tuple[NearMiss, ...]

    @cached_property
    def defined(self) -> dict[tuple[str, str], Item]:
        """Map each type and name to the first item that defines it; later items with that id are duplicates."""
        found: dict[tuple[str, str], Item] = {}
        for item in self.items:
            found.setdefault(item.id.key, item)
        return found


_Parsed = tuple[list[Item], list[Link], list[NearMiss]]


def split_lines(text: str) -> tuple[Line, ...]:
    """Number text's lines from 1, split at each newline alone, as Git counts them; a final newline adds no line."""
    return tuple(Line(number, raw) for number, raw in enumerate(text.removesuffix("\n").split("\n"), 1)) if text else ()


def build_index(sources: Iterable[Source]) -> Index:
    """Parse every source into one index, keeping the order of the sources and of their lines."""
    items: list[Item] = []
    links: list[Link] = []
    misses: list[NearMiss] = []
    for source in sources:
        if source.surface == MARKDOWN:
            found_items, found_links, found_misses = _markdown(source)
            items.extend(found_items)
            links.extend(found_links)
            misses.extend(found_misses)
    return Index(tuple(items), tuple(links), tuple(misses))


def _to_id(match: re.Match[str], first: int = 1) -> Id:
    return Id(match.group(first), match.group(first + 1), int(match.group(first + 2)))


def _fix(text: str, place: str) -> str:
    """Return the canned fix of the first Near-miss row that fits text written at place."""
    for where, pattern, fix in _FIXES:
        if where in (None, place) and pattern.search(text):
            return fix
    unknown = [word for word in _TYPE_SLOT.findall(text) if word not in TYPES]
    if unknown:
        closest = difflib.get_close_matches(unknown[0], TYPES, n=1, cutoff=0)[0]
        return f"use a known item type, such as `{closest}`"
    return f"rewrite it as {_FORMS[place]}"


def _markdown(source: Source) -> _Parsed:
    items: list[Item] = []
    links: list[Link] = []
    spans, misses = _spans(source)
    for item_id, number, lines in spans:
        needs, item_links, key_misses = _keys(source.path, item_id, lines)
        items.append(Item(item_id, source.path, number, needs))
        links.extend(item_links)
        misses.extend(key_misses)
    return items, links, misses


def _spans(source: Source) -> tuple[list[tuple[Id, int, list[Line]]], list[NearMiss]]:
    """Split a Markdown file into items: an id line owns the lines up to the next id line or ATX heading."""
    spans: list[tuple[Id, int, list[Line]]] = []
    misses: list[NearMiss] = []
    body: list[Line] | None = None
    for line in source.lines:
        if line.number in source.fenced:
            continue  # fenced code is body, and never starts, ends or keys an item
        text = line.text.rstrip()
        if loose := _ID_LINE.fullmatch(text):
            token, after = loose.group(2, 3)
            strict = None if after else _ID_ENTRY.fullmatch(token)
            if strict is None:
                misses.append(NearMiss(source.path, line.number, token + after, _fix(token + after, "id line")))
                body = None  # a malformed id line ends the item above it, as an id line would
            else:
                body = []
                spans.append((_to_id(strict), line.number, body))
        elif _HEADING.match(text):
            body = None
        elif body is not None:
            body.append(line)
    return spans, misses


def _keys(path: str, owner: Id, lines: Iterable[Line]) -> tuple[tuple[str, ...] | None, list[Link], list[NearMiss]]:
    """Read an item's key lines: its needs, its links, and every key, value or entry that fails to parse."""
    needs: tuple[str, ...] | None = None
    links: list[Link] = []
    misses: list[NearMiss] = []
    for line in lines:
        text = line.text.rstrip()
        if (key := _KEY.match(text)) is None:
            continue
        if (exact := _KEY_LINE.fullmatch(text)) is None:
            misses.append(NearMiss(path, line.number, text, _KEY_FIX.format(key.group(1).capitalize())))
            continue
        name, value = exact.group(1), exact.group(2) or ""
        if name == "Override":
            if not _OVERRIDE.fullmatch(value):
                misses.append(NearMiss(path, line.number, value or text, _fix(value, name)))
        elif name == "Needs":
            types, found = _list(path, line, value, _TYPE_ENTRY, name)
            misses.extend(found)
            if not found:
                needs = tuple(entry.group() for entry in types)
        else:
            ids, found = _list(path, line, value, _ID_ENTRY, "id")
            misses.extend(found)
            links.extend(Link(name, owner.type, _to_id(entry), path, line.number, owner=owner) for entry in ids)
    return needs, links, misses


def _list(
    path: str, line: Line, value: str, grammar: re.Pattern[str], place: str
) -> tuple[list[re.Match[str]], list[NearMiss]]:
    """Read a list value: the entries that parse, and a near-miss for each that does not.

    Entries are separated by exactly `, `. Any other separator, or an empty entry, fails the whole line once, and each
    entry is still read.
    """
    entries = [entry for entry in _SEPARATORS.split(value) if entry]
    misses: list[NearMiss] = []
    if not entries or ", ".join(entries) != value:
        misses.append(NearMiss(path, line.number, line.text.rstrip(), _EMPTY_FIX))
    parsed: list[re.Match[str]] = []
    for entry in entries:
        if match := grammar.fullmatch(entry):
            parsed.append(match)
        else:
            misses.append(NearMiss(path, line.number, entry, _fix(entry, place)))
    return parsed, misses
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/test_index.py -v && make lint`

Expected: `45 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/index.py tests/unit/test_index.py
git commit -m "feat: parse Markdown items, key lines and near-misses into the index"
```

### Task 4: Tag surfaces and Reference resolution, `index.py`

**Files:**

- Modify: `packages/earnest/src/earnest/index.py` (two `_FORMS` rows, the tag patterns, `Resolution`, `Index.resolutions`, `build_index`, `_tags` at the end)
- Test: `packages/earnest/tests/unit/test_index.py` (import line, and tests appended)

**Interfaces:**

- Consumes: everything Task 3 produces in `earnest.index`.
- Produces:
  - `build_index(sources: Iterable[Source]) -> Index` now also reads `COMMENT` and `GHERKIN` sources. Each tag that parses becomes `Link("Covers", <artifact type>, <target Id>, path, line)`, with `owner` None; each tag candidate that fails its surface's grammar becomes a `NearMiss`. A bracket tag takes OFT's optional whitespace after `[`, around `->` and before `]`, and the `@` forms are candidates only on the Gherkin surface.
  - `Resolution(item: Item | None, status: str, closest: Id | None = None)`, frozen: the item a written id names by type and name, and `status` `resolved`, `outdated`, `predated` or `orphaned`; an orphaned id's `closest` is the nearest id of its own type, when one is close enough to suggest.
  - `Index.resolutions`, a `functools.cached_property`, `dict[Id, Resolution]`: Reference resolution of each id the links name, computed once per id written. `index.py` owns Reference resolution (G7); `structural.py` only turns each status into findings.

- [ ] **Step 1: Write the failing tests**

In `packages/earnest/tests/unit/test_index.py`, replace:

```python
from earnest.index import MARKDOWN, Id, Item, Line, Source, build_index, split_lines
```

with:

```python
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Id, Item, Line, Link, Source, build_index, split_lines
```

Append to `packages/earnest/tests/unit/test_index.py`:

```python


def comments(*lines):
    return Source("src/a.py", COMMENT, tuple(Line(number, text) for number, text in lines))


def gherkin(*lines):
    return Source("tests/a.feature", GHERKIN, tuple(Line(number, text) for number, text in lines))


def test_a_comment_tag_covers_its_target_from_its_artifact_type_with_or_without_spaces():
    index = build_index([comments((3, "# see [impl->req~a~2] and [ utest -> req~b~1 ]"))])
    assert index.links == (
        Link("Covers", "impl", Id("req", "a", 2), "src/a.py", 3),
        Link("Covers", "utest", Id("req", "b", 1), "src/a.py", 3),
    )
    assert index.near_misses == ()


@pytest.mark.parametrize(
    ("source", "fix"),
    [
        (comments((1, "# [impl-req~x~1]")), "write `->`"),
        (comments((1, "# [ impl-req~x~1 ]")), "write `->`"),
        (comments((1, "# [impl->req~x]")), "append `~`"),
        (comments((1, "# [impl->req~x_y~1]")), "rewrite it as `[type->type~name~revision]`"),
        (comments((1, "# [impel->req~x~1]")), "use a known item type, such as `impl`"),
        (gherkin((1, "@stest:feat~Login~1")), "lower-case the name"),
        (gherkin((1, "@stest feat~login~1")), "put `:`"),
        (gherkin((1, "@stest:fet~login~1")), "use a known item type, such as `feat`"),
        (gherkin((1, "@stest:feat~login~1,")), "rewrite it as `@type:type~name~revision`"),
    ],
)
def test_a_tag_that_fails_its_surface_is_a_near_miss(source, fix):
    (miss,) = build_index([source]).near_misses
    assert miss.fix.startswith(fix)


def test_a_line_of_bracket_and_arrow_runs_parses_at_once():
    line = "# [" + "->~" * 2000 + " [impl->req~a~1]"
    assert build_index([comments((1, line))]).links == (Link("Covers", "impl", Id("req", "a", 1), "src/a.py", 1),)


def test_at_forms_are_tags_only_on_the_gherkin_surface():
    index = build_index(
        [
            gherkin((1, "@smoke @stest:feat~a~1")),
            comments((1, "/** @see req~x~1 */"), (2, "// @stest feat~y~1, and user@host:~/notes")),
        ]
    )
    assert [str(link.target) for link in index.links] == ["feat~a~1"]
    assert index.near_misses == ()


def test_each_written_id_resolves_once_by_type_and_name_then_by_revision():
    items = markdown("`feat~login~2`\n`req~login~1`\n")
    tags = comments(
        (1, "# [impl->feat~login~2] [impl->feat~login~1] [impl->feat~login~3]"),
        (2, "# [impl->feat~logn~2] [impl->feat~logn~2] [impl->dsn~login~1]"),
    )
    index = build_index([items, tags])
    feat = index.defined[Id("feat", "login", 2).key]
    assert {
        str(target): (resolution.item, resolution.status, resolution.closest)
        for target, resolution in index.resolutions.items()
    } == {
        "feat~login~2": (feat, "resolved", None),
        "feat~login~1": (feat, "outdated", None),
        "feat~login~3": (feat, "predated", None),
        "feat~logn~2": (None, "orphaned", Id("feat", "login", 2)),
        "dsn~login~1": (None, "orphaned", None),
    }
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/test_index.py -v`

Expected: FAIL, the 13 new tests red (`build_index` still reads only Markdown, so `index.links` is empty, `(miss,) =` finds no near-miss, and `Index` has no `resolutions`) and the 45 Markdown tests green: `13 failed, 45 passed`.

- [ ] **Step 3: Add the tag surfaces and Reference resolution**

The candidate patterns and `Index.resolutions` carry their rules in their comments and docstrings. In `packages/earnest/src/earnest/index.py`, replace:

```python
_NAME_RULE = "a name of lower-case letters, digits and hyphens, and a revision from 1"
_FORMS = {
```

with:

```python
_NAME_RULE = "a name of lower-case letters, digits and hyphens, and a revision from 1"
_FORMS = {
    COMMENT: f"`[type->type~name~revision]`, with {_NAME_RULE}",
    GHERKIN: f"`@type:type~name~revision`, with {_NAME_RULE}",
```

In the same file, replace:

```python
    "Override": f"`type~name~revision implemented at commit, reason`, or `tested` for tests, with {_NAME_RULE}",
}
```

with:

```python
    "Override": f"`type~name~revision implemented at commit, reason`, or `tested` for tests, with {_NAME_RULE}",
}
# Each run ends where the next part begins, at the first `->` or `~`, so no line backtracks more than linearly.
_BRACKET = r"\[\s*(?:(?:[^\[\]\s>-]+\s*)?->\s*)?[^\[\]\s~]*~[^\[\]\s]*\s*\]"
_TAG_FORMS = {
    COMMENT: re.compile(rf"\[\s*{_TYPE}\s*->\s*{_ID}\s*\]"),
    GHERKIN: re.compile(rf"@{_TYPE}:{_ID}"),
}
# A tag candidate is the near-miss superset of a surface: a bracketed token with a `~` inside, spaced as OFT allows, and
# on the Gherkin surface alone a token that opens with `@` and holds a `~`, including `@stest feat~login~1`. A JSDoc
# `@see req~x~1` in a comment is therefore no candidate.
_TAG_CANDIDATES = {
    COMMENT: re.compile(_BRACKET),
    GHERKIN: re.compile(rf"{_BRACKET}|(?<!\S)@[a-z]+[ \t]+[a-z]+~\S*|(?<!\S)@[^\s@~]*~\S*"),
}
```

In the same file, replace:

```python
@dataclass(frozen=True)
class Index:
```

with:

```python
@dataclass(frozen=True)
class Resolution:
    """What a written id names: its item, and `resolved`, `outdated`, `predated` or `orphaned`.

    An orphaned id carries the closest id of its own type, when one is close enough to suggest.
    """

    item: Item | None
    status: str
    closest: Id | None = None


@dataclass(frozen=True)
class Index:
```

In the same file, replace:

```python
            found.setdefault(item.id.key, item)
        return found
```

with:

```python
            found.setdefault(item.id.key, item)
        return found

    @cached_property
    def resolutions(self) -> dict[Id, Resolution]:
        """Resolve each id the links name, once per id written, by type and name and then by revision."""
        return {target: self._resolve(target) for target in dict.fromkeys(link.target for link in self.links)}

    def _resolve(self, target: Id) -> Resolution:
        item = self.defined.get(target.key)
        if item is None:
            same_type = {found.id.name: found.id for found in self.defined.values() if found.id.type == target.type}
            close = difflib.get_close_matches(target.name, same_type, n=1)
            return Resolution(None, "orphaned", same_type[close[0]] if close else None)
        if target.revision < item.id.revision:
            return Resolution(item, "outdated")
        if target.revision > item.id.revision:
            return Resolution(item, "predated")
        return Resolution(item, "resolved")
```

In the same file, replace:

```python
    for source in sources:
        if source.surface == MARKDOWN:
            found_items, found_links, found_misses = _markdown(source)
            items.extend(found_items)
            links.extend(found_links)
            misses.extend(found_misses)
    return Index(tuple(items), tuple(links), tuple(misses))
```

with:

```python
    for source in sources:
        parse = _markdown if source.surface == MARKDOWN else _tags
        found_items, found_links, found_misses = parse(source)
        items.extend(found_items)
        links.extend(found_links)
        misses.extend(found_misses)
    return Index(tuple(items), tuple(links), tuple(misses))
```

Append to `packages/earnest/src/earnest/index.py`:

```python


def _tags(source: Source) -> _Parsed:
    strict = _TAG_FORMS[source.surface]
    links: list[Link] = []
    misses: list[NearMiss] = []
    for line in source.lines:
        for candidate in _TAG_CANDIDATES[source.surface].finditer(line.text):
            text = candidate.group()
            if tag := strict.fullmatch(text):
                links.append(Link("Covers", tag.group(1), _to_id(tag, 2), source.path, line.number))
            else:
                misses.append(NearMiss(source.path, line.number, text, _fix(text, source.surface)))
    return [], links, misses
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/test_index.py -v && make lint`

Expected: `58 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/index.py tests/unit/test_index.py
git commit -m "feat: parse comment and Gherkin tags, and resolve each written id"
```

### Task 5: The comment adapters, Python and TypeScript

**Files:**

- Create: `packages/earnest/src/earnest/adapters/__init__.py` (its docstring; Task 6 fills it in)
- Create: `packages/earnest/src/earnest/adapters/python.py`
- Create: `packages/earnest/src/earnest/adapters/typescript.py`
- Create: `packages/earnest/tests/unit/adapters/__init__.py`
- Test: `packages/earnest/tests/unit/adapters/test_python.py`, `packages/earnest/tests/unit/adapters/test_typescript.py`

**Interfaces:**

- Consumes: `Line` from `earnest.index` (Task 3).
- Produces: `earnest.adapters.python.scan(text: str) -> tuple[Line, ...]` and `earnest.adapters.typescript.scan(text: str) -> tuple[Line, ...]`. Each returns the file's comment lines, one `Line` per physical line with its comment text. Task 6 maps `.py` to the first, and `.ts`, `.tsx`, `.mts` and `.cts` to the second, under the `COMMENT` surface.

- [ ] **Step 1: Write the failing tests**

```bash
mkdir -p tests/unit/adapters
touch tests/unit/adapters/__init__.py
```

Create `packages/earnest/tests/unit/adapters/test_python.py`:

```python
"""Tests for the Python host adapter."""

from earnest.adapters import python
from earnest.index import Line


def test_comments_come_with_their_line_numbers_and_strings_stay_text():
    lines = python.scan('x = "# not a comment"  # [impl->req~a~1]\n\ny = """\n# inside a string\n"""  # second\n')
    assert lines == (Line(1, "# [impl->req~a~1]"), Line(5, "# second"))


def test_a_file_that_stops_tokenizing_keeps_the_comments_before_the_error():
    assert python.scan("# [impl->req~a~1]\ndef f(:\n    x = (\n") == (Line(1, "# [impl->req~a~1]"),)


def test_a_comment_after_a_lone_carriage_return_is_read_on_the_line_git_counts():
    assert python.scan("x = 1\r# [impl->req~r~1]\n") == (Line(1, "# [impl->req~r~1]"),)
```

Create `packages/earnest/tests/unit/adapters/test_typescript.py`. Each regular expression case sits above a string that holds a tag and a comment that holds one: a regex read as a template would swallow the comment, and one read as a comment would turn the string into a tag:

```python
"""Tests for the TypeScript host adapter."""

import pytest

from earnest.adapters import typescript
from earnest.index import Line


def test_line_and_block_comments_are_read_line_by_line():
    lines = typescript.scan("// [impl->req~a~1]\nconst x = 1; /* one\n[impl->req~b~1] */\n")
    assert lines == (Line(1, "// [impl->req~a~1]"), Line(2, "/* one"), Line(3, "[impl->req~b~1] */"))


def test_tag_shaped_text_inside_strings_and_template_literals_is_text():
    text = (
        'const url = "https://example.com/[impl->req~a~1]";\n'
        "const note = 'a // b';\n"
        "const t = `line // [impl->req~b~1]\n${f(x)} // still text`;\n"
        "// [impl->req~c~1]\n"
    )
    assert typescript.scan(text) == (Line(5, "// [impl->req~c~1]"),)


@pytest.mark.parametrize(
    "code",
    [
        's = s.replace(/`/g, "");',
        "const trail = /\\/*$/;",
        "return /\\/*/.test(s);",
        "const quote = /[/`]/;",
    ],
)
def test_a_regular_expression_literal_opens_no_template_or_comment(code):
    text = f'{code}\nconst s = "[impl->req~x~1]";\n// [impl->req~a~1]\n'
    assert typescript.scan(text) == (Line(3, "// [impl->req~a~1]"),)


@pytest.mark.parametrize(
    "code",
    [
        "const half = total / 2;",
        "const ratio = (a + b) / c;",
        "i++ / 2;",
        "x! / 2;",
        "obj.return / 2;",
        "return <p>Loading</p>;",
    ],
)
def test_a_slash_that_divides_or_closes_a_jsx_tag_opens_no_regular_expression(code):
    assert typescript.scan(f"{code} // [impl->req~a~1]\n") == (Line(1, "// [impl->req~a~1]"),)
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/adapters -v`

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'earnest.adapters'` in both modules.

- [ ] **Step 3: Write the two adapters**

Create `packages/earnest/src/earnest/adapters/__init__.py`:

```python
"""Host adapters: each listed file's adapter, picked by suffix, hands its lines to the grammar."""
```

Create `packages/earnest/src/earnest/adapters/python.py`. `tokenize` yields each token before it raises, so a file that stops tokenizing keeps its earlier comments. `tokenize` also reads a lone `\r` and the character after it as one operator, so `x = 1\r# [impl->req~r~1]` would hold no comment at all; Git breaks no line at a lone `\r`, so a space stands in for it and every line number stays Git's:

```python
"""Python host adapter: `#` comments, through `tokenize`."""

import contextlib
import io
import re
import tokenize
from collections.abc import Iterator

from earnest.index import Line


def scan(text: str) -> tuple[Line, ...]:
    """Return the file's comments, each with its line number.

    A file that stops tokenizing, such as one an agent is halfway through editing, keeps what came before the error.
    """
    return tuple(Line(token.start[0], token.string) for token in _tokens(text) if token.type == tokenize.COMMENT)


def _tokens(text: str) -> Iterator[tokenize.TokenInfo]:
    spaced = re.sub(r"\r(?!\n)", " ", text)  # a lone `\r` would swallow the `#` after it; Git counts no line there
    with contextlib.suppress(tokenize.TokenError, SyntaxError):
        yield from tokenize.generate_tokens(io.StringIO(spaced).readline)
```

Create `packages/earnest/src/earnest/adapters/typescript.py`. The scan reads one token at a time: a comment, a string, template or regular expression literal, a name or number, whitespace, `++` or `--`, or any other character, and counts lines as it goes. Without the operand state its docstring gives, the backtick in `` s.replace(/`/g, "") `` would open a template that swallows the rest of the file, the `/*` in `/\/*$/` would open a comment, and the `/` in `i++ / 2` or `</p>` would open a regular expression that swallows the tag after it:

```python
"""TypeScript host adapter: `//` and block comments outside string, template and regular expression literals."""

import re

from earnest.index import Line


# ponytail: a template literal is one string up to its next backtick, so a template nested inside `${...}` ends the
# outer one early and a comment inside `${...}` reads as text; JSX text reads as code, so `//` there opens a comment.
# A TypeScript parser lifts both limits, at the cost of a dependency.
_TOKEN = re.compile(
    r"(?P<comment>//[^\n]*|/\*[\s\S]*?(?:\*/|\Z))"
    r"|(?P<literal>'(?:\\[\s\S]|[^'\\\n])*'?|\"(?:\\[\s\S]|[^\"\\\n])*\"?|`(?:\\[\s\S]|[^`\\])*`?)"
    r"|(?P<word>[\w$]+)|(?P<space>\s+)|(?P<step>\+\+|--)|(?P<other>[\s\S])",
)
# Possessive: each alternative opens on a character of its own, so a literal that never closes costs one pass.
# ponytail: that pass may run to the end of the line from each `/` that could open a regular expression, so a line of
# unclosed ones such as `(/a[/a[/a[` scans in time quadratic in its length; the TypeScript parser above lifts it too.
_REGEX = re.compile(r"/(?:\\.|\[(?:\\.|[^\]\\\n])*+\]|[^/\\\n\[])++/[A-Za-z]*+")
_BEFORE_REGEX = frozenset(
    {"return", "typeof", "instanceof", "case", "in", "of", "new", "delete", "void", "throw", "yield", "await"}
)
_CLOSERS = frozenset({")", "]", "}"})


def scan(text: str) -> tuple[Line, ...]:
    """Return the comment lines outside string, template and regular expression literals, one per physical line.

    A `/` starts a regular expression unless the token before it ends an operand or is `<`, as in the JSX closing tag
    `</p>`. A name, a number, a literal, `)`, `]`, `}`, `++` and `--` end an operand; a keyword such as `return` does
    not, unless it follows `.` or `?.` as a property name; and a postfix `!` leaves the state as it was.
    """
    comments: list[Line] = []
    operand = False  # whether the last token that is no comment or space ends an operand, so a `/` after it divides
    previous = ""  # the last token that is no comment or space
    number = 1  # the line the next token starts on
    position = 0
    while token := _TOKEN.match(text, position):
        kind, value = token.lastgroup, token.group()
        if value == "/" and not operand and previous != "<" and (regex := _REGEX.match(text, position)):
            token, kind, value = regex, "literal", regex.group()
        if kind == "comment":
            comments.extend(Line(number + offset, part) for offset, part in enumerate(value.split("\n")))
        elif kind != "space":
            if value != "!" or text.startswith("=", token.end()):  # a postfix `!` leaves the state as it was
                operand = _ends_operand(kind, value, previous)
            previous = value
        number += value.count("\n")
        position = token.end()
    return tuple(comments)


def _ends_operand(kind: str | None, value: str, previous: str) -> bool:
    if kind == "word":
        return previous == "." or value not in _BEFORE_REGEX  # after `.` or `?.`, even a keyword is a property name
    return kind in {"literal", "step"} or value in _CLOSERS
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/adapters -v && make lint`

Expected: `15 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/adapters tests/unit/adapters
git commit -m "feat: read Python and TypeScript comments outside their literals"
```

### Task 6: The Markdown and Gherkin adapters, and the adapter by suffix

**Files:**

- Create: `packages/earnest/src/earnest/adapters/markdown.py`
- Create: `packages/earnest/src/earnest/adapters/gherkin.py`
- Modify: `packages/earnest/src/earnest/adapters/__init__.py` (the whole file)
- Test: `packages/earnest/tests/unit/adapters/test_markdown.py`, `packages/earnest/tests/unit/adapters/test_gherkin.py`, `packages/earnest/tests/unit/test_adapters.py`

**Interfaces:**

- Consumes: `python.scan` and `typescript.scan` (Task 5); `Line`, `Source`, `split_lines`, `MARKDOWN`, `COMMENT`, `GHERKIN` and `build_index` from `earnest.index` (Tasks 3 and 4).
- Produces:
  - `earnest.adapters.markdown.scan(text: str) -> tuple[tuple[Line, ...], frozenset[int]]`: every line, and the lines inside code fences, fence lines included.
  - `earnest.adapters.gherkin.scan(text: str) -> tuple[Line, ...]`: the `@` tag lines outside doc strings, each cut at its first `#` after whitespace, where its comment opens.
  - `earnest.adapters.scan(root: Path, paths: Iterable[str]) -> list[Source]`: one `Source` per path whose suffix an adapter reads (`.md`, `.py`, `.ts`, `.tsx`, `.mts`, `.cts`, `.feature`), in the order given, which `git.work_tree_files` sorts. It skips other suffixes, paths gone from the work tree, binary files (a NUL byte in the first 8000 bytes) and code files whose bytes hold no `~`, and decodes the rest as UTF-8 with a byte order mark dropped and undecodable bytes replaced. A file that cannot be read raises `OSError`.

- [ ] **Step 1: Write the failing tests**

Create `packages/earnest/tests/unit/adapters/test_markdown.py`:

````python
"""Tests for the Markdown host adapter."""

import pytest

from earnest.adapters import markdown
from earnest.index import MARKDOWN, Source, build_index


EXAMPLES = """# Examples

`req~real~1`

```markdown
`req~quoted~2`
Covers: FR1.2
```

Needs: impl
"""


def test_fenced_lines_are_marked_fence_lines_included():
    lines, fenced = markdown.scan(EXAMPLES)
    assert len(lines) == 10
    assert fenced == {5, 6, 7, 8}


def test_id_shaped_text_in_a_fence_is_neither_an_item_nor_a_near_miss():
    lines, fenced = markdown.scan(EXAMPLES)
    index = build_index([Source("docs/a.md", MARKDOWN, lines, fenced)])
    assert [str(item.id) for item in index.items] == ["req~real~1"]
    assert index.items[0].needs == ("impl",)
    assert index.near_misses == ()


@pytest.mark.parametrize(
    ("opening", "inside"),
    [("~~~", "```"), ("~~~~", "~~~"), ("```", "``` more"), ("```", "    ```")],
)
def test_a_fence_closes_only_on_its_own_marker_at_least_as_long_alone_on_its_line(opening, inside):
    _, fenced = markdown.scan(f"{opening}\n{inside}\n`req~a~1`\n")
    assert fenced == {1, 2, 3}


def test_a_fence_may_sit_three_spaces_in_and_close_on_a_longer_marker():
    _, fenced = markdown.scan("   ~~~ text\n`req~a~1`\n  ~~~~  \nafter\n")
    assert fenced == {1, 2, 3}


def test_backticks_in_the_info_string_make_inline_code_not_a_fence():
    _, fenced = markdown.scan("```x``` is inline code\n`req~a~1`\n")
    assert fenced == set()


def test_an_unclosed_fence_runs_to_the_end_of_the_file():
    _, fenced = markdown.scan("text\n~~~\n`req~a~1`\n")
    assert fenced == {2, 3}
````

Create `packages/earnest/tests/unit/adapters/test_gherkin.py`:

```python
"""Tests for the Gherkin host adapter."""

import pytest

from earnest.adapters import gherkin
from earnest.index import Line


def test_tag_lines_are_read_and_comments_and_doc_strings_are_text():
    text = (
        "Feature: F\n\n  @stest:feat~a~1 @smoke\n  Scenario: S\n    Given a note\n"
        '      """\n      @stest:feat~b~1\n      """\n'
        "    And a snippet\n      ```markdown\n      @stest:feat~c~1\n      ```\n"
        "  # @stest:feat~d~1\n  @stest:feat~e~1\n"
    )
    assert gherkin.scan(text) == (Line(3, "  @stest:feat~a~1 @smoke"), Line(14, "  @stest:feat~e~1"))


def test_a_doc_string_closes_on_a_delimiter_line_with_a_comment_after_it():
    text = '  """\n  @stest:feat~a~1\n  """ # end\n  @stest:feat~b~1\n'
    assert gherkin.scan(text) == (Line(4, "  @stest:feat~b~1"),)


@pytest.mark.parametrize("space", [" ", "\t"], ids=["space", "tab"])
def test_a_tag_line_ends_at_its_first_hash_after_whitespace(space):
    assert gherkin.scan(f"@stest:feat~f~2{space}# was @stest:feat~f~1\n") == (Line(1, "@stest:feat~f~2"),)
```

Create `packages/earnest/tests/unit/test_adapters.py`:

```python
"""Tests for earnest.adapters: the adapter picked by suffix for each listed file, and how its bytes are read."""

from earnest import adapters
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Line


def test_each_suffix_gets_its_adapter_and_other_files_are_skipped(tmp_path):
    files = {
        "a.md": "`req~a~1`\n",
        "b.py": "# [impl->req~a~1]\nx = 1\n",
        "c.ts": "// [impl->req~a~1]\n",
        "d.mts": "// [impl->req~a~1]\n",
        "e.cts": "// [impl->req~a~1]\n",
        "f.tsx": "// [impl->req~a~1]\n",
        "g.feature": "@stest:feat~f~1\nScenario: S\n",
        "h.txt": "[impl->req~a~1]\n",
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    sources = adapters.scan(tmp_path, [*files, "gone.py"])
    assert [(source.path, source.surface, len(source.lines)) for source in sources] == [
        ("a.md", MARKDOWN, 1),
        ("b.py", COMMENT, 1),
        ("c.ts", COMMENT, 1),
        ("d.mts", COMMENT, 1),
        ("e.cts", COMMENT, 1),
        ("f.tsx", COMMENT, 1),
        ("g.feature", GHERKIN, 1),
    ]


def test_a_byte_order_mark_is_dropped(tmp_path):
    (tmp_path / "a.md").write_bytes(b"\xef\xbb\xbf`req~a~1`\n")
    (source,) = adapters.scan(tmp_path, ["a.md"])
    assert source.lines == (Line(1, "`req~a~1`"),)


def test_a_binary_file_is_skipped(tmp_path):
    (tmp_path / "a.ts").write_bytes(b"// [impl->req~a~1]\n\0\n")
    assert adapters.scan(tmp_path, ["a.ts"]) == []


def test_text_that_is_not_utf_8_keeps_its_lines_with_replacement_characters(tmp_path):
    (tmp_path / "a.md").write_bytes(b"# Caf\xe9\n\n`req~a~1`\n")
    (source,) = adapters.scan(tmp_path, ["a.md"])
    assert source.lines == (Line(1, "# Caf\ufffd"), Line(2, ""), Line(3, "`req~a~1`"))
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/adapters tests/unit/test_adapters.py -v`

Expected: FAIL, `Interrupted: 2 errors during collection`, from `ImportError: cannot import name 'markdown' from 'earnest.adapters'` and `ImportError: cannot import name 'gherkin' from 'earnest.adapters'`.

- [ ] **Step 3: Write the adapters and the scan by suffix**

Create `packages/earnest/src/earnest/adapters/markdown.py`:

```python
"""Markdown host adapter: the lines of a stage artifact, with its code fences marked."""

import re

from earnest.index import Line, split_lines


_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")


def scan(text: str) -> tuple[tuple[Line, ...], frozenset[int]]:
    """Return every line, and the lines inside code fences, fence lines included; an unclosed fence runs to the end.

    A fence opens on three or more backticks or tildes after up to three spaces, and a backtick fence's info string
    holds no backtick. It closes on the same character, at least as many, with nothing after them.
    """
    lines = split_lines(text)
    fenced: set[int] = set()
    fence = ""
    for line in lines:
        marker = _FENCE.fullmatch(line.text)
        if fence:
            fenced.add(line.number)
            if marker and marker.group(1).startswith(fence) and not marker.group(2).strip():
                fence = ""
        elif marker and not (marker.group(1).startswith("`") and "`" in marker.group(2)):
            fenced.add(line.number)
            fence = marker.group(1)
    return lines, frozenset(fenced)
```

Create `packages/earnest/src/earnest/adapters/gherkin.py`:

```python
"""Gherkin host adapter: the `@` tag lines outside doc strings, each without its comment."""

import re

from earnest.index import Line, split_lines


_DOC_STRINGS = ('"""', "```")


def scan(text: str) -> tuple[Line, ...]:
    """Return the `@` tag lines, each cut at its first `#` after whitespace, where a comment opens, as Gherkin cuts it.

    A doc string opens and closes on a line whose stripped text starts with its delimiter, three double quotes or three
    backticks, and its lines are text, never tags.
    """
    # ponytail: a description line that starts with a delimiter opens a doc string and hides the tags below it until the
    # next delimiter line; the official Gherkin parser tells the two apart, at the cost of a dependency.
    tags: list[Line] = []
    doc_string = ""
    for line in split_lines(text):
        stripped = line.text.strip()
        if doc_string:
            doc_string = "" if stripped.startswith(doc_string) else doc_string
        elif stripped.startswith(_DOC_STRINGS):
            doc_string = stripped[:3]
        elif stripped.startswith("@"):
            tags.append(Line(line.number, re.split(r"\s#", line.text, maxsplit=1)[0]))
    return tuple(tags)
```

Replace the whole of `packages/earnest/src/earnest/adapters/__init__.py` with the scan by suffix. A file that cannot be read raises `OSError`, which the command turns into exit code 2 (Task 9):

```python
"""Host adapters: each listed file's adapter, picked by suffix, hands its lines to the grammar."""

from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath

from earnest.adapters import gherkin, markdown, python, typescript
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Line, Source


_Scan = Callable[[str], tuple[tuple[Line, ...], frozenset[int]]]


def _unfenced(scan: Callable[[str], tuple[Line, ...]]) -> _Scan:
    return lambda text: (scan(text), frozenset())


# Each suffix an adapter reads: its surface, and the scan that gives its lines and the lines inside its code fences.
_SCANS: dict[str, tuple[str, _Scan]] = {
    ".md": (MARKDOWN, markdown.scan),
    ".feature": (GHERKIN, _unfenced(gherkin.scan)),
    ".py": (COMMENT, _unfenced(python.scan)),
    ".ts": (COMMENT, _unfenced(typescript.scan)),
    ".tsx": (COMMENT, _unfenced(typescript.scan)),
    ".mts": (COMMENT, _unfenced(typescript.scan)),
    ".cts": (COMMENT, _unfenced(typescript.scan)),
}


def scan(root: Path, paths: Iterable[str]) -> list[Source]:
    """Scan each listed file whose suffix an adapter reads, in the order given, which `git.work_tree_files` sorts.

    Other files are skipped, and so are files gone from the work tree, binary files, which hold a NUL byte in their
    first 8000 bytes as Git judges, and code files with no `~`, since every tag holds one. Text decodes as UTF-8, with
    a byte order mark dropped and each byte that is not UTF-8 replaced.

    Raises:
        OSError: a file cannot be read.
    """
    sources: list[Source] = []
    for path in paths:
        adapter = _SCANS.get(PurePosixPath(path).suffix)
        file = root / path
        if adapter is None or not file.is_file():
            continue
        surface, read = adapter
        data = file.read_bytes()
        if b"\0" not in data[:8000] and (surface != COMMENT or b"~" in data):
            sources.append(Source(path, surface, *read(data.decode("utf-8-sig", errors="replace"))))
    return sources
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit -v && make lint`

Expected: `97 passed`, the 17 new tests among them, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/adapters tests/unit/adapters tests/unit/test_adapters.py
git commit -m "feat: read Markdown fences and Gherkin tags, and pick each file's adapter by suffix"
```

### Task 7: The reporter, SARIF 2.1.0 and the summary

**Files:**

- Create: `packages/earnest/src/earnest/reporter.py`
- Test: `packages/earnest/tests/unit/test_reporter.py`

**Interfaces:**

- Consumes: `sarif_run` from `tests/sarif.py` (Task 1).
- Produces, in `earnest.reporter`:
  - `RULES: dict[str, str]`, rule id to SARIF level, for the seven link rules: `earnest/duplicate`, `earnest/gap`, `earnest/near-miss`, `earnest/orphaned`, `earnest/outdated` and `earnest/predated` at `error`, `earnest/unwanted` at `warning`.
  - `LEVELS = ("untraced", "traced", "judged", "evidenced")`.
  - `Finding(path: str, line: int, rule: str, subject: str, message: str)`, frozen and ordered, with the properties `level -> str`, the rule's SARIF level, and `text -> str`, the message as reported, opening with `in scope:`. `subject` is the id or text the finding is about, and `message` names the change to make and never repeats the position. The reporter is the one place that sorts findings.
  - `percentages(levels: Mapping[str, str]) -> dict[str, int]`: `traced`, `judged` and `evidenced`, each the share of requirements at that level or above in whole percent rounded down, so 100 means all, and 0 with no requirements.
  - `sarif(findings: Sequence[Finding], levels: Mapping[str, str], commit: str) -> str`: one SARIF 2.1.0 log as compact JSON text on one line, keys and results sorted. Each result carries `properties.position` `current`, no `properties.stage`, and `properties.observations`: one observation with the fields of `01`'s Process vocabulary, method `trace`, subject, result, reasoning and location. Its `uri` is the path percent-encoded with `urllib.parse.quote`.
  - `summary(findings: Sequence[Finding], levels: Mapping[str, str]) -> str`: the stderr text, whose first line is `traced N%, judged N%, evidenced N%; requirements: N`.

- [ ] **Step 1: Write the failing tests**

Create `packages/earnest/tests/unit/test_reporter.py`:

```python
"""Tests for earnest.reporter: SARIF 2.1.0, percentages and the summary."""

import json

from earnest import reporter
from earnest.reporter import Finding
from tests.sarif import sarif_run


FINDINGS = [
    Finding("src/b.py", 3, "earnest/unwanted", "req~b~1", "b"),
    Finding("docs/a b.md", 9, "earnest/gap", "req~a~1", "a"),
]
LEVELS = {"req~a~1": "traced", "req~b~1": "untraced", "req~c~1": "traced"}


def test_each_rule_has_its_sarif_level():
    assert reporter.RULES == {
        "earnest/duplicate": "error",
        "earnest/gap": "error",
        "earnest/near-miss": "error",
        "earnest/orphaned": "error",
        "earnest/outdated": "error",
        "earnest/predated": "error",
        "earnest/unwanted": "warning",
    }


def test_percentages_round_down_so_100_means_every_requirement():
    assert reporter.percentages(LEVELS) == {"traced": 66, "judged": 0, "evidenced": 0}
    almost = {f"req~r{number}~1": "traced" for number in range(199)} | {"req~last~1": "untraced"}
    assert reporter.percentages(almost)["traced"] == 99
    assert reporter.percentages({}) == {"traced": 0, "judged": 0, "evidenced": 0}


def test_the_log_is_one_sarif_2_1_0_run_with_located_results_in_order():
    text = reporter.sarif(FINDINGS, LEVELS, "abc123")
    assert json.loads(text)["version"] == "2.1.0"
    run = sarif_run(text)
    assert run["tool"] == {"driver": {"name": "earnest"}}
    assert [(result["ruleId"], result["level"]) for result in run["results"]] == [
        ("earnest/gap", "error"),
        ("earnest/unwanted", "warning"),
    ]
    assert run["properties"] == {"traceLevels": LEVELS, "percentages": {"traced": 66, "judged": 0, "evidenced": 0}}
    assert run["invocations"] == [
        {"executionSuccessful": True, "properties": {"commit": "abc123", "layers": ["trace"]}},
    ]


def test_each_result_sits_at_its_percent_encoded_file_in_scope_over_its_observation():
    first = sarif_run(reporter.sarif(FINDINGS, LEVELS, "abc123"))["results"][0]
    location = {"artifactLocation": {"uri": "docs/a%20b.md"}, "region": {"startLine": 9}}
    assert first["locations"] == [{"physicalLocation": location}]
    assert first["message"] == {"text": "in scope: a"}
    assert first["properties"]["position"] == "current"
    assert "stage" not in first["properties"]
    assert first["properties"]["observations"] == [
        {"method": "trace", "subject": "req~a~1", "result": "gap", "reasoning": "a", "location": location},
    ]


def test_the_same_findings_in_another_order_give_the_same_bytes():
    shuffled = dict(reversed(LEVELS.items()))
    assert reporter.sarif(FINDINGS, LEVELS, "abc") == reporter.sarif(FINDINGS[::-1], shuffled, "abc")


def test_the_summary_leads_with_the_three_percentages():
    lines = reporter.summary(FINDINGS, LEVELS).splitlines()
    assert lines[0] == "traced 66%, judged 0%, evidenced 0%; requirements: 3"
    assert lines[1:4] == ["  req~a~1: traced", "  req~b~1: untraced", "  req~c~1: traced"]
    assert lines[4] == "docs/a b.md:9: error earnest/gap: in scope: a"
    assert lines[-1] == "findings: 2, errors: 1"
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/test_reporter.py -v`

Expected: FAIL at collection with `ImportError: cannot import name 'reporter' from 'earnest'`.

- [ ] **Step 3: Write `reporter.py`**

The SARIF 2.1.0 section of `01` asks for no rule metadata and no tool version, so the driver carries its name alone; the commit and the layers run ride on the invocation, whose `executionSuccessful` SARIF requires. Each result carries the observation behind it, whose five fields are those of the Process vocabulary in `01`. The log is compact JSON with sorted keys, one line for a tool to parse. Both outputs sort the findings, so no caller has to.

Create `packages/earnest/src/earnest/reporter.py`:

```python
"""Reporter: the SARIF 2.1.0 log, with each requirement's trace level, and the summary that leads with three percentages."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import quote


RULES = {
    "earnest/duplicate": "error",
    "earnest/gap": "error",
    "earnest/near-miss": "error",
    "earnest/orphaned": "error",
    "earnest/outdated": "error",
    "earnest/predated": "error",
    "earnest/unwanted": "warning",
}
LEVELS = ("untraced", "traced", "judged", "evidenced")
_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"


@dataclass(frozen=True, order=True)
class Finding:
    """A located result: file, line, rule, the id or text it is about, and a message that names the change to make."""

    path: str
    line: int
    rule: str
    subject: str
    message: str

    @property
    def level(self) -> str:
        """Return the SARIF level of the finding's rule."""
        return RULES[self.rule]

    @property
    def text(self) -> str:
        """Return the message as it is reported, opening with the finding's position."""
        # ponytail: no finding reaches a stage until stages exist, so each sits at position current, `in scope`.
        return f"in scope: {self.message}"


def percentages(levels: Mapping[str, str]) -> dict[str, int]:
    """Return the share of requirements at each level or above, in whole percent rounded down, so 100 means all."""
    ranks = [LEVELS.index(level) for level in levels.values()]
    shares: dict[str, int] = {}
    for rank, name in enumerate(LEVELS[1:], start=1):
        reached = sum(1 for value in ranks if value >= rank)
        shares[name] = 100 * reached // len(ranks) if ranks else 0
    return shares


def sarif(findings: Sequence[Finding], levels: Mapping[str, str], commit: str) -> str:
    """Return one SARIF 2.1.0 log; it holds no timestamp, so an unchanged repository gives the same bytes."""
    run = {
        "tool": {"driver": {"name": "earnest"}},
        "invocations": [{"executionSuccessful": True, "properties": {"commit": commit, "layers": ["trace"]}}],
        "results": [_result(finding) for finding in sorted(findings)],
        "properties": {"traceLevels": dict(levels), "percentages": percentages(levels)},
    }
    log = {"$schema": _SCHEMA, "version": "2.1.0", "runs": [run]}
    return json.dumps(log, sort_keys=True, separators=(",", ":")) + "\n"


def summary(findings: Sequence[Finding], levels: Mapping[str, str]) -> str:
    """Return the human summary: the three percentages, each requirement's level, then each finding."""
    shares = percentages(levels)
    head = (
        f"traced {shares['traced']}%, judged {shares['judged']}%, evidenced {shares['evidenced']}%;"
        f" requirements: {len(levels)}"
    )
    lines = [
        head,
        *(f"  {req}: {level}" for req, level in sorted(levels.items())),
        *(f"{f.path}:{f.line}: {f.level} {f.rule}: {f.text}" for f in sorted(findings)),
    ]
    errors = sum(1 for finding in findings if finding.level == "error")
    lines.append(f"findings: {len(findings)}, errors: {errors}")
    return "\n".join(lines) + "\n"


def _result(finding: Finding) -> dict[str, object]:
    uri = quote(finding.path, errors="surrogateescape")  # Git hands over names that are not UTF-8 as surrogates
    location = {"artifactLocation": {"uri": uri}, "region": {"startLine": finding.line}}
    observation = {
        "method": "trace",
        "subject": finding.subject,
        "result": finding.rule.removeprefix("earnest/"),
        "reasoning": finding.message,
        "location": location,
    }
    return {
        "ruleId": finding.rule,
        "level": finding.level,
        "message": {"text": finding.text},
        "locations": [{"physicalLocation": location}],
        "properties": {"position": "current", "observations": [observation]},
    }
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/test_reporter.py -v && make lint`

Expected: `6 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/reporter.py tests/unit/test_reporter.py
git commit -m "feat: report findings as SARIF 2.1.0 with their observations and a summary"
```

### Task 8: The link rules, `structural.py`

**Files:**

- Create: `packages/earnest/src/earnest/structural.py`
- Test: `packages/earnest/tests/unit/test_structural.py`

**Interfaces:**

- Consumes: `Id`, `Index`, `Item`, `Link`, `NearMiss`, `Resolution`, `Index.defined` and `Index.resolutions` from `earnest.index` (Tasks 3 and 4); `Finding` from `earnest.reporter` (Task 7).
- Produces, in `earnest.structural`:
  - `DEFAULT_NEEDS: dict[str, tuple[str, ...]]`, the Default Needs table: `tenet` needs `goal`, `goal` needs `feat`, `feat` needs `req` and `stest`, `req` needs `impl` and `utest`, `dsn` needs `impl`.
  - `needs(item: Item) -> tuple[str, ...]`: the item's `Needs:` types, or its type's default; `()` for a type with none.
  - `check(index: Index) -> list[Finding]`: the findings under `earnest/near-miss`, `earnest/duplicate`, `earnest/orphaned`, `earnest/outdated`, `earnest/predated`, `earnest/unwanted` and `earnest/gap`, in the order of the index; the reporter sorts them.
  - `traced(index: Index) -> dict[str, str]`: each `req`, first definition only, keyed by its id as text, to its trace level, `traced` when a cover of every type it needs resolves at its current revision and `untraced` otherwise.

- [ ] **Step 1: Write the failing tests**

Create `packages/earnest/tests/unit/test_structural.py`:

```python
"""Tests for earnest.structural: the link rules and each requirement's trace level."""

import pytest

from earnest import structural
from earnest.index import Id, Index, Item, Link, NearMiss


FEAT = Id("feat", "f", 1)
REQ = Id("req", "r", 2)
ITEMS = (Item(FEAT, "docs/f.md", 1, ("req",)), Item(REQ, "docs/r.md", 5))
PARENT = Link("Covers", "req", FEAT, "docs/r.md", 7, owner=REQ)
IMPL = Link("Covers", "impl", REQ, "src/a.py", 3)
UTEST = Link("Covers", "utest", REQ, "tests/test_a.py", 3)


def index(*links, items=ITEMS, misses=(), parent=True):
    return Index(items, (PARENT, *links) if parent else links, misses)


def check(*links, items=ITEMS, misses=(), parent=True):
    """Check a requirement under a feat; the feat names no goal, and its own finding is not under test here."""
    found = structural.check(index(*links, items=items, misses=misses, parent=parent))
    return [finding for finding in found if finding.path != "docs/f.md"]


def located(rule, found):
    return [(finding.path, finding.line) for finding in found if finding.rule == rule]


def message(rule, found):
    (text,) = [finding.message for finding in found if finding.rule == rule]
    return text


def test_a_requirement_whose_needs_resolve_at_its_revision_is_traced():
    assert check(IMPL, UTEST) == []
    assert structural.traced(index(IMPL, UTEST)) == {"req~r~2": "traced"}


def test_a_need_with_no_cover_at_any_revision_is_a_gap_at_the_item():
    found = check(IMPL)
    assert located("earnest/gap", found) == [("docs/r.md", 5)]
    assert "`[utest->req~r~2]`" in message("earnest/gap", found)
    assert structural.traced(index(IMPL)) == {"req~r~2": "untraced"}


def test_a_cover_of_an_older_revision_is_outdated_not_a_gap():
    old = Link("Covers", "utest", Id("req", "r", 1), "tests/test_a.py", 9)
    found = check(IMPL, old)
    assert [finding.rule for finding in found] == ["earnest/outdated"]
    assert "write `req~r~2`" in message("earnest/outdated", found)
    assert structural.traced(index(IMPL, old)) == {"req~r~2": "untraced"}


def test_a_link_to_a_revision_above_the_items_is_predated():
    ahead = Link("Covers", "utest", Id("req", "r", 3), "tests/test_a.py", 9)
    assert located("earnest/predated", check(IMPL, ahead)) == [("tests/test_a.py", 9)]


def test_a_link_to_no_item_is_orphaned_and_names_the_closest_id_of_its_type():
    typo = Link("Covers", "utest", Id("req", "rr", 2), "tests/test_a.py", 9)
    other_type = Link("Covers", "impl", Id("dsn", "r", 2), "src/b.py", 4)
    found = check(IMPL, UTEST, typo, other_type)
    assert located("earnest/orphaned", found) == [("tests/test_a.py", 9), ("src/b.py", 4)]
    assert [finding.message for finding in found] == [
        "`req~rr~2` names no item: did you mean `req~r~2`?",
        "`dsn~r~2` names no item: define the item, or name one that exists",
    ]


def test_an_item_that_names_no_parent_is_orphaned():
    found = check(IMPL, UTEST, parent=False)
    assert located("earnest/orphaned", found) == [("docs/r.md", 5)]
    assert "add a `Covers:` line naming the `feat` it derives from" in message("earnest/orphaned", found)


@pytest.mark.parametrize("target", [Id("goal", "g", 1), REQ])
def test_a_covers_line_naming_no_item_of_the_parent_type_names_no_parent(target):
    items = (*ITEMS, Item(Id("goal", "g", 1), "docs/g.md", 1))
    wrong = Link("Covers", "req", target, "docs/r.md", 7, owner=REQ)
    found = check(IMPL, UTEST, wrong, items=items, parent=False)
    assert [(f.line, f.rule) for f in found if f.path == "docs/r.md"] == [
        (7, "earnest/unwanted"),
        (5, "earnest/orphaned"),
    ]


def test_a_cover_by_a_type_the_item_never_needs_is_unwanted_at_warning_level():
    itest = Link("Covers", "itest", REQ, "tests/test_b.py", 4)
    found = check(IMPL, UTEST, itest)
    assert located("earnest/unwanted", found) == [("tests/test_b.py", 4)]
    assert [finding.level for finding in found] == ["warning"]


def test_an_unwanted_cover_names_the_id_it_wrote():
    old = Link("Covers", "itest", Id("req", "r", 1), "tests/test_b.py", 4)
    assert message("earnest/unwanted", check(IMPL, UTEST, old)).startswith("`itest` covers `req~r~1` ")


def test_an_explicit_needs_line_replaces_the_default():
    items = (ITEMS[0], Item(REQ, "docs/r.md", 5, ("impl", "itest")))
    itest = Link("Covers", "itest", REQ, "tests/test_b.py", 4)
    assert located("earnest/unwanted", check(IMPL, UTEST, itest, items=items)) == [("tests/test_a.py", 3)]
    assert structural.traced(index(IMPL, itest, items=items)) == {"req~r~2": "traced"}


def test_a_second_item_with_the_same_id_is_a_duplicate():
    found = check(IMPL, UTEST, items=(*ITEMS, Item(REQ, "docs/other.md", 9)))
    assert located("earnest/duplicate", found) == [("docs/other.md", 9)]
    assert "already defined at docs/r.md:5" in message("earnest/duplicate", found)


def test_a_near_miss_is_a_finding_with_its_canned_fix():
    miss = NearMiss("src/a.py", 8, "[impl-req~r~2]", "write `->` between the artifact type and the id")
    (finding,) = check(IMPL, UTEST, misses=(miss,))
    assert (finding.rule, finding.subject) == ("earnest/near-miss", "[impl-req~r~2]")
    assert finding.message == "`[impl-req~r~2]` does not parse: " + miss.fix


def test_a_decision_names_its_drivers_and_they_count_toward_no_need():
    dsn = Id("dsn", "d", 1)
    items = (*ITEMS, Item(dsn, "docs/d.md", 1))
    drivers = Link("Drivers", "dsn", REQ, "docs/d.md", 3, owner=dsn)
    impl = Link("Covers", "impl", dsn, "src/b.py", 1)
    assert check(IMPL, UTEST, drivers, impl, items=items) == []
    assert located("earnest/orphaned", check(IMPL, UTEST, impl, items=items)) == [("docs/d.md", 1)]
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/test_structural.py -v`

Expected: FAIL at collection with `ImportError: cannot import name 'structural' from 'earnest'`.

- [ ] **Step 3: Write `structural.py`**

`index.py` owns Reference resolution, so this module reads each resolution's status and never compares revisions itself. `traced` and `_gaps` share one set of covers, each with the resolution of the id it names: `traced` counts a cover only when that resolution is `resolved`, and `_gaps` counts it at any revision, so a stale cover raises `outdated` or `predated` and no `gap`.

Create `packages/earnest/src/earnest/structural.py`:

```python
"""Structural checks: the link findings the index decides without a model, and each requirement's trace level."""

from collections.abc import Iterator

from earnest.index import Index, Item, Resolution
from earnest.reporter import Finding


DEFAULT_NEEDS: dict[str, tuple[str, ...]] = {
    "tenet": ("goal",),
    "goal": ("feat",),
    "feat": ("req", "stest"),
    "req": ("impl", "utest"),
    "dsn": ("impl",),
}
# The parent edge of each item type, from the Edges of the logic design: its key, the parent types, and the fix.
_PARENTS = {
    "goal": ("Covers", ("tenet",), "add a `Covers:` line naming the `tenet` it serves"),
    "feat": ("Covers", ("goal",), "add a `Covers:` line naming the `goal` it refines"),
    "req": ("Covers", ("feat",), "add a `Covers:` line naming the `feat` it derives from"),
    "dsn": ("Drivers", ("req", "goal"), "add a `Drivers:` line naming the `req` or `goal` that drives it"),
}
_COVER_HINTS = {
    "impl": "tag the code that implements it with `[impl->{id}]`",
    "utest": "tag a unit test that verifies it with `[utest->{id}]`",
    "itest": "tag an integration test that verifies it with `[itest->{id}]`",
    "stest": "tag a scenario that verifies it with `@stest:{id}`",
}


def needs(item: Item) -> tuple[str, ...]:
    """Return the types on the item's `Needs:` line, or its type's default."""
    return item.needs if item.needs is not None else DEFAULT_NEEDS.get(item.id.type, ())


def check(index: Index) -> list[Finding]:
    """Return the link findings, in the order of the index; the reporter sorts them.

    Near-misses, duplicate ids, links that resolve to no item or to another revision, covers that count toward
    nothing, items that name no parent of their type, and needs that no cover meets.
    """
    return [*_near_misses(index), *_duplicates(index), *_links(index), *_parentless(index), *_gaps(index)]


def traced(index: Index) -> dict[str, str]:
    """Give each requirement its trace level, keyed by its id: traced when a cover of every type it needs resolves."""
    resolved = {(kind, resolution.item) for kind, resolution in _covers(index) if resolution.status == "resolved"}
    return {
        str(item.id): "traced" if all((kind, item) in resolved for kind in needs(item)) else "untraced"
        for item in index.defined.values()
        if item.id.type == "req"
    }


def _near_misses(index: Index) -> Iterator[Finding]:
    for miss in index.near_misses:
        yield Finding(miss.path, miss.line, "earnest/near-miss", miss.text, f"`{miss.text}` does not parse: {miss.fix}")


def _duplicates(index: Index) -> Iterator[Finding]:
    for item in index.items:
        first = index.defined[item.id.key]
        if item != first:
            message = f"`{item.id}` is already defined at {first.path}:{first.line}: give one of them another name"
            yield Finding(item.path, item.line, "earnest/duplicate", str(item.id), message)


def _links(index: Index) -> Iterator[Finding]:
    """Turn each link's resolution into its findings: orphaned, outdated or predated, and unwanted."""
    for link in index.links:
        resolution = index.resolutions[link.target]
        subject = str(link.target)
        item = resolution.item
        if item is None:
            close = (
                f"did you mean `{resolution.closest}`?"
                if resolution.closest
                else "define the item, or name one that exists"
            )
            yield Finding(link.path, link.line, "earnest/orphaned", subject, f"`{subject}` names no item: {close}")
            continue
        if resolution.status == "outdated":
            message = (
                f"`{subject}` names revision {link.target.revision}, and the item is at revision {item.id.revision}:"
                f" check the change, then write `{item.id}`"
            )
            yield Finding(link.path, link.line, "earnest/outdated", subject, message)
        elif resolution.status == "predated":
            message = (
                f"`{subject}` names revision {link.target.revision}, above the item's revision {item.id.revision}:"
                f" write `{item.id}`, or bump the item if its meaning changed"
            )
            yield Finding(link.path, link.line, "earnest/predated", subject, message)
        if link.key == "Covers" and link.type not in needs(item):
            wanted = ", ".join(f"`{kind}`" for kind in needs(item)) or "no cover"
            message = (
                f"`{link.type}` covers `{link.target}` and counts toward nothing, because the item needs {wanted}:"
                f" use a type it needs, or add `{link.type}` to its `Needs:` line"
            )
            yield Finding(link.path, link.line, "earnest/unwanted", subject, message)


def _parentless(index: Index) -> Iterator[Finding]:
    """An item whose parent key names no id of a parent type, itself included, covers no parent."""
    named = {(link.owner, link.key, link.target.type) for link in index.links if link.owner is not None}
    for item in index.defined.values():
        if item.id.type not in _PARENTS:
            continue
        key, parents, fix = _PARENTS[item.id.type]
        if not any((item.id, key, parent) in named for parent in parents):
            yield Finding(
                item.path, item.line, "earnest/orphaned", str(item.id), f"`{item.id}` covers no parent: {fix}"
            )


def _gaps(index: Index) -> Iterator[Finding]:
    """A need no cover meets at any revision is a gap; a cover at another revision is outdated or predated instead."""
    covered = {(kind, resolution.item) for kind, resolution in _covers(index)}
    for item in index.defined.values():
        for kind in needs(item):
            if (kind, item) not in covered:
                hint = _COVER_HINTS.get(kind, "add a `{kind}` item with `Covers: {id}`").format(kind=kind, id=item.id)
                message = f"`{item.id}` needs a `{kind}` cover and has none: {hint}"
                yield Finding(item.path, item.line, "earnest/gap", str(item.id), message)


def _covers(index: Index) -> set[tuple[str, Resolution]]:
    """Return each cover as its artifact type and the resolution of the id it names."""
    return {(link.type, index.resolutions[link.target]) for link in index.links if link.key == "Covers"}
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/test_structural.py -v && make lint`

Expected: `14 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/structural.py tests/unit/test_structural.py
git commit -m "feat: turn the index into link findings and trace levels"
```

### Task 9: `earnest check` end to end, and the exit command green

**Files:**

- Create: `packages/earnest/src/earnest/cli.py`
- Modify: `packages/earnest/pyproject.toml` (`[project.scripts]`, L4)
- Modify: `docs/design/03-implementation-plan.md` (the `done` class on M1 in the milestone DAG)
- Create: `packages/earnest/tests/integration/__init__.py`
- Test: `packages/earnest/tests/unit/test_cli.py`, `packages/earnest/tests/integration/test_check.py`

**Interfaces:**

- Consumes: `git.repo_root`, `git.head_commit`, `git.work_tree_files` and `git.GitError` (Task 2); `build_index` (Tasks 3 and 4); `adapters.scan` and the `OSError` it raises (Task 6); `reporter.sarif`, `reporter.summary` and `Finding.level` (Task 7); `structural.check` and `structural.traced` (Task 8); the `files_repo` fixture (Task 2); `sarif_run` and `located` from `tests/sarif.py`, the feature and its step module (Task 1).
- Produces: `earnest.cli.main(argv: Sequence[str] | None = None) -> int`, which returns 0 when no error-level finding sits at position behind or current, 1 when one does, and 2 when the check cannot run: Git cannot answer, or a file cannot be read, and then it writes one line on stderr and nothing on stdout. It also returns 2, and writes nothing more, when the reader of stdout or of stderr goes away before its text is written; both streams then point at `os.devnull`, so the exit flush raises nothing. A bare `earnest` exits 2 from `argparse`. The console script `earnest`, from `[project.scripts] earnest = "earnest.cli:main"`.

- [ ] **Step 1: Write the failing tests**

```bash
mkdir -p tests/integration
touch tests/integration/__init__.py
```

Create `packages/earnest/tests/unit/test_cli.py`. Git's messages depend on the locale, so the test that reads one runs Git with `LC_ALL=C`. The pipe tests run the command in a child process whose stdout or stderr pipe the test closes before the child writes, as `head` does when it has read enough:

```python
"""Tests for earnest.cli: the required command, and the exit code when the check cannot run or loses its reader."""

import subprocess
import sys

import pytest

from earnest import cli


CHECK = [sys.executable, "-c", "import sys; from earnest.cli import main; sys.exit(main(['check']))"]


def test_a_command_is_required(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])
    assert exit_info.value.code == 2
    assert "check" in capsys.readouterr().err


def test_a_check_outside_a_work_tree_exits_2_with_one_line_on_stderr(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["check"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("earnest: fatal: not a git repository")
    assert len(err.splitlines()) == 1


def test_a_reader_that_goes_away_early_gets_exit_code_2_and_no_traceback(files_repo):
    repo = files_repo({"docs/a.md": "# A\n"})
    with subprocess.Popen(CHECK, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as check:
        check.stdout.close()
        err = check.stderr.read()
    assert check.returncode == 2
    assert b"Traceback" not in err


def test_a_reader_of_the_summary_that_goes_away_early_gets_exit_code_2(files_repo):
    repo = files_repo({"docs/a.md": "# A\n"})
    with subprocess.Popen(CHECK, cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as check:
        check.stderr.close()
    assert check.returncode == 2
```

Create `packages/earnest/tests/integration/test_check.py`. The second test writes its extra document after the commit, so the check must read an untracked file, from a subdirectory, under a name whose space the SARIF `uri` percent-encodes. The third overwrites a committed document with bytes that are not UTF-8, or with a lone `\r` inside its first line, which a reader that translates newlines would split in two; either way, its id stays on the line Git counts:

```python
"""Integration: `earnest check` over a committed repository, from the scan to the exit code."""

import pytest

from earnest import cli
from tests.sarif import located, sarif_run


CHAIN = {
    "docs/intent.md": "# Intent\n\n`tenet~t~1`\n\n`goal~g~1`\n\nCovers: tenet~t~1\n",
    "docs/scope.md": "# Scope\n\n`feat~f~1`\n\nCovers: goal~g~1\n",
    "docs/requirements.md": "# Requirements\n\n`req~r~1`\n\nThe service shall answer.\n\nCovers: feat~f~1\n",
    "src/app.py": "# [impl->req~r~1]\ndef answer() -> int:\n    return 42\n",
    "tests/test_app.py": "# [utest->req~r~1]\ndef test_answer() -> None:\n    assert True\n",
    "tests/app.feature": "Feature: App\n\n  @stest:feat~f~1\n  Scenario: It answers\n    Then it answers\n",
}


def check(cwd, monkeypatch, capsys):
    monkeypatch.chdir(cwd)
    code = cli.main(["check"])
    out, err = capsys.readouterr()
    return code, sarif_run(out), err


def test_a_complete_chain_passes_with_every_requirement_traced(files_repo, monkeypatch, capsys):
    code, run, err = check(files_repo(CHAIN), monkeypatch, capsys)
    assert (code, run["results"]) == (0, [])
    assert run["properties"]["traceLevels"] == {"req~r~1": "traced"}
    assert err.startswith("traced 100%, judged 0%, evidenced 0%; requirements: 1\n")


def test_a_check_from_a_subdirectory_reads_the_whole_work_tree_untracked_files_included(
    files_repo, monkeypatch, capsys
):
    repo = files_repo(CHAIN)
    (repo / "docs" / "more notes.md").write_text("# More\n\n`req~x~1`\n\nCovers: feat~f~1\n", encoding="utf-8")
    code, run, _ = check(repo / "src", monkeypatch, capsys)
    assert code == 1
    assert {(result["ruleId"], located(result)) for result in run["results"]} == {
        ("earnest/gap", ("docs/more%20notes.md", 3)),
    }


@pytest.mark.parametrize(
    "data",
    [b"# Caf\xe9\n\n`req~a~1`\n", b"# A\r x\n\n`req~a~1`\n"],
    ids=["not-utf-8", "lone-carriage-return"],
)
def test_bytes_that_are_not_utf_8_or_a_lone_carriage_return_move_no_line(data, files_repo, monkeypatch, capsys):
    repo = files_repo({"docs/a.md": "# A\n"})
    (repo / "docs" / "a.md").write_bytes(data)
    code, run, _ = check(repo, monkeypatch, capsys)
    assert code == 1
    assert {located(result) for result in run["results"]} == {("docs/a.md", 3)}
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/test_cli.py tests/integration -v`

Expected: FAIL at collection with `ImportError: cannot import name 'cli' from 'earnest'` in both modules.

- [ ] **Step 3: Write `cli.py` and declare the `earnest` script**

`cli.py` wires the pipeline and keeps no logic of its own. The boundary catches only `GitError` and `OSError`; it writes one line on stderr, nothing on stdout, and exits 2. The two writes, the log's and the summary's, share one `try` that catches `BrokenPipeError`, and each flushes inside it, since text held in a buffer would otherwise meet the closed pipe at the exit flush, outside any handler. The handler points both streams at `os.devnull`, so that flush writes nowhere and raises nothing.

Create `packages/earnest/src/earnest/cli.py`:

```python
"""Command surface: `earnest check`, which wires the scanner, the index, the checks and the reporter."""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from earnest import adapters, git, reporter, structural
from earnest.index import build_index


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return its exit code.

    The exit code is 0 when no error-level finding sits at position behind or current, 1 when one does, and 2 when
    the check cannot run: Git cannot answer, a file cannot be read, or the reader of the log or the summary goes away.
    """
    parser = argparse.ArgumentParser(prog="earnest", description="Requirements traceability for LLM-written code.")
    # main never dispatches on the command, so a bare `earnest` must stop here rather than run the check
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="trace the repository; SARIF 2.1.0 on stdout, a summary on stderr")
    parser.parse_args(argv)
    try:
        root = git.repo_root(Path.cwd())
        commit = git.head_commit(root)
        sources = adapters.scan(root, git.work_tree_files(root))
    except (git.GitError, OSError) as error:
        sys.stderr.write(f"earnest: {error}\n")
        return 2
    index = build_index(sources)
    findings = structural.check(index)
    levels = structural.traced(index)
    try:
        sys.stdout.write(reporter.sarif(findings, levels, commit))
        sys.stdout.flush()
        sys.stderr.write(reporter.summary(findings, levels))
        sys.stderr.flush()
    except BrokenPipeError:  # a reader went away, as `head` does: send what is left to devnull, so exit stays quiet
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.dup2(devnull, sys.stderr.fileno())
        return 2
    # ponytail: every finding sits at position current until stages exist, so any error-level one fails the check
    return 1 if any(finding.level == "error" for finding in findings) else 0
```

In `packages/earnest/pyproject.toml`, replace:

```toml
dependencies = []
```

with:

```toml
dependencies = []

[project.scripts]
earnest = "earnest.cli:main"
```

Run: `make install`

Expected: uv reinstalls `earnest`, now with its console script `earnest` beside the interpreter.

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/test_cli.py tests/integration -v`

Expected: `8 passed`.

- [ ] **Step 5: Run the exit command and watch it pass**

Run: `uv run pytest tests/steps/test_trace_check.py`

Expected: PASS, `5 passed`. It is the first green run of the exit command since Task 1.

- [ ] **Step 6: Run the whole suite and the linters**

Run: `make test && make lint`

Expected: `130 passed` across the three tiers, then `make lint` exits 0.

- [ ] **Step 7: Mark M1 done on the milestone DAG**

In `docs/design/03-implementation-plan.md`, replace:

```text
  classDef done fill:#d4edda,stroke:#2e7d32
```

with:

```text
  classDef done fill:#d4edda,stroke:#2e7d32
  class M1 done
```

- [ ] **Step 8: Commit**

```bash
git add src/earnest/cli.py pyproject.toml uv.lock tests/unit/test_cli.py tests/integration ../../docs/design/03-implementation-plan.md
git commit -m "feat: run earnest check end to end, trace_check green"
```
