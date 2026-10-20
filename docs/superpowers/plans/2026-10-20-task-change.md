# M3 `task_change` Implementation Plan

Status: draft for plan approval. It rests on the maintainer's resolutions 1–4 and decisions (a)–(d), (i) and (ii), and on the Lead's decisions E1–E5. These are recorded in `docs/design/01-logic-design.md` (Out-of-task rule, Impact rule, D11, D12, SARIF 2.1.0, Runtime and permission model), `docs/design/02-structural-design.md` (`git.py`, `impact.py`, `fixtures/seeded-change/`) and `docs/design/04-bdd-test-plan.md` (the M2 Notes and the M3 section). The maintainer's amendment confirms E4 as an exact-name match (`task/add-limiter` resolves to `add-limiter`) and re-derives E1 so that exit 2 resolves the finding.

**Superseded in part.** The maintainer later ruled that no check runs against Git branches. Resolutions 1 and 3 and E4 are withdrawn, and resolution 4 is rewritten; see [Rework: no Git branch read](#rework-no-git-branch-read) at the end, which governs where it differs from the sections above. Tasks 1 to 8 are done as of `0775233`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `earnest check` runs on a `task/…` branch or with `--task`, it:

- reports each changed region outside the current task, prose and code alike, as `earnest/out-of-task` with the three exits;
- prints an impact section of the requirements, features and tests to run, carried as `properties.impact`;
- raises `earnest/impact-degraded` for each changed line that has no coverage data.

`earnest check --stage` takes the coverage map. M2's three amended tables and the exit command `uv run pytest tests/steps/test_task_change.py` turn green at Task 7.

**Architecture:**

- `git.py` gains four reads:
  - the current branch;
  - the default branch (`refs/remotes/origin/HEAD`'s, else `main`);
  - the merge-base;
  - the changed lines from a commit to the work tree, untracked files included, as `-U0` hunks that pair old lines with new.
- `plan.py` owns the Out-of-task rule.
  - It resolves the current task: `--task`, else the longest task name in the plan that the rest of the branch name equals, or begins with followed by `-`.
  - It keeps the changed lines of files in the evaluated tree only.
  - It forms regions: each tag region of `index.py` that holds a changed line, and each hunk of changed lines outside every tag region, prose included.
  - It raises `out-of-task` at a region's first changed line, unless an `outdated` finding lies on one of the region's lines. The finding goes against the task's stage, at position current.
  - It also places `impact-degraded` by M2's rule: a line in a stage artifact counts against that stage, and any other line reaches no stage.
- `impact.py` owns the Impact rule.
  - At `check --stage` it runs the repository's tests under pytest-cov with `--cov-context=test`, writing the data file to `.earnest/coverage/<commit>`. It reads the per-test contexts through `coverage json --show-contexts`.
  - On a later check it pairs each modified line with its base line in the map.
  - A tag-region line that the map never saw falls back to the tests tagged, on type and name, to that region's requirements.
  - A line in no tag region, blank lines included, selects the full suite and raises one `impact-degraded` note per line.
  - Requirements are named at their current revision.
- `reporter.py` renders the out-of-task lines, the impact section and `properties.impact`, and stores the map's commit in the record's `coverage`.
- `cli.py` wires `--task`. It runs the out-of-task check when a current task exists, and impact on a `task/…` branch or with `--task` (resolution 4).

**Tech Stack:** Python 3.12 standard library at runtime (`subprocess`, `json`, `re`, `pathlib`, `dataclasses`). pytest-cov and coverage run as subprocesses over the repository under check, through the interpreter that runs Earnest. There is no new runtime dependency (L4); `pytest-cov` is already a dev dependency.

**Spec:**

- `docs/design/03-implementation-plan.md`, milestone M3.
- `01`: the Out-of-task rule, Impact rule, Region rule, D11 and D12.
- `02`: `git.py`, `index.py`, `plan.py`, `impact.py` and `fixtures/seeded-change/`.
- `04`: the M2 Notes (the ratified rows of M2) and the M3 section.

## Global Constraints

- **Layout and lint:**
  - Paths follow the File and directory tree of `02`.
  - The runtime is the standard library alone (L4).
  - The lint bar is M2's: ruff (line length 120, complexity 10, five arguments, Google docstrings), `ruff format`, `mypy --strict`, and vulture at 80.
- **Resolution 4, as revised by (a):** without a current task named by `--task`, or a `task/…` branch, there is no `out-of-task`, no impact section, no `properties.impact` and no `impact-degraded`. M1 and M2b gain no row. M2 gains exactly the rows that `04` ratifies in three scenarios, and nothing else in M2 changes.
- **Resolution 1 and (c):**
  - The base commit is `git merge-base HEAD <default>`.
  - `<default>` is the branch `refs/remotes/origin/HEAD` names, else `main`.
  - The diff runs from the base commit to the work tree, untracked files included.
  - The diff is read only in the evaluated tree (decision i).
- **Resolution 3 and E4:**
  - A branch `task/<rest>` resolves to the longest task name `n` in the plan such that `<rest>` equals `n` or begins with `n-`.
  - `task/add-limiter` and `task/add-limiter-window` both resolve to `add-limiter` (E4, confirmed).
  - No match gives no current task; `task/add-limiterx` and `task/unknown-x` are such branches.
- **Resolution 2 and (d):**
  - Only `check --stage` takes the map.
  - Its data file is `.earnest/coverage/<HEAD sha>`.
  - The record's `coverage` is `{"commit": "<sha>"}`, keeping M2's object shape.
  - Earnest's own options to the map run write nothing outside `.earnest/`: it uses `-p no:cacheprovider`, `-o addopts=`, `-o log_file=`, `PYTHONDONTWRITEBYTECODE=1`, and a `COVERAGE_FILE` under `.earnest/`; the repository's tests run under the test-suite trust model.
  - A dirty tree, a timeout (900 s), pytest exit codes 2 to 5, or no coverage data give no map; the summary names the cause.
  - A failing test still gives a map.
  - The run header's `layers` stays `trace`.
- **(a), R1h′ and (ii):**
  - Prose stays in scope.
  - A changed hunk outside every tag region is a region.
  - `impact-degraded` is one note per such line, blank lines included.
  - It counts against the stage whose artifact holds the line, else reaches no stage.
- **(b):** the `task/` overlay is committed on top of `change/` on `task/add-limiter-window`.
- **E1, re-derived:** exits 1 and 2 clear the finding, and exit 3 leaves it standing.
  - A changed region is not out-of-task when the diff adds a task item (its id line is a changed line) whose `Delivers:` names one of the region's tags on type and name.
  - The hunk that adds such a task item is the proposal itself and raises no `out-of-task`.
  - The Impact rule is unchanged, so the added plan lines still raise `impact-degraded` per line.
- **E5:** `properties.impact` is `{requirements, features, tests, degraded}`, with ids and node ids sorted.
- **Full suite:** it is every test the map holds a context for. With no map, `tests` is `[]` and `degraded` is `true` (a Lead decision).
- **Writes:** `plan` stays read-only, and plain `check` writes nothing.
- **Exit codes** are unchanged: `out-of-task` is a warning and `impact-degraded` is a note.
- **Process:**
  - No agent `rm`s a path it did not create.
  - `.pi-herdsman/` stays untracked.
  - Each commit stages its task's paths by name, with no `--no-verify`.

## Review Focus

- **M2's three amended tables** ("After a revision bump …", "The stage that awaits its fresh approval …", "After a fresh approval the findings left …"):
  - Line 3's hunk is suppressed only while the stale-approval `outdated` note lies on it.
  - `out-of-task` stays out of a `--stage` run of another stage.
  - The appended audit row of the gate step raises nothing.
- **The map run** in the fixture leaves `git status` empty, with no `.pytest_cache`, `__pycache__` or `.coverage`. M2's "Git lists no new file" therefore stays green.
- **Hunks and pairing:**
  - A modified line is seen through the base line its hunk pairs it with.
  - An added line beyond the pairing is unseen.
  - Several hunks in one file give one region each.
- **Branches:**
  - several candidate prefixes;
  - `--task` winning over the branch;
  - a detached HEAD (no current task without `--task`);
  - a `task/` branch that names no task (impact runs, out-of-task does not).
- **A repository without pytest or tests:** the map run gives no map, never exit 2, and the summary names the cause, so every changed line falls back to the tagged tests.

## Task order and the scenarios each turns green

Scenario names are those of `04`: M3's "Task change feature" and the M2 "Stage status feature".

| Task | Content | Depends on | Scenarios green after it |
| --- | --- | --- | --- |
| 0 | This plan, committed with the docs (done by the docs commit) | none | none |
| 1 | The `task_change` behavior gate, red: fixture, `task/` overlay, feature, steps | none | M3: "Off a task branch, with no task named, the check reports nothing of the task change" (a guard, green from here on) |
| 2 | M2's three amended tables, red: `stage_status.feature` | T1 | none; the three amended M2 scenarios turn red |
| 3 | Branch, default branch, merge-base and changed lines, `git.py` | T1 | none (unit tier) |
| 4 | Out-of-task and impact rendering, `reporter.py` | T1 | none (unit tier) |
| 5 | The current task, regions and the Out-of-task rule, `plan.py`; `--task` in `cli.py` | T3, T4 | M3: "An out-of-task finding names the task and offers exactly three exits" |
| 6 | The coverage map at `check --stage`, `impact.py`, `cli.py` | T4 | M3: "The stage check takes the coverage map and leaves Git's listing as it was" |
| 7 | Impact selection, `impact-degraded` and its placement, `impact.py`, `plan.py`, `cli.py`; both gates turn green | T2, T5, T6 | the other ten M3 scenarios (see the table below), and M2's three amended scenarios |
| 8 | The full suite, lint and the pre-PR review | T7 | all 13 of M3 (14 tests, the outline giving two) and all 26 of M2, with M1 and M2b unchanged |

The ten M3 scenarios that turn green at Task 7:

| M3 scenario |
| --- |
| "Each changed region outside the task is flagged, prose and code alike" |
| "Tagging the region under a requirement the task delivers clears its finding" |
| "Proposing a task that delivers the region's requirement clears its finding" |
| "Declaring the change blocked leaves the repository and the finding as they were" |
| "A task name with hyphens resolves to the longest task name the branch names" (an outline: `task/add-limiter-window` and `task/add-limiter`) |
| "The task named on the command line wins over the branch" |
| "Off a task branch the named task diffs from the default branch, uncommitted work included" |
| "The impact section names the requirements, features and tests to run, from the coverage map" |
| "A changed line with no coverage data selects the full suite and says so" |
| "Without a coverage map a changed line selects the tests tagged to its requirement" |

M2's three amended scenarios, which turn green again at Task 7:

| M2 scenario |
| --- |
| "After a revision bump every place left at the old revision is flagged" |
| "The stage that awaits its fresh approval passes its own check" |
| "After a fresh approval the findings left at the old revision are in scope at the next stage" |

**Regression expectations:**

- **Tasks 1 to 7:** the regression run is `uv run pytest --ignore=tests/steps/test_task_change.py --ignore=tests/steps/test_stage_status.py` in `packages/earnest/`.
- **From Task 2 to Task 6:** `uv run pytest tests/steps/test_stage_status.py` reports exactly 23 passed and the 3 amended scenarios failed.
- **From Task 7:** it reports 26 passed.
- **Task 1:** `tests/steps/test_trace_check.py` and `tests/steps/test_unit_status.py` stay green, and so does the whole of `test_stage_status.py`, despite the E3 base edits.
- **Every task** records its exact count against the baseline at the plan's base commit.

## File Structure

| Path under `packages/earnest/` | Responsibility | Task |
| --- | --- | --- |
| `tests/fixtures/seeded-change/pytest.ini` | `pythonpath = src` for the map run | 1 |
| `tests/fixtures/seeded-change/tests/test_auth.py` | lines 2, 6, 11 and 16 call the code (E3); the tag lines stay at 4, 9 and 14 | 1 |
| `tests/fixtures/seeded-change/task/src/checkout/auth.py` | the `task/` overlay: lines 2, 6 and 11 changed | 1 |
| `tests/features/task_change.feature` | M3's 13 scenarios (14 tests), verbatim from `04` | 1 |
| `tests/steps/test_task_change.py` | pytest-bdd steps; the exit command | 1, 7 |
| `tests/conftest.py` | the base builder leaves `task/` out; `-` in a `stage` column means no `properties.stage`; the stacked task-change committer | 1 |
| `tests/integration/test_seeded_change.py` | the M3 seeds and the `task/` overlay pinned to the lines `04` names | 1 |
| `tests/features/stage_status.feature` | the three amended tables, byte for byte as in `04`; nothing else changes | 2 |
| `src/earnest/git.py` | `current_branch`, `default_branch`, `merge_base`, `changed_lines(root, base)` | 3 |
| `src/earnest/reporter.py` | `earnest/out-of-task` and `earnest/impact-degraded` in `RULES`; the summary's out-of-task and impact lines; `properties.impact`; `coverage` written | 4, 6 |
| `src/earnest/index.py` | a region lookup by file and line over the existing Region rule, with no change to the rule | 5 |
| `src/earnest/plan.py` | `current_task`, `changed_regions`, `out_of_task`, the placement of `impact-degraded` | 5, 7 |
| `src/earnest/impact.py` | `take_map`, `read_map`, `select` (new module) | 6, 7 |
| `src/earnest/cli.py` | `--task`; the M3 checks gated by resolution 4; the map at `--stage` | 5, 6, 7 |
| `tests/unit/test_git.py`, `test_reporter.py`, `test_plan.py`, `test_impact.py`, `test_cli.py`; `tests/integration/test_task_change.py` | each task's tests | 3-7 |

Outside the package nothing changes. The docs commit that adds this plan also adds its link to M3's entry in `docs/design/03-implementation-plan.md`; marking M3 done there is outside this plan's scope.

## Known limits

- Impact for TypeScript (Jest `--findRelatedTests`) is not built. M3 reads pytest-cov alone, so a changed `.ts` line takes the fallback.
- A deletion-only change raises no `out-of-task`.
- With no map, the full suite is written as `tests: []` with `degraded: true` in `properties.impact`, and the summary says `tests: the full suite`.
- Every changed prose line on a task branch is `impact-degraded`, blank lines included. That is the literal reading the maintainer chose (R1h′, ii), and it makes a spec edit always select the full suite.

---

## Tasks

### Task 1: The `task_change` behavior gate, red

**Files:**

- Create: `packages/earnest/tests/fixtures/seeded-change/pytest.ini`
- Modify: `packages/earnest/tests/fixtures/seeded-change/tests/test_auth.py` (lines 2, 6, 11 and 16 only)
- Create: `packages/earnest/tests/fixtures/seeded-change/task/src/checkout/auth.py`
- Create: `packages/earnest/tests/features/task_change.feature`
- Create: `packages/earnest/tests/steps/test_task_change.py`
- Modify: `packages/earnest/tests/conftest.py`, `packages/earnest/tests/integration/test_seeded_change.py`

- [ ] **Step 1:** Write the fixture files exactly as the M3 tables of `04` give them. Check that the tag lines stay at 4, 9 and 14.
- [ ] **Step 2:** Leave `task/` out of the base builder, as `change/` and `units/` already are. Add the step that commits `change/` and then `task/` on `task/add-limiter-window`. Add the steps that write both overlays uncommitted on `main` and that commit both on `feature/limiter`.
- [ ] **Step 3:** Copy the M3 Gherkin of `04` into `task_change.feature` verbatim.
- [ ] **Step 4:** Write the step module.
  - The Givens edit the work tree as the M3 Notes of `04` say.
  - The Thens read the SARIF log, the summary, `properties.impact`, `properties.plan`, the record and `git status`.
- [ ] **Step 5:** Extend the shared findings-table step so that a `-` in the `stage` column means the result has no `properties.stage`.
- [ ] **Step 6:** Pin the seeds and the overlay in `test_seeded_change.py`.
- [ ] **Step 7:** Run the gates.
  - Run `uv run pytest tests/steps/test_task_change.py`. Expected: 13 of the 14 tests fail, and the off-branch guard passes.
  - Run `uv run pytest tests/steps/test_trace_check.py tests/steps/test_stage_status.py tests/steps/test_unit_status.py`. Expected: all green.
- [ ] **Step 8:** Commit `test: RED task_change behavior gate and seeded-change M3 cases`.

### Task 2: M2's three amended tables, red

**Files:** Modify `packages/earnest/tests/features/stage_status.feature`.

- [ ] **Step 1:** Replace the findings tables of the three amended M2 scenarios with those of `04`, byte for byte. These are the 5, 2 and 4 new rows the M2 Notes list. The other 23 scenarios stay byte-identical to `04`.
- [ ] **Step 2:** Check that no step changes in `tests/steps/test_stage_status.py`. The new rows use only the columns `rule`, `file`, `line`, `level`, `position` and `stage`, with a stage on every row. `the finding at requirements.md line 3 names …` already accepts any one of the findings at that place.
- [ ] **Step 3:** Run `uv run pytest tests/steps/test_stage_status.py`. Expected: 23 passed and the 3 amended scenarios failed.
- [ ] **Step 4:** Commit `test: RED M2 tables gain the M3 rows on the task branch`.

### Task 3: Branch, default branch, merge-base and changed lines, `git.py`

**Files:** Modify `packages/earnest/src/earnest/git.py`; Test `packages/earnest/tests/unit/test_git.py`.

- [ ] **Step 1:** Write failing tests:
  - `current_branch` is `None` on a detached HEAD.
  - `default_branch` follows `origin/HEAD` and falls back to `main`.
  - `merge_base`.
  - `changed_lines` covers modified, added and deleted lines, blank added lines, several hunks in one file, an untracked file, a file name with spaces or glob characters, and CRLF.
- [ ] **Step 2:** Implement with `--literal-pathspecs`, `--no-optional-locks` and `git diff --no-renames -U0 <base>` against the work tree, plus `git ls-files --others --exclude-standard`. No path under `.earnest/` is listed.
- [ ] **Step 3:** The tests pass and `make lint` is clean. Commit `feat: git reads for the task base and changed lines`.

### Task 4: Out-of-task and impact rendering, `reporter.py`

**Files:** Modify `packages/earnest/src/earnest/reporter.py`; Test `packages/earnest/tests/unit/test_reporter.py`.

- [ ] **Step 1:** Write failing tests:
  - the two rule ids and their levels (warning, note);
  - the out-of-task message naming the task, the region's tags or "no tag", and the three exits in order;
  - the `impact-degraded` message ("selected the full suite");
  - `properties.impact`, present only when given;
  - the summary's impact lines (`features: none` when empty, and `tests: the full suite` when degraded with no map);
  - `coverage` stored as `{"commit": sha}`.
- [ ] **Step 2:** Implement. `reporter.py` still imports neither `plan` nor `impact`.
- [ ] **Step 3:** Tests pass and lint is clean. Commit.

### Task 5: The current task, regions and the Out-of-task rule, `plan.py`; `--task` in `cli.py`

**Files:** Modify `packages/earnest/src/earnest/plan.py`, `index.py`, `cli.py`; Test `tests/unit/test_plan.py`, `tests/unit/test_cli.py`.

- [ ] **Step 1:** Write failing tests:
  - **`current_task`:**
    - `--task` wins over the branch;
    - the longest-name rule (`add` and `add-limiter` against `task/add-limiter-window`);
    - the exact-name case (`task/add-limiter` gives `add-limiter`);
    - `task/add-limiterx` and `task/unknown-x` give `None`.
  - **`changed_regions`:**
    - only files in the evaluated tree, so an audit shard or the state file gives none;
    - tag regions;
    - one region per hunk outside every tag region, Markdown prose included.
  - **`out_of_task`:**
    - type-and-name matching that ignores revision;
    - the location at the first changed line;
    - suppression when an `outdated` finding lies on a region's line, the stale-approval note included;
    - exit 2: a region whose tags a task item added in the diff delivers raises none, and the hunk that adds the task item raises none, while a declared block changes nothing;
    - the stage is the task's stage, at position current.
- [ ] **Step 2:** Implement. `cli.py` adds `--task <id>` and calls `out_of_task` only under resolution 4. A `--stage` run of another stage leaves `out-of-task` out of its assessment.
- [ ] **Step 3:** The scenario "An out-of-task finding names the task and offers exactly three exits" passes. Commit.

### Task 6: The coverage map at `check --stage`, `impact.py`

**Files:** Create `packages/earnest/src/earnest/impact.py`; Modify `cli.py`, `reporter.py`; Test `tests/unit/test_impact.py`, `tests/integration/test_task_change.py`.

- [ ] **Step 1:** Write failing tests:
  - `take_map` writes `.earnest/coverage/<sha>` and nothing else, so `git status` stays empty;
  - a failing test still gives a map;
  - a repository without pytest or tests gives no map, a named cause and no exit 2;
  - `read_map` maps `(path, line)` to sorted node ids, dropping the `|run` suffix.
- [ ] **Step 2:** Implement in two runs, each with `COVERAGE_FILE=.earnest/coverage/<sha>`:
  - `sys.executable -m pytest --cov=. --cov-context=test -p no:cacheprovider -q`;
  - then `sys.executable -m coverage json --show-contexts -o .earnest/coverage/<sha>.json`.
- [ ] **Step 3:** `cli.py` takes the map after the record write at `--stage`, and the record's `coverage` is the commit. The scenario "The stage check takes the coverage map and leaves Git's listing as it was" passes. M2's and M2b's `--stage` scenarios stay as before: green, apart from the three amended scenarios still red from Task 2. Commit.

### Task 7: Impact selection and `impact-degraded`; both gates turn green

**Files:** Modify `packages/earnest/src/earnest/impact.py`, `plan.py`, `cli.py`; Test `tests/unit/test_impact.py`, `tests/unit/test_plan.py`, `tests/unit/test_cli.py`.

- [ ] **Step 1:** Write failing tests for `select` and for the placement:
  - A modified line goes through its paired base line in the map.
  - An added or unseen line in a tag region takes the tests tagged, on type and name, to that region's requirements.
  - A line in no tag region, blank lines included, gives the full suite (every test in the map) and one `impact-degraded` per line.
  - Placement: the stage whose artifact holds the line, at that stage's position; a code or test line reaches no stage.
  - Requirements come from the changed tag regions, at their current revision. Features come from their `Covers:` (none on `bugfix`).
  - With no map there is only the fallback, and the summary says no map exists for the base commit.
- [ ] **Step 2:** Implement, and wire into `cli.py` under resolution 4.
- [ ] **Step 3:** Run the gates:
  - `uv run pytest tests/steps/test_task_change.py`: 14 passed.
  - `uv run pytest tests/steps/test_stage_status.py`: 26 passed.
  - The regression run is green, with M1 and M2b unchanged.
- [ ] **Step 4:** Commit.

### Task 8: The full suite, lint and the pre-PR review

**Files:** none; this task only runs the checks.

- [ ] **Step 1:** From the repository root, run `rtk proxy make test; echo $?` and `rtk proxy make lint; echo $?`. Expected: both print `0`.
- [ ] **Step 2:** In `packages/earnest/`, run `rtk proxy uv run pytest tests/steps/test_task_change.py tests/steps/test_stage_status.py; echo $?`. Expected: `0`.
- [ ] **Step 3:** Run the `/pre-pr-review` skill on HEAD and record its verdict. Nothing is committed in this task.

## Scope paths

```json
[
  "packages/earnest/src/earnest/git.py",
  "packages/earnest/src/earnest/index.py",
  "packages/earnest/src/earnest/plan.py",
  "packages/earnest/src/earnest/impact.py",
  "packages/earnest/src/earnest/reporter.py",
  "packages/earnest/src/earnest/cli.py",
  "packages/earnest/tests/conftest.py",
  "packages/earnest/tests/sarif.py",
  "packages/earnest/tests/features/task_change.feature",
  "packages/earnest/tests/features/stage_status.feature",
  "packages/earnest/tests/steps/test_task_change.py",
  "packages/earnest/tests/unit/test_git.py",
  "packages/earnest/tests/unit/test_reporter.py",
  "packages/earnest/tests/unit/test_plan.py",
  "packages/earnest/tests/unit/test_impact.py",
  "packages/earnest/tests/unit/test_cli.py",
  "packages/earnest/tests/integration/test_seeded_change.py",
  "packages/earnest/tests/integration/test_task_change.py",
  "packages/earnest/tests/fixtures/seeded-change/pytest.ini",
  "packages/earnest/tests/fixtures/seeded-change/tests/test_auth.py",
  "packages/earnest/tests/fixtures/seeded-change/task/src/checkout/auth.py"
]
```

---

## Rework: no Git branch read

The maintainer ruled that "we should not do any checks against git branches". `01` (the Out-of-task rule, the Impact rule, D11 and D12), `02` (`git.py`, `plan.py`, `conftest.py`, `fixtures/seeded-change/`) and `04` (the M2 Notes and the M3 section) now record:

- **The change baseline** replaces the task base commit. It is the `commit` of the run header of the stage whose approval row's `Assessment Hash` equals that header's `hash`, current or outdated, the latest such row in audit order, within the current task's intent. No such stage, or a commit Git no longer holds, gives no baseline. Both the out-of-task check and impact diff from it to the work tree, and impact reads `.earnest/coverage/<baseline>` alone.
- **The current task** is `--task`, else the one `- **Current Task**: <task id>` line in the `## Project Information` section of an intent's `aidlc-state.md`, naming a task of that intent. No such line, several lines, or a value that names no task gives no current task.
- **Resolution 4, rewritten:** the out-of-task check and impact both run only with a current task and a baseline. Otherwise there is no M3 finding, no impact section and no `properties.impact`, only one summary line naming what is missing.
- **Withdrawn:** resolutions 1 and 3 and E4: the merge-base, the `origin/HEAD` fallback and the `task/<name>` resolution. Earnest reads no branch, branch name, merge-base or `origin/HEAD`; the fixture's branches are step mechanics.
- **Unchanged:** decisions (a), (b), (d), (i), (ii), E1, E2, E3, E5, the hash exclusion, the deletion rules, tag-only regions and per-line `impact-degraded`.

### Rework constraints

- `git.py`'s `current_branch`, `default_branch` and `merge_base` are used only by `cli.py`'s task change, so they and their unit tests go. `git.py` gains a check that a commit exists.
- M2's `stage_status.feature` returns to its tables on `main`, byte for byte; its 11 M3 rows go. M1 and M2b stay unchanged.
- The state-file line is outside the evaluated tree, so writing it makes no tree dirty and enters no diff or hash.

### Rework task order and the scenarios each turns green

Scenario names are those of `04`'s "Task change feature" (14 scenarios; the outline's two examples make 15 test cases) and the M2 "Stage status feature".

| Task | Content | Depends on | Scenarios green after it |
| --- | --- | --- | --- |
| R1 | The behavior gates, red: `task_change.feature` and `stage_status.feature` from `04`, verbatim, and the new steps | none | M3: "The stage check takes the coverage map and leaves Git's listing as it was" |
| R2 | The current task from the state file; `--task` wins; drop the branch resolution | R1 | M2's three scenarios that `0775233` amended, back on `main`'s tables; M3: "With no single current task the check reports nothing of the task change" (both examples) |
| R3 | The change baseline from the record and the audit; impact on the baseline's map; drop the branch, default-branch and merge-base reads | R2 | the other 12 M3 test cases |
| R4 | The full suite, lint and the pre-PR review | R3 | all 15 M3 test cases and all 26 of M2, with M1 and M2b unchanged |

The 12 M3 test cases that turn green at R3:

| M3 scenario |
| --- |
| "Each changed region since the approved stage check that lies outside the task is flagged, prose and code alike" |
| "An out-of-task finding names the task and offers exactly three exits" |
| "Tagging the region under a requirement the task delivers clears its finding" |
| "Proposing a task that delivers the region's requirement clears its finding" |
| "Declaring the change blocked leaves the repository and the finding as they were" |
| "The state file's current task is the task the check reads" |
| "The task named on the command line wins over the state file" |
| "With no approved stage check recorded the check reports nothing of the task change" |
| "An uncommitted change is diffed against the commit the approved stage check recorded" |
| "The impact section names the requirements, features and tests to run, from the coverage map" |
| "A changed line with no coverage data selects the full suite and says so", and "Without a coverage map a changed line selects the tests tagged to its requirement" |

**Regression expectations:**

- **R1 to R3:** the regression run is `uv run pytest --ignore=tests/steps/test_task_change.py --ignore=tests/steps/test_stage_status.py` in `packages/earnest/`, green, with each task's exact count recorded against `0775233`.
- **R1:** `uv run pytest tests/steps/test_stage_status.py` reports 23 passed and the 3 restored scenarios failed.
- **From R2:** that run reports 26 passed.

### Task R1: The behavior gates, red

**Files:**

- Modify: `packages/earnest/tests/features/task_change.feature`, `packages/earnest/tests/features/stage_status.feature`
- Modify: `packages/earnest/tests/steps/test_task_change.py`, `packages/earnest/tests/conftest.py`

- [ ] **Step 1:** Copy the M3 Gherkin of `04` into `task_change.feature` verbatim. Restore `stage_status.feature` to `main`'s bytes: `git diff main -- packages/earnest/tests/features/stage_status.feature` is empty.
- [ ] **Step 2:** Write the steps the M3 Notes of `04` name:
  - "the coding agent's state file names `<id>` as the current task", "names no task" and "names both …", writing the `Current Task` lines uncommitted;
  - "the coding agent's task change is committed", replacing the step that named the task branch; it may still commit on `task/add-limiter-window`, and no assertion reads the branch name;
  - "the coverage maps under `.earnest/coverage/` are gone", deleting only the files the scenario's own stage check wrote;
  - "the summary states once that there is no current task", and "… that no approved stage check is recorded".
  
  Drop the steps of the removed scenarios: the hyphenated branch outline, the `feature/limiter` branch, and adding `task~add~1` on `main`. Reuse the shared approval step of M2.
- [ ] **Step 3:** Run `uv run pytest tests/steps/test_task_change.py tests/steps/test_stage_status.py`. Expected: the map scenario passes, the M3 scenarios that need a marker or a baseline fail, and M2 has 23 passed and 3 failed. Commit `test: RED task_change gate without branches, M2 tables back to main`.

### Task R2: The current task from the state file, `plan.py`

**Files:** Modify `packages/earnest/src/earnest/plan.py`, `packages/earnest/src/earnest/cli.py`, `packages/earnest/src/earnest/reporter.py`; Test `tests/unit/test_plan.py`, `tests/unit/test_cli.py`, `tests/unit/test_reporter.py`.

- [ ] **Step 1:** Write failing tests for `current_task`:
  - `--task` wins over the line;
  - one `- **Current Task**:` line under `## Project Information` names the task, on type and name, revision ignored;
  - no line, two lines in one intent, lines in two intents, a line outside that section, or a value naming no task of its intent each give `None` and a reason;
  - the summary line, which is no SARIF result.
- [ ] **Step 2:** Implement. Delete the branch-name resolution and its tests. In `cli.py`, the task change runs only with a current task.
- [ ] **Step 3:** M2's 26 scenarios and the outline's two examples pass. Commit `feat: the current task from the state file, no branch name read`.

### Task R3: The change baseline from the record, `plan.py`, `git.py`, `cli.py`

**Files:** Modify `packages/earnest/src/earnest/plan.py`, `packages/earnest/src/earnest/git.py`, `packages/earnest/src/earnest/cli.py`, `packages/earnest/src/earnest/impact.py`; Test `tests/unit/test_plan.py`, `tests/unit/test_git.py`, `tests/unit/test_cli.py`, `tests/integration/test_task_change.py`.

- [ ] **Step 1:** Write failing tests for `change_baseline`, covering every case the M3 Notes of `04` give to the unit and integration tiers:
  - the header whose hash the approval row carries;
  - the latest such row in audit order, across stages;
  - an outdated approval still counting;
  - a later stage check that replaces the header ending that stage's claim;
  - a row without `Assessment Hash`, and the seeded placeholder hash, giving none;
  - a per-unit stage;
  - a dirty header's commit read as is;
  - a commit Git no longer holds giving none, through the new `git` commit check.
- [ ] **Step 2:** Implement:
  - `cli.py` diffs from the baseline, and impact reads `.earnest/coverage/<baseline>`.
  - Delete `current_branch`, `default_branch` and `merge_base`, with their tests. The "no base commit" note becomes "no approved stage check is recorded".
  - Run `grep -rn "merge-base\|origin/HEAD\|symbolic-ref\|rev-parse --abbrev-ref" packages/earnest/src`. Expected: no hit.
- [ ] **Step 3:** All 15 M3 test cases pass, and the regression run is green. Commit `feat: the change baseline is the last approved stage check, no branch read`.

### Task R4: The full suite, lint and the pre-PR review

**Files:** none; this task only runs the checks.

- [ ] **Step 1:** From the repository root, run `rtk proxy make; echo $?`. Expected: `0`.
- [ ] **Step 2:** Run `git diff main -- packages/earnest/tests/features/trace_check.feature packages/earnest/tests/features/stage_status.feature packages/earnest/tests/features/unit_status.feature`. Expected: empty.
- [ ] **Step 3:** Run the `/pre-pr-review` skill on HEAD and record its verdict.

### Rework scope paths

```json
[
  "packages/earnest/src/earnest/git.py",
  "packages/earnest/src/earnest/plan.py",
  "packages/earnest/src/earnest/impact.py",
  "packages/earnest/src/earnest/reporter.py",
  "packages/earnest/src/earnest/cli.py",
  "packages/earnest/tests/conftest.py",
  "packages/earnest/tests/features/task_change.feature",
  "packages/earnest/tests/features/stage_status.feature",
  "packages/earnest/tests/steps/test_task_change.py",
  "packages/earnest/tests/unit/test_git.py",
  "packages/earnest/tests/unit/test_plan.py",
  "packages/earnest/tests/unit/test_reporter.py",
  "packages/earnest/tests/unit/test_cli.py",
  "packages/earnest/tests/integration/test_task_change.py"
]
```
