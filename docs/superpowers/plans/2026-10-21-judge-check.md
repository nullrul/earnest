# M4 `judge_check` Implementation Plan

Status: draft for plan approval. It rests on the maintainer's resolution of the stub model (a canned-verdict file named by `EARNEST_JUDGE`), recorded in the Runtime and permission model of `docs/design/01-logic-design.md`, and on the fixture layout of resolution A (the `override/` and `override-change/` overlays on `main`), recorded in `docs/design/02-structural-design.md` (`fixtures/seeded-change/`) and in the M4 section of `docs/design/04-bdd-test-plan.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `earnest check --judge` runs against the stub model, it:

- reports `earnest/req-not-ears` for a requirement that is not one EARS sentence (on every check, judge or not);
- asks each traced EARS requirement its `implemented` and `tested` questions, built from its clause spans, and raises `earnest/judge-not-satisfied` with the judge's reasoning and location;
- raises `earnest/judge-uncalibrated` on every judge run, as the record holds no calibration until M6;
- gives each requirement its trace level up to `judged`, and the judged percentage;
- reads `Override:` lines, which stand as the observation of record, and after the change commit raises `earnest/override-expired` and `earnest/override-drift`;
- keeps the judge cache in the record's `judge` slot.

The exit command `uv run pytest tests/steps/test_judge_check.py` turns green at Task 6.

**Architecture:**

- `ears.py` parses each `req` body into its clauses, `where`, `while`, `when`, `if` and `response`, each with its text span, or returns `req-not-ears` (D2), located at the id line.
- `judge/__init__.py` owns the judge:
  - the questions (D14): `implemented` of the `impl` regions and `tested` of the test regions, for each traced requirement that parses;
  - the model, from `EARNEST_JUDGE`: `stub:<path>` loads the canned-verdict file, and its model id is `stub:sha256:<hex>` of the file's bytes;
  - the Override rule: reading `Override:` lines, `override-expired`, `duplicate`, and `override-drift` through the region diff since the override's commit;
  - the judge cache, keyed by the item's id and revision, the question, the hash of the covered regions, the hash of the covering tests, the model id and the prompt hash;
  - the observations of record and the `judged` level.
- `judge/prompt.txt` is the fixed prompt, and its SHA-256 is the prompt hash. The stub never reads it, but its hash still enters the cache key and the run's invocation.
- `git.py` gains the changed lines between a named commit and the work tree, the read the drift check needs. M3's `changed_lines(root, base)` may already serve.
- `reporter.py` renders the new rules, the observations of record under run `properties.observations`, the model id and prompt hash in the run's invocation, the judged percentage, and writes the `judge` slot.
- `cli.py` adds `--judge`, which runs the judge layer after the trace layer and exits 2 when the model cannot run.

**Tech Stack:** Python 3.12 standard library at runtime (`json`, `hashlib`, `re`, `os`, `pathlib`, `dataclasses`). There is no new runtime dependency and no network access (L4); the real model's SDK waits for M6.

**Spec:**

- `docs/design/03-implementation-plan.md`, milestone M4.
- `01`: Grammar, the Override rule, the Process vocabulary, the Region rule, D2, D3, D14, the Command surface and the Runtime and permission model.
- `02`: `ears.py`, `judge/` and `structural.py` in Module boundaries; L4; `fixtures/seeded-change/`.
- `04`: the M4 section.

## Global Constraints

- **Layout and lint:**
  - Paths follow the File and directory tree of `02`.
  - The runtime is the standard library alone (L4).
  - The lint bar is M2's: ruff (line length 120, complexity 10, five arguments, Google docstrings), `ruff format`, `mypy --strict`, and vulture at 80.
- **No network, no key:** the only model M4 builds is the stub. No test reaches a provider.
- **No Git branch:** Earnest reads no branch name, merge-base or `refs/remotes/origin/HEAD`. The fixture's commits sit on `main`; the override's `at` commit is a sha, resolved to its full object id by `git rev-parse --disambiguate=<sha>`, which lists objects alone and never a ref, and kept only when exactly one listed object is a commit.
- **`EARNEST_JUDGE`:** `stub:<path>`, the path relative to the working directory or absolute. `--judge` exits 2 when it is unset or names no known model, when the file cannot be read or is not the object of `01`, and when a question has no answer in the file.
- **The canned-verdict file:** one JSON object keyed by requirement id and revision (`req~rate-limit~1`), then by `implemented` or `tested`. Each answer is `{"result": "satisfied" | "not-satisfied", "reasoning": str, "location": {"file": str, "line": int}}`.
- **Questions:** an overridden question, its override standing, is not asked; under drift it is asked again. An untraced or unparsed requirement is asked nothing.
- **Observations of record:** one per question of each requirement asked or overridden. Each is `{method, subject, question, author, result, reasoning, location}`, sorted by subject and question, under the run's `properties.observations`. An override is method `inspection`, author `maintainer`, result `satisfied`, its reason as reasoning with surrounding spaces trimmed, located at its `Override:` line.
- **Placement:** `req-not-ears`, `override-expired` and `override-drift` count against the stage whose artifact holds their line; `judge-not-satisfied` sits at the verdict's location when that lies in a region the question asked about, else at the id line; `judge-uncalibrated` sits at `.earnest/assessment.json` line 1 and reaches no stage.
- **Drift:** the override's region changed between its commit and the work tree. Only a standing override (current revision) is checked. The `override-drift` finding carries both observations, the override's then the rerun's. The rerun raises no `judge-not-satisfied`; the override stays the observation of record.
- **Writes:** `--judge` writes the record's `judge` slot. Plain `check` still writes nothing, `plan` stays read-only.
- **Exit codes:** `req-not-ears` is an error, so the M4 tables exit non-zero. The other new rules are warnings.
- **Process:**
  - No agent `rm`s a path it did not create.
  - `.pi-herdsman/` stays untracked.
  - Each commit stages its task's paths by name, with no `--no-verify`.

## Review Focus

- **M1 to M3 unchanged:** the EARS parse runs on every check, and every requirement those fixtures seed must parse. A requirement whose body spans lines parses with the breaks read as spaces.
- **The base sha:** `override/` names `89f3937`. Any change to the base fixture files changes that sha and breaks the overlay; the pin in `test_seeded_change.py` catches it.
- **The stub never asks an overridden question:** the canned file deliberately holds no `req~rate-limit~1 implemented`, so asking it exits 2.
- **Cache key:** each of the six parts reruns the question when it changes; a stub file edit changes the model id.
- **Drift region:** the region of an `implemented` override is the requirement's `impl` regions at the work tree, compared through the diff since the override's commit; a moved tag counts as a change.

## Task order and the scenarios each turns green

Scenario names are those of `04`'s "Judge check feature". The clause column maps each scenario to the M4 exit behavior of `03`: (a) `req-not-ears`; (b) a `judge-not-satisfied` verdict with reasoning and location; (c) `judge-uncalibrated`; (d) the judged percentage; (e) an override as the observation of record; (f) after the change commit, `override-expired` and `override-drift`.

| Scenario | Clause |
| --- | --- |
| "Against the stub model the judge check reports its findings" | (a), (b), (c) in one exact table |
| "A requirement that is not one EARS sentence is flagged with the five templates and never judged" | (a) |
| "A not-satisfied verdict is a warning with the judge's reasoning and location" | (b) |
| "A judge run with no passing calibration says so" | (c) |
| "The judged percentage counts the requirements whose every question is satisfied or overridden" | (d) |
| "An override is the observation of record, and the judge is not asked its question" | (e) |
| "The judge cache answers a second run with the same log" | the judge cache of the Goal |
| "After the change commit an override at the old revision expires" | (f) `override-expired` |
| "After the change commit an override whose code moved drifts, and both verdicts show" | (f) `override-drift` |
| "Without --judge the check asks no model" | (a) without the judge; a guard |

| Task | Content | Depends on | Scenarios green after it |
| --- | --- | --- | --- |
| 0 | This plan, committed with the docs (done by the docs commit) | none | none |
| 1 | The `judge_check` behavior gate, red: overlays, canned verdicts, feature, steps | none | none |
| 2 | The EARS parse and `req-not-ears`, `ears.py` | T1 | "Without --judge the check asks no model" |
| 3 | The stub model, questions, observations and `--judge`, `judge/`, `cli.py`, `reporter.py` | T2 | "A not-satisfied verdict …", "A judge run with no passing calibration says so" |
| 4 | The Override rule at a standing override, and the judged level, `judge/` | T3 | "Against the stub model …", "A requirement that is not one EARS sentence …", "The judged percentage …", "An override is the observation of record …" |
| 5 | The judge cache in the record, `judge/`, `reporter.py` | T4 | "The judge cache answers a second run with the same log" |
| 6 | `override-expired` and `override-drift`, `judge/`, `git.py` | T4 | "After the change commit an override at the old revision expires", "After the change commit an override whose code moved drifts, and both verdicts show" |
| 7 | The full suite, lint and the pre-PR review | T5, T6 | all 10 of M4, with M1, M2, M2b and M3 unchanged |

**Regression expectations:**

- **Tasks 1 to 6:** the regression run is `uv run pytest --ignore=tests/steps/test_judge_check.py` in `packages/earnest/`, and it stays green at the count of the plan's base commit.
- **Task 1:** every M4 scenario is red; the base sha pin passes.
- **Every task** records its exact count against that baseline.

## File Structure

| Path under `packages/earnest/` | Responsibility | Task |
| --- | --- | --- |
| `tests/fixtures/seeded-change/override/aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md` | the `override/` overlay, 19 lines as in `04` | 1 |
| `tests/fixtures/seeded-change/override-change/aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md` | the `override/` text with line 3 `req~rate-limit~2` and thirty minutes | 1 |
| `tests/fixtures/seeded-change/override-change/src/checkout/auth.py` | the base file with line 11 `return "Try again shortly."` | 1 |
| `tests/fixtures/seeded-change/judge-verdicts.json` | the three canned verdicts of `04` | 1 |
| `tests/features/judge_check.feature` | M4's 10 scenarios, verbatim from `04` | 1 |
| `tests/steps/test_judge_check.py` | pytest-bdd steps; the exit command | 1, 6 |
| `tests/conftest.py` | the base builder leaves `override/`, `override-change/` and `judge-verdicts.json` out; the overlay committers on `main`; the `location` cell `<file>:<line>` | 1 |
| `tests/integration/test_seeded_change.py` | the base sha `89f3937` and the M4 overlays pinned to the lines `04` names | 1 |
| `src/earnest/ears.py` | `parse(body)`, the clauses with their spans or `None` (new module) | 2 |
| `src/earnest/judge/__init__.py` | `load_model`, `questions`, `overrides`, `judge`, the cache (new package) | 3-6 |
| `src/earnest/judge/prompt.txt` | the fixed prompt | 3 |
| `src/earnest/index.py` | `Override:` key lines kept per item, with their line | 4 |
| `src/earnest/git.py` | the changed lines from a named commit, and the commit's existence | 6 |
| `src/earnest/reporter.py` | the five new rules in `RULES`; `properties.observations`; the invocation's model id and prompt hash; the `judge` slot | 2-5 |
| `src/earnest/cli.py` | `--judge`; exit 2 for a model that cannot run | 3 |
| `pyproject.toml` | `judge/prompt.txt` shipped as package data, if the build needs it | 3 |
| `tests/unit/test_ears.py`, `test_judge.py`, `test_index.py`, `test_git.py`, `test_reporter.py`, `test_cli.py`; `tests/integration/test_judge_check.py` | each task's tests | 2-6 |

Outside the package nothing changes. The docs commit that adds this plan also adds its link to M4's entry in `docs/design/03-implementation-plan.md`; marking M4 done there is outside this plan's scope.

## Known limits

- The stub is the only model. The real model, its SDK and the prompt's wording settle at M6.
- `judge-uncalibrated` fires on every judge run until M6 writes a calibration.
- The questions ask of a whole region; the judge does not split a region by clause.

---

## Tasks

### Task 1: The `judge_check` behavior gate, red

**Files:**

- Create: the two overlays and `judge-verdicts.json` under `packages/earnest/tests/fixtures/seeded-change/`
- Create: `packages/earnest/tests/features/judge_check.feature`, `packages/earnest/tests/steps/test_judge_check.py`
- Modify: `packages/earnest/tests/conftest.py`, `packages/earnest/tests/integration/test_seeded_change.py`

- [ ] **Step 1:** Write the fixture files exactly as the M4 tables of `04` give them.
- [ ] **Step 2:** Leave `override/`, `override-change/` and `judge-verdicts.json` out of the base builder. Add the steps that commit `override/`, then `override-change/`, on `main`. Make no branch.
- [ ] **Step 3:** Pin the base commit's short sha, `89f3937`, and the overlays' lines in `test_seeded_change.py`. If the pin fails, stop: the base fixture changed under the overrides.
- [ ] **Step 4:** Copy the M4 Gherkin of `04` into `judge_check.feature` verbatim.
- [ ] **Step 5:** Write the step module as the M4 Notes of `04` give it. The stub step sets `EARNEST_JUDGE` through `monkeypatch` to `stub:` and the absolute path of `judge-verdicts.json`.
- [ ] **Step 6:** Run the regression run, then `uv run pytest tests/steps/test_judge_check.py`. Expected: the regression run is green, and all 10 M4 scenarios fail.
- [ ] **Step 7:** Commit `test: RED judge_check behavior gate and seeded-change M4 cases`.

### Task 2: The EARS parse and `req-not-ears`, `ears.py`

**Files:** Create `packages/earnest/src/earnest/ears.py`; Modify `reporter.py`, `cli.py`; Test `tests/unit/test_ears.py`, `tests/unit/test_reporter.py`.

- [ ] **Step 1:** Write failing tests:
  - each of the five templates of D2 parses, with its clause spans;
  - `Where`, `While` and `When` or `If` combine in that order;
  - line breaks read as spaces;
  - a body without `shall`, or with two sentences, does not parse.
- [ ] **Step 2:** Implement. `req-not-ears` is an error at the requirement's id line, its message listing the five templates in D2's order. It runs on every check.
- [ ] **Step 3:** M1, M2, M2b and M3 stay green. The scenario "Without --judge the check asks no model" passes. Commit `feat: the EARS parse and req-not-ears`.

### Task 3: The stub model, questions and observations, `judge/`; `--judge` in `cli.py`

**Files:** Create `packages/earnest/src/earnest/judge/__init__.py`, `packages/earnest/src/earnest/judge/prompt.txt`; Modify `reporter.py`, `cli.py`; Test `tests/unit/test_judge.py`, `tests/unit/test_cli.py`.

- [ ] **Step 1:** Write failing tests:
  - `EARNEST_JUDGE` unset, `foo:x`, a missing file, a file that is not the object, and a question with no answer each exit 2;
  - the model id is `stub:sha256:` and the file's SHA-256;
  - two questions per traced EARS requirement, none for an untraced or unparsed one;
  - `judge-not-satisfied` placement: in an asked region at the verdict's location, else at the id line;
  - one `judge-uncalibrated` per run, at `.earnest/assessment.json` line 1, naming the model id and prompt hash.
- [ ] **Step 2:** Implement. The reporter adds the run's `properties.observations` and the model id and prompt hash to the invocation.
- [ ] **Step 3:** The scenarios "A not-satisfied verdict …" and "A judge run with no passing calibration says so" pass. Commit `feat: the stub judge, its questions and --judge`.

### Task 4: The Override rule at a standing override, and the judged level

**Files:** Modify `packages/earnest/src/earnest/judge/__init__.py`, `index.py`, `reporter.py`; Test `tests/unit/test_judge.py`, `tests/unit/test_index.py`.

- [ ] **Step 1:** Write failing tests:
  - an `Override:` line parses by the Grammar, and a malformed one is a near-miss;
  - two overrides of one id and kind give `duplicate`;
  - a standing override replaces the judge's question of its kind, which is not asked;
  - `judged` means traced, with both questions satisfied or overridden.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** The four scenarios of Task 4 in the order table pass. Commit `feat: overrides as the observation of record, and the judged level`.

### Task 5: The judge cache

**Files:** Modify `packages/earnest/src/earnest/judge/__init__.py`, `reporter.py`; Test `tests/unit/test_judge.py`, `tests/integration/test_judge_check.py`.

- [ ] **Step 1:** Write failing tests: a change to each of the key's six parts reruns its question; an unchanged key reuses it; the record's `judge` slot round-trips.
- [ ] **Step 2:** Implement. `--judge` writes the slot through the record's existing atomic write.
- [ ] **Step 3:** The scenario "The judge cache answers a second run with the same log" passes. Commit `feat: the judge cache`.

### Task 6: `override-expired` and `override-drift`

**Files:** Modify `packages/earnest/src/earnest/judge/__init__.py`, `git.py`; Test `tests/unit/test_judge.py`, `tests/unit/test_git.py`.

- [ ] **Step 1:** Write failing tests:
  - an override at a revision other than the current one raises `override-expired` and drops out of the verdict;
  - a standing override whose region changed since its commit raises `override-drift`, reruns the question and carries both observations;
  - an `at` commit Git does not hold raises `override-drift`, as nothing shows the code held still since it, and never exits 2.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** All 10 M4 scenarios pass, and the regression run is green. Commit `feat: expired and drifted overrides`.

### Task 7: The full suite, lint and the pre-PR review

**Files:** none; this task only runs the checks.

- [ ] **Step 1:** From the repository root, run `rtk proxy make test; echo $?` and `rtk proxy make lint; echo $?`. Expected: both print `0`.
- [ ] **Step 2:** In `packages/earnest/`, run `rtk proxy uv run pytest tests/steps/test_judge_check.py; echo $?`. Expected: `0`.
- [x] **Step 3:** Run the `/pre-pr-review` skill on HEAD and record its verdict. Nothing is committed in this task. Verdict at `44ec740`: four reviews (code, ponytail, simplify, security), no P0 or P1.

## Scope paths

```json
[
  "packages/earnest/src/earnest/ears.py",
  "packages/earnest/src/earnest/judge/__init__.py",
  "packages/earnest/src/earnest/judge/prompt.txt",
  "packages/earnest/src/earnest/index.py",
  "packages/earnest/src/earnest/git.py",
  "packages/earnest/src/earnest/reporter.py",
  "packages/earnest/src/earnest/cli.py",
  "packages/earnest/pyproject.toml",
  "packages/earnest/tests/conftest.py",
  "packages/earnest/tests/sarif.py",
  "packages/earnest/tests/features/judge_check.feature",
  "packages/earnest/tests/steps/test_judge_check.py",
  "packages/earnest/tests/unit/test_ears.py",
  "packages/earnest/tests/unit/test_judge.py",
  "packages/earnest/tests/unit/test_index.py",
  "packages/earnest/tests/unit/test_git.py",
  "packages/earnest/tests/unit/test_reporter.py",
  "packages/earnest/tests/unit/test_cli.py",
  "packages/earnest/tests/integration/test_seeded_change.py",
  "packages/earnest/tests/integration/test_judge_check.py",
  "packages/earnest/tests/fixtures/seeded-change/override/",
  "packages/earnest/tests/fixtures/seeded-change/override-change/",
  "packages/earnest/tests/fixtures/seeded-change/judge-verdicts.json"
]
```
