# M1 `trace_check` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the trace spine end to end: `earnest check` reads a repository's Markdown items and its Python, TypeScript and Gherkin tags, reports every broken link at file and line as a SARIF 2.1.0 log on stdout with a summary on stderr, places each `req` at untraced or traced, and exits non-zero on an error-level finding.

**Architecture:** One pass along the Container pipeline of `01`: `git.py` lists the tracked files, the `adapters/` hand each file's Markdown, comment or tag lines to `index.py`, whose grammar builds the items, links, tag regions and near-misses; `structural.py` decides the link findings and which requirements are traced, and `reporter.py` writes SARIF and the summary; `cli.py` wires the pipeline and sets the exit code. No plan exists yet, so every finding reaches no stage and sits at position `current` with no `properties.stage`. The behavior feature over the `broken-links` fixture is written first and stays red until the last task.

**Tech Stack:** Python 3.12 standard library at runtime (`argparse`, `tokenize`, `re`, `json`, `difflib`, `subprocess`, `bisect`); pytest with pytest-bdd 8.1 and pytest-cov; uv with hatchling; ruff, `mypy --strict`, vulture.

**Spec:** `docs/design/03-implementation-plan.md`, milestone M1 `trace_check`, and the sections its Context to load names in `docs/design/00-project-intent.md`, `docs/design/01-logic-design.md` and `docs/design/02-structural-design.md`; the scenarios are those of M1 in `docs/design/04-bdd-test-plan.md`.

## Global Constraints

- Every path matches the File and directory tree of `02` verbatim: modules under `packages/earnest/src/earnest/`, tests under `packages/earnest/tests/`.
- The runtime is the standard library alone (L4); the one new dependency is pytest-bdd, added to the `dev` extra with `uv add --optional dev pytest-bdd` in `packages/earnest` (L5).
- Lint bar (L1): ruff at "line length 120, complexity 10, five arguments, Google docstrings", `ruff format`, `mypy --strict` over `src/`, and vulture at `min_confidence = 80`; `make lint` runs all four.
- "`earnest check` writes the SARIF log to stdout and the summary to stderr" (D13).
- "A finding that reaches no stage has `properties.position` `current`, omits `properties.stage`, and its message opens with `in scope`"; with no plan yet, every M1 finding is one.
- "Each requirement's trace level and the three percentages travel under the run's `properties`"; the commit and the layers run travel under the run's `invocations`.
- "The exit code is non-zero only when an error-level finding exists at position behind or current."
- SC1: two runs over an unchanged repository give the same SARIF bytes, so the log holds no timestamp, and its keys and results are sorted.
- "No coverage threshold applies for now"; pytest reports coverage on every run.
- L6: fixtures are plain files whose Git history `tests/conftest.py` builds at test time; `tests/fixtures` stays out of ruff, pytest collection and markdownlint.
- Run every command in `packages/earnest/` unless a step names the repository root, and start each task with `make install`.
- Commit messages take the form `<type>: <description>`; before each commit, `git status --short` lists only the task's files.

## Review Focus

- A design doc that quotes an item in a code fence, such as `` `req~login-rate-limit~2` `` or `Covers: FR1.2` in an example: fenced lines start, end and key no item, and raise no near-miss (Task 6).
- `//` or tag-shaped text inside a TypeScript string or template literal, such as a URL: it is text, while a comment inside `${…}` still counts as a comment (Task 5).
- A Python file that stops tokenizing halfway through an agent's edit: the tags above the error still count, and the check never crashes (Task 5).
- `earnest check` run from a subdirectory, over file names with spaces or accents: the whole repository is read, and every path is relative to its root (Tasks 2 and 9).
- `earnest check` outside a Git work tree: one line on stderr, exit code 2, nothing on stdout, no traceback (Task 9).

## File Structure

| Path under `packages/earnest/` | Responsibility | Task |
| --- | --- | --- |
| `pyproject.toml`, `uv.lock` | pytest-bdd, the fixture excludes, then the `earnest` script | 1, 9 |
| `tests/conftest.py` | fixture repositories committed in `tmp_path` | 1, 2 |
| `tests/fixtures/broken-links/` | one seeded broken link of every kind, across four languages | 1 |
| `tests/features/trace_check.feature` | M1's scenarios, verbatim from `04` | 1 |
| `tests/steps/test_trace_check.py` | pytest-bdd steps; the exit command | 1 |
| `src/earnest/git.py` | tracked files, work-tree root and commit, through Git | 2 |
| `src/earnest/index.py` | the grammar: items, key lines, tags, regions, the Near-miss table | 3, 4 |
| `src/earnest/adapters/python.py`, `typescript.py` | comment lines and code lines of each language | 5 |
| `src/earnest/adapters/markdown.py`, `gherkin.py`, `__init__.py` | Markdown lines and fences, Gherkin tag lines, the adapter by suffix | 6 |
| `src/earnest/reporter.py` | `Finding`, trace levels, percentages, SARIF 2.1.0, the summary | 7 |
| `src/earnest/structural.py` | the link rules and whether each requirement is traced | 8 |
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
- Create: `packages/earnest/tests/conftest.py`
- Create: `packages/earnest/tests/fixtures/broken-links/` with `docs/intent.md`, `docs/scope.md`, `docs/requirements.md`, `docs/plan.md`, `src/auth.py`, `tests/test_auth.py`, `tests/sign_in.feature`, `web/login.ts`
- Create: `packages/earnest/tests/features/trace_check.feature`
- Test: `packages/earnest/tests/steps/test_trace_check.py`

**Interfaces:**

- Consumes: nothing; the package holds only `earnest.__version__`.
- Produces: the pytest fixture `fixture_repo`, a `Callable[[str], Path]` that copies `tests/fixtures/<name>` to `tmp_path / name`, commits it on `main` and returns the repository; the helper `_commit(repo: Path) -> Path` in `tests/conftest.py`, which Task 2 reuses; and the exit command `uv run pytest tests/steps/test_trace_check.py`, which runs the console script `earnest` beside `sys.executable` and stays red until Task 9 declares that script.

- [ ] **Step 1: Add pytest-bdd and keep the fixtures out of ruff and pytest**

Run:

```bash
cd packages/earnest
make install
uv add --optional dev pytest-bdd
```

Expected: `uv add` resolves `pytest-bdd` 8.1.0, installs it beside the rest of the `dev` extra, and appends it to the end of the `dev` list in `pyproject.toml`; `uv.lock` gains pytest-bdd, gherkin-official, Mako, parse and parse-type:

```toml
[project.optional-dependencies]
dev = [
    "mypy",
    "pre-commit",
    "ruff",
    "taskipy",
    "pytest",
    "pytest-cov",
    "pytest-asyncio",
    "hypothesis>=6.100",
    "vulture>=2.14",
    "pytest-bdd>=8.1.0",
]
```

`[tool.ruff]` gains the fixture exclude. In `packages/earnest/pyproject.toml`, replace:

```toml
src = ["src", "tests"]
```

with:

```toml
src = ["src", "tests"]
extend-exclude = ["tests/fixtures"]
```

`[tool.pytest.ini_options]` gains the collection ignore on `addopts`, the features directory, and one warning filter. pytest-bdd 8.1.0 calls two fixture APIs that pytest 9 deprecates, and the `"error"` filter would turn those warnings into failures. In the same file, replace:

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
addopts = "--cov=earnest --cov-report=term-missing --ignore=tests/fixtures"
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
grep -c 'ruff format --force-exclude -- "$$LINT_FILE" && uv run --project packages/earnest --all-extras ruff check --force-exclude --fix' Makefile
```

Expected: `1`.

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


# [utest->req~session-expiry~1]
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

- [ ] **Step 5: Write the fixture builder**

Create `packages/earnest/tests/conftest.py`:

```python
"""Shared fixtures: fixture repositories, their Git history built in tmp_path at test time."""

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"
_GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Earnest Fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.com",
    "GIT_AUTHOR_DATE": "2026-09-26T12:00:00+00:00",
    "GIT_COMMITTER_NAME": "Earnest Fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.com",
    "GIT_COMMITTER_DATE": "2026-09-26T12:00:00+00:00",
}


def _git(repo: Path, *args: str) -> str:
    """Run git in repo, shut off from the user's own Git configuration, and return its output."""
    done = subprocess.run(
        ["git", *args], cwd=repo, env={**os.environ, **_GIT_ENV}, capture_output=True, text=True, check=True
    )
    return done.stdout


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

  Scenario: Every finding names the change that fixes it (SC10)
    When the coding agent runs earnest check
    Then each finding at these places names its fix:
      | file                  | line | fix                                                                   |
      | docs/plan.md          | 7    | lower-case the name                                                   |
      | docs/plan.md          | 8    | rewrite it as `type~name~revision`                                    |
      | docs/requirements.md  | 11   | tag a unit test that verifies it with `[utest->req~lockout-notice~2]` |
      | docs/requirements.md  | 18   | add a `Covers:` line naming the `feat` it derives from                |
      | docs/requirements.md  | 22   | such as `impl, utest`                                                 |
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


scenarios("trace_check.feature")

EARNEST = Path(sys.executable).with_name("earnest")


def run_check(repo):
    """Run `earnest check` in repo, as the coding agent does."""
    return subprocess.run([str(EARNEST), "check"], cwd=repo, capture_output=True, text=True, check=False)


def sarif_run(run):
    """Return the one SARIF run in the log on stdout."""
    return json.loads(run.stdout)["runs"][0]


def located(result):
    """Return a result's file and line."""
    location = result["locations"][0]["physicalLocation"]
    return location["artifactLocation"]["uri"], location["region"]["startLine"]


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
    actual = sorted((result["ruleId"], *located(result)) for result in sarif_run(run)["results"])
    assert actual == expected


@then("every finding is in scope at position current, with no stage")
def all_current(run):
    for result in sarif_run(run)["results"]:
        assert result["properties"] == {"position": "current"}
        assert result["message"]["text"].startswith("in scope: ")


@then("each finding at these places names its fix:")
def findings_name_fix(run, datatable):
    results = sarif_run(run)["results"]
    for row in rows(datatable):
        texts = [r["message"]["text"] for r in results if located(r) == (row["file"], int(row["line"]))]
        assert any(row["fix"] in text for text in texts), (row, texts)


@then("the SARIF log gives each requirement one trace level:")
def trace_levels(run, datatable):
    expected = {row["requirement"]: row["level"] for row in rows(datatable)}
    assert sarif_run(run)["properties"]["traceLevels"] == expected


@then("each untraced requirement has a located finding that names it")
def untraced_have_reasons(run):
    run_log = sarif_run(run)
    for requirement, level in run_log["properties"]["traceLevels"].items():
        if level == "untraced":
            assert any(f"`{requirement}`" in result["message"]["text"] for result in run_log["results"]), requirement


@then(parsers.parse("the SARIF log gives the traced percentage as {percent:d}"))
def traced_percentage(run, percent):
    assert sarif_run(run)["properties"]["percentages"]["traced"] == percent


@then(parsers.parse('the summary leads with "{text}"'))
def summary_leads(run, text):
    assert run.stderr.splitlines()[0] == text


@then("the check exits non-zero, with the SARIF log on stdout")
def exits_non_zero(run):
    assert run.returncode != 0
    assert sarif_run(run)["results"]
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
  - `class GitError(Exception)`, raised when Git cannot answer, its message Git's own stderr line.
  - `repo_root(cwd: Path) -> Path`: the top of the work tree that holds `cwd`.
  - `tracked_files(root: Path) -> list[str]`: every tracked path relative to `root`, with forward slashes, in Git's order.
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

Create `packages/earnest/tests/unit/test_git.py`:

```python
"""Tests for earnest.git: the work tree's root, its tracked files and its commit."""

import re

import pytest

from earnest import git


def test_tracked_files_are_relative_to_the_root_even_with_spaces_and_accents(files_repo):
    repo = files_repo({"docs/a b.md": "a\n", "src/né.py": "x = 1\n", "top.ts": "let y = 2;\n"})
    assert git.tracked_files(repo) == ["docs/a b.md", "src/né.py", "top.ts"]


def test_the_root_of_a_subdirectory_is_the_top_of_the_work_tree(files_repo):
    repo = files_repo({"packages/app/a.py": "x = 1\n"})
    assert git.repo_root(repo / "packages" / "app") == repo.resolve()


def test_the_head_commit_is_a_full_sha(files_repo):
    repo = files_repo({"a.md": "a\n"})
    assert re.fullmatch(r"[0-9a-f]{40}", git.head_commit(repo))


def test_a_directory_outside_any_work_tree_raises_git_error(tmp_path):
    with pytest.raises(git.GitError, match="not a git repository"):
        git.repo_root(tmp_path)


def test_a_missing_git_raises_git_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(git.GitError, match="git is not on the PATH"):
        git.repo_root(tmp_path)
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/test_git.py -v`

Expected: FAIL at collection with `ImportError: cannot import name 'git' from 'earnest'`.

- [ ] **Step 3: Write `git.py`**

Create `packages/earnest/src/earnest/git.py`. `ls-files -z` keeps names with spaces and accents unquoted, and `--show-toplevel` makes a check from a subdirectory read the whole repository. `shutil.which` gives the absolute path ruff's S607 asks for; S603 stays, with its `noqa`, because every argument is a fixed Git subcommand:

```python
"""Repository reader: the work tree's root, its tracked files and its commit, read through Git."""

import shutil
import subprocess
from pathlib import Path


class GitError(Exception):
    """Git could not answer: no work tree, no commit, or no `git` on the PATH."""


def repo_root(cwd: Path) -> Path:
    """Return the top of the work tree that holds cwd, so a check run in a subdirectory reads the whole repository."""
    return Path(_git(cwd, "rev-parse", "--show-toplevel").strip())


def tracked_files(root: Path) -> list[str]:
    """Return every tracked path relative to root, with forward slashes, in Git's order."""
    return [path for path in _git(root, "ls-files", "-z").split("\0") if path]


def head_commit(root: Path) -> str:
    """Return the full sha of the commit HEAD names."""
    return _git(root, "rev-parse", "HEAD").strip()


def _git(cwd: Path, *args: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        msg = "git is not on the PATH"
        raise GitError(msg)
    try:
        done = subprocess.run([executable, *args], cwd=cwd, capture_output=True, text=True, check=True)  # noqa: S603
    except subprocess.CalledProcessError as error:
        raise GitError(error.stderr.strip()) from error
    return done.stdout
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/test_git.py -v && make lint`

Expected: `5 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/git.py tests/conftest.py tests/unit/test_git.py
git commit -m "feat: read the work tree, tracked files and commit through git"
```

### Task 3: The Markdown grammar and the Near-miss table, `index.py`

**Files:**

- Create: `packages/earnest/src/earnest/index.py`
- Test: `packages/earnest/tests/unit/test_index.py`

**Interfaces:**

- Consumes: nothing from earlier tasks.
- Produces, in `earnest.index`; later tasks use exactly these names and fields:
  - Surface names `MARKDOWN = "markdown"`, `COMMENT = "comment"`, `GHERKIN = "gherkin"`.
  - `Line(number: int, text: str)`, frozen.
  - `Source(path: str, surface: str, lines: tuple[Line, ...], code_lines: frozenset[int], line_count: int)`, frozen. For Markdown, `lines` holds every line and `code_lines` the fenced ones; for the comment and Gherkin surfaces, `lines` holds the comment or tag lines and `code_lines` the lines that hold code.
  - `Id(type: str, name: str, revision: int)`, frozen and ordered; `str(id)` gives `type~name~revision`.
  - `Item(id: Id, path: str, line: int, needs: tuple[str, ...] | None = None)`, frozen; `needs` is None without a valid `Needs:` line.
  - `Link(key: str, type: str, target: Id, path: str, line: int, owner: Id | None = None, region: tuple[int, int] | None = None)`, frozen; `key` is `Covers`, `Drivers`, `Delivers` or `Depends`, `type` the naming item's type or the tag's artifact type, `owner` the item whose key line names `target`.
  - `NearMiss(path: str, line: int, text: str, fix: str)`, frozen.
  - `Index(items: tuple[Item, ...], links: tuple[Link, ...], near_misses: tuple[NearMiss, ...])`, frozen, with `defined() -> dict[tuple[str, str], Item]`, the first item of each type and name.
  - `build_index(sources: Iterable[Source]) -> Index`; this task reads Markdown sources, and Task 4 adds the tag surfaces.

- [ ] **Step 1: Write the failing tests**

Create `packages/earnest/tests/unit/test_index.py`:

```python
"""Tests for earnest.index: the grammar, the Near-miss table and the Region rule."""

import pytest

from earnest.index import MARKDOWN, Id, Item, Line, Source, build_index


def markdown(text, fenced=frozenset()):
    lines = tuple(Line(number, raw) for number, raw in enumerate(text.splitlines(), start=1))
    return Source("docs/a.md", MARKDOWN, lines, fenced, len(lines))


def test_an_item_runs_from_its_id_line_to_the_next_id_line_or_heading():
    text = (
        "`req~a~2`\n\nWhen x, the s shall y.\n\nNeeds: impl, itest\nCovers: feat~f~1, feat~g~1\n"
        "### `req~b~1`\n\nCovers: feat~f~1\n## Notes\n\nCovers: feat~h~1\n"
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


@pytest.mark.parametrize(
    ("line", "fix"),
    [
        ("`req~x`", "append `~` and the item's current revision"),
        ("### `req~Login~1`", "lower-case the name"),
        ("`req~login_rate~1`", "rewrite it as `type~name~revision` in backticks"),
    ],
)
def test_a_malformed_id_line_is_a_near_miss_that_ends_the_item_above(line, fix):
    index = build_index([markdown(f"`req~a~1`\n{line}\nCovers: feat~f~1\n")])
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
        ("Needs: impl utest", "impl utest", "rewrite it as item types"),
        ("Override: req~a~1 implemented 3f9c2a1, why", "req~a~1 implemented 3f9c2a1, why", "rewrite it as `type~"),
    ],
)
def test_a_key_line_value_that_fails_its_grammar_is_a_near_miss(line, text, fix):
    index = build_index([markdown(f"`req~a~1`\n{line}\n")])
    (miss,) = index.near_misses
    assert (miss.line, miss.text) == (2, text)
    assert miss.fix.startswith(fix)


def test_a_valid_needs_line_and_override_parse_cleanly():
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
    assert index.defined()[("req", "a")].line == 1
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/test_index.py -v`

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'earnest.index'`.

- [ ] **Step 3: Write `index.py` with the Markdown grammar**

The item-span rule of the Grammar section: an item runs from its id line to the next id line, the next heading or the end of the file; fenced lines are body and never start, end or key an item; a key, a colon and a space make a key line even when the value fails; a malformed id line ends the item above it. `_FIXES` is the Near-miss table in order, and the last row's fix quotes the form the text's place takes.

Create `packages/earnest/src/earnest/index.py`:

```python
"""Grammar and index: items, links and near-misses from the lines the host adapters hand over."""

import re
from collections.abc import Iterable
from dataclasses import dataclass


MARKDOWN = "markdown"
COMMENT = "comment"
GHERKIN = "gherkin"

_ID = r"([a-z]+)~([a-z0-9-]+)~([1-9][0-9]*)"
_ID_ENTRY = re.compile(_ID)
_ID_LINE = re.compile(rf"(?:#+ )?`{_ID}`")
_LOOSE_ID_LINE = re.compile(r"(?:#+[ \t]+)?`([^`]*~[^`]*)`")
_HEADING = re.compile(r"#{1,6}(?:[ \t]|$)")
_KEY_LINE = re.compile(r"(Needs|Covers|Drivers|Delivers|Depends|Override): (.*)")
_VALUE_FORMS = {
    "Needs": re.compile(r"[a-z]+(?:, [a-z]+)*"),
    "Override": re.compile(rf"{_ID} (?:implemented|tested) at [0-9a-f]+,.+"),
}

# The Near-miss table of the logic design, in order; the first pattern that fits gives the canned fix.
_FIXES = (
    (re.compile(r"\[[a-z]+-[^>]"), "write `->` between the artifact type and the id"),
    (re.compile(r"(?:^|->|:)[A-Za-z]+~[^~\s\]]+\]?$"), "append `~` and the item's current revision"),
    (re.compile(r"[a-z]+~[^~\s]*[A-Z][^~\s]*~"), "lower-case the name"),
    (re.compile(r"^@[a-z]+[ \t]+[a-z]+~"), "put `:` between the artifact type and the id"),
    (
        re.compile(r"^[A-Z]+-?[0-9]+(?:\.[0-9]+)*$"),
        "lower-case it, turn dots into hyphens, and add the type and the revision, so `FR1.2` becomes `req~fr1-2~1`",
    ),
)
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
    """One tracked file as its host adapter saw it.

    For Markdown, `lines` holds every line and `code_lines` the lines inside code fences. For comment and
    Gherkin surfaces, `lines` holds the comment or tag lines and `code_lines` the lines that hold code.
    """

    path: str
    surface: str
    lines: tuple[Line, ...]
    code_lines: frozenset[int]
    line_count: int


@dataclass(frozen=True, order=True)
class Id:
    """An item id: type, name and revision."""

    type: str
    name: str
    revision: int

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
    target, and is None for a tag. `region` is the first and last line a tag governs, and is None for a key line.
    """

    key: str
    type: str
    target: Id
    path: str
    line: int
    owner: Id | None = None
    region: tuple[int, int] | None = None


@dataclass(frozen=True)
class NearMiss:
    """Text that nearly parses as a tag, an id line or a key-line value, with its canned fix."""

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

    def defined(self) -> dict[tuple[str, str], Item]:
        """Map each type and name to the first item that defines it; later items with that id are duplicates."""
        found: dict[tuple[str, str], Item] = {}
        for item in self.items:
            found.setdefault((item.id.type, item.id.name), item)
        return found


_Parsed = tuple[list[Item], list[Link], list[NearMiss]]


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


def _near_miss(path: str, line: int, text: str, place: str) -> NearMiss:
    for pattern, fix in _FIXES:
        if pattern.search(text):
            return NearMiss(path, line, text, fix)
    return NearMiss(path, line, text, f"rewrite it as {_FORMS[place]}")


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
    """Split a Markdown file into items: an id line owns the lines up to the next id line or heading."""
    spans: list[tuple[Id, int, list[Line]]] = []
    misses: list[NearMiss] = []
    body: list[Line] | None = None
    for line in source.lines:
        if line.number in source.code_lines:
            continue  # fenced code is body, and never starts, ends or keys an item
        text = line.text.rstrip()
        if strict := _ID_LINE.fullmatch(text):
            body = []
            spans.append((_to_id(strict), line.number, body))
        elif loose := _LOOSE_ID_LINE.fullmatch(text):
            misses.append(_near_miss(source.path, line.number, loose.group(1), "id line"))
            body = None
        elif _HEADING.match(text):
            body = None
        elif body is not None:
            body.append(line)
    return spans, misses


def _keys(path: str, owner: Id, lines: Iterable[Line]) -> tuple[tuple[str, ...] | None, list[Link], list[NearMiss]]:
    """Read an item's key lines: its needs, its links, and every value that fails to parse."""
    needs: tuple[str, ...] | None = None
    links: list[Link] = []
    misses: list[NearMiss] = []
    for line in lines:
        match = _KEY_LINE.match(line.text.rstrip())
        if match is None:
            continue
        key, value = match.groups()
        if key in _VALUE_FORMS:
            if not _VALUE_FORMS[key].fullmatch(value):
                misses.append(_near_miss(path, line.number, value, key))
            elif key == "Needs":
                needs = tuple(value.split(", "))
            continue
        for entry in filter(None, (part.strip() for part in value.split(","))):
            if target := _ID_ENTRY.fullmatch(entry):
                links.append(Link(key, owner.type, _to_id(target), path, line.number, owner=owner))
            else:
                misses.append(_near_miss(path, line.number, entry, "id"))
    return needs, links, misses
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/test_index.py -v && make lint`

Expected: `13 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/index.py tests/unit/test_index.py
git commit -m "feat: parse Markdown items, key lines and near-misses into the index"
```

### Task 4: Tag surfaces and the Region rule, `index.py`

**Files:**

- Modify: `packages/earnest/src/earnest/index.py` (tag patterns, two `_FORMS` rows, `build_index`, two new functions at the end)
- Test: `packages/earnest/tests/unit/test_index.py` (import line, and tests appended)

**Interfaces:**

- Consumes: everything Task 3 produces in `earnest.index`.
- Produces: `build_index(sources: Iterable[Source]) -> Index` now also reads `COMMENT` and `GHERKIN` sources. Each tag that parses becomes `Link("Covers", <artifact type>, <target Id>, path, line, region=(first, last))`, with `owner` None; each tag candidate that fails its surface's grammar becomes a `NearMiss`. Regions follow the Region rule, and repeated tags for one id govern the union of their regions because each tag keeps its own.

- [ ] **Step 1: Write the failing tests**

In `packages/earnest/tests/unit/test_index.py`, replace:

```python
from earnest.index import MARKDOWN, Id, Item, Line, Source, build_index
```

with:

```python
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Id, Item, Line, Link, Source, build_index
```

Append to `packages/earnest/tests/unit/test_index.py`:

```python


def comments(lines, code, line_count):
    return Source("src/a.py", COMMENT, tuple(Line(n, t) for n, t in sorted(lines.items())), frozenset(code), line_count)


def test_a_comment_tag_covers_its_target_from_its_artifact_type():
    index = build_index([comments({3: "# see [impl->req~a~2] and [utest->req~b~1]"}, {4}, 4)])
    assert index.links == (
        Link("Covers", "impl", Id("req", "a", 2), "src/a.py", 3, region=(3, 4)),
        Link("Covers", "utest", Id("req", "b", 1), "src/a.py", 3, region=(3, 4)),
    )


@pytest.mark.parametrize(
    ("surface", "text", "fix"),
    [
        (COMMENT, "# [impl-req~x~1]", "write `->`"),
        (COMMENT, "# [impl->req~x]", "append `~`"),
        (COMMENT, "# [impl->req~x_y~1]", "rewrite it as `[type->type~name~revision]`"),
        (GHERKIN, "@stest:feat~Login~1", "lower-case the name"),
        (GHERKIN, "@stest feat~login~1", "put `:`"),
        (GHERKIN, "@stest:feat~login~1,", "rewrite it as `@type:type~name~revision`"),
    ],
)
def test_a_tag_that_fails_its_surface_is_a_near_miss(surface, text, fix):
    (miss,) = build_index([Source("f", surface, (Line(1, text),), frozenset(), 1)]).near_misses
    assert miss.fix.startswith(fix)


def test_other_gherkin_tags_and_at_signs_inside_words_are_left_alone():
    gherkin = Source("f.feature", GHERKIN, (Line(1, "@smoke @stest:feat~a~1"),), frozenset(), 1)
    comment = comments({1: "# scp user@host:~/notes"}, set(), 1)
    index = build_index([gherkin, comment])
    assert [str(link.target) for link in index.links] == ["feat~a~1"]
    assert index.near_misses == ()


def test_a_tag_governs_its_lines_up_to_the_next_tag_or_the_end_of_the_file():
    source = comments({1: "# [impl->req~a~1]", 4: "# [impl->req~b~1]"}, {2, 3, 5, 6}, 7)
    assert [link.region for link in build_index([source]).links] == [(1, 3), (4, 7)]


def test_tags_with_no_code_between_them_share_the_region_that_follows():
    source = comments(
        {1: "# [impl->req~a~1]", 2: "# a note", 3: "# [utest->req~a~1]", 5: "# [impl->req~c~1]"}, {4, 6}, 6
    )
    assert [link.region for link in build_index([source]).links] == [(1, 4), (3, 4), (5, 6)]


def test_a_tag_on_a_code_line_ends_the_stack_above_it():
    source = comments({1: "# [impl->req~a~1]", 2: "# [impl->req~b~1]"}, {1, 2, 3}, 3)
    assert [link.region for link in build_index([source]).links] == [(1, 1), (2, 3)]
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/test_index.py -v`

Expected: FAIL, the 11 new tests red (`build_index` still reads only Markdown, so `index.links` is empty and `(miss,) =` finds no near-miss) and the 13 Markdown tests green: `11 failed, 13 passed`.

- [ ] **Step 3: Add the tag surfaces and the Region rule**

A tag candidate is the near-miss superset of the tag surfaces: a bracketed token with a `~` inside, or a token that opens with `@` and holds a `~`, including `@stest feat~login~1`. The surface's strict pattern decides whether it parses.

In `packages/earnest/src/earnest/index.py`, replace:

```python
    "Override": re.compile(rf"{_ID} (?:implemented|tested) at [0-9a-f]+,.+"),
}

# The Near-miss table of the logic design, in order; the first pattern that fits gives the canned fix.
```

with:

```python
    "Override": re.compile(rf"{_ID} (?:implemented|tested) at [0-9a-f]+,.+"),
}
_TAG_FORMS = {
    COMMENT: re.compile(rf"\[([a-z]+)->{_ID}\]"),
    GHERKIN: re.compile(rf"@([a-z]+):{_ID}"),
}
_TAG_CANDIDATE = re.compile(r"\[[^\[\]\s]*~[^\[\]\s]*\]|(?<!\S)@[a-z]+[ \t]+[a-z]+~\S*|(?<!\S)@[^\s@~]*~\S*")

# The Near-miss table of the logic design, in order; the first pattern that fits gives the canned fix.
```

In the same file, replace:

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
    found: list[tuple[int, str, Id]] = []
    misses: list[NearMiss] = []
    for line in source.lines:
        for candidate in _TAG_CANDIDATE.finditer(line.text):
            if tag := strict.fullmatch(candidate.group()):
                found.append((line.number, tag.group(1), _to_id(tag, 2)))
            else:
                misses.append(_near_miss(source.path, line.number, candidate.group(), source.surface))
    regions = _regions({number for number, _, _ in found}, source.code_lines, source.line_count)
    links = [
        Link("Covers", kind, target, source.path, number, region=regions[number]) for number, kind, target in found
    ]
    return [], links, misses


def _regions(tag_lines: set[int], code_lines: frozenset[int], line_count: int) -> dict[int, tuple[int, int]]:
    """Apply the Region rule to one file's tag lines.

    A tag governs its own line up to the line before the next tag, or to the end of the file. Tags with no code
    between them stack and share the region that follows the stack; code on a tag's own line ends the stack above it.
    """
    ordered = sorted(tag_lines)
    regions: dict[int, tuple[int, int]] = {}
    for position, start in enumerate(ordered):
        end = line_count
        previous = start
        for following in ordered[position + 1 :]:
            if any(number in code_lines for number in range(previous + 1, following + 1)):
                end = following - 1
                break
            previous = following
        regions[start] = (start, end)
    return regions
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/test_index.py -v && make lint`

Expected: `24 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/index.py tests/unit/test_index.py
git commit -m "feat: parse comment and Gherkin tags with their regions"
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
- Produces: `earnest.adapters.python.scan(text: str) -> tuple[tuple[Line, ...], frozenset[int]]` and `earnest.adapters.typescript.scan(text: str) -> tuple[tuple[Line, ...], frozenset[int]]`. Each returns the file's comment lines, one `Line` per physical line with its comment text, and the numbers of the lines that hold code, which the Region rule reads. Task 6 maps `.py` to the first, and `.ts` and `.tsx` to the second, under the `COMMENT` surface.

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


def test_comments_come_with_their_line_numbers_and_strings_stay_code():
    lines, code = python.scan('x = "# not a comment"  # [impl->req~a~1]\n\n# second\ny = 2\n')
    assert lines == (Line(1, "# [impl->req~a~1]"), Line(3, "# second"))
    assert code == {1, 4}


def test_a_multi_line_string_is_code_on_every_line():
    _, code = python.scan('x = """\n# inside a string\n"""\n')
    assert code == {1, 2, 3}


def test_a_file_that_stops_tokenizing_keeps_the_comments_before_the_error():
    lines, code = python.scan("# [impl->req~a~1]\ndef f(:\n    x = (\n")
    assert lines == (Line(1, "# [impl->req~a~1]"),)
    assert 2 in code
```

Create `packages/earnest/tests/unit/adapters/test_typescript.py`:

```python
"""Tests for the TypeScript host adapter."""

from earnest.adapters import typescript
from earnest.index import Line


def test_line_and_block_comments_are_read_line_by_line():
    lines, code = typescript.scan("// [impl->req~a~1]\nconst x = 1; /* one\n[impl->req~b~1] */\n")
    assert lines == (Line(1, "// [impl->req~a~1]"), Line(2, "/* one"), Line(3, "[impl->req~b~1] */"))
    assert code == {2}


def test_comment_markers_inside_strings_and_template_literals_are_text():
    text = (
        'const url = "https://example.com/[impl->req~a~1]";\n'
        "const note = 'a // b';\n"
        "const t = `line // [impl->req~b~1]\n${f(`// nested`)} // still text`;\n"
        "// [impl->req~c~1]\n"
    )
    lines, code = typescript.scan(text)
    assert lines == (Line(5, "// [impl->req~c~1]"),)
    assert code == {1, 2, 3, 4}


def test_a_comment_inside_a_template_expression_is_a_comment():
    lines, _ = typescript.scan("const t = `a ${ // [impl->req~a~1]\n  b } c`;\n")
    assert lines == (Line(1, "// [impl->req~a~1]"),)


def test_braces_inside_a_template_expression_do_not_end_it_early():
    lines, _ = typescript.scan("const t = `x ${ {a: '//'}.a } // text`;\n// [impl->req~a~1]\n")
    assert lines == (Line(2, "// [impl->req~a~1]"),)
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/adapters -v`

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'earnest.adapters'` in both modules.

- [ ] **Step 3: Write the two adapters**

Create `packages/earnest/src/earnest/adapters/__init__.py`:

```python
"""Host adapters: each tracked file's adapter, picked by suffix, hands its lines to the grammar."""
```

Create `packages/earnest/src/earnest/adapters/python.py`. `tokenize` yields each token before it raises, so a file that stops tokenizing keeps its earlier comments:

```python
"""Python host adapter: `#` comments, through `tokenize`."""

import contextlib
import io
import tokenize

from earnest.index import Line


_LAYOUT = frozenset(
    {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER},
)


def scan(text: str) -> tuple[tuple[Line, ...], frozenset[int]]:
    """Return the file's comments and the lines that hold code.

    A file that stops tokenizing, such as one an agent is halfway through editing, keeps what came before the error.
    """
    comments: list[Line] = []
    code: set[int] = set()
    with contextlib.suppress(tokenize.TokenError, SyntaxError):
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                comments.append(Line(token.start[0], token.string))
            elif token.type not in _LAYOUT:
                code.update(range(token.start[0], token.end[0] + 1))
    return tuple(comments), frozenset(code)
```

Create `packages/earnest/src/earnest/adapters/typescript.py`. The scan alternates between code and template text: a backtick opens a template, `${` opens an expression whose braces it counts, and the `}` that balances them returns to the template. A regular expression literal that holds `/*` would read as a comment; a tag never sits in one:

```python
"""TypeScript host adapter: `//` and block comments outside string and template literals."""

import bisect
import re
from dataclasses import dataclass, field

from earnest.index import Line


_TOKEN = re.compile(
    r"(?P<comment>//[^\n]*|/\*[\s\S]*?(?:\*/|\Z))"
    r"|(?P<string>'(?:\\[\s\S]|[^'\\\n])*'?|\"(?:\\[\s\S]|[^\"\\\n])*\"?)"
    r"|(?P<tick>`)|(?P<open>\{)|(?P<close>\})|(?P<code>[^\s/'\"`{}]+|/)",
)
_TEMPLATE_STOP = re.compile(r"\\[\s\S]|`|\$\{")


@dataclass
class _Scan:
    text: str
    starts: list[int]
    comments: list[Line] = field(default_factory=list)
    code: set[int] = field(default_factory=set)
    braces: list[int] = field(default_factory=list)  # open braces inside each `${` the scan is in

    def line(self, offset: int) -> int:
        return bisect.bisect_right(self.starts, offset)

    def mark(self, start: int, end: int) -> None:
        if end > start:
            self.code.update(range(self.line(start), self.line(end - 1) + 1))


def scan(text: str) -> tuple[tuple[Line, ...], frozenset[int]]:
    """Return the comment lines outside string and template literals, and the lines that hold code.

    A block comment gives one line per physical line. Template literals nest through `${`, so a comment inside a
    template's expression is still a comment, and `//` inside any literal is text.
    """
    state = _Scan(text, [0, *(match.end() for match in re.finditer("\n", text))])
    position = 0
    while position < len(text):
        position = _template(state, _code(state, position))
    return tuple(state.comments), frozenset(state.code)


def _code(state: _Scan, position: int) -> int:
    """Scan code from position; return where template text starts, or the end of the text."""
    for match in _TOKEN.finditer(state.text, position):
        kind = match.lastgroup
        if kind == "comment":
            first = state.line(match.start())
            state.comments.extend(Line(first + offset, part) for offset, part in enumerate(match.group().split("\n")))
            continue
        state.mark(match.start(), match.end())
        if kind == "tick":
            return match.end()
        if kind == "open" and state.braces:
            state.braces[-1] += 1
        elif kind == "close" and state.braces:
            if state.braces[-1] == 0:
                state.braces.pop()
                return match.end()
            state.braces[-1] -= 1
    return len(state.text)


def _template(state: _Scan, position: int) -> int:
    """Scan template text from position; return where code resumes, after its closing backtick or a `${`."""
    for match in _TEMPLATE_STOP.finditer(state.text, position):
        if match.group() in ("`", "${"):
            state.mark(position, match.end())
            if match.group() == "${":
                state.braces.append(0)
            return match.end()
    state.mark(position, len(state.text))
    return len(state.text)
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/adapters -v && make lint`

Expected: `7 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/adapters tests/unit/adapters
git commit -m "feat: read Python and TypeScript comments with their code lines"
```

### Task 6: The Markdown and Gherkin adapters, and the adapter by suffix

**Files:**

- Create: `packages/earnest/src/earnest/adapters/markdown.py`
- Create: `packages/earnest/src/earnest/adapters/gherkin.py`
- Modify: `packages/earnest/src/earnest/adapters/__init__.py` (the whole file)
- Test: `packages/earnest/tests/unit/adapters/test_markdown.py`, `packages/earnest/tests/unit/adapters/test_gherkin.py`, `packages/earnest/tests/unit/test_adapters.py`

**Interfaces:**

- Consumes: `python.scan` and `typescript.scan` (Task 5); `Line`, `Source`, `MARKDOWN`, `COMMENT`, `GHERKIN` and `build_index` from `earnest.index` (Tasks 3 and 4).
- Produces:
  - `earnest.adapters.markdown.scan(text: str) -> tuple[tuple[Line, ...], frozenset[int]]`: every line, and the lines inside code fences, fence lines included.
  - `earnest.adapters.gherkin.scan(text: str) -> tuple[tuple[Line, ...], frozenset[int]]`: the `@` tag lines, and the keyword, step, table and doc-string lines as code.
  - `earnest.adapters.scan(root: Path, paths: Iterable[str]) -> list[Source]`: one `Source` per path whose suffix an adapter reads (`.md`, `.py`, `.ts`, `.tsx`, `.feature`), in the order given; other suffixes, and paths gone from the work tree, are skipped; text that is not UTF-8 is replaced, never fatal.

- [ ] **Step 1: Write the failing tests**

Create `packages/earnest/tests/unit/adapters/test_markdown.py`:

````python
"""Tests for the Markdown host adapter."""

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
    index = build_index([Source("docs/a.md", MARKDOWN, lines, fenced, len(lines))])
    assert [str(item.id) for item in index.items] == ["req~real~1"]
    assert index.items[0].needs == ("impl",)
    assert index.near_misses == ()


def test_a_fence_closes_only_on_its_own_marker_at_least_as_long():
    _, fenced = markdown.scan("~~~~\n```\n~~~\n~~~~\nafter\n")
    assert fenced == {1, 2, 3, 4}


def test_an_unclosed_fence_runs_to_the_end_of_the_file():
    _, fenced = markdown.scan("text\n~~~\n`req~a~1`\n")
    assert fenced == {2, 3}
````

Create `packages/earnest/tests/unit/adapters/test_gherkin.py`:

```python
"""Tests for the Gherkin host adapter."""

from earnest.adapters import gherkin
from earnest.index import Line


def test_tag_lines_are_read_and_keyword_and_step_lines_are_code():
    text = "Feature: F\n\n  @stest:feat~a~1 @smoke\n  Scenario: S\n    Given x\n  # a comment\n"
    lines, code = gherkin.scan(text)
    assert lines == (Line(3, "  @stest:feat~a~1 @smoke"),)
    assert code == {1, 4, 5}
```

Create `packages/earnest/tests/unit/test_adapters.py`:

```python
"""Tests for earnest.adapters: the adapter picked by suffix for each tracked file."""

from earnest import adapters
from earnest.index import COMMENT, GHERKIN, MARKDOWN


def test_each_suffix_gets_its_adapter_and_other_files_are_skipped(tmp_path):
    files = {
        "a.md": "`req~a~1`\n",
        "b.py": "# [impl->req~a~1]\nx = 1\n",
        "c.ts": "// [impl->req~a~1]\n",
        "d.feature": "@stest:feat~f~1\nScenario: S\n",
        "e.txt": "[impl->req~a~1]\n",
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    sources = adapters.scan(tmp_path, [*files, "gone.py"])
    assert [(source.path, source.surface, source.line_count) for source in sources] == [
        ("a.md", MARKDOWN, 1),
        ("b.py", COMMENT, 2),
        ("c.ts", COMMENT, 1),
        ("d.feature", GHERKIN, 2),
    ]


def test_bytes_that_are_not_utf_8_are_replaced(tmp_path):
    (tmp_path / "a.py").write_bytes(b"# [impl->req~a~1] \xff\n")
    (source,) = adapters.scan(tmp_path, ["a.py"])
    assert source.lines[0].text == "# [impl->req~a~1] \ufffd"
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/adapters tests/unit/test_adapters.py -v`

Expected: FAIL, `Interrupted: 2 errors during collection`, from `ImportError: cannot import name 'markdown' from 'earnest.adapters'` and `ImportError: cannot import name 'gherkin' from 'earnest.adapters'`.

- [ ] **Step 3: Write the adapters and the scan by suffix**

Create `packages/earnest/src/earnest/adapters/markdown.py`. A fence is three or more backticks or tildes after up to three spaces, and it closes on the same marker at least as long, alone on its line:

```python
"""Markdown host adapter: the lines of a stage artifact, with its code fences marked."""

import re

from earnest.index import Line


_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})")


def scan(text: str) -> tuple[tuple[Line, ...], frozenset[int]]:
    """Return every line, and the lines inside code fences, fence lines included; an unclosed fence runs to the end."""
    lines: list[Line] = []
    fenced: set[int] = set()
    fence = ""
    for number, raw in enumerate(text.splitlines(), start=1):
        lines.append(Line(number, raw))
        marker = _FENCE.match(raw)
        if fence:
            fenced.add(number)
            if marker and marker.group(1).startswith(fence) and raw.strip() == marker.group(1):
                fence = ""
        elif marker:
            fenced.add(number)
            fence = marker.group(1)
    return tuple(lines), frozenset(fenced)
```

Create `packages/earnest/src/earnest/adapters/gherkin.py`:

```python
"""Gherkin host adapter: `@` tag lines, and the scenario lines each one tags."""

from earnest.index import Line


def scan(text: str) -> tuple[tuple[Line, ...], frozenset[int]]:
    """Return the `@` tag lines, and the lines that hold keywords, steps, tables or doc strings."""
    tags: list[Line] = []
    code: set[int] = set()
    for number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if stripped.startswith("@"):
            tags.append(Line(number, raw))
        elif stripped and not stripped.startswith("#"):
            code.add(number)
    return tuple(tags), frozenset(code)
```

Replace the whole of `packages/earnest/src/earnest/adapters/__init__.py` with:

```python
"""Host adapters: each tracked file's adapter, picked by suffix, hands its lines to the grammar."""

from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath

from earnest.adapters import gherkin, markdown, python, typescript
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Line, Source


_Scan = Callable[[str], tuple[tuple[Line, ...], frozenset[int]]]
_BY_SUFFIX: dict[str, tuple[str, _Scan]] = {
    ".md": (MARKDOWN, markdown.scan),
    ".py": (COMMENT, python.scan),
    ".ts": (COMMENT, typescript.scan),
    ".tsx": (COMMENT, typescript.scan),
    ".feature": (GHERKIN, gherkin.scan),
}


def scan(root: Path, paths: Iterable[str]) -> list[Source]:
    """Scan each path under root that an adapter reads, skipping other suffixes and files gone from the work tree."""
    sources: list[Source] = []
    for path in paths:
        adapter = _BY_SUFFIX.get(PurePosixPath(path).suffix)
        file = root / path
        if adapter is None or not file.is_file():
            continue
        surface, scan_text = adapter
        text = file.read_text(encoding="utf-8", errors="replace")
        lines, code_lines = scan_text(text)
        sources.append(Source(path, surface, lines, code_lines, len(text.splitlines())))
    return sources
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit -v && make lint`

Expected: `44 passed`, the 7 new tests among them, then `make lint` exits 0.

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

- Consumes: `Id` from `earnest.index` (Task 3).
- Produces, in `earnest.reporter`:
  - `RULES: dict[str, str]`, rule id to SARIF level, for the seven link rules: `earnest/duplicate`, `earnest/gap`, `earnest/near-miss`, `earnest/orphaned`, `earnest/outdated` and `earnest/predated` at `error`, `earnest/unwanted` at `warning`.
  - `LEVELS = ("untraced", "traced", "judged", "evidenced")`.
  - `Finding(path: str, line: int, rule: str, message: str)`, frozen and ordered by path, line, rule and message, with the properties `level -> str`, the rule's SARIF level, and `text -> str`, the message as reported, opening with `in scope:`. `message` names the change to make and never repeats the position.
  - `trace_levels(traced: Mapping[Id, bool]) -> dict[str, str]`: each requirement id, as text, to `traced` or `untraced`.
  - `percentages(levels: Mapping[str, str]) -> dict[str, int]`: `traced`, `judged` and `evidenced`, each the share of requirements at that level or above, rounded to a whole percent, and 0 with no requirements.
  - `sarif(findings: Sequence[Finding], levels: Mapping[str, str], commit: str) -> str`: one SARIF 2.1.0 log as JSON text, keys and results sorted.
  - `summary(findings: Sequence[Finding], levels: Mapping[str, str]) -> str`: the stderr text, whose first line is `traced N%, judged N%, evidenced N%; requirements: N`.

- [ ] **Step 1: Write the failing tests**

Create `packages/earnest/tests/unit/test_reporter.py`:

```python
"""Tests for earnest.reporter: SARIF 2.1.0, trace levels, percentages and the summary."""

import json

from earnest import reporter
from earnest.index import Id
from earnest.reporter import Finding


FINDINGS = [Finding("src/b.py", 3, "earnest/unwanted", "b"), Finding("docs/a.md", 9, "earnest/gap", "a")]
LEVELS = {"req~a~1": "traced", "req~b~1": "untraced", "req~c~1": "traced"}


def test_each_requirement_is_named_by_its_id_at_one_level():
    traced = {Id("req", "b", 1): False, Id("req", "a", 2): True}
    assert reporter.trace_levels(traced) == {"req~b~1": "untraced", "req~a~2": "traced"}


def test_percentages_count_each_level_and_above_in_whole_percent():
    assert reporter.percentages(LEVELS) == {"traced": 67, "judged": 0, "evidenced": 0}
    assert reporter.percentages({}) == {"traced": 0, "judged": 0, "evidenced": 0}


def test_the_log_is_one_sarif_2_1_0_run_with_located_results_in_order():
    log = json.loads(reporter.sarif(FINDINGS, LEVELS, "abc123"))
    assert log["version"] == "2.1.0"
    (run,) = log["runs"]
    assert [(result["ruleId"], result["level"]) for result in run["results"]] == [
        ("earnest/gap", "error"),
        ("earnest/unwanted", "warning"),
    ]
    first = run["results"][0]
    assert first["locations"] == [
        {"physicalLocation": {"artifactLocation": {"uri": "docs/a.md"}, "region": {"startLine": 9}}},
    ]
    assert first["message"] == {"text": "in scope: a"}
    assert first["properties"] == {"position": "current"}
    assert run["properties"] == {"traceLevels": LEVELS, "percentages": {"traced": 67, "judged": 0, "evidenced": 0}}
    assert run["invocations"] == [
        {"executionSuccessful": True, "properties": {"commit": "abc123", "layers": ["trace"]}}
    ]
    assert {rule["id"] for rule in run["tool"]["driver"]["rules"]} == set(reporter.RULES)


def test_the_same_findings_in_another_order_give_the_same_bytes():
    shuffled = dict(reversed(LEVELS.items()))
    assert reporter.sarif(FINDINGS, LEVELS, "abc") == reporter.sarif(FINDINGS[::-1], shuffled, "abc")


def test_the_summary_leads_with_the_three_percentages():
    lines = reporter.summary(FINDINGS, LEVELS).splitlines()
    assert lines[0] == "traced 67%, judged 0%, evidenced 0%; requirements: 3"
    assert lines[1:4] == ["  req~a~1: traced", "  req~b~1: untraced", "  req~c~1: traced"]
    assert lines[4] == "docs/a.md:9: error earnest/gap: in scope: a"
    assert lines[-1] == "findings: 2, errors: 1"
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/test_reporter.py -v`

Expected: FAIL at collection with `ImportError: cannot import name 'reporter' from 'earnest'`.

- [ ] **Step 3: Write `reporter.py`**

`json.dumps` with `sort_keys=True` and sorted results give the same bytes for the same findings, and the log carries no timestamp. The commit and the layers run ride on the invocation, whose `executionSuccessful` SARIF requires.

Create `packages/earnest/src/earnest/reporter.py`:

```python
"""Reporter: the SARIF 2.1.0 log, each requirement's trace level, and the summary that leads with three percentages."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from earnest import __version__
from earnest.index import Id


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
    """A located result: file, line, rule, and a message that names the change to make."""

    path: str
    line: int
    rule: str
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


def trace_levels(traced: Mapping[Id, bool]) -> dict[str, str]:
    """Name each requirement's trace level, keyed by its id: traced when every cover it needs resolves."""
    return {str(req): "traced" if ok else "untraced" for req, ok in traced.items()}


def percentages(levels: Mapping[str, str]) -> dict[str, int]:
    """Return the share of requirements at each level or above, in whole percent; 0 when there are none."""
    ranks = [LEVELS.index(level) for level in levels.values()]
    shares: dict[str, int] = {}
    for rank, name in enumerate(LEVELS[1:], start=1):
        reached = sum(1 for value in ranks if value >= rank)
        shares[name] = round(100 * reached / len(ranks)) if ranks else 0
    return shares


def sarif(findings: Sequence[Finding], levels: Mapping[str, str], commit: str) -> str:
    """Return one SARIF 2.1.0 log; it holds no timestamp, so an unchanged repository gives the same bytes."""
    driver = {
        "name": "earnest",
        "version": __version__,
        "rules": [{"id": rule, "defaultConfiguration": {"level": level}} for rule, level in RULES.items()],
    }
    run = {
        "tool": {"driver": driver},
        "invocations": [{"executionSuccessful": True, "properties": {"commit": commit, "layers": ["trace"]}}],
        "results": [_result(finding) for finding in sorted(findings)],
        "properties": {"traceLevels": dict(levels), "percentages": percentages(levels)},
    }
    log = {"$schema": _SCHEMA, "version": "2.1.0", "runs": [run]}
    return json.dumps(log, indent=2, sort_keys=True) + "\n"


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
    location = {"artifactLocation": {"uri": finding.path}, "region": {"startLine": finding.line}}
    return {
        "ruleId": finding.rule,
        "level": finding.level,
        "message": {"text": finding.text},
        "locations": [{"physicalLocation": location}],
        "properties": {"position": "current"},
    }
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/test_reporter.py -v && make lint`

Expected: `5 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/reporter.py tests/unit/test_reporter.py
git commit -m "feat: report findings as SARIF 2.1.0 with trace levels and a summary"
```

### Task 8: The link rules, `structural.py`

**Files:**

- Create: `packages/earnest/src/earnest/structural.py`
- Test: `packages/earnest/tests/unit/test_structural.py`

**Interfaces:**

- Consumes: `Id`, `Index`, `Item`, `Link` and `NearMiss` from `earnest.index` (Tasks 3 and 4); `Finding` from `earnest.reporter` (Task 7).
- Produces, in `earnest.structural`:
  - `DEFAULT_NEEDS: dict[str, tuple[str, ...]]`, the Default Needs table: `tenet` needs `goal`, `goal` needs `feat`, `feat` needs `req` and `stest`, `req` needs `impl` and `utest`, `dsn` needs `impl`.
  - `needs(item: Item) -> tuple[str, ...]`: the item's `Needs:` types, or its type's default; `()` for a type with none.
  - `check(index: Index) -> list[Finding]`: sorted findings under `earnest/near-miss`, `earnest/duplicate`, `earnest/orphaned`, `earnest/outdated`, `earnest/predated`, `earnest/unwanted` and `earnest/gap`.
  - `traced(index: Index) -> dict[Id, bool]`: each `req`, first definition only, to whether a cover of every type it needs names its current revision.

- [ ] **Step 1: Write the failing tests**

Create `packages/earnest/tests/unit/test_structural.py`:

```python
"""Tests for earnest.structural: the link rules and whether each requirement is traced."""

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
    assert structural.traced(index(IMPL, UTEST)) == {REQ: True}


def test_a_need_with_no_cover_at_any_revision_is_a_gap_at_the_item():
    found = check(IMPL)
    assert located("earnest/gap", found) == [("docs/r.md", 5)]
    assert "`[utest->req~r~2]`" in message("earnest/gap", found)
    assert structural.traced(index(IMPL)) == {REQ: False}


def test_a_cover_of_an_older_revision_is_outdated_not_a_gap():
    old = Link("Covers", "utest", Id("req", "r", 1), "tests/test_a.py", 9)
    found = check(IMPL, old)
    assert [finding.rule for finding in found] == ["earnest/outdated"]
    assert "write `req~r~2`" in message("earnest/outdated", found)
    assert structural.traced(index(IMPL, old)) == {REQ: False}


def test_a_link_to_a_revision_above_the_items_is_predated():
    ahead = Link("Covers", "utest", Id("req", "r", 3), "tests/test_a.py", 9)
    assert located("earnest/predated", check(IMPL, ahead)) == [("tests/test_a.py", 9)]


def test_a_link_to_no_item_is_orphaned_and_names_the_closest_id():
    typo = Link("Covers", "utest", Id("req", "rr", 2), "tests/test_a.py", 9)
    found = check(IMPL, UTEST, typo)
    assert located("earnest/orphaned", found) == [("tests/test_a.py", 9)]
    assert message("earnest/orphaned", found).endswith("did you mean `req~r~2`?")


def test_an_item_that_names_no_parent_is_orphaned():
    found = check(IMPL, UTEST, parent=False)
    assert located("earnest/orphaned", found) == [("docs/r.md", 5)]
    assert "add a `Covers:` line naming the `feat` it derives from" in message("earnest/orphaned", found)


def test_a_cover_by_a_type_the_item_never_needs_is_unwanted_at_warning_level():
    itest = Link("Covers", "itest", REQ, "tests/test_b.py", 4)
    found = check(IMPL, UTEST, itest)
    assert located("earnest/unwanted", found) == [("tests/test_b.py", 4)]
    assert [finding.level for finding in found] == ["warning"]


def test_an_explicit_needs_line_replaces_the_default():
    items = (ITEMS[0], Item(REQ, "docs/r.md", 5, ("impl", "itest")))
    itest = Link("Covers", "itest", REQ, "tests/test_b.py", 4)
    assert located("earnest/unwanted", check(IMPL, UTEST, itest, items=items)) == [("tests/test_a.py", 3)]
    assert structural.traced(index(IMPL, itest, items=items)) == {REQ: True}


def test_a_second_item_with_the_same_id_is_a_duplicate():
    found = check(IMPL, UTEST, items=(*ITEMS, Item(REQ, "docs/other.md", 9)))
    assert located("earnest/duplicate", found) == [("docs/other.md", 9)]
    assert "already defined at docs/r.md:5" in message("earnest/duplicate", found)


def test_a_near_miss_is_a_finding_with_its_canned_fix():
    miss = NearMiss("src/a.py", 8, "[impl-req~r~2]", "write `->` between the artifact type and the id")
    found = check(IMPL, UTEST, misses=(miss,))
    assert message("earnest/near-miss", found) == "`[impl-req~r~2]` does not parse: " + miss.fix


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

Reference resolution matches type and name, then the revision picks `outdated`, `predated` or a resolved link, and `difflib` offers the closest id for an `orphaned` one. A `gap` needs no cover of the type at any revision, so a cover at a stale revision raises only `outdated` or `predated`, while `traced` still counts it as missing. `goal`, `feat` and `req` name their parent on a `Covers:` line and `dsn` on a `Drivers:` line; an item that names none is `orphaned`.

Create `packages/earnest/src/earnest/structural.py`:

```python
"""Structural checks: the link findings the index decides without a model."""

import difflib
from collections.abc import Iterator

from earnest.index import Id, Index, Item, Link
from earnest.reporter import Finding


DEFAULT_NEEDS: dict[str, tuple[str, ...]] = {
    "tenet": ("goal",),
    "goal": ("feat",),
    "feat": ("req", "stest"),
    "req": ("impl", "utest"),
    "dsn": ("impl",),
}
_PARENTS = {
    "goal": ("Covers", "add a `Covers:` line naming the `tenet` it serves"),
    "feat": ("Covers", "add a `Covers:` line naming the `goal` it refines"),
    "req": ("Covers", "add a `Covers:` line naming the `feat` it derives from"),
    "dsn": ("Drivers", "add a `Drivers:` line naming the `req` or `goal` that drives it"),
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
    """Return the link findings, sorted by file, line and rule.

    Near-misses, duplicate ids, links that resolve to no item or to another revision, covers that count toward
    nothing, items that name no parent, and needs that no cover meets.
    """
    defined = index.defined()
    return sorted(
        [
            *_near_misses(index),
            *_duplicates(index, defined),
            *_resolution(index, defined),
            *_parentless(index, defined),
            *_gaps(index, defined),
        ],
    )


def traced(index: Index) -> dict[Id, bool]:
    """Map each requirement to whether every cover it needs exists at its current revision."""
    covers = {(link.type, link.target) for link in index.links if link.key == "Covers"}
    return {
        item.id: all((kind, item.id) in covers for kind in needs(item))
        for item in index.defined().values()
        if item.id.type == "req"
    }


def _near_misses(index: Index) -> Iterator[Finding]:
    for miss in index.near_misses:
        yield Finding(miss.path, miss.line, "earnest/near-miss", f"`{miss.text}` does not parse: {miss.fix}")


def _duplicates(index: Index, defined: dict[tuple[str, str], Item]) -> Iterator[Finding]:
    for item in index.items:
        first = defined[(item.id.type, item.id.name)]
        if item != first:
            message = f"`{item.id}` is already defined at {first.path}:{first.line}: give one of them another name"
            yield Finding(item.path, item.line, "earnest/duplicate", message)


def _resolution(index: Index, defined: dict[tuple[str, str], Item]) -> Iterator[Finding]:
    by_name = {f"{item.id.type}~{item.id.name}": item for item in defined.values()}
    for link in index.links:
        item = defined.get((link.target.type, link.target.name))
        if item is None:
            yield _orphaned(link, by_name)
            continue
        if link.target.revision < item.id.revision:
            message = (
                f"`{link.target}` names revision {link.target.revision}, and the item is at revision"
                f" {item.id.revision}: check the change, then write `{item.id}`"
            )
            yield Finding(link.path, link.line, "earnest/outdated", message)
        elif link.target.revision > item.id.revision:
            message = (
                f"`{link.target}` names revision {link.target.revision}, above the item's revision"
                f" {item.id.revision}: write `{item.id}`, or bump the item if its meaning changed"
            )
            yield Finding(link.path, link.line, "earnest/predated", message)
        if link.key == "Covers" and link.type not in needs(item):
            wanted = ", ".join(f"`{kind}`" for kind in needs(item)) or "no cover"
            message = (
                f"`{link.type}` covers `{item.id}` and counts toward nothing, because the item needs {wanted}:"
                f" use a type it needs, or add `{link.type}` to its `Needs:` line"
            )
            yield Finding(link.path, link.line, "earnest/unwanted", message)


def _orphaned(link: Link, by_name: dict[str, Item]) -> Finding:
    written = f"{link.target.type}~{link.target.name}"
    close = difflib.get_close_matches(written, sorted(by_name), n=1)
    hint = f"did you mean `{by_name[close[0]].id}`?" if close else "define the item, or name one that exists"
    return Finding(link.path, link.line, "earnest/orphaned", f"`{link.target}` names no item: {hint}")


def _parentless(index: Index, defined: dict[tuple[str, str], Item]) -> Iterator[Finding]:
    named = {(link.owner, link.key) for link in index.links if link.owner is not None}
    for item in defined.values():
        parent = _PARENTS.get(item.id.type)
        if parent is not None and (item.id, parent[0]) not in named:
            yield Finding(item.path, item.line, "earnest/orphaned", f"`{item.id}` covers no parent: {parent[1]}")


def _gaps(index: Index, defined: dict[tuple[str, str], Item]) -> Iterator[Finding]:
    """A need no cover meets at any revision is a gap; a cover at another revision is outdated or predated instead."""
    covered = {(link.type, link.target.type, link.target.name) for link in index.links if link.key == "Covers"}
    for item in defined.values():
        for kind in needs(item):
            if (kind, item.id.type, item.id.name) not in covered:
                hint = _COVER_HINTS.get(kind, "add a `{kind}` item with `Covers: {id}`").format(kind=kind, id=item.id)
                message = f"`{item.id}` needs a `{kind}` cover and has none: {hint}"
                yield Finding(item.path, item.line, "earnest/gap", message)
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest tests/unit/test_structural.py -v && make lint`

Expected: `11 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/structural.py tests/unit/test_structural.py
git commit -m "feat: check gaps, unwanted covers, duplicates and reference resolution"
```

### Task 9: `earnest check` end to end, and the exit command green

**Files:**

- Create: `packages/earnest/src/earnest/cli.py`
- Modify: `packages/earnest/pyproject.toml` (`[project.scripts]`, L4)
- Modify: `docs/design/03-implementation-plan.md` (the `done` class on M1 in the milestone DAG)
- Create: `packages/earnest/tests/integration/__init__.py`
- Test: `packages/earnest/tests/unit/test_cli.py`, `packages/earnest/tests/integration/test_check.py`

**Interfaces:**

- Consumes: `git.repo_root`, `git.head_commit`, `git.tracked_files` and `git.GitError` (Task 2); `build_index` (Tasks 3 and 4); `adapters.scan` (Task 6); `reporter.trace_levels`, `reporter.sarif`, `reporter.summary` and `Finding.level` (Task 7); `structural.check` and `structural.traced` (Task 8); the `files_repo` fixture (Task 2); the feature and its step module (Task 1).
- Produces: `earnest.cli.main(argv: Sequence[str] | None = None) -> int`, which returns 0 when no error-level finding is in scope, 1 when one is, and 2 when Git cannot answer; argparse exits 2 on a usage error. The console script `earnest`, from `[project.scripts] earnest = "earnest.cli:main"`.

- [ ] **Step 1: Write the failing tests**

```bash
mkdir -p tests/integration
touch tests/integration/__init__.py
```

Create `packages/earnest/tests/unit/test_cli.py`:

```python
"""Tests for earnest.cli: the command surface and its exit codes."""

import pytest

from earnest import cli


def test_a_command_is_required(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])
    assert exit_info.value.code == 2
    assert "check" in capsys.readouterr().err


def test_a_check_outside_a_work_tree_exits_2_with_one_line_on_stderr(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["check"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("earnest: ")
    assert "not a git repository" in err
    assert len(err.splitlines()) == 1
```

Create `packages/earnest/tests/integration/test_check.py`:

```python
"""Integration: `earnest check` over a committed repository, from the scan to the exit code."""

import json

from earnest import cli


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
    return code, json.loads(out)["runs"][0], err


def test_a_complete_chain_passes_with_every_requirement_traced(files_repo, monkeypatch, capsys):
    code, run, err = check(files_repo(CHAIN), monkeypatch, capsys)
    assert (code, run["results"]) == (0, [])
    assert run["properties"]["traceLevels"] == {"req~r~1": "traced"}
    assert err.startswith("traced 100%, judged 0%, evidenced 0%; requirements: 1\n")


def test_a_check_from_a_subdirectory_reads_the_whole_repository(files_repo, monkeypatch, capsys):
    repo = files_repo({**CHAIN, "docs/more notes.md": "# More\n\n`req~x~1`\n\nCovers: feat~f~1\n"})
    code, run, _ = check(repo / "src", monkeypatch, capsys)
    assert code == 1
    found = {(r["ruleId"], r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]) for r in run["results"]}
    assert found == {("earnest/gap", "docs/more notes.md")}
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/unit/test_cli.py tests/integration -v`

Expected: FAIL at collection with `ImportError: cannot import name 'cli' from 'earnest'` in both modules.

- [ ] **Step 3: Write `cli.py` and declare the `earnest` script**

`cli.py` wires the pipeline and keeps no logic of its own. With `GitError` caught, a check outside a work tree prints one line and exits 2.

Create `packages/earnest/src/earnest/cli.py`:

```python
"""Command surface: `earnest check`, which wires the scanner, the index, the checks and the reporter."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from earnest import adapters, git, reporter, structural
from earnest.index import build_index


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return its exit code.

    0 when no error-level finding is in scope, 1 when one is, and 2 when the check cannot run.
    """
    parser = argparse.ArgumentParser(prog="earnest", description="Requirements traceability for LLM-written code.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="trace the repository; SARIF 2.1.0 on stdout, a summary on stderr")
    parser.parse_args(argv)
    try:
        root = git.repo_root(Path.cwd())
        commit = git.head_commit(root)
        sources = adapters.scan(root, git.tracked_files(root))
    except git.GitError as error:
        sys.stderr.write(f"earnest: {error}\n")
        return 2
    index = build_index(sources)
    findings = structural.check(index)
    levels = reporter.trace_levels(structural.traced(index))
    sys.stdout.write(reporter.sarif(findings, levels, commit))
    sys.stderr.write(reporter.summary(findings, levels))
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

Expected: `4 passed`.

- [ ] **Step 5: Run the exit command and watch it pass**

Run: `uv run pytest tests/steps/test_trace_check.py`

Expected: PASS, `5 passed`. It is the first green run of the exit command since Task 1.

- [ ] **Step 6: Run the whole suite and the linters**

Run: `make test && make lint`

Expected: `69 passed` across the three tiers, then `make lint` exits 0.

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
