# M6 `calibration_gate` Implementation Plan

Status: gating answers approved; execution starts once the maintainer supplies Task 1's fixture. The maintainer approved the three gating answers and the output contract on 2026-10-25, as set out in Gating open questions below. Task 0 records each answer in the row of `docs/design/01-logic-design.md` or `docs/design/02-structural-design.md` that asks it, as each row's "Resolved by" column requires.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `earnest calibrate <fixture>`, against the stub model:

- runs the judge over the ten hand-tagged requirements of the fixture;
- prints each requirement's verdicts beside the maintainer's, the match count, and pass or fail;
- counts a pass at eight or more matches (SC4) and writes the result to the record's `calibration` slot;
- after a passing result for the current model id and prompt hash, `check --judge` stops raising `judge-uncalibrated`.

The exit command `uv run pytest tests/steps/test_calibration_gate.py` turns green at Task 5. The real-model run is the SC4 gate itself. It is the maintainer's act after this plan, and Task 7 builds the model it needs off the exit path.

**Architecture:**

- `judge/__init__.py` gains calibration. It asks each of `questions(index, levels)` through `model.ask`, with no override and no cache. It compares each `result` with the maintainer's, and judges pass or fail. It also gains `calibrated(slot, model)`, which reads the record's `calibration` slot. `judge()` takes the whole `Record` in place of its `judge` slot, and raises `judge-uncalibrated` only when `calibrated` is false.
- `cli.py` gains the `calibrate` subcommand. It indexes `<fixture>` through the same chain as `check` and reads `<fixture>/verdicts.json`. It prints the comparison and writes the slot through `reporter.write_record` at the working directory's repository root (L7).
- `tests/fixtures/calibration/` is a plain-file fixture (L6), built into a one-commit repository in `tmp_path` by `tests/conftest.py`.

**Tech Stack:** Python 3.12 standard library at runtime for Tasks 1 to 6 (`json`, `pathlib`, `dataclasses`, `argparse`). Task 7 adds the `anthropic` SDK inside `judge/` (L4), as gating answer 3 sets out.

**Spec:**

- `docs/design/03-implementation-plan.md`, milestone M6.
- `00`: SC4, and "Passing SC4, the calibration gate, is a precondition to executing the first unit."
- `01`: G10, UC8, the Capabilities row "Calibration", Process vocabulary (the record's fifth item), Command surface (the `earnest calibrate` row and the paragraph on `judge-uncalibrated`), Assessment record (the `calibration` key), Runtime and permission model, D14, and Open questions.
- `02`: `cli.py` and `judge/__init__.py` in Module boundaries, `fixtures/calibration/` among its `fixtures/` entries, L4, L6, L7, and Open questions.
- `04`: the milestone table row for M6, and the M6 section Task 0 added.

## Gating open questions

The M6 entry of `03` names three gating rows. Each answer below is **APPROVED (2026-10-25)** by the maintainer. Each cites the paragraph it comes from.

### 1. The file format of `tests/fixtures/calibration/`

Row as asked, before Task 0 resolved it: `02`, Open questions, "The file format of `tests/fixtures/calibration/`: the ten requirements, their hand links and the maintainer's verdicts", resolved by "a revision of `01`, before the calibration gate runs".

**APPROVED (2026-10-25):**

- **Plain files, history at test time.** The fixture is a plain-file repository like `broken-links` and `seeded-change`. `conftest.py` copies it to `tmp_path` and commits it once on `main`. Source: `02` L6 ("seeded fixtures are plain repositories under `tests/fixtures/` … `tests/conftest.py` builds each one's history in `tmp_path`").
- **Items and tags.** The ten requirements are `req` items in one Markdown file, `requirements.md`, in Earnest's item syntax. Each is one EARS sentence (D2), so the judge can ask it (D14). The code and tests are hand-tagged to them with the tags the adapters already read. No `aidlc-state.md` is in the fixture, so the fixture holds no intent. Source: `02` Module boundaries, the `fixtures/` entries, "`fixtures/calibration/`: SC4. The existing repository with ten hand-written requirements, hand-linked code and tests, and the maintainer's verdicts, read by `earnest calibrate`".
- **The maintainer's verdicts.** These are `verdicts.json` at the fixture root, in the canned-verdict format the stub model already reads. That format is one JSON object keyed by `<id>~<revision>`, then by `implemented` and `tested`. Each answer is `{"result", "reasoning", "location": {"file", "line"}}`. With one format there is one parser (`_answers` in `judge/__init__.py`), and a stub file is a verdict file with some results flipped. Source: `01` Runtime and permission model, the paragraph starting "`--judge` reads its model from the environment variable `EARNEST_JUDGE`" ("The file is one JSON object keyed by requirement id and revision, then by question …").
- **A match.** A requirement matches when the judge's `result` equals the maintainer's on both `implemented` and `tested`. `reasoning` and `location` are shown but not compared. The pass is at eight or more matches of ten. Source: `00` SC4 ("the judge agrees with the maintainer on eight or more of ten", counted over the ten requirements), and `01` UC8 ("the judge runs over ten hand-tagged requirements, its verdicts are compared with the maintainer's, and the gate passes at eight or more matches").
- **The test stubs.** `stub-pass.json` (eight matches) and `stub-fail.json` (seven) sit beside `verdicts.json`. The fixture's commit leaves them out, as the `seeded-change` commits leave out `judge-verdicts.json`. Source: `02` Module boundaries, the `fixtures/` entries, "`fixtures/seeded-change/judge-verdicts.json` … No commit holds it".

### 2. Which existing repository SC4's ten requirements come from

Row as asked, before Task 0 resolved it: `01`, Open questions, "Which existing repository SC4's ten hand-written requirements come from", resolved "before milestone `calibration_gate` of `03-implementation-plan.md`".

**APPROVED (2026-10-25):** this repository, `nullrul/earnest`, at commit `4762161`.

- The maintainer picks a few modules of `packages/earnest/src/earnest/` and their unit tests and copies them into the fixture. They write ten EARS requirements against behavior those files already have, tag the code and tests by hand, and rule on every question in `verdicts.json`.
- At least three of the twenty answers should be `not-satisfied`, spread over at least three requirements. Then a judge that always answers `satisfied` matches at most seven and fails.
- Source: `00` SC4 ("on one existing repository with ten hand-written requirements and hand-linked code and tests"), and `01` G10 ("Gate the judge on calibration against a maintainer's hand verdicts").

Why this repository:

- It is an existing repository the maintainer knows, so the hand verdicts are informed.
- Its Python adapter already exists.
- Copying from it needs no licence review and no network access, which keeps L4 and L6.

Trade-off:

- An outside Python repository would make a more independent test of the judge.
- It costs a licence check, a vendored snapshot, and verdicts on code the maintainer did not write.

**Not answerable by this plan:** the ten requirements, their tags, and the maintainer's twenty verdicts. SC4 and G10 make these hand-written, so Task 1 is the maintainer's.

### 3. Judge model choice and prompt

Row as asked, before Task 0 resolved it: `01`, Open questions, "Judge model choice and prompt", resolved by "the calibration gate". The gate does not choose a model; it tests one. The maintainer's approval below settles the choice for L4, so Task 7 may add the SDK, and the SC4 run then confirms the choice or sends it back.

**APPROVED (2026-10-25):**

- **Model.** `EARNEST_JUDGE=anthropic:claude-opus-5-5`. The model id in the run header, the cache key and the calibration slot is that value, verbatim.
- **Credentials.** The `anthropic` Python SDK resolves them on its own, from `ANTHROPIC_API_KEY` or an `ant auth login` profile. Earnest reads no key itself.
- **Request settings.** Effort is pinned to `high` in code. The verdict object is requested through structured outputs. `temperature` is not sent, because the API has rejected sampling parameters since 2026-10-21 (the `claude-api` skill, read 2026-10-25; Task 7 re-checks it).
- **Prompt.** `judge/prompt.txt` stays as M4 wrote it. Any rewording changes the prompt hash and calls for a new calibration (UC8's trigger).
- Sources:
  - `01` Runtime and permission model, the paragraph's last sentence: "The value that names a real model settles with 'Judge model choice and prompt' in the Open questions section".
  - `02` L4, Decision: "plus the judge's model SDK once 'Judge model choice and prompt' … settles; that SDK lands inside `judge/`".
  - `01` UC8, Trigger: "whenever the judge model or prompt changes".
  - `01` D14, Rationale: "fixed questions make verdicts comparable across runs and calibratable".

Trade-offs:

| Option | For | Against |
| --- | --- | --- |
| `claude-opus-5-5` (approved) | The most capable default; a judge is the only check on a verdict | $4 / $20 per million tokens (the `claude-api` skill, read 2026-10-25) |
| `claude-sonnet-5-5` | Half the price | Weaker reading of the code |
| `claude-haiku-5-5` | Cheapest | Least likely to reach eight of ten |
| Standard-library `urllib` in place of the SDK | Keeps the runtime dependency-free | L4 names the SDK, and the API surface shifts under hand-written calls |

### 4. The output contract of `calibrate`

Not a gating row: the Command surface row of `01` leaves it open, and Task 0 adds it to that section's exit-code paragraph.

**APPROVED (2026-10-25):**

- It prints the comparison table and the verdict line to stdout.
- It exits 0 on a pass, 1 on a fail, and 2 when it cannot run.
- It writes the slot on a pass and on a fail. The record holds "the latest calibration result" (`01` Process vocabulary, item 5), so a failing run replaces an earlier pass.

## Global Constraints

- **Layout and lint:**
  - Paths follow the File and directory tree of `02`.
  - The runtime is the standard library alone until Task 7 (L4).
  - The lint bar is M2's: ruff (line length 120, complexity 10, five arguments, Google docstrings), `ruff format`, `mypy --strict`, and vulture at 80.
- **No network, no key:** Tasks 1 to 6 build on the stub alone, and no test reaches a provider. Task 7's tests mock the SDK client.
- **The fixture argument:** `<fixture>` is a directory in a Git work tree. Earnest indexes `git.work_tree_files(<fixture>)`, the paths Git lists under it, relative to it. This works whether the fixture is its own repository or a subdirectory of the one under check. `calibrate` exits 2 in any of these cases:
  - `<fixture>/verdicts.json` is missing or is not the canned-verdict object;
  - the index defines other than exactly ten requirements, or any of them is untraced or does not parse as EARS;
  - the verdict file lacks an answer for any of their twenty questions;
  - `EARNEST_JUDGE` fails as it does for `--judge`.
- **No overrides, no cache:** calibration measures the model. `calibrate` asks every question, ignores `Override:` lines, and neither reads nor writes the record's `judge` slot.
- **The `calibration` slot:** `{"model": str, "prompt": str, "matches": int, "total": 10, "pass": bool}`, written whole through `reporter.write_record` at `git.repo_root(Path.cwd())`. The other slots are kept as read.
- **`judge-uncalibrated`:** raised on a judge run unless the slot holds `pass` true with `model` equal to the run's model id and `prompt` equal to `PROMPT_HASH` (`01` Command surface: "While the record holds no passing calibration for the current model id and prompt hash, every judge run raises `judge-uncalibrated`").
- **Exit codes:** `calibrate` keeps the output contract of answer 4. `check` keeps M4's codes.
- **Process:**
  - No agent `rm`s a path it did not create.
  - `.pi-herdsman/` stays untracked.
  - Each commit stages its task's paths by name, with no `--no-verify`.

## Review Focus

- **An always-satisfied judge must fail.** `verdicts.json` holds at least three `not-satisfied` answers over three requirements. Task 3 adds `test_constant_judge_fails`.
- **Model id and prompt hash both bind.** A pass under one stub file leaves a run with an edited stub file uncalibrated, and a pass under an older prompt hash is not a pass. Task 5 adds `test_calibrated_needs_same_model_and_prompt`.
- **The record is per repository (L7).** Calibrating with the working directory in repository A does not quiet `--judge` in repository B. The step module runs both commands with the same working directory. Known limits states this.
- **A requirement the judge cannot ask.** An untraced requirement, or one that is not EARS, in the fixture exits 2. It does not silently shrink the ten. Task 3 adds `test_not_ten_judgeable_exits`.
- **The fixture is read where it lies.** `calibrate` must not index the working directory's repository in place of `<fixture>`. Task 4 runs it with the working directory in a different Git repository and asserts that only the fixture's ten ids appear. Outside any Git repository, `repo_root` raises `GitError` and the command exits 2.

## Task order and the scenarios each turns green

These scenario names are PROPOSED in the M6 section of `04`, which Task 0 wrote. The clause column maps each one to the M6 exit behavior of `03`: (a) the judge's verdicts on the ten requirements beside the maintainer's; (b) the match count; (c) a pass at eight or more, written to the record; (d) after that, `--judge` stops raising `judge-uncalibrated`.

| Scenario | Clause |
| --- | --- |
| "Calibration shows each verdict beside the maintainer's and passes at eight matches" | (a), (b), (c) |
| "Calibration at seven matches fails and records the failure" | (b), (c) |
| "After a passing calibration the judge run is not uncalibrated" | (d) |
| "A calibration of another model leaves the judge uncalibrated" | (d), the model id binding |
| "Calibrate cannot run without a model or a valid fixture" | exit 2; a guard |

| Task | Content | Depends on | Scenarios green after it |
| --- | --- | --- | --- |
| 0 | The docs commits: this plan with approved answers, `04`'s M6 section, the rows of `01` and `02` resolved, answers 1 and 4 in `01`, and the link in `03` | approval | none |
| 1 | The maintainer's fixture: ten requirements, tags, `verdicts.json` | T0 | none |
| 2 | The `calibration_gate` behavior gate, red: stubs, builder, feature, steps | T1, T0 Step 5 | none |
| 3 | Calibration in `judge/` | T2 | none (unit tier) |
| 4 | `earnest calibrate` in `cli.py`, the output and the slot write | T3 | "Calibration shows …", "Calibration at seven …", "Calibrate cannot run …"; "A calibration of another model …" also passes here, trivially, since every judge run is uncalibrated until Task 5 |
| 5 | `judge-uncalibrated` read from the slot | T4 | "After a passing calibration …"; `test_calibrated_needs_same_model_and_prompt` is the red-to-green proof of the model and prompt binding |
| 6 | The full suite, lint and the pre-PR review | T5 | all 5 of M6, with M1 to M4 unchanged |
| 7 | The `anthropic:` model, off the exit path | T6 | none new |

**Regression expectations:**

- **Tasks 2 to 5:** the regression run is `uv run pytest --ignore=tests/steps/test_calibration_gate.py` in `packages/earnest/`, and it stays green at this branch's 826 passed (821 at `4762161`, plus the five `tests/unit/test_conftest.py` tests of `1d6a5d3`, `53bb562` and `55edd10` and their review fix, before the M6 test files exist) plus the tests each task adds; record the exact count. The fixture builders in `tests/conftest.py` leave bytecode out of every copy and file list, so a stray `__pycache__/` in a fixture no longer changes a commit sha.
- **Task 2:** every M6 scenario is red.
- **Every task** records its exact count against that baseline.

## File Structure

| Path under `packages/earnest/` | Responsibility | Task |
| --- | --- | --- |
| `tests/fixtures/calibration/requirements.md` | the ten `req` items | 1 |
| `tests/fixtures/calibration/<copied src and tests>` | the hand-tagged code and tests from the pinned commit | 1 |
| `tests/fixtures/calibration/verdicts.json` | the maintainer's twenty answers | 1 |
| `tests/fixtures/calibration/stub-pass.json`, `stub-fail.json` | `verdicts.json` with results flipped on two, then three, requirements | 2 |
| `tests/conftest.py` | the two stubs added to `_OVERLAYS`; `verdicts_file`, `model_id`, `prompt_hash` and the `stub_judge` step moved here from `test_judge_check.py` | 2 |
| `tests/steps/test_judge_check.py` | loses `verdicts_file`, `model_id`, `prompt_hash` and `stub_judge` to `conftest.py` | 2 |
| `tests/features/calibration_gate.feature` | M6's 5 scenarios, verbatim from `04` | 2 |
| `tests/steps/test_calibration_gate.py` | pytest-bdd steps; the exit command | 2 |
| `src/earnest/judge/__init__.py` | `Model`, `Row`, `Calibration`, `calibrate`, `slot`, `load_verdicts`, `calibrated`; `Model` in place of `Stub` in signatures; `load_model`'s unset-model message; `judge` takes the `Record` | 3, 4, 5 |
| `src/earnest/cli.py` | the `calibrate` subcommand, dispatched before `_read()`; `judge` passed the `Record` | 4, 5 |
| `tests/unit/test_judge.py`, `tests/unit/test_cli.py`, `tests/integration/test_calibration_gate.py` | each task's tests | 3-5 |
| `src/earnest/judge/__init__.py`, `src/earnest/cli.py`, `pyproject.toml`, `uv.lock`, `tests/unit/test_judge_anthropic.py`, `tests/unit/test_cli.py`, `tests/unit/test_judge.py` | Task 7's model, its root, and its dependency | 7 |

`reporter.py` keeps its `Record.calibration` field and its `write_record`, and it needs no change. Outside the package, only Task 0's docs change. Before Task 1, the branch also carries a test-tree fix in `tests/conftest.py`, so that fixture copies leave bytecode out; Task 2 builds on it. Scope paths below cover Tasks 1 to 7; Task 0's docs are named in its Files line.

## Known limits

- The record is per repository (L7). A calibration quiets `--judge` only in the repository whose record it was written to.
- The slot holds one result, the latest (answer 4). Calibrating a second candidate model replaces the pass of the model in use, and `check --judge` under that model is uncalibrated again until it is recalibrated.
- Effort is pinned in code and is not part of the model id. A change to it is a code change, and a new calibration should follow.
- The slot binds the model id and the prompt hash, as the Command surface of `01` says, and not the fixture's content. An edit to `verdicts.json` or `requirements.md` after a pass leaves the judge calibrated until `calibrate` runs again.
- The match compares `result` alone. A judge that is right for the wrong reason still matches, and the printed reasoning is for the maintainer to read.
- The SC4 gate is unrun until the maintainer runs Task 7's model over the fixture: `EARNEST_JUDGE=anthropic:claude-opus-5-5 uv run earnest calibrate tests/fixtures/calibration`, from `packages/earnest/`.

---

## Tasks

### Task 0: The docs commit

**Files:** Create `docs/superpowers/plans/2026-10-25-calibration-gate.md`; Modify `docs/design/01-logic-design.md`, `docs/design/02-structural-design.md`, `docs/design/03-implementation-plan.md`, `docs/design/04-bdd-test-plan.md`.

- [x] **Step 1:** Replace each PROPOSED answer with the maintainer's decision. Done: all four APPROVED (2026-10-25).
- [x] **Step 2:** Write the M6 section of `04`: the feature, the fixture, the readings, and the five scenario titles, marked PROPOSED.
- [x] **Step 3:** Resolve the three rows in `01` and `02`, add answers 1 and 4 to `01` (UC8 and the Command surface's exit-code paragraph), name `earnest calibrate` in `01`'s provider sentence and the judge's whole-record exception in `02`, and link this plan from M6's entry in `03`. Run `LINT_FILE=<path> make lint-file` on each file. Committed as `ddfc072` (the plan), `1d1ea25` (approvals, `04`, rows, link) and the checker-fix commits `fcfa597`, `be0f384`, `3d09d97` and `03369f0`, the wording commit `39bbf4a`, and the pre-PR review fixes `8cc76af`, `48a435b`, `7e3dfac` and `57d9627`, the checker fixes `800bfce`, the fixture-copy fix `1d6a5d3`, its review fix `53bb562`, the end-to-end tests `55edd10`, and their review fix.
- [x] **Step 4:** Check that the index builds with a subdirectory as its root. Result at `ddfc072`: `git.work_tree_files` on `tests/fixtures/seeded-change` lists 22 files relative to it, and `adapters.scan`, `build_index` and `structural.traced` give 3 requirements, 3 traced. On `tests/fixtures/broken-links` they list 8 files and give 4 requirements, 2 traced. `earnest check` run from `packages/earnest/` writes SARIF byte-identical to a run from the repository root.
- [ ] **Step 5:** Once Task 1's fixture exists, add the Gherkin of the five scenarios with exact tables, and notes for this plan, to `04`'s M6 section.

### Task 1: The maintainer's fixture

**Files:** Create everything under `packages/earnest/tests/fixtures/calibration/` except the two stubs.

This task is the maintainer's: SC4 and G10 make the requirements and the verdicts hand-written. An agent may copy the chosen files from the pinned commit, and nothing else.

- [ ] **Step 1:** Copy the chosen modules and tests from the pinned commit.
- [ ] **Step 2:** The maintainer writes ten EARS requirements in `requirements.md`, tags the code and tests, and writes `verdicts.json` with at least three `not-satisfied` answers over three requirements.
- [ ] **Step 3:** Index the fixture as its own root, by the chain of Task 0 Step 4: `git.work_tree_files(fixture)`, `adapters.scan`, `build_index`, `structural.traced`. It gives ten requirements, all traced, and `ears.findings(index)` gives no `req-not-ears`. Do not run `uv run earnest check` from inside the fixture: `_read()` takes `repo_root(cwd)` and indexes the whole earnest repository. Commit `test: the calibration fixture`.

### Task 2: The `calibration_gate` behavior gate, red

**Files:**

- Create: `stub-pass.json` and `stub-fail.json` under `packages/earnest/tests/fixtures/calibration/`
- Create: `packages/earnest/tests/features/calibration_gate.feature`, `packages/earnest/tests/steps/test_calibration_gate.py`
- Modify: `packages/earnest/tests/conftest.py`, `packages/earnest/tests/steps/test_judge_check.py`

- [ ] **Step 1:** Write `stub-pass.json` as `verdicts.json` with one result flipped on each of two requirements, and `stub-fail.json` with three.
- [ ] **Step 2:** Add both stubs to `_OVERLAYS` in `conftest.py`, so the existing `fixture_repo("calibration")` leaves them out and commits once on `main` under the pinned identity and dates. Write no second builder.
- [ ] **Step 3:** Copy the M6 Gherkin of `04` into `calibration_gate.feature` verbatim.
- [ ] **Step 4:** Move `verdicts_file`, `model_id`, `prompt_hash` and the `stub_judge` step from `test_judge_check.py` into `conftest.py`, so both features share them. `verdicts_file(name)` hard-codes `judge-verdicts.json`, so it gains a file parameter, `verdicts_file(name, file="judge-verdicts.json")`. A new step, `the judge is the stub model with the canned verdicts "{file}" of "{name}"`, sits beside M4's step text, which keeps working. `test_judge_check.py` extends its `tests.conftest` import, keeping `commit_on_main` and `location_cell`, with `model_id, prompt_hash` (its only remaining use of `verdicts_file` moves with `model_id` and `stub_judge`), the M6 step module imports all three, as `tests/unit/test_judge.py` already imports from `tests.conftest`, and `test_judge_check.py` drops its now-unused `FIXTURES`, `hashlib` and `importlib.resources.files` imports (ruff F401). `model_id` gains the same `file="judge-verdicts.json"` parameter, so the M6 steps get the id of `stub-pass.json`. Then write the step module. The working directory is the built fixture, so the calibration and the later `check --judge` share one record.
- [ ] **Step 5:** Run the regression run, then `uv run pytest tests/steps/test_calibration_gate.py`. Expected: the regression run is green, and all 5 M6 scenarios fail. "Calibrate cannot run …" fails only because it also asserts `err.startswith("earnest: ")` on the whole stderr and `len(err.splitlines()) == 1`, as `tests/unit/test_cli.py:71-72` does, and that the line names the cause; before Task 4, argparse's "invalid choice" also exits 2, but its stderr starts with `usage:` and runs to two lines.
- [ ] **Step 6:** Commit `test: RED calibration_gate behavior gate`.

### Task 3: Calibration in `judge/`

**Files:** Modify `packages/earnest/src/earnest/judge/__init__.py`; Test `packages/earnest/tests/unit/test_judge.py`.

**Interfaces:**

- Consumes: `questions(index, levels)`, `Stub.ask(question)`, `Verdict`, `JudgeError`, `PROMPT_HASH`, all from M4.
- Produces:
  - `class Model(Protocol)` with `@property def id(self) -> str: ...` and `def ask(self, question: Question) -> Verdict: ...`. A read-only `id` property is needed because `Stub` is a frozen dataclass; a plain `id: str` member fails `mypy --strict`. `Stub` satisfies it, and every signature that takes a model takes `Model`: `calibrate`, `judge`, `uncalibrated`, `Cache.model`, `cli._analyse` in Task 4, and `calibrated` in Task 5. Task 7's model then needs no other signature change.
  - `@dataclass(frozen=True) class Row: subject: str; judge: Mapping[str, Verdict]; maintainer: Mapping[str, Verdict]`, each keyed by `implemented` and `tested`, so the printer has reasoning and location. `matched` is a property: both results agree.
  - `@dataclass(frozen=True) class Calibration: model: str; rows: tuple[Row, ...]`, with `matches` (the count of matched rows) and `passed` (`matches >= 8`) as properties, so no stored field can disagree with the rows.
  - `def calibrate(index: Index, levels: Mapping[str, str], model: Model, maintainer: Mapping[str, Mapping[str, Verdict]]) -> Calibration`. It raises `JudgeError` for the fixture faults of Global Constraints. The ten-requirement check counts the `req` items in `index.defined`, which must be exactly ten, each `traced` in `levels` and parsing by `ears.parse`. `questions()` alone would silently skip an unaskable eleventh. It asks only the questions of those ten `req` items, so a traced non-`req` item in the fixture is neither asked nor counted.
  - `def slot(calibration: Calibration) -> dict[str, object]`, the record's `calibration` value.
  - `def load_verdicts(path: Path) -> dict[str, dict[str, Verdict]]`, the maintainer's file read through `_answers`, raising `JudgeError` for a missing, truncated or wrongly shaped file. Pull `load_model`'s read and `except` block (`OSError`; `ValueError`, `TypeError`, `KeyError`, `RecursionError`) into one private helper that both call, so neither copies it. The helper takes the name its messages give the file (the stub model's file, or the maintainer's verdicts) and returns the bytes and the parsed answers, since `load_model` digests the bytes for its id. It does not go through `load_model`, whose return type Task 7 widens to `Model`.

- [ ] **Step 1:** Write failing tests:
  - `test_eight_matches_pass`: `matches == 8` and `passed`;
  - `test_seven_matches_fail`;
  - `test_match_needs_both_questions`: one question differing makes the row a mismatch;
  - `test_constant_judge_fails`: a stub answering `satisfied` everywhere does not pass against a verdict file with three `not-satisfied` answers over three requirements;
  - `test_overrides_ignored`: an `Override:` line does not stop its question being asked;
  - `test_not_ten_judgeable_exits`: nine, or eleven with one untraced, or ten with one that is not EARS, raises `JudgeError`;
  - `test_missing_maintainer_answer_raises`;
  - `test_slot_shape`: `{"model", "prompt", "matches", "total": 10, "pass"}`.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_judge.py`. Expected: the new tests fail.
- [ ] **Step 3:** Implement. Rows are sorted by subject.
- [ ] **Step 4:** Run the same command. Expected: it passes, and the regression run is green. Commit `feat: calibration against the maintainer's verdicts`.

### Task 4: `earnest calibrate`

**Files:** Modify `packages/earnest/src/earnest/cli.py`, `packages/earnest/src/earnest/judge/__init__.py` (`load_model`'s unset-model message); Test `packages/earnest/tests/unit/test_cli.py`, `packages/earnest/tests/integration/test_calibration_gate.py`.

**Interfaces:**

- Consumes: `judge.calibrate`, `judge.slot`, `judge.load_verdicts`, `judge.load_model`, `git.repo_root`, `reporter.read_record`, `reporter.write_record`. The fixture's index uses the chain `check` already runs in `cli.py`:
  - `files = git.work_tree_files(fixture)`
  - `index = build_index(adapters.scan(fixture, files))`, with `build_index` from `earnest.index`
  - `levels = structural.traced(index)`, where `produces` is None because the fixture holds no intent
- The maintainer's verdicts are `judge.load_verdicts(fixture / "verdicts.json")` (Task 3). A bad file exits 2, not a traceback.
- Produces: `earnest calibrate <fixture>` on the parser of `main`. `main` runs `_read()` on the working directory's repository before it dispatches, so `calibrate` is dispatched before `_read()`, inside the existing `try` and through `_Result`, so its faults and a broken pipe exit 2 as `check`'s do. A fault in the working directory's own items or intents then cannot make it exit 2.

- [ ] **Step 1:** Write failing tests:
  - stdout holds one line per requirement with its id, both pairs and `match` or `differs`, then `matches: <n>/10` and `pass` or `fail`;
  - exit 0 on a pass, 1 on a fail, and 2 for each cause in Global Constraints;
  - the slot is written on both a pass and a fail, and the record's other slots are unchanged;
  - with the working directory in a different Git repository, only the fixture's ten ids appear.
- [ ] **Step 2:** Run them. Expected: they fail.
- [ ] **Step 3:** Implement. `main`'s exit-2 handling already catches `GitError`, `RecordError`, `JudgeError` and `OSError`, so `calibrate` raises only exceptions `main` already catches. `load_model`'s message for an unset `EARNEST_JUDGE` becomes `earnest needs a model: set EARNEST_JUDGE to stub:<path of a canned-verdict file>`, which names no flag, so it reads right for both commands. No test pins the old text.
- [ ] **Step 4:** The four scenarios of Task 4 in the order table pass, and the regression run is green. Commit `feat: earnest calibrate`.

### Task 5: `judge-uncalibrated` from the record

**Files:** Modify `packages/earnest/src/earnest/judge/__init__.py`, `packages/earnest/src/earnest/cli.py`; Test `packages/earnest/tests/unit/test_judge.py`.

**Interfaces:**

- Produces: `def calibrated(slot: Mapping[str, object] | None, model: Model) -> bool`. It is `slot is not None and slot.get("pass") is True and slot.get("model") == model.id and slot.get("prompt") == PROMPT_HASH`, using `.get` because the record reader copies the slot without checking its fields.
- `judge(index, levels, model, root, record: Record)` takes the whole record in place of its `judge` slot, still five arguments. This departs from `02`'s "hands each assessor the part of the record it reads" (`cli.py` in Module boundaries), because the judge now reads two slots, `judge` and `calibration`, and passing both would make six arguments, over the lint limit. Task 0 notes the exception in `02`. It reads the cache from `record.judge`, and inserts `uncalibrated(model)` first only when `not calibrated(record.calibration, model)`, so no caller can skip the gate. `cli.py` passes `world.record`. Remove the `shortcut:` comment in `uncalibrated`.

- [ ] **Step 1:** Write failing tests:
  - `test_calibrated_needs_pass`;
  - `test_calibrated_needs_same_model_and_prompt`: a slot under another model id, or another prompt hash, returns false;
  - `test_calibrated_none`: a missing slot returns false;
  - `test_calibrated_malformed_slot`: a slot with `"pass": "false"`, and a slot with no `pass` key, each return false without raising.
- [ ] **Step 2:** Implement. Update the one existing `judge.judge(...)` call, the `ask` helper at `tests/unit/test_judge.py:70`, to pass `Record(judge=slot or {"cache": {}})` (importing `Record` from `earnest.reporter`), so its callers that pass a slot dict, such as `first.cache`, stay unchanged. `test_one_uncalibrated_finding_per_run_at_line_one_of_the_record` keeps passing with `Record()`, whose `calibration` is None.
- [ ] **Step 3:** All 5 M6 scenarios pass, M4's `judge_check` stays green (its record holds no calibration), and the regression run is green. Commit `feat: a passing calibration quiets judge-uncalibrated`.

### Task 6: The full suite, lint and the pre-PR review

**Files:** none; this task only runs the checks.

- [ ] **Step 1:** From the repository root, run `rtk proxy make test; echo $?` and `rtk proxy make lint; echo $?`. Expected: both print `0`.
- [ ] **Step 2:** In `packages/earnest/`, run `rtk proxy uv run pytest tests/steps/test_calibration_gate.py; echo $?`. Expected: `0`.
- [ ] **Step 3:** Run the `/pre-pr-review` skill on HEAD and record its verdict. Nothing is committed in this task.

### Task 7: The `anthropic:` model, off the exit path

This builds the model of gating answer 3. Load the `claude-api` skill before writing the call.

**Files:** Modify `packages/earnest/src/earnest/judge/__init__.py`, `packages/earnest/src/earnest/cli.py` (the root passed to `load_model`), `packages/earnest/pyproject.toml`, `packages/earnest/uv.lock` (rewritten by `uv` when the dependency is added); Test `packages/earnest/tests/unit/test_judge_anthropic.py`, `packages/earnest/tests/unit/test_cli.py`, `packages/earnest/tests/unit/test_judge.py` (its one-argument `load_model` calls pass a root).

- [ ] **Step 1:** Write failing tests with a mocked client:
  - `load_model(value, root)` gains the root whose files the regions name. `check` passes the repository root, and `calibrate` passes `<fixture>`, since the fixture's region paths are relative to it, not to the working directory. `root` does not change how a `stub:<path>` value resolves, which stays relative to the working directory. Also, `anthropic:claude-opus-5-5` loads a model whose id is that value; it keeps `ask(question) -> Verdict`, so `judge` and `calibrate` are unchanged;
  - the question text is built from the clause spans and `prompt.txt`, and the `shortcut:` comment in `questions` is removed. All instructions live in `prompt.txt`, which stays as M4 wrote it (answer 3). The code adds only labelled fields (the question kind, the clause, the regions and the tests) in a fixed layout that a unit test pins;
  - each question sends the prompt, the clause, and the tagged regions and tests (`01` Runtime and permission model: "only the requirement clause, the tagged code regions and the tagged tests"), at effort `high`, with no `temperature`;
  - a structured reply becomes a `Verdict`;
  - an API error, a refusal or a malformed reply raises `JudgeError`, so the command exits 2.
- [ ] **Step 2:** Implement. Import the SDK only when an `anthropic:` value is named, and add `anthropic` to `[project] dependencies`.
- [ ] **Step 3:** The full suite and lint stay green. Commit `feat: the anthropic judge model`. The SC4 run in Known limits is then the maintainer's.

## Scope paths

```json
[
  "packages/earnest/src/earnest/judge/__init__.py",
  "packages/earnest/src/earnest/cli.py",
  "packages/earnest/pyproject.toml",
  "packages/earnest/uv.lock",
  "packages/earnest/tests/conftest.py",
  "packages/earnest/tests/features/calibration_gate.feature",
  "packages/earnest/tests/steps/test_calibration_gate.py",
  "packages/earnest/tests/steps/test_judge_check.py",
  "packages/earnest/tests/unit/test_judge.py",
  "packages/earnest/tests/unit/test_judge_anthropic.py",
  "packages/earnest/tests/unit/test_cli.py",
  "packages/earnest/tests/integration/test_calibration_gate.py",
  "packages/earnest/tests/fixtures/calibration/"
]
```
