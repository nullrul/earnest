# M6 `calibration_gate` Implementation Plan

Status: APPROVED-ready, 2026-11-25: every maintainer-only decision of Remaining work is DECIDED except the post-run rulings, so what is left is by hand: the user's twenty verdicts (Task 1 Step 6) and, for the SC4 run, this host's Claude Code logged in to Amazon Bedrock, through the `claude-code:` judge backend that Task 7b designs (from spike G) and adds. Gating answers approved; on 2026-10-27 the user decided that Tasks 2 to 5 and 7 build against the synthetic `tests/fixtures/calibration-dev/`, while Task 1 stays the maintainer's. The maintainer approved the three gating answers and the output contract on 2026-10-25, and on 2026-10-26 revised answer 2 (the fixture source) and approved vendoring the 3d-pipe excerpts, as set out in Gating open questions and Task 1 below. Task 0 records each answer in the row of `docs/design/01-logic-design.md` or `docs/design/02-structural-design.md` that asks it, as each row's "Resolved by" column requires.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `earnest calibrate <fixture>`, against the stub model:

- runs the judge over the ten hand-tagged requirements of the fixture;
- prints each requirement's verdicts beside the maintainer's, the match count, and pass or fail;
- counts a pass at eight or more matches (SC4) and writes the result to the record's `calibration` slot;
- after a passing result for the current model id and prompt hash, `check --judge` stops raising `judge-uncalibrated`.

The exit command `uv run pytest tests/steps/test_calibration_gate.py` turns green at Task 5. The real-model run is the SC4 gate itself. It is the maintainer's act after this plan, and Task 7 builds the model it needs off the exit path.

**Architecture:**

- `judge/__init__.py` gains calibration. It asks each of `questions(index, levels)` through `model.ask`, with no override. A later review fix gave `calibrate` its own answer cache, so a rerun skips the answers it already holds (Global Constraints). It compares each `result` with the maintainer's, and judges pass or fail. It also gains `calibrated(slot, model)`, which reads the record's `calibration` slot. `judge()` takes the whole `Record` in place of its `judge` slot, and raises `judge-uncalibrated` only when `calibrated` is false.
- `cli.py` gains the `calibrate` subcommand. It indexes `<fixture>` through the same chain as `check` and reads `<fixture>/verdicts.json`. It prints the comparison and writes the slot through `reporter.write_record` at the working directory's repository root (L7).
- `tests/fixtures/calibration/` is a plain-file fixture (L6), built into a one-commit repository in `tmp_path` by `tests/conftest.py`.

**Tech Stack:** Python 3.12 standard library at runtime for Tasks 1 to 6 (`json`, `pathlib`, `dataclasses`, `argparse`). Task 7 adds the `anthropic` SDK inside `judge/` (L4), as gating answer 3 sets out. Task 7b adds the `claude-code:` model beside it, which runs `claude -p` through the standard library's `subprocess` and so adds no dependency.

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
- **Credentials.** The `anthropic:` adapter's `anthropic` Python SDK resolves them on its own, from `ANTHROPIC_API_KEY` or an `ant auth login` profile, and Earnest reads no key itself. The SC4 run does not use this path: it uses a logged-in Claude Code (Remaining work, Decision 1).
- **Request settings.** Effort is pinned to `high` in code. The verdict object is requested through structured outputs. `temperature` is not sent, because the API has rejected sampling parameters since 2026-10-21 (the `claude-api` skill, read 2026-10-25; Task 7 re-checks it).
- **Prompt.** `judge/prompt.txt` stays as M4 wrote it. Any rewording changes the prompt hash and calls for a new calibration (UC8's trigger).
- Sources:
  - `01` Runtime and permission model, the paragraph's last sentence: "The value that names a real model settles with 'Judge model choice and prompt' in the Open questions section".
  - `02` L4, Decision: "plus the judge's model SDK once 'Judge model choice and prompt' … settles; that SDK lands inside `judge/`".
  - `01` UC8, Trigger: "whenever the judge model or prompt changes".
  - `01` D14, Rationale: "fixed questions make verdicts comparable across runs and calibratable".

Trade-offs:

| Option                                        | For                                                              | Against                                                               |
| --------------------------------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------- |
| `claude-opus-5-5` (approved)                  | The most capable default; a judge is the only check on a verdict | $4 / $20 per million tokens (the `claude-api` skill, read 2026-10-25) |
| `claude-sonnet-5-5`                           | Half the price                                                   | Weaker reading of the code                                            |
| `claude-haiku-5-5`                            | Cheapest                                                         | Least likely to reach eight of ten                                    |
| Standard-library `urllib` in place of the SDK | Keeps the runtime dependency-free                                | L4 names the SDK, and the API surface shifts under hand-written calls |

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
- **No overrides; answers kept apart from check's:** calibration measures the model. `calibrate` ignores `Override:` lines and never reads or writes check's `judge.cache`. It keeps its own answers in the record's `judge.calibrate` entry, through a `Cache` with check's key, so it asks a question again only when the model id, the prompt hash, the sentence or the regions changed (and, from Task 7b, the harness, which is part of the model id). A question that fails, or a ^C, still saves the answers given before it (`cli._calibrate`, `_keep_calibration`; tests `test_a_failed_calibration_keeps_the_answers_already_given` and `test_a_calibration_rerun_asks_no_question_it_has_an_answer_to` in `tests/unit/test_cli.py`). It writes the `calibration` slot only after all twenty are answered.
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

| Scenario                                                                             | Clause                    |
| ------------------------------------------------------------------------------------ | ------------------------- |
| "Calibration shows each verdict beside the maintainer's and passes at eight matches" | (a), (b), (c)             |
| "Calibration at seven matches fails and records the failure"                         | (b), (c)                  |
| "After a passing calibration the judge run is not uncalibrated"                      | (d)                       |
| "A calibration of another model leaves the judge uncalibrated"                       | (d), the model id binding |
| "Calibrate cannot run without a model or a valid fixture"                            | exit 2; a guard           |

| Task | Content                                                                                                                                                                                                  | Depends on    | Scenarios green after it                                                                                                                                                                      |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0    | The docs commits: this plan with approved answers, `04`'s M6 section, the rows of `01` and `02` resolved, answers 1 and 4 in `01`, and the link in `03`                                                  | approval      | none                                                                                                                                                                                          |
| 1    | The maintainer's fixture: ten requirements, tags, `verdicts.json`                                                                                                                                        | T0            | none                                                                                                                                                                                          |
| 2    | The `calibration_gate` behavior gate, red: stubs, builder, feature, steps                                                                                                                                | T1, T0 Step 5 | none                                                                                                                                                                                          |
| 3    | Calibration in `judge/`                                                                                                                                                                                  | T2            | none (unit tier)                                                                                                                                                                              |
| 4    | `earnest calibrate` in `cli.py`, the output and the slot write                                                                                                                                           | T3            | "Calibration shows …", "Calibration at seven …", "Calibrate cannot run …"; "A calibration of another model …" also passes here, trivially, since every judge run is uncalibrated until Task 5 |
| 5    | `judge-uncalibrated` read from the slot                                                                                                                                                                  | T4            | "After a passing calibration …"; `test_calibrated_needs_same_model_and_prompt` is the red-to-green proof of the model and prompt binding                                                      |
| 6    | The full suite, lint and the pre-PR review                                                                                                                                                               | T5            | all 5 of M6, with M1 to M5 unchanged                                                                                                                                                          |
| 7    | The `anthropic:` model, off the exit path                                                                                                                                                                | T6            | none new                                                                                                                                                                                      |
| 7b   | The `claude-code:` model through Claude Code on Bedrock, with the `claude` version and flags in its model id, so in every cache key and the calibration slot; the live one-call check before the SC4 run | T7            | none new                                                                                                                                                                                      |

**Regression expectations:**

- **Tasks 2 to 5:** the regression run is `uv run pytest --ignore=tests/steps/test_calibration_gate.py` in `packages/earnest/`, and it stays green at this branch's 956 passed after its rebase onto `0a30de5` (951 at `0a30de5`, which merged M5, plus the five `tests/unit/test_conftest.py` tests of `bc26d79`, `62f78e1` and `a5e0859` and their review fix `fcc2667`, before the M6 test files exist) plus the tests each task adds; record the exact count. The fixture builders in `tests/conftest.py` leave bytecode out of every copy and file list, so a stray `__pycache__/` in a fixture no longer changes a commit sha.
- **Task 2:** every M6 scenario is red.
- **Every task** records its exact count against that baseline.

## File Structure

| Path under `packages/earnest/`                                                                                                                                                                                                        | Responsibility                                                                                                                                                                              | Task    |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `tests/fixtures/calibration/requirements.md`                                                                                                                                                                                          | the ten `req` items                                                                                                                                                                         | 1       |
| `tests/fixtures/calibration/<copied src and tests>`                                                                                                                                                                                   | the hand-tagged code and tests from the pinned commit                                                                                                                                       | 1       |
| `tests/fixtures/calibration/SOURCE.md`                                                                                                                                                                                                | the chosen requirements' spec text, verbatim; the source repository, the pin and the ownership note                                                                                         | 1       |
| `tests/fixtures/calibration/verdicts.json`                                                                                                                                                                                            | the maintainer's twenty answers                                                                                                                                                             | 1       |
| `tests/fixtures/calibration/stub-pass.json`, `stub-fail.json`                                                                                                                                                                         | `verdicts.json` with results flipped on two, then three, requirements                                                                                                                       | 2       |
| `tests/fixtures/calibration-dev/README.md`                                                                                                                                                                                            | marks the fixture SYNTHETIC: agent-written, not the SC4 set                                                                                                                                 | dev     |
| `tests/fixtures/calibration-dev/requirements.md`                                                                                                                                                                                      | the synthetic `req` items                                                                                                                                                                   | dev     |
| `tests/fixtures/calibration-dev/src/meter.py`, `tests/test_meter.py`                                                                                                                                                                  | the tagged code and tests                                                                                                                                                                   | dev     |
| `tests/fixtures/calibration-dev/verdicts.json`                                                                                                                                                                                        | the synthetic verdicts                                                                                                                                                                      | dev     |
| `tests/fixtures/calibration-dev/stub-pass.json`, `stub-fail.json`                                                                                                                                                                     | `verdicts.json` with results flipped on two, then three, requirements                                                                                                                       | 2       |
| `docs/demo/m6-calibrate.sh`                                                                                                                                                                                                           | the demo script, run on `calibration-dev`                                                                                                                                                   | demo    |
| `docs/demo/m6-calibrate.md`                                                                                                                                                                                                           | the demo's captured output                                                                                                                                                                  | demo    |
| `tests/conftest.py`                                                                                                                                                                                                                   | the two stubs added to `_OVERLAYS`; `verdicts_file`, `model_id`, `prompt_hash` and the `stub_judge` step moved here from `test_judge_check.py`                                              | 2       |
| `tests/steps/test_judge_check.py`                                                                                                                                                                                                     | loses `verdicts_file`, `model_id`, `prompt_hash` and `stub_judge` to `conftest.py`                                                                                                          | 2       |
| `tests/features/calibration_gate.feature`                                                                                                                                                                                             | M6's 5 scenarios, verbatim from `04`                                                                                                                                                        | 2       |
| `tests/steps/test_calibration_gate.py`                                                                                                                                                                                                | pytest-bdd steps; the exit command                                                                                                                                                          | 2       |
| `src/earnest/judge/__init__.py`                                                                                                                                                                                                       | `Model`, `Row`, `Calibration`, `calibrate`, `slot`, `load_verdicts`, `calibrated`; `Model` in place of `Stub` in signatures; `load_model`'s unset-model message; `judge` takes the `Record` | 3, 4, 5 |
| `src/earnest/cli.py`                                                                                                                                                                                                                  | the `calibrate` subcommand, dispatched before `_read()`; `judge` passed the `Record`                                                                                                        | 4, 5    |
| `tests/unit/test_judge.py`, `tests/unit/test_cli.py`, `tests/integration/test_calibration_gate.py`                                                                                                                                    | each task's tests                                                                                                                                                                           | 3-5     |
| `src/earnest/judge/__init__.py`, `src/earnest/cli.py`, `pyproject.toml`, `uv.lock`, `tests/unit/test_judge_anthropic.py`, `tests/unit/test_cli.py`, `tests/unit/test_judge.py`                                                        | Task 7's model, its root, and its dependency                                                                                                                                                | 7       |
| `src/earnest/judge/__init__.py`, `src/earnest/cli.py` (`_keep_calibration`), `tests/unit/test_judge_claude_code.py`, `tests/conftest.py`, `tests/unit/test_impact.py`, `tests/unit/test_cli.py`, `tests/unit/test_judge_anthropic.py` | Task 7b's model with its harness in the id, `_decode` and `_bound`, the two `load_model` messages, `fake_executable`                                                                        | 7b      |
| `docs/superpowers/plans/2026-11-25-spikes/spike-g-live-check.sh`                                                                                                                                                                      | spike G's live-check script, kept as reference                                                                                                                                              | 7b      |
| `docs/demo/m6-calibrate.md`, `.claude/skills/verify-earnest/features/judge.md`, `docs/design/01-logic-design.md`                                                                                                                      | the new unset-model message, and the harness in the id and the provider paragraph                                                                                                           | 7b      |

`reporter.py` keeps its `Record.calibration` field and its `write_record`, and it needs no change. Outside the package, only Task 0's docs and the demo files `docs/demo/m6-calibrate.sh` and `docs/demo/m6-calibrate.md` change. Before Task 1, the branch also carries a test-tree fix in `tests/conftest.py`, so that fixture copies leave bytecode out; Task 2 builds on it.

## Known limits

- The record is per repository (L7). A calibration quiets `--judge` only in the repository whose record it was written to.
- The record takes no lock. A `check` and a `calibrate` run at the same time on one repository are last-writer-wins: a calibration written between check's reread and its write is lost and must be run again.
- The slot holds one result, the latest (answer 4). Calibrating a second candidate model replaces the pass of the model in use, and `check --judge` under that model is uncalibrated again until it is recalibrated.
- Effort is pinned in code and is not part of the model id. A change to it is a code change, and a new calibration should follow.
- The prompt hash covers `prompt.txt` alone. The rest of each question, its labels, clause list and region layout, is built in `question_text`; a change to that code changes what the model is asked but leaves the calibration pass and the cache keys standing, so a new calibration should follow it, as it does for effort.
- An `anthropic:` model id must be the id that answers: a reply whose `model` differs, as from an alias, exits 2 and names the id to set, so a pass binds the model that gave it. A `claude-code:` id is bound the same way, by the single key of the reply's `modelUsage`, and on Bedrock that key may be an inference-profile id (Task 7b).
- A `claude-code:` model also binds its harness, because its id carries it: `claude --version` and a digest of the flags, the schema, the system text and the two pinned variables. A `claude` upgrade, or a change to any of them, makes the judge uncalibrated again and asks every question again, which is the intent. Keep the version the run recorded on #29, so a later uncalibrated warning can be traced to the upgrade.
- A `claude-code:` call loads the user settings (`--setting-sources user`), so the user's `env` block, `model` allowlist and telemetry settings apply to it beside the allowlisted variables. A credential in the user settings' `env` reaches `claude` whatever the allowlist says. On this host that block names no `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` (checked 2026-11-25 by key name).
- The slot binds the model id and the prompt hash, as the Command surface of `01` says, and not the fixture's content. An edit to `verdicts.json` or `requirements.md` after a pass leaves the judge calibrated until `calibrate` runs again.
- The match compares `result` alone. A judge that is right for the wrong reason still matches, and the printed reasoning is for the maintainer to read.
- Until Task 1 lands, every M6 test and the demo run on the synthetic `calibration-dev` fixture, and a pass there is no SC4 evidence.
- The SC4 gate is unrun until the maintainer runs Task 7b's model over the fixture: `EARNEST_JUDGE=claude-code:claude-opus-5-5 uv run earnest calibrate tests/fixtures/calibration`, from `packages/earnest/`, on the host where Claude Code is logged in to Bedrock (the `anthropic:` model of Task 7 is built and needs a key, which the run does not use).

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

#### Steps and exit criterion (issue #28)

Run from the repository root unless a block says otherwise. `[maintainer]` steps are the maintainer's alone; `[agent]` steps may be delegated.

- [x] **Step 1 [maintainer]:** Decisions 1 to 4 below, decided 2026-11-25: the spend, the pin `aff94e3`, and that an agent drafts the ten requirements, the EARS rewrites and the tags for the user to approve. Still to supply: the redaction names (Step 4).
- [ ] **Step 1b [agent]:** Draft the choice of ten of the fifteen (with two alternates), each EARS rewrite, the tags and the region bounds, and hand them to the user for approval. Step 5 starts from this draft.
- [ ] **Step 2 [agent]:** Fetch the source into a new, empty directory outside the repository, and prove the pin resolves.
- [ ] **Step 3 [agent]:** Copy the chosen candidates' code and test files, each once, under their relative paths. Write `SOURCE.md` as the vendoring decision says: the source repository, the pin, the ownership note, and each chosen requirement's spec text verbatim in a `text` fence, so it defines no `req` item. The only change to a copied file is the maintainer's tags.
- [ ] **Step 4 [agent]:** Run the redaction scan. On a hit, stop and ask the owner to redact or drop the candidate.
- [ ] **Step 5 [agent, then maintainer approves]:** Write `requirements.md` from the approved draft of Step 1b, ten items in the syntax of `calibration-dev`: an id line `` `req~<slug>~1` ``, a blank line, then one EARS sentence with lowercase `shall`. Tag the copied code and tests above the function or test, as `# [impl->req~<slug>~1]` and `# [utest->req~<slug>~1]`. Check each sentence with `ears.parse` before writing it.
- [ ] **Step 6 [maintainer, alone]:** Write `verdicts.json`, twenty answers in the canned-verdict format, with at least three `not-satisfied` answers over at least three requirements.
- [ ] **Step 7 [agent]:** Run the checks of the exit criterion. Commit `test: the calibration fixture`, staging the fixture's paths by name and never with `--no-verify`. The maintainer opens the PR through the pre-PR gate, with `Closes #28`.

```bash
WORK=$(mktemp -d)
gh repo clone nullrul/apartment-twin "$WORK/apartment-twin" -- --filter=blob:none --no-checkout
SHA=aff94e3c0ba5667645c5779bbd5b80baf715fc10    # or the pin chosen in Step 1
git -C "$WORK/apartment-twin" cat-file -t "$SHA"    # expect: commit
```

```bash
FIX=packages/earnest/tests/fixtures/calibration
for f in packages/blueprint/src/blueprint/blender.py packages/blueprint/tests/test_blender.py; do    # the chosen files, each once
  mkdir -p "$FIX/$(dirname "$f")"
  git -C "$WORK/apartment-twin" show "$SHA:$f" > "$FIX/$f"
done
```

```bash
rtk proxy grep -rnEi '[0-9a-f]{64}|api[_-]?key|token|secret|/home/|/Users/|https?://' "$FIX"; echo $?    # 1 means no hit
```

Add `-e '<name>'` to the scan for each client and project name the owner supplies. The exit criterion, from `packages/earnest/` with the fixture staged (`git add tests/fixtures/calibration`), is all of these together:

```bash
EARNEST_JUDGE=stub:tests/fixtures/calibration/verdicts.json rtk proxy uv run earnest calibrate tests/fixtures/calibration; echo $?
uv run python - tests/fixtures/calibration <<'EOF'
import sys
from pathlib import Path
from earnest import adapters, ears, git, structural
from earnest.index import build_index
fixture = Path(sys.argv[1]).resolve()
index = build_index(adapters.scan(fixture, git.work_tree_files(fixture)))
levels = structural.traced(index)
reqs = [i for i in index.defined.values() if i.id.type == "req"]
traced = [i for i in reqs if levels.get(str(i.id)) == "traced"]
bad = [f for f in ears.findings(index) if "req-not-ears" in str(f)]
print(f"requirements={len(reqs)} traced={len(traced)} req-not-ears={len(bad)}")
EOF
jq '{answers: [to_entries[] | .value | to_entries[] | select(.value.result=="not-satisfied")] | length, reqs: [to_entries[] | select(.value | to_entries | any(.value.result=="not-satisfied"))] | length, total: ([to_entries[] | .value | to_entries[]] | length)}' tests/fixtures/calibration/verdicts.json
```

Done when:

- the first command prints ten rows that each end in `match`, then `matches: 10/10` and `pass`, with exit `0` (the maintainer's verdicts answer their own questions, which proves all twenty answers exist and the ten are askable);
- the script prints `requirements=10 traced=10 req-not-ears=0` (checked on `calibration-dev`, and on a scratch repository with one `SHALL` sentence, which it counts as `req-not-ears=1`);
- the `jq` output reads `total` 20, with `answers` and `reqs` each at least 3, so an always-`satisfied` judge matches at most 7;
- the scan prints nothing and exits 1;
- `make lint` and `make test` from the repository root both exit 0.

The BDD gate stays on `calibration-dev` (Decision 7, decided); the real fixture needs no code change.

Do not run `uv run earnest check` from inside the fixture: `_read()` takes `repo_root(cwd)` and indexes the whole earnest repository.

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
- [x] **Step 3:** Implement. `_main`'s exit-2 handling already catches `GitError`, `OSError`, `RecordError`, `PlanError`, `JudgeError` and `EvidenceError`, so `calibrate` raises only exceptions `_main` already catches. `load_model`'s message for an unset `EARNEST_JUDGE` becomes `earnest needs a model: set EARNEST_JUDGE to anthropic:<model> or stub:<path of a canned-verdict file>`, which names no flag, so it reads right for `--judge`, `--evidence` (which implies `--judge`) and `calibrate`. No test pins the old text.
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
  "packages/earnest/tests/unit/test_judge_claude_code.py",
  "packages/earnest/tests/unit/test_impact.py",
  "packages/earnest/tests/unit/test_cli.py",
  "packages/earnest/tests/integration/test_calibration_gate.py",
  "packages/earnest/tests/fixtures/calibration/",
  "packages/earnest/tests/fixtures/calibration-dev/",
  "docs/demo/m6-calibrate.sh",
  "docs/demo/m6-calibrate.md",
  ".claude/skills/verify-earnest/features/judge.md",
  "docs/design/01-logic-design.md",
  "docs/superpowers/plans/2026-11-25-spikes/"
]
```

## Remaining work (2026-11-25)

M6's code merged in PR #15 on 2026-11-04, on the synthetic `calibration-dev` fixture. The GitHub milestone "M6 calibration_gate" holds two open issues, and they are the whole of what is left: #28 (Task 1, the SC4 fixture) and #29 (the SC4 real-model run of Known limits). No code is missing. The one box this section leaves alone is Task 6 Step 3, whose PR has merged; the maintainer ticks it. The maintainer decided seven of the eight maintainer-only decisions below on 2026-11-25 (DECIDED (user, 2026-11-25)); Decision 6, the rulings after the run, can only be made once the run exists.

### Ground truth, measured 2026-11-25

All commands ran from `packages/earnest/` at `docs/plan-m6-m9`, with the stub model and no network.

| `EARNEST_JUDGE=`, then `earnest calibrate <fixture>`                                      | Exit | Result                                                                                                                               |
| ----------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `stub:tests/fixtures/calibration-dev/verdicts.json`, on `tests/fixtures/calibration-dev`  | 0    | `matches: 10/10`, `pass`                                                                                                             |
| `stub:tests/fixtures/calibration-dev/stub-pass.json`, on `tests/fixtures/calibration-dev` | 0    | `matches: 8/10`, `pass`                                                                                                              |
| `stub:tests/fixtures/calibration-dev/stub-fail.json`, on `tests/fixtures/calibration-dev` | 1    | `matches: 7/10`, `fail`                                                                                                              |
| `stub:tests/fixtures/calibration-dev/stub-pass.json`, on `tests/fixtures/calibration`     | 2    | `earnest: the maintainer's verdicts cannot be read: [Errno 2] No such file or directory: 'tests/fixtures/calibration/verdicts.json'` |
| unset, on `tests/fixtures/calibration-dev`                                                | 2    | `earnest: earnest needs a model: set EARNEST_JUDGE to anthropic:<model> or stub:<path of a canned-verdict file>`                     |

So `tests/fixtures/calibration/` does not exist yet, and the command named in #28 and #29 exits 2 until it does.

What the real run needs:

- **Adapter:** Task 7b's `ClaudeCode` is to be written; the run waits for it. `Claude` in `src/earnest/judge/__init__.py` is Task 7's `anthropic:` model, built and not used for this run (`anthropic>=2.3.0` stays in `pyproject.toml`, locked at 2.3.0 in `uv.lock`).
- **Environment variable:** `EARNEST_JUDGE=claude-code:claude-opus-5-5`. The name goes to `--model` verbatim (the model's id then adds the harness, Task 7b); a reply whose `modelUsage` names another key, as an alias or a Bedrock inference-profile id would, exits 2 and names the id to set (Task 7b, "The model id may need the Bedrock form"; unverified until its live check).
- **Credentials: DECIDED (user, 2026-11-25), no `ANTHROPIC_API_KEY`.** The SC4 run calls Claude through Claude Code, `claude -p`, on this host, where Claude Code authenticates to Amazon Bedrock (decided 2026-11-25; the first decision named the subscription plan, and the later one moved the run to this host). Task 7b designs and adds that backend, and its environment allowlist forwards exactly the Bedrock and AWS variables that Claude Code reads. The run bills the AWS account Claude Code is configured for, at Bedrock's price, and not a subscription or an Anthropic key. The `anthropic:` adapter of Task 7 stays as built, and its key-or-`ant auth login` credentials are not used for this run. A passing `claude-code:` calibration satisfies SC4. Nothing of the credentials is written to the repository or CI.
- **Shape of the run:** 20 sequential calls, one per question (ten requirements, `implemented` and `tested`), effort `high`, `max_tokens` 16000, no `temperature`. There is a resume: `calibrate` keeps its answers in the record's `judge.calibrate` entry, keyed as check's are, and saves the ones given before a failed call (the code is `cli._calibrate` and `_keep_calibration`; `test_a_failed_calibration_keeps_the_answers_already_given` and `test_a_calibration_rerun_asks_no_question_it_has_an_answer_to` pin it). So a fault at call k exits 2 with no `calibration` slot written, the k-1 answers kept, and the next run asks only the rest. The keys cover the model id, the prompt hash, the sentence and the regions (and, from Task 7b, the harness, which is part of the model id), so an edit to any of them, or a new `claude`, asks again; nothing else makes the next run pay twice. A run that finishes, pass or fail, drops this model's older answers and keeps the other models'.
- **Where the result lands:** `calibrate` writes the `calibration` slot of `.earnest/assessment.json` at the root of the working directory's repository. That file is gitignored (`.earnest/.gitignore` holds `*`), so a pass is a local file and not in Git; the evidence to commit is the captured output and the note in `03`. The stub runs above left a stub slot (7 of 10, fail) in this checkout's record; the real run replaces it.
- **Prompt hash in force:** `sha256:94db4a9d47417c69a26d450d6b74e0ab7dfff4d17288cbdaf76bf1c7ef9c20a6`. Any edit to `judge/prompt.txt` changes it and voids a pass.

### Cost estimate for one real run

20 calls; read the real cost from the AWS account's usage after the run.

### Where the source is

- **No local checkout.** `find ~ -maxdepth 4` for `apartment-twin*`, `3d-pipe*`, `openspec` and `blueprint` finds nothing; `~/Projects` holds `cdk-tf` and `earnest`; `git cat-file -t <pin>` fails in this repository.
- **The pin does not resolve.** `gh api repos/nullrul/apartment-twin/commits/ef5b737ff6d8032c0ae2ae81b253127f660a8734` answers HTTP 422, "No commit found", as the unpushed branch of Task 1 predicts. The repository is private, its `main`, as read on 2026-11-25, is `aff94e3c0ba5667645c5779bbd5b80baf715fc10`, and that `main` now carries `openspec/specs/`. This supersedes "holds no `openspec/`" under "Vendoring the 3d-pipe material".
- **The candidates survive on that `main`.** All 15 requirements match the quotes above and begin at the cited spec lines. Fourteen code anchors (`_build_scene`, `_add_parts`, `NAMESPACE`, `_anchor`, `build_model`, `NOISE_FLOOR`, `_beats`, `review`, `parse_vote`, `index`, `_UNREACHABLE`, `EXIT_CODES`, and two tests) sit inside the cited line ranges, and the eleven test names sampled exist. Not checked: the remaining test line ranges, and whether `blender.py`, `cli.py`, `ifc.py`, `index.py` and `test_index.py` equal the old pin byte for byte. The vendored files are the record, so a new pin is acceptable (Decision 2).
- **EARS rewriting is real work.** Only 6 of the 15 (numbers 1, 3, 4, 5, 12 and 13) parse as one EARS sentence once `SHALL` is lowercased; 2, 6, 7, 8, 9, 10, 11, 14 and 15 do not, and uppercase `SHALL` does not parse at all today (#21, in M9, is open). #28 does not wait for #21 or for #20 (how OpenSpec specs carry ids): `requirements.md` is Earnest's own item syntax, with lowercase `shall`.
- **Lint and tests ignore the fixture.** Ruff and markdownlint exclude `tests/fixtures`, mypy and vulture read `src` alone, and `conftest.py` sets `collect_ignore = ["fixtures"]`, so vendored files with unresolved imports break nothing. The repository-level index does read every tracked file: it defines 26 ids today, among them the ten of `calibration-dev`. Pick slugs that no other fixture already defines.

### Task 7b: The `claude-code:` model, through Claude Code on Bedrock

DECIDED (user, 2026-11-25): the SC4 run uses no `ANTHROPIC_API_KEY`. The judge calls Claude through Claude Code, `claude -p`, and the run happens on this host, where Claude Code authenticates to Amazon Bedrock. A passing `claude-code:` calibration SATISFIES SC4. Spike G prototyped the backend on 2026-11-25 in a scratch copy of earnest at `ae4136c`: 88 lines in `judge/__init__.py`, 29 tests against a fake `claude` on `PATH` (29 passed), and two real calls that both failed at the provider (Change 1 and Step 5 say why). The live-check script is kept in [2026-11-25-spikes/](2026-11-25-spikes/README.md). This task takes its design with three changes, marked below. Gating answer 3 stands (Opus 5.5, effort `high`, `prompt.txt` as M4 wrote it); only the transport differs, so the model id differs. An earlier draft put a `harness` member on `Model`; that draft was built in a scratch copy on 2026-11-25 (the full suite ran 1,108 passed and 1 failed, the demo-transcript test of `test_judge.py`, which reads `docs/`, absent from the scratch copy; `mypy --strict` and `vulture` clean). The id-based design below replaces it, changes far less, and has not been built: Step 3's counts are its proof. No model was called.

#### Design

- **Selector and id.** `EARNEST_JUDGE=claude-code:<name>`, for the SC4 run `claude-code:claude-opus-5-5`. The model's id, in the run header, the cache key and the calibration slot, is `claude-code:<name>@<claude --version output>; flags sha256:<digest>` (the next section), so the harness binds wherever the id does. `<name>` is kept in its own field, `ClaudeCode.model`, and goes to `--model`. It must be the one key of the reply's `modelUsage`: a reply from another key, or from two, exits 2 and names the id to set, so a pass binds the model that gave it. The SDK path of Task 7 is untouched, and no `anthropic` package is imported on this path.
- **Command.** One `claude -p` process per question, so 20 for the SC4 run. The question text, from `question_text`, goes in on stdin and never on the command line. The working directory is a fresh empty temporary directory, removed afterwards, so nothing there is discoverable. A call is bounded at 900 seconds.

  ```text
  claude -p --model <name> --effort high --output-format json --json-schema <_SCHEMA> --tools ""
         --safe-mode --setting-sources user --no-session-persistence --permission-prompts none
         --system-prompt "You are a code reviewer. Follow the user's instructions exactly."
  ```

  `--tools ""` leaves only the schema's `StructuredOutput`; `--safe-mode` drops CLAUDE.md, skills, plugins, hooks, MCP servers and auto memory (`claude --help`: authentication and model selection "work normally"); `--system-prompt` replaces Claude Code's own; `--permission-prompts none` denies anything that would prompt. The reply is one JSON object: `structured_output` holds the verdict (documented: absent when the model declined), `modelUsage` the models that answered, `is_error` and `terminal_reason` the failure.

- **Change 1 from the spike: `--setting-sources user` in place of `--restricted`.** `claude --help` says `--restricted` "ignores user, project and local settings files (managed settings and `--settings` still apply)". On this host the provider setup lives in the user settings: the `env` block (`CLAUDE_CODE_USE_BEDROCK`, `AWS_REGION`, `ANTHROPIC_BEDROCK_REGION_PREFIX`) and an `awsCredentialExport` command, and the process environment holds no `AWS_ACCESS_KEY_ID` or other AWS credential variable. The spike's second call ran with `--restricted` and none of those, and Bedrock refused it with a 403 for the host's EC2 instance profile role, on `inference-profile/us.anthropic.claude-opus-5-5` in `us-east-1`, where the user's settings name the `global` prefix and `us-west-2`: the user's region, prefix and credentials were not applied. Forwarding environment variables alone cannot reach the credential helper, so the user settings must load. `--setting-sources user` loads those and no project or local settings; with `--tools ""` and `--permission-prompts none`, what `--restricted` also did (no code-running tools, file tools confined, writes to settings refused) has nothing left to act on. UNVERIFIED until Step 5: that this flag pair makes `claude -p` run `awsCredentialExport` and apply the `env` block.
- **Change 2 from the spike: the Bedrock variables.** The environment is an allowlist: `claude` gets exactly the variables below when the caller has them set, plus the two pins, and nothing else. `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` never pass, nor does `CLAUDE_CODE_OAUTH_TOKEN` (the spike forwarded it for the subscription path; one billing path per run is clearer, and it is Bedrock). Sources: A is the Amazon Bedrock page of the Claude Code docs (`https://code.claude.com/docs/en/amazon-bedrock.md`, read 2026-11-25), E its Environment variables page (`/env-vars.md`, the same date), H is `claude --help` of 2.1.330.1791.

  | Variable                                                                        | Why `claude` needs it                                                                                                                                                                                                                                                  | Source |
  | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
  | `PATH`, `HOME`, `LANG`, `LC_ALL`, `TMPDIR`                                      | find `claude`, its user directory and a temporary directory                                                                                                                                                                                                            | spike  |
  | `CLAUDE_CONFIG_DIR`                                                             | where Claude Code reads the user settings, when not `~/.claude`                                                                                                                                                                                                        | E      |
  | `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY`, `SSL_CERT_FILE`, `NODE_EXTRA_CA_CERTS` | reach the provider through the host's proxy and certificates                                                                                                                                                                                                           | spike  |
  | `CLAUDE_CODE_USE_BEDROCK`                                                       | selects Amazon Bedrock (step 3, "Configure Claude Code")                                                                                                                                                                                                               | A, E   |
  | `AWS_REGION`, `AWS_DEFAULT_REGION`                                              | the region, in that order, then the profile's, then `us-east-1`                                                                                                                                                                                                        | A      |
  | `ANTHROPIC_BEDROCK_REGION_PREFIX`                                               | the inference-profile prefix tried first: `us`, `eu`, `apac`, `jp`, `au` or `global`                                                                                                                                                                                   | A, E   |
  | `AWS_PROFILE`, `AWS_CONFIG_FILE`, `AWS_SHARED_CREDENTIALS_FILE`                 | the active profile and non-default file paths                                                                                                                                                                                                                          | A      |
  | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`               | an exported access key ("Export an access key")                                                                                                                                                                                                                        | A      |
  | `AWS_BEARER_TOKEN_BEDROCK`                                                      | a Bedrock API key; when set it replaces the credential chain                                                                                                                                                                                                           | A, E   |
  | `AWS_EC2_METADATA_DISABLED`                                                     | the AWS SDK's own switch for the instance-profile fallback of the default chain; not named by the docs; kept because, without it, the spike's second call resolved the instance role through the metadata service, and a host that sets it must have it reach `claude` | spike  |

  Left out on purpose: `ANTHROPIC_DEFAULT_*_MODEL` and `ANTHROPIC_MODEL` (they resolve aliases, and `--model` names an id), `ANTHROPIC_BEDROCK_BASE_URL` and `CLAUDE_CODE_SKIP_BEDROCK_AUTH` (gateways), `ANTHROPIC_BEDROCK_SERVICE_TIER`, and the timeout and cache tuning variables. The two pins are `CLAUDE_CODE_MAX_OUTPUT_TOKENS=16000` (`MAX_TOKENS`, as `Claude` sends) and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`.

- **Billing.** The run bills the AWS account that Claude Code is configured for on this host (the identity `awsCredentialExport` or the variables above resolve to), at Bedrock's price for the model, not the subscription and not an Anthropic key. Read the usage in that account.
- **The model id may need the Bedrock form.** Claude Code maps `--model claude-opus-5-5` to an inference profile: `us.anthropic.claude-opus-5-5` was the resource of the spike's 403, and the docs name the prefix by region (`us.`, `eu.`, `apac.`, `global.`) or by `ANTHROPIC_BEDROCK_REGION_PREFIX`. UNVERIFIED: what key `modelUsage` takes on Bedrock, the name as typed or the profile id; no call has returned an answer. Step 5 prints the keys. If the key differs from the selector, set `EARNEST_JUDGE=claude-code:<that key>` (the error message says so), and check that `--model` accepts it: the docs say to give Bedrock an inference profile id, and an `availableModels` allowlist in the user settings, enforced on this host, may refuse an id that it does not list, in which case that id is added to it by the maintainer. Do not widen the check to a substring match: that would let a dated alias or a fallback model bind to a calibration it did not earn.
- **Every failure is a `JudgeError`, so exit 2.** No `claude` on `PATH`, or `claude --version` failing or empty (`cannot start`); `claude` not executable, timing out or exiting non-zero; output that is not a JSON object; `is_error` (the text of `result`, or `errors`, or `subtype`, or stderr, cut at 300 characters); a `modelUsage` that is not exactly `{name}`; a missing or malformed `structured_output` (a line below 1 is read as line 1, as `Claude` does).

**The harness in the model id (Change 3).** Claude Code changes under the model: a new `claude` can change the system prompt, the tool schema or the structured-output handling. The harness therefore goes into `ClaudeCode.id`, which `Cache.ask` (its `model` part), `calibrate` (`Calibration.model`), `slot`, `calibrated`, `uncalibrated` and `cli._comparison` already key on:

```text
claude-code:<name>@<claude --version output>; flags sha256:<digest>
```

`<digest>` is that of `canonical({"flags": [*_CLAUDE_FLAGS], "pin": _CLAUDE_PIN})`. `_CLAUDE_FLAGS` is the module constant that holds every flag but the model name, including the schema and the system text, and `ask` builds its argv from it, so the hash and the command cannot differ. On this host `claude --version` prints `claude 2.1.330.1791 (ASBX Claude Code, channel stable)`. `_claude_code` builds the id from the selector; the bare `<name>` stays in `ClaudeCode.model`, because `Claude.ask` takes its name as `self.id.partition(":")[2]` and on this id that would return the version and the digest too.

Nothing else in `judge/__init__.py` changes: `Model`, `Stub`, `Claude`, `Cache`, `Calibration`, `calibrate`, `slot`, `calibrated`, `uncalibrated` and `cli._comparison` already take `model.id`, and the test doubles (`Counting`, `Recording`) already copy it. A new `claude` or flag is a new id: every cache key differs, so every question is asked again; a slot written under the old id is not `calibrated`; the table header and the warning name the full id, with the version. A slot keeps its five keys, and the BDD gate's tables of `04` do not move.

One place changes, `cli._keep_calibration`. It drops a finished run's earlier answers by exact id (`_model_of(value) != calibration.model`), so the answers of an older harness, whose ids differ, would never go. It prunes by lineage instead: `_lineage(id) = id.partition("@")[0]`, and an entry goes when its lineage equals the finished run's, where an entry whose `model` is not a string has none and stays. A `claude-code:` id's lineage is `claude-code:<name>`, so the older harnesses of that name go and other models stay. A stub or `anthropic:` id holds no `@`, so it is its own lineage and behaves as before; a stub path with an `@` only widens the prune to ids that share its prefix, which costs a re-ask and never a wrong answer. Until a run finishes, the older answers sit unused under their old keys.

**Shared decoding (extracted from `Claude.ask`).** `ClaudeCode.ask` would repeat the tail of `Claude.ask`, so Step 1 extracts two helpers in `judge/__init__.py` as a pure refactor, and both models call them:

- `_decode(model_id, asked, read)`: `try: return _verdict(_from_line_one(read()))`, and on `(ValueError, TypeError, KeyError, RecursionError)` raise `JudgeError` `the model {model_id} gave a malformed answer to {asked}: {error}`. `read` is a zero-argument callable (`lambda: json.loads(text)` for `Claude`, `lambda: reply["structured_output"]` for `ClaudeCode`), because both parse steps raise the errors the helper catches; a parsed payload would raise outside its `try`.
- `_bound(kind, model_id, asked, name, answered)`: when `answered != [name]`, raise `JudgeError` `the model {model_id} answered {asked} as {names}: set EARNEST_JUDGE={kind}:{that}`, where `names` is the sorted answerers joined by commas (or `no model`) and `that` is the one answerer, else `<that id>`. For `Claude` (`kind` `anthropic`, `answered` `[reply.model]`) the text equals today's message, which `test_judge_anthropic.py` pins; for `ClaudeCode` (`answered` the sorted keys of `modelUsage` when that is a dict, and none otherwise, so a missing or non-dict `modelUsage` reads as `no model`) a single wrong key now names itself in the message, as Step 5 says.

**Files:** Create `packages/earnest/tests/unit/test_judge_claude_code.py` (Step 2 lists it) and `docs/superpowers/plans/2026-11-25-spikes/spike-g-live-check.sh` (already written with this plan); Modify `packages/earnest/src/earnest/judge/__init__.py` (the model, `_run_claude`, `_decode`, `_bound`, `load_model`'s two messages and docstring), `packages/earnest/src/earnest/cli.py` (`_keep_calibration` only), `packages/earnest/tests/conftest.py` (`fake_executable`, hoisted from `fake_python`; the first plan to land does the hoist, and a later one uses it) and `packages/earnest/tests/unit/test_impact.py` (`fake_python` goes; its callers call `fake_executable`); Test `packages/earnest/tests/unit/test_cli.py`, `packages/earnest/tests/unit/test_judge_anthropic.py` (one message pattern, and its existing tests are the proof of `_decode` and `_bound`); Doc `docs/demo/m6-calibrate.md`, `.claude/skills/verify-earnest/features/judge.md`, `docs/design/01-logic-design.md`. `pyproject.toml` and `uv.lock` do not change: `os`, `shutil`, `subprocess` and `tempfile` are standard library.

**Interfaces:**

- Consumes: `load_model(value, root)`, `question_text`, `_SCHEMA`, `_verdict`, `_from_line_one`, `MAX_TOKENS`, `JudgeError`, and `digest` (from `earnest.index`) and `canonical` (from `earnest.reporter`), both already imported.
- Produces: `@dataclass(frozen=True) class ClaudeCode` with `id` (the harness-bearing id above), `model` (the bare name, for `--model` and the `modelUsage` check), `root`, `claude` (the executable's path) and `ask(question) -> Verdict`; `_claude_code(value, root)`, which finds `claude` with `shutil.which`, runs `claude --version` (30 seconds, the same environment) and builds the id; `_claude_env()`, the allowlisted environment that the version call and `ask` share; `_run_claude(argv, *, input, cwd, timeout)`, the one `subprocess.run` that they share too, which raises the underlying error for each caller to word with its own prefix; `_decode` and `_bound` above; the constants `_CLAUDE_ENV`, `_CLAUDE_PIN`, `_CLAUDE_SYSTEM`, `_CLAUDE_FLAGS`, `_CLAUDE_TIMEOUT` and `_CLAUDE_VERSION_TIMEOUT`; a `load_model` branch for `claude-code:<name>` beside `anthropic:`.

**Spike artifact:**

| File in [2026-11-25-spikes/](2026-11-25-spikes/README.md) | What it is                                                                                                                                            |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `spike-g-live-check.sh`                                   | the one-call live check of Step 5, adapted from the spike's `drive.py`: it saves no record, makes one call and prints what the 20-call run depends on |

- [ ] **Step 1 [agent]:** Extract `_decode` and `_bound` from `Claude.ask`: a pure refactor, so the tests that exist are its proof. From `packages/earnest/` run `uv run pytest tests/unit/test_judge_anthropic.py tests/unit/test_judge.py tests/unit/test_cli.py -q` and record the counts. In `judge/__init__.py`, add `Callable` to the `TYPE_CHECKING` import of `collections.abc`, and after `_from_line_one` add:

  ```python
  def _decode(model_id: str, asked: str, read: Callable[[], object]) -> Verdict:
      """Return the verdict that `read` gives, or raise when what it gives is not one."""
      try:
          return _verdict(_from_line_one(read()))
      except (ValueError, TypeError, KeyError, RecursionError) as error:
          msg = f"the model {model_id} gave a malformed answer to {asked}: {error}"
          raise JudgeError(msg) from error


  def _bound(kind: str, model_id: str, asked: str, name: str, answered: Sequence[str]) -> None:
      """Bind the cache and the calibration to the model that answers: any answerer but `name` cannot run."""
      if list(answered) != [name]:
          names = ", ".join(sorted(answered)) or "no model"
          that = answered[0] if len(answered) == 1 else "<that id>"
          msg = f"the model {model_id} answered {asked} as {names}: set EARNEST_JUDGE={kind}:{that}"
          raise JudgeError(msg)
  ```

  In `Claude.ask`, the `if reply.model != name:` block becomes `_bound("anthropic", self.id, asked, name, [reply.model])`, and the closing `try` block becomes `return _decode(self.id, asked, lambda: json.loads(text))`. Run the same three files again: expect the recorded counts, all green, no test changed. Then `rtk proxy uv run mypy --strict src/; echo $?` and `rtk proxy uv run ruff check src/; echo $?`: expect `0` from each.

- [ ] **Step 2 [agent]:** Tests first. Hoist `fake_python` (`tests/unit/test_impact.py:91-95`) into `tests/conftest.py` as `fake_executable(directory, name, script)`: it writes `#!/bin/sh` and the script to `directory/name`, marks it executable and returns the path as a string. `test_impact.py` imports it, and its five uses of `fake_python` (lines 99, 105, 111, 119 and 764) call `fake_executable(tmp_path, "python", script)`; if another plan has landed the hoist first, use it and skip this part. Then create `packages/earnest/tests/unit/test_judge_claude_code.py`. It needs no login, no network and no real `claude`: a fake `claude` on `PATH` records how it was run and prints what a test says. The fake's Python body sits beside its `sh` wrapper in `bin/` and finds `spec.json` and `record.json` beside itself; it answers `--version` before it writes the record, so `ran()` reports the last question's run. Spike G measured this file (29 tests, all passing); the listing is that file adapted to `fake_executable`, `--setting-sources user`, the Bedrock allowlist and the harness-bearing id:

  ```python
  """Unit tests for the `claude-code:` judge model, with a fake `claude` on PATH: no test needs a login or the network.

  The success reply follows the documented `--output-format json` result (structured_output, modelUsage); the failure
  reply is the shape `claude` printed on the spike's host when the provider refused the call.
  """

  import json
  import os
  import re
  import sys
  from pathlib import Path

  import pytest

  from earnest import judge
  from tests.conftest import fake_executable
  from tests.unit.test_judge_anthropic import VERDICT, question


  NAME = "claude-opus-5-5"
  MODEL = f"claude-code:{NAME}"
  FAKE = """\
  import json, os, sys, time

  here = os.path.dirname(os.path.abspath(__file__))
  spec = json.load(open(os.path.join(here, "spec.json")))
  if sys.argv[1:] == ["--version"]:
      time.sleep(spec["version_sleep"])
      print(spec["version"])
      sys.exit(spec["version_exit"])
  record = {"argv": sys.argv[1:], "stdin": sys.stdin.read(), "cwd": os.getcwd(), "listing": os.listdir("."),
            "env": dict(os.environ)}
  open(os.path.join(here, "record.json"), "w").write(json.dumps(record))
  time.sleep(spec["sleep"])
  sys.stdout.write(spec["stdout"])
  sys.stderr.write(spec["stderr"])
  sys.exit(spec["exit"])
  """


  class FakeClaude:
      """A `claude` executable that records how it was run and prints what a test says."""

      def __init__(self, folder: Path) -> None:
          """Keep the folder that holds the executable, its spec and its record."""
          self.folder = folder

      def says(
          self, stdout: object = "", *, exit: int = 0, stderr: str = "", sleep: float = 0,  # noqa: A002
          version: str = "claude 9.9.9 (fake)", version_exit: int = 0, version_sleep: float = 0,
      ) -> None:  # fmt: skip
          out = stdout if isinstance(stdout, str) else json.dumps(stdout)
          spec = {"stdout": out, "exit": exit, "stderr": stderr, "sleep": sleep,
                  "version": version, "version_exit": version_exit, "version_sleep": version_sleep}  # fmt: skip
          (self.folder / "spec.json").write_text(json.dumps(spec))

      def ran(self) -> dict:
          return json.loads((self.folder / "record.json").read_text())


  @pytest.fixture
  def claude(tmp_path, monkeypatch):
      folder = tmp_path / "bin"
      folder.mkdir()
      (folder / "fake_claude.py").write_text(FAKE, encoding="utf-8")
      fake_executable(folder, "claude", f'exec "{sys.executable}" "{folder}/fake_claude.py" "$@"')
      monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
      fake = FakeClaude(folder)
      fake.says(answer())
      return fake


  def answer(model=NAME, verdict=VERDICT, **more):
      reply = {
          "type": "result",
          "subtype": "success",
          "is_error": False,
          "terminal_reason": "completed",
          "num_turns": 2,
          "result": "",
          "structured_output": verdict,
          "modelUsage": {model: {"inputTokens": 900, "outputTokens": 40}},
      }
      return {**reply, **more}


  API_FAILURE = {  # what `claude -p --output-format json` printed, with exit 1, when the provider refused the call
      "type": "result",
      "subtype": "success",
      "is_error": True,
      "terminal_reason": "api_error",
      "api_error_status": 403,
      "api_error": "provider_credentials",
      "num_turns": 1,
      "result": "AWS authentication failed · API Error: 403 not authorized to perform: bedrock:InvokeModel",
      "modelUsage": {},
  }


  def ask(tmp_path):
      return judge.load_model(MODEL, tmp_path).ask(question(tmp_path))


  def test_a_claude_code_value_loads_a_model_whose_id_holds_the_harness(tmp_path, claude):
      loaded = judge.load_model(MODEL, tmp_path)
      assert re.fullmatch(rf"{MODEL}@claude 9\.9\.9 \(fake\); flags sha256:[0-9a-f]{{64}}", loaded.id)
      assert loaded.model == NAME
      assert ask(tmp_path).result == "not-satisfied"


  def test_the_question_goes_in_on_stdin_and_the_command_line_is_exactly_the_flags_the_id_hashes(tmp_path, claude):
      asked = question(tmp_path)
      judge.load_model(MODEL, tmp_path).ask(asked)
      ran = claude.ran()
      assert ran["stdin"] == judge.question_text(tmp_path, asked)
      argv = ran["argv"]
      assert argv[:3] == ["-p", "--model", NAME]
      assert argv[3:] == list(judge._CLAUDE_FLAGS)  # a flag `ask` adds outside `_CLAUDE_FLAGS` would escape the digest
      assert json.loads(argv[argv.index("--json-schema") + 1]) == judge._SCHEMA
      assert argv[argv.index("--system-prompt") + 1] == judge._CLAUDE_SYSTEM
      assert argv[argv.index("--tools") + 1] == ""  # no tools at all
      assert {"--safe-mode", "--no-session-persistence"} <= set(argv)
      assert argv[argv.index("--setting-sources") + 1] == "user"
      assert "--restricted" not in argv
      assert argv[argv.index("--permission-prompts") + 1] == "none"
      assert "When a member logs in" not in " ".join(argv)  # the repository's text never rides the command line


  def test_claude_runs_in_an_empty_directory_that_is_removed_afterwards(tmp_path, claude):
      ask(tmp_path)
      ran = claude.ran()
      assert ran["listing"] == []
      assert Path(ran["cwd"]).resolve() != tmp_path.resolve()
      assert not Path(ran["cwd"]).exists()


  def test_only_allowlisted_variables_reach_claude(tmp_path, claude, monkeypatch):
      forbidden = {
          "ANTHROPIC_API_KEY": "key",
          "ANTHROPIC_AUTH_TOKEN": "bearer",
          "ANTHROPIC_BASE_URL": "https://example.invalid",
          "ANTHROPIC_MODEL": "other",
          "CLAUDE_CODE_OAUTH_TOKEN": "subscription-token",
          "CLAUDE_CODE_EFFORT_LEVEL": "low",
          "CLAUDECODE": "1",
          "CLAUDE_CODE_CHILD_SESSION": "1",
          "EARNEST_JUDGE": MODEL,
      }
      for name, value in forbidden.items():
          monkeypatch.setenv(name, value)
      ask(tmp_path)
      env = claude.ran()["env"]
      assert not set(forbidden) & set(env)
      assert env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == str(judge.MAX_TOKENS)
      assert env["PATH"] == os.environ["PATH"]


  def test_a_structured_reply_becomes_a_verdict(tmp_path, claude):
      assert ask(tmp_path) == judge.Verdict("not-satisfied", "no greeting", "src/a.py", 3)


  def test_a_reply_at_line_0_is_read_at_line_1(tmp_path, claude):
      claude.says(answer(verdict={**VERDICT, "location": {"file": "a", "line": 0}}))
      assert ask(tmp_path).line == 1


  def test_an_api_failure_cannot_run_and_says_why(tmp_path, claude):
      claude.says(API_FAILURE, exit=1)
      with pytest.raises(judge.JudgeError, match=r"cannot answer `req~greet~1` implemented: claude exited 1: AWS auth"):
          ask(tmp_path)


  def test_an_error_reply_with_exit_0_still_cannot_run(tmp_path, claude):
      claude.says(API_FAILURE)
      with pytest.raises(judge.JudgeError, match="API Error: 403"):
          ask(tmp_path)


  def test_a_refusal_cannot_run(tmp_path, claude):
      claude.says(answer(is_error=True, stop_reason="refusal", result="I can't help with that.", structured_output=None))
      with pytest.raises(judge.JudgeError, match="I can't help with that"):
          ask(tmp_path)


  def test_a_failed_structured_output_names_its_errors(tmp_path, claude):
      reply = {"type": "result", "subtype": "error_max_structured_output_retries", "is_error": True, "result": None}
      claude.says({**reply, "errors": ["Failed to provide valid structured output after 5 attempts"]}, exit=1)
      with pytest.raises(judge.JudgeError, match="Failed to provide valid structured output"):
          ask(tmp_path)


  @pytest.mark.parametrize(("out", "code"), [("", 1), ("not json", 0), ("[]", 0), ("[]", 1)])
  def test_output_that_is_not_a_result_object_cannot_run(tmp_path, claude, out, code):
      claude.says(out, exit=code, stderr="Not logged in")
      with pytest.raises(judge.JudgeError, match=f"claude exited {code}"):
          ask(tmp_path)


  @pytest.mark.parametrize(
      ("used", "said"),
      [
          (
              {"claude-opus-5-5-20270101": {}},
              "as claude-opus-5-5-20270101: set EARNEST_JUDGE=claude-code:claude-opus-5-5-20270101",
          ),
          (
              {NAME: {}, "claude-haiku-5-5": {}},
              "as claude-haiku-5-5, claude-opus-5-5: set EARNEST_JUDGE=claude-code:<that id>",
          ),
          ({}, "as no model:"),
          (None, "as no model:"),
      ],
  )
  def test_a_reply_from_other_models_than_the_id_cannot_run(tmp_path, claude, used, said):
      claude.says({**answer(), "modelUsage": used})
      with pytest.raises(judge.JudgeError, match=said):
          ask(tmp_path)


  @pytest.mark.parametrize(
      "verdict",
      [
          None,
          "not json",
          [],
          {"result": "maybe", "reasoning": "x", "location": {"file": "a", "line": 1}},
          {"result": "satisfied", "reasoning": "x"},
          {"result": "satisfied", "reasoning": "x", "location": {"file": "a", "line": "1"}},
      ],
  )
  def test_a_malformed_structured_output_cannot_run(tmp_path, claude, verdict):
      claude.says(answer(verdict=verdict))
      with pytest.raises(judge.JudgeError, match="malformed"):
          ask(tmp_path)


  def test_a_reply_without_structured_output_cannot_run(tmp_path, claude):
      reply = answer()
      del reply["structured_output"]
      claude.says(reply)
      with pytest.raises(judge.JudgeError, match=r"malformed.*structured_output"):
          ask(tmp_path)


  def test_a_claude_that_hangs_cannot_run(tmp_path, claude, monkeypatch):
      monkeypatch.setattr(judge, "_CLAUDE_TIMEOUT", 0.5)
      claude.says(answer(), sleep=5)
      with pytest.raises(judge.JudgeError, match=r"cannot answer.*timed out"):
          ask(tmp_path)


  def test_a_claude_that_cannot_be_executed_cannot_run(tmp_path):
      asked = question(tmp_path)
      with pytest.raises(judge.JudgeError, match="cannot answer `req~greet~1` implemented"):
          judge.ClaudeCode(MODEL, NAME, tmp_path, str(tmp_path / "no-such-claude")).ask(asked)


  def test_no_claude_on_path_cannot_start(tmp_path, monkeypatch):
      monkeypatch.setenv("PATH", str(tmp_path))
      with pytest.raises(judge.JudgeError, match="cannot start: there is no `claude` executable on PATH"):
          judge.load_model(MODEL, tmp_path)


  def test_a_claude_code_value_without_a_model_name_cannot_run(tmp_path):
      with pytest.raises(judge.JudgeError, match="names no model"):
          judge.load_model("claude-code:", tmp_path)
  ```

  Then add these tests to the file, over the same fixtures:
  - **The environment.** A parametrized `test_a_bedrock_variable_reaches_claude` over the twelve variables of the table (`CLAUDE_CODE_USE_BEDROCK`, `AWS_REGION`, `AWS_DEFAULT_REGION`, `ANTHROPIC_BEDROCK_REGION_PREFIX`, `AWS_PROFILE`, `AWS_CONFIG_FILE`, `AWS_SHARED_CREDENTIALS_FILE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_BEARER_TOKEN_BEDROCK`, `AWS_EC2_METADATA_DISABLED`): each set to a marker reaches `claude` unchanged. `test_the_allowlist_is_exactly_the_documented_set`: `set(judge._CLAUDE_ENV)` equals the base variables plus those twelve, so an addition needs a test and a row.
  - **The id.** `test_a_new_claude_changes_the_id` (`says(version="claude 9.9.10 (fake)")`); `test_a_changed_flag_or_pin_changes_the_id` (monkeypatch `_CLAUDE_FLAGS` with one more flag: the id changes and the argv the fake records carries that flag; then `_CLAUDE_PIN`); parametrized `test_a_claude_without_a_version_cannot_start` matching `cannot start`, over four rows: `version_exit=1`; an empty `version`; a `--version` that sleeps (`version_sleep`) with `judge._CLAUDE_VERSION_TIMEOUT` monkeypatched to a fraction of a second, so `subprocess.TimeoutExpired` must surface as `JudgeError`; and a `claude` on `PATH` whose shebang names no interpreter, so the version call raises `OSError`; `test_a_claude_upgrade_voids_a_calibration`: a slot whose `model` is the loaded model's `id` is `calibrated` for it, and after `says(version="claude 9.9.10 (fake)")` and a second `load_model` it is not.
  - **The pruning**, in `test_cli.py`: `test_a_finished_calibration_drops_the_answers_of_an_older_harness`. The record's `judge.calibrate` holds entries whose `model` is `claude-code:m@v1; flags sha256:a`, `claude-code:m@v2; flags sha256:a`, `claude-code:other@v1; flags sha256:a` and a stub id; a calibration that finishes under `claude-code:m@v2; flags sha256:a` leaves the `other` and stub entries and its own answers, and the two `m` entries of older harnesses are gone. The existing prune test stays green.
  - **The shared helpers** need no new test: `test_judge_anthropic.py`'s existing tests pin `Claude`'s messages and must pass unchanged after Step 1, and the alias and malformed-answer tests above run `ClaudeCode` through the same helpers.
  - **The doubles** (`Counting`, `Recording`) need no change: the id-based design adds no `Model` member.
  - **The messages**, Step 4's two tests: `test_cli.py:951` (`"anthropic:<model>" in result[2]` also asserts `claude-code:<model>`) and `test_judge_anthropic.py:209` (its pattern `anthropic:<model> or stub:<path>` becomes the new order).

  Run `uv run pytest tests/unit/test_judge_claude_code.py tests/unit/test_cli.py tests/unit/test_judge_anthropic.py tests/unit/test_impact.py` from `packages/earnest/`. Expected: the new and changed tests fail (no `claude-code` branch, no `fake_executable` in `conftest.py` until it is hoisted, no lineage prune) and the rest pass.

- [ ] **Step 3 [agent]:** The backend, in `judge/__init__.py`, then the lineage prune. Spike G measured the first version (88 lines, 29 tests); this is that code with the plan's three changes: `--setting-sources user` for `--restricted`, the Bedrock allowlist, and the id that holds the harness. It calls Step 1's helpers from the start, and runs `claude` through one wrapper, `_run_claude`. Add `import os`, `import shutil`, `import subprocess` and `import tempfile` beside `import json`. In `load_model`, after the `anthropic` branch:

  ```python
      if kind == "claude-code" and path:
          return _claude_code(value, root)
  ```

  Then, after `Claude`, and before `question_text`:

  ```python
  # `claude-code:<model>`: the verdict comes from `claude -p`, logged in as the user. Only these variables reach it, so
  # billing follows the Bedrock and AWS variables below and the `env` block of the user settings, and no
  # ANTHROPIC_API_KEY of the calling session can redirect it.
  _CLAUDE_ENV = (
      "PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "CLAUDE_CONFIG_DIR",
      "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE", "NODE_EXTRA_CA_CERTS",
      "CLAUDE_CODE_USE_BEDROCK", "AWS_REGION", "AWS_DEFAULT_REGION", "ANTHROPIC_BEDROCK_REGION_PREFIX",
      "AWS_PROFILE", "AWS_CONFIG_FILE", "AWS_SHARED_CREDENTIALS_FILE",
      "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_BEARER_TOKEN_BEDROCK",
      "AWS_EC2_METADATA_DISABLED",
  )  # fmt: skip
  # max_tokens as for `Claude`; no auto-update, telemetry or feedback traffic mid-run
  _CLAUDE_PIN = {"CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(MAX_TOKENS), "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}
  _CLAUDE_SYSTEM = "You are a code reviewer. Follow the user's instructions exactly."  # replaces Claude Code's own prompt
  # every flag but the model name; `ask` builds its argv from it and the id hashes it, so the two cannot differ
  _CLAUDE_FLAGS = (
      "--effort", "high", "--output-format", "json", "--json-schema", json.dumps(_SCHEMA),
      "--tools", "",  # none: the question text is all the judge sees, and only the schema's StructuredOutput remains
      "--safe-mode",  # no CLAUDE.md, skills, plugins, hooks, MCP servers or auto memory
      "--setting-sources", "user",  # the user's `env` block and `awsCredentialExport`, no project or local settings
      "--no-session-persistence", "--permission-prompts", "none", "--system-prompt", _CLAUDE_SYSTEM,
  )  # fmt: skip
  _CLAUDE_TIMEOUT = 900  # seconds for one question
  _CLAUDE_VERSION_TIMEOUT = 30  # seconds for `claude --version`


  def _claude_env() -> dict[str, str]:
      """Return the allowlisted variables the caller has set, and the two pins; `claude` gets nothing else."""
      return {key: os.environ[key] for key in _CLAUDE_ENV if key in os.environ} | _CLAUDE_PIN


  def _run_claude(
      argv: list[str],
      *,
      input: str | None = None,  # noqa: A002  # the name of `subprocess.run`'s own parameter
      cwd: str | None = None,
      timeout: float,
  ) -> subprocess.CompletedProcess[str]:
      """Run `claude` under the allowlisted environment with its output captured; the caller words any error it raises."""
      return subprocess.run(  # noqa: S603  # argv is a list; the question goes in on stdin, never the command line
          argv, input=input, capture_output=True, text=True, cwd=cwd, env=_claude_env(), timeout=timeout, check=False
      )


  def _claude_code(value: str, root: Path) -> ClaudeCode:
      """Return the `claude-code:` model; `claude` holds its own login, and earnest reads no key.

      Raises:
          JudgeError: there is no `claude` on PATH, or `claude --version` fails, is empty or times out.
      """
      if (path := shutil.which("claude")) is None:
          msg = f"the model {value} cannot start: there is no `claude` executable on PATH"
          raise JudgeError(msg)
      try:
          done = _run_claude([path, "--version"], timeout=_CLAUDE_VERSION_TIMEOUT)
      except (OSError, subprocess.SubprocessError) as error:  # TimeoutExpired is a SubprocessError, not an OSError
          msg = f"the model {value} cannot start: {error}"
          raise JudgeError(msg) from error
      version = done.stdout.strip()
      if done.returncode != 0 or not version:
          msg = f"the model {value} cannot start: `claude --version` exited {done.returncode} and printed {version!r}"
          raise JudgeError(msg)
      name = value.partition(":")[2]
      flags = digest(canonical({"flags": [*_CLAUDE_FLAGS], "pin": _CLAUDE_PIN}).encode())
      return ClaudeCode(f"claude-code:{name}@{version}; flags {flags}", name, root, path)


  @dataclass(frozen=True)
  class ClaudeCode:
      """A Claude model through Claude Code's `claude -p`; `id` holds the `claude` version and the flags' digest."""

      id: str
      model: str
      root: Path
      claude: str

      def ask(self, question: Question) -> Verdict:
          """Send the question's text on stdin and return the model's structured verdict.

          Raises:
              JudgeError: `claude` cannot run or fails, another model answers, or its reply is not a verdict.
          """
          asked = f"`{question.subject}` {question.kind}"
          text = question_text(self.root, question)
          argv = [self.claude, "-p", "--model", self.model, *_CLAUDE_FLAGS]
          try:
              with tempfile.TemporaryDirectory(prefix="earnest-judge-") as empty:  # nothing there for it to discover
                  done = _run_claude(argv, input=text, cwd=empty, timeout=_CLAUDE_TIMEOUT)
          except (OSError, subprocess.SubprocessError) as error:
              msg = f"the model {self.id} cannot answer {asked}: {error}"
              raise JudgeError(msg) from error
          try:
              reply = json.loads(done.stdout)
          except ValueError:
              reply = None
          if not isinstance(reply, dict) or done.returncode != 0 or reply.get("is_error"):
              # an API failure is `is_error` under `subtype: success`, its text in `result`; an `error_*` subtype has `errors`
              why = (
                  (reply.get("result") or reply.get("errors") or reply.get("subtype"))
                  if isinstance(reply, dict)
                  else done.stderr
              )
              msg = (
                  f"the model {self.id} cannot answer {asked}: claude exited {done.returncode}: {str(why).strip()[:300]}"
              )
              raise JudgeError(msg)
          used = reply.get("modelUsage")  # an alias, or a fallback: bind to the models that answer
          _bound("claude-code", self.id, asked, self.model, sorted(used) if isinstance(used, dict) else [])
          return _decode(self.id, asked, lambda: reply["structured_output"])
  ```

  `digest` (from `earnest.index`) and `canonical` (from `earnest.reporter`) are already imported; `digest` takes bytes, hence `.encode()`.

  Then `cli._keep_calibration`'s lineage prune, as the section above says. Run the four files, then the regression run (`uv run pytest --ignore=tests/steps/test_calibration_gate.py`) and `uv run pytest tests/steps/test_calibration_gate.py`. Expected: all green except the two message tests of Step 2 (`test_cli.py:951` and `test_judge_anthropic.py:209`), which only Step 4 makes pass, with no existing test changed beyond Step 2's; record the exact counts against the same runs before the task. `git diff --stat` for `Model`, `Stub`, `Cache`, `Calibration`, `slot`, `calibrated` and `_comparison` shows no change.

- [ ] **Step 4 [agent]:** The two `load_model` messages and its docstring. The unset one becomes `earnest needs a model: set EARNEST_JUDGE to anthropic:<model>, claude-code:<model> or stub:<path of a canned-verdict file>`, and the unknown one `EARNEST_JUDGE names no model Earnest knows: {value!r}; use anthropic:<model>, claude-code:<model> or stub:<path>`. A `claude-code:` value with no name after the colon falls to the unknown-model message, as `anthropic:` does (the spike has `test_a_claude_code_value_without_a_model_name_cannot_run`).
- [ ] **Step 5 [agent, on this host]:** The live check, ONE real call and the step before the 20-call run. It bills one question to the account of "Billing", and it is covered by Decision 1. The spike's two real calls reached Bedrock and neither got an answer: call 2 was refused with a 403 for the host's EC2 instance profile role because `--restricted` had dropped the user settings (the `env` block and `awsCredentialExport`; see Change 1). Separately, the agent's permission classifier stripped provider variables from call 2's environment (it held only `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS`, `HOME`, `LANG` and `PATH`). If the classifier blocks this call, the maintainer runs the command. From `packages/earnest/`, on a host where Claude Code is logged in to Bedrock:

  ```bash
  EARNEST_JUDGE=claude-code:claude-opus-5-5 rtk proxy bash ../../docs/superpowers/plans/2026-11-25-spikes/spike-g-live-check.sh; echo "exit=$?"
  ```

  It asks `req~daily-cap~1` `implemented` of the synthetic `calibration-dev` fixture and prints the id (which holds the harness), the argv, the NAMES of the variables that reached `claude` (never their values), `claude`'s exit and wall time, the `modelUsage` keys, `num_turns`, `usage` and `total_cost_usd`, the verdict beside the maintainer's, and the path of the raw output. Its verdict need not match the maintainer's: this is a plumbing check, and its `match` line is informational. It passes when all of these hold; paste its output on #29:
  - `claude exit=0`, `is_error` false and `terminal_reason` `completed`, and a `verdict` line (exit `0` of the script);
  - `modelUsage` has exactly one key, equal to the selector's name. If it has one key that differs, follow "The model id may need the Bedrock form", then run the check again; if it has two, a fallback model answered, and the run stops there for the maintainer;
  - the `env names` line holds the Bedrock variables the host sets and no `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` or `CLAUDE_CODE_OAUTH_TOKEN`.

  A failure maps to a cause. A 403 that names the EC2 instance profile role, or an `us.` prefix when the user's settings say `global`, means the user settings did not load: the flag pair is the suspect (Change 1), and the maintainer rules between `--settings` carrying `awsCredentialExport` and dropping `--safe-mode`, because the plan does not guess. A 403 that names the user's own role means the credentials loaded and lack Bedrock access for the model: that is the account's, not the backend's. "Not logged in" means no login on this host. An unknown-flag error means a `claude` newer or older than 2.1.330.1791: record the version and read `claude --help`.

- [ ] **Step 6 [agent]:** Replace the one line of "Cost estimate for one real run" with the live check's measured numbers (wall time per call, `num_turns`, input and output tokens, and the account's usage), and the run's length computed from them.
- [ ] **Step 7 [agent]:** `docs/demo/m6-calibrate.md`: rerun `docs/demo/m6-calibrate.sh` and paste its output over the document's captured run, because the unset-model line (line 114 today) carries the old message. `test_judge.py` pins the document's prompt hash and nothing else.
- [ ] **Step 8 [agent]:** `.claude/skills/verify-earnest/features/judge.md`, line 24 (the "No model" case): the expected stderr becomes Step 4's unset message.
- [ ] **Step 9 [agent]:** `docs/design/01-logic-design.md`: the judge cache key paragraph (lines 743 to 746) needs no new part, since the key holds the model id; the paragraph on `EARNEST_JUDGE` (lines 1674 to 1690) names `claude-code:<model>`, that its id is `claude-code:<model>@<claude --version>; flags <digest>` and so binds the version, and the Bedrock billing; the row "Judge model choice and prompt" (line 1700) notes that the SC4 run used `claude-code:claude-opus-5-5`, the same model by another transport. `02` needs no change: L4 names the model SDKs, and this backend uses the standard library.
- [ ] **Step 10 [agent]:** From the repository root run `rtk proxy make lint; echo $?` and `rtk proxy make test; echo $?`; both must print `0`. Run `LINT_FILE=<path> make lint-file` on each Markdown file touched. Commit `feat: the claude-code judge model`, staging the paths of this task by name and never with `--no-verify`; the live check's output goes on #29, not into a commit.

Done when:

- Steps 1 to 4 and 7 to 10 are done, the regression run, `tests/steps/test_calibration_gate.py` and both makes are green, and the new tests need no login, no network and no `claude` on the real `PATH`;
- the stub model's behavior and every stub key and slot are unchanged: the BDD gate's tables of `04` did not move, and `Model`, `Cache`, `Calibration`, `slot`, `calibrated` and `_comparison` are untouched;
- Step 5 passed on this host and its output is on #29, with the `claude --version` line that the SC4 run will record;
- "Cost estimate for one real run" carries the live check's numbers, and the #29 commands below carry `claude-code:`.

Unverified until Step 5, because no call has returned an answer: the `modelUsage` key on Bedrock; that `--setting-sources user` with `--safe-mode` applies the user's `awsCredentialExport` and `env` block; that `--effort high` and the pins behave as under the API; how many model requests one question makes (the documented result shows `num_turns` 2) and so its tokens; the wall time of a call; and Bedrock's price for the model, which this plan has not read.

The SC4 run (issue #29) starts only after this task lands and Step 5 has passed.

### The SC4 run: issue #29

Depends on #28 landing on the branch it runs from, and on Task 7b. Run from `packages/earnest/`.

- [ ] **Step 1 [maintainer]:** The run is approved (Decision 1); run it on this host, with Claude Code logged in to Bedrock, once #28 and Task 7b have landed (Task 7b's Step 5, the one-call live check, has passed on this host). The run bills the AWS account Claude Code is configured for. Check that `tests/fixtures/calibration/verdicts.json` exists and that `git status` shows `src/earnest/judge/prompt.txt` unmodified, since its hash binds the pass. Note `claude --version`: the pass binds it, and a `claude` upgrade between the run and a later `check --judge` makes the judge uncalibrated again.
- [ ] **Step 2 [agent]:** Run the free dry run: the stub command of #28's exit criterion above, expecting exit 0 and `matches: 10/10`. It proves the fixture before any money is spent.
- [ ] **Step 3 [maintainer]:** Run the gate, with output kept for the record.
- [ ] **Step 4 [maintainer]:** Read the table: ten requirements, the judge's pair beside the maintainer's, and `matches: <n>/10`. Exit 0 is a pass (8 or more), 1 a fail, 2 means it could not run (a provider error, a refusal, a malformed reply, an alias or another `modelUsage` key, or a missing `claude`). On a 2 the `calibration` slot is not written, but the answers already given are kept in the record, so the retry asks only the rest. Confirm the record, and keep the `jq` output with the captured table, because `.earnest/` is gitignored. The table's first line names the `claude` version the pass binds.
- [ ] **Step 5 [agent]:** Prove that `judge-uncalibrated` is quiet for this model, prompt and `claude`. The free form loads the model (it runs `claude --version`, no model call) and checks the slot with the function `check --judge` uses. It prints `True` on a pass, and `False` if `claude` was upgraded since the run.
- [ ] **Step 6 [agent]:** On a pass, write it down: the M6 entry of `03` (SC4 done, with the date, model id, prompt hash, `claude` version and match count, and the "SC4 real-model run is unrun" sentence of its Development fixture bullet replaced); the "Judge model choice and prompt" row of `01` (the gate confirmed the choice, with the result); and this plan's last two Known limits bullets, Task 1's boxes and Task 6 Step 3. Run `LINT_FILE=<path> make lint-file` on each. The maintainer comments on #29 and closes #28 and #29.
- [ ] **Step 7 [maintainer]:** On a fail (fewer than 8), reopen the "Judge model choice and prompt" row of `01`. Do not edit `verdicts.json` to fit the judge's answers. Change the prompt (a new hash) or the model (a new id), and run again; each run costs about as much as the first. The slot keeps the latest result, so a failing run replaces an earlier pass, and the run is recorded on the issue either way.

```bash
# no API key (Decision 1): Claude Code, logged in to Bedrock on this host, answers through the claude-code: backend of Task 7b
OUT="$(mktemp -d)/sc4-run.txt"
EARNEST_JUDGE=claude-code:claude-opus-5-5 rtk proxy uv run earnest calibrate tests/fixtures/calibration > "$OUT"; echo "exit=$?"
cat "$OUT"
jq .calibration ../../.earnest/assessment.json
```

```bash
EARNEST_JUDGE=claude-code:claude-opus-5-5 uv run python -c 'import json, os; from pathlib import Path; from earnest import judge; s = json.load(open("../../.earnest/assessment.json"))["calibration"]; print(judge.calibrated(s, judge.load_model(os.environ["EARNEST_JUDGE"], Path("."))))'
```

If Task 7b's live check had to use another `<model>` (the Bedrock form of the id), use that value in both commands and in the record below. The paid form of Step 5 is not run (Decision 8); it would be `EARNEST_JUDGE=claude-code:claude-opus-5-5 rtk proxy uv run earnest check --judge > sarif.json; echo $?`, then `grep -c judge-uncalibrated sarif.json`, expecting 0. It would add 26 more calls (13 judgeable requirements, two questions each, as measured 2026-11-25), and the maintainer declined it (Decision 8).

Done when:

- the record holds `{"model": "claude-code:claude-opus-5-5@claude <version>; flags sha256:…", "prompt": "sha256:94db4a9d…", "matches": <8 to 10>, "total": 10, "pass": true}` and the run's table is on the issue;
- Step 5 prints `True` (or the paid `check --judge` shows no `judge-uncalibrated`);
- the M6 entry of `03` notes that the SC4 run is done.

### Maintainer-only decisions

An agent may not make these for the maintainer. Each is DECIDED (user, 2026-11-25) below, except Decision 6.

1. **Spend and credentials.** Reference: 20 calls a run, and the same again for every rerun. **DECIDED (user, 2026-11-25):** the real SC4 run (#29) is APPROVED, with no `ANTHROPIC_API_KEY`. The judge calls Claude through Claude Code programmatically (`claude -p`, on the subscription plan), or through the Claude Agent SDK if needed. **Later the same day (user):** the run happens on this host, where Claude Code authenticates to Amazon Bedrock, so the spend is Bedrock usage on the AWS account Claude Code is configured for and not subscription usage; Task 7b's allowlist forwards the Bedrock and AWS variables; and a passing `claude-code:` calibration satisfies SC4, its slot and cache key recording the `claude` version and a hash of the flags and system text. The user needs Claude Code logged in to Bedrock on this host once the fixture and Task 7b are ready. A rerun after a fail spends that usage again, and the user approves it when it arises.
2. **The new pin.** Accept `aff94e3c0ba5667645c5779bbd5b80baf715fc10`, the `main` as read on 2026-11-25, in place of the unresolvable `ef5b737`, and confirm the 2026-10-26 approval to publish excerpts covers files taken from it. Also supply the client and project names for the redaction scan, and rule on each hit: redact or drop. **DECIDED (user, 2026-11-25):** pin apartment-twin `aff94e3` (`aff94e3c0ba5667645c5779bbd5b80baf715fc10`), and the user approved cloning it, read-only, for a real-world run. The client and project names for the redaction scan are not yet supplied; Step 4 stops on a hit and asks for them.
3. **Which ten of the fifteen,** with the two alternates. **DECIDED (user, 2026-11-25):** an agent drafts the choice and the user approves it.
4. **The EARS rewrite of each, the tags and where each region begins and ends.** Nine of the fifteen need more than lowercasing `SHALL`. **DECIDED (user, 2026-11-25):** an agent drafts the rewrites, the tags and the regions, and the user approves them.
5. **The twenty verdicts,** at least three `not-satisfied` over at least three requirements, written before the real run and never changed to fit its output. **DECIDED (user, 2026-11-25):** the user writes the twenty verdicts; an agent does not. The slot does not bind the fixture's content (Known limits), so an edit after a pass leaves the judge calibrated until `calibrate` runs again.
6. **Rulings after the run.** The match compares `result` alone, so a judge that is right for the wrong reason still matches: the maintainer reads the reasoning. On a fail, whether to reword the prompt, change the model or accept the result, and whether a disagreement is the judge's error or the maintainer's. Still open by nature: the maintainer rules once the run's table exists.
7. **Which fixture the BDD gate uses.** **DECIDED (user, 2026-11-25):** it stays on `calibration-dev`. Repointing it needs `stub-pass.json` and `stub-fail.json` for the real fixture and the tables of `04` redone.
8. **The paid `check --judge`.** **DECIDED (user, 2026-11-25):** no paid `check --judge`; the free slot check of Step 5 is enough.
