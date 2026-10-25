# M5 `evidence_check` Implementation Plan

Status: draft for plan approval. It rests on two answers that are PROPOSED and await the maintainer's approval, one for each gating open question that the M5 section of `docs/design/03-implementation-plan.md` names: where the evidence result is kept (answer E1 below) and the TypeScript evidence fixture (answer E2). It also rests on the M5 scenarios of `docs/design/04-bdd-test-plan.md`, which do not exist yet: `04` adds them "when each milestone's plan is written", so Task 1 writes them there for ratification before it copies them into the feature.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `earnest check --evidence` runs against the stub model, it:

- runs the judge first, as `--evidence` implies `--judge`;
- runs mutmut on the Python files that hold tagged regions, leaving test selection to mutmut, and keeps only the mutants inside tagged regions (D4);
- raises `earnest/evidence-failed` against every requirement whose region holds a surviving mutant, or whose tagged test fails;
- puts every requirement at exactly one of untraced, traced, judged and evidenced, and gives the three percentages separately (SC3 in full);
- writes the evidence result to the record's `evidence` slot (E1), so that the read-only `earnest plan` shows the evidenced task and its unit as done (SC8).

The exit command `uv run pytest tests/steps/test_evidence_check.py` turns green at Task 6.

**Architecture:**

- `impact.py` gains the Evidence rule beside the Impact rule (`02`, `impact.py` in Module boundaries):
  - the files to mutate: each Python file that holds a tagged `impl` region of a traced requirement;
  - the mutmut run, a subprocess through `sys.executable` as `take_map` runs pytest-cov, on a temporary copy of the files Git lists, so nothing is written to the work tree;
  - the read of mutmut's results, each surviving mutant mapped to its file and line, and kept when that line lies in a tagged region (the Region rule);
  - the evidence key and result of each requirement, for the record (E1).
- `structural.py` gives a requirement the level `evidenced` when it is judged and its evidence result is `passed` under a key that matches the current tree.
- `plan.py` reads the record's `evidence` slot through the Reporter's reader in both `check` and `plan`, so Computed status sees evidence without running it; `plan` stays read-only.
- `reporter.py` adds `evidence-failed` to `RULES`, the evidenced percentage, `evidence` in the run header's `layers`, and writes the `evidence` slot.
- `cli.py` adds `--evidence`, which implies `--judge` and exits 2 when mutmut cannot run.

**Tech Stack:** Python 3.12 standard library at runtime (`subprocess`, `json`, `hashlib`, `tempfile`, `shutil`, `pathlib`). mutmut is the repository's tool, run as a subprocess (L4); it joins the package's `dev` dependency group only so that the fixture's runs find it. Task 1 pins its major version after a spike, as mutmut's command line, configuration and result files differ between majors.

**Spec:**

- `docs/design/03-implementation-plan.md`, milestone M5.
- `01`: the Evidence rule, Trace levels, Computed status, D4, the Assessment record, the Process vocabulary, the Command surface, the Runtime and permission model, and the Open questions.
- `02`: `impact.py` in Module boundaries; L1, L4, L5, L6 and L7; `fixtures/seeded-change/`.
- `04`: the M5 section, written in Task 1.

## Gating open questions: proposed answers

Both rows sit in the Open questions section of `01`, resolved "before milestone `evidence_check`". Each answer below is **PROPOSED, awaiting maintainer approval**. Neither is recorded in `01` or `02` until the maintainer approves it; the docs revision that records it is part of Task 1.

### E1 Where the evidence result is kept (PROPOSED, awaiting maintainer approval)

Question (`01`, Open questions): "Where the evidence result is kept, so that the read-only `earnest plan` can show a task as done".

Proposed answer: a sixth key of the assessment record, `evidence`, beside `judge`.

- **Key:** one entry per requirement id with its revision (`req~rate-limit~1`), as the judge cache keys its entries.
- **Value:** `{"key": {"regions": <sha256>, "tests": <sha256>, "tool": "mutmut <version>"}, "result": "passed" | "failed", "commit": <full sha>, "dirty": bool}`. `regions` hashes the requirement's `impl` regions and `tests` its test regions, as the judge cache key's "hash of the covered regions" and "hash of the covering tests" do; `commit` and `dirty` are those of the run header. No timestamp, so a rerun on the same tree writes the same record.
- **Writer:** `earnest check --evidence`, through the Reporter, the record's only writer. It replaces the entry of each requirement it ran and keeps the others.
- **Readers:** `structural.py` and Computed status in `plan.py`, in both `check` and `plan`. An entry counts only when its `regions` and `tests` hashes match the current work tree; any other entry, or none, leaves the requirement short of `evidenced`. `plan` hashes the regions itself, which is model-free and runs no test, so it stays read-only.

Basis:

- `01`, Runtime and permission model, first paragraph: "Until the judge, impact and evidence layers exist, `earnest check` writes only with `--stage` …; each of those layers adds the write of its own slot to `earnest check` when it is built." The evidence layer's own slot is the answer that paragraph already implies.
- `01`, Assessment record: the record "holds the five things listed under Process vocabulary, under these keys", one key per supplying component, and Earnest "preserves the keys it does not know", so a sixth key stays at `version` 1 and an older Earnest keeps it.
- `01`, Process vocabulary: the judge cache key is "the item's id and revision, the question, the hash of the covered regions, the hash of the covering tests, the model id and the prompt hash"; E1's key is the same key less the judge's own parts, so an edit to the code or the tests invalidates the result exactly as it reruns the judge.
- `01`, Computed status and Invariants: a task is done when "each delivered `req` is at trace level evidenced", and "Done is computed from the graph and evidence"; the Command surface makes `earnest plan` read-only, so `plan` can only read evidence that a check kept.
- `02`, L7: the record is "one JSON file, written by the standard library", outside the sensor's `matches`, so the new key adds no file and no artifact.

Approving E1 revises three paragraphs of `01`: the Assessment record's key table (a sixth row, `evidence`, supplied by the evidence layer), the Process vocabulary's "The record holds five things" list (a sixth item), and Computed status (an evidence result counts only under a matching key). `02`'s `reporter.py` entry ("its five contents") and `impact.py` entry change to match.

Alternative weighed: evidence stored in the run header of `--stage`. It would tie evidence to stage checks, while M5's exit behavior runs `check --evidence` with no stage, and a run header holds a stage's status, not a requirement's.

### E2 A TypeScript evidence fixture (PROPOSED, awaiting maintainer approval)

Question (`01`, Open questions): "A TypeScript fixture for evidence through StrykerJS and Jest".

Proposed answer: M5 exits on Python and mutmut alone, with no TypeScript fixture and no Node in the package's tests. The region filter that D4 asks for is one function over a list of surviving mutants with file and line, and the StrykerJS reader is written now and unit-tested against a canned StrykerJS JSON report (`mutation-testing-report-schema`) checked in under `tests/unit/`. A live TypeScript fixture, its Jest and StrykerJS toolchain and an end-to-end scenario move to a later milestone, which a revision of `03` adds.

Basis:

- `03`, M5: the Goal is "run the tagged tests and mutmut", and the exit behavior names no TypeScript case, so the gate needs none.
- `02`, L5, Alternatives considered: the Cucumber scaffold was rejected because it "needs Node to test a Python package"; a Jest and StrykerJS fixture would bring the same Node dependency into `make test` and CI.
- `02`, L1: "The template's TypeScript … packages stay unselected: the engine is Python, and the fork's TypeScript lives in the fork under upstream's Bun and Biome toolchain."
- `02`, L4, table row "Coverage, tests and mutants": `subprocess` running the repository's tools, `json` reading their reports; the StrykerJS side is then one JSON reader, which a canned report tests without Node.
- `01`, D4: Earnest "only filters their results by region", so the filter shared by both tools is the part Earnest owns.

This narrows the question rather than closing it: `01`'s Scope keeps "evidence through mutmut and StrykerJS" in v1, so the TypeScript fixture still owes a milestone. Approving E2 revises the `01` row's "Resolved by" to that later milestone and adds it to `03`'s DAG.

## Global Constraints

- **Layout and lint:**
  - Paths follow the File and directory tree of `02`.
  - The runtime is the standard library alone (L4); mutmut is a dev dependency, never imported.
  - The lint bar is M2's: ruff (line length 120, complexity 10, five arguments, Google docstrings), `ruff format`, `mypy --strict`, and vulture at 80.
- **No network, no key:** `--evidence` implies `--judge`, and the only model is the stub of M4.
- **No Git branch:** the M5 overlay is a commit on `main`, as M4's are.
- **Writes:** the mutmut run works on a temporary copy of the files Git lists for the work tree, outside the repository, and removes it after; Earnest's only write stays `.earnest/` (`01`, Runtime and permission model). mutmut's own configuration for the run is written into that copy, never into the repository's files.
- **Trust:** `--evidence` runs the repository's tests against mutated code, with the trust of running its test suite (`01`, Runtime and permission model). It runs no test with `--evidence` absent.
- **Timeouts and failures:** a mutmut run that cannot start, times out or reports no result exits 2, naming the tool and the reason. A tagged test that fails on the unmutated copy raises `evidence-failed` and is not a mutant result.
- **Region filter:** a surviving mutant counts only when its line lies in a tagged region (the Region rule); it raises `evidence-failed` against every requirement that region's tags cover, located at the mutant's line.
- **Evidenced:** judged, and an evidence result `passed` under a key that matches the current tree (E1). A requirement with no `impl` region of a mutated file is not evidenced.
- **Placement:** `evidence-failed` counts against the stage of the task that delivers the requirement, as M3 places code findings, and its level follows Frontier and position.
- **Exit codes:** `evidence-failed` is an error. `judge-uncalibrated` still fires on every judge run until M6.
- **Process:**
  - No agent `rm`s a path it did not create.
  - `.pi-herdsman/` stays untracked.
  - Each commit stages its task's paths by name, with no `--no-verify`.

## Review Focus

- **The work tree stays clean:** after `check --evidence`, `git status --porcelain` is unchanged; mutmut writes its `mutants/` tree only inside the temporary copy.
- **Stale evidence:** an edit to a covered region or a covering test drops the requirement below `evidenced` in both `check` and `plan`, without a rerun.
- **M1 to M4 unchanged:** none passes `--evidence`; the new key is absent from their records, and their evidenced percentage stays 0%.
- **Position:** `evidence-failed` is an error only at position behind or current; the scenarios that assert a non-zero exit place it there.
- **mutmut's version:** the reader parses the result format of the pinned major alone, and fails with exit 2 on another.

## Task order and the scenarios each turns green

The scenarios are PROPOSED here and written into `04`'s M5 section in Task 1. The clause column maps each to the M5 exit behavior of `03`: (a) `evidence-failed` for a surviving mutant in a tagged region; (b) every requirement at exactly one level, with three separate percentages; (c) the evidenced task and its unit shown as done.

| Scenario | Clause |
| --- | --- |
| "Against the stub model the evidence check reports a surviving mutant in a tagged region" | (a) in one exact findings table |
| "A surviving mutant outside every tagged region raises nothing" | (a), the region filter |
| "Each requirement lands at exactly one trace level, with three percentages" | (b): `traced 100%, judged 66%, evidenced 33%; requirements: 3` |
| "After the evidence check, the plan shows the evidenced task and its unit as done" | (c), through `earnest plan` |
| "An edit under an evidenced requirement drops it below evidenced until the check reruns" | (c), the stale key of E1 |
| "Without --evidence the check runs no test and no mutant" | a guard |

| Task | Content | Depends on | Scenarios green after it |
| --- | --- | --- | --- |
| 0 | This plan, committed with the docs | none | none |
| 1 | The approved E1 and E2 in `01` and `02`, the `04` M5 section, and the `evidence_check` behavior gate, red | maintainer approval of E1, E2 and the scenarios | none |
| 2 | The mutmut run on a temporary copy, and its results, `impact.py` | T1 | "Without --evidence the check runs no test and no mutant" |
| 3 | The region filter and `evidence-failed`; the StrykerJS reader against a canned report | T2 | "Against the stub model …", "A surviving mutant outside every tagged region …" |
| 4 | The `evidenced` level and the three percentages, `structural.py`, `reporter.py` | T3 | "Each requirement lands at exactly one trace level …" |
| 5 | The `evidence` slot, written by `check` and read by `plan` | T4 | "After the evidence check, the plan shows …" |
| 6 | Stale keys | T5 | "An edit under an evidenced requirement …"; all 6 |
| 7 | The full suite, lint and the pre-PR review | T6 | all 6 of M5, with M1 to M4 unchanged |

**Regression expectations:**

- **Tasks 1 to 6:** the regression run is `uv run pytest --ignore=tests/steps/test_evidence_check.py` in `packages/earnest/`, and it stays green at the count of the plan's base commit.
- **Task 1:** every M5 scenario is red; the sha pins pass.
- **Every task** records its exact count against that baseline.

## Fixture: what `seeded-change` adds for M5

M5 reads the units variant of M2b, because SC8's "unit as done" needs a unit. One overlay, `evidence/`, stacks on the units variant as a commit on `main`, and one canned-verdict file sits beside `judge-verdicts.json`, held by no commit.

- `evidence/src/checkout/auth.py`, PROPOSED content, confirmed by the spike of Task 1:
  - adds `# [impl->dsn~window-counter~1]` over a small function of its own, so `task~add-limiter~1`'s design is traced;
  - adds to the `req~lockout-notice~1` region a helper that `test_lockout_message` never calls, such as `lockout_minutes(failures)` returning `15 if failures >= 5 else 0`, so its mutants survive inside a tagged region;
- `evidence/src/checkout/util.py`: an untagged file whose mutants survive and count for nothing. A region runs from its tag to the next tag or the end of the file (the Region rule), so `auth.py` has no untagged line after its first tag, and the "outside every tagged region" scenario needs a second file. mutmut mutates it only if it shares a run with a tagged file; the spike of Task 1 confirms how.
- `evidence-verdicts.json`: every question of the three requirements, `satisfied` for `req~rate-limit~1` and `req~lockout-notice~1`, and `req~audit-log~1 tested` `not-satisfied`, so the levels read evidenced, judged (its evidence failed) and traced.
- Expected readings: `req~rate-limit~1` evidenced, so `task~add-limiter~1` and `unit~u1~1` are done; `req~lockout-notice~1` judged with one `evidence-failed`, so `task~notify-lockout~1` and `unit~u2~1` are not done; `req~audit-log~1` traced.

The exact lines, the surviving mutants and the findings table come from running the pinned mutmut on a scratch copy in Task 1, not from prediction. Two points Task 1 settles before it writes `04`:

- **Position.** In the units variant the frontier is `construction/u1-limiter/code-generation` (`unit_status.feature`), so an `evidence-failed` against `req~lockout-notice~1`, delivered in `construction/u2-notice/code-generation`, sits ahead and is a note with exit 0. PROPOSED: scenarios (a) and (b) run on the base history, where both tasks share the current `construction/code-generation` stage and the error exits non-zero, with the overlay applied there too; scenario (c) and the stale-key scenario run on the units variant.
- **Adjacent tags.** A region runs to the next tag (D10), so a `dsn` tag placed directly above the `req` tag would leave the `req` region with no code. The `dsn~window-counter~1` tag goes on its own small function, and Task 1 checks that the `req~rate-limit~1` region still holds `count_failed_logins`.

## File Structure

| Path under `packages/earnest/` | Responsibility | Task |
| --- | --- | --- |
| `tests/fixtures/seeded-change/evidence/src/checkout/auth.py` | the overlay's tags and seeded surviving mutant | 1 |
| `tests/fixtures/seeded-change/evidence/src/checkout/util.py` | an untagged file whose mutants survive | 1 |
| `tests/fixtures/seeded-change/evidence-verdicts.json` | the stub's verdicts for M5 | 1 |
| `tests/features/evidence_check.feature` | M5's 6 scenarios, verbatim from `04` | 1 |
| `tests/steps/test_evidence_check.py` | pytest-bdd steps; the exit command | 1, 6 |
| `tests/conftest.py` | the builders leave `evidence/` and `evidence-verdicts.json` out; the overlay committer on `main` | 1 |
| `tests/integration/test_seeded_change.py` | the units variant's sha and the overlay's lines pinned | 1 |
| `src/earnest/impact.py` | the mutmut run, its results, the region filter, the StrykerJS reader, the evidence keys | 2-6 |
| `src/earnest/structural.py` | the `evidenced` level | 4 |
| `src/earnest/plan.py` | Computed status reads the `evidence` slot | 5 |
| `src/earnest/reporter.py` | `evidence-failed` in `RULES`; the evidenced percentage; `layers`; the `evidence` slot | 3-5 |
| `src/earnest/cli.py` | `--evidence`, implying `--judge`; exit 2 when mutmut cannot run | 2 |
| `pyproject.toml` | mutmut in the `dev` group, at the major the spike pins | 1 |
| `tests/unit/test_impact.py`, `test_structural.py`, `test_plan.py`, `test_reporter.py`, `test_cli.py`; `tests/unit/stryker-report.json`; `tests/integration/test_evidence_check.py` | each task's tests | 2-6 |

Outside the package, Task 1 revises `01` and `02` as E1 and E2 say and adds the M5 section to `04`. The docs commit that adds this plan also adds its link to M5's entry in `03`; marking M5 done there is outside this plan's scope.

## Known limits

- Python only end to end (E2); StrykerJS results are read but never produced by a test.
- Mutation testing is slow; M5 sets a timeout like `MAP_TIMEOUT` and runs only on `--evidence`.
- mutmut mutates whole files and selects tests itself (D4); Earnest filters by region and never picks tests.
- `judge-uncalibrated` fires on every evidence run until M6.

---

## Tasks

### Task 1: Approved answers, the `04` scenarios, and the behavior gate, red

**Files:**

- Modify: `docs/design/01-logic-design.md`, `docs/design/02-structural-design.md`, `docs/design/04-bdd-test-plan.md`
- Create: the `evidence/` overlay and `evidence-verdicts.json` under `packages/earnest/tests/fixtures/seeded-change/`
- Create: `packages/earnest/tests/features/evidence_check.feature`, `packages/earnest/tests/steps/test_evidence_check.py`
- Modify: `packages/earnest/tests/conftest.py`, `packages/earnest/tests/integration/test_seeded_change.py`, `packages/earnest/pyproject.toml`

- [ ] **Step 1:** Stop unless the maintainer has approved E1, E2 and the scenario list. Record the approved answers in `01` and `02` as each answer's last paragraph says, and close the two rows of `01`'s Open questions.
- [ ] **Step 2:** Spike: add mutmut to the `dev` group, copy the units variant with the proposed overlay to a scratch directory, and run mutmut there. Record its version, command line, configuration and result format, and which mutants survive on which lines. Pin the major in `pyproject.toml`.
- [ ] **Step 3:** Write the overlay and `evidence-verdicts.json` from what the spike showed, then write `04`'s M5 section in the shape of M4's: what `seeded-change` adds, the readings and their basis in `01`, the feature, and the notes.
- [ ] **Step 4:** Leave `evidence/` and `evidence-verdicts.json` out of the builders, add the step that commits `evidence/` on `main` over the units variant, and pin the units variant's sha and the overlay's lines in `test_seeded_change.py`.
- [ ] **Step 5:** Copy the M5 Gherkin of `04` into `evidence_check.feature` verbatim, and write the step module. The stub step sets `EARNEST_JUDGE` to `stub:` and the absolute path of `evidence-verdicts.json`.
- [ ] **Step 6:** Run the regression run, then `uv run pytest tests/steps/test_evidence_check.py`. Expected: the regression run is green, and all 6 M5 scenarios fail.
- [ ] **Step 7:** Commit `test: RED evidence_check behavior gate and seeded-change M5 cases`, with the docs changes in a separate `docs:` commit before it.

### Task 2: The mutmut run and its results, `impact.py`; `--evidence` in `cli.py`

**Files:** Modify `packages/earnest/src/earnest/impact.py`, `cli.py`; Test `tests/unit/test_impact.py`, `tests/unit/test_cli.py`.

- [ ] **Step 1:** Write failing tests:
  - the files to mutate are the Python files holding an `impl` region of a traced requirement, and no others;
  - the run copies the listed files to a temporary directory, writes mutmut's configuration there, and leaves `git status --porcelain` unchanged;
  - mutmut missing, a timeout, and an unreadable result each exit 2;
  - `--evidence` implies `--judge`, and without it no subprocess runs.
- [ ] **Step 2:** Implement, running mutmut through `sys.executable` with the environment `take_map` cleans.
- [ ] **Step 3:** The scenario "Without --evidence the check runs no test and no mutant" passes. Commit `feat: the mutmut run for --evidence`.

### Task 3: The region filter and `evidence-failed`

**Files:** Modify `packages/earnest/src/earnest/impact.py`, `reporter.py`; Create `packages/earnest/tests/unit/stryker-report.json`; Test `tests/unit/test_impact.py`, `tests/unit/test_reporter.py`.

- [ ] **Step 1:** Write failing tests:
  - a surviving mutant on a tagged line raises `evidence-failed` against each requirement the region's tags cover, at the mutant's line;
  - a surviving mutant outside every region raises nothing;
  - a tagged test failing on the unmutated copy raises `evidence-failed`;
  - the StrykerJS reader turns the canned report's `Survived` mutants into the same file-and-line list.
- [ ] **Step 2:** Implement. The message names the requirement, the file and line, and the mutation.
- [ ] **Step 3:** The two scenarios of Task 3 pass. Commit `feat: evidence-failed for surviving mutants in tagged regions`.

### Task 4: The `evidenced` level and the three percentages

**Files:** Modify `packages/earnest/src/earnest/structural.py`, `reporter.py`; Test `tests/unit/test_structural.py`, `tests/unit/test_reporter.py`.

- [ ] **Step 1:** Write failing tests: evidenced needs judged and a passing result; each requirement has exactly one level; the evidenced percentage counts among all requirements, rounded down; `layers` names `evidence`.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** The scenario "Each requirement lands at exactly one trace level …" passes. Commit `feat: the evidenced level and percentage`.

### Task 5: The `evidence` slot, written by `check` and read by `plan`

**Files:** Modify `packages/earnest/src/earnest/impact.py`, `plan.py`, `reporter.py`; Test `tests/unit/test_reporter.py`, `tests/unit/test_plan.py`, `tests/integration/test_evidence_check.py`.

- [ ] **Step 1:** Write failing tests: the slot round-trips in canonical JSON; a rerun on the same tree writes the same record; `plan` reads it and shows `task~add-limiter~1` and `unit~u1~1` done and writes nothing.
- [ ] **Step 2:** Implement through the record's existing atomic write.
- [ ] **Step 3:** The scenario "After the evidence check, the plan shows …" passes. Commit `feat: the evidence slot and done from evidence`.

### Task 6: Stale keys

**Files:** Modify `packages/earnest/src/earnest/impact.py`, `plan.py`; Test `tests/unit/test_impact.py`, `tests/unit/test_plan.py`.

- [ ] **Step 1:** Write failing tests: an edit to a covered region, to a covering test, or a different mutmut version each leaves the entry unmatched, so the requirement reads judged and its task not done, in `check` and `plan` alike.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** All 6 M5 scenarios pass, and the regression run is green. Commit `feat: stale evidence drops below evidenced`.

### Task 7: The full suite, lint and the pre-PR review

**Files:** none; this task only runs the checks.

- [ ] **Step 1:** From the repository root, run `rtk proxy make test; echo $?` and `rtk proxy make lint; echo $?`. Expected: both print `0`.
- [ ] **Step 2:** In `packages/earnest/`, run `rtk proxy uv run pytest tests/steps/test_evidence_check.py; echo $?`. Expected: `0`.
- [ ] **Step 3:** Run the `/pre-pr-review` skill on HEAD and record its verdict. Nothing is committed in this task.

## Scope paths

```json
[
  "docs/design/01-logic-design.md",
  "docs/design/02-structural-design.md",
  "docs/design/04-bdd-test-plan.md",
  "packages/earnest/src/earnest/impact.py",
  "packages/earnest/src/earnest/structural.py",
  "packages/earnest/src/earnest/plan.py",
  "packages/earnest/src/earnest/reporter.py",
  "packages/earnest/src/earnest/cli.py",
  "packages/earnest/pyproject.toml",
  "packages/earnest/uv.lock",
  "packages/earnest/tests/conftest.py",
  "packages/earnest/tests/features/evidence_check.feature",
  "packages/earnest/tests/steps/test_evidence_check.py",
  "packages/earnest/tests/unit/test_impact.py",
  "packages/earnest/tests/unit/test_structural.py",
  "packages/earnest/tests/unit/test_plan.py",
  "packages/earnest/tests/unit/test_reporter.py",
  "packages/earnest/tests/unit/test_cli.py",
  "packages/earnest/tests/unit/stryker-report.json",
  "packages/earnest/tests/integration/test_seeded_change.py",
  "packages/earnest/tests/integration/test_evidence_check.py",
  "packages/earnest/tests/fixtures/seeded-change/evidence/",
  "packages/earnest/tests/fixtures/seeded-change/evidence-verdicts.json"
]
```
