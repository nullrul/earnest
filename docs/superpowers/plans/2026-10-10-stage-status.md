# M2 `stage_status` Implementation Plan

Status: ratified — design committed at cf7f8d4 (RP1-RP10, RP7 addendum items 1-11, 8a); M2b `unit_status` is a later milestone

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the stage engine to `earnest`: `earnest plan` prints the route (read from the intent's Stage Progress) with each stage's computed status, approval and the frontier; `earnest check --stage` prints the assessment hash and writes the run header to the assessment record; and after a revision bump a check flags the tag, edge and approval left at the old revision and a body edited without a bump, each at its stage position. A route with per-unit stages is refused with exit 2.

**Architecture:** The Container pipeline of `01` gains its second half. The scanner hands `index.py` more per file (code lines, a digest, a line count) and skips the files AI-DLC writes inside a record directory; `index.py` adds each item's body hash and the Region rule. `structural.py` applies the route rule and raises `unbumped-change` against the hashes a counting approval froze. `plan.py` reads each record directory's `aidlc-state.md` and every `audit/*.md` shard itself, by raw read, orders the audit rows, applies the attempt, jump, skip and rejection rules, builds the route, approvals and frontier, computes status, `unplanned`, `cycle`, `route-mismatch`, the stale-approval notes and every finding's position, and builds the assessment document whose hash a stage check records. `git.py` lists the changed paths from one lock-free `git status`, and `plan.py` filters them by the evaluated-tree rule to decide `dirty`. `reporter.py` owns the record (canonical JSON, atomic write) and renders positions, `properties.plan` and `properties.assessment`; it receives plain data and imports from neither `structural.py` nor `plan.py`. `cli.py` wires `plan`, `--stage` and `--intent` and refuses a per-unit route. The behavior feature over `seeded-change` is written first and stays red until Task 12.

**Tech Stack:** Python 3.12 standard library at runtime (`json`, `hashlib`, `os`, `posixpath`, `tempfile`, `datetime`, `re`, `subprocess`, `dataclasses`, `typing`); pytest 9 with pytest-bdd 8.1 and pytest-cov; uv with hatchling; ruff, `mypy --strict`, vulture. No new dependency.

**Spec:** `docs/design/03-implementation-plan.md`, milestone M2 `stage_status`, and the sections its Context to load names in `docs/design/00-project-intent.md`, `docs/design/01-logic-design.md` and `docs/design/02-structural-design.md`; the scenarios are those of M2 in `docs/design/04-bdd-test-plan.md`. All four are committed at cf7f8d4 in their ratified form. The design record is `.pi-herdsman/m2/` (`rp7-addendum.md`, `rp7-upstream.md`, `rp7-upstream-2.md`, `01-02-revision-proposal.md`, `proposed-decisions.md`, `task-plan-proposal.md` revision 7).

## Global Constraints

- Every path matches the File and directory tree of `02`: modules under `packages/earnest/src/earnest/`, tests under `packages/earnest/tests/`.
- The runtime is the standard library alone (L4); M2 adds no dependency.
- Lint bar (L1): ruff at "line length 120, complexity 10, five arguments, Google docstrings" (PLR0913 counts keyword-only parameters, so every function takes at most five), `ruff format`, `mypy --strict` over `src/`, vulture at `min_confidence = 80`; `make lint` runs all four. Optional run inputs travel in the frozen dataclass `reporter.Run`, and no parameter or field shadows a builtin (A002, A003), so a digest is `digest`, never `hash`. `cli.main` and `plan.py` functions stay under complexity 10 by splitting into helpers.
- Platforms: macOS and Linux only.
- `earnest plan` is read-only. `earnest check` writes nothing without `--stage`. `check --stage` writes only the `.earnest/` directory (the record, its `.gitignore` marker holding `*`, and a temporary file), as ratified under RP1. The one `git status` call runs with `--no-optional-locks`, so `plan` and plain `check` leave `.git/index` untouched and take no `index.lock`.
- Exit codes: 0 when no error-level finding sits at position behind or current, 1 when one does, and 2 when the command cannot run: Git cannot answer, a file or the record cannot be read or written, the record is corrupt or newer, `--intent` names a record directory that does not exist, `--stage` has no intent to use (no record directory, or several and no `--intent`), is ambiguous (a bare slug that several route stages share) or names a stage that is not on the route, the selected intent's route holds per-unit stages, or a reader of stdout or stderr goes away (B7). A stage's computed status sets no exit code (RP10). The exit code of `check --stage S` is set by the findings that run reports: those counting against S plus those that reach no stage (Command surface), at error level and position behind or current (PD9 (e)).
- The unsupported-route line is exactly `earnest: unsupported route: units-generation is on the route, so per-unit stages`, on stderr, with empty stdout, and nothing is written (RP7 1(j)).
- A finding that reaches no stage has position `current`, omits `properties.stage` and opens its message with `in scope:`; a repository with no intent record directory has no plan, so every finding keeps that form and M1's `trace_check` stays green. A finding's message opens with its position (the position paragraph of SARIF 2.1.0): `regression in approved stage <stage>:` for behind, `in scope at <stage>:` for current with a stage, and `expected at <stage>:` for ahead (level note), each followed by a space.
- The record directory of an intent is the directory that holds an `aidlc-state.md`, normally `aidlc/spaces/<space>/intents/<YYMMDD>-<label>/`. A stage id is `<phase>/<slug>`: the heading `### INCEPTION PHASE` gives `inception`, and the slug is the Stage Progress row's token. Stage artifacts sit at `<record>/<phase>/<slug>/`.
- The route (RP7 1(a), (h), (i)) is the Stage Progress rows marked EXECUTE outside the initialization phase, in row order, less each stage that a counting `STAGE_SKIPPED` row skips. The checkbox marks are never read as status; every row marked EXECUTE and skipped (`[S]`) with no counting `STAGE_SKIPPED` row, an Initialization row included (Findings; Frontier and position), raises `earnest/route-mismatch` (error, reaches no stage, located at the row of the state file) and, outside the Initialization phase, stays on the route. A line under `## Stage Progress` that starts `- [` and is no row Earnest can read, and a state file with no Stage Progress row at all, raise the same error-level `earnest/route-mismatch`, at that line (at the heading's line, or line 1 without one), so a route that a mistyped row or a renamed heading would shrink silently fails every command and holds the gate instead. A row ends after `EXECUTE` or `SKIP`, or goes on with a colon or a space and a reason.
- Audit rows (RP7 1(c)): every `<record>/audit/*.md` shard, blocks split at the lines that are exactly `---`, fields as `**Field**: value`, the first `Timestamp` per block, the `Event` field names the event; total order by timestamp, then shard file name, then position in the shard. A row for a stage counts only if it follows the latest `WORKFLOW_STARTED` and every `STAGE_JUMPED` whose reset span includes the stage. The span (from the current Stage Progress rows): BACKWARD resets its Target and every later row marked EXECUTE, skipped marks included; REDO resets its Target; FORWARD resets none. The rule applies to approval, rejection and skip rows alike.
- Approval (RP7 1(d), RP9): the approval of a stage is the latest counting `GATE_APPROVED` row for its slug, unless a counting `GATE_REJECTED` row for it follows, which leaves the stage with none. A row that carries `Unit`, `Gate Scope` or `Gate Stages` is ignored: it is no approval and names nothing in `named_items`. A row without an `Items` field is current, never stale and freezes no body hash; a row whose `Items` do not parse is not an approval and names nothing. A row is current when its `Items` ids with revisions equal the stage's current ones. `Approved By` is `human`, `automatic` or absent.
- A stale approval raises `earnest/outdated` at level note (Level cell "error; note for a stage approval"), located at the id line of each item whose revision moved, at its stage's position (RP9, P1).
- The baseline (RP3, B-d): `check --stage` records an item's body hash, keyed `type~name~revision`, when none is held, and replaces it on each later run until a counting `GATE_APPROVED` row names the id with that revision; then it stays. `unbumped-change` fires only for an id and revision such a row names, when the item's hash differs from the held one. A voided row (rejected, before the latest `WORKFLOW_STARTED`, or jumped over) names nothing. `check` and `plan` never write the record.
- The body hash is the SHA-256 of the UTF-8 bytes of the body's non-blank lines joined by `\n`, with no final `\n`. The body is the lines after the id line up to the next id line or ATX heading; key lines are left out, fenced lines count. A line loses one trailing `\r`, then trailing spaces and tabs, and is blank when nothing is left; other Unicode whitespace is kept (B4, E9).
- The scanner skips, through the predicate `adapters.skipped(path, directories)` that `plan.dirty` also uses, inside a record directory (the parent of a listed `aidlc-state.md`): that file, `audit/**`, `.aidlc-engine/**`, the sibling entries whose names begin `.aidlc-`, and `memory.md` files under a stage directory. `plan.py` reads the first two itself (RP7 1(g), C5).
- The record is canonical JSON v1: keys `version`, `runs`, `bodies`, `coverage`, `judge`, `calibration`; sorted keys, ASCII, integers only, `sha256:` digests, SARIF-uri paths. The hash input uses the compact form with no trailing newline (the SARIF log keeps M1's single trailing `\n`), the file the two-space-indented form with one trailing newline (RP2). `runs` is keyed `<intent dir>/<stage id>`.
- The assessment hash covers the stage assessment document and the evaluated-tree digest; the commit, timestamp, route and approvals stay outside it. Findings derived from approvals (the stale-approval notes) stay out of the document, and findings in files outside the evaluated tree do not enter it (RP4, F-a).
- Option behaviours the design leaves open, as the plan fixes them: `check --intent <dir>` without `--stage` validates the directory (a missing one exits 2) and changes nothing else, every intent still being reported; `--intent` is read relative to the repository root first and, if that names no record directory, relative to the working directory; `plan` over several intents that are all unsupported exits 0 with only the skip lines and an empty `properties.plan`; `properties.plan` is `{"intents": []}` when a record directory exists but none is supported, and absent only when there is no record directory (Command surface: plain `check` omits the unsupported intent's entry, not the container).
- `dirty` is true when a path the evaluated tree holds or would hold (a scanned suffix, outside every record directory or under a route stage's path) is untracked, differs from HEAD or the index, or is missing from the work tree. It comes from one `git --no-optional-locks status --porcelain=v1 -z --untracked-files=all --no-renames` over the work tree (no path is handed to Git), filtered in Python; `_git` prefixes every call with `--literal-pathspecs` (E4, C4).
- `earnest/unplanned` counts against the Code Generation stage whose unit delivers the requirement, or the first Code Generation stage on the route when no unit does (M2 has no units, so always the latter); a route with no Code Generation stage raises none (B9, Q13). `earnest/cycle` counts against the stage that holds the cycle and is located at the id line of the first item in id order.
- `properties.plan` is `{"intents": [...]}`, one entry per supported record directory, on `plan`, `check` and `check --stage` (B8, PD6); an unsupported intent has no entry.
- SC1: two runs over an unchanged repository give the same SARIF bytes and the same hash. SARIF and the hash input hold no timestamp.
- Coverage (L1): reported with no threshold; a run passes or fails on its tests alone.
- Fixtures are plain files whose Git history `tests/conftest.py` builds at test time (L6); `tests/fixtures` stays out of ruff, pytest collection and markdownlint.
- Run every command in `packages/earnest/` unless a step names the repository root, and start each task with `make install`.
- Commit messages take the form `<type>: <description>`; before each commit, `git status --short` lists only the task's files (`.pi-herdsman/` stays untracked and unstaged).
- No agent `rm`s a path it did not create.
- Test counts are exact: each task states the count that the regression run (`uv run pytest --ignore=tests/steps/test_stage_status.py`) must report after it, each parametrized case counted as one test; the baseline is the 139 tests at 746d9a0, and Task 12 lifts the ignore. A run as root skips M1's unreadable-file test and Task 12's unreadable-shard test.
- Tasks run one at a time in one worktree, in the order T0 to T13 (a topological order of the DAG). Sequential in one worktree is the only authorized mode; running DAG branches in parallel needs the maintainer's explicit approval first. Each commit stages the paths its task owns by name (`git add <path>`, a file or a directory only that task writes).

## Review Focus

- A repository with no intent record directory (`broken-links`, any plain checkout): no plan, every finding at position `current` with no stage, `earnest plan` prints SARIF without `properties.plan`, says `no plan` on stderr and exits 0, and nothing is written; `produces` is `None` when no intent is supported, so M1's findings are untouched (Tasks 9, 10, 12).
- Audit shards from two clones, and a restart or jump: the approval in the shard whose name sorts first but whose timestamp is later still counts; an approval from before a `WORKFLOW_STARTED`, or inside a BACKWARD jump's reset span, does not, and neither does a skip row there, which puts its stage back on the route; a FORWARD jump leaves approvals standing (Tasks 8 and 9).
- A route a flipped mark could shrink: a stage marked `[S]` and EXECUTE with no counting skip row stays on the route and raises `earnest/route-mismatch`, which fails every gate of that intent; so does a Stage Progress row, or a whole section, that Earnest cannot read, which would otherwise shrink the route silently and let the check pass at 100% traced (Task 9).
- A route with `units-generation` on it: `plan` and `check --stage` exit 2 with the one unsupported-route line, empty stdout and no `.earnest/`; plain `check` places that intent's findings as in a run with no plan (Tasks 9, 10, 12).
- A damaged or newer `.earnest/assessment.json`, an unreadable audit shard, a write that fails, and two sensor fires for one gate: the first three exit 2 with one `earnest:` line on stderr and empty stdout and leave the old file whole; the last writes the same hash twice and never leaves a half file (Tasks 6 and 12).
- A draft edited between a failed gate and its approval, a gate rejected after approval, and a row written without the fork's fields: a plain `check` raises no `unbumped-change` on a hash no counting row names, the next `--stage` run replaces it, a rejected row freezes nothing, and a row without `Items` is current and freezes nothing (Tasks 9, 11, 12).
- Several record directories, or a `--stage` that names no stage: `--intent` selects, a missing, unknown or ambiguous choice exits 2 with one line that lists the candidates (Task 12).
- File names with spaces, accents or glob characters (`*`, `[`), a deleted tracked stage artifact or audit shard, CRLF bodies, a touched-but-unchanged tracked file, and an audit row appended between two runs: `git status` is read as bytes with no pathspec magic and without refreshing `.git/index`, a deleted tracked file is skipped by `plan.load` as it is by the scanner, a deleted stage artifact makes the run dirty while an audit row, the state file, a stage's `memory.md` and a scratch `.txt` do not, CRLF and LF bodies hash alike, and the audit row changes neither hash nor `dirty` (Tasks 3, 4, 8 and 11).

## Task order and regression counts

Tasks run in the order below, one at a time in one worktree. The regression run is `uv run pytest --ignore=tests/steps/test_stage_status.py` in `packages/earnest/`; it covers the unit and integration tiers and the M1 gate and states its exact expected count after each task. The baseline is the 139 tests at 746d9a0.

| Task | Content | Depends on | New tests | Regression total |
| --- | --- | --- | --- | --- |
| 0 | Commit this plan | none | 0 | 139 |
| 1 | The `stage_status` behavior gate, red: fixture, feature, steps | none | 6 | 145 |
| 2 | `Source` fields, code-line scans, the record-directory skips | T1 | 18 | 163 |
| 3 | Body hash and the Region rule, `index.py` | T2 | 18 | 181 |
| 4 | The record directory and the changed paths, `git.py` | T1 | 12 | 193 |
| 5 | Positions, stages and properties, `reporter.py` | T1 | 18 | 211 |
| 6 | The assessment record, `reporter.py` | T5 | 14 | 225 |
| 7 | The route rule and `unbumped-change`, `structural.py` | T3, T5 | 13 | 238 |
| 8 | The state and audit readers, `plan.py` | T1 | 21 | 259 |
| 9 | The route, counting rules, approvals, frontier, `plan.py` | T5, T8 | 46 | 305 |
| 10 | Status, `unplanned`, `cycle`, positions, `plan.py` | T7, T9 | 44 | 349 |
| 11 | The assessment hash, baseline and `dirty`, `plan.py` | T10, T2, T3, T6 | 27 | 376 |
| 12 | `earnest plan`, `check --stage`, `--intent`, `cli.py`; the gate turns green | T11, T4, T6 | 48 | 424 |
| 13 | The full suite, the review and the milestone DAG | T12 | 0 | 452 (424 plus 28 scenarios): the historical checkpoint at T12; 481 at HEAD (see below) |

The counts in this table and in each task's steps are the historical TDD checkpoints. The milestone review pass (D17, commit bc7e5c1) added 29 tests, 24 gap tests (D9 3, D11 2, D12 5, D14 8, D15 2, D16 4) and 5 fix tests (2 in `test_cli.py`, 1 in `test_reporter.py`, 2 in `test_plan.py`), so the suite at HEAD is 481 = 453 + 28 scenarios. Task 13 states the final figures.

## File Structure

| Path under `packages/earnest/` | Responsibility | Task |
| --- | --- | --- |
| `tests/fixtures/seeded-change/` | the AI-DLC-shaped repository: `aidlc/spaces/default/intents/260926-checkout/` with state file, audit shard, three-stage route, two tasks, tagged Python code and tests; `change/` is the overlay | 1 |
| `tests/features/stage_status.feature` | M2's 28 scenarios, verbatim from the ratified `04` | 1 |
| `tests/steps/test_stage_status.py` | pytest-bdd steps; the exit command | 1, 12 |
| `tests/conftest.py` | base-commit builder that leaves out `change/`; overlay committer; steps that two features share | 1 |
| `tests/sarif.py` | the SARIF helpers plus `rows` and `run_earnest` | 1 |
| `tests/integration/test_seeded_change.py` | the fixture's seeds and overlay, pinned to the lines `04` names | 1 |
| `src/earnest/index.py` | `Source` fields, `digest`, `Item.body_hash`, `Region`, `Index.regions`, `Literal` status | 2, 3 |
| `src/earnest/adapters/` | `code_lines` per language; `reads`; the record-directory skips; `Source` built by keyword | 2 |
| `src/earnest/git.py` | no path under `.earnest/`; `changes` from one lock-free `git status`; every call literal | 4 |
| `src/earnest/reporter.py` | `Finding` position, stage, note and child; rule aliases; `Run`; SARIF and summary properties; `canonical`; the record | 5, 6 |
| `src/earnest/structural.py` | the route rule, `unbumped-change`, `resolved_covers` | 7 |
| `src/earnest/plan.py` | state and audit readers, `load`; counting rules, route, approvals, frontier, `route_findings`; status, `unplanned`, `cycle`, approval notes, positions, `in_tree`, `PRODUCES`; assessment document, hash, baseline, `dirty`; `select_intent`, `select_stage` | 8 to 12 |
| `src/earnest/cli.py` | `earnest plan`, `check --stage --intent`, the `RecordError` and `PlanError` boundary | 5, 12 |
| `tests/unit/test_<module>.py`, `tests/unit/adapters/test_<language>.py`, `tests/integration/test_stage.py` | each task's tests | 2-12 |

Outside the package, Task 0 commits this plan, Task 9 edits one row of the Findings table in `docs/design/01-logic-design.md` (the `earnest/route-mismatch` row), and Task 13 edits `docs/design/03-implementation-plan.md` (the `done` class on M2 and the M2 task-plan entry).

## Known limits

Each is a ceiling that the milestone accepts, with the upgrade path; several have a `ponytail:` comment in the code at the place it applies, and the others live here alone.

- Names: `properties.assessment.stage` and the summary's `assessment` line carry `<intent dir>/<stage id>`, while a result's `properties.stage` is the bare stage id. Settle the names in `01` when the gate display (M7) reads them.
- The record's `coverage` slot is `{"commit": null}` until Milestone 3 says whether it holds an object or the bare commit (Task 6).
- Record validation is shallow: `version: true` or a non-string body hash passes. The file is mode 0600, and a write that fails after `.earnest/` is new leaves its `.gitignore` (Task 6).
- `run_key` for a record directory at the repository root has a leading slash that `--intent ""` cannot name (Task 6).
- Timestamps order as strings, which is right for upstream's fixed-width format (Task 8).
- The record is rewritten whole, so two stage checks of different stages racing are last-writer-wins; the same stage twice is safe (Task 12).
- `bodies` entries for revisions that no longer exist are never pruned (Task 11).
- A stage's `errors` count leaves out findings placed ahead of the frontier, which are notes, so an approved stage after the frontier can read done despite one (Task 10).
- One shortest cycle is reported per task, so a cycle that is never the shortest through any of its tasks shows once the shorter ones are fixed (Task 10).
- One union `produces` serves every intent's items when a repository mixes supported and unsupported intents (Task 10).
- A record directory at the repository root drops every source file from the evaluated tree, since each path lies inside it (Task 10, D14).
- The index is built over all sources, so an edit outside the evaluated tree can move the body hash and the assessment hash while `dirty` stays false (Task 11, D15).
- The record write is not fsynced (Task 6, D10). A symlinked `.earnest` directory is refused on read and write (Task 6, MUST-FIX 2); so is a symlinked `.earnest/assessment.json` (pre-PR review fix 2cdd239). The symlink check and the open are separate steps, so a concurrent local process could swap the record between them, and a FIFO record is not refused. Both lie outside the repository-content threat model; opening with `O_NOFOLLOW` and checking for a regular file would close both.
- Stage Progress rows must start at column 0 with `- [`, so an indented or `* [` row is neither a row nor an unread line, as upstream's own setter requires; audit blocks end only at a line that is exactly `---`, so a separator with a trailing space merges two blocks; any `###` heading sets the phase (Task 8, D12).
- A slug that appears in two phases collapses into one row, and a `STAGE_JUMPED` row that carries a `Unit` still voids the rows it follows (Task 9, D13).
- With several intents, every `stest` finding goes to the first plan's Build and Test and each plan counts all `stest`s; `task_done` is quadratic in the tasks; "id order" is string order (Task 10, D14).
- A file that the scanner drops (an untagged `.py` or `.ts`, a binary) makes `dirty` true without moving the hash, which over-reports and never hides; `next_bodies` reads the intent's own items while `frozen_bodies` reads every intent's, which differ for an item that another intent cites (Task 11, D15).
- D17-1: stage slugs are parsed with `partition("/")` in several places in `plan.py`, which breaks per-unit ids, so M2b replaces it with one slug and id parser.
- D17-2: the header's `reasons` are built twice, in `cli._stage` and in `plan.header`.
- D17-3: `Row.reason`, `Approval.digest`, `State.scope` and `Record.version` are parsed and kept but read only by tests or not at all.
- D17-4: `State.scope` is parsed but not displayed in M2; `04` no longer calls it read for display.
- D17-5: M4 needs the layers, model and prompt threaded through `Run`, and body text or spans on `Item`.
- D17-6: the record-directory rule is decided in three places: `adapters`, `plan.load` and `plan.dirty`.
- D17-7: `plan._SUBJECT` accepts a looser grammar than the item-id grammar `index.ID_ENTRY`.

---

## Tasks

### Task 0: Commit this plan

The verifier runs this task once, from the repository root, before Task 1. It puts the plan in history first, as M1 did, so that every later task's `git status --short` lists only that task's files and the link that Task 13 writes into `03` does not dangle.

**Files:**

- Commit: `docs/superpowers/plans/2026-10-10-stage-status.md`

- [ ] **Step 1: Check what is untracked**

Run: `git status --short`

Expected: the plan is listed as `?? docs/superpowers/plans/2026-10-10-stage-status.md`; the design record `.pi-herdsman/` and any harness directories may be listed as untracked too, and nothing is staged or modified.

- [ ] **Step 2: Lint the plan**

Run: `LINT_FILE=docs/superpowers/plans/2026-10-10-stage-status.md make lint-file`

Expected: the hook lints the file and reports no issue.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-10-10-stage-status.md
git commit -m "docs: add the M2 stage_status plan"
```

### Task 1: The `stage_status` behavior gate, red

> Superseded in part by the final state in Task 13 (D17, S1–S7); these snippets are the historical TDD record.

**Files:**

- Create: `packages/earnest/tests/fixtures/seeded-change/aidlc/spaces/default/intents/260926-checkout/aidlc-state.md`
- Create: `packages/earnest/tests/fixtures/seeded-change/aidlc/spaces/default/intents/260926-checkout/audit/fixture-a1b2c3d4.md`
- Create: `packages/earnest/tests/fixtures/seeded-change/aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md`
- Create: `packages/earnest/tests/fixtures/seeded-change/aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md`
- Create: `packages/earnest/tests/fixtures/seeded-change/src/checkout/auth.py`, `packages/earnest/tests/fixtures/seeded-change/tests/test_auth.py`
- Create: `packages/earnest/tests/fixtures/seeded-change/change/aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md` (the overlay)
- Modify: `packages/earnest/tests/sarif.py`, `packages/earnest/tests/conftest.py`, `packages/earnest/tests/steps/test_trace_check.py`
- Create: `packages/earnest/tests/features/stage_status.feature`
- Test: `packages/earnest/tests/steps/test_stage_status.py`, `packages/earnest/tests/integration/test_seeded_change.py`

**Interfaces:**

- Consumes: `fixture_repo`, `_commit`, `_git` and `_isolated_git` from M1's `tests/conftest.py`; `sarif_run`, `located` from `tests/sarif.py`; the M1 step module's shared steps.
- Produces, in `tests/sarif.py`: `EARNEST`, `sarif_run(text)`, `located(result)`, `rows(datatable) -> list[dict[str, str]]`, `run_earnest(repo: Path, *args: str) -> subprocess.CompletedProcess[str]` and `git_output(repo: Path, *args: str) -> str`.
- Produces, in `tests/conftest.py`: `fixture_repo(name)` now copies a fixture without its top-level `change/`; `commit_overlay: Callable[[Path, str, str], Path]` taking `(repo, fixture name, branch)`, which creates the branch, copies `change/` over the work tree and commits just the overlay's files with the pinned identity; the shared steps `the SARIF log holds exactly these findings:` (compares only the columns the table gives among `rule`, `file`, `line`, `level`, `position`, `stage`), `both runs write the same SARIF log`, `the check exits zero` and `the check exits non-zero` (exit code 1 with a SARIF log), each reading the fixtures `run` or `runs`.
- Produces the exit command `uv run pytest tests/steps/test_stage_status.py`: 28 scenarios, all failing (the commands `plan` and `--stage` do not exist) until Task 12. Its steps fix the contracts that later tasks meet: `properties.plan.intents[0]` carries `stages` (`stage`, `status`, `approval`, `approvedBy`), `tasks` (`id`, `status`) and `frontier`; the summary prints `<stage>: <status>, approval <approval>` (with `, <approvedBy>` after `current`), `frontier: <stage>` and `assessment <stage>: <hash> (<status>)`; `properties.assessment` carries `hash`, `status` and `reasons.approval`; the record keeps `runs["<record dir>/<stage>"]` with `commit`, `dirty`, `layers`, `items` and `hash`, and `bodies` keyed by `type~name~revision`; an `unplanned` message contains "delivered by no task"; an `outdated` approval note contains the stage id, "approval" and `revision <n>`; a `route-mismatch` message contains the slug and `STAGE_SKIPPED`; the refusal line is exactly `earnest: unsupported route: units-generation is on the route, so per-unit stages`.

The fixture is the base commit of `seeded-change`. Every path below is under `RECORD = aidlc/spaces/default/intents/260926-checkout/`, which the sensor's `matches` selects. The line numbers are those of the seed tables of `docs/design/04-bdd-test-plan.md`; the shapes are upstream's (`rp7-upstream.md` sections 2, 3 and 7), and only the `Assessment Hash`, `Items` and `Approved By` fields are Fork-delta. The dash in the Stage Progress rows is U+2014.

- [ ] **Step 1: Add the shared helpers to `tests/sarif.py`**

Replace the whole of `packages/earnest/tests/sarif.py` with:

```python
"""Helpers the tests share: the one run in a SARIF log, the earnest command, Git, and a data table as rows."""

import json
import subprocess
import sys
from pathlib import Path


EARNEST = Path(sys.executable).with_name("earnest")


def sarif_run(text):
    """Return the one run of the SARIF log in text."""
    (run,) = json.loads(text)["runs"]
    return run


def located(result):
    """Return a result's file, as its percent-encoded uri, and its line."""
    location = result["locations"][0]["physicalLocation"]
    return location["artifactLocation"]["uri"], location["region"]["startLine"]


def rows(datatable):
    """Return a data table's rows as dicts keyed by its header."""
    header, *body = datatable
    return [dict(zip(header, row, strict=True)) for row in body]


def run_earnest(repo, *args):
    """Run `earnest` with args in repo, as the coding agent does, and return the finished process."""
    return subprocess.run([str(EARNEST), *args], cwd=repo, capture_output=True, text=True, check=False)


def git_output(repo, *args):
    """Return what `git args` prints in repo; a failing Git raises."""
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout
```

- [ ] **Step 2: Split the builder and move the shared steps into `tests/conftest.py`**

In `packages/earnest/tests/conftest.py`, replace:

```python
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
```

with:

```python
import json
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_bdd import then

from tests.sarif import located, rows, sarif_run
```

In the same file, replace:

```python
@pytest.fixture
def fixture_repo(tmp_path: Path) -> Callable[[str], Path]:
    """Return a builder that copies tests/fixtures/<name> into tmp_path and commits it on main."""

    def build(name: str) -> Path:
        repo = tmp_path / name
        shutil.copytree(FIXTURES / name, repo)
        return _commit(repo)

    return build
```

with:

```python
def _leave_out_change(root: Path) -> Callable[[str, list[str]], list[str]]:
    """Return a copytree ignore that leaves out the `change/` overlay at the top of the fixture at root."""

    def ignore(directory: str, names: list[str]) -> list[str]:
        return ["change"] if Path(directory) == root and "change" in names else []

    return ignore


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Callable[[str], Path]:
    """Return a builder that copies tests/fixtures/<name>, less its `change/` overlay, into tmp_path and commits it."""

    def build(name: str) -> Path:
        repo = tmp_path / name
        shutil.copytree(FIXTURES / name, repo, ignore=_leave_out_change(FIXTURES / name))
        return _commit(repo)

    return build
```

At the end of the same file, after `files_repo`, append:

```python


@pytest.fixture
def commit_overlay() -> Callable[[Path, str, str], Path]:
    """Return a builder that commits a fixture's `change/` overlay, and only its files, on a new branch of repo."""

    def commit(repo: Path, name: str, branch: str) -> Path:
        overlay = FIXTURES / name / "change"
        files = sorted(str(path.relative_to(overlay)) for path in overlay.rglob("*") if path.is_file())
        _git(repo, "checkout", "-q", "-b", branch)
        shutil.copytree(overlay, repo, dirs_exist_ok=True)
        _git(repo, "add", "--", *files)
        _git(repo, "commit", "-q", "--no-verify", "-m", "change")
        return repo

    return commit


# What each column of a findings table reads from a SARIF result.
_COLUMNS = {
    "rule": lambda result: result["ruleId"],
    "file": lambda result: located(result)[0],
    "line": lambda result: located(result)[1],
    "level": lambda result: result["level"],
    "position": lambda result: result["properties"]["position"],
    "stage": lambda result: result["properties"].get("stage"),
}


@then("the SARIF log holds exactly these findings:")
def exact_findings(run, datatable):
    table = rows(datatable)
    columns = list(table[0])
    expected = [tuple(int(row[c]) if c == "line" else row[c] for c in columns) for row in table]
    actual = [tuple(_COLUMNS[c](result) for c in columns) for result in sarif_run(run.stdout)["results"]]
    assert sorted(actual, key=repr) == sorted(expected, key=repr)


@then("both runs write the same SARIF log")
def same_log(runs):
    first, second = runs
    assert json.loads(first.stdout)["version"] == "2.1.0"
    assert first.stdout == second.stdout


@then("the check exits zero")
def exits_zero(run):
    assert run.returncode == 0, run.stderr


@then("the check exits non-zero")
def exits_non_zero(run):
    assert run.returncode == 1, run.stderr
    assert sarif_run(run.stdout)["results"]
```

- [ ] **Step 3: Point the M1 step module at the shared helpers and run the M1 gate**

In `packages/earnest/tests/steps/test_trace_check.py`, replace:

```python
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
```

with:

```python
from pytest_bdd import given, parsers, scenarios, then, when

from tests.sarif import located, rows, run_earnest, sarif_run


scenarios("trace_check.feature")


def run_check(repo):
    """Run `earnest check` in repo, as the coding agent does."""
    return run_earnest(repo, "check")
```

In the same file, replace:

```python
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
```

with:

```python
@then("every finding is in scope at position current, with no stage")
```

Run: `uv run pytest tests/steps/test_trace_check.py`

Expected: `5 passed`. The two shared steps now live in `conftest.py` and read the `run` and `runs` fixtures that this module's `When` steps set.

- [ ] **Step 4: Write the failing tests for the fixture**

Create `packages/earnest/tests/integration/test_seeded_change.py`:

```python
"""Integration: the seeded-change fixture holds the seeds and the overlay that the stage_status scenarios read."""

from earnest.index import MARKDOWN, Source, build_index, split_lines
from tests.sarif import git_output


RECORD = "aidlc/spaces/default/intents/260926-checkout"
STATE = f"{RECORD}/aidlc-state.md"
SHARD = f"{RECORD}/audit/fixture-a1b2c3d4.md"
REQUIREMENTS = f"{RECORD}/inception/requirements-analysis/requirements.md"
PLAN = f"{RECORD}/construction/code-generation/code-generation-plan.md"


def lines_of(repo, path):
    return (repo / path).read_text(encoding="utf-8").split("\n")


def test_base_commit_holds_the_seeded_lines(fixture_repo):
    repo = fixture_repo("seeded-change")
    state = lines_of(repo, STATE)
    assert state[5] == "- **Scope**: bugfix"
    assert [state[n - 1] for n in (11, 16, 21, 25)] == [
        "### INITIALIZATION PHASE",
        "### INCEPTION PHASE",
        "### CONSTRUCTION PHASE",
        "### OPERATION PHASE",
    ]
    rows = {state[n - 1].split(" ")[2]: state[n - 1].split(" ")[1] for n in (12, 13, 14, 17, 18, 19, 22, 23, 26, 27)}
    assert rows == {
        "workspace-scaffold": "[x]",
        "workspace-detection": "[x]",
        "state-init": "[x]",
        "reverse-engineering": "[S]",
        "requirements-analysis": "[x]",
        "units-generation": "[S]",
        "code-generation": "[x]",
        "build-and-test": "[x]",
        "deployment-pipeline": "[S]",
        "deployment-execution": "[S]",
    }
    requirements = lines_of(repo, REQUIREMENTS)
    assert [requirements[n - 1] for n in (3, 8, 13)] == [
        "`req~rate-limit~1`",
        "`req~lockout-notice~1`",
        "`req~audit-log~1`",
    ]
    assert requirements[10] == "when they may try again."
    plan = lines_of(repo, PLAN)
    assert [plan[n - 1] for n in (3, 9)] == ["`task~add-limiter~1`", "`task~notify-lockout~1`"]
    assert [plan[n - 1] for n in (7, 13, 14)] == [
        "Delivers: req~rate-limit~1",
        "Delivers: req~lockout-notice~1",
        "Depends: task~add-limiter~1",
    ]
    for path, kind in (("src/checkout/auth.py", "impl"), ("tests/test_auth.py", "utest")):
        code = lines_of(repo, path)
        assert [code[n - 1] for n in (4, 9, 14)] == [
            f"# [{kind}->req~rate-limit~1]",
            f"# [{kind}->req~lockout-notice~1]",
            f"# [{kind}->req~audit-log~1]",
        ]


def test_audit_shard_blocks_sit_at_the_seeded_lines(fixture_repo):
    shard = lines_of(fixture_repo("seeded-change"), SHARD)
    assert [n for n, text in enumerate(shard, 1) if text.startswith("## ")] == [1, 7, 14, 21, 28]
    assert [n for n, text in enumerate(shard, 1) if text == "---"] == [6, 13, 20, 27, 36]
    assert [shard[n - 1] for n in (3, 9, 16, 23, 30)] == [
        "**Event**: WORKFLOW_STARTED",
        "**Event**: STAGE_SKIPPED",
        "**Event**: STAGE_SKIPPED",
        "**Event**: STAGE_SKIPPED",
        "**Event**: GATE_APPROVED",
    ]
    assert shard[33] == "**Items**: req~audit-log~1, req~lockout-notice~1, req~rate-limit~1"
    assert shard[34] == "**Approved By**: human"


def test_overlay_is_committed_on_the_task_branch(fixture_repo, commit_overlay):
    repo = commit_overlay(fixture_repo("seeded-change"), "seeded-change", "task/add-limiter-window")
    assert git_output(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() == "task/add-limiter-window"
    assert git_output(repo, "rev-list", "--count", "main..HEAD").strip() == "1"


def test_overlay_changes_two_places_of_the_requirements(fixture_repo, commit_overlay):
    repo = commit_overlay(fixture_repo("seeded-change"), "seeded-change", "task/add-limiter-window")
    diff = git_output(repo, "diff", "--unified=0", "main", "HEAD")
    assert [line for line in diff.splitlines() if line.startswith("diff --git")] == [
        f"diff --git a/{REQUIREMENTS} b/{REQUIREMENTS}",
    ]
    hunks = [line.split(" @@")[0] + " @@" for line in diff.splitlines() if line.startswith("@@")]
    assert hunks == ["@@ -3 +3 @@", "@@ -5 +5 @@", "@@ -11 +11 @@"]
    requirements = lines_of(repo, REQUIREMENTS)
    assert requirements[2] == "`req~rate-limit~2`"
    assert requirements[4].endswith("for thirty minutes")
    assert requirements[10] == "how long the lockout lasts."


def test_base_copy_leaves_the_change_directory_out(fixture_repo):
    repo = fixture_repo("seeded-change")
    assert not (repo / "change").exists()
    assert "change/" not in git_output(repo, "ls-files")


def test_state_and_audit_files_hold_no_item_id_tag_or_near_miss(fixture_repo):
    repo = fixture_repo("seeded-change")
    sources = [
        Source(path, MARKDOWN, split_lines((repo / path).read_text(encoding="utf-8"))) for path in (STATE, SHARD)
    ]
    index = build_index(sources)
    assert (index.items, index.links, index.near_misses) == ((), (), ())
```

Run: `uv run pytest tests/integration/test_seeded_change.py -v`

Expected: `6 failed`, each with `FileNotFoundError` for `tests/fixtures/seeded-change`.

- [ ] **Step 5: Create the fixture**

Create `packages/earnest/tests/fixtures/seeded-change/aidlc/spaces/default/intents/260926-checkout/aidlc-state.md` (abridged: upstream lists every compiled stage and more sections; only the Stage Progress rows are read):

```markdown
# AI-DLC State Tracking

## Project Information
- **Project**: checkout
- **Project Type**: Greenfield
- **Scope**: bugfix
- **Start Date**: 2026-09-26

## Stage Progress
<!-- Checkbox states: [ ] pending, [-] in-progress, [?] awaiting approval, [R] revising, [x] completed, [S] skipped -->
### INITIALIZATION PHASE
- [x] workspace-scaffold — EXECUTE: always
- [x] workspace-detection — EXECUTE: always
- [x] state-init — EXECUTE: always

### INCEPTION PHASE
- [S] reverse-engineering — EXECUTE: greenfield project
- [x] requirements-analysis — EXECUTE: always
- [S] units-generation — SKIP: not in bugfix scope

### CONSTRUCTION PHASE
- [x] code-generation — EXECUTE: always
- [x] build-and-test — EXECUTE: always

### OPERATION PHASE
- [S] deployment-pipeline — EXECUTE: no pipeline change
- [S] deployment-execution — EXECUTE: no pipeline change
```

Create `packages/earnest/tests/fixtures/seeded-change/aidlc/spaces/default/intents/260926-checkout/audit/fixture-a1b2c3d4.md` (five blocks, each closed by a line `---`; the timestamps are synthetic and the skip order does not follow a real run):

```markdown
## Workflow Started
**Timestamp**: 2026-09-26T09:00:00Z
**Event**: WORKFLOW_STARTED
**Scope**: bugfix
**Request**: Lock members out after repeated failed logins.
---
## Stage Skipped
**Timestamp**: 2026-09-26T09:10:00Z
**Event**: STAGE_SKIPPED
**Stage**: reverse-engineering
**Reason**: greenfield project
**Skip Kind**: conditional-runtime
---
## Stage Skipped
**Timestamp**: 2026-09-26T09:20:00Z
**Event**: STAGE_SKIPPED
**Stage**: deployment-pipeline
**Reason**: no pipeline change
**Skip Kind**: conditional-runtime
---
## Stage Skipped
**Timestamp**: 2026-09-26T09:21:00Z
**Event**: STAGE_SKIPPED
**Stage**: deployment-execution
**Reason**: no pipeline change
**Skip Kind**: conditional-runtime
---
## Gate Approved
**Timestamp**: 2026-09-26T10:00:00Z
**Event**: GATE_APPROVED
**Stage**: requirements-analysis
**User Input**: Approve
**Assessment Hash**: sha256:0000000000000000000000000000000000000000000000000000000000000000
**Items**: req~audit-log~1, req~lockout-notice~1, req~rate-limit~1
**Approved By**: human
---
```

Create `packages/earnest/tests/fixtures/seeded-change/aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md`:

```markdown
# Requirements

`req~rate-limit~1`

The system shall lock a member out for fifteen minutes
after five failed logins in a window.

`req~lockout-notice~1`

When a member is locked out, the system shall tell the member
when they may try again.

`req~audit-log~1`

The system shall record each lockout in the audit log.
```

Create `packages/earnest/tests/fixtures/seeded-change/aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md`:

```markdown
# Code generation plan

`task~add-limiter~1`

Add a limiter that counts failed logins in a window.

Delivers: req~rate-limit~1

`task~notify-lockout~1`

Tell the member when the lockout starts.

Delivers: req~lockout-notice~1
Depends: task~add-limiter~1
```

Create `packages/earnest/tests/fixtures/seeded-change/src/checkout/auth.py`:

```python
"""Checkout authentication."""


# [impl->req~rate-limit~1]
def count_failed_logins(window: int) -> int:
    return window


# [impl->req~lockout-notice~1]
def lockout_message() -> str:
    return "Try again later."


# [impl->req~audit-log~1]
def audit_lockout(member: str) -> str:
    return member
```

Create `packages/earnest/tests/fixtures/seeded-change/tests/test_auth.py`:

```python
"""Checkout authentication tests."""


# [utest->req~rate-limit~1]
def test_count_failed_logins() -> None:
    assert True


# [utest->req~lockout-notice~1]
def test_lockout_message() -> None:
    assert True


# [utest->req~audit-log~1]
def test_audit_lockout() -> None:
    assert True
```

Create the overlay `packages/earnest/tests/fixtures/seeded-change/change/aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md`, the base file with line 3 now `req~rate-limit~2`, line 5 now ending `for thirty minutes`, and line 11 changed:

```markdown
# Requirements

`req~rate-limit~2`

The system shall lock a member out for thirty minutes
after five failed logins in a window.

`req~lockout-notice~1`

When a member is locked out, the system shall tell the member
how long the lockout lasts.

`req~audit-log~1`

The system shall record each lockout in the audit log.
```

Run: `uv run pytest tests/integration/test_seeded_change.py -v`

Expected: `6 passed`.

- [ ] **Step 6: Add the feature**

Create `packages/earnest/tests/features/stage_status.feature` with the M2 feature of `docs/design/04-bdd-test-plan.md` verbatim, all 28 scenarios (copied from the committed `04`; the block is reproduced here and must stay byte-identical to it):

```gherkin
Feature: Stage status
  The coding agent and the repo maintainer read where the work stands from the
  command output alone: the route with each stage's computed status, its
  approval and the frontier; the assessment hash that a stage check prints and
  records; and, after a revision bump, every place left at the old revision
  (UC4, UC7, UC9; SC1, SC5, SC8, SC9).

  Background:
    Given the repo maintainer's "seeded-change" repository at its base commit, with the requirements stage approved

  Scenario: The plan prints the route, each stage's status, its approval and the frontier (SC8)
    When the coding agent runs earnest plan
    Then the plan lists these stages in route order:
      | stage                           | status   | approval       |
      | inception/requirements-analysis | done     | current, human |
      | construction/code-generation    | not done | none           |
      | construction/build-and-test     | not done | none           |
    And the frontier is "construction/code-generation"
    And the plan lists these tasks:
      | task                  | status   |
      | task~add-limiter~1    | not done |
      | task~notify-lockout~1 | not done |
    And the plan lists neither the initialization stages nor the stages skipped by scope or by an audited skip
    And the summary names each stage with its status and approval, and the frontier

  Scenario: A status someone typed is not read (SC8)
    When the coding agent runs earnest plan
    Then "construction/code-generation" is "not done" although the state file marks it complete

  Scenario: The plan changes nothing in the repository (SC8)
    When the coding agent runs earnest plan
    Then the repository is unchanged
    And no assessment record exists

  Scenario: Two plans of an unchanged repository write the same SARIF log (SC1)
    When the coding agent runs earnest plan twice
    Then both runs write the same SARIF log

  Scenario: A requirement that no task delivers is flagged in scope at the frontier (SC8)
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule              | file                                                                                         | line | level   | position | stage                        |
      | earnest/unplanned | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 13   | warning | current  | construction/code-generation |
    And the finding names "req~audit-log~1" and says that no task delivers it
    And the check exits zero

  Scenario: Tasks that wait on each other are a cycle in scope at the frontier (SC8)
    Given the repo maintainer makes "task~add-limiter~1" wait on "task~notify-lockout~1", which already waits on it
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule              | file                                                                                              | line | level   | position | stage                        |
      | earnest/cycle     | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 3    | error   | current  | construction/code-generation |
      | earnest/unplanned | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | warning | current  | construction/code-generation |
    And the cycle finding lists "task~add-limiter~1 -> task~notify-lockout~1 -> task~add-limiter~1"
    And the check exits non-zero

  Scenario: The stage check prints the assessment hash and writes the run header (SC9)
    When the coding agent runs earnest check --stage "construction/code-generation"
    Then the summary prints the assessment hash
    And the SARIF log gives the same hash and the stage status "not done"
    And the run header for "construction/code-generation" in the assessment record holds:
      | field  | value                                     |
      | commit | the repository's HEAD commit              |
      | dirty  | false                                     |
      | layers | trace                                     |
      | items  | task~add-limiter~1, task~notify-lockout~1 |
      | hash   | the hash the summary printed              |
    And Git lists no new file
    And the check exits zero

  Scenario: Two stage checks of an unchanged repository print the same hash (SC1)
    When the coding agent runs earnest check --stage "construction/code-generation" twice
    Then both runs print the same assessment hash
    And both runs write the same SARIF log

  Scenario: An uncommitted edit gives a new hash and is recorded as dirty (SC9)
    Given the coding agent has run earnest check --stage "construction/code-generation"
    And the coding agent has an uncommitted edit to "src/checkout/auth.py"
    When the coding agent runs earnest check --stage "construction/code-generation"
    Then the assessment hash differs from the first run's
    And the run header records the same commit as dirty

  Scenario: What the maintainer's approval adds to the audit log leaves the hash as it was (SC9)
    Given the coding agent has run earnest check --stage "construction/code-generation"
    And the repo maintainer approves "construction/code-generation" at the gate
    When the coding agent runs earnest check --stage "construction/code-generation"
    Then the assessment hash equals the first run's
    And the run header records the repository as not dirty

  Scenario: After a revision bump every place left at the old revision is flagged (SC5)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer's change is committed on a task branch
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule                    | file                                                                                              | line | level | position | stage                           |
      | earnest/unbumped-change | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 8    | error | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 3    | note  | current  | inception/requirements-analysis |
      | earnest/outdated        | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | note  | ahead    | construction/code-generation    |
      | earnest/outdated        | src/checkout/auth.py                                                                              | 4    | note  | ahead    | construction/code-generation    |
      | earnest/outdated        | tests/test_auth.py                                                                                | 4    | note  | ahead    | construction/code-generation    |
      | earnest/unplanned       | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | note  | ahead    | construction/code-generation    |
    And the finding at requirements.md line 3 names the approval of "inception/requirements-analysis" and the current revision 2
    And the check exits non-zero

  Scenario: After the bump the requirements stage waits for a fresh approval (SC5, SC8)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer's change is committed on a task branch
    When the coding agent runs earnest plan
    Then the plan lists these stages in route order:
      | stage                           | status   | approval |
      | inception/requirements-analysis | not done | outdated |
      | construction/code-generation    | not done | none     |
      | construction/build-and-test     | not done | none     |
    And the frontier is "inception/requirements-analysis"

  Scenario: The stage that awaits its fresh approval passes its own check (SC5, SC9)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer's change is committed on a task branch
    And the repo maintainer restores the approved text of "req~lockout-notice~1"
    When the coding agent runs earnest check --stage "inception/requirements-analysis"
    Then the SARIF log holds exactly these findings:
      | rule             | file                                                                                         | line | level | position | stage                           |
      | earnest/outdated | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md | 3    | note  | current  | inception/requirements-analysis |
    And the SARIF log gives the stage status "not done" with its approval "outdated"
    And the check exits zero

  Scenario: A fresh approval replaces the old one and the work list moves into scope (SC5, SC8)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer's change is committed on a task branch
    And the repo maintainer restores the approved text of "req~lockout-notice~1"
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    When the coding agent runs earnest plan
    Then the plan lists these stages in route order:
      | stage                           | status   | approval       |
      | inception/requirements-analysis | done     | current, human |
      | construction/code-generation    | not done | none           |
      | construction/build-and-test     | not done | none           |
    And the frontier is "construction/code-generation"

  Scenario: After a fresh approval the findings left at the old revision are in scope at the next stage (SC5)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer's change is committed on a task branch
    And the repo maintainer restores the approved text of "req~lockout-notice~1"
    And the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the repo maintainer approves "inception/requirements-analysis" at the gate
    When the coding agent runs earnest check
    Then the SARIF log holds exactly these findings:
      | rule              | file                                                                                              | line | level   | position | stage                        |
      | earnest/outdated  | aidlc/spaces/default/intents/260926-checkout/construction/code-generation/code-generation-plan.md | 7    | error   | current  | construction/code-generation |
      | earnest/outdated  | src/checkout/auth.py                                                                              | 4    | error   | current  | construction/code-generation |
      | earnest/outdated  | tests/test_auth.py                                                                                | 4    | error   | current  | construction/code-generation |
      | earnest/unplanned | aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis/requirements.md      | 13   | warning | current  | construction/code-generation |
    And the check exits non-zero

  Scenario: A held hash that no approval names is no baseline (SC5)
    Given the coding agent has run earnest check --stage "construction/code-generation"
    And the coding agent has an uncommitted edit to the body of "task~notify-lockout~1"
    When the coding agent runs earnest check
    Then the SARIF log holds no earnest/unbumped-change finding

  Scenario: A stage check before the approval replaces the held hash (SC5)
    Given the coding agent has run earnest check --stage "construction/code-generation"
    And the coding agent has an uncommitted edit to the body of "task~notify-lockout~1"
    When the coding agent runs earnest check --stage "construction/code-generation"
    Then the SARIF log holds no earnest/unbumped-change finding
    And the record holds a different body hash for "task~notify-lockout~1" than the first run held

  Scenario: A missing record is stated, not silent (SC5)
    When the coding agent runs earnest check
    Then the summary states that the record is absent and the body-hash baseline is unavailable

  Scenario: A rejected gate after an approval reopens the stage (SC8)
    Given the audit log gains a GATE_REJECTED row for "requirements-analysis" after its approval
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "none"
    And the frontier is "inception/requirements-analysis"

  Scenario: An approval from before a workflow restart does not count (SC8)
    Given the audit log gains a WORKFLOW_STARTED row after the approval
    And the audit log gains a fresh STAGE_SKIPPED row after the restart for each stage the state file marks skipped
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "none"
    And the frontier is "inception/requirements-analysis"

  Scenario: The audit shards of two clones are read as one log (SC8)
    Given the requirements approval sits in a second shard "fixture-0000aaaa.md", which sorts before the first shard, written later than the first shard's WORKFLOW_STARTED row
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "current, human"

  Scenario: An approval row without the fork's fields counts and never goes stale (SC8)
    Given the approval row names no Assessment Hash, Items or Approved By
    And the repo maintainer's change is committed on a task branch
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "current"
    And the frontier is "construction/code-generation"

  Scenario: A stage marked skipped with no audited skip stays on the route and is flagged (SC8)
    Given the state file marks "deployment-pipeline" as skipped and the audit log holds no skip row for it
    When the coding agent runs earnest check
    Then the SARIF log holds exactly one earnest/route-mismatch finding, at the "deployment-pipeline" row of the state file, naming the audit row that is missing
    And the plan lists "operation/deployment-pipeline" among the stages
    And the check exits non-zero

  Scenario: A backward jump resets the approval of its target stage (SC8)
    Given the audit log gains a STAGE_JUMPED row with direction BACKWARD and target "requirements-analysis" after the approval
    And the state file resets the marks of every later stage marked EXECUTE to pending
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "none"
    And the frontier is "inception/requirements-analysis"
    And the plan lists "operation/deployment-pipeline" and "operation/deployment-execution" among the stages

  Scenario: A forward jump leaves approvals standing (SC8)
    Given the audit log gains a STAGE_JUMPED row with direction FORWARD and target "build-and-test" after the approval
    And the audit log gains a STAGE_SKIPPED row of kind jump for "code-generation", which the state file marks skipped
    When the coding agent runs earnest plan
    Then "inception/requirements-analysis" has the approval "current, human"
    And the plan does not list "construction/code-generation"
    And the frontier is "construction/build-and-test"

  Scenario: A rejected approval freezes no body hash (SC5)
    Given the coding agent has run earnest check --stage "inception/requirements-analysis"
    And the audit log gains a GATE_REJECTED row for "requirements-analysis" after its approval
    And the coding agent has an uncommitted edit to the body of "req~lockout-notice~1"
    When the coding agent runs earnest check
    Then the SARIF log holds no earnest/unbumped-change finding

  Scenario: A route with per-unit stages is refused by the plan (SC8)
    Given the state file marks "units-generation" as EXECUTE and not skipped
    When the coding agent runs earnest plan
    Then the plan exits with code 2, with empty stdout
    And stderr is one line that names the unsupported per-unit route

  Scenario: A route with per-unit stages is refused by the stage check (SC9)
    Given the state file marks "units-generation" as EXECUTE and not skipped
    When the coding agent runs earnest check --stage "construction/code-generation"
    Then the check exits with code 2, with empty stdout
    And stderr is one line that names the unsupported per-unit route
    And Git lists no new file
```

- [ ] **Step 7: Write the step module**

Create `packages/earnest/tests/steps/test_stage_status.py`, which defines every step the feature uses, so that no failure is a missing step. Two steps are strengthened so that no scenario passes against a binary without `plan` and `--stage`: the `Given` that has run `check --stage` asserts that the run did not exit 2 and that the record holds that stage's run header, and `the repository is unchanged` first asserts that the plan printed a SARIF log. The Gherkin stays as ratified; the strengthening lives here:

```python
"""Steps for tests/features/stage_status.feature: `earnest plan` and `earnest check --stage` over seeded-change."""

import json
import re

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.sarif import git_output, located, rows, run_earnest, sarif_run


scenarios("stage_status.feature")

RECORD = "aidlc/spaces/default/intents/260926-checkout"
STATE = f"{RECORD}/aidlc-state.md"
SHARD = f"{RECORD}/audit/fixture-a1b2c3d4.md"
REQUIREMENTS = f"{RECORD}/inception/requirements-analysis/requirements.md"
PLAN = f"{RECORD}/construction/code-generation/code-generation-plan.md"
UNSUPPORTED = "earnest: unsupported route: units-generation is on the route, so per-unit stages"
HASH_LINE = re.compile(r"^assessment (\S+): (sha256:[0-9a-f]{64}) \((?:done|not done)\)$", re.MULTILINE)
ROW = re.compile(r"^- \[.\] (\S+) — (EXECUTE|SKIP)")
SKIPPED_EXECUTE_ROW = re.compile(r"^- \[S\] (\S+) — EXECUTE", re.MULTILINE)


@pytest.fixture
def memory():
    """What a scenario remembers between steps: the stage, hash and bodies of its first stage check, a jump's target."""
    return {}


def read(repo, path):
    return (repo / path).read_text(encoding="utf-8")


def write(repo, path, text):
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text, encoding="utf-8")


def block(event, timestamp, fields=()):
    """Return one audit block as AI-DLC writes it: a heading, Timestamp, Event, the fields, then the rule line."""
    heading = event.replace("_", " ").title()
    lines = [f"## {heading}", f"**Timestamp**: {timestamp}", f"**Event**: {event}"]
    lines += [f"**{name}**: {value}" for name, value in fields]
    return "\n".join([*lines, "---"]) + "\n"


def append_block(repo, event, timestamp, fields=()):
    write(repo, SHARD, read(repo, SHARD) + block(event, timestamp, fields))


def with_mark(row, mark):
    """Return a Stage Progress row with its checkbox mark replaced."""
    return f"- [{mark}]{row[5:]}"


def intent_plan(run):
    """Return the one intent's plan from the SARIF log of a `plan` run."""
    return sarif_run(run.stdout)["properties"]["plan"]["intents"][0]


def approval_text(stage):
    """Return a stage's approval as the tables write it: `current, human` for a current approval, else the bare word."""
    by = stage["approvedBy"]
    return f"current, {by}" if stage["approval"] == "current" and by else stage["approval"]


def printed_hash(run):
    match = HASH_LINE.search(run.stderr)
    assert match, run.stderr
    return match.group(2)


def record(repo):
    return json.loads(read(repo, ".earnest/assessment.json"))


def header(repo, stage):
    return record(repo)["runs"][f"{RECORD}/{stage}"]


def results(run):
    return sarif_run(run.stdout)["results"]


def messages(run, rule):
    return [result["message"]["text"] for result in results(run) if result["ruleId"] == rule]


# Background and the steps that change the repository.


@given(
    parsers.parse(
        'the repo maintainer\'s "{name}" repository at its base commit, with the requirements stage approved'
    ),
    target_fixture="repo",
)
def maintainer_repository(fixture_repo, name):
    repo = fixture_repo(name)
    assert "**Event**: GATE_APPROVED" in read(repo, SHARD)
    return repo


@given(parsers.parse('the coding agent has run earnest check --stage "{stage}"'))
def agent_has_run_stage_check(repo, memory, stage):
    run = run_earnest(repo, "check", "--stage", stage)
    assert run.returncode != 2, run.stderr  # the run happened: a missing command or a refusal exits 2
    header(repo, stage)  # and the record holds that stage's run header
    memory["stage"] = stage
    memory.setdefault("hash", printed_hash(run))
    memory.setdefault("bodies", record(repo)["bodies"])


@given("the repo maintainer's change is committed on a task branch")
def change_committed(repo, commit_overlay):
    commit_overlay(repo, "seeded-change", "task/add-limiter-window")


@given(parsers.parse('the coding agent has an uncommitted edit to "{path}"'))
def uncommitted_edit(repo, path):
    write(repo, path, read(repo, path) + "LOCKOUT_WINDOW = 15\n")


@given(parsers.parse('the coding agent has an uncommitted edit to the body of "{item}"'))
def uncommitted_body_edit(repo, item):
    for path in (REQUIREMENTS, PLAN):
        lines = read(repo, path).split("\n")
        if f"`{item}`" in lines:
            lines[lines.index(f"`{item}`") + 2] += " (edited)"  # the id line, a blank line, then the first body line
            write(repo, path, "\n".join(lines))
            return
    pytest.fail(f"no id line for {item}")


@given(parsers.parse('the repo maintainer makes "{first}" wait on "{second}", which already waits on it'))
def task_cycle(repo, first, second):
    lines = read(repo, PLAN).split("\n")
    assert (lines[2], lines[7]) == (f"`{first}`", "")
    lines[7] = f"Depends: {second}"
    write(repo, PLAN, "\n".join(lines))


@given(parsers.parse('the repo maintainer restores the approved text of "{item}"'))
def restore_text(repo, item):
    assert item == "req~lockout-notice~1", item
    text = read(repo, REQUIREMENTS)
    assert "how long the lockout lasts." in text
    write(repo, REQUIREMENTS, text.replace("how long the lockout lasts.", "when they may try again."))


@given(parsers.parse('the repo maintainer approves "{stage}" at the gate'))
def approve_at_gate(repo, stage):
    held = header(repo, stage)
    fields = [
        ("Stage", stage.split("/")[1]),
        ("User Input", "Approve"),
        ("Assessment Hash", held["hash"]),
        ("Items", ", ".join(held["items"])),
        ("Approved By", "human"),
    ]
    append_block(repo, "GATE_APPROVED", "2026-09-26T12:00:00Z", fields)


@given(parsers.parse('the audit log gains a GATE_REJECTED row for "{slug}" after its approval'))
def audit_rejection(repo, slug):
    append_block(repo, "GATE_REJECTED", "2026-09-26T11:00:00Z", [("Stage", slug), ("Feedback", "Rework the limits.")])


@given("the audit log gains a WORKFLOW_STARTED row after the approval")
def audit_restart(repo):
    append_block(repo, "WORKFLOW_STARTED", "2026-09-26T11:00:00Z", [("Scope", "bugfix"), ("Request", "Start again.")])


@given("the audit log gains a fresh STAGE_SKIPPED row after the restart for each stage the state file marks skipped")
def audit_fresh_skips(repo):
    for number, slug in enumerate(SKIPPED_EXECUTE_ROW.findall(read(repo, STATE))):
        fields = [("Stage", slug), ("Reason", "skipped again"), ("Skip Kind", "conditional-runtime")]
        append_block(repo, "STAGE_SKIPPED", f"2026-09-26T11:10:{number:02d}Z", fields)


@given(
    parsers.parse(
        'the requirements approval sits in a second shard "{name}", which sorts before the first shard,'
        " written later than the first shard's WORKFLOW_STARTED row"
    )
)
def approval_in_second_shard(repo, name):
    shard = read(repo, SHARD)
    start = shard.index("## Gate Approved")
    write(repo, SHARD, shard[:start])
    write(repo, f"{RECORD}/audit/{name}", shard[start:])
    assert name < SHARD.rsplit("/", 1)[1]


@given("the approval row names no Assessment Hash, Items or Approved By")
def approval_without_fork_fields(repo):
    dropped = ("**Assessment Hash**", "**Items**", "**Approved By**")
    write(repo, SHARD, "\n".join(line for line in read(repo, SHARD).split("\n") if not line.startswith(dropped)))


@given(parsers.parse('the state file marks "{slug}" as skipped and the audit log holds no skip row for it'))
def unaudited_skip(repo, slug):
    assert f"- [S] {slug} — EXECUTE" in read(repo, STATE)
    blocks = read(repo, SHARD).split("---\n")
    kept = [text for text in blocks if not ("**Event**: STAGE_SKIPPED" in text and f"**Stage**: {slug}\n" in text)]
    assert len(kept) == len(blocks) - 1
    write(repo, SHARD, "---\n".join(kept))


@given(
    parsers.parse(
        'the audit log gains a STAGE_JUMPED row with direction {direction} and target "{target}" after the approval'
    )
)
def audit_jump(repo, memory, direction, target):
    memory["target"] = target
    fields = [("Direction", direction), ("Source", "code-generation"), ("Target", target), ("Scope", "bugfix")]
    append_block(repo, "STAGE_JUMPED", "2026-09-26T11:00:00Z", fields)


@given("the state file resets the marks of every later stage marked EXECUTE to pending")
def reset_later_marks(repo, memory):
    after = False
    lines = []
    for line in read(repo, STATE).split("\n"):
        row = ROW.match(line)
        if row and after and row.group(2) == "EXECUTE":
            lines.append(with_mark(line, " "))
        elif row and row.group(1) == memory["target"]:
            after = True
            lines.append(with_mark(line, "-"))  # the target is in progress again, as upstream's jump leaves it
        else:
            lines.append(line)
    write(repo, STATE, "\n".join(lines))


@given(
    parsers.parse(
        'the audit log gains a STAGE_SKIPPED row of kind jump for "{slug}", which the state file marks skipped'
    )
)
def audit_jump_skip(repo, slug):
    fields = [("Stage", slug), ("Reason", "Skipped by jump to build-and-test (forward)"), ("Skip Kind", "jump")]
    append_block(repo, "STAGE_SKIPPED", "2026-09-26T11:00:01Z", fields)
    state = read(repo, STATE)
    assert f"- [x] {slug} — EXECUTE" in state
    write(repo, STATE, state.replace(f"- [x] {slug} — EXECUTE", f"- [S] {slug} — EXECUTE"))


@given(parsers.parse('the state file marks "{slug}" as EXECUTE and not skipped'))
def execute_stage(repo, slug):
    state = read(repo, STATE)
    old = f"- [S] {slug} — SKIP: not in bugfix scope"
    assert old in state
    write(repo, STATE, state.replace(old, f"- [ ] {slug} — EXECUTE: needed"))


# The commands.


@when("the coding agent runs earnest plan", target_fixture="run")
def agent_runs_plan(repo):
    return run_earnest(repo, "plan")


@when("the coding agent runs earnest plan twice", target_fixture="runs")
def agent_runs_plan_twice(repo):
    return [run_earnest(repo, "plan"), run_earnest(repo, "plan")]


@when("the coding agent runs earnest check", target_fixture="run")
def agent_runs_check(repo):
    return run_earnest(repo, "check")


@when(parsers.parse('the coding agent runs earnest check --stage "{stage}"'), target_fixture="run")
def agent_runs_stage_check(repo, memory, stage):
    memory["stage"] = stage
    return run_earnest(repo, "check", "--stage", stage)


@when(parsers.parse('the coding agent runs earnest check --stage "{stage}" twice'), target_fixture="runs")
def agent_runs_stage_check_twice(repo, memory, stage):
    memory["stage"] = stage
    return [run_earnest(repo, "check", "--stage", stage), run_earnest(repo, "check", "--stage", stage)]


# What the plan prints.


@then("the plan lists these stages in route order:")
def plan_lists_stages(run, datatable):
    actual = [(stage["stage"], stage["status"], approval_text(stage)) for stage in intent_plan(run)["stages"]]
    assert actual == [(row["stage"], row["status"], row["approval"]) for row in rows(datatable)]


@then(parsers.parse('the frontier is "{stage}"'))
def frontier_is(run, stage):
    assert intent_plan(run)["frontier"] == stage


@then("the plan lists these tasks:")
def plan_lists_tasks(run, datatable):
    actual = [(task["id"], task["status"]) for task in intent_plan(run)["tasks"]]
    assert actual == [(row["task"], row["status"]) for row in rows(datatable)]


@then("the plan lists neither the initialization stages nor the stages skipped by scope or by an audited skip")
def plan_omits_stages(run):
    skipped = {"inception/reverse-engineering", "inception/units-generation"}
    skipped |= {"operation/deployment-pipeline", "operation/deployment-execution"}
    stages = [stage["stage"] for stage in intent_plan(run)["stages"]]
    assert [stage for stage in stages if stage.startswith("initialization/") or stage in skipped] == []


@then(parsers.re(r'the plan lists "(?P<first>[^"]+)"(?: and "(?P<second>[^"]+)")? among the stages'))
def plan_lists_stage(run, first, second):
    stages = [stage["stage"] for stage in intent_plan(run)["stages"]]
    assert first in stages
    assert second is None or second in stages


@then(parsers.parse('the plan does not list "{stage}"'))
def plan_does_not_list(run, stage):
    assert stage not in [entry["stage"] for entry in intent_plan(run)["stages"]]


@then("the summary names each stage with its status and approval, and the frontier")
def summary_names_stages(run):
    plan = intent_plan(run)
    lines = {line.strip() for line in run.stderr.splitlines()}
    for stage in plan["stages"]:
        assert f"{stage['stage']}: {stage['status']}, approval {approval_text(stage)}" in lines
    assert f"frontier: {plan['frontier']}" in lines


@then(parsers.parse('"{stage}" is "{status}" although the state file marks it complete'))
def typed_status_is_not_read(repo, run, stage, status):
    assert f"- [x] {stage.split('/')[1]} — EXECUTE" in read(repo, STATE)
    assert {entry["stage"]: entry["status"] for entry in intent_plan(run)["stages"]}[stage] == status


@then(parsers.parse('"{stage}" has the approval "{approval}"'))
def stage_has_approval(run, stage, approval):
    assert {entry["stage"]: approval_text(entry) for entry in intent_plan(run)["stages"]}[stage] == approval


@then("the repository is unchanged")
def repository_unchanged(repo, run):
    assert json.loads(run.stdout)["version"] == "2.1.0"  # the plan ran and printed its log
    assert git_output(repo, "status", "--porcelain", "--untracked-files=all") == ""


@then("no assessment record exists")
def no_record(repo):
    assert not (repo / ".earnest").exists()


# What a check prints and records.


@then(parsers.parse('the finding names "{item}" and says that no task delivers it'))
def unplanned_finding_names_item(run, item):
    assert any(f"`{item}`" in text and "delivered by no task" in text for text in messages(run, "earnest/unplanned"))


@then(parsers.parse('the cycle finding lists "{cycle}"'))
def cycle_finding_lists_cycle(run, cycle):
    assert any(cycle in text for text in messages(run, "earnest/cycle"))


@then("the summary prints the assessment hash")
def summary_prints_hash(run):
    printed_hash(run)


@then('the SARIF log gives the same hash and the stage status "not done"')
def sarif_gives_hash_and_status(run):
    assessment = sarif_run(run.stdout)["properties"]["assessment"]
    assert assessment["hash"] == printed_hash(run)
    assert assessment["status"] == "not done"


@then(parsers.parse('the run header for "{stage}" in the assessment record holds:'))
def run_header_holds(repo, run, stage, datatable):
    held = header(repo, stage)
    for row in rows(datatable):
        field, value = row["field"], row["value"]
        actual = held[field]
        if field == "commit":
            value = git_output(repo, "rev-parse", "HEAD").strip()
        elif field == "hash":
            value = printed_hash(run)
        elif field == "dirty":
            value = value == "true"
        elif field in {"layers", "items"}:
            actual = ", ".join(actual)
        assert actual == value, field


@then("Git lists no new file")
def git_lists_no_new_file(repo):
    assert git_output(repo, "ls-files", "--others", "--exclude-standard") == ""


@then("both runs print the same assessment hash")
def same_hash(runs):
    first, second = runs
    assert printed_hash(first) == printed_hash(second)


@then("the assessment hash differs from the first run's")
def hash_differs(run, memory):
    assert printed_hash(run) != memory["hash"]


@then("the assessment hash equals the first run's")
def hash_equals(run, memory):
    assert printed_hash(run) == memory["hash"]


@then("the run header records the same commit as dirty")
def header_dirty(repo, memory):
    held = header(repo, memory["stage"])
    assert held["commit"] == git_output(repo, "rev-parse", "HEAD").strip()
    assert held["dirty"] is True


@then("the run header records the repository as not dirty")
def header_not_dirty(repo, memory):
    assert header(repo, memory["stage"])["dirty"] is False


@then(
    parsers.parse(
        'the finding at requirements.md line 3 names the approval of "{stage}" and the current revision {revision:d}'
    )
)
def outdated_finding_names_approval(run, stage, revision):
    texts = [result["message"]["text"] for result in results(run) if located(result) == (REQUIREMENTS, 3)]
    assert any(stage in text and "approval" in text and f"revision {revision}" in text for text in texts), texts


@then('the SARIF log gives the stage status "not done" with its approval "outdated"')
def sarif_gives_outdated_status(run):
    assessment = sarif_run(run.stdout)["properties"]["assessment"]
    assert assessment["status"] == "not done"
    assert assessment["reasons"]["approval"] == "outdated"


@then("the SARIF log holds no earnest/unbumped-change finding")
def no_unbumped_change(run):
    assert "earnest/unbumped-change" not in [result["ruleId"] for result in results(run)]


@then(parsers.parse('the record holds a different body hash for "{item}" than the first run held'))
def body_hash_differs(repo, memory, item):
    assert record(repo)["bodies"][item] != memory["bodies"][item]


@then("the summary states that the record is absent and the body-hash baseline is unavailable")
def summary_states_record_absent(run):
    assert "record: absent, body-hash baseline unavailable" in run.stderr.splitlines()


@then(
    parsers.parse(
        'the SARIF log holds exactly one earnest/route-mismatch finding, at the "{slug}" row of the state file,'
        " naming the audit row that is missing"
    )
)
def route_mismatch_finding(repo, run, slug):
    found = [result for result in results(run) if result["ruleId"] == "earnest/route-mismatch"]
    assert len(found) == 1
    row = next(n for n, text in enumerate(read(repo, STATE).split("\n"), 1) if text.startswith(f"- [S] {slug} "))
    assert located(found[0]) == (STATE, row)
    text = found[0]["message"]["text"]
    assert slug in text
    assert "STAGE_SKIPPED" in text


# Exit codes and the refusal.


@then(parsers.parse("the {command} exits with code 2, with empty stdout"))
def exits_with_code_two(run, command):
    assert command in {"plan", "check"}
    assert (run.returncode, run.stdout) == (2, "")


@then("stderr is one line that names the unsupported per-unit route")
def stderr_names_unsupported_route(run):
    assert run.stderr.splitlines() == [UNSUPPORTED]
```

- [ ] **Step 8: Run the exit command and watch it fail by assertion**

```bash
uv run pytest tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -3
uv run pytest tests/steps/test_stage_status.py --no-cov -q 2>&1 | grep -c StepDefinitionNotFoundError
```

Expected: `28 failed`, then `0`: every scenario fails at its first `plan`, `--stage`, summary or table step, since the M1 binary rejects `plan` and `check --stage` with exit 2. Without the two strengthened steps scenarios 3, 16 and 26 would pass vacuously (25 failed, 3 passed). Scenarios 27 and 28 pass their exit-2-with-empty-stdout step, then fail on the one-line stderr step, because argparse prints a usage line and an error line.

- [ ] **Step 9: Run the regression run and the linters**

```bash
uv run pytest --ignore=tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
make lint
```

Expected: `145 passed`, then `make lint` exits 0.

- [ ] **Step 10: Commit**

```bash
git add tests/fixtures/seeded-change tests/features/stage_status.feature tests/steps/test_stage_status.py tests/steps/test_trace_check.py tests/conftest.py tests/sarif.py tests/integration/test_seeded_change.py
git commit -m "test: add the stage_status feature and the seeded-change fixture"
```

CI and `make test` stay red from here to Task 12 by design; nothing is pushed.

### Task 2: Source fields, code-line scans and the record-directory skips

**Files:**

- Modify: `packages/earnest/src/earnest/index.py` (`Source`, `digest`)
- Modify: `packages/earnest/src/earnest/adapters/__init__.py`, `python.py`, `typescript.py`, `gherkin.py`
- Test: `packages/earnest/tests/unit/test_adapters.py`, `packages/earnest/tests/unit/adapters/test_python.py`, `test_typescript.py`, `test_gherkin.py`

**Interfaces:**

- Consumes: `index.Line`, `index.split_lines`, `index.Source` (M1).
- Produces: `index.digest(data: bytes) -> str`, `"sha256:"` and 64 lower-case hex of the SHA-256 of `data`; `Source` gains `code_lines: frozenset[int] = frozenset()`, `digest: str = ""` and `line_count: int = 0`, appended after `fenced`, so M1's positional `Source(path, surface, lines, fenced)` calls in the tests keep working.
- Produces: `python.code_lines`, `typescript.code_lines` and `gherkin.code_lines`, each `(text: str) -> frozenset[int]`, the numbers of the lines that hold code. Python and TypeScript: a token that is no comment, blank or layout, with every line of a multi-line string or template counting. Gherkin: every line that is not blank, a comment or a tag line, doc-string lines included. `typescript.scan` and `gherkin.scan` share their tokenizer or line classifier with `code_lines`, so the two cannot disagree about what a comment or a tag is.
- Produces, in `adapters`: `scan` builds every `Source` by keyword (R34-5) with the SHA-256 of the raw bytes read, `line_count = len(split_lines(text))` and `code_lines` (empty for Markdown); `reads(path: str) -> bool`, true when a suffix has an adapter; `record_directories(paths: Iterable[str]) -> frozenset[str]`, the parent of each listed `aidlc-state.md` (`""` at the repository root); `skipped(path: str, directories: Collection[str]) -> bool`, true for the bookkeeping AI-DLC writes below one of the given record directories: its `aidlc-state.md`, everything under `audit/`, every entry whose name begins `.aidlc-` (`.aidlc-engine/` and the legacy siblings), and a `memory.md` three or more components down, in a stage directory. `scan` skips such a path before reading it, so the files never enter the evaluated tree (`02` Scanner); `plan.dirty` (Task 11) shares the predicate. A repository with no listed `aidlc-state.md` skips nothing.

- [ ] **Step 1: Write the failing tests**

Append to `packages/earnest/tests/unit/adapters/test_python.py`:

```python


def test_code_lines_skip_comments_and_blank_lines():
    text = "# [impl->req~a~1]\nx = 1  # trailing\n\n    \n# second\ny = 2\n"
    assert python.code_lines(text) == frozenset({2, 6})


def test_code_lines_cover_every_line_of_a_multiline_string():
    assert python.code_lines('y = """\n# inside\nstill\n"""\n# done\n') == frozenset({1, 2, 3, 4})


def test_code_lines_keep_what_came_before_a_tokenize_error():
    assert python.code_lines("y = 1\nif 1:\n        x=1\n    y=2\n") == frozenset({1, 2, 3})
```

Append to `packages/earnest/tests/unit/adapters/test_typescript.py`, after its existing imports are in place (`typescript` is already imported there):

```python


def test_code_lines_skip_comments_and_blank_lines():
    text = "// [impl->req~a~1]\nlet x = 1; // trailing\n\n/* block\n comment */\nlet y = 2;\n"
    assert typescript.code_lines(text) == frozenset({2, 6})


def test_code_lines_count_template_literal_lines():
    assert typescript.code_lines("const s = `a\n// not a comment\nb`;\n// done\n") == frozenset({1, 2, 3})


def test_code_lines_after_a_block_comment_on_the_same_line():
    assert typescript.code_lines("/* a\n b */ let x = 1;\n") == frozenset({2})
```

Append to `packages/earnest/tests/unit/adapters/test_gherkin.py`:

```python


def test_code_lines_skip_tags_comments_and_blank_lines():
    text = (
        "# language: en\nFeature: F\n\n  @stest:feat~a~1\n  # a note\n  Scenario: S\n    Given a note\n"
        '      """\n      @stest:feat~b~1\n\n      """\n    Then done\n'
    )
    assert gherkin.code_lines(text) == frozenset({2, 6, 7, 8, 9, 11, 12})
```

In `packages/earnest/tests/unit/test_adapters.py`, replace:

```python
from earnest import adapters
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Line
```

with:

```python
import hashlib

from earnest import adapters
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Line


RECORD = "aidlc/spaces/default/intents/260926-checkout"
```

Append to the same file:

```python


def scanned(tmp_path, paths):
    """Write each path as a file holding one tag line, scan them all, and return the paths that were read."""
    for path in paths:
        file = tmp_path / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("# [impl->req~a~1]\n", encoding="utf-8")
    return [source.path for source in adapters.scan(tmp_path, paths)]


def test_source_digest_is_of_the_raw_bytes_even_with_bad_utf8(tmp_path):
    data = b"# Caf\xe9\n\n`req~a~1`\n"
    (tmp_path / "a.md").write_bytes(data)
    (source,) = adapters.scan(tmp_path, ["a.md"])
    assert source.digest == "sha256:" + hashlib.sha256(data).hexdigest()


def test_source_carries_line_count_as_git_counts_it(tmp_path):
    files = {"a.md": b"one\ntwo\n", "b.md": b"one\ntwo", "c.md": b"a\rb\n", "d.md": b""}
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    counts = {source.path: source.line_count for source in adapters.scan(tmp_path, list(files))}
    assert counts == {"a.md": 2, "b.md": 2, "c.md": 1, "d.md": 0}


def test_source_code_lines_are_set_for_comment_surfaces_only(tmp_path):
    files = {
        "a.py": "# [impl->req~a~1]\nx = 1\n",
        "a.ts": "// [impl->req~a~1]\nlet x = 1;\n",
        "a.feature": "@stest:feat~f~1\nScenario: S\n",
        "a.md": "`req~a~1`\n",
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    found = {source.path: source.code_lines for source in adapters.scan(tmp_path, list(files))}
    assert found == {"a.py": {2}, "a.ts": {2}, "a.feature": {2}, "a.md": frozenset()}


def test_reads_is_true_for_scanned_suffixes_only():
    assert all(adapters.reads(path) for path in ("a/b.py", "c.tsx", "d.mts", "e.cts", "f.feature", "g.md", "h.ts"))
    assert not any(adapters.reads(path) for path in ("a.txt", "b.json", "c.toml", "Makefile", "d/e.yml"))


def test_scan_skips_the_state_file_and_the_audit_shards_of_a_record_directory(tmp_path):
    paths = [f"{RECORD}/aidlc-state.md", f"{RECORD}/audit/a.md", f"{RECORD}/audit/b.md", f"{RECORD}/notes.md"]
    assert scanned(tmp_path, paths) == [f"{RECORD}/notes.md"]


def test_scan_skips_engine_files_and_the_legacy_aidlc_siblings(tmp_path):
    paths = [
        f"{RECORD}/aidlc-state.md",
        f"{RECORD}/.aidlc-engine/sensors/earnest/detail.md",
        f"{RECORD}/.aidlc-sensors/detail.md",
        f"{RECORD}/.aidlc-reviews/review.md",
        f"{RECORD}/inception/requirements-analysis/requirements.md",
    ]
    assert scanned(tmp_path, paths) == [f"{RECORD}/inception/requirements-analysis/requirements.md"]


def test_scan_skips_memory_md_under_a_stage_directory_and_reads_other_markdown(tmp_path):
    paths = [
        f"{RECORD}/aidlc-state.md",
        f"{RECORD}/inception/requirements-analysis/memory.md",
        f"{RECORD}/inception/requirements-analysis/requirements.md",
        f"{RECORD}/memory.md",
        f"{RECORD}/inception/memory.md",
    ]
    assert scanned(tmp_path, paths) == [
        f"{RECORD}/inception/requirements-analysis/requirements.md",
        f"{RECORD}/memory.md",
        f"{RECORD}/inception/memory.md",
    ]


def test_scan_reads_the_artifacts_of_a_record_directory(tmp_path):
    paths = [
        f"{RECORD}/aidlc-state.md",
        f"{RECORD}/inception/requirements-analysis/requirements.md",
        f"{RECORD}/construction/code-generation/code-generation-plan.md",
        "src/checkout/auth.py",
    ]
    assert scanned(tmp_path, paths) == paths[1:]


def test_scan_without_a_state_file_skips_nothing(tmp_path):
    paths = ["audit/a.md", ".aidlc-engine/x.md", "x/inception/y/memory.md", "aidlc/spaces/default/intents/z/audit/b.md"]
    assert scanned(tmp_path, paths) == paths


def test_scan_applies_the_skips_to_each_record_directory_alone(tmp_path):
    paths = ["one/aidlc-state.md", "one/audit/a.md", "one-b/audit/a.md", "two/audit/a.md", "two/notes.md"]
    assert scanned(tmp_path, paths) == ["one-b/audit/a.md", "two/audit/a.md", "two/notes.md"]


def test_skipped_is_the_one_predicate_scan_uses():
    directories = {RECORD}
    below = ("aidlc-state.md", "audit/a.md", ".aidlc-engine/x.md", ".aidlc-sensors/y.md", "inception/stage/memory.md")
    assert all(adapters.skipped(f"{RECORD}/{path}", directories) for path in below)
    other = (
        f"{RECORD}/notes.md",
        f"{RECORD}/inception/stage/requirements.md",
        "docs/audit/a.md",
        "other/aidlc-state.md",
        f"{RECORD}-b/aidlc-state.md",
    )
    assert not any(adapters.skipped(path, directories) for path in other)
    assert adapters.skipped("audit/a.md", {""})
    paths = [f"{RECORD}/aidlc-state.md", "aidlc-state.md", "docs/a.md"]
    assert adapters.record_directories(paths) == {RECORD, ""}
```

- [ ] **Step 2: Run the new tests and watch them fail**

Run: `uv run pytest tests/unit/adapters tests/unit/test_adapters.py --no-cov -q`

Expected: `17 failed, 39 passed`. Seventeen of the 18 new tests fail (`AttributeError` for `code_lines`, `reads`, `skipped` and `record_directories`, or a missing `digest` field); `test_scan_without_a_state_file_skips_nothing` already holds, since M1 skips nothing, and the 38 earlier tests of these files pass.

- [ ] **Step 3: Add `digest` and the `Source` fields to `index.py`**

In `packages/earnest/src/earnest/index.py`, replace:

```python
import difflib
import re
```

with:

```python
import difflib
import hashlib
import re
```

In the same file, replace:

```python
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
```

with:

```python
def digest(data: bytes) -> str:
    """Return `sha256:` and the lower-case hex SHA-256 of data."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Source:
    """One listed file as its host adapter saw it.

    For Markdown, `lines` holds every line and `fenced` the lines inside code fences. For the comment and Gherkin
    surfaces, `lines` holds the comment or tag lines and `code_lines` the numbers of the lines that hold code, which
    the Region rule reads. `digest` is the digest of the raw bytes read, and `line_count` the lines Git counts.
    """

    path: str
    surface: str
    lines: tuple[Line, ...]
    fenced: frozenset[int] = frozenset()
    code_lines: frozenset[int] = frozenset()
    digest: str = ""
    line_count: int = 0
```

- [ ] **Step 4: Add `code_lines` to the three comment adapters**

In `packages/earnest/src/earnest/adapters/python.py`, replace:

```python
def _tokens(text: str) -> Iterator[tokenize.TokenInfo]:
```

with:

```python
# Tokens that stand for no code: a comment, a line break that ends no statement, and the indentation bookkeeping.
_LAYOUT = frozenset(
    {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
)


def code_lines(text: str) -> frozenset[int]:
    """Return the numbers of the lines that hold code: every line of each token that is no comment or layout.

    A string that spans lines holds code on each of them, and a file that stops tokenizing keeps what came before the
    error, as `scan` does.
    """
    found: set[int] = set()
    for token in _tokens(text):
        if token.type not in _LAYOUT:
            found.update(range(token.start[0], token.end[0] + 1))
    return frozenset(found)


def _tokens(text: str) -> Iterator[tokenize.TokenInfo]:
```

In `packages/earnest/src/earnest/adapters/typescript.py`, replace:

```python
import re

from earnest.index import Line
```

with:

```python
import re
from collections.abc import Iterator

from earnest.index import Line
```

In the same file, replace:

```python
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
```

with:

```python
    comments: list[Line] = []
    for kind, value, number in _tokens(text):
        if kind == "comment":
            comments.extend(Line(number + offset, part) for offset, part in enumerate(value.split("\n")))
    return tuple(comments)


def code_lines(text: str) -> frozenset[int]:
    """Return the numbers of the lines that hold code: every line of each token that is no comment or space.

    A string or template literal that spans lines holds code on each of them, and code after a block comment on the
    line where it ends counts, because the tokens are the ones `scan` reads.
    """
    found: set[int] = set()
    for kind, value, number in _tokens(text):
        if kind not in {"comment", "space"}:
            found.update(range(number, number + value.count("\n") + 1))
    return frozenset(found)


def _tokens(text: str) -> Iterator[tuple[str | None, str, int]]:
    """Yield each token as its kind, its text and the line it starts on."""
    operand = False  # whether the last token that is no comment or space ends an operand, so a `/` after it divides
    previous = ""  # the last token that is no comment or space
    number = 1  # the line the next token starts on
    position = 0
    while token := _TOKEN.match(text, position):
        kind, value = token.lastgroup, token.group()
        if value == "/" and not operand and previous != "<" and (regex := _REGEX.match(text, position)):
            token, kind, value = regex, "literal", regex.group()
        yield kind, value, number
        if kind not in {"comment", "space"}:
            if value != "!" or text.startswith("=", token.end()):  # a postfix `!` leaves the state as it was
                operand = _ends_operand(kind, value, previous)
            previous = value
        number += value.count("\n")
        position = token.end()
```

In `packages/earnest/src/earnest/adapters/gherkin.py`, replace:

```python
import re

from earnest.index import Line, split_lines
```

with:

```python
import re
from collections.abc import Iterator

from earnest.index import Line, split_lines
```

In the same file, replace:

```python
    tags: list[Line] = []
    doc_string = ""
    after_step = False
    for line in split_lines(text):
        stripped = line.text.strip()
        if doc_string:
            doc_string = "" if stripped.startswith(doc_string) else doc_string
        elif after_step and stripped.startswith(_DOC_STRINGS):
            doc_string = stripped[:3]
        elif stripped.startswith("@"):
            tags.append(Line(line.number, re.split(r"\s#", line.text, maxsplit=1)[0]))
        if stripped and not stripped.startswith("#"):
            after_step = stripped.startswith(_STEPS)
    return tuple(tags)
```

with:

```python
    return tuple(
        Line(line.number, re.split(r"\s#", line.text, maxsplit=1)[0])
        for line, kind in _classified(text)
        if kind == "tag"
    )


def code_lines(text: str) -> frozenset[int]:
    """Return the numbers of the lines that hold code: every line that is no tag line, comment or blank.

    The lines of a doc string, its delimiters included, are code, and a `#` or `@` line inside one is text.
    """
    return frozenset(line.number for line, kind in _classified(text) if _holds_code(line, kind))


def _holds_code(line: Line, kind: str) -> bool:
    stripped = line.text.strip()
    return bool(stripped) and kind != "tag" and (kind == "doc" or not stripped.startswith("#"))


def _classified(text: str) -> Iterator[tuple[Line, str]]:
    """Yield each line with its kind: `tag` for a tag line, `doc` for a doc-string line, else `plain`."""
    doc_string = ""
    after_step = False
    for line in split_lines(text):
        stripped = line.text.strip()
        kind = "plain"
        if doc_string:
            kind = "doc"
            doc_string = "" if stripped.startswith(doc_string) else doc_string
        elif after_step and stripped.startswith(_DOC_STRINGS):
            kind = "doc"
            doc_string = stripped[:3]
        elif stripped.startswith("@"):
            kind = "tag"
        yield line, kind
        if stripped and not stripped.startswith("#"):
            after_step = stripped.startswith(_STEPS)
```

- [ ] **Step 5: Rewrite the adapter by suffix in `adapters/__init__.py`**

Replace the whole of `packages/earnest/src/earnest/adapters/__init__.py` with:

```python
"""Host adapters: each listed file's adapter, picked by suffix, hands its lines to the grammar."""

from collections.abc import Callable, Collection, Iterable
from pathlib import Path, PurePosixPath

from earnest.adapters import gherkin, markdown, python, typescript
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Line, Source, digest, split_lines


STATE = "aidlc-state.md"
_STAGE_DEPTH = 3  # `<phase>/<slug>/memory.md` below a record directory

_Scan = Callable[[str], tuple[tuple[Line, ...], frozenset[int]]]
_Code = Callable[[str], frozenset[int]]


def _unfenced(scan: Callable[[str], tuple[Line, ...]]) -> _Scan:
    return lambda text: (scan(text), frozenset())


# Each suffix an adapter reads: its surface, the scan that gives its lines and the lines inside its code fences, and
# the scan that gives the lines that hold code (None for Markdown, which holds no code lines).
_SCANS: dict[str, tuple[str, _Scan, _Code | None]] = {
    ".md": (MARKDOWN, markdown.scan, None),
    ".feature": (GHERKIN, _unfenced(gherkin.scan), gherkin.code_lines),
    ".py": (COMMENT, _unfenced(python.scan), python.code_lines),
    ".ts": (COMMENT, _unfenced(typescript.scan), typescript.code_lines),
    ".tsx": (COMMENT, _unfenced(typescript.scan), typescript.code_lines),
    ".mts": (COMMENT, _unfenced(typescript.scan), typescript.code_lines),
    ".cts": (COMMENT, _unfenced(typescript.scan), typescript.code_lines),
}


def reads(path: str) -> bool:
    """Return whether an adapter reads files with the suffix of path."""
    return PurePosixPath(path).suffix in _SCANS


def record_directories(paths: Iterable[str]) -> frozenset[str]:
    """Return the record directories among the listed paths: the parent of each `aidlc-state.md`, `""` at the root."""
    parents = (PurePosixPath(path).parent for path in paths if PurePosixPath(path).name == STATE)
    return frozenset("" if parent == PurePosixPath(".") else parent.as_posix() for parent in parents)


def skipped(path: str, directories: Collection[str]) -> bool:
    """Return whether path is bookkeeping that AI-DLC writes inside one of the record directories, which no scan reads.

    Below a record directory these are its `aidlc-state.md`, everything under `audit/`, every entry whose name begins
    `.aidlc-` (`.aidlc-engine/` and the legacy siblings), and a `memory.md` in a stage directory, three or more
    components down. Directories compare by whole components, so `one` never holds `one-b`.
    """
    parts = PurePosixPath(path).parts
    bases = (PurePosixPath(directory).parts for directory in directories)
    return any(parts[: len(base)] == base and _is_bookkeeping(parts[len(base) :]) for base in bases)


def _is_bookkeeping(below: tuple[str, ...]) -> bool:
    return (
        below == (STATE,)
        or (len(below) > 1 and below[0] == "audit")
        or (bool(below) and below[0].startswith(".aidlc-"))
        or (len(below) >= _STAGE_DEPTH and below[-1] == "memory.md")
    )


def scan(root: Path, paths: Iterable[str]) -> list[Source]:
    """Scan each listed file whose suffix an adapter reads, in the order given, which `git.work_tree_files` sorts.

    Other files are skipped, and so are the bookkeeping files of a record directory (see `skipped`), files gone from
    the work tree, symlinks, whose target Git does not hold, binary files, which hold a NUL byte in their first 8000
    bytes as Git judges, and code files with no `~`, since every tag holds one. Text decodes as UTF-8, with a byte
    order mark dropped and each byte that is not UTF-8 replaced. Each source carries the digest of the raw bytes.

    Raises:
        OSError: a file cannot be read.
    """
    listed = list(paths)
    directories = record_directories(listed)
    sources: list[Source] = []
    for path in listed:
        adapter = _SCANS.get(PurePosixPath(path).suffix)
        file = root / path
        if adapter is None or skipped(path, directories) or file.is_symlink() or not file.is_file():
            continue
        surface, read, code = adapter
        data = file.read_bytes()
        if b"\0" in data[:8000] or (surface == COMMENT and b"~" not in data):
            continue
        text = data.decode("utf-8-sig", errors="replace")
        lines, fenced = read(text)
        sources.append(
            Source(
                path=path,
                surface=surface,
                lines=lines,
                fenced=fenced,
                code_lines=code(text) if code else frozenset(),
                digest=digest(data),
                line_count=len(split_lines(text)),
            )
        )
    return sources
```

- [ ] **Step 6: Run the new tests and watch them pass**

Run: `uv run pytest tests/unit/adapters tests/unit/test_adapters.py --no-cov -q`

Expected: `56 passed`: the 38 tests these files held before, plus the 18 new ones.

- [ ] **Step 7: Run the regression run and the linters**

```bash
uv run pytest --ignore=tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
make lint
```

Expected: `163 passed`, then `make lint` exits 0.

- [ ] **Step 8: Commit**

```bash
git add src/earnest/index.py src/earnest/adapters tests/unit/test_adapters.py tests/unit/adapters
git commit -m "feat: carry code lines, a digest and a line count on every source and skip AI-DLC's files"
```

### Task 3: Body hash and the Region rule, `index.py`

**Files:**

- Modify: `packages/earnest/src/earnest/index.py`
- Test: `packages/earnest/tests/unit/test_index.py`

**Interfaces:**

- Consumes: `Source.code_lines`, `Source.line_count`, `Source.fenced` and `digest` (Task 2).
- Produces: `Item.body_hash: str`, the digest of the bytes that Revision lifecycle (B4) fixes: the lines after the id line up to the next id line or ATX heading, fenced lines included and key lines (the loose `_KEY` match) left out unless fenced; each line loses one carriage return before its line feed, then trailing spaces and tabs, and is dropped when nothing is left (a line of other Unicode whitespace stays); the rest are joined by `\n`, with no final `\n`, and encoded as UTF-8. The field is `field(default="", compare=False)`, so item equality is what M1's tests already assume. `_spans` keeps fenced lines in the item's span and `_markdown` hands `_keys` only the unfenced ones (R34-1).
- Produces: `Region(target: Id, path: str, first: int, last: int)` and `Index.regions: tuple[Region, ...] = ()`, a defaulted last field so M1's positional `Index(items, links, misses)` calls keep working. `build_index` fills it for the comment and Gherkin surfaces and sorts it by `(path, first, str(target))`. A tag governs its own line to the line before the next group of tags in the file, or to `line_count`, and not past the last tag's own line. Tags with no code line from one to the next (a code line on a tag's own line counts) are one group and share one region, which starts at the group's first tag. The regions of one id in one file merge when they overlap or touch.
- Produces: `Status = Literal["resolved", "outdated", "predated", "orphaned"]`, the type of `Resolution.status` (R34-4).

- [ ] **Step 1: Write the failing tests**

In `packages/earnest/tests/unit/test_index.py`, replace:

```python
import pytest

from earnest.index import COMMENT, GHERKIN, MARKDOWN, Id, Item, Line, Link, Source, build_index, split_lines
```

with:

```python
import hashlib

import pytest

from earnest import adapters
from earnest.index import (
    COMMENT,
    GHERKIN,
    MARKDOWN,
    Id,
    Item,
    Line,
    Link,
    Region,
    Source,
    build_index,
    digest,
    split_lines,
)
```

Append to the same file:

```python


def body_hash(text, fenced=frozenset()):
    return build_index([markdown(text, fenced)]).items[0].body_hash


def sha(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_body_hash_ignores_blank_lines_and_trailing_whitespace():
    plain = "`req~a~1`\n\nWhen x, the s shall y.\n\n"
    noisy = "`req~a~1`\nWhen x, the s shall y.   \n\n\n\t\n"
    assert body_hash(plain) == body_hash(noisy)


def test_body_hash_ignores_key_lines_and_where_they_sit():
    above = "`req~a~1`\n\nCovers: feat~f~1\nNeeds: impl\n\nWhen x, the s shall y.\n"
    below = "`req~a~1`\n\nWhen x, the s shall y.\n\nNeeds: impl\n\nCovers: feat~f~1, feat~g~1\n"
    assert body_hash(above) == body_hash(below) == sha("When x, the s shall y.")


def test_body_hash_counts_fenced_lines():
    text = "`req~a~1`\n\nBody.\n\n```text\ncode\n```\n"
    assert body_hash(text, frozenset({5, 6, 7})) == sha("Body.\n```text\ncode\n```")
    assert body_hash(text, frozenset({5, 6, 7})) != body_hash("`req~a~1`\n\nBody.\n")


def test_fenced_key_like_line_stays_body_and_keys_nothing():
    text = "`req~a~1`\n\nBody.\n\n```\nCovers: feat~z~9\n```\n"
    index = build_index([markdown(text, frozenset({5, 6, 7}))])
    assert index.links == ()
    assert index.items[0].body_hash == sha("Body.\n```\nCovers: feat~z~9\n```")


def test_body_hash_changes_with_one_word():
    assert body_hash("`req~a~1`\n\nThe s shall y.\n") != body_hash("`req~a~1`\n\nThe s shall z.\n")


def test_item_without_body_hashes_the_empty_body():
    assert body_hash("`req~a~1`\n") == digest(b"") == sha("")


def test_each_item_hashes_its_own_span():
    index = build_index([markdown("`req~a~1`\n\nOne.\n\n`req~b~1`\n\nTwo.\n")])
    assert [item.body_hash for item in index.items] == [sha("One."), sha("Two.")]


def test_crlf_and_lf_bodies_hash_alike():
    lf = "`req~a~1`\n\nOne.\nTwo.\n"
    assert body_hash(lf.replace("\n", "\r\n")) == body_hash(lf)


def test_body_hash_is_the_sha256_of_utf8_lines_joined_by_lf_with_no_final_lf():
    text = "`req~a~1`\n\nalpha caf\u00e9\n\n  beta\n"
    expected = "sha256:" + hashlib.sha256("alpha caf\u00e9\n  beta".encode()).hexdigest()
    assert body_hash(text) == expected


def test_body_hash_removes_only_trailing_spaces_and_tabs():
    base = body_hash("`req~a~1`\n\nx y\n")
    assert body_hash("`req~a~1`\n\nx y \t \n") == base
    assert body_hash("`req~a~1`\n\n  x y\n") != base
    assert body_hash("`req~a~1`\n\nx  y\n") != base


def test_a_line_of_other_unicode_whitespace_is_not_blank():
    assert body_hash("`req~a~1`\n\na\n\u00a0\nb\n") == sha("a\n\u00a0\nb")
    assert body_hash("`req~a~1`\n\na\n\u00a0\nb\n") != body_hash("`req~a~1`\n\na\nb\n")


def test_body_hash_of_bad_bytes_uses_the_replacement_character(tmp_path):
    (tmp_path / "a.md").write_bytes(b"`req~a~1`\n\nCaf\xe9\n")
    index = build_index(adapters.scan(tmp_path, ["a.md"]))
    assert index.items[0].body_hash == sha("Caf\ufffd")


def tagged(tags, code, count, path="src/a.py", surface=COMMENT):
    """Return a source with a tag comment at each (line, id), code on the given lines, and count lines in all."""
    lines = tuple(Line(number, f"# [impl->{item}]") for number, item in tags)
    return Source(path, surface, lines, code_lines=frozenset(code), line_count=count)


A, B = Id("req", "a", 1), Id("req", "b", 1)


def test_region_runs_from_a_tag_to_the_next_tag():
    source = tagged([(1, "req~a~1"), (5, "req~b~1")], {2, 3, 4, 6, 7}, 8)
    assert build_index([source]).regions == (Region(A, "src/a.py", 1, 4), Region(B, "src/a.py", 5, 8))


def test_region_of_the_last_tag_ends_at_the_end_of_the_file():
    assert build_index([tagged([(3, "req~a~1")], {4, 5}, 6)]).regions == (Region(A, "src/a.py", 3, 6),)
    assert build_index([tagged([(3, "req~a~1")], {4, 5}, 0)]).regions == (Region(A, "src/a.py", 3, 3),)


def test_stacked_tags_share_the_region_that_follows():
    stacked = tagged([(1, "req~a~1"), (2, "req~b~1")], {3, 4}, 5)
    assert build_index([stacked]).regions == (Region(A, "src/a.py", 1, 5), Region(B, "src/a.py", 1, 5))
    on_code = tagged([(1, "req~a~1"), (2, "req~b~1")], {1, 3, 4}, 5)  # a code line on the tag's own line is code
    assert build_index([on_code]).regions == (Region(A, "src/a.py", 1, 1), Region(B, "src/a.py", 2, 5))


def test_repeated_tags_for_one_id_union_their_regions():
    joined = tagged([(1, "req~a~1"), (4, "req~a~1"), (7, "req~b~1")], {2, 3, 5, 6, 8, 9}, 9)
    assert build_index([joined]).regions == (Region(A, "src/a.py", 1, 6), Region(B, "src/a.py", 7, 9))
    apart = tagged([(1, "req~a~1"), (4, "req~b~1"), (7, "req~a~1")], {2, 3, 5, 6, 8, 9}, 9)
    assert build_index([apart]).regions == (
        Region(A, "src/a.py", 1, 3),
        Region(B, "src/a.py", 4, 6),
        Region(A, "src/a.py", 7, 9),
    )


def test_tags_in_different_files_never_share_a_region():
    one = tagged([(1, "req~a~1")], {2}, 3, path="src/a.py")
    two = tagged([(1, "req~a~1")], {2, 3}, 4, path="src/b.py")
    assert build_index([two, one]).regions == (Region(A, "src/a.py", 1, 3), Region(A, "src/b.py", 1, 4))


def test_gherkin_tags_have_regions():
    lines = (Line(1, "@stest:feat~f~1"),)
    source = Source("tests/a.feature", GHERKIN, lines, code_lines=frozenset({2, 3}), line_count=4)
    assert build_index([source]).regions == (Region(Id("feat", "f", 1), "tests/a.feature", 1, 4),)
```

Run: `uv run pytest tests/unit/test_index.py --no-cov -q`

Expected: collection fails with `ImportError: cannot import name 'Region' from 'earnest.index'`, `1 error`. The import resolves after Step 2, and the new tests then fail by `AttributeError` and `AssertionError` until Steps 3 and 4 land.

- [ ] **Step 2: Add `Item.body_hash`, `Region`, `Status` and `Index.regions`**

In `packages/earnest/src/earnest/index.py`, replace:

```python
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property
```

with:

```python
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import cached_property
from typing import Literal
```

In the same file, replace:

```python
@dataclass(frozen=True)
class Item:
    """A Markdown item: its id, where its id line sits, and the types on its `Needs:` line."""

    id: Id
    path: str
    line: int
    needs: tuple[str, ...] | None = None
```

with:

```python
@dataclass(frozen=True)
class Item:
    """A Markdown item: its id, where its id line sits, the types on its `Needs:` line, and its body hash.

    The body hash derives from the lines, so it takes no part in equality: two items with one id, place and needs are
    the same item.
    """

    id: Id
    path: str
    line: int
    needs: tuple[str, ...] | None = None
    body_hash: str = field(default="", compare=False)
```

In the same file, replace:

```python
@dataclass(frozen=True)
class Resolution:
    """What a written id names: its item, and `resolved`, `outdated`, `predated` or `orphaned`.

    An orphaned id carries the closest id of its own type, when one is close enough to suggest.
    """

    item: Item | None
    status: str
    closest: Id | None = None
```

with:

```python
Status = Literal["resolved", "outdated", "predated", "orphaned"]


@dataclass(frozen=True)
class Region:
    """The lines of a file that a tag governs, from `first` to `last` inclusive."""

    target: Id
    path: str
    first: int
    last: int


@dataclass(frozen=True)
class Resolution:
    """What a written id names: its item, and `resolved`, `outdated`, `predated` or `orphaned`.

    An orphaned id carries the closest id of its own type, when one is close enough to suggest.
    """

    item: Item | None
    status: Status
    closest: Id | None = None
```

In the same file, replace:

```python
    near_misses: tuple[NearMiss, ...]
```

with:

```python
    near_misses: tuple[NearMiss, ...]
    regions: tuple[Region, ...] = ()
```

- [ ] **Step 3: Build the regions in `build_index`**

In the same file, replace:

```python
    items: list[Item] = []
    links: list[Link] = []
    misses: list[NearMiss] = []
    for source in sources:
        parse = _markdown if source.surface == MARKDOWN else _tags
        found_items, found_links, found_misses = parse(source)
        items.extend(found_items)
        links.extend(found_links)
        misses.extend(found_misses)
    return Index(tuple(items), tuple(links), tuple(misses))
```

with:

```python
    items: list[Item] = []
    links: list[Link] = []
    misses: list[NearMiss] = []
    regions: list[Region] = []
    for source in sources:
        parse = _markdown if source.surface == MARKDOWN else _tags
        found_items, found_links, found_misses = parse(source)
        items.extend(found_items)
        links.extend(found_links)
        misses.extend(found_misses)
        if source.surface != MARKDOWN:
            regions.extend(_regions(source, found_links))
    return Index(tuple(items), tuple(links), tuple(misses), tuple(sorted(regions, key=_region_order)))
```

In the same file, replace:

```python
def _to_id(match: re.Match[str], first: int = 1) -> Id:
```

with:

```python
def _region_order(region: Region) -> tuple[str, int, str]:
    return region.path, region.first, str(region.target)


def _regions(source: Source, tags: Sequence[Link]) -> list[Region]:
    """Derive the regions of a file's tags by the Region rule.

    A tag governs the lines from itself to the next group of tags, or to the end of the file. Tags with no code line
    from one to the next are one group, and share the region that follows them, which starts at the group's first tag.
    A code line on a tag's own line counts as code. The regions of one id that overlap or touch merge into one.
    """
    groups: list[list[Link]] = []
    for tag in sorted(tags, key=lambda link: link.line):
        if groups and not any(line in source.code_lines for line in range(groups[-1][-1].line, tag.line)):
            groups[-1].append(tag)
        else:
            groups.append([tag])
    spans: dict[Id, list[tuple[int, int]]] = {}
    for group, after in zip(groups, [*groups[1:], None], strict=False):
        last = after[0].line - 1 if after else max(source.line_count, group[-1].line)
        for tag in group:
            spans.setdefault(tag.target, []).append((group[0].line, last))
    return [
        Region(target, source.path, first, last) for target, found in spans.items() for first, last in _merge(found)
    ]


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for first, last in sorted(spans):
        if merged and first <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], last))
        else:
            merged.append((first, last))
    return merged


def _to_id(match: re.Match[str], first: int = 1) -> Id:
```

- [ ] **Step 4: Hash each item's body**

In the same file, replace:

```python
    for item_id, number, lines in spans:
        needs, item_links, key_misses = _keys(source.path, item_id, lines)
        items.append(Item(item_id, source.path, number, needs))
```

with:

```python
    for item_id, number, lines in spans:
        keyed = [line for line in lines if line.number not in source.fenced]
        needs, item_links, key_misses = _keys(source.path, item_id, keyed)
        items.append(Item(item_id, source.path, number, needs, _body_hash(lines, source.fenced)))
```

In the same file, replace:

```python
    """Split a Markdown file into items: an id line owns the lines up to the next id line or ATX heading."""
```

with:

```python
    """Split a Markdown file into items: an id line owns the lines up to the next id line or ATX heading.

    Fenced lines belong to the item above them, and never start, end or key an item.
    """
```

In the same file, replace:

```python
        if line.number in source.fenced:
            continue  # fenced code is body, and never starts, ends or keys an item
```

with:

```python
        if line.number in source.fenced:
            if body is not None:
                body.append(line)
            continue
```

In the same file, replace:

```python
def _keys(path: str, owner: Id, lines: Iterable[Line]) -> tuple[tuple[str, ...] | None, list[Link], list[NearMiss]]:
```

with:

```python
def _body_hash(lines: Iterable[Line], fenced: frozenset[int]) -> str:
    """Return the digest of an item's body: its non-blank lines, less its key lines, joined by line feeds.

    A fenced line is body even where it looks like a key line. Each line loses one carriage return before its line
    feed, then trailing spaces and tabs, and is blank when nothing is left; other whitespace stays, so only what Git
    and an editor add at a line's end leaves the hash as it was.
    """
    stripped = [(line.number, line.text.removesuffix("\r").rstrip(" \t")) for line in lines]
    kept = [text for number, text in stripped if text and (number in fenced or _KEY.match(text) is None)]
    return digest("\n".join(kept).encode("utf-8"))


def _keys(path: str, owner: Id, lines: Iterable[Line]) -> tuple[tuple[str, ...] | None, list[Link], list[NearMiss]]:
```

- [ ] **Step 5: Run the new tests and watch them pass**

Run: `uv run pytest tests/unit/test_index.py --no-cov -q`

Expected: `78 passed`: the 60 tests the file held, plus the 18 new ones.

- [ ] **Step 6: Run the regression run and the linters**

```bash
uv run pytest --ignore=tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
make lint
```

Expected: `181 passed`, then `make lint` exits 0.

- [ ] **Step 7: Commit**

```bash
git add src/earnest/index.py tests/unit/test_index.py
git commit -m "feat: hash each item's body and derive tag regions in the index"
```

### Task 4: The record directory and the changed paths, `git.py`

**Files:**

- Modify: `packages/earnest/src/earnest/git.py`
- Test: `packages/earnest/tests/unit/test_git.py`

**Interfaces:**

- Consumes: `_git` and `GitError` (M1); the `files_repo` fixture; `git_output` from `tests/sarif.py` (Task 1).
- Produces: `_git` runs every command as `git --literal-pathspecs <args>`, so no file name is read as pathspec magic whatever a later call passes. `work_tree_files(root)` drops any path equal to `.earnest` or under `.earnest/`, tracked or not (RP1, E6). `changes(root: Path) -> list[str]`: the sorted, unique paths of one `git --no-optional-locks status --porcelain=v1 -z --untracked-files=all --no-renames`, the only status call. It lists a path that is untracked, differs from HEAD or the index (staged or not, including type changes and conflicts), or is missing from the work tree, less any path under `.earnest/` (R34-6). No path is handed to Git, since `git status` has no pathspec-file option. `--no-optional-locks` keeps the call from refreshing `.git/index` or taking `index.lock`, so `earnest plan` and a plain `earnest check` stay read-only and never hold the lock against an agent's `git add`. `git.py` knows no scanned suffix and no record directory; `plan.dirty` (Task 11) applies the evaluated-tree rule to this list.

- [ ] **Step 1: Write the failing tests**

In `packages/earnest/tests/unit/test_git.py`, replace:

```python
import re

import pytest

from earnest import git
```

with:

```python
import os
import re

import pytest

from earnest import git
from tests.sarif import git_output
```

Append to the same file:

```python


def test_work_tree_files_drops_the_record_directory(files_repo):
    repo = files_repo({"a.md": "a\n"})
    (repo / ".earnest").mkdir()
    (repo / ".earnest" / "assessment.json").write_text("{}\n", encoding="utf-8")
    assert git.work_tree_files(repo) == ["a.md"]


def test_work_tree_files_drops_a_tracked_record(files_repo):
    repo = files_repo({"a.md": "a\n", ".earnest/assessment.json": "{}\n", ".earnestry/b.md": "b\n"})
    assert git.work_tree_files(repo) == [".earnestry/b.md", "a.md"]


def test_changes_is_empty_for_a_clean_tree(files_repo):
    assert git.changes(files_repo({"a.md": "a\n", "b.md": "b\n"})) == []


def test_changes_lists_a_modified_file(files_repo):
    repo = files_repo({"a.md": "a\n", "b.md": "b\n"})
    (repo / "a.md").write_text("changed\n", encoding="utf-8")
    assert git.changes(repo) == ["a.md"]


def test_changes_lists_an_untracked_file(files_repo):
    repo = files_repo({"a.md": "a\n"})
    (repo / "docs").mkdir()
    (repo / "docs" / "new.md").write_text("new\n", encoding="utf-8")
    assert git.changes(repo) == ["docs/new.md"]


def test_changes_lists_a_staged_only_change(files_repo):
    repo = files_repo({"a.md": "a\n"})
    (repo / "a.md").write_text("changed\n", encoding="utf-8")
    git_output(repo, "add", "a.md")
    assert git.changes(repo) == ["a.md"]


def test_changes_lists_a_deleted_file_and_a_staged_deletion(files_repo):
    repo = files_repo({"a.md": "a\n", "b.md": "b\n", "c.md": "c\n"})
    (repo / "a.md").unlink()
    git_output(repo, "rm", "-q", "b.md")
    assert git.changes(repo) == ["a.md", "b.md"]


def test_changes_lists_both_paths_of_a_rename_as_separate_changes(files_repo):
    repo = files_repo({"a.md": "a\n", "b.md": "b\n"})
    git_output(repo, "mv", "a.md", "c.md")
    assert git.changes(repo) == ["a.md", "c.md"]


def test_changes_drops_the_record_directory(files_repo):
    repo = files_repo({"a.md": "a\n", ".earnest/assessment.json": "{}\n"})
    (repo / "a.md").write_text("changed\n", encoding="utf-8")
    (repo / ".earnest" / "assessment.json").write_text('{"version": 1}\n', encoding="utf-8")
    (repo / ".earnest" / "temp").write_text("x\n", encoding="utf-8")
    assert git.changes(repo) == ["a.md"]


def test_changes_reads_names_with_spaces_accents_and_glob_characters_literally(files_repo):
    names = ["docs/a b.md", "src/né.py", "x[1].md", "*.md", "dir/:(top).md"]
    repo = files_repo(dict.fromkeys(names, "a\n"))
    for name in names:
        (repo / name).write_text("changed\n", encoding="utf-8")
    assert git.changes(repo) == sorted(names)


def test_git_calls_treat_pathspec_magic_literally(files_repo):
    repo = files_repo({"a.md": "a\n", "*.md": "star\n"})
    assert git._git(repo, "ls-files", "--", "*.md") == "*.md\n"


def test_changes_leaves_the_index_alone(files_repo):
    repo = files_repo({"a.md": "a\n"})
    stamp = (repo / "a.md").stat().st_mtime_ns + 5_000_000_000  # touched, not changed: Git would refresh its entry
    os.utime(repo / "a.md", ns=(stamp, stamp))
    index = repo / ".git" / "index"
    before = (index.read_bytes(), index.stat().st_mtime_ns)
    assert git.changes(repo) == []
    assert (index.read_bytes(), index.stat().st_mtime_ns) == before
    assert not (repo / ".git" / "index.lock").exists()
```

Run: `uv run pytest tests/unit/test_git.py --no-cov -q`

Expected: `12 failed` (`AttributeError: module 'earnest.git' has no attribute 'changes'`, `work_tree_files` still listing `.earnest/` paths, and the pathspec test returning both files), and `6 passed`, the earlier tests of the file.

- [ ] **Step 2: Implement the record exclusion, `changes` and the literal calls**

In `packages/earnest/src/earnest/git.py`, replace:

```python
class GitError(Exception):
```

with:

```python
_RECORD_DIRECTORY = ".earnest"


class GitError(Exception):
```

In the same file, replace:

```python
def work_tree_files(root: Path) -> list[str]:
    """Return the files Git lists for the work tree: tracked files plus untracked files that are not ignored.

    Each path is relative to root, with forward slashes, sorted, and listed once, even a file in a merge conflict,
    which the index holds three times.
    """
    listed = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return sorted({path for path in listed.split("\0") if path})
```

with:

```python
def work_tree_files(root: Path) -> list[str]:
    """Return the files Git lists for the work tree: tracked files plus untracked files that are not ignored.

    Each path is relative to root, with forward slashes, sorted, and listed once, even a file in a merge conflict,
    which the index holds three times. Nothing under `.earnest/`, the assessment record's directory, is listed,
    whether Git ignores it or a repository tracks it.
    """
    listed = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return sorted({path for path in listed.split("\0") if path and not _in_record_directory(path)})


def changes(root: Path) -> list[str]:
    """Return the paths that differ from the commit: untracked, changed in the work tree or the index, or missing.

    One `git status` gives them, sorted and listed once, with a rename as the two paths it touches and nothing under
    `.earnest/`. `--no-optional-locks` keeps Git from refreshing `.git/index`, so a read-only command stays read-only.
    """
    listed = _git(
        root, "--no-optional-locks", "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames"
    )
    paths = {entry[3:] for entry in listed.split("\0") if entry}  # each entry is two status letters, a space, a path
    return sorted(path for path in paths if not _in_record_directory(path))
```

In the same file, replace:

```python
def _git(cwd: Path, *args: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        msg = "git is not on the PATH"
        raise GitError(msg)
    done = subprocess.run([executable, *args], cwd=cwd, capture_output=True, check=False)  # noqa: S603
    if done.returncode != 0:
        lines = map(str.strip, done.stderr.decode(errors="replace").splitlines())
        msg = next((line for line in lines if line), f"git {args[0]} failed")
        raise GitError(msg)
```

with:

```python
def _in_record_directory(path: str) -> bool:
    return path == _RECORD_DIRECTORY or path.startswith(_RECORD_DIRECTORY + "/")


def _git(cwd: Path, *args: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        msg = "git is not on the PATH"
        raise GitError(msg)
    # --literal-pathspecs: a path given to any call is a name, never a pattern, whatever `*`, `[` or `:` it holds
    done = subprocess.run([executable, "--literal-pathspecs", *args], cwd=cwd, capture_output=True, check=False)  # noqa: S603
    if done.returncode != 0:
        lines = map(str.strip, done.stderr.decode(errors="replace").splitlines())
        msg = next((line for line in lines if line), f"git {next(a for a in args if not a.startswith('-'))} failed")
        raise GitError(msg)
```

- [ ] **Step 3: Run the new tests and watch them pass**

Run: `uv run pytest tests/unit/test_git.py --no-cov -q`

Expected: `18 passed`: the 6 tests the file held, plus the 12 new ones.

- [ ] **Step 4: Run the regression run and the linters**

```bash
uv run pytest --ignore=tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
make lint
```

Expected: `193 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/git.py tests/unit/test_git.py
git commit -m "feat: keep the record directory out of the file list and list the changed paths"
```

### Task 5: Positions, stages and properties in SARIF and the summary, `reporter.py`

**Files:**

- Modify: `packages/earnest/src/earnest/reporter.py`, `packages/earnest/src/earnest/cli.py` (the one `sarif` call)
- Test: `packages/earnest/tests/unit/test_reporter.py`

**Interfaces:**

- Consumes: `Finding`, `RULES`, `sarif`, `summary`, `percentages` (M1).
- Produces: `RuleId`, a `Literal` over every rule id, with `Finding.rule: RuleId` and `RULES: dict[RuleId, str]`, so `mypy --strict` accepts `RULES[self.rule]`. `RULES` gains `earnest/unbumped-change` (error), `earnest/unplanned` (warning), `earnest/cycle` (error) and `earnest/route-mismatch` (error). `Position = Literal["behind", "current", "ahead"]`.
- Produces: `Finding` gains `stage: str | None`, `intent: str | None` (internal, never serialized), `position: Position`, `note: bool` and `child: str` (the item type whose absence a `gap` reports, which Task 10 needs to place it). All five default (`None`, `None`, `"current"`, `False`, `""`) and are declared with `compare=False`, so ordering, equality and hashing stay M1's and `None` is never compared with a string. `level` is `note` when `note` is set or `position` is `ahead`, otherwise the rule's level. `text` opens with its position and a colon and a space: `regression in approved stage <stage>` (behind), `in scope at <stage>` (current, with a stage), `expected at <stage>` (ahead), and `in scope` for a finding with no stage.
- Produces: `uri(path: str) -> str`, the percent-encoded path `_result` used. `Run`, a frozen dataclass of the run inputs: `commit: str`, `dirty: bool = False`, `timestamp: str = ""`, `plan: Mapping[str, object] | None = None` (`{"intents": [...]}`), `assessment: Mapping[str, object] | None = None` (`{"stage", "hash", "status", "reasons"}`), `record_absent: bool = False` and `unheld: int = 0`.
- Produces: `sarif(findings, levels, run: Run) -> str`, which takes the commit from `run.commit` alone (M1's positional `commit` is gone, so the two cannot diverge). Each result carries `properties.position` and, when `stage` is set, `properties.stage`; the invocation properties always carry `dirty`; the run properties gain `plan` and `assessment` when given; the log keeps M1's single trailing newline. M1's five callers move to `Run`: `cli.py`, and the four `sarif` call expressions in `tests/unit/test_reporter.py` (line 37, line 52, and two on line 64).
- Produces: `summary(findings, levels, run: Run | None = None) -> str`. After the percentage head it adds, when `run` is given: for each intent of `run.plan["intents"]`, an `intent <dir>` line, then, indented two spaces, `<stage>: <status>, approval <approval>` per stage in route order, where `current` is followed by `, <approvedBy>` when there is one, then `frontier: <stage>` (`none` without one), then `task <id>: <status>` and `unit <id>: <status>` lines in the order given; then `assessment <stage>: <hash> (<status>)`, then `record: absent, body-hash baseline unavailable` when `record_absent` is set, then `body-hash baseline: <n> items without a held hash` when `unheld > 0`. The last three start in column 0. Without a `run` the summary is M1's, byte for byte. The module imports from no other `earnest` module.

- [ ] **Step 1: Write the failing tests**

In `packages/earnest/tests/unit/test_reporter.py`, replace:

```python
import json

from earnest import reporter
from earnest.reporter import Finding
from tests.sarif import sarif_run
```

with:

```python
import json

import pytest

from earnest import reporter
from earnest.reporter import Finding, Run
from tests.sarif import sarif_run
```

In the same file, replace:

```python
        "earnest/predated": "error",
        "earnest/unwanted": "warning",
    }
```

with:

```python
        "earnest/predated": "error",
        "earnest/unwanted": "warning",
        "earnest/unbumped-change": "error",
        "earnest/unplanned": "warning",
        "earnest/cycle": "error",
        "earnest/route-mismatch": "error",
    }
```

In the same file, replace:

```python
    text = reporter.sarif(FINDINGS, LEVELS, "abc123")
```

with:

```python
    text = reporter.sarif(FINDINGS, LEVELS, Run(commit="abc123"))
```

In the same file, replace:

```python
        {"executionSuccessful": True, "properties": {"commit": "abc123", "layers": ["trace"]}},
```

with:

```python
        {"executionSuccessful": True, "properties": {"commit": "abc123", "dirty": False, "layers": ["trace"]}},
```

In the same file, replace:

```python
    first = sarif_run(reporter.sarif(FINDINGS, LEVELS, "abc123"))["results"][0]
```

with:

```python
    first = sarif_run(reporter.sarif(FINDINGS, LEVELS, Run(commit="abc123")))["results"][0]
```

In the same file, replace:

```python
    assert reporter.sarif(FINDINGS, LEVELS, "abc") == reporter.sarif(FINDINGS[::-1], shuffled, "abc")
```

with:

```python
    run = Run(commit="abc")
    assert reporter.sarif(FINDINGS, LEVELS, run) == reporter.sarif(FINDINGS[::-1], shuffled, run)
```

Append to the same file:

```python


RECORD = "aidlc/spaces/default/intents/260926-checkout"
STAGE = "construction/code-generation"
HASH = "sha256:" + "0" * 64
PLAN = {
    "intents": [
        {
            "intent": RECORD,
            "stages": [
                {
                    "stage": "inception/requirements-analysis",
                    "status": "done",
                    "approval": "current",
                    "approvedBy": "human",
                },
                {"stage": STAGE, "status": "not done", "approval": "none", "approvedBy": None},
            ],
            "frontier": STAGE,
            "tasks": [{"id": "task~a~1", "status": "not done"}, {"id": "task~b~1", "status": "done"}],
            "units": [],
        },
    ],
}
ASSESSMENT = {"stage": f"{RECORD}/{STAGE}", "hash": HASH, "status": "not done", "reasons": {"approval": "none"}}


def gap(**fields):
    return Finding("a.md", 1, "earnest/gap", "req~a~1", "m", **fields)


@pytest.mark.parametrize(
    ("rule", "level"),
    [
        ("earnest/unbumped-change", "error"),
        ("earnest/unplanned", "warning"),
        ("earnest/cycle", "error"),
        ("earnest/route-mismatch", "error"),
    ],
)
def test_new_rules_carry_their_levels(rule, level):
    assert reporter.RULES[rule] == level
    assert Finding("a.md", 1, rule, "x", "m").level == level


def test_ahead_position_makes_a_note():
    assert gap(stage=STAGE, position="ahead").level == "note"
    assert gap(stage=STAGE, position="behind").level == "error"
    assert gap(stage=STAGE, position="current").level == "error"
    assert gap(stage=STAGE, intent=RECORD, position="ahead", note=True, child="impl") == gap()  # no part in equality


def test_note_flag_makes_a_note_at_every_position():
    for position in ("behind", "current", "ahead"):
        assert gap(stage=STAGE, position=position, note=True).level == "note"
    assert Finding("a.md", 1, "earnest/outdated", "req~a~1", "m", note=True).level == "note"
    assert Finding("a.md", 1, "earnest/outdated", "req~a~1", "m").level == "error"


@pytest.mark.parametrize(
    ("stage", "position", "text"),
    [
        (None, "current", "in scope: m"),
        (STAGE, "current", f"in scope at {STAGE}: m"),
        (STAGE, "behind", f"regression in approved stage {STAGE}: m"),
        (STAGE, "ahead", f"expected at {STAGE}: m"),
    ],
)
def test_text_opens_with_the_position(stage, position, text):
    assert gap(stage=stage, position=position).text == text


def test_result_carries_position_and_stage():
    (result,) = sarif_run(reporter.sarif([gap(stage=STAGE, position="ahead")], {}, Run(commit="abc")))["results"]
    assert result["properties"]["position"] == "ahead"
    assert result["properties"]["stage"] == STAGE
    assert result["level"] == "note"
    assert result["message"] == {"text": f"expected at {STAGE}: m"}


def test_result_omits_stage_when_none():
    (result,) = sarif_run(reporter.sarif([gap()], {}, Run(commit="abc")))["results"]
    assert result["properties"]["position"] == "current"
    assert "stage" not in result["properties"]


def test_invocation_carries_dirty():
    run = sarif_run(reporter.sarif([], {}, Run(commit="abc", dirty=True)))
    assert run["invocations"][0]["properties"] == {"commit": "abc", "dirty": True, "layers": ["trace"]}


def test_run_carries_plan_with_an_intents_list_and_assessment_properties():
    run = sarif_run(reporter.sarif([], {}, Run(commit="abc", plan=PLAN, assessment=ASSESSMENT)))
    assert run["properties"]["plan"] == PLAN
    assert run["properties"]["assessment"] == ASSESSMENT
    assert run["properties"]["plan"]["intents"][0]["intent"] == RECORD
    bare = sarif_run(reporter.sarif([], {}, Run(commit="abc")))
    assert set(bare["properties"]) == {"traceLevels", "percentages"}


def test_summary_lists_stages_frontier_and_hash():
    lines = reporter.summary([], {}, Run(commit="abc", plan=PLAN, assessment=ASSESSMENT)).splitlines()
    assert lines[:5] == [
        "traced 0%, judged 0%, evidenced 0%; requirements: 0",
        f"intent {RECORD}",
        "  inception/requirements-analysis: done, approval current, human",
        f"  {STAGE}: not done, approval none",
        f"  frontier: {STAGE}",
    ]
    assert f"assessment {RECORD}/{STAGE}: {HASH} (not done)" in lines
    assert lines[-1] == "findings: 0, errors: 0"


def test_summary_lists_tasks_and_units_with_their_status():
    entry = {**PLAN["intents"][0], "frontier": None, "units": [{"id": "unit~a~1", "status": "not done"}]}
    lines = reporter.summary([], {}, Run(commit="abc", plan={"intents": [entry]})).splitlines()
    assert lines[4:8] == [
        "  frontier: none",
        "  task task~a~1: not done",
        "  task task~b~1: done",
        "  unit unit~a~1: not done",
    ]


def test_summary_states_a_missing_record():
    lines = reporter.summary([], {}, Run(commit="abc", record_absent=True)).splitlines()
    assert "record: absent, body-hash baseline unavailable" in lines
    assert not [line for line in lines if line.startswith("body-hash baseline")]
    assert (
        "record: absent, body-hash baseline unavailable" not in reporter.summary([], {}, Run(commit="abc")).splitlines()
    )


def test_summary_counts_items_without_a_held_hash():
    lines = reporter.summary([], {}, Run(commit="abc", unheld=2)).splitlines()
    assert "body-hash baseline: 2 items without a held hash" in lines
    assert not [
        line for line in reporter.summary([], {}, Run(commit="abc", unheld=0)).splitlines() if "baseline" in line
    ]
    assert reporter.summary(FINDINGS, LEVELS) == reporter.summary(FINDINGS, LEVELS, Run(commit="abc"))
```

Run: `uv run pytest tests/unit/test_reporter.py --no-cov -q`

Expected: the M1 tests that now call `sarif` with a `Run` fail (`AttributeError` on `Run`, which also fails the import, so the whole file errors at collection with `ImportError: cannot import name 'Run' from 'earnest.reporter'`).

- [ ] **Step 2: Rewrite `reporter.py`**

Replace the whole of `packages/earnest/src/earnest/reporter.py` with:

```python
"""Reporter: the SARIF 2.1.0 log, with each requirement's trace level, and the summary that leads with three percentages."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, cast
from urllib.parse import quote


RuleId = Literal[
    "earnest/cycle",
    "earnest/duplicate",
    "earnest/gap",
    "earnest/near-miss",
    "earnest/orphaned",
    "earnest/outdated",
    "earnest/predated",
    "earnest/route-mismatch",
    "earnest/unbumped-change",
    "earnest/unplanned",
    "earnest/unwanted",
]
Position = Literal["behind", "current", "ahead"]
RULES: dict[RuleId, str] = {
    "earnest/cycle": "error",
    "earnest/duplicate": "error",
    "earnest/gap": "error",
    "earnest/near-miss": "error",
    "earnest/orphaned": "error",
    "earnest/outdated": "error",
    "earnest/predated": "error",
    "earnest/route-mismatch": "error",
    "earnest/unbumped-change": "error",
    "earnest/unplanned": "warning",
    "earnest/unwanted": "warning",
}
LEVELS = ("untraced", "traced", "judged", "evidenced")
_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_OPENINGS: dict[Position, str] = {
    "behind": "regression in approved stage {}",
    "current": "in scope at {}",
    "ahead": "expected at {}",
}


@dataclass(frozen=True, order=True)
class Finding:
    """A located result: file, line, rule, the id or text it is about, and a message that names the change to make.

    The stage it counts against and its position come from the plan; with no stage a finding is in scope. The extra
    fields take no part in equality or order.
    """

    path: str
    line: int
    rule: RuleId
    subject: str
    message: str
    stage: str | None = field(default=None, compare=False)
    intent: str | None = field(default=None, compare=False)  # the record directory of its stage; never serialized
    position: Position = field(default="current", compare=False)
    note: bool = field(default=False, compare=False)  # a note at every position, as a stale stage approval is
    child: str = field(default="", compare=False)  # for a gap, the item type whose absence it reports

    @property
    def level(self) -> str:
        """Return the SARIF level: note at position ahead or when flagged, else the level of the finding's rule."""
        return "note" if self.note or self.position == "ahead" else RULES[self.rule]

    @property
    def text(self) -> str:
        """Return the message as it is reported, opening with the finding's position."""
        if self.stage is None:
            return f"in scope: {self.message}"
        return f"{_OPENINGS[self.position].format(self.stage)}: {self.message}"


@dataclass(frozen=True)
class Run:
    """What one run adds to its log and summary besides the findings: the commit and the plan's view of the work."""

    commit: str
    dirty: bool = False
    timestamp: str = ""
    plan: Mapping[str, object] | None = None
    assessment: Mapping[str, object] | None = None
    record_absent: bool = False
    unheld: int = 0


def percentages(levels: Mapping[str, str]) -> dict[str, int]:
    """Return the share of requirements at each level or above, in whole percent rounded down, so 100 means all."""
    ranks = [LEVELS.index(level) for level in levels.values()]
    return {
        name: 100 * sum(rank >= floor for rank in ranks) // len(ranks) if ranks else 0
        for floor, name in enumerate(LEVELS[1:], start=1)
    }


def uri(path: str) -> str:
    """Return a path as a SARIF artifact uri: percent-encoded, with names that are not UTF-8 kept apart."""
    return quote(path, errors="surrogateescape")  # Git hands over names that are not UTF-8 as surrogates


def sarif(findings: Sequence[Finding], levels: Mapping[str, str], run: Run) -> str:
    """Return one SARIF 2.1.0 log; it holds no timestamp, so an unchanged repository gives the same bytes."""
    properties: dict[str, object] = {"traceLevels": dict(levels), "percentages": percentages(levels)}
    if run.plan is not None:
        properties["plan"] = run.plan
    if run.assessment is not None:
        properties["assessment"] = run.assessment
    body = {
        "tool": {"driver": {"name": "earnest"}},
        "invocations": [
            {
                "executionSuccessful": True,
                "properties": {"commit": run.commit, "dirty": run.dirty, "layers": ["trace"]},
            },
        ],
        "results": [_result(finding) for finding in sorted(findings)],
        "properties": properties,
    }
    log = {"$schema": _SCHEMA, "version": "2.1.0", "runs": [body]}
    return json.dumps(log, sort_keys=True, separators=(",", ":")) + "\n"


def summary(findings: Sequence[Finding], levels: Mapping[str, str], run: Run | None = None) -> str:
    """Return the human summary: the percentages, the plan's view of the work, each level, then each finding."""
    shares = percentages(levels)
    head = (
        f"traced {shares['traced']}%, judged {shares['judged']}%, evidenced {shares['evidenced']}%;"
        f" requirements: {len(levels)}"
    )
    lines = [
        head,
        *(_run_lines(run) if run is not None else []),
        *(f"  {req}: {level}" for req, level in sorted(levels.items())),
        *(f"{f.path}:{f.line}: {f.level} {f.rule}: {f.text}" for f in sorted(findings)),
    ]
    errors = sum(1 for finding in findings if finding.level == "error")
    lines.append(f"findings: {len(findings)}, errors: {errors}")
    return "\n".join(lines) + "\n"


def _run_lines(run: Run) -> list[str]:
    lines: list[str] = []
    if run.plan is not None:
        for entry in cast("Sequence[Mapping[str, Any]]", run.plan["intents"]):
            lines.extend(_intent_lines(entry))
    if run.assessment is not None:
        lines.append(f"assessment {run.assessment['stage']}: {run.assessment['hash']} ({run.assessment['status']})")
    if run.record_absent:
        lines.append("record: absent, body-hash baseline unavailable")
    if run.unheld > 0:
        lines.append(f"body-hash baseline: {run.unheld} items without a held hash")
    return lines


def _intent_lines(entry: Mapping[str, Any]) -> list[str]:
    lines = [f"intent {entry['intent']}"]
    for stage in entry["stages"]:
        by = stage["approvedBy"] if stage["approval"] == "current" else None
        approval = f"{stage['approval']}, {by}" if by else stage["approval"]
        lines.append(f"  {stage['stage']}: {stage['status']}, approval {approval}")
    lines.append(f"  frontier: {entry['frontier'] or 'none'}")
    lines.extend(f"  task {task['id']}: {task['status']}" for task in entry["tasks"])
    lines.extend(f"  unit {unit['id']}: {unit['status']}" for unit in entry["units"])
    return lines


def _result(finding: Finding) -> dict[str, object]:
    location = {"artifactLocation": {"uri": uri(finding.path)}, "region": {"startLine": finding.line}}
    observation = {
        "method": "trace",
        "subject": finding.subject,
        "result": finding.rule.removeprefix("earnest/"),
        "reasoning": finding.message,
        "location": location,
    }
    properties: dict[str, object] = {"position": finding.position, "observations": [observation]}
    if finding.stage is not None:
        properties["stage"] = finding.stage
    return {
        "ruleId": finding.rule,
        "level": finding.level,
        "message": {"text": finding.text},
        "locations": [{"physicalLocation": location}],
        "properties": properties,
    }
```

- [ ] **Step 3: Move `cli.py` to `Run`**

In `packages/earnest/src/earnest/cli.py`, replace:

```python
        sys.stdout.write(reporter.sarif(findings, levels, commit))
```

with:

```python
        sys.stdout.write(reporter.sarif(findings, levels, reporter.Run(commit=commit)))
```

- [ ] **Step 4: Run the new tests and watch them pass**

Run: `uv run pytest tests/unit/test_reporter.py --no-cov -q`

Expected: `24 passed`: the 6 tests the file held, plus the 18 new ones (each four-case parametrization counts four).

- [ ] **Step 5: Run the regression run and the linters**

```bash
uv run pytest --ignore=tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
make lint
```

Expected: `211 passed`, then `make lint` exits 0.

- [ ] **Step 6: Commit**

```bash
git add src/earnest/reporter.py src/earnest/cli.py tests/unit/test_reporter.py
git commit -m "feat: place findings by stage and position in SARIF and the summary"
```

### Task 6: The assessment record, `reporter.py`

> Superseded in part by the final state in Task 13 (D17, S1–S7); these snippets are the historical TDD record.

**Files:**

- Modify: `packages/earnest/src/earnest/reporter.py`
- Test: `packages/earnest/tests/unit/test_reporter.py`

**Interfaces:**

- Consumes: Task 5's `reporter.py`.
- Produces: `RECORD = ".earnest/assessment.json"`; `VERSION = 1`; `class RecordError(Exception)`, whose message names the file.
- Produces: `RunHeader`, a frozen dataclass: `intent`, `stage`, `commit`, `dirty`, `timestamp`, `layers: tuple[str, ...]`, `model: str | None`, `prompt: str | None`, `items: tuple[str, ...]`, `status`, `reasons: Mapping[str, int | str]` and `digest`. The digest is stored under the ratified key `hash`, so no attribute shadows a builtin.
- Produces: `Record`, a mutable dataclass: `version`, `runs: dict[str, RunHeader]`, `bodies: dict[str, str]`, `coverage: dict[str, object]`, `judge: dict[str, object]`, `calibration: dict[str, object] | None` and `extra: dict[str, object]`, the top-level keys another tool added. `Record()` is the empty record: `version` 1, `runs` and `bodies` empty, `coverage` `{"commit": null}`, `judge` `{"cache": {}}`, `calibration` null.
- Produces: `canonical(obj, *, pretty=False) -> str`: sorted keys, ASCII, no NaN, and no float anywhere (`TypeError`); compact with no trailing newline for the hash and the SARIF log, or two-space indented with one trailing newline for the file. `run_key(intent, stage) -> str`, `<intent dir>/<stage id>`, the key of `runs`. `utc_timestamp(now=None) -> str`, `YYYY-MM-DDTHH:MM:SSZ` in UTC. `read_record(root) -> Record`: a missing file is the empty record; text that does not parse, a wrong shape or a newer `version` raises `RecordError`; an unreadable file raises `OSError`. `write_record(root, record) -> None`: creates `.earnest/` with a `.gitignore` holding `*` only when the directory is new, writes a temporary file beside the record, replaces the record with it, removes the temporary file when anything fails, and writes back `extra` (the keys of a file at its own `version`).

- [ ] **Step 1: Write the failing tests**

In `packages/earnest/tests/unit/test_reporter.py`, replace:

```python
import json

import pytest

from earnest import reporter
from earnest.reporter import Finding, Run
from tests.sarif import sarif_run
```

with:

```python
import ast
import json
import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from earnest import reporter
from earnest.reporter import Finding, Record, RecordError, Run, RunHeader
from tests.sarif import sarif_run
```

Append to the same file:

```python


INTENT = "aidlc/spaces/default/intents/260926-checkout"


def header(intent=INTENT, stage="construction/code-generation"):
    return RunHeader(
        intent=intent,
        stage=stage,
        commit="a" * 40,
        dirty=False,
        timestamp="2026-09-26T12:00:00Z",
        layers=("trace",),
        model=None,
        prompt=None,
        items=("task~a~1", "task~b~1"),
        status="not done",
        reasons={"errors": 0, "openTasks": 2, "approval": "none"},
        digest="sha256:" + "1" * 64,
    )


def stored(root):
    return json.loads((root / ".earnest" / "assessment.json").read_text(encoding="utf-8"))


def test_canonical_compact_bytes_have_no_trailing_newline():
    assert reporter.canonical({"b": [1, 2], "a": "caf\u00e9", "c": None}) == '{"a":"caf\\u00e9","b":[1,2],"c":null}'
    assert reporter.canonical({"t": (1, 2), "f": False}) == '{"f":false,"t":[1,2]}'


def test_canonical_pretty_bytes_end_with_one_newline():
    pretty = reporter.canonical({"b": 1, "a": {"c": 2}, "e": "\u00e9"}, pretty=True)
    assert pretty == '{\n  "a": {\n    "c": 2\n  },\n  "b": 1,\n  "e": "\\u00e9"\n}\n'


def test_canonical_rejects_floats_and_nan():
    for value in (1.5, float("nan"), float("inf"), [1, (2, 0.5)], {"a": {"b": 2.0}}):
        with pytest.raises(TypeError, match="integers only"):
            reporter.canonical({"value": value})


def test_run_key_joins_intent_and_stage():
    assert reporter.run_key(INTENT, "inception/requirements-analysis") == f"{INTENT}/inception/requirements-analysis"


def test_utc_timestamp_shape():
    assert reporter.utc_timestamp(datetime(2026, 9, 26, 12, 0, 0, tzinfo=UTC)) == "2026-09-26T12:00:00Z"
    plus_two = timezone(timedelta(hours=2))
    assert reporter.utc_timestamp(datetime(2026, 9, 26, 12, 0, 0, 999, tzinfo=plus_two)) == "2026-09-26T10:00:00Z"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", reporter.utc_timestamp())


def test_record_round_trips(tmp_path):
    held = header()
    record = Record(runs={reporter.run_key(INTENT, held.stage): held}, bodies={"req~a~1": "sha256:" + "2" * 64})
    reporter.write_record(tmp_path, record)
    assert reporter.read_record(tmp_path) == record
    data = stored(tmp_path)
    assert data["runs"][f"{INTENT}/{held.stage}"]["hash"] == held.digest  # the digest travels as the key `hash`
    assert "digest" not in data["runs"][f"{INTENT}/{held.stage}"]
    text = (tmp_path / ".earnest" / "assessment.json").read_text(encoding="utf-8")
    assert text == reporter.canonical(data, pretty=True)


def test_missing_record_is_empty_with_the_slot_defaults(tmp_path):
    record = reporter.read_record(tmp_path)
    assert record == Record()
    assert (record.version, record.runs, record.bodies) == (1, {}, {})
    assert (record.coverage, record.judge, record.calibration) == ({"commit": None}, {"cache": {}}, None)
    assert not (tmp_path / ".earnest").exists()  # reading writes nothing


def test_corrupt_record_raises_and_names_the_file(tmp_path):
    (tmp_path / ".earnest").mkdir()
    slots = '"runs": {}, "bodies": {}, "coverage": {}, "judge": {}, "calibration": null'  # a whole record's slots
    for text in (
        "{not json",
        "[]",
        '{"version": 1}',
        '{"version": 0}',
        '{"version": "1"}',
        '{"version": 1, "runs": []}',
        f'{{"version": 1, {slots}, "x": 1.5}}',  # a float or NaN would crash the next write
        f'{{"version": 1, {slots}, "x": NaN}}',
        "[" * 100_000,  # RecursionError
        "\xff",
    ):
        (tmp_path / ".earnest" / "assessment.json").write_text(text, encoding="utf-8")
        with pytest.raises(RecordError, match=r"\.earnest/assessment\.json"):
            reporter.read_record(tmp_path)
    (tmp_path / ".earnest" / "assessment.json").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(RecordError, match=r"\.earnest/assessment\.json"):
        reporter.read_record(tmp_path)


def test_newer_version_raises(tmp_path):
    (tmp_path / ".earnest").mkdir()
    (tmp_path / ".earnest" / "assessment.json").write_text('{"version": 2}', encoding="utf-8")
    with pytest.raises(RecordError, match="version 2"):
        reporter.read_record(tmp_path)


def test_unknown_top_level_keys_survive_a_write_at_the_same_version(tmp_path):
    reporter.write_record(tmp_path, Record(extra={"future": {"a": [1, 2]}}))
    record = reporter.read_record(tmp_path)
    assert record.extra == {"future": {"a": [1, 2]}}
    record.bodies["req~a~1"] = "sha256:" + "3" * 64
    reporter.write_record(tmp_path, record)
    data = stored(tmp_path)
    assert data["future"] == {"a": [1, 2]}
    assert data["bodies"] == {"req~a~1": "sha256:" + "3" * 64}
    assert data["version"] == 1


def test_write_creates_the_marker_once_and_never_rewrites_an_existing_directory(tmp_path):
    reporter.write_record(tmp_path, Record())
    marker = tmp_path / ".earnest" / ".gitignore"
    assert marker.read_text(encoding="utf-8") == "*\n"
    marker.write_text("custom\n", encoding="utf-8")  # a repository's own choice
    reporter.write_record(tmp_path, Record())
    assert marker.read_text(encoding="utf-8") == "custom\n"
    other = tmp_path / "other"
    (other / ".earnest").mkdir(parents=True)
    reporter.write_record(other, Record())
    assert not (other / ".earnest" / ".gitignore").exists()


def test_write_is_atomic_when_replace_fails(tmp_path, monkeypatch):
    reporter.write_record(tmp_path, Record(bodies={"req~a~1": "sha256:" + "4" * 64}))
    before = (tmp_path / ".earnest" / "assessment.json").read_bytes()

    def refuse(self, target):
        raise PermissionError(target)

    monkeypatch.setattr(Path, "replace", refuse)
    with pytest.raises(PermissionError):
        reporter.write_record(tmp_path, Record(bodies={"req~a~1": "sha256:" + "5" * 64}))
    assert (tmp_path / ".earnest" / "assessment.json").read_bytes() == before
    assert sorted(path.name for path in (tmp_path / ".earnest").iterdir()) == [".gitignore", "assessment.json"]


def test_runs_are_keyed_by_intent_and_stage_so_two_intents_never_collide(tmp_path):
    one, two = header("intents/one"), header("intents/two")
    record = Record(runs={reporter.run_key(h.intent, h.stage): h for h in (one, two)})
    reporter.write_record(tmp_path, record)
    assert sorted(stored(tmp_path)["runs"]) == [
        "intents/one/construction/code-generation",
        "intents/two/construction/code-generation",
    ]
    assert reporter.read_record(tmp_path) == record


def test_reporter_imports_neither_structural_nor_plan():
    tree = ast.parse(Path(reporter.__file__).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert not {name for name in names if name.startswith(("earnest.structural", "earnest.plan"))}
```

Run: `uv run pytest tests/unit/test_reporter.py --no-cov -q`

Expected: collection fails with `ImportError: cannot import name 'Record' from 'earnest.reporter'`, `1 error`.

- [ ] **Step 2: Add the record to `reporter.py`**

In `packages/earnest/src/earnest/reporter.py`, replace:

```python
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, cast
from urllib.parse import quote
```

with:

```python
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import quote
```

At the end of the same file, append:

```python


RECORD = ".earnest/assessment.json"
VERSION = 1
_KNOWN = frozenset({"version", "runs", "bodies", "coverage", "judge", "calibration"})


class RecordError(Exception):
    """The assessment record cannot be used: it does not parse, has the wrong shape, or is newer than this release."""


@dataclass(frozen=True)
class RunHeader:
    """The latest run of one stage of one intent, as the record keeps it; the digest is stored under the key `hash`."""

    intent: str
    stage: str
    commit: str
    dirty: bool
    timestamp: str
    layers: tuple[str, ...]
    model: str | None
    prompt: str | None
    items: tuple[str, ...]
    status: str
    reasons: Mapping[str, int | str]
    digest: str


def _empty_coverage() -> dict[str, object]:
    # ponytail: a placeholder shape; Milestone 3 settles whether `coverage` holds an object or the bare commit
    return {"commit": None}


def _empty_judge() -> dict[str, object]:
    return {"cache": {}}


@dataclass
class Record:
    """The assessment record: the latest run header of each stage, the body hashes, and the slots later layers fill.

    `extra` holds the top-level keys another tool added, so a write does not lose them. `Record()` is the empty record.
    """

    version: int = VERSION
    runs: dict[str, RunHeader] = field(default_factory=dict)
    bodies: dict[str, str] = field(default_factory=dict)
    coverage: dict[str, object] = field(default_factory=_empty_coverage)
    judge: dict[str, object] = field(default_factory=_empty_judge)
    calibration: dict[str, object] | None = None
    extra: dict[str, object] = field(default_factory=dict)


def canonical(obj: object, *, pretty: bool = False) -> str:
    """Return obj as canonical JSON: sorted keys, ASCII, integers only.

    The compact form has no trailing newline and is what the assessment hash and the SARIF log use; the pretty form
    indents two spaces and ends with one newline, and is what the record file holds.

    Raises:
        TypeError: obj holds a float.
    """
    _integers_only(obj)
    if pretty:
        return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def run_key(intent: str, stage: str) -> str:
    """Return the key of a stage's run header in `runs`: the intent's record directory and the stage's id."""
    # ponytail: a record directory at the repository root is "", which gives a leading slash that `--intent ""` cannot
    # name; give the root a name here if a repository ever keeps its state file there
    return f"{intent}/{stage}"


def utc_timestamp(now: datetime | None = None) -> str:
    """Return now, or the current time, in UTC to the second as `YYYY-MM-DDTHH:MM:SSZ`."""
    return (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_record(root: Path) -> Record:
    """Return the assessment record under root; a missing file is the empty record.

    Raises:
        RecordError: the file does not parse, has the wrong shape, or has a newer `version` than this release reads.
        OSError: the file cannot be read.
    """
    try:
        record = _record(json.loads((root / RECORD).read_text(encoding="utf-8")))
    except FileNotFoundError:
        return Record()
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError) as error:  # UnicodeDecodeError: ValueError
        msg = f"{RECORD} is not an assessment record: {error!r}"
        raise RecordError(msg) from error
    return record


def write_record(root: Path, record: Record) -> None:
    """Replace the assessment record under root with record, whole or not at all.

    The text goes to a temporary file in `.earnest/` and replaces the record, so a crash or a second writer leaves a
    whole file. A new `.earnest/` gets a `.gitignore` holding `*`; an existing one is left as it is.

    Raises:
        OSError: the directory or the file cannot be written; the old record stays and no temporary file does.
    """
    directory = root / ".earnest"
    created = not directory.exists()
    directory.mkdir(exist_ok=True)
    if created:
        (directory / ".gitignore").write_text("*\n", encoding="utf-8")
    body = {
        **record.extra,
        "version": VERSION,
        "runs": {key: _header_json(held) for key, held in record.runs.items()},
        "bodies": record.bodies,
        "coverage": record.coverage,
        "judge": record.judge,
        "calibration": record.calibration,
    }
    # ponytail: mkstemp makes the file mode 0600 (Git tracks 100644 either way), and a write that fails after the
    # directory is new leaves its `.gitignore` behind; chmod and clean up if either ever matters
    descriptor, name = tempfile.mkstemp(dir=directory, prefix="assessment.", suffix=".tmp")
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(canonical(body, pretty=True))
        temp.replace(root / RECORD)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _integers_only(obj: object) -> None:
    if isinstance(obj, float):
        msg = f"canonical JSON holds integers only, not {obj!r}"
        raise TypeError(msg)
    if isinstance(obj, Mapping):
        for value in obj.values():
            _integers_only(value)
    elif isinstance(obj, list | tuple):
        for value in obj:
            _integers_only(value)


def _record(data: object) -> Record:
    # ponytail: shallow validation, so `version: true` or a non-string body hash passes; type-check every field when
    # something other than Earnest writes the record
    if not isinstance(data, dict) or not isinstance(data["version"], int) or data["version"] < 1:
        msg = "the file is not a JSON object with a version"
        raise TypeError(msg)
    if data["version"] > VERSION:
        msg = f"{RECORD} has version {data['version']}, and this release reads up to version {VERSION}: update earnest"
        raise RecordError(msg)
    _integers_only(data)  # a float would pass the read and crash the next write
    return Record(
        version=data["version"],
        runs={key: _header(held) for key, held in data["runs"].items()},
        bodies=dict(data["bodies"]),
        coverage=dict(data["coverage"]),
        judge=dict(data["judge"]),
        calibration=None if data["calibration"] is None else dict(data["calibration"]),
        extra={key: value for key, value in data.items() if key not in _KNOWN},
    )


def _header(held: Mapping[str, Any]) -> RunHeader:
    return RunHeader(
        intent=held["intent"],
        stage=held["stage"],
        commit=held["commit"],
        dirty=held["dirty"],
        timestamp=held["timestamp"],
        layers=tuple(held["layers"]),
        model=held["model"],
        prompt=held["prompt"],
        items=tuple(held["items"]),
        status=held["status"],
        reasons=dict(held["reasons"]),
        digest=held["hash"],
    )


def _header_json(held: RunHeader) -> dict[str, object]:
    return {
        "intent": held.intent,
        "stage": held.stage,
        "commit": held.commit,
        "dirty": held.dirty,
        "timestamp": held.timestamp,
        "layers": list(held.layers),
        "model": held.model,
        "prompt": held.prompt,
        "items": list(held.items),
        "status": held.status,
        "reasons": dict(held.reasons),
        "hash": held.digest,
    }
```

- [ ] **Step 3: Run the new tests and watch them pass**

Run: `uv run pytest tests/unit/test_reporter.py --no-cov -q`

Expected: `38 passed`: the 24 tests the file held, plus the 14 new ones.

- [ ] **Step 4: Run the regression run and the linters**

```bash
uv run pytest --ignore=tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
make lint
```

Expected: `225 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/reporter.py tests/unit/test_reporter.py
git commit -m "feat: read and write the assessment record as canonical JSON"
```

### Task 7: The route rule and `unbumped-change`, `structural.py`

**Files:**

- Modify: `packages/earnest/src/earnest/structural.py`
- Test: `packages/earnest/tests/unit/test_structural.py`

**Interfaces:**

- Consumes: `Index`, `Item.body_hash` (Task 3); `Finding` with `child` and the new rule ids (Task 5).
- Produces: `check(index, *, produces: frozenset[str] | None = None, frozen: Mapping[str, str] | None = None) -> list[Finding]`. `produces` is the set of item types some stage on the route produces; `None` is M1's behaviour, with no route. With a set, the route rule of Stages applies to needs, to parentless items and to edges. `needs(item, produces=None)` drops the types the route does not produce. `_parentless` skips an item whose parent types the route produces none of, which is the chain root (`req` on a route without `feat`). `_links` drops a link whose target type the route does not produce, so a `Covers:` or `Delivers:` naming `feat` on such a route raises nothing. `traced(index, produces=None)` follows the routed needs.
- Produces: `resolved_covers(index) -> set[tuple[str, Item]]`, the covers that resolve at their item's current revision, public for Task 10.
- Produces: `frozen` maps `type~name~revision` to the body hash that a counting approval froze (Task 11 builds it). For each defined item whose key is in `frozen` and whose `body_hash` differs, `check` yields an `earnest/unbumped-change` finding at the item's id line: "bump the revision to" the next number, "or restore the text". An item with no entry raises nothing. `_gaps` sets `Finding.child` to the missing type.

- [ ] **Step 1: Write the failing tests**

Append to `packages/earnest/tests/unit/test_structural.py`:

```python


ROUTE = frozenset({"req", "impl", "utest"})
GOAL = Item(Id("goal", "g", 1), "docs/g.md", 1)
BARE_REQ = Item(REQ, "docs/r.md", 5)
WRONG_PARENT = Link("Covers", "req", Id("feat", "zzz", 1), "docs/r.md", 7, owner=REQ)


def rules(found):
    return sorted((finding.rule, finding.path, finding.line) for finding in found)


def test_route_without_ideation_exempts_req_from_a_parent():
    bare = Index((BARE_REQ,), (), ())
    assert rules(structural.check(bare)) == [
        ("earnest/gap", "docs/r.md", 5),
        ("earnest/gap", "docs/r.md", 5),
        ("earnest/orphaned", "docs/r.md", 5),
    ]
    assert rules(structural.check(bare, produces=ROUTE)) == [
        ("earnest/gap", "docs/r.md", 5),
        ("earnest/gap", "docs/r.md", 5),
    ]


def test_route_without_scope_definition_keeps_the_goal_parent_and_exempts_req():
    poc = frozenset({"tenet", "goal", "req", "impl", "utest"})
    found = structural.check(Index((GOAL, BARE_REQ), (), ()), produces=poc)
    assert [(f.rule, f.path) for f in found if f.rule == "earnest/orphaned"] == [("earnest/orphaned", "docs/g.md")]
    assert [f.path for f in found if f.rule == "earnest/gap"] == ["docs/r.md", "docs/r.md"]  # the goal needs no feat


def test_full_route_still_requires_the_req_parent():
    full = frozenset({"tenet", "goal", "feat", "req", "impl", "utest", "stest"})
    found = structural.check(Index((BARE_REQ,), (), ()), produces=full)
    assert [(f.path, f.line) for f in found if f.rule == "earnest/orphaned"] == [("docs/r.md", 5)]


def test_no_route_keeps_the_m1_behavior():
    assert rules(structural.check(Index((BARE_REQ,), (), ()), produces=None)) == rules(
        structural.check(Index((BARE_REQ,), (), ()))
    )
    assert "earnest/orphaned" in {f.rule for f in structural.check(Index((BARE_REQ,), (), ()))}


def test_needs_drop_types_the_route_does_not_produce():
    assert structural.needs(BARE_REQ) == ("impl", "utest")
    assert structural.needs(BARE_REQ, frozenset({"impl"})) == ("impl",)
    explicit = Item(REQ, "docs/r.md", 5, ("impl", "itest"))
    assert structural.needs(explicit, frozenset({"impl"})) == ("impl",)
    assert structural.needs(Item(Id("feat", "f", 1), "docs/f.md", 1), ROUTE) == ("req",)


def test_edges_naming_types_the_route_does_not_produce_are_dropped():
    index_ = Index((BARE_REQ,), (WRONG_PARENT,), ())
    assert ("earnest/orphaned", "docs/r.md", 7) in rules(structural.check(index_))
    assert rules(structural.check(index_, produces=ROUTE)) == [
        ("earnest/gap", "docs/r.md", 5),
        ("earnest/gap", "docs/r.md", 5),
    ]


def test_edges_naming_produced_types_still_resolve():
    route = ROUTE | {"feat"}
    found = structural.check(Index((BARE_REQ,), (WRONG_PARENT,), ()), produces=route)
    assert ("earnest/orphaned", "docs/r.md", 7) in rules(found)


def test_traced_follows_the_routed_needs():
    index_ = Index((BARE_REQ,), (IMPL,), ())
    assert structural.traced(index_) == {"req~r~2": "untraced"}
    assert structural.traced(index_, frozenset({"req", "impl"})) == {"req~r~2": "traced"}
    assert structural.resolved_covers(index_) == {("impl", BARE_REQ)}


def hashed(held, current):
    item = Item(REQ, "docs/r.md", 5, None, current)
    found = structural.check(Index((ITEMS[0], item), (PARENT, IMPL, UTEST), ()), frozen=held)
    return [finding for finding in found if finding.path != "docs/f.md"]  # the feat names no goal, as in `check` above


def test_unbumped_change_when_the_frozen_hash_differs():
    found = hashed({"req~r~2": "sha256:aaa"}, "sha256:bbb")
    assert located("earnest/unbumped-change", found) == [("docs/r.md", 5)]
    assert [(f.rule, f.subject, f.level) for f in found if f.line == 5] == [
        ("earnest/unbumped-change", "req~r~2", "error")
    ]


def test_no_unbumped_change_when_the_hash_is_equal():
    assert hashed({"req~r~2": "sha256:aaa"}, "sha256:aaa") == []


def test_no_entry_in_frozen_no_unbumped_change():
    assert hashed({"req~r~1": "sha256:aaa"}, "sha256:bbb") == []  # a bump gives a new key, so the new revision is free
    assert hashed({}, "sha256:bbb") == []
    assert hashed(None, "sha256:bbb") == []


def test_unbumped_message_names_the_next_revision_and_the_restore():
    text = message("earnest/unbumped-change", hashed({"req~r~2": "sha256:aaa"}, "sha256:bbb"))
    assert "bump the revision to 3" in text
    assert "restore the text" in text
    assert text.startswith("`req~r~2` ")


def test_gap_carries_the_missing_type():
    found = structural.check(Index((BARE_REQ,), (PARENT,), ()))
    assert [f.child for f in found if f.rule == "earnest/gap"] == ["impl", "utest"]
```

Run: `uv run pytest tests/unit/test_structural.py --no-cov -q`

Expected: `13 failed` (`TypeError: check() got an unexpected keyword argument 'produces'`, `AttributeError` for `resolved_covers`, and `Finding` carrying no `child`), and `14 passed`, the earlier tests of the file.

- [ ] **Step 2: Add the route rule, `resolved_covers` and `unbumped-change`**

In `packages/earnest/src/earnest/structural.py`, replace:

```python
from collections.abc import Iterator

from earnest.index import Index, Item, Resolution
```

with:

```python
from collections.abc import Iterable, Iterator, Mapping

from earnest.index import Index, Item, Resolution
```

In the same file, replace:

```python
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
```

with:

```python
def needs(item: Item, produces: frozenset[str] | None = None) -> tuple[str, ...]:
    """Return the types on the item's `Needs:` line, or its type's default, less those the route does not produce."""
    wanted = item.needs if item.needs is not None else DEFAULT_NEEDS.get(item.id.type, ())
    return _produced(wanted, produces)


def check(
    index: Index, *, produces: frozenset[str] | None = None, frozen: Mapping[str, str] | None = None
) -> list[Finding]:
    """Return the link findings, in the order of the index; the reporter sorts them.

    Near-misses, duplicate ids, links that resolve to no item or to another revision, covers that count toward
    nothing, items that name no parent of their type, needs that no cover meets, and bodies that changed after an
    approval froze their hash. `produces` is the set of item types some stage on the route produces: needs, parents
    and links that name any other type are dropped, as the route rule of Stages says. `None` is no route. `frozen`
    maps `type~name~revision` to the body hash that an approval froze.
    """
    return [
        *_near_misses(index),
        *_duplicates(index),
        *_links(index, produces),
        *_parentless(index, produces),
        *_gaps(index, produces),
        *_unbumped(index, frozen or {}),
    ]


def resolved_covers(index: Index) -> set[tuple[str, Item]]:
    """Return each cover that resolves at its item's current revision, as its artifact type and the item."""
    return {
        (kind, resolution.item)
        for kind, resolution in _covers(index)
        if resolution.status == "resolved" and resolution.item is not None
    }


def traced(index: Index, produces: frozenset[str] | None = None) -> dict[str, str]:
    """Give each requirement its trace level, keyed by its id: traced when a cover of every type it needs resolves."""
    resolved = resolved_covers(index)
    return {
        str(item.id): "traced" if all((kind, item) in resolved for kind in needs(item, produces)) else "untraced"
        for item in index.defined.values()
        if item.id.type == "req"
    }


def _produced(types: Iterable[str], produces: frozenset[str] | None) -> tuple[str, ...]:
    return tuple(types) if produces is None else tuple(kind for kind in types if kind in produces)
```

In the same file, replace:

```python
def _links(index: Index) -> Iterator[Finding]:
    """Turn each link's resolution into its findings: orphaned, outdated or predated, and unwanted."""
    for link in index.links:
```

with:

```python
def _links(index: Index, produces: frozenset[str] | None) -> Iterator[Finding]:
    """Turn each link's resolution into its findings: orphaned, outdated or predated, and unwanted."""
    for link in [link for link in index.links if produces is None or link.target.type in produces]:
```

In the same file, replace:

```python
            wanted = ", ".join(f"`{kind}`" for kind in needs(item)) or "no cover"
```

with:

```python
            wanted = ", ".join(f"`{kind}`" for kind in needs(item, produces)) or "no cover"
```

In the same file, replace:

```python
        if link.key == "Covers" and link.type not in needs(item):
```

with:

```python
        if link.key == "Covers" and link.type not in needs(item, produces):
```

In the same file, replace:

```python
def _parentless(index: Index) -> Iterator[Finding]:
    """An item whose parent key names no id of a parent type, itself included, covers no parent."""
    named = {(link.owner, link.key, link.target.type) for link in index.links if link.owner is not None}
    for item in index.defined.values():
        if item.id.type not in _PARENTS:
            continue
        key, parents, fix = _PARENTS[item.id.type]
        if not any((item.id, key, parent) in named for parent in parents):
```

with:

```python
def _parentless(index: Index, produces: frozenset[str] | None) -> Iterator[Finding]:
    """An item whose parent key names no id of a parent type, itself included, covers no parent.

    On a route that produces none of an item's parent types the item is the chain root, and covers no parent.
    """
    named = {(link.owner, link.key, link.target.type) for link in index.links if link.owner is not None}
    for item in index.defined.values():
        if item.id.type not in _PARENTS:
            continue
        key, all_parents, fix = _PARENTS[item.id.type]
        parents = _produced(all_parents, produces)
        if parents and not any((item.id, key, parent) in named for parent in parents):
```

In the same file, replace:

```python
def _gaps(index: Index) -> Iterator[Finding]:
    """A need no cover meets at any revision is a gap; a cover at another revision is outdated or predated instead."""
    covered = {(kind, resolution.item) for kind, resolution in _covers(index)}
    for item in index.defined.values():
        for kind in needs(item):
            if (kind, item) not in covered:
                hint = _COVER_HINTS.get(kind, "add a `{kind}` item with `Covers: {id}`").format(kind=kind, id=item.id)
                message = f"`{item.id}` needs a `{kind}` cover and has none: {hint}"
                yield Finding(item.path, item.line, "earnest/gap", str(item.id), message)
```

with:

```python
def _gaps(index: Index, produces: frozenset[str] | None) -> Iterator[Finding]:
    """A need no cover meets at any revision is a gap; a cover at another revision is outdated or predated instead."""
    covered = {(kind, resolution.item) for kind, resolution in _covers(index)}
    for item in index.defined.values():
        for kind in needs(item, produces):
            if (kind, item) not in covered:
                hint = _COVER_HINTS.get(kind, "add a `{kind}` item with `Covers: {id}`").format(kind=kind, id=item.id)
                message = f"`{item.id}` needs a `{kind}` cover and has none: {hint}"
                yield Finding(item.path, item.line, "earnest/gap", str(item.id), message, child=kind)


def _unbumped(index: Index, frozen: Mapping[str, str]) -> Iterator[Finding]:
    """A body whose hash differs from the one an approval froze for its id and revision changed without a bump."""
    for item in index.defined.values():
        held = frozen.get(str(item.id))
        if held is not None and held != item.body_hash:
            message = (
                f"`{item.id}` changed its body after its approval and is still at revision {item.id.revision}:"
                f" bump the revision to {item.id.revision + 1}, or restore the text"
            )
            yield Finding(item.path, item.line, "earnest/unbumped-change", str(item.id), message)
```

- [ ] **Step 3: Run the new tests and watch them pass**

Run: `uv run pytest tests/unit/test_structural.py --no-cov -q`

Expected: `27 passed`: the 14 tests the file held, plus the 13 new ones.

- [ ] **Step 4: Run the regression run and the linters**

```bash
uv run pytest --ignore=tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
make lint
```

Expected: `238 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/structural.py tests/unit/test_structural.py
git commit -m "feat: apply the route rule and raise unbumped-change"
```

### Task 8: The state and audit readers, `plan.py`

> Superseded in part by the final state in Task 13 (D17, S1–S7); these snippets are the historical TDD record.

**Files:**

- Create: `packages/earnest/src/earnest/plan.py`
- Test: `packages/earnest/tests/unit/test_plan.py`

**Interfaces:**

- Consumes: `index.split_lines` (M1). Nothing from the earlier tasks of this milestone.
- Produces, with every shape read from upstream at `fe563195d827` (`rp7-upstream.md` sections 2, 3 and 7): `STATE = "aidlc-state.md"` and `AUDIT = "audit"`.
- Produces: `Row(phase, slug, mark, action, reason, line)`, a frozen dataclass for one Stage Progress row, with the property `stage`, `<phase>/<slug>`; `State(scope, rows, unread, heading)`; `Event(key, name, fields)`, a frozen dataclass ordered by `key` alone, where `key` is `(timestamp, shard file name, position in the shard)` and is the total order of the audit log, `name` is the `Event` field and `fields` every field of the block; `Record(directory, state_path, state, events)`.
- Produces: `parse_state(text) -> State`. `scope` is the first `- **Scope**: <value>` line. The rows are those of the `## Stage Progress` section, up to the next second-level heading: a `### <NAME> PHASE` heading sets the phase (the trailing word `PHASE` stripped, case ignored, lower-cased), and a row is `- [<mark>] <slug> — EXECUTE|SKIP` followed by nothing, or by a colon or a space and a reason, with a mark among space, `-`, `?`, `R`, `x` and `S`. Marks come back as written and are never read as status. Checkbox lines outside the section are ignored. Inside it, a line that starts with `- [` and is not a row Earnest can read, because it does not match the pattern or stands before the first phase heading, is not dropped silently: its line number goes into `unread`, so that Task 9 reports it. `heading` is the line of the first `## Stage Progress` heading, `0` when the file has none. Lines are numbered as Git counts them.
- Produces: `parse_audit(text, shard) -> list[Event]`. CRLF reads as LF. A block ends at a line that is exactly `---`. Its fields are the lines `**Field**: value`, the first of each name winning, so the first `Timestamp` of a block is the one used. A block with no `Timestamp` or no `Event` is ignored. The position counts every block of the shard, ignored ones included.
- Produces: `load(root, files) -> list[Record]`. One `Record` per listed `aidlc-state.md`, whose `directory` is its parent (`""` at the repository root), with the events of every listed `<directory>/audit/*.md` shard in one list sorted by key. Text decodes as UTF-8 with a byte order mark dropped and bad bytes replaced. A listed file that is gone from the work tree, or is a symlink, is skipped as `adapters.scan` skips it (R11); any other read failure raises `OSError`. The records are sorted by `directory`, not by state-file path, which would put `a-b/` before `a/`.

- [ ] **Step 1: Write the failing tests**

Create `packages/earnest/tests/unit/test_plan.py`:

```python
"""Tests for earnest.plan: the state file's Stage Progress, the audit shards, and loading both from a work tree."""

from earnest import plan
from earnest.plan import Event, Record, Row


DASH = "\u2014"
STATE_TEXT = f"""# AI-DLC State Tracking

## Project Information
- **Project**: checkout
- **Scope**: bugfix

## Stage Progress
<!-- Checkbox states: [ ] pending, [-] in-progress, [?] awaiting approval, [R] revising, [x] completed, [S] skipped -->
### INITIALIZATION PHASE
- [x] workspace-scaffold {DASH} EXECUTE: always
- [x] state-init {DASH} EXECUTE: always

### INCEPTION PHASE
- [S] reverse-engineering {DASH} EXECUTE: greenfield project
- [S] units-generation {DASH} SKIP: not in bugfix scope

## Current Status
- [x] not-a-row {DASH} EXECUTE: after the section
"""


def block(timestamp, event, **fields):
    """Return an audit block as AI-DLC writes it."""
    lines = ["## Heading", f"**Timestamp**: {timestamp}", f"**Event**: {event}"]
    lines += [f"**{name.replace('_', ' ')}**: {value}" for name, value in fields.items()]
    return "\n".join([*lines, "---"]) + "\n"


def put(root, files):
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")


def test_scope_is_read_from_the_state_file():
    assert plan.parse_state(STATE_TEXT).scope == "bugfix"
    assert plan.parse_state("# nothing\n").scope == ""


def test_stage_progress_rows_are_read_in_order_with_phase_slug_mark_action_reason_and_line():
    assert plan.parse_state(STATE_TEXT).rows == (
        Row("initialization", "workspace-scaffold", "x", "EXECUTE", "always", 10),
        Row("initialization", "state-init", "x", "EXECUTE", "always", 11),
        Row("inception", "reverse-engineering", "S", "EXECUTE", "greenfield project", 14),
        Row("inception", "units-generation", "S", "SKIP", "not in bugfix scope", 15),
    )
    assert plan.parse_state(STATE_TEXT).rows[2].stage == "inception/reverse-engineering"


def test_phase_heading_loses_the_word_phase_and_is_lower_cased():
    text = f"## Stage Progress\n### CONSTRUCTION PHASE\n- [ ] a {DASH} EXECUTE\n### Operation Phase\n- [ ] b {DASH} SKIP: x\n"
    assert [(row.phase, row.reason) for row in plan.parse_state(text).rows] == [
        ("construction", ""),
        ("operation", "x"),
    ]


def test_checkbox_lines_outside_stage_progress_are_ignored():
    text = (
        f"- [x] early {DASH} EXECUTE: before any section\n## Stage Progress\n- [x] no-phase {DASH} EXECUTE: no heading yet\n"
        f"### INCEPTION PHASE\n- [x] a {DASH} EXECUTE: yes\nnot a row\n- [x] b - EXECUTE: wrong dash\n"
        f"## Unit Progress\n- [x] c {DASH} EXECUTE: after\n"
    )
    state = plan.parse_state(text)
    assert [row.slug for row in state.rows] == ["a"]
    assert (state.unread, state.heading) == ((3, 7), 2)  # the row before any phase, and the one with the wrong dash


def test_state_without_stage_progress_has_no_rows():
    assert plan.parse_state("# AI-DLC State Tracking\n\n## Project Information\n- **Scope**: classic\n").rows == ()
    assert plan.parse_state("").rows == ()
    for text in ("# AI-DLC State Tracking\n\n## Stage  Progress\n### INCEPTION PHASE\n- [x] a - EXECUTE\n", ""):
        state = plan.parse_state(text)
        assert (state.rows, state.unread, state.heading) == ((), (), 0)  # a renamed heading is no section at all


def test_unreadable_rows_under_stage_progress_are_collected_by_line():
    text = (
        f"## Stage Progress\n### INCEPTION PHASE\n- [x] a {DASH} EXECUTE (always)\n- [x] b {DASH} EXECUTE: ok\n"
        f"- [x] c -- EXECUTE\n- [?x] d {DASH} EXECUTE\n- [x] e {DASH} MAYBE\n- [x] f {DASH} EXECUTEX\n"
    )
    state = plan.parse_state(text)
    assert [row.slug for row in state.rows] == ["a", "b"]
    assert (state.unread, state.heading) == ((5, 6, 7, 8), 1)


def test_row_tail_may_be_a_bare_word_or_follow_a_space():
    text = (
        f"## Stage Progress\n### INCEPTION PHASE\n- [x] a {DASH} EXECUTE\n- [x] b {DASH} EXECUTE (always)\n"
        f"- [x] c {DASH} SKIP: x\n- [x] d {DASH} EXECUTE:x\n"
    )
    assert [(row.slug, row.action, row.reason) for row in plan.parse_state(text).rows] == [
        ("a", "EXECUTE", ""),
        ("b", "EXECUTE", "(always)"),
        ("c", "SKIP", "x"),
        ("d", "EXECUTE", "x"),
    ]


def test_heading_line_of_stage_progress_is_recorded():
    assert plan.parse_state(STATE_TEXT).heading == 7
    assert plan.parse_state("## Stage Progress\n## Stage Progress\n").heading == 1  # the first one


def test_row_marks_are_returned_as_written():
    marks = [" ", "-", "?", "R", "x", "S"]
    text = "## Stage Progress\n### INCEPTION PHASE\n" + "".join(
        f"- [{mark}] s{number} {DASH} EXECUTE\n" for number, mark in enumerate(marks)
    )
    assert [row.mark for row in plan.parse_state(text).rows] == marks


def test_blocks_split_at_the_rule_line_and_fields_are_read():
    text = block("2026-09-26T09:00:00Z", "WORKFLOW_STARTED", Scope="bugfix") + block(
        "2026-09-26T10:00:00Z", "GATE_APPROVED", Stage="requirements-analysis", Items="req~a~1, req~b~1"
    )
    events = plan.parse_audit(text, "a.md")
    assert [(event.key, event.name) for event in events] == [
        (("2026-09-26T09:00:00Z", "a.md", 0), "WORKFLOW_STARTED"),
        (("2026-09-26T10:00:00Z", "a.md", 1), "GATE_APPROVED"),
    ]
    assert events[1].fields["Items"] == "req~a~1, req~b~1"
    assert events[1].fields["Stage"] == "requirements-analysis"


def test_first_timestamp_of_a_block_is_used():
    text = "## H\n**Timestamp**: 2026-09-26T09:00:00Z\n**Event**: STAGE_STARTED\n**Timestamp**: 2030-01-01T00:00:00Z\n---\n"
    (event,) = plan.parse_audit(text, "a.md")
    assert event.key[0] == "2026-09-26T09:00:00Z"


def test_block_without_timestamp_or_event_is_ignored():
    text = "## H\n**Event**: STAGE_STARTED\n---\n## H\n**Timestamp**: 2026-09-26T09:00:00Z\n---\n" + block(
        "2026-09-26T10:00:00Z", "HUMAN_TURN"
    )
    events = plan.parse_audit(text, "a.md")
    assert [(event.name, event.key[2]) for event in events] == [
        ("HUMAN_TURN", 2)
    ]  # ignored blocks still take a position


def test_event_name_is_the_event_field():
    text = (
        "## Gate Approved\n**Timestamp**: 2026-09-26T10:00:00Z\n**Event**: GATE_APPROVED\n**Details**: **Event**: no\n"
    )
    (event,) = plan.parse_audit(text, "a.md")  # a last block that the file leaves unclosed still counts
    assert (event.name, event.fields["Details"]) == ("GATE_APPROVED", "**Event**: no")


def test_crlf_shard_is_read_like_lf():
    text = block("2026-09-26T10:00:00Z", "GATE_APPROVED", Stage="a")
    assert plan.parse_audit(text.replace("\n", "\r\n"), "a.md") == plan.parse_audit(text, "a.md")
    assert plan.parse_audit(text.replace("\n", "\r\n"), "a.md")[0].fields["Stage"] == "a"


def test_events_order_by_timestamp_then_shard_name_then_position():
    same = "2026-09-26T09:00:00Z"
    early = plan.parse_audit(block("2026-09-26T08:00:00Z", "STAGE_STARTED"), "z.md")
    first = plan.parse_audit(block(same, "STAGE_STARTED") + block(same, "STAGE_COMPLETED"), "a.md")
    second = plan.parse_audit(block(same, "HUMAN_TURN"), "b.md")
    ordered = sorted([*second, *first[::-1], *early])
    assert [(event.key[1], event.name) for event in ordered] == [
        ("z.md", "STAGE_STARTED"),
        ("a.md", "STAGE_STARTED"),
        ("a.md", "STAGE_COMPLETED"),
        ("b.md", "HUMAN_TURN"),
    ]


def test_load_merges_every_audit_shard_into_one_ordered_log(tmp_path):
    record = "aidlc/spaces/default/intents/260926-checkout"
    put(
        tmp_path,
        {
            f"{record}/aidlc-state.md": STATE_TEXT,
            f"{record}/audit/b-1.md": block("2026-09-26T10:00:00Z", "GATE_APPROVED", Stage="requirements-analysis"),
            f"{record}/audit/a-1.md": block("2026-09-26T11:00:00Z", "GATE_REJECTED", Stage="requirements-analysis"),
            f"{record}/audit/notes.txt": block("2026-09-26T08:00:00Z", "WORKFLOW_STARTED"),
            f"{record}/inception/audit/c.md": block("2026-09-26T07:00:00Z", "WORKFLOW_STARTED"),
        },
    )
    files = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file())
    (found,) = plan.load(tmp_path, files)
    assert (found.directory, found.state_path) == (record, f"{record}/aidlc-state.md")
    assert found.state.scope == "bugfix"
    assert [(event.key[1], event.name) for event in found.events] == [
        ("b-1.md", "GATE_APPROVED"),
        ("a-1.md", "GATE_REJECTED"),
    ]


def test_load_lists_one_record_per_directory_holding_a_state_file(tmp_path):
    put(
        tmp_path,
        {
            "aidlc-state.md": STATE_TEXT,
            "audit/r.md": block("2026-09-26T09:00:00Z", "WORKFLOW_STARTED"),
            "one/aidlc-state.md": STATE_TEXT,
            "one/audit/o.md": block("2026-09-26T09:00:00Z", "STAGE_STARTED"),
            "two/deep/aidlc-state.md": STATE_TEXT,
            "docs/a.md": "# A\n",
        },
    )
    files = [
        "aidlc-state.md",
        "audit/r.md",
        "docs/a.md",
        "one/aidlc-state.md",
        "one/audit/o.md",
        "two/deep/aidlc-state.md",
    ]
    records = plan.load(tmp_path, files)
    assert [(record.directory, [event.name for event in record.events]) for record in records] == [
        ("", ["WORKFLOW_STARTED"]),
        ("one", ["STAGE_STARTED"]),
        ("two/deep", []),
    ]


def test_load_orders_records_by_directory_not_by_state_file_path(tmp_path):
    put(tmp_path, {"a-b/aidlc-state.md": STATE_TEXT, "a/aidlc-state.md": STATE_TEXT})
    files = ["a-b/aidlc-state.md", "a/aidlc-state.md"]  # by path, "a-b/" sorts before "a/"
    assert [record.directory for record in plan.load(tmp_path, files)] == ["a", "a-b"]


def test_load_without_a_state_file_gives_no_record(tmp_path):
    put(tmp_path, {"audit/a.md": block("2026-09-26T09:00:00Z", "WORKFLOW_STARTED"), "docs/a.md": "# A\n"})
    assert plan.load(tmp_path, ["audit/a.md", "docs/a.md"]) == []
    assert plan.load(tmp_path, []) == []


def test_load_reads_bad_utf8_with_replacement(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "aidlc-state.md").write_bytes(
        f"## Stage Progress\n### INCEPTION PHASE\n- [x] a {DASH} EXECUTE: caf".encode() + b"\xe9\n"
    )
    (tmp_path / "x" / "audit").mkdir()
    (tmp_path / "x" / "audit" / "a.md").write_bytes(
        b"\xef\xbb\xbf## H\n**Timestamp**: 2026-09-26T09:00:00Z\n**Event**: HUMAN_TURN\n**Details**: caf\xe9\n---\n"
    )
    (found,) = plan.load(tmp_path, ["x/aidlc-state.md", "x/audit/a.md"])
    assert found.state.rows[0].reason == "caf\ufffd"
    assert found.events[0].fields["Details"] == "caf\ufffd"  # and the byte order mark did not hide the first field


def test_load_skips_a_deleted_tracked_file_and_a_symlink(tmp_path):
    put(tmp_path, {"real/aidlc-state.md": STATE_TEXT, "real/audit/a.md": block("2026-09-26T09:00:00Z", "HUMAN_TURN")})
    (tmp_path / "link").mkdir()
    (tmp_path / "link" / "aidlc-state.md").symlink_to(tmp_path / "real" / "aidlc-state.md")
    (tmp_path / "real" / "audit" / "b.md").symlink_to(tmp_path / "real" / "audit" / "a.md")
    files = [
        "gone/aidlc-state.md",
        "link/aidlc-state.md",
        "real/aidlc-state.md",
        "real/audit/a.md",
        "real/audit/b.md",
        "real/audit/gone.md",
    ]
    records = plan.load(tmp_path, files)
    assert [record.directory for record in records] == ["real"]
    assert [event.key[1] for event in records[0].events] == ["a.md"]
    assert isinstance(records[0], Record)
    assert all(isinstance(event, Event) for event in records[0].events)
```

Run: `uv run pytest tests/unit/test_plan.py --no-cov -q`

Expected: collection fails with `ImportError: cannot import name 'plan' from 'earnest'`, `1 error`.

- [ ] **Step 2: Create `plan.py`**

Create `packages/earnest/src/earnest/plan.py`:

```python
"""Plan and stage engine: the state file's Stage Progress and the audit shards, read from the work tree."""

import posixpath
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from earnest.index import split_lines


STATE = "aidlc-state.md"
AUDIT = "audit"
_SCOPE = re.compile(r"^- \*\*Scope\*\*:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
_ROW = re.compile(r"- \[([ \-?RxS])\] (\S+) \u2014 (EXECUTE|SKIP)(?:[:\s][ \t]*(.*))?")
_FIELD = re.compile(r"\*\*([^*:]+)\*\*:[ \t]*(.*)")
_PHASE_WORD = re.compile(r"\s+PHASE$", re.IGNORECASE)


@dataclass(frozen=True)
class Row:
    """One Stage Progress row: its phase and slug, the checkbox mark as written, EXECUTE or SKIP, and its line."""

    phase: str
    slug: str
    mark: str
    action: str
    reason: str
    line: int

    @property
    def stage(self) -> str:
        """Return the stage's id: its phase and slug."""
        return f"{self.phase}/{self.slug}"


@dataclass(frozen=True)
class State:
    """What Earnest reads of an intent's `aidlc-state.md`: its scope, for display, and its Stage Progress rows.

    The lines it cannot read as rows are kept, so a route that shrinks because of them is never silent.
    """

    scope: str
    rows: tuple[Row, ...]
    unread: tuple[int, ...] = ()  # lines under Stage Progress that start `- [` and are no row Earnest can read
    heading: int = 0  # the line of the `## Stage Progress` heading, 0 when the file has none


@dataclass(frozen=True, order=True)
class Event:
    """One audit block. Events order by `key`: timestamp, then shard file name, then position in the shard."""

    # ponytail: timestamps compare as strings, which is right for upstream's fixed-width `YYYY-MM-DDTHH:MM:SSZ`; parse
    # them if a fractional second or an offset ever appears
    key: tuple[str, str, int]
    name: str = field(compare=False)
    fields: dict[str, str] = field(compare=False)


@dataclass(frozen=True)
class Record:
    """An intent's record directory: its state file's path and content, and every audit event, in order."""

    directory: str
    state_path: str
    state: State
    events: tuple[Event, ...]


def parse_state(text: str) -> State:
    """Read the scope and the Stage Progress rows of a state file; the marks are returned as written, never trusted."""
    normalized = text.replace("\r\n", "\n")
    scope = _SCOPE.search(normalized)
    rows: list[Row] = []
    unread: list[int] = []
    heading = 0
    in_progress = False
    phase = ""
    for line in split_lines(normalized):
        stripped = line.text.rstrip()
        if stripped.startswith("## "):
            in_progress = stripped[3:].strip() == "Stage Progress"
            heading = heading or (line.number if in_progress else 0)
            phase = ""
        elif in_progress and stripped.startswith("### "):
            phase = _PHASE_WORD.sub("", stripped[4:].strip()).lower()
        elif in_progress and stripped.startswith("- ["):
            if phase and (row := _ROW.fullmatch(stripped)):
                rows.append(Row(phase, row[2], row[1], row[3], row[4] or "", line.number))
            else:
                unread.append(line.number)
    return State(scope.group(1) if scope else "", tuple(rows), tuple(unread), heading)


def parse_audit(text: str, shard: str) -> list[Event]:
    """Read the events of one audit shard: blocks that end at a line `---`, with a Timestamp and an Event field."""
    events: list[Event] = []
    block: list[str] = []
    position = 0
    for line in [*text.replace("\r\n", "\n").split("\n"), "---"]:  # the last block counts, closed or not
        if line != "---":
            block.append(line)
            continue
        fields = _fields(block)
        if "Timestamp" in fields and "Event" in fields:
            events.append(Event((fields["Timestamp"], shard, position), fields["Event"], fields))
        block = []
        position += 1
    return events


def load(root: Path, files: Sequence[str]) -> list[Record]:
    """Read every intent among the listed files: one record per `aidlc-state.md`, sorted by its directory.

    Raises:
        OSError: a listed file that exists cannot be read.
    """
    records: list[Record] = []
    for path in files:
        state = _read(root, path) if posixpath.basename(path) == STATE else None
        if state is not None:
            directory = posixpath.dirname(path)
            events = [event for shard in _shards(files, directory) for event in _events(root, shard)]
            records.append(Record(directory, path, parse_state(state), tuple(sorted(events))))
    return sorted(records, key=lambda record: record.directory)


def _fields(lines: Sequence[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in lines:
        if match := _FIELD.fullmatch(line.rstrip()):
            found.setdefault(match[1], match[2].strip())  # the first of each name wins
    return found


def _shards(files: Sequence[str], directory: str) -> list[str]:
    audit = posixpath.join(directory, AUDIT)
    return [path for path in files if posixpath.dirname(path) == audit and path.endswith(".md")]


def _events(root: Path, shard: str) -> list[Event]:
    text = _read(root, shard)
    return [] if text is None else parse_audit(text, posixpath.basename(shard))


def _read(root: Path, path: str) -> str | None:
    """Return a listed file's text, or None when it is gone from the work tree or is a symlink, as the scanner skips."""
    file = root / path
    if file.is_symlink() or not file.is_file():
        return None
    return file.read_bytes().decode("utf-8-sig", errors="replace")
```

- [ ] **Step 3: Run the new tests and watch them pass**

Run: `uv run pytest tests/unit/test_plan.py --no-cov -q`

Expected: `21 passed`.

- [ ] **Step 4: Run the regression run and the linters**

```bash
uv run pytest --ignore=tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
make lint
```

Expected: `259 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/plan.py tests/unit/test_plan.py
git commit -m "feat: read the state file's Stage Progress and the audit shards"
```

### Task 9: The route, the counting rules, approvals and the frontier, `plan.py`

> Superseded in part by the final state in Task 13 (D17, S1–S7); these snippets are the historical TDD record.

**Files:**

- Modify: `packages/earnest/src/earnest/plan.py`
- Modify: `docs/design/01-logic-design.md` (one sentence of the `earnest/route-mismatch` row of the Findings table)
- Test: `packages/earnest/tests/unit/test_plan.py`

**Interfaces:**

- Consumes: `Record`, `Row`, `Event` (Task 8); `Index`, `Item` (M1); `Finding` and the rule `earnest/route-mismatch` (Task 5).
- Produces: `counting(events, rows) -> list[Event]`, the events that count. An event counts only if its key follows the key of the latest `WORKFLOW_STARTED` event and of every `STAGE_JUMPED` event whose reset span holds the event's `Stage`. `jump_span(jump, rows) -> frozenset[str]`: for a BACKWARD jump, its `Target` and the slug of every later row marked EXECUTE, skipped marks included; for a REDO jump, its `Target`; for a FORWARD jump, or a `Target` that names no row, nothing.
- Produces: `Approval(stage, items, by, digest)`: `items` is the tuple of ids and revisions the approving row's `Items` field names, `None` when the row has no such field; `by` is `human`, `automatic` or `None`; `digest` is the row's `Assessment Hash` or `None`.
- Produces: `Intent(directory, state_path, scope, rows, route, approvals, named_items, mismatches, unread, heading)` and `intent(record) -> Intent`. The route is the ids of the rows marked EXECUTE outside the initialization phase, in row order, less each slug that a counting `STAGE_SKIPPED` event names. `mismatches` are the rows of any phase, Initialization included, marked EXECUTE and skipped (`S`) that no counting `STAGE_SKIPPED` event names. `approvals` maps a route stage's id to its approval: the latest counting `GATE_APPROVED` event for its slug whose `Items` parse, unless a counting `GATE_REJECTED` event for the slug follows it. An event that carries `Unit`, `Gate Scope` or `Gate Stages` belongs to a team's per-unit gate and is ignored. `named_items` holds the `type~name~revision` ids of every counting `GATE_APPROVED` event with parsable items, whatever its stage, that no later counting `GATE_REJECTED` event for the same stage voids. `Intent.unsupported` is true when the route holds the slug `units-generation`.
- Produces: `route_findings(intent) -> list[Finding]`, each an error-level `earnest/route-mismatch` at the state file that reaches no stage. One per mismatch, at the row's line, naming the slug and the missing `STAGE_SKIPPED` row. One per unreadable line (`Intent.unread`, from Task 8), at that line, whose message names the line and says that Earnest cannot read it as a Stage Progress row. And one when the state file has no Stage Progress row at all, neither a readable nor an unreadable one, at the heading's line or at line 1 when there is no heading, saying that Earnest cannot read a Stage Progress section, so the route would be empty. Without this a stage dropped by a mistyped row, or a renamed heading, would shrink the route silently and the check would pass without checking; with it every command reports the line, exits 1 and holds the gate. A stage that such a row dropped is no longer on the route, so `check --stage` naming it exits 2 (not a stage on the route) instead.
- Produces: the amended Findings row. The `earnest/route-mismatch` row of the Findings table in `docs/design/01-logic-design.md` gains one clause, `, or a Stage Progress row, or the section itself, that Earnest cannot read`, and its message clause the line; the prose sentence about `route-mismatch` in Stages (Frontier and position's route paragraph) gains one clause (Step 5).
- Produces: `StageState(stage, approval, state, items)` with `state` one of `current`, `outdated` and `none`, `Plan(intent, stages, frontier)`, and `build(intent, index) -> Plan`. A stage's items are the index's defined items whose path lies under `<directory>/<stage id>/`. The state is `none` without an approval, `current` when the approval's `items` is `None` or equals the stage's current ids with revisions, and `outdated` otherwise. The frontier is the first stage whose state is not `current`, or `None`.

- [ ] **Step 1: Write the failing tests**

In `packages/earnest/tests/unit/test_plan.py`, replace:

```python
from earnest import plan
from earnest.plan import Event, Record, Row
```

with:

```python
from earnest import plan
from earnest.index import Id, Index, Item
from earnest.plan import Approval, Event, Record, Row
```

Append to the same file:

```python


HASH = "sha256:" + "0" * 64
STAGES = ("inception/requirements-analysis", "construction/code-generation", "construction/build-and-test")
FULL_STATE = f"""## Project Information
- **Scope**: bugfix

## Stage Progress
### INITIALIZATION PHASE
- [x] workspace-scaffold {DASH} EXECUTE: always
- [x] workspace-detection {DASH} EXECUTE: always
- [x] state-init {DASH} EXECUTE: always
### INCEPTION PHASE
- [S] reverse-engineering {DASH} EXECUTE: greenfield project
- [x] requirements-analysis {DASH} EXECUTE: always
- [S] units-generation {DASH} SKIP: not in bugfix scope
### CONSTRUCTION PHASE
- [x] code-generation {DASH} EXECUTE: always
- [x] build-and-test {DASH} EXECUTE: always
### OPERATION PHASE
- [S] deployment-pipeline {DASH} EXECUTE: no pipeline change
- [S] deployment-execution {DASH} EXECUTE: no pipeline change
"""
ROWS = plan.parse_state(FULL_STATE).rows
START = block("2026-09-26T09:00:00Z", "WORKFLOW_STARTED", Scope="bugfix")
SKIPS = "".join(
    block(f"2026-09-26T09:{minute}:00Z", "STAGE_SKIPPED", Stage=slug, Skip_Kind="conditional-runtime")
    for minute, slug in (("10", "reverse-engineering"), ("20", "deployment-pipeline"), ("21", "deployment-execution"))
)


def gate(timestamp, event="GATE_APPROVED", stage="requirements-analysis", **fields):
    return block(timestamp, event, Stage=stage, **fields)


def jump(timestamp, direction, target):
    fields = {"Direction": direction, "Source": "code-generation", "Target": target, "Scope": "bugfix"}
    return block(timestamp, "STAGE_JUMPED", **fields)


APPROVED = gate("2026-09-26T10:00:00Z", Items="req~a~1, req~b~1", Approved_By="human", Assessment_Hash=HASH)
BASE = START + SKIPS + APPROVED
REQUIREMENTS = STAGES[0]


def events_of(*blocks):
    return plan.parse_audit("".join(blocks), "a.md")


def intent_of(*blocks, state=FULL_STATE, directory="r"):
    events = tuple(sorted(events_of(*blocks)))
    return plan.intent(Record(directory, f"{directory}/aidlc-state.md", plan.parse_state(state), events))


def item(text, stage=REQUIREMENTS, line=1):
    kind, name, revision = text.split("~")
    return Item(Id(kind, name, int(revision)), f"r/{stage}/doc.md", line)


def counted(*blocks):
    return [(event.name, event.fields.get("Stage")) for event in plan.counting(events_of(*blocks), ROWS)]


def test_row_before_the_latest_workflow_started_does_not_count():
    assert counted(APPROVED, block("2026-09-26T11:00:00Z", "WORKFLOW_STARTED")) == []


def test_row_after_the_latest_workflow_started_counts():
    assert counted(START, APPROVED) == [("GATE_APPROVED", "requirements-analysis")]
    restart = block("2026-09-26T09:30:00Z", "WORKFLOW_STARTED")
    assert counted(START, gate("2026-09-26T09:20:00Z"), restart, APPROVED) == [
        ("GATE_APPROVED", "requirements-analysis")
    ]


def test_backward_jump_voids_rows_of_its_target_and_every_later_execute_row():
    later = gate("2026-09-26T10:30:00Z", stage="code-generation")
    kept = counted(START, SKIPS, APPROVED, later, jump("2026-09-26T11:00:00Z", "BACKWARD", "requirements-analysis"))
    assert kept == [("STAGE_SKIPPED", "reverse-engineering"), ("STAGE_JUMPED", None)]
    again = gate("2026-09-26T12:00:00Z")  # an approval after the jump belongs to the new attempt
    after = jump("2026-09-26T11:00:00Z", "BACKWARD", "requirements-analysis")
    assert REQUIREMENTS in intent_of(START, SKIPS, APPROVED, after, again).approvals


def test_backward_jump_reset_span_includes_skipped_marks():
    (event,) = events_of(jump("2026-09-26T11:00:00Z", "BACKWARD", "requirements-analysis"))
    span = plan.jump_span(event, ROWS)
    assert {"deployment-pipeline", "deployment-execution"} <= span  # rows marked [S] and EXECUTE
    assert "units-generation" not in span  # a planned SKIP row is no EXECUTE row


def test_backward_jump_leaves_earlier_stages_alone():
    (event,) = events_of(jump("2026-09-26T11:00:00Z", "BACKWARD", "code-generation"))
    span = plan.jump_span(event, ROWS)
    assert span == {"code-generation", "build-and-test", "deployment-pipeline", "deployment-execution"}


def test_redo_jump_voids_its_target_only():
    (event,) = events_of(jump("2026-09-26T11:00:00Z", "REDO", "code-generation"))
    assert plan.jump_span(event, ROWS) == {"code-generation"}
    (lower,) = events_of(jump("2026-09-26T11:00:00Z", "redo", "code-generation"))  # Direction is read in any case
    assert plan.jump_span(lower, ROWS) == {"code-generation"}


def test_forward_jump_voids_nothing():
    (event,) = events_of(jump("2026-09-26T11:00:00Z", "FORWARD", "build-and-test"))
    assert plan.jump_span(event, ROWS) == frozenset()
    assert counted(START, APPROVED, jump("2026-09-26T11:00:00Z", "FORWARD", "build-and-test"))[0] == (
        "GATE_APPROVED",
        "requirements-analysis",
    )


def test_jump_to_an_unknown_target_voids_nothing():
    for direction in ("BACKWARD", "REDO"):
        (event,) = events_of(jump("2026-09-26T11:00:00Z", direction, "no-such-stage"))
        assert plan.jump_span(event, ROWS) == frozenset()


def test_route_is_execute_rows_outside_initialization_in_row_order():
    assert intent_of(BASE).route == STAGES
    assert intent_of(START).route == (
        "inception/reverse-engineering",
        *STAGES,
        "operation/deployment-pipeline",
        "operation/deployment-execution",
    )


def test_route_id_is_phase_slash_slug():
    route = intent_of(BASE).route
    assert route[0] == "inception/requirements-analysis"
    assert not [stage for stage in route if stage.startswith("initialization/")]
    assert "inception/units-generation" not in route  # a SKIP row


def test_counting_skip_row_removes_a_stage_from_the_route():
    only = block("2026-09-26T09:20:00Z", "STAGE_SKIPPED", Stage="deployment-pipeline", Skip_Kind="conditional-runtime")
    route = intent_of(START, only).route
    assert "operation/deployment-pipeline" not in route
    assert "operation/deployment-execution" in route


def test_skip_mark_without_a_row_does_not_remove_a_stage():
    assert "operation/deployment-pipeline" in intent_of(START).route  # marked [S] and EXECUTE, and no audit row


def test_skip_row_inside_a_reset_span_puts_the_stage_back_on_the_route():
    route = intent_of(BASE, jump("2026-09-26T11:00:00Z", "BACKWARD", "requirements-analysis")).route
    assert "operation/deployment-pipeline" in route
    assert "operation/deployment-execution" in route
    assert "inception/reverse-engineering" not in route  # its skip row precedes the target, so it still counts


def test_skip_row_before_the_boundary_puts_the_stage_back_on_the_route():
    route = intent_of(SKIPS, block("2026-09-26T11:00:00Z", "WORKFLOW_STARTED")).route
    assert "inception/reverse-engineering" in route
    assert "operation/deployment-pipeline" in route


def test_route_mismatch_for_a_skipped_mark_without_a_counting_row():
    current = intent_of(START)
    assert [row.slug for row in current.mismatches] == [
        "reverse-engineering",
        "deployment-pipeline",
        "deployment-execution",
    ]
    found = plan.route_findings(current)
    assert [(f.rule, f.path, f.line, f.subject, f.level) for f in found] == [
        ("earnest/route-mismatch", "r/aidlc-state.md", 10, "reverse-engineering", "error"),
        ("earnest/route-mismatch", "r/aidlc-state.md", 17, "deployment-pipeline", "error"),
        ("earnest/route-mismatch", "r/aidlc-state.md", 18, "deployment-execution", "error"),
    ]
    assert all("`STAGE_SKIPPED`" in f.message and f.subject in f.message for f in found)
    assert all(f.stage is None for f in found)  # it reaches no stage


def test_route_mismatch_for_a_skipped_initialization_row():
    state = FULL_STATE.replace(f"- [x] state-init {DASH} EXECUTE", f"- [S] state-init {DASH} EXECUTE")
    current = intent_of(BASE, state=state)
    assert [row.slug for row in current.mismatches] == ["state-init"]
    assert "initialization/state-init" not in current.route  # an Initialization row never joins the route


def test_no_route_mismatch_when_a_counting_skip_row_exists():
    assert intent_of(BASE).mismatches == ()
    assert plan.route_findings(intent_of(BASE)) == []


def test_no_route_mismatch_for_pending_marks_and_skip_rows():
    state = FULL_STATE.replace(f"- [S] reverse-engineering {DASH} EXECUTE", f"- [ ] reverse-engineering {DASH} EXECUTE")
    only = block("2026-09-26T09:20:00Z", "STAGE_SKIPPED", Stage="deployment-pipeline", Skip_Kind="conditional-runtime")
    rest = block("2026-09-26T09:21:00Z", "STAGE_SKIPPED", Stage="deployment-execution", Skip_Kind="conditional-runtime")
    assert intent_of(START, only, rest, state=state).mismatches == ()  # [S] on a SKIP row is no EXECUTE row either


def test_unreadable_row_is_a_route_mismatch_finding_at_its_line():
    state = FULL_STATE.replace(f"- [x] code-generation {DASH} EXECUTE", "- [x] code-generation -- EXECUTE")
    current = intent_of(BASE, state=state)
    assert "construction/code-generation" not in current.route  # the route shrank, and the finding says why
    (found,) = plan.route_findings(current)
    assert (found.rule, found.path, found.line, found.level, found.stage) == (
        "earnest/route-mismatch",
        "r/aidlc-state.md",
        14,
        "error",
        None,
    )
    assert "Earnest cannot read line 14" in found.message
    assert "Stage Progress row" in found.message
    only = "## Stage Progress\n### CONSTRUCTION PHASE\n- [x] code-generation -- EXECUTE\n"
    (alone,) = plan.route_findings(intent_of(BASE, state=only))  # an unreadable row is no empty section as well
    assert "Earnest cannot read line 3" in alone.message


def test_empty_stage_progress_section_is_a_route_mismatch_finding_at_the_heading():
    state = "## Project Information\n- **Scope**: bugfix\n\n## Stage Progress\n\n## Current Status\n"
    current = intent_of(BASE, state=state)
    assert current.route == ()
    (found,) = plan.route_findings(current)
    assert (found.rule, found.line, found.level) == ("earnest/route-mismatch", 4, "error")
    assert "Earnest cannot read a Stage Progress section at line 4" in found.message


def test_missing_stage_progress_section_is_a_route_mismatch_finding_at_line_one():
    renamed = FULL_STATE.replace("## Stage Progress", "## Stage  Progress")
    for state in (renamed, "", "## Project Information\n- **Scope**: bugfix\n"):
        current = intent_of(BASE, state=state)
        assert current.route == ()
        (found,) = plan.route_findings(current)
        assert (found.line, found.path) == (1, "r/aidlc-state.md")
    assert plan.route_findings(intent_of(BASE)) == []  # a state file that reads gives none


def test_units_generation_on_the_route_is_unsupported():
    state = FULL_STATE.replace(
        f"- [S] units-generation {DASH} SKIP: not in bugfix scope", f"- [ ] units-generation {DASH} EXECUTE: needed"
    )
    current = intent_of(BASE, state=state)
    assert "inception/units-generation" in current.route
    assert current.unsupported


def test_units_generation_off_the_route_is_supported():
    assert not intent_of(BASE).unsupported
    assert not intent_of(START).unsupported


def test_approval_row_is_read():
    approval = intent_of(BASE).approvals[REQUIREMENTS]
    assert approval == Approval(REQUIREMENTS, ("req~a~1", "req~b~1"), "human", HASH)


def test_approved_by_automatic_is_read():
    row = gate("2026-09-26T10:00:00Z", Items="req~a~1", Approved_By="automatic")
    assert intent_of(START, row).approvals[REQUIREMENTS].by == "automatic"
    other = gate("2026-09-26T10:00:00Z", Items="req~a~1", Approved_By="robot")
    assert intent_of(START, other).approvals[REQUIREMENTS].by is None


def test_malformed_latest_approval_lets_the_older_one_count():
    bad = gate("2026-09-26T10:30:00Z", Items="req~a~1, nonsense")
    current = intent_of(START, APPROVED, bad)
    assert current.approvals[REQUIREMENTS].items == ("req~a~1", "req~b~1")  # the later row is no approval at all
    assert current.named_items == {"req~a~1", "req~b~1"}


def test_latest_counting_row_per_stage_is_the_approval():
    second = gate("2026-09-26T10:30:00Z", Items="req~a~2, req~b~1", Approved_By="automatic")
    approval = intent_of(START, APPROVED, second).approvals[REQUIREMENTS]
    assert (approval.items, approval.by) == (("req~a~2", "req~b~1"), "automatic")
    events = tuple(reversed(events_of(START, APPROVED, second)))  # the result does not depend on the input order
    unsorted = plan.intent(Record("r", "r/aidlc-state.md", plan.parse_state(FULL_STATE), events))
    assert unsorted.approvals[REQUIREMENTS] == approval


def test_rejection_after_the_approval_leaves_none():
    rejected = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Feedback="Rework.")
    assert intent_of(START, APPROVED, rejected).approvals == {}


def test_rejection_before_the_approval_is_history():
    rejected = gate("2026-09-26T09:30:00Z", "GATE_REJECTED", Feedback="Rework.")
    assert REQUIREMENTS in intent_of(START, rejected, APPROVED).approvals


def test_approval_after_a_rejection_counts():
    rejected = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Feedback="Rework.")
    again = gate("2026-09-26T12:00:00Z", Items="req~c~1")
    assert intent_of(START, APPROVED, rejected, again).approvals[REQUIREMENTS].items == ("req~c~1",)


def test_rows_with_unit_gate_scope_or_gate_stages_are_ignored():
    for field_name in ("Unit", "Gate_Scope", "Gate_Stages"):
        team = gate("2026-09-26T10:00:00Z", Items="req~a~1", **{field_name: "u1"})
        assert intent_of(START, team).approvals == {}
    team_rejection = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Unit="u1")
    assert REQUIREMENTS in intent_of(START, APPROVED, team_rejection).approvals


def test_row_without_items_is_an_approval_with_no_items():
    approval = intent_of(START, gate("2026-09-26T10:00:00Z")).approvals[REQUIREMENTS]
    assert approval == Approval(REQUIREMENTS, None, None, None)


def test_row_with_malformed_items_is_not_an_approval():
    bad = gate("2026-09-26T10:30:00Z", Items="req~a~1, nonsense")
    assert intent_of(START, bad).approvals == {}
    assert intent_of(START, APPROVED, bad).approvals[REQUIREMENTS].items == ("req~a~1", "req~b~1")  # the earlier row


def test_row_for_a_slug_off_the_route_is_not_an_approval():
    off = gate("2026-09-26T10:00:00Z", stage="reverse-engineering", Items="req~a~1")
    unknown = gate("2026-09-26T10:00:00Z", stage="no-such-stage", Items="req~a~1")
    assert intent_of(START, SKIPS, off, unknown).approvals == {}


def test_stage_progress_marks_never_change_an_approval():
    assert intent_of(START).approvals == {}  # every route stage is marked [x], and none is approved
    state = FULL_STATE.replace(f"- [x] requirements-analysis {DASH}", f"- [ ] requirements-analysis {DASH}")
    assert REQUIREMENTS in intent_of(BASE, state=state).approvals


def test_named_items_hold_the_ids_of_every_counting_row():
    other = gate("2026-09-26T10:30:00Z", stage="reverse-engineering", Items="req~z~9")
    assert intent_of(START, APPROVED, other).named_items == {"req~a~1", "req~b~1", "req~z~9"}


def test_voided_rows_name_nothing():
    rejected = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Feedback="Rework.")
    assert intent_of(START, APPROVED, rejected).named_items == frozenset()
    assert intent_of(APPROVED, block("2026-09-26T11:00:00Z", "WORKFLOW_STARTED")).named_items == frozenset()
    later = gate("2026-09-26T12:00:00Z", Items="req~c~1")
    assert intent_of(START, APPROVED, rejected, later).named_items == {"req~c~1"}
    other = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", stage="code-generation")  # another stage's rejection
    assert intent_of(START, APPROVED, other).named_items == {"req~a~1", "req~b~1"}


def test_rows_without_items_name_nothing():
    assert intent_of(START, gate("2026-09-26T10:00:00Z")).named_items == frozenset()
    assert intent_of(START, gate("2026-09-26T10:00:00Z", Items="nonsense")).named_items == frozenset()
    rejected = gate("2026-09-26T10:00:00Z", "GATE_REJECTED", Items="req~z~9")  # only an approval names its items
    assert intent_of(START, rejected).named_items == frozenset()


def test_team_rows_name_nothing_in_named_items():
    team = gate("2026-09-26T10:00:00Z", Items="req~a~1", Unit="u1", Gate_Scope="per-stage")
    assert intent_of(START, team).named_items == frozenset()


def test_approval_is_current_when_items_and_revisions_match():
    index = Index((item("req~a~1"), item("req~b~1")), (), ())
    state = plan.build(intent_of(BASE), index).stages[0]
    assert (state.state, state.items) == ("current", index.items)
    extra = Index((*index.items, item("req~c~1", stage=f"{REQUIREMENTS}-extra")), (), ())  # a stage of a longer name
    assert plan.build(intent_of(BASE), extra).stages[0].state == "current"


def test_approval_is_outdated_when_a_revision_moved():
    index = Index((item("req~a~2"), item("req~b~1")), (), ())
    assert plan.build(intent_of(BASE), index).stages[0].state == "outdated"
    assert plan.build(intent_of(BASE), Index((item("req~a~1"),), (), ())).stages[0].state == "outdated"  # one gone
    assert plan.build(intent_of(BASE), Index((*index.items, item("req~c~1")), (), ())).stages[0].state == "outdated"
    grown = Index((item("req~a~1"), item("req~b~1"), item("req~c~1")), (), ())  # an item added after the approval
    assert plan.build(intent_of(BASE), grown).stages[0].state == "outdated"


def test_approval_without_items_is_current_and_never_outdated():
    current = intent_of(START, SKIPS, gate("2026-09-26T10:00:00Z"))
    index = Index((item("req~a~7"), item("req~new~1")), (), ())
    assert plan.build(current, index).stages[0].state == "current"


def test_stage_without_a_row_has_no_approval():
    built = plan.build(intent_of(BASE), Index((), (), ()))
    assert [(state.stage, state.approval, state.state) for state in built.stages[1:]] == [
        (STAGES[1], None, "none"),
        (STAGES[2], None, "none"),
    ]


def test_frontier_is_the_first_stage_without_a_current_approval():
    index = Index((item("req~a~1"), item("req~b~1")), (), ())
    assert plan.build(intent_of(BASE), index).frontier == "construction/code-generation"
    assert plan.build(intent_of(START, SKIPS), index).frontier == REQUIREMENTS
    assert plan.build(intent_of(BASE), Index((item("req~a~2"),), (), ())).frontier == REQUIREMENTS


def test_frontier_is_none_when_every_stage_is_approved():
    rows = [gate("2026-09-26T10:00:00Z", stage=slug, Items="") for slug in ("requirements-analysis", "code-generation")]
    rows.append(gate("2026-09-26T10:30:00Z", stage="build-and-test"))
    built = plan.build(intent_of(START, SKIPS, *rows), Index((), (), ()))
    assert [state.state for state in built.stages] == ["current", "current", "current"]
    assert built.frontier is None


def test_rejected_stage_is_the_frontier_with_approval_none():
    rejected = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Feedback="Rework.")
    built = plan.build(intent_of(BASE, rejected), Index((item("req~a~1"), item("req~b~1")), (), ()))
    assert (built.stages[0].approval, built.stages[0].state, built.frontier) == (None, "none", REQUIREMENTS)
```

Run: `uv run pytest tests/unit/test_plan.py --no-cov -q`

Expected: collection fails with `ImportError: cannot import name 'Approval' from 'earnest.plan'`, `1 error`.

- [ ] **Step 2: Add the route, the counting rules, approvals and the frontier**

In `packages/earnest/src/earnest/plan.py`, replace:

```python
import posixpath
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from earnest.index import split_lines
```

with:

```python
import posixpath
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from earnest.index import TYPES, Index, Item, split_lines
from earnest.reporter import Finding
```

At the end of `packages/earnest/src/earnest/plan.py`, append:

```python


_INITIALIZATION = "initialization"
_TEAM_FIELDS = ("Unit", "Gate Scope", "Gate Stages")
_NO_BOUNDARY = ("", "", -1)  # sorts before every key
_ITEM_ID = re.compile(rf"(?:{'|'.join(TYPES)})~[a-z0-9-]+~[1-9][0-9]{{0,8}}")
_UNSUPPORTED = "units-generation"


@dataclass(frozen=True)
class Approval:
    """A stage's approval: the ids and revisions its row names (None without an `Items` field), who gave it, its hash."""

    stage: str
    items: tuple[str, ...] | None
    by: str | None
    digest: str | None


@dataclass(frozen=True)
class Intent:
    """An intent as its record says: its route, the approvals that count, and the ids that approvals froze."""

    directory: str
    state_path: str
    scope: str
    rows: tuple[Row, ...]
    route: tuple[str, ...]
    approvals: Mapping[str, Approval]
    named_items: frozenset[str]
    mismatches: tuple[Row, ...]
    unread: tuple[int, ...] = ()
    heading: int = 0

    @property
    def unsupported(self) -> bool:
        """Return whether the route holds `units-generation`, so per-unit stages, which M2 does not report."""
        return any(stage.partition("/")[2] == _UNSUPPORTED for stage in self.route)


@dataclass(frozen=True)
class StageState:
    """One stage of a plan: its approval, whether that approval is current, and the items its artifacts hold."""

    stage: str
    approval: Approval | None
    state: Literal["current", "outdated", "none"]
    items: tuple[Item, ...]


@dataclass(frozen=True)
class Plan:
    """An intent's stages in route order, and the frontier: the first stage without a current approval."""

    intent: Intent
    stages: tuple[StageState, ...]
    frontier: str | None


def jump_span(jump: Event, rows: Sequence[Row]) -> frozenset[str]:
    """Return the slugs whose earlier audit rows a jump voids.

    A BACKWARD jump resets its target and every later row marked EXECUTE, skipped marks included; a REDO jump resets
    its target; a FORWARD jump, or a target that names no row, resets nothing. Upstream voids no row: this is the rule
    by which Earnest reads an approval or a skip as part of the attempt it follows.
    """
    slugs = [row.slug for row in rows]
    target = jump.fields.get("Target", "")
    direction = jump.fields.get("Direction", "").upper()
    if target not in slugs or direction not in {"BACKWARD", "REDO"}:
        return frozenset()
    later = rows[slugs.index(target) + 1 :] if direction == "BACKWARD" else []
    return frozenset({target, *(row.slug for row in later if row.action == "EXECUTE")})


def counting(events: Sequence[Event], rows: Sequence[Row]) -> list[Event]:
    """Return the events that count: those after the latest `WORKFLOW_STARTED` and outside every jump's reset span."""
    boundary = max((event.key for event in events if event.name == "WORKFLOW_STARTED"), default=_NO_BOUNDARY)
    jumps = [(event.key, jump_span(event, rows)) for event in events if event.name == "STAGE_JUMPED"]
    return [
        event
        for event in events
        if event.key > boundary
        and not any(event.key <= key and event.fields.get("Stage") in span for key, span in jumps)
    ]


def intent(record: Record) -> Intent:
    """Build an intent from its record: the route, the approvals that count, and the ids they froze."""
    rows = record.state.rows
    events = counting(record.events, rows)
    skipped = {event.fields.get("Stage") for event in events if event.name == "STAGE_SKIPPED"}
    route = tuple(
        row.stage
        for row in rows
        if row.action == "EXECUTE" and row.phase != _INITIALIZATION and row.slug not in skipped
    )
    mismatches = tuple(row for row in rows if row.action == "EXECUTE" and row.mark == "S" and row.slug not in skipped)
    gates = [
        event
        for event in events
        if event.name in {"GATE_APPROVED", "GATE_REJECTED"} and not any(name in event.fields for name in _TEAM_FIELDS)
    ]
    approvals = {stage: found for stage in route if (found := _approval(stage, gates)) is not None}
    state = record.state
    return Intent(
        record.directory,
        record.state_path,
        state.scope,
        rows,
        route,
        approvals,
        _named(gates),
        mismatches,
        state.unread,
        state.heading,
    )


def route_findings(intent: Intent) -> list[Finding]:
    """Return the route-mismatch findings: unrecorded skips, and Stage Progress that Earnest cannot read.

    A stage marked skipped that the audit log does not record as skipped is one. So is any Stage Progress row, or the
    section itself, that Earnest cannot read, which would shrink the route silently.
    """
    path = intent.state_path
    found = [
        Finding(
            path,
            row.line,
            "earnest/route-mismatch",
            row.slug,
            f"`{row.slug}` is marked skipped and EXECUTE, and the audit log holds no counting `STAGE_SKIPPED` row for"
            " it: record the skip in the audit log, or restore the stage's mark",
        )
        for row in intent.mismatches
    ]
    for line in intent.unread:
        message = (
            f"Earnest cannot read line {line} of the state file as a Stage Progress row: write it as"
            " `- [x] slug \u2014 EXECUTE: reason` under a `### NAME PHASE` heading"
        )
        found.append(Finding(path, line, "earnest/route-mismatch", "Stage Progress", message))
    if not intent.rows and not intent.unread:
        line = intent.heading or 1
        message = (
            f"Earnest cannot read a Stage Progress section at line {line} of the state file, so the route would be"
            " empty: restore its `## Stage Progress` section, with `### NAME PHASE` headings and one row per stage"
        )
        found.append(Finding(path, line, "earnest/route-mismatch", "Stage Progress", message))
    return found


def build(intent: Intent, index: Index) -> Plan:
    """Build the plan of an intent over an index: each stage's items and approval, and the frontier."""
    stages: list[StageState] = []
    for stage in intent.route:
        prefix = posixpath.join(intent.directory, stage) + "/"
        items = tuple(item for item in index.defined.values() if item.path.startswith(prefix))
        approval = intent.approvals.get(stage)
        current = {str(item.id) for item in items}
        if approval is None:
            state: Literal["current", "outdated", "none"] = "none"
        elif approval.items is None or set(approval.items) == current:
            state = "current"
        else:
            state = "outdated"
        stages.append(StageState(stage, approval, state, items))
    frontier = next((state.stage for state in stages if state.state != "current"), None)
    return Plan(intent, tuple(stages), frontier)


def _items(event: Event) -> tuple[bool, tuple[str, ...] | None]:
    """Return whether the event's `Items` field parses, and the ids it names: None when the field is absent."""
    text = event.fields.get("Items")
    if text is None:
        return True, None
    tokens = tuple(token for token in re.split(r"[\s,]+", text) if token)
    return all(_ITEM_ID.fullmatch(token) for token in tokens), tokens


def _approval(stage: str, gates: Sequence[Event]) -> Approval | None:
    mine = [event for event in gates if event.fields.get("Stage") == stage.partition("/")[2]]
    approved = [
        (event, items) for event in mine if event.name == "GATE_APPROVED" for ok, items in (_items(event),) if ok
    ]
    if not approved:
        return None
    event, items = max(approved, key=lambda pair: pair[0].key)
    if any(other.name == "GATE_REJECTED" and other.key > event.key for other in mine):
        return None
    by = event.fields.get("Approved By")
    return Approval(stage, items, by if by in {"human", "automatic"} else None, event.fields.get("Assessment Hash"))


def _named(gates: Sequence[Event]) -> frozenset[str]:
    """Return the ids that counting approvals froze: those of every row that no later rejection of its stage voids."""
    named: set[str] = set()
    for event in gates:
        ok, items = _items(event)
        voided = any(
            other.name == "GATE_REJECTED"
            and other.key > event.key
            and other.fields.get("Stage") == event.fields.get("Stage")
            for other in gates
        )
        if event.name == "GATE_APPROVED" and ok and items and not voided:
            named.update(items)
    return frozenset(named)
```

- [ ] **Step 3: Run the new tests and watch them pass**

Run: `uv run pytest tests/unit/test_plan.py --no-cov -q`

Expected: `67 passed`: the 21 tests the file held, plus the 46 new ones.

- [ ] **Step 4: Run the regression run and the linters**

```bash
uv run pytest --ignore=tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
make lint
```

Expected: `305 passed`, then `make lint` exits 0.

- [ ] **Step 5: Amend the Findings row in `01`**

In `docs/design/01-logic-design.md`, replace the row:

```text
| `earnest/route-mismatch` | error | a stage row of the state file's Stage Progress that is marked EXECUTE carries the skipped mark with no counting `STAGE_SKIPPED` row; the message names the stage and the audit row that is missing. The finding reaches no stage |
```

with:

```text
| `earnest/route-mismatch` | error | a stage row of the state file's Stage Progress that is marked EXECUTE carries the skipped mark with no counting `STAGE_SKIPPED` row, or a Stage Progress row, or the section itself, that Earnest cannot read; the message names the stage and the audit row that is missing, or the line Earnest cannot read. The finding reaches no stage |
```

In the same file, replace the sentence of the Stages paragraph, which reads:

```text
EXECUTE row with the audit log, and such a row with no `STAGE_SKIPPED` row
raises `earnest/route-mismatch`. The route rule: needs and edges that name an
```

with:

```text
EXECUTE row with the audit log, and such a row with no `STAGE_SKIPPED` row,
like a Stage Progress row or section it cannot read, raises
`earnest/route-mismatch`. The route rule: needs and edges that name an
```

From the repository root run `LINT_FILE=docs/design/01-logic-design.md make lint-file`.

Expected: the hook lints the file and reports no issue.

- [ ] **Step 6: Commit**

From the repository root:

```bash
git add packages/earnest/src/earnest/plan.py packages/earnest/tests/unit/test_plan.py docs/design/01-logic-design.md
git commit -m "feat: build the route, read approvals and find the frontier"
```

### Task 10: Stage status, `unplanned`, `cycle`, approval notes and positions, `plan.py`

> Superseded in part by the final state in Task 13 (D17, S1–S7); these snippets are the historical TDD record.

**Files:**

- Modify: `packages/earnest/src/earnest/plan.py`
- Test: `packages/earnest/tests/unit/test_plan.py`

**Interfaces:**

- Consumes: `Plan`, `StageState`, `Intent`, `intent`, `route_findings` (Task 9); `structural.resolved_covers` (Task 7); `Finding` fields and `Position` (Task 5).
- Produces: `PRODUCES`, the item types that the artifacts of a stage slug hold, from the mapping table of Adopting AI-DLC, with the tag types pinned: `intent-capture` holds `tenet` and `goal`; `scope-definition` `feat`; `approval-and-handoff`, `domain-design`, `functional-design` and `nfr-design` `dsn`; `requirements-analysis` and `nfr-requirements` `req`; `units-generation` `unit`; `code-generation` `task`, `impl`, `utest`, `itest` and `stest`; every other slug nothing. `produces(intents) -> frozenset[str] | None`, the union over the route stages of the supported intents among those given, or `None` when none is supported or the union is empty, which is `structural.check`'s M1 behaviour: with an empty set every need and link would be dropped, `trace_check` would go red, and a route that an unreadable Stage Progress emptied would pass at 100% traced (Task 9 reports the unreadable section itself). With both kinds of intent present one union serves every intent's items (ponytail: a per-intent rule when a repository holds mixed profiles).
- Produces: `inside(intent, path) -> bool`, whether a file lies in the intent's record directory. `stage_of(intent, path) -> str | None`, the route stage id of a path under `<directory>/<stage id>/`. `in_tree(intents, path) -> bool`, the evaluated-tree rule: true when the path lies outside every intent directory, or under a route stage's path of the intent that holds it, so the state file, the audit log, `.aidlc-engine/` and the files of a stage off the route are out. It receives every record directory, supported or not, so an unsupported intent's AI-DLC files stay out of the tree.
- Produces: `task_done(task, index, levels) -> bool`: every `Delivers:` target resolves at its current revision, each delivered `req` is at trace level evidenced, and each delivered `dsn` has a resolved `impl` cover. In M2 no `req` is evidenced, so a task that delivers one is never done (PD5). `StageStatus(status, errors, open_tasks, approval)` and `statuses(plan, index, findings, levels) -> dict[str, StageStatus]`, keyed by stage id: a stage is done when no error-level finding is placed against it, every task among its items is done, and its approval is current. A stage with the slug `build-and-test` also counts each distinct `stest`-covered id as open, since an `stest` passes only at evidence.
- Produces: `plan_findings(plan, index) -> list[Finding]`, each stamped with its `stage` and `intent`: `earnest/unplanned` for each `req` of the intent that no task delivers, counted against the first stage on the route whose slug is `code-generation`, and none on a route without one; `earnest/cycle` for each cycle in the `Depends:` graph of the intent's tasks, located at the id line of the first task of the cycle in id order, with the message listing the loop as `task~a~1 -> task~b~1 -> task~a~1`, counted against the stage that holds that task; and `route_findings(plan.intent)`.
- Produces: `approval_findings(plan) -> list[Finding]`, kept apart so that the assessment document can leave them out: for each stage whose approval is outdated, an `earnest/outdated` finding with `note` set, at the id line of each stage item whose revision differs from the one the approval names, counted against that stage, naming the stage to approve again and the item's current revision. An approval that names an item now gone, or a stage that holds an item the approval never named, reads outdated and raises no located finding.
- Produces: `place(plans, index, findings) -> list[Finding]`. With no plan the findings return unchanged. A finding that already carries a stage keeps it. Otherwise a `gap` takes the first route stage whose `PRODUCES` holds its `child` type; a finding at the `path` and `line` of an `stest` link takes the Build and Test stage; a finding in a file under a route stage's path takes that stage; a finding whose subject is a delivered item takes the stage of the task that delivers it, at any revision; every other finding, including one in a stage off the route, reaches no stage. A finding that gets a stage gets its `intent` and its position from the frontier of that intent: before it behind, at it current, after it ahead, and all behind when no frontier is left.
- Produces: `properties(plans, statuses_by_intent, index, levels) -> dict[str, object]`: `{"intents": [...]}`, one entry per supported plan in directory order, each with `intent`, `stages` (in route order, each with `stage`, `status`, `approval` and `approvedBy`, which is set only for a current approval), `frontier`, `tasks` (`id` and `status`, sorted by that pair) and `units`, empty in M2.

- [ ] **Step 1: Write the failing tests**

In `packages/earnest/tests/unit/test_plan.py`, replace:

```python
from earnest import plan
from earnest.index import Id, Index, Item
from earnest.plan import Approval, Event, Record, Row
```

with:

```python
from earnest import plan
from earnest.index import Id, Index, Item, Link
from earnest.plan import Approval, Event, Record, Row
from earnest.reporter import Finding
```

Append to the same file:

```python


CODE_GENERATION = STAGES[1]
BUILD_AND_TEST = STAGES[2]
PLAN_PATH = f"r/{CODE_GENERATION}/plan.md"


def ident(text):
    kind, name, revision = text.split("~")
    return Id(kind, name, int(revision))


def delivers(task_text, req_text, line=7):
    return Link("Delivers", "task", ident(req_text), PLAN_PATH, line, owner=ident(task_text))


def depends(task_text, other_text, line=8):
    return Link("Depends", "task", ident(other_text), PLAN_PATH, line, owner=ident(task_text))


def task(text, line=3):
    return item(text, stage=CODE_GENERATION, line=line)


def planned(*blocks, items=(), links=(), state=FULL_STATE):
    """Return the plan and the index of an intent that the audit blocks describe, over the given items and links."""
    index = Index(tuple(items), tuple(links), ())
    return plan.build(intent_of(*blocks, state=state), index), index


def found_in(stage, **fields):
    return Finding("r/x.md", 1, "earnest/gap", "req~a~1", "m", stage=stage, intent="r", **fields)


def test_stage_of_a_path_under_a_route_stage():
    current = intent_of(BASE)
    assert plan.stage_of(current, "r/inception/requirements-analysis/requirements.md") == REQUIREMENTS
    assert plan.stage_of(current, f"r/{CODE_GENERATION}/deep/plan.md") == CODE_GENERATION


def test_stage_of_a_path_outside_every_stage():
    current = intent_of(BASE)
    for path in ("r/aidlc-state.md", "src/a.py", "r/inception/reverse-engineering/a.md", "rr/inception/x.md"):
        assert plan.stage_of(current, path) is None


def test_in_tree_for_paths_outside_every_intent():
    assert plan.in_tree([intent_of(BASE)], "src/a.py")
    assert plan.in_tree([intent_of(BASE)], "docs/readme.md")
    assert plan.in_tree([], "r/aidlc-state.md")


def test_in_tree_for_a_route_stage_artifact():
    assert plan.in_tree([intent_of(BASE)], "r/inception/requirements-analysis/requirements.md")
    assert plan.in_tree([intent_of(BASE)], f"r/{CODE_GENERATION}/plan.md")


def test_in_tree_is_false_for_state_audit_engine_and_off_route_stage_files():
    current = intent_of(BASE)
    for path in (
        "r/aidlc-state.md",
        "r/audit/a.md",
        "r/.aidlc-engine/sensors/earnest/detail.md",
        "r/inception/reverse-engineering/notes.md",
        "r/loose.md",
    ):
        assert not plan.in_tree([current], path)


def test_produces_is_the_union_of_the_route_stages_types():
    assert plan.produces([intent_of(BASE)]) == {"req", "task", "impl", "utest", "itest", "stest"}


def test_produces_pins_the_tag_types_of_code_generation():
    assert {"impl", "utest", "itest", "stest", "task"} <= plan.PRODUCES["code-generation"]
    assert plan.PRODUCES["requirements-analysis"] == {"req"}
    assert plan.PRODUCES.get("build-and-test", frozenset()) == frozenset()


def test_unknown_slug_produces_nothing():
    state = FULL_STATE.replace("### OPERATION PHASE", f"### OPERATION PHASE\n- [x] mystery-stage {DASH} EXECUTE: x")
    assert plan.produces([intent_of(BASE, state=state)]) == {"req", "task", "impl", "utest", "itest", "stest"}


def test_produces_is_none_when_the_route_produces_nothing():
    assert plan.produces([intent_of(BASE, state="## Stage Progress\n")]) is None  # an emptied route is no route rule
    assert plan.produces([intent_of(BASE, state="")]) is None


def test_produces_is_none_when_no_intent_is_supported():
    state = FULL_STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")
    assert plan.produces([]) is None
    assert plan.produces([intent_of(BASE, state=state)]) is None
    assert plan.produces([intent_of(BASE, state=state), intent_of(BASE)]) == plan.produces([intent_of(BASE)])


def test_in_tree_is_false_for_an_unsupported_intents_state_and_audit_files():
    state = FULL_STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")
    unsupported = intent_of(BASE, state=state, directory="u")
    assert unsupported.unsupported
    assert not plan.in_tree([unsupported], "u/aidlc-state.md")
    assert not plan.in_tree([unsupported], "u/audit/a.md")
    assert plan.in_tree([unsupported], "u/inception/requirements-analysis/requirements.md")


def test_stage_is_not_done_without_an_approval():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    assert plan.statuses(built, index, [], {})[BUILD_AND_TEST] == plan.StageStatus("not done", 0, 0, "none")


def test_stage_is_done_with_an_approval_and_no_error():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    assert plan.statuses(built, index, [], {})[REQUIREMENTS] == plan.StageStatus("done", 0, 0, "current")


def test_stage_is_not_done_with_an_error_counted_against_it():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    counted_ = [
        found_in(REQUIREMENTS),  # an error, and the only one that counts
        found_in(REQUIREMENTS, position="ahead"),  # a note
        found_in(REQUIREMENTS, note=True),
        found_in(CODE_GENERATION),  # another stage
        Finding("r/x.md", 1, "earnest/unplanned", "req~a~1", "m", stage=REQUIREMENTS, intent="r"),  # a warning
        Finding("r/x.md", 1, "earnest/gap", "req~a~1", "m", stage=REQUIREMENTS, intent="other"),
    ]
    assert plan.statuses(built, index, counted_, {})[REQUIREMENTS] == plan.StageStatus("not done", 1, 0, "current")


def test_stage_is_not_done_with_an_open_task():
    approved = gate("2026-09-26T10:30:00Z", stage="code-generation", Items="task~a~1, task~b~1")
    items = [item("req~a~1"), item("req~b~1"), task("task~a~1"), task("task~b~1", 9)]
    links = [delivers("task~a~1", "req~a~1"), delivers("task~b~1", "req~b~1", 13)]
    built, index = planned(BASE, approved, items=items, links=links)
    status = plan.statuses(built, index, [], {"req~a~1": "traced", "req~b~1": "traced"})[CODE_GENERATION]
    assert status == plan.StageStatus("not done", 0, 2, "current")


def test_task_delivering_a_req_is_never_done_before_evidence():
    mine = task("task~a~1")
    index = Index((item("req~a~1"), mine), (delivers("task~a~1", "req~a~1"),), ())
    assert not plan.task_done(mine, index, {"req~a~1": "traced"})
    assert not plan.task_done(mine, index, {})
    assert plan.task_done(mine, index, {"req~a~1": "evidenced"})  # the rule, which no M2 requirement can meet
    stale = Index((item("req~a~2"), mine), (delivers("task~a~1", "req~a~1"),), ())
    assert not plan.task_done(mine, stale, {"req~a~2": "evidenced"})  # it delivers an older revision
    gone = Index((mine,), (delivers("task~a~1", "req~zzz~1"),), ())
    assert not plan.task_done(mine, gone, {})
    decision = Index((item("dsn~d~1"), mine), (delivers("task~a~1", "dsn~d~1"),), ())
    assert not plan.task_done(mine, decision, {})
    cover = Link("Covers", "impl", ident("dsn~d~1"), "src/a.py", 3)
    assert plan.task_done(mine, Index(decision.items, (*decision.links, cover), ()), {})


def test_reasons_count_errors_open_tasks_and_approval():
    stale, index = planned(BASE, items=[item("req~a~2"), item("req~b~1")])
    errors = [found_in(REQUIREMENTS), found_in(REQUIREMENTS)]
    assert plan.statuses(stale, index, errors, {})[REQUIREMENTS] == plan.StageStatus("not done", 2, 0, "outdated")
    stest = Link("Covers", "stest", ident("feat~f~1"), "tests/a.feature", 3)
    built, index = planned(BASE, gate("2026-09-26T10:30:00Z", stage="build-and-test"), links=[stest, stest])
    assert plan.statuses(built, index, [], {})[BUILD_AND_TEST] == plan.StageStatus("not done", 0, 1, "current")


def test_unplanned_counts_against_the_first_code_generation_stage():
    items = [item("req~a~1", line=3), item("req~b~1", line=8)]
    built, index = planned(BASE, items=items, links=[delivers("task~t~1", "req~a~1")])
    (found,) = plan.plan_findings(built, index)
    assert (found.rule, found.path, found.line, found.subject, found.level) == (
        "earnest/unplanned",
        "r/inception/requirements-analysis/doc.md",
        8,
        "req~b~1",
        "warning",
    )
    assert (found.stage, found.intent) == (CODE_GENERATION, "r")
    assert "`req~b~1` is delivered by no task" in found.message


def test_unplanned_ignores_the_delivered_revision():
    built, index = planned(BASE, items=[item("req~a~2")], links=[delivers("task~t~1", "req~a~1")])
    assert plan.plan_findings(built, index) == []


def test_route_without_code_generation_raises_no_unplanned():
    state = FULL_STATE.replace(f"- [x] code-generation {DASH} EXECUTE", f"- [x] code-generation {DASH} SKIP")
    built, index = planned(BASE, items=[item("req~a~1")], state=state)
    assert CODE_GENERATION not in built.intent.route
    assert plan.plan_findings(built, index) == []


def test_cycle_is_located_at_the_first_item_in_id_order():
    items = [task("task~b~1", 9), task("task~a~1", 3)]
    built, index = planned(
        BASE, items=items, links=[depends("task~b~1", "task~a~1"), depends("task~a~1", "task~b~1", 4)]
    )
    (found,) = plan.plan_findings(built, index)
    assert (found.rule, found.path, found.line, found.subject, found.level) == (
        "earnest/cycle",
        f"r/{CODE_GENERATION}/doc.md",
        3,
        "task~a~1",
        "error",
    )
    assert (found.stage, found.intent) == (CODE_GENERATION, "r")


def test_cycle_message_lists_the_loop():
    items = [task("task~a~1", 3), task("task~b~1", 9)]
    built, index = planned(BASE, items=items, links=[depends("task~a~1", "task~b~1"), depends("task~b~1", "task~a~1")])
    (found,) = plan.plan_findings(built, index)
    assert "task~a~1 -> task~b~1 -> task~a~1" in found.message
    alone, own = planned(BASE, items=[task("task~a~1")], links=[depends("task~a~1", "task~a~1")])
    assert "task~a~1 -> task~a~1" in plan.plan_findings(alone, own)[0].message


def test_overlapping_cycles_are_each_located_at_their_first_item_in_id_order():
    items = [task("task~aa~1", 3), task("task~bb~1", 9), task("task~cc~1", 15)]
    links = [
        depends("task~aa~1", "task~bb~1"),
        depends("task~bb~1", "task~aa~1"),
        depends("task~aa~1", "task~cc~1"),
        depends("task~cc~1", "task~aa~1"),
    ]
    built, index = planned(BASE, items=items, links=links)
    found = plan.plan_findings(built, index)
    assert [(f.line, f.subject) for f in found] == [(3, "task~aa~1"), (3, "task~aa~1")]
    loops = ["task~aa~1 -> task~bb~1 -> task~aa~1", "task~aa~1 -> task~cc~1 -> task~aa~1"]
    assert [any(loop in f.message for f in found) for loop in loops] == [True, True]
    assert all(f.message.startswith("the plan's dependencies form a cycle, task~aa~1 -> ") for f in found)


def test_acyclic_graph_has_no_cycle():
    items = [task("task~a~1", 3), task("task~b~1", 9)]
    built, index = planned(BASE, items=items, links=[depends("task~b~1", "task~a~1")])
    assert plan.plan_findings(built, index) == []


def test_finding_in_a_stage_artifact_takes_its_stage_and_intent():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    (found,) = plan.place(
        [built], index, [Finding("r/inception/requirements-analysis/x.md", 4, "earnest/duplicate", "req~a~1", "m")]
    )
    assert (found.stage, found.intent, found.position, found.level) == (REQUIREMENTS, "r", "behind", "error")
    assert found.text.startswith(f"regression in approved stage {REQUIREMENTS}: ")


def test_place_keeps_a_preset_stage():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    preset = Finding(
        "r/inception/requirements-analysis/x.md",
        4,
        "earnest/unplanned",
        "req~a~1",
        "m",
        stage=CODE_GENERATION,
        intent="r",
    )
    (found,) = plan.place([built], index, [preset])
    assert (found.stage, found.position) == (CODE_GENERATION, "current")
    alien = Finding("x", 1, "earnest/gap", "s", "m", stage="s/x", intent="elsewhere", position="ahead")
    (foreign,) = plan.place([built], index, [alien])
    assert (foreign.stage, foreign.intent, foreign.position) == ("s/x", "elsewhere", "ahead")  # no such plan: unchanged


def test_tag_finding_reaches_the_stage_of_the_delivering_task():
    items = [item("req~a~1"), item("req~b~1"), task("task~t~1")]
    built, index = planned(BASE, items=items, links=[delivers("task~t~1", "req~a~1")])
    tag = Finding("src/a.py", 4, "earnest/outdated", "req~a~1", "m")
    (found,) = plan.place([built], index, [tag])
    assert (found.stage, found.intent, found.position) == (CODE_GENERATION, "r", "current")


def test_stest_reaches_the_build_and_test_stage():
    stest = Link("Covers", "stest", ident("feat~f~1"), "tests/a.feature", 3)
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")], links=[stest])
    (found,) = plan.place([built], index, [Finding("tests/a.feature", 3, "earnest/orphaned", "feat~f~1", "m")])
    assert (found.stage, found.position, found.level) == (BUILD_AND_TEST, "ahead", "note")
    (other,) = plan.place([built], index, [Finding("tests/a.feature", 9, "earnest/orphaned", "feat~f~1", "m")])
    assert other.stage is None


def test_gap_counts_against_the_stage_of_the_missing_childs_type():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    path = "r/inception/requirements-analysis/doc.md"
    gaps = [Finding(path, 5, "earnest/gap", "req~a~1", "m", child=kind) for kind in ("impl", "utest", "req")]
    stages = [found.stage for found in plan.place([built], index, gaps)]
    assert stages == [CODE_GENERATION, CODE_GENERATION, REQUIREMENTS]  # a req gap falls back to its own file's stage


def test_finding_reaching_no_stage_keeps_position_current():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    orphan = Finding("src/z.py", 2, "earnest/orphaned", "req~zzz~1", "m")
    near = Finding("src/z.py", 3, "earnest/near-miss", "[impl-x]", "m")
    for found in plan.place([built], index, [orphan, near]):
        assert (found.stage, found.intent, found.position, found.level) == (None, None, "current", "error")


def test_position_behind_current_and_ahead():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    paths = [f"r/{stage}/x.md" for stage in STAGES]
    found = plan.place([built], index, [Finding(path, 1, "earnest/duplicate", "req~a~1", "m") for path in paths])
    assert [(f.stage, f.position) for f in found] == list(zip(STAGES, ["behind", "current", "ahead"], strict=True))


def test_place_takes_several_plans_and_uses_each_findings_own_frontier():
    first, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    second = plan.build(intent_of(START, SKIPS, directory="s"), index)
    mine = Finding(f"r/{CODE_GENERATION}/x.md", 1, "earnest/duplicate", "req~a~1", "m")
    theirs = Finding(f"s/{CODE_GENERATION}/x.md", 1, "earnest/duplicate", "req~a~1", "m")
    placed = plan.place([first, second], index, [mine, theirs])
    assert [(f.intent, f.position) for f in placed] == [("r", "current"), ("s", "ahead")]


def test_ahead_finding_is_a_note():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    (found,) = plan.place([built], index, [Finding(f"r/{BUILD_AND_TEST}/x.md", 1, "earnest/duplicate", "req~a~1", "m")])
    assert (found.position, found.level) == ("ahead", "note")
    assert found.text == f"expected at {BUILD_AND_TEST}: m"


def test_finding_in_a_stage_off_the_route_is_stage_less_and_current():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    (found,) = plan.place(
        [built], index, [Finding("r/inception/reverse-engineering/a.md", 1, "earnest/duplicate", "req~a~1", "m")]
    )
    assert (found.stage, found.intent, found.position) == (None, None, "current")


def test_finding_under_an_intent_without_a_plan_is_left_alone():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    elsewhere = Finding("other/inception/requirements-analysis/x.md", 1, "earnest/duplicate", "req~a~1", "m")
    assert plan.place([], index, [elsewhere])[0] is elsewhere
    (found,) = plan.place([built], index, [elsewhere])
    assert (found.stage, found.intent, found.position) == (None, None, "current")


def stale_plan(*items_, extra=()):
    """Return the plan of an intent whose requirements approval names req~a~1 and req~b~1, over the given items."""
    return planned(BASE, *extra, items=list(items_))


def test_stale_approval_is_a_note_at_the_position_of_its_stage():
    built, index = stale_plan(item("req~a~2", line=3), item("req~b~1", line=8))
    (found,) = plan.approval_findings(built)
    assert (found.rule, found.path, found.line, found.subject, found.note) == (
        "earnest/outdated",
        "r/inception/requirements-analysis/doc.md",
        3,
        "req~a~2",
        True,
    )
    (placed,) = plan.place([built], index, [found])
    assert (placed.stage, placed.intent, placed.position, placed.level) == (REQUIREMENTS, "r", "current", "note")


def test_stale_approval_in_a_stage_after_the_frontier_reads_ahead():
    approved = gate("2026-09-26T10:30:00Z", stage="code-generation", Items="task~a~1")
    built, index = planned(START, SKIPS, approved, items=[task("task~a~2")])
    assert built.frontier == REQUIREMENTS  # nothing approves the requirements stage
    (found,) = plan.approval_findings(built)
    (placed,) = plan.place([built], index, [found])
    assert (placed.stage, placed.position, placed.level) == (CODE_GENERATION, "ahead", "note")


def test_stale_approval_is_located_at_each_moved_item():
    built, _ = stale_plan(item("req~a~2", line=3), item("req~b~3", line=8))
    assert [(f.line, f.subject) for f in plan.approval_findings(built)] == [(3, "req~a~2"), (8, "req~b~3")]


def test_stale_approval_names_the_stage_and_the_current_revision():
    built, _ = stale_plan(item("req~a~2"), item("req~b~1"))
    (found,) = plan.approval_findings(built)
    assert REQUIREMENTS in found.message
    assert "approval" in found.message
    assert "revision 2" in found.message
    assert "`req~a~1`" in found.message


def test_earlier_rows_raise_nothing_after_a_fresh_approval():
    fresh = gate("2026-09-26T10:30:00Z", Items="req~a~2, req~b~1")
    built, _ = stale_plan(item("req~a~2"), item("req~b~1"), extra=[fresh])
    assert built.stages[0].state == "current"
    assert plan.approval_findings(built) == []


def test_stale_approval_with_a_removed_or_unnamed_item_reads_outdated_without_a_located_finding():
    gone, _ = stale_plan(item("req~a~1"))
    assert gone.stages[0].state == "outdated"
    assert plan.approval_findings(gone) == []
    extra, _ = stale_plan(item("req~a~1"), item("req~b~1"), item("req~c~1"))
    assert extra.stages[0].state == "outdated"
    assert plan.approval_findings(extra) == []


def test_properties_list_stages_in_route_order_and_tasks_sorted():
    items = [item("req~a~1"), item("req~b~1"), task("task~b~1"), task("task~a~1", 9)]
    built, index = planned(BASE, items=items, links=[delivers("task~a~1", "req~a~1")])
    statuses = {"r": plan.statuses(built, index, [], {})}
    (entry,) = plan.properties([built], statuses, index, {})["intents"]
    assert (entry["intent"], entry["frontier"], entry["units"]) == ("r", CODE_GENERATION, [])
    assert entry["stages"] == [
        {"stage": REQUIREMENTS, "status": "done", "approval": "current", "approvedBy": "human"},
        {"stage": CODE_GENERATION, "status": "not done", "approval": "none", "approvedBy": None},
        {"stage": BUILD_AND_TEST, "status": "not done", "approval": "none", "approvedBy": None},
    ]
    assert entry["tasks"] == [{"id": "task~a~1", "status": "not done"}, {"id": "task~b~1", "status": "done"}]


def test_properties_hold_one_entry_per_supported_intent():
    first, index = planned(BASE, items=[item("req~a~2"), item("req~b~1")])
    second = plan.build(intent_of(START, SKIPS, directory="a"), index)
    statuses = {p.intent.directory: plan.statuses(p, index, [], {}) for p in (first, second)}
    props = plan.properties([first, second], statuses, index, {})
    assert [entry["intent"] for entry in props["intents"]] == ["a", "r"]
    stale = props["intents"][1]["stages"][0]
    assert (stale["approval"], stale["approvedBy"]) == ("outdated", None)  # `approvedBy` is for a current approval


def test_properties_leave_out_an_unsupported_intent():
    state = FULL_STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")
    built, index = planned(BASE)
    unsupported = plan.build(intent_of(BASE, state=state, directory="u"), index)
    statuses = {p.intent.directory: plan.statuses(p, index, [], {}) for p in (built, unsupported)}
    props = plan.properties([unsupported, built], statuses, index, {})
    assert [entry["intent"] for entry in props["intents"]] == ["r"]
    assert plan.properties([unsupported], statuses, index, {}) == {"intents": []}
```

Run: `uv run pytest tests/unit/test_plan.py --no-cov -q`

Expected: `44 failed, 67 passed`: each new test fails with `AttributeError` (`module 'earnest.plan' has no attribute 'stage_of'` and the like), and the 67 tests the file held pass.

- [ ] **Step 2: Add the stage engine**

In `packages/earnest/src/earnest/plan.py`, replace:

```python
import posixpath
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from earnest.index import TYPES, Index, Item, split_lines
from earnest.reporter import Finding
```

with:

```python
import posixpath
import re
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from earnest import structural
from earnest.index import TYPES, Index, Item, split_lines
from earnest.reporter import Finding, Position
```

At the end of `packages/earnest/src/earnest/plan.py`, append:

```python


# What the artifacts of each stage slug hold, from the mapping table of Adopting AI-DLC. Code Generation holds the
# code and test tags too, so a route that runs it keeps the default needs of `req`.
PRODUCES: dict[str, frozenset[str]] = {
    "intent-capture": frozenset({"tenet", "goal"}),
    "scope-definition": frozenset({"feat"}),
    "approval-and-handoff": frozenset({"dsn"}),
    "requirements-analysis": frozenset({"req"}),
    "domain-design": frozenset({"dsn"}),
    "units-generation": frozenset({"unit"}),
    "functional-design": frozenset({"dsn"}),
    "nfr-requirements": frozenset({"req"}),
    "nfr-design": frozenset({"dsn"}),
    "code-generation": frozenset({"task", "impl", "utest", "itest", "stest"}),
}
_CODE_GENERATION = "code-generation"
_BUILD_AND_TEST = "build-and-test"
_SUBJECT = re.compile(r"([a-z]+)~([a-z0-9-]+)~[0-9]+")
_Located = tuple[Plan, str]


@dataclass(frozen=True)
class StageStatus:
    """A stage's computed status and the reasons for it: the errors against it, its open tasks, its approval."""

    status: Literal["done", "not done"]
    errors: int
    open_tasks: int
    approval: str


def produces(intents: Sequence[Intent]) -> frozenset[str] | None:
    """Return the item types that some route stage of a supported intent produces, or None when none is supported.

    None is the route rule's off switch: `structural.check` then keeps every need and link, as it does with no plan.
    """
    supported = [current for current in intents if not current.unsupported]
    types = frozenset().union(
        *(PRODUCES.get(stage.partition("/")[2], frozenset()) for current in supported for stage in current.route)
    )
    return types or None  # no supported route, or one that produces nothing: keep every need and link


def stage_of(intent: Intent, path: str) -> str | None:
    """Return the route stage whose path holds the file at path, or None."""
    return next(
        (stage for stage in intent.route if path.startswith(posixpath.join(intent.directory, stage) + "/")), None
    )


def in_tree(intents: Sequence[Intent], path: str) -> bool:
    """Return whether the file at path is in the evaluated tree: outside every record directory, or in a route stage.

    The state file, the audit shards, `.aidlc-engine/` and the files of a stage off the route lie in a record
    directory and in no route stage, so they are out.
    """
    holders = [current for current in intents if inside(current, path)]
    return not holders or any(stage_of(current, path) is not None for current in holders)


def task_done(task: Item, index: Index, levels: Mapping[str, str]) -> bool:
    """Return whether a task is done: each thing it delivers resolves, a `req` is evidenced and a `dsn` has an `impl`."""
    covers = structural.resolved_covers(index)
    for link in index.links:
        if link.key != "Delivers" or link.owner != task.id:
            continue
        resolution = index.resolutions[link.target]
        delivered = resolution.item
        if resolution.status != "resolved" or delivered is None:
            return False
        if delivered.id.type == "req" and levels.get(str(delivered.id)) != "evidenced":
            return False
        if delivered.id.type == "dsn" and ("impl", delivered) not in covers:
            return False
    return True


def statuses(
    plan: Plan, index: Index, findings: Sequence[Finding], levels: Mapping[str, str]
) -> dict[str, StageStatus]:
    """Return each stage's computed status from the graph: no error against it, its tasks done, a current approval."""
    stest = len({str(link.target) for link in index.links if link.type == "stest"})
    result: dict[str, StageStatus] = {}
    for state in plan.stages:
        # ponytail: an error placed ahead of the frontier is a note and not counted, so an approved stage after the
        # frontier can read done despite one; count `ahead` errors here if a gate ever depends on that stage.
        errors = sum(
            1
            for found in findings
            if found.intent == plan.intent.directory and found.stage == state.stage and found.level == "error"
        )
        open_tasks = sum(1 for item in state.items if item.id.type == "task" and not task_done(item, index, levels))
        if state.stage.partition("/")[2] == _BUILD_AND_TEST:
            open_tasks += stest  # an `stest` passes only at evidence, which M2 has none of
        done = errors == 0 and open_tasks == 0 and state.state == "current"
        result[state.stage] = StageStatus("done" if done else "not done", errors, open_tasks, state.state)
    return result


def plan_findings(plan: Plan, index: Index) -> list[Finding]:
    """Return the findings the plan itself raises: `unplanned`, `cycle` and `route-mismatch`."""
    return [*_unplanned(plan, index), *_cycle_findings(plan, index), *route_findings(plan.intent)]


def approval_findings(plan: Plan) -> list[Finding]:
    """Return a note for each item that a stale approval names at an older revision, located at the item's id line.

    They stay apart from `plan_findings` so that the assessment document can leave them out: a fresh approval removes
    them, and recording an approval must not change the hash.
    """
    found: list[Finding] = []
    for state in plan.stages:
        if state.state != "outdated" or state.approval is None or state.approval.items is None:
            continue
        named = {tuple(entry.split("~")[:2]): entry for entry in state.approval.items}
        for item in state.items:
            old = named.get(item.id.key)
            if old is not None and old != str(item.id):
                message = (
                    f"the approval of `{state.stage}` names `{old}`, and the item is at revision {item.id.revision}:"
                    f" check the change, then approve `{state.stage}` again"
                )
                found.append(
                    Finding(
                        item.path,
                        item.line,
                        "earnest/outdated",
                        str(item.id),
                        message,
                        stage=state.stage,
                        intent=plan.intent.directory,
                        note=True,
                    )
                )
    return found


def place(plans: Sequence[Plan], index: Index, findings: Sequence[Finding]) -> list[Finding]:
    """Give each finding the stage it counts against, its intent and its position by that intent's frontier.

    With no plan the findings return unchanged. A finding that reaches no stage keeps position current.
    """
    if not plans:
        return list(findings)
    delivering = _delivering(plans, index)
    stest_lines = {(link.path, link.line) for link in index.links if link.type == "stest"}
    placed: list[Finding] = []
    for finding in findings:
        found = _locate(finding, plans, delivering, stest_lines)
        if found is None:
            placed.append(finding)
            continue
        current, stage = found
        placed.append(
            replace(finding, stage=stage, intent=current.intent.directory, position=_position(current, stage))
        )
    return placed


def properties(
    plans: Sequence[Plan],
    statuses_by_intent: Mapping[str, Mapping[str, StageStatus]],
    index: Index,
    levels: Mapping[str, str],
) -> dict[str, object]:
    """Return `properties.plan`: one entry per supported plan, in directory order, with its stages, frontier and tasks."""
    entries: list[dict[str, object]] = []
    for current in sorted(plans, key=lambda each: each.intent.directory):
        if current.intent.unsupported:
            continue
        status = statuses_by_intent[current.intent.directory]
        tasks = sorted(
            (
                {"id": str(item.id), "status": "done" if task_done(item, index, levels) else "not done"}
                for state in current.stages
                for item in state.items
                if item.id.type == "task"
            ),
            key=lambda task: (task["id"], task["status"]),
        )
        stages = [
            {
                "stage": state.stage,
                "status": status[state.stage].status,
                "approval": state.state,
                "approvedBy": state.approval.by if state.state == "current" and state.approval else None,
            }
            for state in current.stages
        ]
        entries.append(
            {
                "intent": current.intent.directory,
                "stages": stages,
                "frontier": current.frontier,
                "tasks": tasks,
                "units": [],
            }
        )
    return {"intents": entries}


def inside(intent: Intent, path: str) -> bool:
    """Return whether the file at path lies in the intent's record directory."""
    return intent.directory == "" or path.startswith(intent.directory + "/")


def _unplanned(plan: Plan, index: Index) -> list[Finding]:
    stage = next((each for each in plan.intent.route if each.partition("/")[2] == _CODE_GENERATION), None)
    if stage is None:
        return []
    delivered = {
        link.target.key
        for link in index.links
        if link.key == "Delivers" and link.owner is not None and link.owner.type == "task"
    }
    return [
        Finding(
            item.path,
            item.line,
            "earnest/unplanned",
            str(item.id),
            f"`{item.id}` is delivered by no task: add a `task` that delivers it, with a `Delivers:` line",
            stage=stage,
            intent=plan.intent.directory,
        )
        for item in index.defined.values()
        if item.id.type == "req" and inside(plan.intent, item.path) and item.id.key not in delivered
    ]


def _depends(plan: Plan, index: Index) -> dict[str, list[str]]:
    edges: dict[str, list[str]] = {}
    for link in index.links:
        owner = index.defined.get(link.owner.key) if link.owner is not None else None
        target = index.defined.get(link.target.key)
        if link.key == "Depends" and owner is not None and target is not None and inside(plan.intent, owner.path):
            edges.setdefault(str(owner.id), []).append(str(target.id))
    return edges


def _cycle_through(edges: Mapping[str, Sequence[str]], start: str) -> list[str] | None:
    """Return the shortest path from start back to itself, taking the lowest id first, or None.

    ponytail: one cycle per start, the shortest, so a cycle that is never the shortest through any of its tasks is not
    listed; it shows once the shorter ones are fixed. Enumerate elementary cycles if that ever matters.
    """
    queue = deque([[start]])
    visited = {start}
    while queue:
        path = queue.popleft()
        for follower in sorted(edges.get(path[-1], ())):
            if follower == start:
                return [*path, start]
            if follower not in visited:
                visited.add(follower)
                queue.append([*path, follower])
    return None


def _cycle_findings(plan: Plan, index: Index) -> list[Finding]:
    edges = _depends(plan, index)
    by_id = {str(item.id): item for item in index.defined.values()}
    found: list[Finding] = []
    seen: set[tuple[str, ...]] = set()
    for start in sorted(edges):
        path = _cycle_through(edges, start)
        if path is None:
            continue
        nodes = path[:-1]
        turn = nodes.index(min(nodes))  # a cycle starts at its first id in id order, however it was found
        cycle = tuple(nodes[turn:] + nodes[:turn])
        if cycle in seen:
            continue
        seen.add(cycle)
        item = by_id[cycle[0]]
        stage = stage_of(plan.intent, item.path)
        loop = " -> ".join([*cycle, cycle[0]])
        message = f"the plan's dependencies form a cycle, {loop}: remove a `Depends:` line from it"
        directory = plan.intent.directory if stage else None
        found.append(Finding(item.path, item.line, "earnest/cycle", cycle[0], message, stage=stage, intent=directory))
    return found


def _owner(plans: Sequence[Plan], path: str) -> Plan | None:
    holders = [current for current in plans if inside(current.intent, path)]
    return max(holders, key=lambda current: len(current.intent.directory), default=None)


def _delivering(plans: Sequence[Plan], index: Index) -> dict[tuple[str, str], _Located]:
    """Map each delivered item's type and name to the plan and stage of the task that delivers it."""
    found: dict[tuple[str, str], _Located] = {}
    for link in index.links:
        if link.key != "Delivers" or link.owner is None or link.owner.type != "task":
            continue
        owner = _owner(plans, link.path)
        stage = stage_of(owner.intent, link.path) if owner is not None else None
        if owner is not None and stage is not None:
            found.setdefault(link.target.key, (owner, stage))
    return found


def _locate(
    finding: Finding,
    plans: Sequence[Plan],
    delivering: Mapping[tuple[str, str], _Located],
    stest_lines: set[tuple[str, int]],
) -> _Located | None:
    if finding.stage is not None:
        preset = next((current for current in plans if current.intent.directory == finding.intent), None)
        return None if preset is None else (preset, finding.stage)
    owner = _owner(plans, finding.path)
    return (
        _gap_stage(finding, owner)
        or (_stest_stage(plans) if (finding.path, finding.line) in stest_lines else None)
        or _file_stage(finding, owner)
        or _delivered_stage(finding, delivering)
    )


def _gap_stage(finding: Finding, owner: Plan | None) -> _Located | None:
    if finding.rule != "earnest/gap" or owner is None:
        return None
    wanted = (stage for stage in owner.intent.route if finding.child in PRODUCES.get(stage.partition("/")[2], ()))
    stage = next(wanted, None)
    return None if stage is None else (owner, stage)


def _stest_stage(plans: Sequence[Plan]) -> _Located | None:
    return next(
        (
            (current, stage)
            for current in plans
            for stage in current.intent.route
            if stage.endswith("/" + _BUILD_AND_TEST)
        ),
        None,
    )


def _file_stage(finding: Finding, owner: Plan | None) -> _Located | None:
    stage = None if owner is None else stage_of(owner.intent, finding.path)
    return None if owner is None or stage is None else (owner, stage)


def _delivered_stage(finding: Finding, delivering: Mapping[tuple[str, str], _Located]) -> _Located | None:
    named = _SUBJECT.fullmatch(finding.subject)
    return delivering.get((named[1], named[2])) if named else None


def _position(plan: Plan, stage: str) -> Position:
    if plan.frontier is None:
        return "behind"
    order = [state.stage for state in plan.stages]
    here, front = order.index(stage), order.index(plan.frontier)
    return "behind" if here < front else "current" if here == front else "ahead"
```

- [ ] **Step 3: Run the new tests and watch them pass**

Run: `uv run pytest tests/unit/test_plan.py --no-cov -q`

Expected: `111 passed`: the 67 tests the file held, plus the 44 new ones.

- [ ] **Step 4: Run the regression run and the linters**

```bash
uv run pytest --ignore=tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
make lint
```

Expected: `349 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/plan.py tests/unit/test_plan.py
git commit -m "feat: compute stage status, unplanned and cycle, and place findings by position"
```

### Task 11: The assessment hash, the body-hash baseline and `dirty`, `plan.py`

> Superseded in part by the final state in Task 13 (D17, S1–S7); these snippets are the historical TDD record.

**Files:**

- Modify: `packages/earnest/src/earnest/plan.py`
- Test: `packages/earnest/tests/unit/test_plan.py`

**Interfaces:**

- Consumes: `reporter.canonical`, `reporter.run_key`, `reporter.RunHeader`, `reporter.Run`, `reporter.uri` (Tasks 5-6); `index.digest`, `Item.body_hash` (Tasks 2-3); `adapters.reads` and `adapters.skipped` (Task 2); `Plan`, `Intent`, `in_tree`, `StageStatus`, `place` (Tasks 9-10).
- Produces: `evaluated_tree(sources, intents) -> list[Source]`, the sources for which `in_tree` holds. `tree_digest(tree) -> str`, the digest of the compact canonical JSON of the `[uri, digest]` pairs sorted by uri.
- Produces: `scoped(findings, plan, stage) -> list[Finding]`, what a `--stage` run reports: the findings whose `intent` and `stage` are the plan's intent directory and the stage, so equal stage ids of two intents never collide, and the findings that reach no stage.
- Produces: `assessment_document(plan, stage, tree, findings) -> dict[str, object]`, version 1: `v` 1; `stage`, the run key `<intent directory>/<stage id>`; `layers` `["trace"]`; null `model` and `prompt`; `items`, the stage's `[id, body hash]` pairs, sorted; `findings`, the scoped findings that lie in the tree, as `[rule, uri, line, subject, message]` sorted, position-free, with the approval notes left out because a fresh approval removes them and recording an approval must not move the hash; and `tree`, the tree digest. `assessment_hash(document) -> str`, the digest of its compact canonical JSON. Neither the commit, the timestamp, the route nor the approvals enter it.
- Produces: `next_bodies(held, plan, stage) -> dict[str, str]`, the baseline of RP3 and B-d: for each of the stage's items, keyed `type~name~revision`, it records the current hash when none is held, replaces it when no counting approval row of `plan.intent.named_items` names the key, and leaves it when one does. `frozen_bodies(held, intents) -> dict[str, str]`, the held hashes whose key some intent's `named_items` holds, which `structural.check` reads as `frozen`.
- Produces: `dirty(changes, intents) -> bool`, true when some changed path has a scanned suffix (`adapters.reads`), is not bookkeeping of a record directory (`adapters.skipped`, over the directories of all given intents), and lies in the evaluated tree (`in_tree`). A stage's `memory.md` diary write, the audit log and the state file leave the run clean.
- Produces: `header(plan, stage, status, run, digest) -> RunHeader`, five parameters: `commit`, `dirty` and `timestamp` come from `run`, `reasons` is `{"errors", "openTasks", "approval"}` from `status`, and `items` are the stage's ids, sorted.

- [ ] **Step 1: Write the failing tests**

In `packages/earnest/tests/unit/test_plan.py`, replace:

```python
from earnest import plan
from earnest.index import Id, Index, Item, Link
from earnest.plan import Approval, Event, Record, Row
from earnest.reporter import Finding
```

with:

```python
from earnest import plan
from earnest.index import MARKDOWN, Id, Index, Item, Link, Source
from earnest.index import digest as digest_of
from earnest.plan import Approval, Event, Record, Row
from earnest.reporter import Finding, Run
```

Append to the same file:

```python


def source(path, data="x"):
    return Source(path, MARKDOWN, (), digest=digest_of(data.encode()))


def hashed(text, body, stage=REQUIREMENTS, line=1):
    return Item(ident(text), f"r/{stage}/doc.md", line, None, body)


def document(built, stage, tree, findings):
    return plan.assessment_document(built, stage, tree, findings)


TREE = [source("src/a.py", "code")]


def test_evaluated_tree_is_the_sources_in_tree():
    paths = [
        "src/a.py",
        "r/aidlc-state.md",
        "r/audit/a.md",
        f"r/{REQUIREMENTS}/x.md",
        "r/inception/reverse-engineering/y.md",
    ]
    tree = plan.evaluated_tree([source(path) for path in paths], [intent_of(BASE)])
    assert [each.path for each in tree] == ["src/a.py", f"r/{REQUIREMENTS}/x.md"]


def test_tree_digest_changes_when_an_evaluated_file_changes():
    one, two = [source("a.py", "1")], [source("a.py", "2")]
    assert plan.tree_digest(one) != plan.tree_digest(two)
    assert plan.tree_digest(one) == plan.tree_digest([source("a.py", "1")])
    pair = [source("b.py", "1"), source("a.py", "1")]
    assert plan.tree_digest(pair) == plan.tree_digest(pair[::-1])  # sorted by uri
    assert plan.tree_digest([source("a b.py", "1")]) != plan.tree_digest([source("a%20b.py", "2")])


def test_tree_digest_ignores_a_state_or_audit_edit():
    intents = [intent_of(BASE)]
    base = [source("src/a.py"), source("r/aidlc-state.md", "one"), source("r/audit/a.md", "one")]
    edited = [source("src/a.py"), source("r/aidlc-state.md", "two"), source("r/audit/a.md", "two")]
    assert plan.tree_digest(plan.evaluated_tree(base, intents)) == plan.tree_digest(
        plan.evaluated_tree(edited, intents)
    )


def test_document_holds_position_free_findings():
    built, _ = planned(BASE, items=[hashed("req~b~1", "h2", line=8), hashed("req~a~1", "h1", line=3)])
    tree = [source(f"r/{REQUIREMENTS}/doc.md"), source("src/a.py")]
    found = Finding(f"r/{REQUIREMENTS}/doc.md", 8, "earnest/duplicate", "req~b~1", "m", stage=REQUIREMENTS, intent="r")
    shifted = Finding("src/a.py", 4, "earnest/orphaned", "req~z~1", "z", position="current")
    shown = document(built, REQUIREMENTS, tree, [found, shifted])
    assert shown == {
        "v": 1,
        "stage": f"r/{REQUIREMENTS}",
        "layers": ["trace"],
        "model": None,
        "prompt": None,
        "items": [["req~a~1", "h1"], ["req~b~1", "h2"]],
        "findings": [
            ["earnest/duplicate", f"r/{REQUIREMENTS}/doc.md", 8, "req~b~1", "m"],
            ["earnest/orphaned", "src/a.py", 4, "req~z~1", "z"],
        ],
        "tree": plan.tree_digest(tree),
    }
    moved = Finding(
        found.path, 8, found.rule, found.subject, found.message, stage=REQUIREMENTS, intent="r", position="ahead"
    )
    assert document(built, REQUIREMENTS, tree, [moved, shifted]) == shown  # the position takes no part


def test_findings_outside_the_tree_are_dropped_from_the_document():
    built, _ = planned(BASE, items=[hashed("req~a~1", "h1")])
    inside = Finding("src/a.py", 1, "earnest/orphaned", "req~z~1", "m")
    outside = Finding("r/aidlc-state.md", 17, "earnest/route-mismatch", "deployment-pipeline", "m")
    elsewhere = Finding(
        f"r/{CODE_GENERATION}/x.md", 1, "earnest/duplicate", "req~a~1", "m", stage=CODE_GENERATION, intent="r"
    )
    tree = [source("src/a.py"), source(f"r/{CODE_GENERATION}/x.md")]
    assert [entry[1] for entry in document(built, REQUIREMENTS, tree, [inside, outside, elsewhere])["findings"]] == [
        "src/a.py"
    ]


def test_document_leaves_out_approval_findings():
    built, _ = planned(BASE, items=[hashed("req~a~2", "h1"), hashed("req~b~1", "h2")])
    (note,) = plan.approval_findings(built)
    path = f"r/{REQUIREMENTS}/doc.md"
    tree = [source(path)]
    assert document(built, REQUIREMENTS, tree, [note]) == document(built, REQUIREMENTS, tree, [])


def test_recording_an_approval_leaves_the_hash_as_it_was():
    items = [hashed("req~a~1", "h1"), hashed("req~b~1", "h2"), hashed("task~t~1", "h3", CODE_GENERATION)]
    before, index = planned(BASE, items=items)
    after, _ = planned(BASE, gate("2026-09-26T12:00:00Z", stage="code-generation", Items="task~t~1"), items=items)
    assert (before.frontier, after.frontier) == (CODE_GENERATION, BUILD_AND_TEST)
    tree = [source("src/a.py")]
    one = plan.assessment_hash(
        document(before, CODE_GENERATION, tree, plan.place([before], index, plan.plan_findings(before, index)))
    )
    two = plan.assessment_hash(
        document(after, CODE_GENERATION, tree, plan.place([after], index, plan.plan_findings(after, index)))
    )
    assert one == two


def test_hash_is_stable_across_two_runs():
    built, _ = planned(BASE, items=[hashed("req~a~1", "h1"), hashed("req~b~1", "h2")])
    first = plan.assessment_hash(document(built, REQUIREMENTS, TREE, []))
    assert first == plan.assessment_hash(document(built, REQUIREMENTS, TREE, []))
    assert first.startswith("sha256:")
    assert len(first) == len("sha256:") + 64
    assert first != plan.assessment_hash(document(built, REQUIREMENTS, [source("src/a.py", "other")], []))


def test_hash_excludes_commit_and_timestamp():
    built, _ = planned(BASE, items=[hashed("req~a~1", "h1")])
    assert set(document(built, REQUIREMENTS, TREE, [])) == {
        "v",
        "stage",
        "layers",
        "model",
        "prompt",
        "items",
        "findings",
        "tree",
    }


def test_baseline_records_when_none_is_held():
    built, _ = planned(START, SKIPS, items=[hashed("req~a~1", "h1"), hashed("req~b~1", "h2")])
    assert plan.next_bodies({}, built, REQUIREMENTS) == {"req~a~1": "h1", "req~b~1": "h2"}


def test_baseline_replaces_until_a_counting_row_names_the_revision():
    built, _ = planned(START, SKIPS, items=[hashed("req~a~1", "new")])
    held = {"req~a~1": "old", "req~other~1": "kept"}
    assert plan.next_bodies(held, built, REQUIREMENTS) == {"req~a~1": "new", "req~other~1": "kept"}
    assert held["req~a~1"] == "old"  # the argument is not changed


def test_baseline_freezes_after_a_counting_row_names_it():
    built, _ = planned(BASE, items=[hashed("req~a~1", "new"), hashed("req~b~1", "new")])
    assert plan.next_bodies({"req~a~1": "old", "req~b~1": "old"}, built, REQUIREMENTS) == {
        "req~a~1": "old",
        "req~b~1": "old",
    }


def test_baseline_for_a_bumped_revision_starts_free():
    built, _ = planned(BASE, items=[hashed("req~a~2", "new"), hashed("req~b~1", "new")])
    result = plan.next_bodies({"req~a~1": "old", "req~b~1": "old"}, built, REQUIREMENTS)
    assert result == {"req~a~1": "old", "req~a~2": "new", "req~b~1": "old"}
    again = plan.next_bodies({**result, "req~a~2": "newer"}, built, REQUIREMENTS)
    assert again["req~a~2"] == "new"  # no row names revision 2 yet, so each run replaces it


def test_baseline_replaces_again_after_a_rejection_voids_the_row():
    rejected = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Feedback="Rework.")
    built, _ = planned(BASE, rejected, items=[hashed("req~a~1", "new"), hashed("req~b~1", "new")])
    assert plan.next_bodies({"req~a~1": "old", "req~b~1": "old"}, built, REQUIREMENTS) == {
        "req~a~1": "new",
        "req~b~1": "new",
    }


def test_baseline_records_when_a_named_revision_has_no_held_hash():
    built, _ = planned(BASE, items=[hashed("req~a~1", "new"), hashed("req~b~1", "new")])
    assert plan.next_bodies({"req~b~1": "old"}, built, REQUIREMENTS) == {"req~a~1": "new", "req~b~1": "old"}


def test_frozen_bodies_keeps_only_hashes_a_counting_row_names():
    held = {"req~a~1": "x", "req~c~1": "y", "req~z~1": "z"}
    other = intent_of(START, SKIPS, gate("2026-09-26T10:00:00Z", Items="req~z~1"), directory="s")
    assert plan.frozen_bodies(held, [intent_of(BASE)]) == {"req~a~1": "x"}
    assert plan.frozen_bodies(held, [intent_of(BASE), other]) == {"req~a~1": "x", "req~z~1": "z"}
    assert plan.frozen_bodies(held, []) == {}


def test_header_carries_the_fields_and_the_reasons_of_the_status():
    built, _ = planned(BASE, items=[hashed("req~b~1", "h2"), hashed("req~a~1", "h1")])
    status = plan.StageStatus("not done", 2, 1, "outdated")
    run = Run(commit="a" * 40, dirty=True, timestamp="2026-09-26T12:00:00Z")
    held = plan.header(built, REQUIREMENTS, status, run, "sha256:" + "1" * 64)
    assert (held.intent, held.stage, held.commit, held.dirty, held.timestamp) == (
        "r",
        REQUIREMENTS,
        "a" * 40,
        True,
        "2026-09-26T12:00:00Z",
    )
    assert (held.layers, held.model, held.prompt) == (("trace",), None, None)
    assert held.items == ("req~a~1", "req~b~1")
    assert (held.status, held.digest) == ("not done", "sha256:" + "1" * 64)
    assert dict(held.reasons) == {"errors": 2, "openTasks": 1, "approval": "outdated"}


def test_scoped_keeps_stage_and_stageless_findings():
    built, _ = planned(BASE)
    mine = found_in(REQUIREMENTS)
    other_stage = found_in(CODE_GENERATION)
    stageless = Finding("src/a.py", 1, "earnest/orphaned", "req~z~1", "m")
    assert plan.scoped([mine, other_stage, stageless], built, REQUIREMENTS) == [mine, stageless]


def test_scoped_separates_equal_stage_ids_of_two_intents():
    built, _ = planned(BASE)
    ours = found_in(REQUIREMENTS)
    theirs = Finding("s/x.md", 1, "earnest/gap", "req~a~1", "m", stage=REQUIREMENTS, intent="s")
    assert plan.scoped([ours, theirs], built, REQUIREMENTS) == [ours]
    assert [found.intent for found in plan.scoped([ours, theirs], built, REQUIREMENTS)] == ["r"]


def test_dirty_counts_an_edited_scanned_file():
    assert plan.dirty(["src/a.py"], [intent_of(BASE)])
    assert plan.dirty(["tests/a.feature"], [intent_of(BASE)])
    assert not plan.dirty([], [intent_of(BASE)])


def test_dirty_ignores_the_audit_log_and_state_file():
    paths = ["r/aidlc-state.md", "r/audit/a.md", "r/audit/fixture-0000aaaa.md", "r/.aidlc-engine/sensors/x.md"]
    assert not plan.dirty(paths, [intent_of(BASE)])


def test_dirty_counts_a_deleted_stage_artifact():
    assert plan.dirty([f"r/{REQUIREMENTS}/requirements.md"], [intent_of(BASE)])  # a missing file is a change too


def test_dirty_ignores_an_unscanned_suffix():
    paths = ["data.json", "notes.txt", "Makefile", f"r/{REQUIREMENTS}/diagram.png"]
    assert not plan.dirty(paths, [intent_of(BASE)])


def test_dirty_counts_a_scratch_markdown_file():
    assert plan.dirty(["notes.md"], [intent_of(BASE)])
    assert plan.dirty(["r/scratch.md"], [intent_of(BASE)]) is False  # inside the record directory, in no route stage


def test_dirty_counts_a_deleted_tracked_markdown_file_outside_every_intent():
    assert plan.dirty(["docs/old.md"], [])
    assert plan.dirty(["docs/old.md"], [intent_of(BASE)])


def test_dirty_ignores_a_stage_diary_memory_md():
    memory = f"r/{REQUIREMENTS}/memory.md"
    assert not plan.dirty([memory], [intent_of(BASE)])
    assert plan.dirty([memory, f"r/{REQUIREMENTS}/requirements.md"], [intent_of(BASE)])


def test_dirty_ignores_the_files_of_an_unsupported_intent_that_ai_dlc_writes():
    state = FULL_STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")
    unsupported = intent_of(BASE, state=state, directory="u")
    assert not plan.dirty(["u/aidlc-state.md", "u/audit/a.md", "u/.aidlc-engine/x.md"], [unsupported])
    assert plan.dirty(["u/inception/requirements-analysis/r.md"], [unsupported])
```

Run: `uv run pytest tests/unit/test_plan.py --no-cov -q`

Expected: `27 failed, 111 passed`: each new test fails with `AttributeError` (`module 'earnest.plan' has no attribute 'evaluated_tree'` and the like), and the 111 tests the file held pass.

- [ ] **Step 2: Add the assessment hash, the baseline and `dirty`**

In `packages/earnest/src/earnest/plan.py`, replace:

```python
from earnest import structural
from earnest.index import TYPES, Index, Item, split_lines
from earnest.reporter import Finding, Position
```

with:

```python
from earnest import adapters, structural
from earnest.index import TYPES, Index, Item, Source, split_lines
from earnest.index import digest as digest_of
from earnest.reporter import Finding, Position, Run, RunHeader, canonical, run_key, uri
```

At the end of `packages/earnest/src/earnest/plan.py`, append:

```python


def evaluated_tree(sources: Sequence[Source], intents: Sequence[Intent]) -> list[Source]:
    """Return the sources in the evaluated tree: outside every record directory, or in a route stage."""
    return [each for each in sources if in_tree(intents, each.path)]


def tree_digest(tree: Sequence[Source]) -> str:
    """Return the digest of the tree: the canonical JSON of each file's uri and digest, sorted by uri."""
    return digest_of(canonical(sorted([uri(each.path), each.digest] for each in tree)).encode("ascii"))


def scoped(findings: Sequence[Finding], plan: Plan, stage: str) -> list[Finding]:
    """Return what a `--stage` run reports: the stage's findings, and the findings that reach no stage."""
    return [
        found
        for found in findings
        if found.stage is None or (found.intent == plan.intent.directory and found.stage == stage)
    ]


def assessment_document(
    plan: Plan, stage: str, tree: Sequence[Source], findings: Sequence[Finding]
) -> dict[str, object]:
    """Return the assessment document that the assessment hash covers, version 1.

    It holds the stage's items with their body hashes, the findings of the run that lie in the evaluated tree, as
    their rule, uri, line, subject and message, and the tree's digest. It holds no position, commit, timestamp, route
    or approval, and no approval note, which a fresh approval removes.
    """
    state = next(each for each in plan.stages if each.stage == stage)
    inside = {each.path for each in tree}
    counted = [found for found in scoped(findings, plan, stage) if not found.note and found.path in inside]
    return {
        "v": 1,
        "stage": run_key(plan.intent.directory, stage),
        "layers": ["trace"],
        "model": None,
        "prompt": None,
        "items": sorted([str(item.id), item.body_hash] for item in state.items),
        "findings": sorted(
            [found.rule, uri(found.path), found.line, found.subject, found.message] for found in counted
        ),
        "tree": tree_digest(tree),
    }


def assessment_hash(document: Mapping[str, object]) -> str:
    """Return the assessment hash: the digest of the document's compact canonical JSON."""
    return digest_of(canonical(document).encode("ascii"))


def next_bodies(held: Mapping[str, str], plan: Plan, stage: str) -> dict[str, str]:
    """Return the body hashes the record holds after a stage check.

    An item's hash is recorded when none is held, and replaced on each run until a counting approval row names the
    item's id with its revision; from then on it stays, and any later difference raises `unbumped-change`.
    """
    # ponytail: an entry for a revision that no longer exists is never pruned; prune by the index if the record grows
    bodies = dict(held)
    for item in next(each for each in plan.stages if each.stage == stage).items:
        key = str(item.id)
        if key not in bodies or key not in plan.intent.named_items:
            bodies[key] = item.body_hash
    return bodies


def frozen_bodies(held: Mapping[str, str], intents: Sequence[Intent]) -> dict[str, str]:
    """Return the held hashes that a counting approval row froze, for `structural.check` to compare with."""
    return {key: value for key, value in held.items() if any(key in current.named_items for current in intents)}


def dirty(changes: Sequence[str], intents: Sequence[Intent]) -> bool:
    """Return whether a changed path lies in the evaluated tree: a scanned suffix, outside AI-DLC's bookkeeping."""
    directories = {current.directory for current in intents}
    return any(
        adapters.reads(path) and not adapters.skipped(path, directories) and in_tree(intents, path) for path in changes
    )


def header(plan: Plan, stage: str, status: StageStatus, run: Run, digest: str) -> RunHeader:
    """Return the run header of a stage check: the run's commit, `dirty` and time, the status, its reasons and the hash."""
    state = next(each for each in plan.stages if each.stage == stage)
    return RunHeader(
        intent=plan.intent.directory,
        stage=stage,
        commit=run.commit,
        dirty=run.dirty,
        timestamp=run.timestamp,
        layers=("trace",),
        model=None,
        prompt=None,
        items=tuple(sorted(str(item.id) for item in state.items)),
        status=status.status,
        reasons={"errors": status.errors, "openTasks": status.open_tasks, "approval": status.approval},
        digest=digest,
    )
```

- [ ] **Step 3: Run the new tests and watch them pass**

Run: `uv run pytest tests/unit/test_plan.py --no-cov -q`

Expected: `138 passed`: the 111 tests the file held, plus the 27 new ones.

- [ ] **Step 4: Run the regression run and the linters**

```bash
uv run pytest --ignore=tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
make lint
```

Expected: `376 passed`, then `make lint` exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/earnest/plan.py tests/unit/test_plan.py
git commit -m "feat: hash the stage assessment, keep the body-hash baseline and decide dirty"
```

### Task 12: `earnest plan`, `earnest check --stage` and `--intent`, `cli.py`

> Superseded in part by the final state in Task 13 (D17, S1–S7); these snippets are the historical TDD record.

**Files:**

- Modify: `packages/earnest/src/earnest/cli.py`, `packages/earnest/src/earnest/plan.py` (the two selection functions)
- Modify: `packages/earnest/tests/steps/test_stage_status.py` (step fixes the integration surfaces)
- Test: `packages/earnest/tests/unit/test_cli.py`, `packages/earnest/tests/unit/test_plan.py`, `packages/earnest/tests/integration/test_stage.py`

**Interfaces:**

- Consumes: `git.changes`, `git.work_tree_files` (Task 4); `reporter.read_record`, `write_record`, `RecordError`, `run_key`, `utc_timestamp`, `Run`, `sarif`, `summary` (Tasks 5-6); `structural.check` with `produces` and `frozen`, `structural.traced` (Task 7); `plan.load`, `intent`, `build`, `produces`, `place`, `plan_findings`, `approval_findings`, `statuses`, `properties`, `evaluated_tree`, `assessment_document`, `assessment_hash`, `scoped`, `next_bodies`, `frozen_bodies`, `dirty`, `header` (Tasks 8-11); `fixture_repo`, `commit_overlay`, `run_earnest` (Task 1).
- Produces, in `plan.py`: `UNSUPPORTED_ROUTE`, the message `unsupported route: units-generation is on the route, so per-unit stages`; `class PlanError(Exception)`; `find_intent(intents, option) -> Intent`: with an option, the intent whose directory equals it, else a `PlanError` naming the record directories; without one, the only intent, else a `PlanError` that says none holds an `aidlc-state.md`, or lists the several and asks for `--intent`. `select_intent(intents, option) -> Intent` does the same and raises `PlanError(UNSUPPORTED_ROUTE)` for an intent with per-unit stages. `select_stage(plan, text) -> str`: the stage id when `text` is one, else the stage whose slug is `text` when exactly one is, else a `PlanError` that names the route's stages (the text is not a stage on the route, or names several).
- Produces, in `cli.py`: `main(argv)` with `earnest check [--stage <id>] [--intent <dir>]` and `earnest plan`. Every command reads the record (a missing file is an empty record), the state files and shards (`plan.load`), the scan and `git.changes`. `--intent` is the record directory relative to the repository root or, if that names no record directory, a path relative to the working directory that resolves to one; the root-relative reading wins when both do. The shared path is `scan`, `build_index`, the intents, `structural.check(produces, frozen_bodies)`, then `plan_findings + approval_findings`, then `place`. The plan covers the supported intents only, and `produces` is `plan.produces(intents)`, which is `None` when no supported intent exists, so M1's findings on `broken-links`, and on a repository whose only intent is unsupported, are untouched. The tree functions (`evaluated_tree`, `in_tree`, `dirty`) receive every record directory. Intents come in directory order, in `properties.plan` too.
- Produces: all three commands carry `properties.plan` when a record directory exists: `{"intents": [...]}` for the supported intents, and `{"intents": []}` when none is supported. It is absent when there is no record directory.
- Produces: a state file whose Stage Progress Earnest cannot read in part or whole reaches every command as the error-level `route-mismatch` findings of Task 9, so `plan`, `check` and `check --stage` exit 1 and the gate is held; `produces` is `None` for a route that emptied, so M1's findings stay. A stage that an unreadable row dropped is no longer on the route, so `check --stage` naming it exits 2.
- Produces: `plan` prints the SARIF log on stdout (`plan_findings + approval_findings` as its results, PD4) and, on stderr, the summary, which lists each intent's stages with status and approval, the frontier, and each task with its status. It writes nothing and exits by the usual rule over its findings. With no record directory it says `no plan` on stderr and exits 0. With a single record directory that has per-unit stages it exits 2 with the unsupported-route line and empty stdout. With several it reports the supported ones and writes one `earnest: skipped <dir>: unsupported route` line per unsupported intent to stderr; when all are unsupported it exits 0 with only those lines.
- Produces: `check` prints the full log and exits as before, with positions and `dirty`; an unsupported intent's findings stay stage-less at position current. `check --intent <dir>` without `--stage` validates the directory (a missing one exits 2) and changes nothing else.
- Produces: `check --stage S` first selects the intent and the stage (a `PlanError` exits 2 before anything is written), scopes the findings, computes the hash from the scoped findings and `dirty`, updates `bodies` by `next_bodies`, writes the stage's run header under `run_key(intent directory, stage)`, and only then prints the SARIF log, with `properties.assessment` (`stage`, `hash`, `status`, `reasons`), and the summary. Its exit code follows the scoped findings (PD9 e): those counting against the stage and those that reach no stage, at error level. A failed write exits 2 with empty stdout.
- Produces: the summary states `record: absent, body-hash baseline unavailable` when the record file is missing and the index holds items (PD7); and, whenever the record file exists, `body-hash baseline: <n> items without a held hash` when `n > 0`: `plan` and plain `check` count the indexed items of the supported intents that have no entry in `bodies` for their id and revision, and `check --stage` counts the stage's items that held none before the run.
- Produces: `(git.GitError, OSError, reporter.RecordError, plan.PlanError)` form the read-phase boundary and print one `earnest:` line and exit 2 (R34-2). Output is written outside that boundary, so a reader that goes away still exits 2 quietly.

- [ ] **Step 1: Write the failing tests**

Append to `packages/earnest/tests/unit/test_plan.py`:

```python


UNSUPPORTED_STATE = FULL_STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")


def test_select_intent_by_directory_option():
    one, two = intent_of(BASE, directory="a"), intent_of(BASE, directory="b")
    assert plan.select_intent([one, two], "b") is two
    assert plan.select_intent([one, two], "a") is one


def test_select_intent_single_record_without_the_option():
    only = intent_of(BASE, directory="a")
    assert plan.select_intent([only], None) is only


def test_select_intent_with_several_records_and_no_option_lists_them():
    with pytest.raises(plan.PlanError, match=r"--intent.*a.*b"):
        plan.select_intent([intent_of(BASE, directory="a"), intent_of(BASE, directory="b")], None)


def test_select_intent_with_no_record_raises():
    with pytest.raises(plan.PlanError, match=r"no record directory holds an aidlc-state\.md"):
        plan.select_intent([], None)


def test_select_intent_unknown_directory_names_the_candidates():
    with pytest.raises(plan.PlanError, match=r"zzz.*a, b"):
        plan.select_intent([intent_of(BASE, directory="a"), intent_of(BASE, directory="b")], "zzz")


def test_select_intent_unsupported_raises_the_unsupported_route_error():
    unsupported = intent_of(BASE, state=UNSUPPORTED_STATE, directory="u")
    with pytest.raises(plan.PlanError) as error:
        plan.select_intent([unsupported], None)
    assert str(error.value) == "unsupported route: units-generation is on the route, so per-unit stages"
    assert plan.find_intent([unsupported], "u") is unsupported  # finding it is no refusal; selecting it is


def test_select_stage_by_phase_slash_slug():
    built, _ = planned(BASE)
    assert plan.select_stage(built, CODE_GENERATION) == CODE_GENERATION


def test_select_stage_by_unique_bare_slug():
    built, _ = planned(BASE)
    assert plan.select_stage(built, "code-generation") == CODE_GENERATION
    assert plan.select_stage(built, "requirements-analysis") == REQUIREMENTS


def test_select_stage_rejects_an_unknown_slug():
    built, _ = planned(BASE)
    with pytest.raises(plan.PlanError, match=r"no-such is not a stage on the route: .*requirements-analysis"):
        plan.select_stage(built, "no-such")
    with pytest.raises(plan.PlanError, match="not a stage on the route"):
        plan.select_stage(built, "inception/units-generation")  # a SKIP row is not on the route


def test_select_stage_names_the_state_file_when_an_unreadable_stage_progress_emptied_the_route():
    built, _ = planned(BASE, state=FULL_STATE.replace("## Stage Progress", "## Stage  Progress"))
    with pytest.raises(plan.PlanError) as error:
        plan.select_stage(built, "requirements-analysis")
    assert str(error.value) == (
        "requirements-analysis is not a stage on the route: the state file's Stage Progress cannot be read"
        " (r/aidlc-state.md:1)"
    )
    empty, _ = planned(START, state="## Stage Progress\n### INCEPTION PHASE\n" + f"- [x] a {DASH} SKIP\n")
    with pytest.raises(plan.PlanError, match=r"route: none$"):  # an empty route that reads fine says so plainly
        plan.select_stage(empty, "a")


def test_select_stage_rejects_an_ambiguous_bare_slug():
    state = FULL_STATE.replace(f"- [x] build-and-test {DASH}", f"- [x] requirements-analysis {DASH}")
    built, _ = planned(BASE, state=state)
    with pytest.raises(plan.PlanError, match=r"names several stages.*inception/requirements-analysis.*construction/"):
        plan.select_stage(built, "requirements-analysis")
    assert plan.select_stage(built, "inception/requirements-analysis") == "inception/requirements-analysis"
```

In the same file, replace:

```python
from earnest import plan
from earnest.index import MARKDOWN, Id, Index, Item, Link, Source
```

with:

```python
import pytest

from earnest import plan
from earnest.index import MARKDOWN, Id, Index, Item, Link, Source
```

In `packages/earnest/tests/unit/test_cli.py`, replace:

```python
import subprocess
import sys

import pytest

from earnest import cli
```

with:

```python
import json
import subprocess
import sys

import pytest

from earnest import cli
from tests.sarif import located, sarif_run
```

Append to the same file:

```python


DASH = "\u2014"
RECORD = "aidlc/spaces/default/intents/260926-checkout"
PLAN_FILE = f"{RECORD}/construction/code-generation/code-generation-plan.md"
UNSUPPORTED = "earnest: unsupported route: units-generation is on the route, so per-unit stages\n"
STATE = f"""## Stage Progress
### INCEPTION PHASE
- [S] units-generation {DASH} SKIP: not in scope
- [x] requirements-analysis {DASH} EXECUTE: always
### CONSTRUCTION PHASE
- [x] code-generation {DASH} EXECUTE: always
"""
UNITS = STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")


def run(repo, monkeypatch, capsys, *args):
    monkeypatch.chdir(repo)
    code = cli.main(list(args))
    out, err = capsys.readouterr()
    return code, out, err


def put(repo, path, text):
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text, encoding="utf-8")


def test_stage_with_no_record_directory_exits_two(files_repo, monkeypatch, capsys):
    code, out, err = run(files_repo({"docs/a.md": "# A\n"}), monkeypatch, capsys, "check", "--stage", "code-generation")
    assert (code, out) == (2, "")
    assert err.startswith("earnest: ")
    assert len(err.splitlines()) == 1


def test_unknown_stage_exits_two_with_one_line(fixture_repo, monkeypatch, capsys):
    code, out, err = run(fixture_repo("seeded-change"), monkeypatch, capsys, "check", "--stage", "no-such-stage")
    assert (code, out) == (2, "")
    assert len(err.splitlines()) == 1
    assert "no-such-stage" in err


def test_ambiguous_bare_slug_exits_two_and_lists_the_stages(files_repo, monkeypatch, capsys):
    state = STATE.replace("code-generation", "requirements-analysis")
    repo = files_repo({"i/aidlc-state.md": state})
    code, out, err = run(repo, monkeypatch, capsys, "check", "--stage", "requirements-analysis")
    assert (code, out) == (2, "")
    assert "inception/requirements-analysis" in err
    assert "construction/requirements-analysis" in err


def test_several_records_without_intent_exits_two_and_lists_them(files_repo, monkeypatch, capsys):
    repo = files_repo({"a/aidlc-state.md": STATE, "b/aidlc-state.md": STATE})
    code, out, err = run(repo, monkeypatch, capsys, "check", "--stage", "requirements-analysis")
    assert (code, out) == (2, "")
    assert "--intent" in err
    assert "a, b" in err


def test_intent_option_names_a_missing_record_exits_two(fixture_repo, monkeypatch, capsys):
    code, out, err = run(fixture_repo("seeded-change"), monkeypatch, capsys, "check", "--intent", "no/such/dir")
    assert (code, out) == (2, "")
    assert "no/such/dir" in err
    assert len(err.splitlines()) == 1


def test_corrupt_record_exits_two_with_empty_stdout(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    put(repo, ".earnest/assessment.json", "{not json")
    for command in (["plan"], ["check"], ["check", "--stage", "construction/code-generation"]):
        code, out, err = run(repo, monkeypatch, capsys, *command)
        assert (code, out) == (2, "")
        assert ".earnest/assessment.json" in err


def test_stage_status_sets_no_exit_code(fixture_repo, monkeypatch, capsys):
    code, out, _ = run(
        fixture_repo("seeded-change"), monkeypatch, capsys, "check", "--stage", "construction/code-generation"
    )
    assert code == 0
    assert sarif_run(out)["properties"]["assessment"]["status"] == "not done"


def test_stage_exit_code_follows_the_scoped_findings(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    lines = (repo / PLAN_FILE).read_text(encoding="utf-8").split("\n")
    lines[7] = "Depends: task~notify-lockout~1"  # a cycle, in the code generation stage
    put(repo, PLAN_FILE, "\n".join(lines))
    assert run(repo, monkeypatch, capsys, "check", "--stage", "inception/requirements-analysis")[0] == 0
    assert run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation")[0] == 1


def test_plan_without_a_record_directory_says_no_plan_and_exits_zero(files_repo, monkeypatch, capsys):
    code, out, err = run(files_repo({"docs/a.md": "# A\n"}), monkeypatch, capsys, "plan")
    assert code == 0
    assert "no plan" in err.splitlines()
    assert "plan" not in sarif_run(out)["properties"]


def test_plan_of_an_only_unsupported_intent_exits_two_with_empty_stdout(files_repo, monkeypatch, capsys):
    code, out, err = run(files_repo({"i/aidlc-state.md": UNITS}), monkeypatch, capsys, "plan")
    assert (code, out, err) == (2, "", UNSUPPORTED)


def test_check_stage_of_an_unsupported_intent_exits_two_and_writes_nothing(files_repo, monkeypatch, capsys):
    repo = files_repo({"i/aidlc-state.md": UNITS})
    code, out, err = run(repo, monkeypatch, capsys, "check", "--stage", "inception/requirements-analysis")
    assert (code, out, err) == (2, "", UNSUPPORTED)
    assert not (repo / ".earnest").exists()


def test_plain_check_places_an_unsupported_intents_findings_without_a_plan(files_repo, monkeypatch, capsys):
    repo = files_repo({"i/aidlc-state.md": UNITS, "i/inception/requirements-analysis/r.md": "`req~a~1`\n\nBody.\n"})
    code, out, _ = run(repo, monkeypatch, capsys, "check")
    assert code == 1
    results = sarif_run(out)["results"]
    assert results
    for result in results:
        assert result["properties"]["position"] == "current"
        assert "stage" not in result["properties"]
        assert result["message"]["text"].startswith("in scope: ")


def test_plan_lists_the_supported_intents_when_another_is_unsupported(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    other = "aidlc/spaces/default/intents/260927-other"
    put(repo, f"{other}/aidlc-state.md", UNITS)
    code, out, err = run(repo, monkeypatch, capsys, "plan")
    assert code == 0
    assert [entry["intent"] for entry in sarif_run(out)["properties"]["plan"]["intents"]] == [RECORD]
    assert f"earnest: skipped {other}: unsupported route" in err.splitlines()


def test_intent_option_without_stage_is_validated_and_changes_nothing_else(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    plain = run(repo, monkeypatch, capsys, "check")
    named = run(repo, monkeypatch, capsys, "check", "--intent", RECORD)
    assert named == plain
    assert not (repo / ".earnest").exists()


def test_intent_option_root_relative_wins_over_the_working_directory_form(files_repo, monkeypatch, capsys):
    repo = files_repo({"a/aidlc-state.md": STATE, "sub/a/aidlc-state.md": STATE, "sub/b/aidlc-state.md": STATE})
    stage = "inception/requirements-analysis"
    monkeypatch.chdir(repo / "sub")
    for name in ("a", "b"):
        assert cli.main(["check", "--stage", stage, "--intent", name]) == 0
        capsys.readouterr()
    runs = json.loads((repo / ".earnest" / "assessment.json").read_text(encoding="utf-8"))["runs"]
    assert sorted(runs) == [f"a/{stage}", f"sub/b/{stage}"]  # `a` exists at the root, `b` only below `sub`


def test_plan_of_several_intents_all_unsupported_exits_zero_with_skip_lines(files_repo, monkeypatch, capsys):
    repo = files_repo({"a/aidlc-state.md": UNITS, "b/aidlc-state.md": UNITS})
    code, out, err = run(repo, monkeypatch, capsys, "plan")
    assert code == 0
    assert sarif_run(out)["properties"]["plan"] == {"intents": []}
    assert [line for line in err.splitlines() if line.startswith("earnest:")] == [
        "earnest: skipped a: unsupported route",
        "earnest: skipped b: unsupported route",
    ]


def test_an_unreadable_stage_progress_row_fails_every_command(files_repo, monkeypatch, capsys):
    state = STATE.replace(f"- [x] code-generation {DASH} EXECUTE", "- [x] code-generation -- EXECUTE")
    repo = files_repo({"i/aidlc-state.md": state})
    for command in (["plan"], ["check"], ["check", "--stage", "inception/requirements-analysis"]):
        code, out, _ = run(repo, monkeypatch, capsys, *command)
        assert code == 1, command
        (found,) = [r for r in sarif_run(out)["results"] if r["ruleId"] == "earnest/route-mismatch"]
        assert (found["level"], "stage" in found["properties"]) == ("error", False)
        assert "Earnest cannot read line 6 of the state file" in found["message"]["text"]
    code, out, err = run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation")
    assert (code, out) == (2, "")  # the row that cannot be read dropped the stage from the route
    assert "not a stage on the route" in err


def test_a_renamed_stage_progress_heading_is_a_finding_not_a_silent_pass(files_repo, monkeypatch, capsys):
    state = STATE.replace("## Stage Progress", "## Stage  Progress")
    repo = files_repo({"i/aidlc-state.md": state, "docs/a.md": "`req~a~1`\n\nBody.\n"})
    code, out, err = run(repo, monkeypatch, capsys, "check")
    assert code == 1
    results = sarif_run(out)["results"]
    assert {result["ruleId"] for result in results} == {"earnest/route-mismatch", "earnest/orphaned", "earnest/gap"}
    assert err.splitlines()[0].startswith("traced 0%")  # the needs survive an emptied route, so no silent 100%
    (found,) = [result for result in results if result["ruleId"] == "earnest/route-mismatch"]
    assert located(found) == ("i/aidlc-state.md", 1)
    assert run(repo, monkeypatch, capsys, "plan")[0] == 1


def test_plain_check_of_an_unsupported_only_repository_keeps_the_m1_findings(files_repo, monkeypatch, capsys):
    repo = files_repo({"i/aidlc-state.md": UNITS, "docs/a.md": "`req~a~1`\n\nBody.\n"})
    code, out, _ = run(repo, monkeypatch, capsys, "check")
    assert code == 1
    log = sarif_run(out)
    assert {result["ruleId"] for result in log["results"]} == {"earnest/orphaned", "earnest/gap"}
    assert log["properties"]["plan"] == {"intents": []}
```

Create `packages/earnest/tests/integration/test_stage.py`:

```python
"""Integration: `earnest plan` and `earnest check --stage` over the seeded-change repository, through the script."""

import json
import os
import re

import pytest

from earnest import cli, reporter
from tests.sarif import git_output, located, run_earnest, sarif_run


RECORD = "aidlc/spaces/default/intents/260926-checkout"
SHARD = f"{RECORD}/audit/fixture-a1b2c3d4.md"
REQUIREMENTS = f"{RECORD}/inception/requirements-analysis/requirements.md"
PLAN_FILE = f"{RECORD}/construction/code-generation/code-generation-plan.md"
REQ_STAGE = "inception/requirements-analysis"
CODE_STAGE = "construction/code-generation"
HASH = re.compile(r"^assessment \S+: (sha256:[0-9a-f]{64}) \((?:done|not done)\)$", re.MULTILINE)


def record_of(repo):
    return json.loads((repo / ".earnest" / "assessment.json").read_text(encoding="utf-8"))


def edit(repo, path, old, new):
    text = (repo / path).read_text(encoding="utf-8")
    assert old in text
    (repo / path).write_text(text.replace(old, new), encoding="utf-8")


def stage_check(repo, stage):
    done = run_earnest(repo, "check", "--stage", stage)
    assert done.returncode in {0, 1}, done.stderr
    return done


def table(done):
    return sorted(
        (
            r["ruleId"],
            located(r)[0],
            located(r)[1],
            r["level"],
            r["properties"]["position"],
            r["properties"].get("stage"),
        )
        for r in sarif_run(done.stdout)["results"]
    )


def test_plan_is_read_only_and_prints_the_route(fixture_repo):
    repo = fixture_repo("seeded-change")
    done = run_earnest(repo, "plan")
    assert done.returncode == 0, done.stderr
    entry = sarif_run(done.stdout)["properties"]["plan"]["intents"][0]
    assert [(s["stage"], s["status"], s["approval"], s["approvedBy"]) for s in entry["stages"]] == [
        (REQ_STAGE, "done", "current", "human"),
        (CODE_STAGE, "not done", "none", None),
        ("construction/build-and-test", "not done", "none", None),
    ]
    assert entry["frontier"] == CODE_STAGE
    assert git_output(repo, "status", "--porcelain", "--untracked-files=all") == ""
    assert not (repo / ".earnest").exists()


def test_plan_stderr_lists_the_tasks(fixture_repo):
    lines = run_earnest(fixture_repo("seeded-change"), "plan").stderr.splitlines()
    assert f"intent {RECORD}" in lines
    assert "  task task~add-limiter~1: not done" in lines
    assert "  task task~notify-lockout~1: not done" in lines
    assert f"  frontier: {CODE_STAGE}" in lines


def test_plan_properties_are_an_intents_list(fixture_repo):
    props = sarif_run(run_earnest(fixture_repo("seeded-change"), "plan").stdout)["properties"]
    assert set(props["plan"]) == {"intents"}
    (entry,) = props["plan"]["intents"]
    assert set(entry) == {"intent", "stages", "frontier", "tasks", "units"}
    assert (entry["intent"], entry["units"]) == (RECORD, [])
    assert [task["id"] for task in entry["tasks"]] == ["task~add-limiter~1", "task~notify-lockout~1"]


def test_check_carries_properties_plan(fixture_repo):
    repo = fixture_repo("seeded-change")
    plain = sarif_run(run_earnest(repo, "check").stdout)["properties"]
    staged = sarif_run(stage_check(repo, CODE_STAGE).stdout)["properties"]
    assert plain["plan"]["intents"][0]["frontier"] == staged["plan"]["intents"][0]["frontier"] == CODE_STAGE
    assert "assessment" not in plain
    assert set(staged["assessment"]) == {"stage", "hash", "status", "reasons"}


def test_check_stage_writes_the_header_and_the_marker(fixture_repo):
    repo = fixture_repo("seeded-change")
    done = stage_check(repo, CODE_STAGE)
    assert (repo / ".earnest" / ".gitignore").read_text(encoding="utf-8") == "*\n"
    held = record_of(repo)["runs"][f"{RECORD}/{CODE_STAGE}"]
    assert held["commit"] == git_output(repo, "rev-parse", "HEAD").strip()
    assert (held["dirty"], held["layers"], held["status"]) == (False, ["trace"], "not done")
    assert held["items"] == ["task~add-limiter~1", "task~notify-lockout~1"]
    assert held["reasons"] == {"errors": 0, "openTasks": 2, "approval": "none"}
    assert held["hash"] == HASH.search(done.stderr).group(1)
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", held["timestamp"])


def test_runs_are_keyed_by_intent_directory_and_stage(fixture_repo):
    repo = fixture_repo("seeded-change")
    stage_check(repo, CODE_STAGE)
    stage_check(repo, REQ_STAGE)
    assert sorted(record_of(repo)["runs"]) == [f"{RECORD}/{CODE_STAGE}", f"{RECORD}/{REQ_STAGE}"]


def test_two_stage_checks_print_the_same_hash_and_log(fixture_repo):
    repo = fixture_repo("seeded-change")
    first, second = stage_check(repo, CODE_STAGE), stage_check(repo, CODE_STAGE)
    assert HASH.search(first.stderr).group(1) == HASH.search(second.stderr).group(1)
    assert first.stdout == second.stdout


def test_a_failed_record_write_exits_two_with_empty_stdout(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")

    def refuse(root, record):
        message = "disk full"
        raise OSError(message)

    monkeypatch.setattr(reporter, "write_record", refuse)
    monkeypatch.chdir(repo)
    assert cli.main(["check", "--stage", CODE_STAGE]) == 2
    assert capsys.readouterr() == ("", "earnest: disk full\n")
    assert not (repo / ".earnest").exists()


def test_check_without_stage_writes_nothing_and_says_the_record_is_absent(fixture_repo):
    repo = fixture_repo("seeded-change")
    done = run_earnest(repo, "check")
    assert not (repo / ".earnest").exists()
    assert "record: absent, body-hash baseline unavailable" in done.stderr.splitlines()
    assert git_output(repo, "status", "--porcelain", "--untracked-files=all") == ""


def test_broken_links_output_is_unchanged_except_dirty_and_the_record_absent_line(fixture_repo):
    done = run_earnest(fixture_repo("broken-links"), "check")
    assert done.returncode == 1
    log = sarif_run(done.stdout)
    assert set(log["properties"]) == {"traceLevels", "percentages"}
    assert log["invocations"][0]["properties"] == {
        "commit": log["invocations"][0]["properties"]["commit"],
        "dirty": False,
        "layers": ["trace"],
    }
    for result in log["results"]:
        assert result["properties"]["position"] == "current"
        assert "stage" not in result["properties"]
        assert result["message"]["text"].startswith("in scope: ")
    lines = done.stderr.splitlines()
    assert lines[0].startswith("traced ")
    assert lines[1] == "record: absent, body-hash baseline unavailable"
    assert lines[2].startswith("  req~")


def test_audit_row_leaves_hash_and_dirty_unchanged(fixture_repo):
    repo = fixture_repo("seeded-change")
    first = stage_check(repo, CODE_STAGE)
    shard = repo / SHARD
    block = "## Gate Approved\n**Timestamp**: 2026-09-26T12:00:00Z\n**Event**: GATE_APPROVED\n"
    shard.write_text(
        shard.read_text(encoding="utf-8") + block + "**Stage**: code-generation\n**Items**: task~add-limiter~1\n---\n",
        encoding="utf-8",
    )
    second = stage_check(repo, CODE_STAGE)
    assert HASH.search(first.stderr).group(1) == HASH.search(second.stderr).group(1)
    assert record_of(repo)["runs"][f"{RECORD}/{CODE_STAGE}"]["dirty"] is False


def test_plain_check_raises_no_unbumped_change_on_a_hash_no_row_names(fixture_repo):
    repo = fixture_repo("seeded-change")
    stage_check(repo, CODE_STAGE)
    edit(repo, PLAN_FILE, "Tell the member when the lockout starts.", "Tell the member when it starts.")
    rules = {result["ruleId"] for result in sarif_run(run_earnest(repo, "check").stdout)["results"]}
    assert "earnest/unbumped-change" not in rules


def test_stage_check_before_the_approval_replaces_the_held_hash(fixture_repo):
    repo = fixture_repo("seeded-change")
    stage_check(repo, CODE_STAGE)
    before = record_of(repo)["bodies"]["task~notify-lockout~1"]
    edit(repo, PLAN_FILE, "Tell the member when the lockout starts.", "Tell the member when it starts.")
    stage_check(repo, CODE_STAGE)
    assert record_of(repo)["bodies"]["task~notify-lockout~1"] != before


def test_overlay_findings_match_the_scenario_table(fixture_repo, commit_overlay):
    repo = fixture_repo("seeded-change")
    stage_check(repo, REQ_STAGE)
    commit_overlay(repo, "seeded-change", "task/add-limiter-window")
    done = run_earnest(repo, "check")
    assert done.returncode == 1
    assert table(done) == sorted(
        [
            ("earnest/unbumped-change", REQUIREMENTS, 8, "error", "current", REQ_STAGE),
            ("earnest/outdated", REQUIREMENTS, 3, "note", "current", REQ_STAGE),
            ("earnest/outdated", PLAN_FILE, 7, "note", "ahead", CODE_STAGE),
            ("earnest/outdated", "src/checkout/auth.py", 4, "note", "ahead", CODE_STAGE),
            ("earnest/outdated", "tests/test_auth.py", 4, "note", "ahead", CODE_STAGE),
            ("earnest/unplanned", REQUIREMENTS, 13, "note", "ahead", CODE_STAGE),
        ]
    )


def test_route_mismatch_fails_the_stage_check_of_any_stage(fixture_repo):
    repo = fixture_repo("seeded-change")
    text = (repo / SHARD).read_text(encoding="utf-8")
    start = text.index("## Stage Skipped\n**Timestamp**: 2026-09-26T09:20:00Z")
    end = text.index("---\n", start) + 4
    (repo / SHARD).write_text(text[:start] + text[end:], encoding="utf-8")
    done = stage_check(repo, REQ_STAGE)
    assert done.returncode == 1
    assert [r["ruleId"] for r in sarif_run(done.stdout)["results"]] == ["earnest/route-mismatch"]


def test_plain_check_prints_the_count_of_indexed_items_without_a_held_hash(fixture_repo):
    repo = fixture_repo("seeded-change")
    stage_check(repo, CODE_STAGE)  # holds the two tasks; the record now exists
    assert "body-hash baseline: 3 items without a held hash" in run_earnest(repo, "check").stderr.splitlines()


def test_plan_results_include_the_stale_approval_note(fixture_repo, commit_overlay):
    repo = fixture_repo("seeded-change")
    commit_overlay(repo, "seeded-change", "task/add-limiter-window")
    done = run_earnest(repo, "plan")
    assert table(done) == [
        ("earnest/outdated", REQUIREMENTS, 3, "note", "current", REQ_STAGE),
        ("earnest/unplanned", REQUIREMENTS, 13, "note", "ahead", CODE_STAGE),
    ]


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads any file")
def test_an_unreadable_audit_shard_exits_two_with_one_line(fixture_repo):
    repo = fixture_repo("seeded-change")
    (repo / SHARD).chmod(0o000)
    try:
        done = run_earnest(repo, "plan")
    finally:
        (repo / SHARD).chmod(0o644)
    assert (done.returncode, done.stdout) == (2, "")
    assert done.stderr.startswith("earnest: ")
    assert len(done.stderr.splitlines()) == 1
```

Run: `uv run pytest tests/unit/test_plan.py tests/unit/test_cli.py tests/integration/test_stage.py --no-cov -q`

Expected: `47 failed, 143 passed`. Forty-seven of the 48 new tests fail (`AttributeError` for `select_intent` and the like, and exit 2 from the M1 command-line parser for `plan` and `--stage`); `test_plain_check_places_an_unsupported_intents_findings_without_a_plan` already holds, since M1's check places every finding without a plan. The other 142 are the tests these files held (190 collected, less the 48 new).

- [ ] **Step 2: Add the selection functions to `plan.py`**

At the end of `packages/earnest/src/earnest/plan.py`, append:

```python


UNSUPPORTED_ROUTE = "unsupported route: units-generation is on the route, so per-unit stages"


class PlanError(Exception):
    """The command cannot pick what it was asked for: an intent, a stage, or a route that M2 does not report."""


def find_intent(intents: Sequence[Intent], option: str | None) -> Intent:
    """Return the intent named by `--intent`, or the only one.

    Raises:
        PlanError: the option names no record directory, or none is named and there is not exactly one.
    """
    known = ", ".join(current.directory for current in intents)
    if option is not None:
        found = next((current for current in intents if current.directory == option), None)
        if found is None:
            msg = f"no record directory {option}: the record directories are {known or 'none'}"
            raise PlanError(msg)
        return found
    if not intents:
        msg = "no record directory holds an aidlc-state.md"
        raise PlanError(msg)
    if len(intents) > 1:
        msg = f"several record directories hold an aidlc-state.md, so name one with --intent: {known}"
        raise PlanError(msg)
    return intents[0]


def select_intent(intents: Sequence[Intent], option: str | None) -> Intent:
    """Return the intent a stage check runs on: `find_intent`, refusing a route with per-unit stages.

    Raises:
        PlanError: see `find_intent`, or the intent's route holds `units-generation`.
    """
    found = find_intent(intents, option)
    if found.unsupported:
        raise PlanError(UNSUPPORTED_ROUTE)
    return found


def select_stage(plan: Plan, text: str) -> str:
    """Return the stage that `--stage` names: its id, or its slug when exactly one route stage has it.

    Raises:
        PlanError: the text is not a stage on the route, or its slug names several.
    """
    route = plan.intent.route
    if text in route:
        return text
    named = [stage for stage in route if stage.partition("/")[2] == text]
    if len(named) == 1:
        return named[0]
    if named:
        msg = f"{text} names several stages, so name one of {', '.join(named)}"
        raise PlanError(msg)
    msg = f"{text} is not a stage on the route: {', '.join(route) or _unreadable(plan.intent)}"
    raise PlanError(msg)


def _unreadable(intent: Intent) -> str:
    """Say where the state file's Stage Progress cannot be read, when that is why the route is empty."""
    found = [each for each in route_findings(intent) if each.subject == "Stage Progress"]
    if not found:
        return "none"
    return f"the state file's Stage Progress cannot be read ({found[0].path}:{found[0].line})"
```

- [ ] **Step 3: Rewrite `cli.py`**

Replace the whole of `packages/earnest/src/earnest/cli.py` with:

```python
"""Command surface: `earnest check` and `earnest plan`, which wire the scanner, the index, the checks and the plan."""

import argparse
import os
import posixpath
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from earnest import adapters, git, plan, reporter, structural
from earnest.index import Index, Source, build_index
from earnest.reporter import Finding, Run


@dataclass(frozen=True)
class _World:
    """Everything one run reads before it decides anything."""

    root: Path
    commit: str
    sources: list[Source]
    changes: list[str]
    record: reporter.Record
    record_exists: bool
    intents: list[plan.Intent]


@dataclass(frozen=True)
class _Analysis:
    """What the run works out: the plans, every placed finding, the plan's own, and what each stage's status is."""

    index: Index
    levels: dict[str, str]
    plans: list[plan.Plan]
    findings: list[Finding]
    derived: list[Finding]
    statuses: dict[str, dict[str, plan.StageStatus]]
    run: Run


@dataclass(frozen=True)
class _Result:
    """What a run prints and returns; `notes` are stderr lines that come before the summary."""

    log: str
    summary: str
    code: int
    notes: str = ""


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return its exit code.

    The exit code is 0 when no error-level finding sits at position behind or current, 1 when one does, and 2 when
    the command cannot run: Git cannot answer, a file or the record cannot be read or written, the record is corrupt
    or newer, an intent or stage cannot be chosen, the route has per-unit stages, or the reader of the log or the
    summary goes away.
    """
    parser = argparse.ArgumentParser(prog="earnest", description="Requirements traceability for LLM-written code.")
    # main never dispatches on the bare command, so a bare `earnest` must stop here rather than run the check
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="trace the repository; SARIF 2.1.0 on stdout, a summary on stderr")
    check.add_argument("--stage", help="check one stage: its id, or its slug when that is unambiguous")
    check.add_argument("--intent", help="the record directory of the intent, when there are several")
    commands.add_parser("plan", help="print the route, each stage's status and approval, and the frontier")
    args = parser.parse_args(argv)
    try:
        world = _read()
        result = _plan(world) if args.command == "plan" else _check(world, args)
    except (git.GitError, OSError, reporter.RecordError, plan.PlanError) as error:
        sys.stderr.write(f"earnest: {error}\n")
        return 2
    try:
        sys.stdout.write(result.log)
        sys.stdout.flush()
        sys.stderr.write(result.notes + result.summary)
        sys.stderr.flush()
    except BrokenPipeError:  # a reader went away, as `head` does: send what is left to devnull, so exit stays quiet
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.dup2(devnull, sys.stderr.fileno())
        return 2
    return result.code


def _read() -> _World:
    root = git.repo_root(Path.cwd())
    commit = git.head_commit(root)
    files = git.work_tree_files(root)
    sources = adapters.scan(root, files)
    intents = [plan.intent(record) for record in plan.load(root, files)]
    record = reporter.read_record(root)
    return _World(root, commit, sources, git.changes(root), record, (root / reporter.RECORD).exists(), intents)


def _analyse(world: _World) -> _Analysis:
    index = build_index(world.sources)
    supported = [current for current in world.intents if not current.unsupported]
    produces = plan.produces(world.intents)
    levels = structural.traced(index, produces)
    plans = [plan.build(current, index) for current in supported]
    frozen = plan.frozen_bodies(world.record.bodies, supported)
    own = [found for each in plans for found in (*plan.plan_findings(each, index), *plan.approval_findings(each))]
    derived = plan.place(plans, index, own)
    findings = [*plan.place(plans, index, structural.check(index, produces=produces, frozen=frozen)), *derived]
    statuses = {each.intent.directory: plan.statuses(each, index, findings, levels) for each in plans}
    props = plan.properties(plans, statuses, index, levels) if world.intents else None
    held = world.record.bodies
    unheld = sum(1 for item in index.defined.values() if _in_any(supported, item.path) and str(item.id) not in held)
    run = Run(
        world.commit,
        plan.dirty(world.changes, world.intents),
        plan=props,
        record_absent=not world.record_exists and bool(index.defined),
        unheld=unheld if world.record_exists else 0,
    )
    return _Analysis(index, levels, plans, findings, derived, statuses, run)


def _in_any(intents: Sequence[plan.Intent], path: str) -> bool:
    return any(plan.inside(current, path) for current in intents)


def _code(findings: Sequence[Finding]) -> int:
    return 1 if any(found.level == "error" for found in findings) else 0


def _option(world: _World, text: str | None) -> str | None:
    """Return the record directory that `--intent` names: root-relative first, else relative to the working directory."""
    if text is None:
        return None
    named = posixpath.normpath(text)
    directories = {current.directory for current in world.intents}
    if named in directories:
        return named
    try:
        relative = (Path.cwd() / text).resolve().relative_to(world.root.resolve()).as_posix()
    except ValueError:
        return named
    return relative if relative in directories else named


def _plan(world: _World) -> _Result:
    skipped = [current for current in world.intents if current.unsupported]
    if len(world.intents) == 1 and skipped:
        raise plan.PlanError(plan.UNSUPPORTED_ROUTE)
    analysis = _analyse(world)
    notes = "".join(f"earnest: skipped {current.directory}: unsupported route\n" for current in skipped)
    results, run = analysis.derived, analysis.run
    return _Result(
        reporter.sarif(results, analysis.levels, run),
        reporter.summary(results, analysis.levels, run),
        _code(results),
        notes or ("" if world.intents else "no plan\n"),
    )


def _check(world: _World, args: argparse.Namespace) -> _Result:
    if args.stage is None:
        if args.intent is not None:
            plan.find_intent(world.intents, _option(world, args.intent))
        analysis = _analyse(world)
        findings, run = analysis.findings, analysis.run
        return _Result(
            reporter.sarif(findings, analysis.levels, run),
            reporter.summary(findings, analysis.levels, run),
            _code(findings),
        )
    chosen = plan.select_intent(world.intents, _option(world, args.intent))
    return _stage(world, _analyse(world), chosen, args.stage)


def _stage(world: _World, analysis: _Analysis, chosen: plan.Intent, text: str) -> _Result:
    current = next(each for each in analysis.plans if each.intent.directory == chosen.directory)
    stage = plan.select_stage(current, text)
    found = plan.scoped(analysis.findings, current, stage)
    state = analysis.statuses[chosen.directory][stage]
    tree = plan.evaluated_tree(world.sources, world.intents)
    digest = plan.assessment_hash(plan.assessment_document(current, stage, tree, found))
    items = next(each for each in current.stages if each.stage == stage).items
    key = reporter.run_key(chosen.directory, stage)
    reasons = {"errors": state.errors, "openTasks": state.open_tasks, "approval": state.approval}
    run = replace(
        analysis.run,
        timestamp=reporter.utc_timestamp(),
        assessment={"stage": key, "hash": digest, "status": state.status, "reasons": reasons},
        record_absent=False,
        unheld=sum(1 for item in items if str(item.id) not in world.record.bodies),
    )
    # ponytail: the record is read and rewritten whole, so two stage checks of different stages racing are
    # last-writer-wins (the same stage twice is safe); take an flock on `.earnest/lock` if sensor fires run in parallel
    world.record.bodies = plan.next_bodies(world.record.bodies, current, stage)
    world.record.runs[key] = plan.header(current, stage, state, run, digest)
    reporter.write_record(world.root, world.record)
    return _Result(
        reporter.sarif(found, analysis.levels, run), reporter.summary(found, analysis.levels, run), _code(found)
    )
```

- [ ] **Step 4: Run the exit command**

Run: `uv run pytest tests/steps/test_stage_status.py --no-cov -q`

Expected: `28 passed`. A failure that traces to a step is fixed in `tests/steps/test_stage_status.py`; the feature changes only through a ratified revision of `04`; a code defect is fixed in its owning module with a unit test first.

- [ ] **Step 5: Run the whole suite**

Run: `uv run pytest --no-cov -q 2>&1 | tail -2`

Expected: `452 passed` (as root, `450 passed, 2 skipped`).

- [ ] **Step 6: Run the linters**

Run: `make lint`

Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add src/earnest/cli.py src/earnest/plan.py tests/unit/test_cli.py tests/unit/test_plan.py tests/integration/test_stage.py tests/steps/test_stage_status.py
git commit -m "feat: run earnest plan and earnest check --stage"
```

### Task 13: The full suite, the review and the milestone DAG

#### Final state after the milestone review (D17 and S1–S7)

This subsection supersedes the historical snippets of Tasks 1, 6, 8, 9, 10, 11 and 12 wherever they differ; each of those tasks carries a pointer to it. Those snippets are the TDD record as the tasks ran; the code at HEAD is what bc7e5c1 left, and anyone replaying the plan applies the items below on top of them. Each item names the module and function in `packages/earnest/src/earnest/`.

- **Symlinked record (MUST-FIX 2, Task 6).** `reporter._refuse_symlink(root)` runs first in `read_record` and `write_record` and raises `OSError("<path> is a symlink; the record must lie in the repository")` for `.earnest` and, since the pre-PR review, for `.earnest/assessment.json`. `cli.main` already catches `OSError`, so `plan`, `check` and `check --stage` exit 2 with one stderr line and write nothing outside the repository.
- **Looping `--intent` symlink (MUST-FIX 1, Task 12).** `cli._option` catches `(ValueError, RuntimeError)`; the `RuntimeError` is the symlink loop that `Path.resolve` raises before Python 3.13.
- **ReDoS in the state reader (Task 8).** `plan._SCOPE` is `^- \*\*Scope\*\*:[ \t]*(.*)$` with no lazy group before the trailing blanks, and `parse_state` strips them with `.rstrip(" \t")`. `_PHASE_WORD` is gone: `plan._phase(heading)` strips a trailing separate word PHASE by string comparison, not by regex. Both are linear; 50 000 spaces took about 7 s before and 0.0 s after.
- **S1 (Task 9).** `index._ID_ENTRY` is `index.ID_ENTRY`, and `plan._items` uses it. `plan._ITEM_ID` and the `TYPES` import are gone.
- **S2 (Task 6).** `reporter.Record` builds `coverage` and `judge` with `field(default_factory=lambda: ...)`. The `_empty_coverage` and `_empty_judge` factories are gone.
- **S3–S5 (tests; Tasks 1, 8, 9, 10, 11 and 12).** S3: `tests/sarif.py` defines `RECORD`, `SHARD`, `REQUIREMENTS` and `PLAN_FILE` once, and `test_stage.py`, `tests/steps/test_stage_status.py`, `test_seeded_change.py` and `test_cli.py` import them (Tasks 1 and 12); `test_adapters.py`, `test_reporter.py` and `test_plan.py` keep their own local `RECORD` or `REQUIREMENTS`. S4: `tests/sarif.py` has one `write(repo, path, text)` helper that makes the parents, which the step file, `test_plan.py` (whose `put` loops over it), `test_cli.py` and `conftest.py` import in place of their own mkdir-then-write copies (Tasks 1, 8 and 12). S5: in `test_plan.py`, `item()` calls `ident()` (Tasks 9 and 10), and the tests that need the unsupported state use the `UNSUPPORTED_STATE` constant instead of rebuilding it inline (Tasks 10, 11 and 12).
- **S6 (Tasks 9 and 12).** `plan.Intent` has no `scope` field and `cli._Analysis` has no `index` field, since neither was read.
- **S7 (Task 8).** `plan.load` uses `adapters.STATE` and defines no `STATE` of its own.
- **Not applied.** S8, sharing one `adapters.read_bytes` for the skip rule, was optional and is left out.
- **State scope.** `plan.State.scope` is still parsed, but nothing displays it in M2 (D17); the Task 8 text that says "for display" is historical, and `04` no longer says it. The live `State` docstring in `plan.py` still says "its scope, for display"; correcting it is a D17-4 follow-up for the next code change, and this correction does not touch code.
- **Tests.** The pass added 29: the D9, D11, D12, D14, D15 and D16 gap tests and the fix tests above. The suite at HEAD is 481 passed (453 plus the 28 scenarios).

The commit that holds all of this is bc7e5c1; ee26b31 adds the two Known limits and the Reporter clause in `02`.

#### Pre-PR review (2026-10-11)

Four review lenses (code, ponytail, simplify, security) read `origin/main...f0734a7`. The fix refuses a symlinked `.earnest/assessment.json` on read and write, builds the "not an assessment record" error from the exception's type and text so file bytes stay out of stderr, names the hours-long ceiling of the TypeScript regular-expression scan in its `ponytail:` comment, and widens the exit-2 causes in `01` to every case where `plan` or `check` cannot run. It adds 3 tests: the suite is 484 passed, with `28 passed` and `5 passed` on the exit commands. The remaining findings are recorded as follow-ups in `.pi-herdsman/publish/prepr/dispositions.md`.

#### Archival gap

The hash of the plan text that the plan reviews read before c9bfd33 was not recorded, and the reviews cite no hash, so no review is tied to that exact text. The count corrections in ee26b31 and this subsection are the reconciliation.

#### The task itself

**Files:**

- Modify: `docs/design/03-implementation-plan.md` (the `done` class on M2; the M2 task-plan entry)
- Modify only when the full-suite run exposes a defect: the owning module under `packages/earnest/src/earnest/` and its unit test, as a regression test

**Interfaces:**

- Consumes: everything above.
- Produces: the full suite green and the milestone DAG with M2 marked done. The milestone's exit command, `uv run pytest tests/steps/test_stage_status.py`, reports `28 passed`.

- [ ] **Step 1: Run the exit commands**

```bash
uv run pytest tests/steps/test_stage_status.py --no-cov -q 2>&1 | tail -2
uv run pytest tests/steps/test_trace_check.py --no-cov -q 2>&1 | tail -2
```

Expected: `28 passed`, then `5 passed`.

The milestone pass (D17) added tests to this task's run: the suite total is now `481 passed`, with the exit commands unchanged at `28 passed` and `5 passed`.

- [ ] **Step 2: Run the whole suite and the linters**

```bash
make test && make lint
```

Expected: `481 passed` across the unit, integration and behavior tiers (as root, `479 passed, 2 skipped`: M1's unreadable-file test in `test_check.py` and Task 12's unreadable-shard test in `test_stage.py` skip), then `make lint` exits 0. At the T12 checkpoint the same run read `452 passed` (`450 passed, 2 skipped` as root); the 29 tests of the milestone pass account for the difference.

- [ ] **Step 3: Fix what the run exposed**

For each defect, write the failing unit test in the owning module's test file, fix the module, rerun Step 2, and commit them with `git add <module> <test file>` and `git commit -m "fix: <description>"`. A clean run needs no commit here.

- [ ] **Step 4: Mark M2 done on the milestone DAG**

Do this after the milestone review, as M1's R29 ruled, in a commit of its own. This step and the next run from the repository root.

In `docs/design/03-implementation-plan.md`, as the ratified edit leaves it, replace:

```text
  class M1 done
```

with:

```text
  class M1,M2 done
```

In the same file, replace the M2 entry, which reads:

```text
- Task plan: `docs/superpowers/plans/<date>-stage-status.md`, written when M2
  is next.
```

with:

```text
- Task plan:
  [2026-10-10-stage-status.md](../superpowers/plans/2026-10-10-stage-status.md).
```

Then, still from the repository root, run `LINT_FILE=docs/design/03-implementation-plan.md make lint-file`.

Expected: the hook lints the file and reports no issue.

- [ ] **Step 5: Commit**

This is Task 13's one commit; a defect fixed in Step 3 has its own `fix:` commit before it. Run it from the repository root.

```bash
git add docs/design/03-implementation-plan.md
git commit -m "docs: mark M2 done on the milestone DAG"
```
