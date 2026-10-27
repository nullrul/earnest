# M6 `calibration_gate` Implementation Plan

Status: gating answers approved; on 2026-10-27 the user decided that Tasks 2 to 5 and 7 build against the synthetic `tests/fixtures/calibration-dev/`, while Task 1 stays the maintainer's. The maintainer approved the three gating answers and the output contract on 2026-10-25, and on 2026-10-26 revised answer 2 (the fixture source) and approved vendoring the 3d-pipe excerpts, as set out in Gating open questions and Task 1 below. Task 0 records each answer in the row of `docs/design/01-logic-design.md` or `docs/design/02-structural-design.md` that asks it, as each row's "Resolved by" column requires.

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

The M6 entry of `03` names three gating rows. Each answer below is **APPROVED** by the maintainer, on 2026-10-25 except answer 2, which the maintainer revised on 2026-10-26. Each cites the paragraph it comes from.

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

**APPROVED (user, 2026-10-26):** the 3d-pipe repository (`nullrul/apartment-twin`), from its OpenSpec specs. This supersedes the 2026-10-25 answer, which was this repository (`nullrul/earnest`) at `4762161`.

- The maintainer picks ten requirements from `openspec/specs/*/spec.md` and rewrites each as one EARS `req` item (D2). They vendor the code and tests that implement them into the fixture at a pinned 3d-pipe commit, tag them by hand, and rule on every question in `verdicts.json`.
- At least three of the twenty answers should be `not-satisfied`, spread over at least three requirements. Then a judge that always answers `satisfied` matches at most seven and fails.
- Source: `00` SC4 ("on one existing repository with ten hand-written requirements and hand-linked code and tests"), and `01` G10 ("Gate the judge on calibration against a maintainer's hand verdicts").

Why the 3d-pipe repository:

- It lies outside this repository, so it is a more independent test of the judge.
- Its specs are already written, by the maintainer's own project, so the hand verdicts are informed.
- Its code is mostly Python, so the Python adapter reads it.

Trade-off:

- It publishes excerpts of a private repository in this public one; the owner approved that on 2026-10-26 (Task 1). It also costs a vendored snapshot and adapting OpenSpec prose to EARS.

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

### 5. The development fixture

**APPROVED (user, 2026-10-27):**

- The maintainer's hand-written ten-requirement fixture (Task 1, G10, SC4) is not available yet.
- Tasks 2 to 5 and 7, and a demo, build against a SYNTHETIC development fixture at `packages/earnest/tests/fixtures/calibration-dev/`. It has the layout of Task 1's fixture: `requirements.md`, tagged code and tests, `verdicts.json`, `stub-pass.json` and `stub-fail.json`.
- The fixture is agent-written and is not the SC4 calibration set. Its `README.md` says so, and it is never used to claim SC4.
- `tests/fixtures/calibration/` stays reserved for the maintainer's fixture as a data-only drop-in. No code change is needed when it lands.
- The feature and the demo point at `calibration-dev`, and a pass there is no SC4 evidence. The SC4 real-model run stays unrun.
- The demo is `docs/demo/m6-calibrate.sh`, with its captured output in `docs/demo/m6-calibrate.md`.

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
- **Exit codes:** `calibrate` keeps the output contract of answer 4. `check` keeps its codes as M5 left them.
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
| 6 | The full suite, lint and the pre-PR review | T5 | all 5 of M6, with M1 to M5 unchanged |
| 7 | The `anthropic:` model, off the exit path | T6 | none new |

**Regression expectations:**

- **Tasks 2 to 5:** the regression run is `uv run pytest --ignore=tests/steps/test_calibration_gate.py` in `packages/earnest/`, and it stays green at this branch's 956 passed after its rebase onto `0a30de5` (951 at `0a30de5`, which merged M5, plus the five `tests/unit/test_conftest.py` tests of `bc26d79`, `62f78e1` and `a5e0859` and their review fix `fcc2667`, before the M6 test files exist) plus the tests each task adds; record the exact count. The fixture builders in `tests/conftest.py` leave bytecode out of every copy and file list, so a stray `__pycache__/` in a fixture no longer changes a commit sha.
- **Task 2:** every M6 scenario is red.
- **Every task** records its exact count against that baseline.

## File Structure

| Path under `packages/earnest/` | Responsibility | Task |
| --- | --- | --- |
| `tests/fixtures/calibration/requirements.md` | the ten `req` items | 1 |
| `tests/fixtures/calibration/<copied src and tests>` | the hand-tagged code and tests from the pinned commit | 1 |
| `tests/fixtures/calibration/SOURCE.md` | the chosen requirements' spec text, verbatim; the source repository, the pin and the ownership note | 1 |
| `tests/fixtures/calibration/verdicts.json` | the maintainer's twenty answers | 1 |
| `tests/fixtures/calibration/stub-pass.json`, `stub-fail.json` | `verdicts.json` with results flipped on two, then three, requirements | 2 |
| `tests/fixtures/calibration-dev/README.md` | marks the fixture SYNTHETIC: agent-written, not the SC4 set | dev |
| `tests/fixtures/calibration-dev/requirements.md` | the synthetic `req` items | dev |
| `tests/fixtures/calibration-dev/src/meter.py`, `tests/test_meter.py` | the tagged code and tests | dev |
| `tests/fixtures/calibration-dev/verdicts.json` | the synthetic verdicts | dev |
| `tests/fixtures/calibration-dev/stub-pass.json`, `stub-fail.json` | `verdicts.json` with results flipped on two, then three, requirements | 2 |
| `docs/demo/m6-calibrate.sh` | the demo script, run on `calibration-dev` | demo |
| `docs/demo/m6-calibrate.md` | the demo's captured output | demo |
| `tests/conftest.py` | the two stubs added to `_OVERLAYS`; `verdicts_file`, `model_id`, `prompt_hash` and the `stub_judge` step moved here from `test_judge_check.py` | 2 |
| `tests/steps/test_judge_check.py` | loses `verdicts_file`, `model_id`, `prompt_hash` and `stub_judge` to `conftest.py` | 2 |
| `tests/features/calibration_gate.feature` | M6's 5 scenarios, verbatim from `04` | 2 |
| `tests/steps/test_calibration_gate.py` | pytest-bdd steps; the exit command | 2 |
| `src/earnest/judge/__init__.py` | `Model`, `Row`, `Calibration`, `calibrate`, `slot`, `load_verdicts`, `calibrated`; `Model` in place of `Stub` in signatures; `load_model`'s unset-model message; `judge` takes the `Record` | 3, 4, 5 |
| `src/earnest/cli.py` | the `calibrate` subcommand, dispatched before `_read()`; `judge` passed the `Record` | 4, 5 |
| `tests/unit/test_judge.py`, `tests/unit/test_cli.py`, `tests/integration/test_calibration_gate.py` | each task's tests | 3-5 |
| `src/earnest/judge/__init__.py`, `src/earnest/cli.py`, `pyproject.toml`, `uv.lock`, `tests/unit/test_judge_anthropic.py`, `tests/unit/test_cli.py`, `tests/unit/test_judge.py` | Task 7's model, its root, and its dependency | 7 |

`reporter.py` keeps its `Record.calibration` field and its `write_record`, and it needs no change. Outside the package, only Task 0's docs and the demo files `docs/demo/m6-calibrate.sh` and `docs/demo/m6-calibrate.md` change. Before Task 1, the branch also carries a test-tree fix in `tests/conftest.py`, so that fixture copies leave bytecode out; Task 2 builds on it. Scope paths below cover Tasks 1 to 7; Task 0's docs are named in its Files line.

## Known limits

- The record is per repository (L7). A calibration quiets `--judge` only in the repository whose record it was written to.
- The slot holds one result, the latest (answer 4). Calibrating a second candidate model replaces the pass of the model in use, and `check --judge` under that model is uncalibrated again until it is recalibrated.
- Effort is pinned in code and is not part of the model id. A change to it is a code change, and a new calibration should follow.
- The slot binds the model id and the prompt hash, as the Command surface of `01` says, and not the fixture's content. An edit to `verdicts.json` or `requirements.md` after a pass leaves the judge calibrated until `calibrate` runs again.
- The match compares `result` alone. A judge that is right for the wrong reason still matches, and the printed reasoning is for the maintainer to read.
- Until Task 1 lands, every M6 test and the demo run on the synthetic `calibration-dev` fixture, and a pass there is no SC4 evidence.
- The SC4 gate is unrun until the maintainer runs Task 7's model over the fixture: `EARNEST_JUDGE=anthropic:claude-opus-5-5 uv run earnest calibrate tests/fixtures/calibration`, from `packages/earnest/`.

---

## Tasks

### Task 0: The docs commit

**Files:** Create `docs/superpowers/plans/2026-10-25-calibration-gate.md`; Modify `docs/design/01-logic-design.md`, `docs/design/02-structural-design.md`, `docs/design/03-implementation-plan.md`, `docs/design/04-bdd-test-plan.md`.

- [x] **Step 1:** Replace each PROPOSED answer with the maintainer's decision. Done: all four APPROVED (2026-10-25; answer 2 revised 2026-10-26).
- [x] **Step 2:** Write the M6 section of `04`: the feature, the fixture, the readings, and the five scenario titles, marked PROPOSED.
- [x] **Step 3:** Resolve the three rows in `01` and `02`, add answers 1 and 4 to `01` (UC8 and the Command surface's exit-code paragraph), name `earnest calibrate` in `01`'s provider sentence and the judge's whole-record exception in `02`, and link this plan from M6's entry in `03`. Run `LINT_FILE=<path> make lint-file` on each file. Committed, as rebased onto `0a30de5`, as `ae14d2e` (the plan), `de3271b` (approvals, `04`, rows, link) and the checker-fix commits `3c8e37d`, `0b80f04`, `b727ee0` and `d128133`, the wording commit `dee9be9`, and the pre-PR review fixes `52a8621`, `8c9d571`, `84eed86` and `5153cde`, the checker fixes `e6f4852`, the fixture-copy fix `bc26d79`, its review fix `62f78e1`, the end-to-end tests `a5e0859`, and their review fix `fcc2667`.
- [x] **Step 4:** Check that the index builds with a subdirectory as its root. Result at `fcc2667`, after the rebase onto `0a30de5`: `git.work_tree_files` on `tests/fixtures/seeded-change` lists 27 files relative to it (22 before M5 added its `evidence` overlays), and `adapters.scan`, `build_index` and `structural.traced` give 3 requirements, 3 traced. On `tests/fixtures/broken-links` they list 8 files and give 4 requirements, 2 traced. `earnest check` run from `packages/earnest/` writes SARIF byte-identical to a run from the repository root.
- [x] **Step 5:** Once Task 1's fixture exists, add the Gherkin of the five scenarios with exact tables, and notes for this plan, to `04`'s M6 section. In "A calibration of another model …" the calibration passes, under `stub-pass.json`, and `check --judge` then runs under `stub-fail.json`, whose model id differs; after a failing calibration that scenario would pass even if `calibrated()` ignored the model. Done against the synthetic `calibration-dev` fixture (2026-10-27); the tables follow the maintainer's fixture when Task 1 lands.

### Task 1: The maintainer's fixture

**Files:** Create everything under `packages/earnest/tests/fixtures/calibration/` except the two stubs.

This task is the maintainer's: SC4 and G10 make the requirements and the verdicts hand-written. An agent may copy the chosen files from the pinned commit and write `SOURCE.md`, as set out below, and nothing else.

#### Adapter finding

Every spec in `openspec/specs/*/spec.md` describes Python code. Earnest's Python adapter reads the `.py` code and tests: 41 src and 39 tests in `packages/blueprint`, 10 and 7 in `packages/gates`, and 22 in `tests/behavior`. The Gherkin adapter reads the 9 `.feature` files in `tests/behavior`. In the fixture, the Markdown adapter reads `requirements.md` and `SOURCE.md`; the spec text quoted in `SOURCE.md` defines no `req` item, so only `requirements.md` holds the ten requirements. The TypeScript adapter is not needed. Earnest cannot read the Workflow loop code (`.claude/workflows/*.js`, 2 files, and `tests/workflows/*.mjs`, 3 files), and no candidate depends on it.

#### Vendoring the 3d-pipe material — APPROVED

**APPROVED (user, 2026-10-26):**

`nullrul/earnest` is public; `nullrul/apartment-twin` is private and has no licence for its own source (owner `nullrul` for both). Vendoring publishes the copied excerpts once the branch is pushed.

- A vendored snapshot: it vendors only (i) the chosen requirements' text from `openspec/specs/*/spec.md`, copied verbatim into `SOURCE.md`, and (ii) the code and test files that implement them, under `packages/earnest/tests/fixtures/calibration/` with their 3d-pipe relative paths. `SOURCE.md` also names `nullrul/apartment-twin`, the pin, and the ownership note. The only changes to a copied file are the maintainer's tags and any redaction Step 1 calls for, so a diff against the pin, while it resolves, shows those alone. A file two candidates share is copied once.
- Pin, informational only: `ef5b737ff6d8032c0ae2ae81b253127f660a8734`, on the maintainer's local, unpushed 3d-pipe branch `worktree-kind-snuggling-willow`, 25 commits past origin/main (`36c08c3220d780d92495a3924e0d0c48860a83e8`, which holds no `openspec/`). It may not resolve later; the vendored files, not the sha, are the record. Of the cited code and test files only `blender.py`, `cli.py`, `ifc.py`, `index.py` and `test_index.py` differ from origin/main.
- Vendor nothing else. Never vendor the client drawing-set PDF (not in the repo; the manifest pins it by SHA-256), `data/arkitscenes/*`, or the texture maps (`materials.json` and the CC0 maps `materials_fetch.py` caches). The rest of the repository stays out too, including `ral_classic.json`, the `demo/` web assets, and SAM 3 / ComfyUI models, weights and workflow files; a chosen candidate's own code and tests, such as `segment.py`, are vendored.
- The tests import sibling fixture modules (`pdf_fixtures.py`, `detail_fixtures.py`, `record_fixtures.py`, `look_fixtures.py`, 3d-pipe's `conftest.py`) and the code imports sibling modules. These are not vendored, so the imports stay unresolved. The fixture's tests never run: earnest's `tests/conftest.py` sets `collect_ignore = ["fixtures"]`, and earnest only scans their text.

#### Candidates for the maintainer

Fifteen requirements from `openspec/specs/*/spec.md` at the pin, each quoted verbatim with the Python code and test that implement it. They carry no EARS rewrite, tag or verdict: SC4 and G10 leave those to the maintainer.

1. scene-export, `openspec/specs/scene-export/spec.md` lines 32-34, "Metric units"

   ```text
   ### Requirement: Metric units

   The system SHALL set the scene's unit system to metric with a scale length of 1.0, so that scene coordinates are metres in the IFC frame.
   ```

   - Code: `packages/blueprint/src/blueprint/blender.py` 199-204 (`_build_scene`).
   - Test: `packages/blueprint/tests/test_blender.py` 203-220 `test_bounds_writes_each_objects_world_box_and_the_scenes_units`.
   - Vendor: 1114 lines.

2. scene-export, `openspec/specs/scene-export/spec.md` lines 55-57, "Pass index to part map"

   ```text
   ### Requirement: Pass index to part map

   The system SHALL give each part a `pass_index` counted from 1 (0 is the background), numbering the shell's elements first and the furnishing elements after them, each group ordered by name and then `GlobalId`, so that adding a piece never moves a shell part's number. It SHALL write `scene-index.json` mapping each pass index, as text, to its spec id.
   ```

   - Code: `packages/blueprint/src/blueprint/blender.py` 117-137 (`_add_parts`), 206-212 (index write).
   - Test: `packages/blueprint/tests/test_blender.py` 181-194 `test_shell_parts_keep_their_pass_indices_when_a_piece_is_added`.
   - Vendor: 1114 lines.

3. scene-export, `openspec/specs/scene-export/spec.md` lines 23-25, "Atomic output"

   ```text
   ### Requirement: Atomic output

   The system SHALL make `scene.blend` and `scene-index.json` in scratch space and move them into the work directory only after the Blender process has succeeded, so that a failed run leaves the previous pair unchanged.
   ```

   - Code: `packages/blueprint/src/blueprint/scene.py` 28-60 (`scene`).
   - Test: `packages/blueprint/tests/test_blender.py` 496-504 `test_a_failed_scene_run_leaves_nothing_behind`.
   - Vendor: 608 lines.

4. shell-model, `openspec/specs/shell-model/spec.md` lines 145-147, "Opening host checks and ordering"

   ```text
   ### Requirement: Opening host checks and ordering

   The system SHALL build all non-opening parts before openings, so a host wall exists when its opening is built, and SHALL reject an opening that has no valid host.
   ```

   - Code: `packages/blueprint/src/blueprint/ifc.py` 145-157 (`_anchor`), 258-278 (`_Model.opening`), 307-327 (`build_model`).
   - Test: `packages/blueprint/tests/test_ifc.py` 352-375 `test_a_part_that_cannot_be_built_names_itself` (cases `missing-host`, `off-the-wall`, `past-the-wall-end`, `outside-the-arc`).
   - Vendor: 778 lines.

5. shell-model, `openspec/specs/shell-model/spec.md` lines 178-180, "Stable identifiers"

   ```text
   ### Requirement: Stable identifiers

   The system SHALL derive every element's GlobalId from a uuid5 of its name in a fixed namespace, so a rebuild of the same specs keeps its ids.
   ```

   - Code: `packages/blueprint/src/blueprint/ifc.py` 41-42 (`NAMESPACE`), 192-198 (`_Model._element`).
   - Test: `packages/blueprint/tests/test_ifc.py` 272-284 `test_global_ids_are_stable_across_builds`, 294-309 `test_occurrences_share_a_name_and_keep_their_own_ids`.
   - Vendor: 778 lines.

6. custom-pieces, `openspec/specs/custom-pieces/spec.md` lines 225-227, "Keep wins on IoU"

   ```text
   ### Requirement: Keep wins on IoU

   The system SHALL promote an attempt whose mean outline IoU exceeds the kept spec's by more than the noise floor. The noise floor is the constant `NOISE_FLOOR`, which is 0.0, so any strictly higher IoU wins.
   ```

   - Code: `packages/blueprint/src/blueprint/keep.py` 36 (`NOISE_FLOOR`), 136-150 (`_beats`), 204-208 (in `keep`).
   - Test: `packages/blueprint/tests/test_keep.py` 75-91 `test_keep_promotes_a_better_attempt`, 94-103 `test_keep_leaves_a_worse_one`, 292-295 `test_the_noise_floor_is_the_frozen_repeat_spread`.
   - Vendor: 843 lines.

7. custom-pieces, `openspec/specs/custom-pieces/spec.md` lines 281-283, "Extent safeguard veto"

   ```text
   ### Requirement: Extent safeguard veto

   The system SHALL refuse any promotion that one of the rules above would make when the attempt's `extent_ratio` is worse than the kept spec's (six decimals, same `extent_axes_measured`), leaving `specs/` unchanged and marking the `keep` row with the rule `r73`. A null `extent_ratio`, a missing field or different measured axes SHALL veto nothing.
   ```

   - Code: `packages/blueprint/src/blueprint/keep.py` 44 (`EXTENT_VETO`), 95-115 (`_comparable`, `_extent_worse`), 204-208, 221-222 (in `keep`).
   - Test: `packages/blueprint/tests/test_keep.py` 488-503 `test_a_win_that_worsens_the_extent_is_not_kept_r73`, 506-520 `test_the_extent_veto_compares_to_six_decimals_r73`, 523-545 `test_an_extent_not_comparable_leaves_the_win_as_before_r73`, 548-559 `test_a_vetoed_keep_twice_writes_one_row_r73`.
   - Vendor: 843 lines.

8. custom-pieces, `openspec/specs/custom-pieces/spec.md` lines 313-315, "Review records a grade against a spec hash"

   ```text
   ### Requirement: Review records a grade against a spec hash

   The system SHALL, for `review --part ID --round R --grade MATCH|NEAR|WRONG`, append a `review:<GRADE>` row keyed on the piece and the kept spec's hash and print one JSON line. A repeat for one part, round and spec SHALL write no row. A review SHALL NOT keep, revert or change any spec.
   ```

   - Code: `packages/blueprint/src/blueprint/review.py` 68-94 (`review`).
   - Test: `packages/blueprint/tests/test_review.py` 31-38 `test_review_keys_on_the_kept_specs_hash`, 41-50 `test_each_grade_is_recorded_as_its_own_measure`, 53-63 `test_a_repeated_review_prints_the_first_line`, 66-79 `test_a_round_used_on_another_spec_is_refused`.
   - Vendor: 221 lines.

9. inspection-cameras, `openspec/specs/inspection-cameras/spec.md` lines 180-182, "Yaw normalisation"

   ```text
   ### Requirement: Yaw normalisation

   `verdict` SHALL bring each vote's `yaw_deg` into -180 up to 180, so a turn-around written as 180 or -180 is one value.
   ```

   - Code: `packages/blueprint/src/blueprint/verdict.py` 103-134 (`parse_vote`, the normalisation at 131-132).
   - Test: `packages/blueprint/tests/test_verdict.py` 188-194 `test_a_turn_around_is_one_yaw_however_it_is_written`.
   - Vendor: 1108 lines.

10. inspection-cameras, `openspec/specs/inspection-cameras/spec.md` lines 124-126, "Segment degrades to a blocked exit"

    ```text
    ### Requirement: Segment degrades to a blocked exit

    When a view needs segmenting and ComfyUI does not answer, `segment` SHALL stop with `blocked: comfyui unreachable (make comfy-tunnel)` and exit 2, and SHALL NOT start a pod or ComfyUI itself. A failure of SAM 3 once ComfyUI answers SHALL be reported as a usage error.
    ```

    - Code: `packages/blueprint/src/blueprint/segment.py` 64 (`_UNREACHABLE`), 157-195 (`segment`, ComfyUI probe and error mapping at 183-194). The change from `Blocked` to exit 2 happens in `packages/blueprint/src/blueprint/cli.py` 48-77 (`except Blocked` at 75), which the fixture vendors with it.
    - Test: `packages/blueprint/tests/test_segment.py` 307-332 `test_segment_blocks_without_comfyui`.
    - Vendor: 736 lines.

11. inspection-cameras, `openspec/specs/inspection-cameras/spec.md` lines 152-154, "Compare rejects stale or mismatched inputs"

    ```text
    ### Requirement: Compare rejects stale or mismatched inputs

    `compare` SHALL raise an error, not score, when the firm masks of a view were made with other settings, or when the id image is not the camera's size, and SHALL tell the reader which stage to run again.
    ```

    - Code: `packages/blueprint/src/blueprint/compare.py` 114-137 (`_mask_ious` guards); `packages/blueprint/src/blueprint/segment.py` 82-88 (`cached`).
    - Test: `packages/blueprint/tests/test_compare.py` 458-467 `test_compare_refuses_masks_made_with_other_settings`, 428-438 `test_mask_iou_needs_an_id_image_the_size_of_the_camera`.
    - Vendor: 878 lines.

12. drawing-set-index, `openspec/specs/drawing-set-index/spec.md` lines 9-11, "Drawing-set precondition"

    ```text
    ### Requirement: Drawing-set precondition

    The system SHALL run `index` only on a manifest whose scene source is a drawing set, and only against the PDF whose SHA-256 equals the one the manifest records, and SHALL return the manifest unchanged.
    ```

    - Code: `packages/blueprint/src/blueprint/index.py` 131-141, 164 (`index`); `packages/blueprint/src/blueprint/pdf.py` 75-90 (`verified_pdf`).
    - Test: `packages/blueprint/tests/test_index.py` 564-575 `test_index_blocks_without_pdf`, 578-583 `test_index_rejects_changed_pdf`.
    - Vendor: 1075 lines.

13. drawing-set-index, `openspec/specs/drawing-set-index/spec.md` lines 76-78, "Shell seed specs and stale seed removal"

    ```text
    ### Requirement: Shell seed specs and stale seed removal

    The system SHALL write the shell's seed specs to `specs/` and, on every run, first remove the spec files whose names match the shell seed ids so an earlier seed's parts do not linger.
    ```

    - Code: `packages/blueprint/src/blueprint/index.py` 146-151, 160-161 (`index`).
    - Test: `packages/blueprint/tests/test_index.py` 107-125 `test_index_replaces_its_own_stale_specs_only`.
    - Vendor: 879 lines.

14. drawing-conventions, `openspec/specs/drawing-conventions/spec.md` lines 123-125, "Camera markers are drawn in red"

    ```text
    ### Requirement: Camera markers are drawn in red

    The system SHALL read a camera marker from the camera plan (page 57) on the `16. Annotation` layer as a shape whose pen lies within 0.1 of pure red in RGB distance, and SHALL read its label as a two-digit number. A shape drawn in any other pen SHALL NOT be a marker.
    ```

    - Code: `packages/blueprint/src/blueprint/markers.py` 28-33 (constants), 51-58 (`_is_chevron`, `_is_label`).
    - Test: `packages/blueprint/tests/test_markers.py` 64-79 `test_markers_from_chevrons`, 82-87 `test_markers_reject_a_label_nearest_two_chevrons`, 90-92 `test_markers_need_a_label`.
    - Vendor: 210 lines.

15. blueprint-gates, `openspec/specs/blueprint-gates/spec.md` lines 117-119, "Outcomes and exit codes"

    ```text
    ### Requirement: Outcomes and exit codes

    A gate SHALL exit 0 when every check passes, 2 when at least one check is blocked and none failed, and 1 on any failure or when no check ran. A blocked check SHALL NOT count as a pass.
    ```

    - Code: `packages/gates/src/gates/report.py` 18-21 (`EXIT_CODES`), 112-117 (`status`).
    - Test: `packages/gates/tests/test_report.py` 200-214 `test_status_and_its_exit_code`.
    - Vendor: 455 lines.

Alternates if one drops out: custom-pieces "Keep is idempotent" (spec 295-297; `keep.py` 188-195; `test_keep.py` 208-223) and drawing-set-index "Tagged plan that does not register" (spec 431-433; `index.py` 177-198; `test_index.py` 467-491, 494-504).

- [ ] **Step 1:** The maintainer picks ten of the fifteen candidates above. Copy their spec text, modules and tests from the pinned commit, as the vendoring decision above sets out. Before committing, grep the copied files for 64-hex-digit hashes (the drawing set's SHA-256 among them), API keys or tokens, absolute local paths, hostnames or URLs, and the client and project names the owner supplies for this scan. On any hit, stop and ask the owner whether to redact it or drop the candidate.
- [ ] **Step 2:** The maintainer writes ten EARS requirements in `requirements.md`, tags the code and tests, and writes `verdicts.json` with at least three `not-satisfied` answers over three requirements.
- [ ] **Step 3:** Index the fixture as its own root, by the chain of Task 0 Step 4: `git.work_tree_files(fixture)`, `adapters.scan`, `build_index`, `structural.traced`. It gives ten requirements, all traced, and `ears.findings(index)` gives no `req-not-ears`. Do not run `uv run earnest check` from inside the fixture: `_read()` takes `repo_root(cwd)` and indexes the whole earnest repository. Commit `test: the calibration fixture`.

### Task 2: The `calibration_gate` behavior gate, red

**Files:**

- Create: `stub-pass.json` and `stub-fail.json` under `packages/earnest/tests/fixtures/calibration/`
- Create: `packages/earnest/tests/features/calibration_gate.feature`, `packages/earnest/tests/steps/test_calibration_gate.py`
- Modify: `packages/earnest/tests/conftest.py`, `packages/earnest/tests/steps/test_judge_check.py`

- [x] **Step 1:** Write `stub-pass.json` as `verdicts.json` with one result flipped on each of two requirements, and `stub-fail.json` with three.
- [x] **Step 2:** Add both stubs to `_OVERLAYS` in `conftest.py`, so the existing `fixture_repo("calibration")` leaves them out and commits once on `main` under the pinned identity and dates. Write no second builder.
- [x] **Step 3:** Copy the M6 Gherkin of `04` into `calibration_gate.feature` verbatim.
- [x] **Step 4:** Move `verdicts_file`, `model_id`, `prompt_hash` and the `stub_judge` step from `test_judge_check.py` into `conftest.py`, so both features share them. `verdicts_file(name)` hard-codes `judge-verdicts.json`, so it gains a file parameter, `verdicts_file(name, file="judge-verdicts.json")`. A new step, `the judge is the stub model with the canned verdicts "{file}" of "{name}"`, sits beside M4's step text, which keeps working. `test_judge_check.py` extends its `tests.conftest` import, keeping `commit_on_main` and `location_cell`, with `model_id, prompt_hash` (its only remaining use of `verdicts_file` moves with `model_id` and `stub_judge`), the M6 step module imports all three, as `tests/unit/test_judge.py` already imports from `tests.conftest`, and `test_judge_check.py` drops its now-unused `FIXTURES`, `hashlib` and `importlib.resources.files` imports (ruff F401). `model_id` gains the same `file="judge-verdicts.json"` parameter, so the M6 steps get the id of `stub-pass.json`. Then write the step module. The working directory is the built fixture, so the calibration and the later `check --judge` share one record.
- [x] **Step 5:** Run the regression run, then `uv run pytest tests/steps/test_calibration_gate.py`. Expected: the regression run is green, and all 5 M6 scenarios fail. "Calibrate cannot run …" fails only because it also asserts `err.startswith("earnest: ")` on the whole stderr and `len(err.splitlines()) == 1`, as `tests/unit/test_cli.py:98-99` does, and that the line names the cause; before Task 4, argparse's "invalid choice" also exits 2, but its stderr starts with `usage:` and runs to two lines.
- [x] **Step 6:** Commit `test: RED calibration_gate behavior gate`.

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

- [x] **Step 1:** Write failing tests:
  - `test_eight_matches_pass`: `matches == 8` and `passed`;
  - `test_seven_matches_fail`;
  - `test_match_needs_both_questions`: one question differing makes the row a mismatch;
  - `test_constant_judge_fails`: a stub answering `satisfied` everywhere does not pass against a verdict file with three `not-satisfied` answers over three requirements;
  - `test_overrides_ignored`: an `Override:` line does not stop its question being asked;
  - `test_not_ten_judgeable_exits`: nine, or eleven with one untraced, or ten with one that is not EARS, raises `JudgeError`;
  - `test_missing_maintainer_answer_raises`;
  - `test_slot_shape`: `{"model", "prompt", "matches", "total": 10, "pass"}`.
- [x] **Step 2:** Run `uv run pytest tests/unit/test_judge.py`. Expected: the new tests fail.
- [x] **Step 3:** Implement. Rows are sorted by subject.
- [x] **Step 4:** Run the same command. Expected: it passes, and the regression run is green. Commit `feat: calibration against the maintainer's verdicts`.

### Task 4: `earnest calibrate`

**Files:** Modify `packages/earnest/src/earnest/cli.py`, `packages/earnest/src/earnest/judge/__init__.py` (`load_model`'s unset-model message); Test `packages/earnest/tests/unit/test_cli.py`, `packages/earnest/tests/integration/test_calibration_gate.py`.

**Interfaces:**

- Consumes: `judge.calibrate`, `judge.slot`, `judge.load_verdicts`, `judge.load_model`, `git.repo_root`, `reporter.read_record`, `reporter.write_record`. The fixture's index uses the chain `check` already runs in `cli.py`:
  - `files = git.work_tree_files(fixture)`
  - `index = build_index(adapters.scan(fixture, files))`, with `build_index` from `earnest.index`
  - `levels = structural.traced(index)`, where `produces` is None because the fixture holds no intent
- The maintainer's verdicts are `judge.load_verdicts(fixture / "verdicts.json")` (Task 3). A bad file exits 2, not a traceback.
- Produces: `earnest calibrate <fixture>` on the parser of `_main`, which `main` wraps with the signal handling and the exit 2 on an interrupt. `_main` runs `_read()` on the working directory's repository before it dispatches, so `calibrate` is dispatched before `_read()`, inside `_main`'s existing `try` and through `_Result`, so its faults, a broken pipe and a failed write exit 2 as `check`'s do. A fault in the working directory's own items or intents then cannot make it exit 2.

- [x] **Step 1:** Write failing tests:
  - stdout holds one line per requirement with its id, both pairs and `match` or `differs`, then `matches: <n>/10` and `pass` or `fail`;
  - exit 0 on a pass, 1 on a fail, and 2 for each cause in Global Constraints;
  - the slot is written on both a pass and a fail, and the record's other slots are unchanged;
  - with the working directory in a different Git repository, only the fixture's ten ids appear.
- [x] **Step 2:** Run them. Expected: they fail.
- [x] **Step 3:** Implement. `_main`'s exit-2 handling already catches `GitError`, `OSError`, `RecordError`, `PlanError`, `JudgeError` and `EvidenceError`, so `calibrate` raises only exceptions `_main` already catches. `load_model`'s message for an unset `EARNEST_JUDGE` becomes `earnest needs a model: set EARNEST_JUDGE to stub:<path of a canned-verdict file>`, which names no flag, so it reads right for `--judge`, `--evidence` (which implies `--judge`) and `calibrate`. No test pins the old text.
- [x] **Step 4:** The four scenarios of Task 4 in the order table pass, and the regression run is green. Commit `feat: earnest calibrate`.

### Task 5: `judge-uncalibrated` from the record

**Files:** Modify `packages/earnest/src/earnest/judge/__init__.py`, `packages/earnest/src/earnest/cli.py`; Test `packages/earnest/tests/unit/test_judge.py`.

**Interfaces:**

- Produces: `def calibrated(slot: Mapping[str, object] | None, model: Model) -> bool`. It is `slot is not None and slot.get("pass") is True and slot.get("model") == model.id and slot.get("prompt") == PROMPT_HASH`, using `.get` because the record reader copies the slot without checking its fields.
- `judge(index, levels, model, root, record: Record)` takes the whole record in place of its `judge` slot, still five arguments. This departs from `02`'s "hands each assessor the part of the record it reads" (`cli.py` in Module boundaries), because the judge now reads two slots, `judge` and `calibration`, and passing both would make six arguments, over the lint limit. Task 0 notes the exception in `02`. It reads the cache from `record.judge`, and inserts `uncalibrated(model)` first only when `not calibrated(record.calibration, model)`, so no caller can skip the gate. `cli.py` passes `world.record`. Remove the `shortcut:` comment in `uncalibrated`.

- [x] **Step 1:** Write failing tests:
  - `test_calibrated_needs_pass`;
  - `test_calibrated_needs_same_model_and_prompt`: a slot under another model id, or another prompt hash, returns false;
  - `test_calibrated_none`: a missing slot returns false;
  - `test_calibrated_malformed_slot`: a slot with `"pass": "false"`, and a slot with no `pass` key, each return false without raising.
- [x] **Step 2:** Implement. Update the one existing `judge.judge(...)` call, the `ask` helper at `tests/unit/test_judge.py:70`, to pass `Record(judge=slot or {"cache": {}})` (importing `Record` from `earnest.reporter`), so its callers that pass a slot dict, such as `first.cache`, stay unchanged. `test_one_uncalibrated_finding_per_run_at_line_one_of_the_record` keeps passing with `Record()`, whose `calibration` is None.
- [x] **Step 3:** All 5 M6 scenarios pass, M4's `judge_check` and M5's `evidence_check` stay green (their records hold no calibration, so each `--judge` or `--evidence` run still raises `judge-uncalibrated`), and the regression run is green. Commit `feat: a passing calibration quiets judge-uncalibrated`.

### Task 6: The full suite, lint and the pre-PR review

**Files:** none; this task only runs the checks.

- [x] **Step 1:** From the repository root, run `rtk proxy make test; echo $?` and `rtk proxy make lint; echo $?`. Expected: both print `0`.
- [x] **Step 2:** In `packages/earnest/`, run `rtk proxy uv run pytest tests/steps/test_calibration_gate.py; echo $?`. Expected: `0`.
- [ ] **Step 3:** Run the `/pre-pr-review` skill on HEAD and record its verdict. Nothing is committed in this task.

### Task 7: The `anthropic:` model, off the exit path

This builds the model of gating answer 3. Load the `claude-api` skill before writing the call.

**Files:** Modify `packages/earnest/src/earnest/judge/__init__.py`, `packages/earnest/src/earnest/cli.py` (the root passed to `load_model`), `packages/earnest/pyproject.toml`, `packages/earnest/uv.lock` (rewritten by `uv` when the dependency is added); Test `packages/earnest/tests/unit/test_judge_anthropic.py`, `packages/earnest/tests/unit/test_cli.py`, `packages/earnest/tests/unit/test_judge.py` (its one-argument `load_model` calls pass a root).

- [x] **Step 1:** Write failing tests with a mocked client:
  - `load_model(value, root)` gains the root whose files the regions name. `check` passes the repository root, and `calibrate` passes `<fixture>`, since the fixture's region paths are relative to it, not to the working directory. `root` does not change how a `stub:<path>` value resolves, which stays relative to the working directory. Also, `anthropic:claude-opus-5-5` loads a model whose id is that value; it keeps `ask(question) -> Verdict`, so `judge` and `calibrate` are unchanged;
  - the question text is built from the clause spans and `prompt.txt`, and the `shortcut:` comment in `questions` is removed. All instructions live in `prompt.txt`, which stays as M4 wrote it (answer 3). The code adds only labelled fields (the question kind, the clause, the regions and the tests) in a fixed layout that a unit test pins;
  - each question sends the prompt, the clause, and the tagged regions and tests (`01` Runtime and permission model: "only the requirement clause, the tagged code regions and the tagged tests"), at effort `high`, with no `temperature`;
  - a structured reply becomes a `Verdict`;
  - an API error, a refusal or a malformed reply raises `JudgeError`, so the command exits 2.
- [x] **Step 2:** Implement. Import the SDK only when an `anthropic:` value is named, and add `anthropic` to `[project] dependencies`.
- [x] **Step 3:** The full suite and lint stay green. Commit `feat: the anthropic judge model`. The SC4 run in Known limits is then the maintainer's.

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
  "packages/earnest/tests/fixtures/calibration/",
  "packages/earnest/tests/fixtures/calibration-dev/",
  "docs/demo/m6-calibrate.sh",
  "docs/demo/m6-calibrate.md"
]
```
