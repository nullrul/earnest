# M5 `evidence_check` Implementation Plan

Status: approved for implementation (2026-10-25). It rests on two answers, APPROVED by the maintainer on 2026-10-25, one for each gating open question that the M5 section of `docs/design/03-implementation-plan.md` names: where the evidence result is kept (answer E1 below) and the TypeScript evidence fixture (answer E2). It also rests on the M5 scenarios of `docs/design/04-bdd-test-plan.md`, RATIFIED there on 2026-10-25; Task 1 copies them into the feature.

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
  - the files to mutate: the distinct `.path` of `judge.regions(index, item, KINDS["implemented"])` over the traced requirements, Python files only;
  - the mutmut run on a temporary copy of `git.work_tree_files(root)`, skipping listed paths that are not files (a tracked file deleted from the work tree), through `impact._run` with `MAP_TIMEOUT` and the environment filter `_map_run` applies to `_INHERITED`, extracted into a function both call;
  - the whole-suite run on the unmutated copy, through the same `_run` with `--junitxml=<tmp> -o junit_family=xunit1`, whose `file`, `classname` and `name` attributes Earnest builds into node ids (`file::name`, or `file::Class::name` for a method), the form `tagged_tests` returns once a parametrized case's trailing `[...]` is stripped from `name`, reading the file with `xml.etree.ElementTree` (with `# noqa: S314`, since the file is Earnest's own temporary output), as `read_map` reads its JSON report, so a missing or unparsable report is a run with no result (exit 2), and matches against `impact.tagged_tests` to tell a tagged failure from an untagged one;
  - the read of mutmut's results, each surviving mutant mapped to its file and line, and kept when that line lies in a tagged region (the Region rule);
  - the evidence key and result of each requirement, for the record (E1).
- The `regions` and `tests` hashes of E1 come from the judge cache's region hash, `Cache._hash` in `judge/__init__.py`, extracted into a free function over `index.digest`, so the judge and the evidence layer hash regions byte for byte alike.
- `cli._analyse` gains an `evidence` flag: after the judge layer it runs the evidence layer (the suite, then mutmut), so its findings join `checked` before `plan.place` and reach `plan.statuses` and `plan.properties`; `take_map`'s spot after placement would leave them unplaced. `_check` writes the slot. `impact.py` owns the evidenced raise, which `cli._analyse` calls after the judge layer, for `check` and `plan` alike. The judge layer sets `judged` today (`judge/__init__.py`; `structural.py` gives only untraced or traced). With a model, a judged requirement whose entry is `passed` under a matching key becomes evidenced. Without one, in plain `check` and in `plan` (`cli._plan` runs `_analyse` with no model), a traced requirement with such an entry becomes evidenced directly: the writer writes `passed` only for a requirement the same run judged, so the entry stands for judged too.
- `plan.py`'s Computed status reads the evidenced level that the raise sets in `cli._analyse` (`plan.task_done` checks the level alone), so it reads no slot of its own; `plan` stays read-only.
- `reporter.py` adds `evidence-failed` to `RULES` and writes the `evidence` slot; the evidenced percentage already exists (`LEVELS`, `percentages`, `summary`). `evidence` joins the layers in three places: the run header, from `plan._layers` and `plan.header`; the stage assessment document, which `plan._layers` also feeds (`plan.py`), so the assessment hash covers it as `01`'s Assessment hash names the layers that ran; and the SARIF invocation, in `reporter.py`.
- `cli.py` adds `--evidence`, which implies `--judge` and exits 2 when mutmut cannot run.

**Tech Stack:** Python 3.12 standard library at runtime (`subprocess`, `json`, `xml.etree.ElementTree`, `ast`, `tempfile`, `shutil`, `pathlib`). mutmut is the repository's tool, run as a subprocess (L4); it joins the package's `dev` dependency group only so that the fixture's runs find it. The spike of 2026-10-25 pinned `mutmut>=3.8,<4` (3.8.0 installed); its command line and result format are under mutmut 3.8 below.

**Spec:**

- `docs/design/03-implementation-plan.md`, milestone M5.
- `01`: the Evidence rule, Trace levels, Computed status, D4, the Assessment record, Frontier and position, the Process vocabulary, the Command surface, the Runtime and permission model, and the Open questions.
- `02`: `impact.py`, `reporter.py`, `plan.py`, `structural.py`, `cli.py` and `judge/__init__.py` in Module boundaries; L1, L4, L5, L6 and L7; `fixtures/seeded-change/`.
- `04`: the M5 section, drafted and ratified before Task 1.

## mutmut 3.8, as the spike ran it

- **Command line:** in the temporary copy, `python -m mutmut run`, then the results are read from files. `mutmut run` writes `mutants/` under its working directory, holding the source paths, the `also_copy` entries and mutmut's defaults (`tests/`, `setup.cfg`, `pyproject.toml`, lock files), which is why the run needs the copy.
- **Configuration:** a `[mutmut]` section that Earnest merges with `configparser` into the copy's `setup.cfg`, keeping any other section it holds. mutmut reads `setup.cfg` only when the copy's `pyproject.toml` has no `[tool.mutmut]`, so a repository with its own `[tool.mutmut]` exits 2 naming it. The section: `source_paths` lists the files to mutate (`paths_to_mutate` and `tests_dir` still work but warn as deprecated), and `also_copy` names files the tests need beside `src/` and `tests/`, such as the fixture's `pytest.ini`, without which `pythonpath = src` is lost and no mutant is reached.
- **Result format:** one JSON file per mutated source, `mutants/<path>.meta`, whose `exit_code_by_key` maps each mutant key to an exit code. A key is `<module>.x_<function>__mutmut_<n>` for a function and `<module>.xǁ<Class>ǁ<method>__mutmut_<n>` for a method. mutmut's own `status_by_exit_code` (3.8) reads: `1` and `3` killed; `0` survived; `5` and `33` no tests; `36`, `24`, `-24`, `152` and `255` timeout; `37` caught by type check; `-9` and `-11` segfault; `34` skipped; `35` suspicious; `2` interrupted; no code (`null`) not checked. `mutants/mutmut-stats.json` holds the test-to-function stats. `mutmut results --all true` prints the same as text.
- **Mutant to line:** a key names the function, not the line. `mutants/<path>` holds, for each function, the unmutated copy `x_<function>__mutmut_orig` and each variant `x_<function>__mutmut_<n>` as plain functions (a method's variants sit inside its class as methods, keyed `xǁ<Class>ǁ<method>__mutmut_<n>`). Earnest parses that file once with `ast`, compares each surviving variant's statements with `__mutmut_orig`'s, and takes the first line that differs as an offset from the `def`; it adds that offset to the `def` line of the same function, by qualified name (class and method), in the unmutated file. No subprocess per mutant, and comments above a `def` never shift the count. (`python -m mutmut show <key>` prints the same change as a diff whose hunk starts at the comments above the `def`, so its offsets are off by one under a tag; Earnest does not use it.)
- **Granularity:** mutmut 3 mutates inside functions and methods only; module-level code and a function with nothing to mutate, such as `return window`, yield no mutant.
- **Exit code of `mutmut run`:** not the verdict; the `.meta` files are.

## Gating open questions: approved answers

Both rows sat in the Open questions section of `01`, resolved "before milestone `evidence_check`". Each answer below is **APPROVED (2026-10-25)**, and the docs commit that approved them records them in `01`, `02` and `03`.

### E1 Where the evidence result is kept (APPROVED 2026-10-25)

Question (`01`, Open questions): "Where the evidence result is kept, so that the read-only `earnest plan` can show a task as done".

Answer: a sixth key of the assessment record, `evidence`, beside `judge`.

- **Key:** one entry per requirement id with its revision (`req~rate-limit~1`), as the stub's verdict file keys its answers.
- **Value:** `{"key": {"regions": <sha256>, "tests": <sha256>, "tool": "mutmut <version>"}, "result": "passed" | "failed", "commit": <full sha>, "dirty": bool}`. `regions` hashes the requirement's `impl` regions and `tests` its test regions, as the judge cache key's "hash of the covered regions" and "hash of the covering tests" do; `commit` and `dirty` are those of the run header. No timestamp, so a rerun on the same tree writes the same record.
- **Writer:** `earnest check --evidence`, through the Reporter, the record's only writer. It replaces the entry of every requirement whose files it set out to mutate: `passed` from the mutant results only for a requirement the same run judged, else `failed` or no entry, `failed` for a requirement a failing tagged test covers, and no entry (the old one dropped) for a requirement the run reached no verdict on, such as one whose mutmut run never started because a tagged test failed. Entries of requirements outside the run are kept.
- **Reader:** the evidenced raise in `impact.py`, in both `check` and `plan`. An entry counts only when its whole key matches: its `regions` and `tests` hashes the current work tree, and its `tool` the installed mutmut; any other entry, or none, leaves the requirement short of `evidenced`. `plan` hashes the regions itself, which is model-free and runs no test, so it stays read-only.

Basis:

- `01`, Runtime and permission model, first paragraph: "Until the judge, impact and evidence layers exist, `earnest check` writes only with `--stage` …; each of those layers adds the write of its own slot to `earnest check` when it is built." The evidence layer's own slot is the answer that paragraph already implies.
- `01`, Assessment record: the record "holds the five things listed under Process vocabulary, under these keys", one key per supplying component, and Earnest "preserves the keys it does not know", so a sixth key stays at `version` 1 and an older Earnest keeps it.
- `01`, Process vocabulary: the judge cache key is "the item's id and revision, the question, the hash of the covered regions, the hash of the covering tests, the model id and the prompt hash"; E1's key is the same key less the judge's own parts, so an edit to the code or the tests invalidates the result exactly as it reruns the judge.
- `01`, Computed status and Invariants: a task is done when "each delivered `req` is at trace level evidenced", and "Done is computed from the graph and evidence"; the Command surface makes `earnest plan` read-only, so `plan` can only read evidence that a check kept.
- `02`, L7: the record is "one JSON file, written by the standard library", outside the sensor's `matches`, so the new key adds no file and no artifact.

Approving E1 revised three paragraphs of `01`: the Assessment record's key table (a sixth row, `evidence`, supplied by the evidence layer), the Process vocabulary's "The record holds five things" list (a sixth item), and Computed status (an evidence result counts only under a matching key). `02`'s `reporter.py` entry ("its six contents") and `impact.py` entry changed to match.

Alternative weighed: evidence stored in the run header of `--stage`. It would tie evidence to stage checks, while M5's exit behavior runs `check --evidence` with no stage, and a run header holds a stage's status, not a requirement's.

### E2 A TypeScript evidence fixture (APPROVED 2026-10-25)

Question (`01`, Open questions): "A TypeScript fixture for evidence through StrykerJS and Jest".

Answer: M5 exits on Python and mutmut alone, with no TypeScript fixture and no Node in the package's tests. The region filter that D4 asks for is one function over a list of surviving mutants with file and line, and the StrykerJS reader is written now and unit-tested against a canned StrykerJS JSON report (`mutation-testing-report-schema`) checked in under `tests/unit/`. A live TypeScript fixture, its Jest and StrykerJS toolchain and an end-to-end scenario move to M8 `typescript_evidence`, which `03` now holds.

Basis:

- `03`, M5: the Goal is "run the tagged tests and mutmut", and the exit behavior names no TypeScript case, so the gate needs none.
- `02`, L5, Alternatives considered: the Cucumber scaffold was rejected because it "needs Node to test a Python package"; a Jest and StrykerJS fixture would bring the same Node dependency into `make test` and CI.
- `02`, L1: "The template's TypeScript … packages stay unselected: the engine is Python, and the fork's TypeScript lives in the fork under upstream's Bun and Biome toolchain."
- `02`, L4, table row "Coverage, tests and mutants": `subprocess` running the repository's tools, `json` reading their reports; the StrykerJS side is then one JSON reader, which a canned report tests without Node.
- `01`, D4: Earnest "only filters their results by region", so the filter shared by both tools is the part Earnest owns.

This narrows the question rather than closing it. Approving E2 set the `01` row's "Resolved by" to M8 and added M8 to `03`'s DAG. FLAGGED, unchanged: `01`'s Scope still lists "the trace, judge and evidence layers, with evidence through mutmut and StrykerJS" in v1; whether M8 stays in v1 or that line changes is the maintainer's call.

## Global Constraints

- **Layout and lint:**
  - Paths follow the File and directory tree of `02`.
  - The runtime is the standard library alone (L4); mutmut is a dev dependency, never imported.
  - The lint bar is M2's: ruff (line length 120, complexity 10, five arguments, Google docstrings), `ruff format`, `mypy --strict`, and vulture at 80.
- **No network, no key:** `--evidence` implies `--judge`, and the only model is the stub of M4.
- **No Git branch:** the M5 overlay is a commit on `main`, as M4's are.
- **Writes:** mutmut runs on a temporary copy outside the repository (see mutmut 3.8), removed after; Earnest's only write stays `.earnest/` (`01`, Runtime and permission model).
- **Trust:** `--evidence` runs the repository's tests against mutated code, with the trust of running its test suite (`01`, Runtime and permission model). With `--evidence` absent it runs no JUnit suite run and no mutmut run; `check --stage` still takes the coverage map of the Impact rule, as before.
- **Timeouts and failures:** a mutmut run that cannot start, times out or reports no result exits 2, naming the tool and the reason. mutmut aborts its whole run when any test fails on the unmutated code, as its stats pass runs the whole suite (the spike: exit 1, "failed to collect stats"). So Earnest first runs the whole suite once on the unmutated copy: a failing tagged test raises `evidence-failed` against the requirements it covers, at its line; a failing untagged test exits 2 naming it, since no mutant result can be taken; in either case mutmut does not run.
- **Region filter:** a surviving mutant counts only when its line lies in a tagged region (the Region rule); it raises `evidence-failed` against every requirement that region's tags cover, located at the mutant's line, one finding per line. mutmut's statuses map once: survived and no tests count as surviving, APPROVED (2026-10-25), since no test kills the mutant; killed, timeout and caught by type check count as killed, since a test or the type check stopped the mutant; skipped raises nothing; segfault, suspicious, interrupted, not checked and any code mutmut does not list exit 2, segfault included because on macOS code that is not fork-safe can crash mutmut's workers with no test involved, as the run is incomplete. `evidence-failed` attaches only to `req` ids, so a region tagged only for a `dsn` raises nothing.
- **Evidenced:** judged, and an evidence result `passed` under a key that matches the current tree (E1); where no model runs, the matching `passed` entry stands for judged, as only a judged requirement gets one. A requirement with no `impl` region of a mutated file is not evidenced.
- **Placement:** `evidence-failed` counts against the stage of the task that delivers the requirement, as M3 places code findings, and its level follows Frontier and position.
- **Exit codes:** `evidence-failed` is an error. `judge-uncalibrated` still fires on every judge run until M6.
- **Process:**
  - No agent `rm`s a path it did not create.
  - `.pi-herdsman/` stays untracked.
  - Each commit stages its task's paths by name, with no `--no-verify`.

## Review Focus

- **The work tree stays clean:** after `check --evidence`, `git status --porcelain` is unchanged; mutmut writes its `mutants/` tree only inside the temporary copy.
- **Stale evidence:** an edit to a covered region or a covering test drops the requirement below `evidenced` in both `check` and `plan`, without a rerun.
- **Position:** `evidence-failed` is an error only at position behind or current; the scenarios that assert a non-zero exit place it there.
- **mutmut's version:** the reader parses the result format of the pinned major alone, and fails with exit 2 on another.

## Task order and the scenarios each turns green

The scenarios are RATIFIED (2026-10-25) in `04`'s M5 section. The clause column maps each to the M5 exit behavior of `03`: (a) `evidence-failed` for a surviving mutant in a tagged region; (b) every requirement at exactly one level, with three separate percentages; (c) the evidenced task and its unit shown as done.

| Scenario | Clause |
| --- | --- |
| "Against the stub model the evidence check reports a surviving mutant in a tagged region" | (a) in one exact findings table |
| "A surviving mutant outside every tagged region raises nothing" | (a), the region filter |
| "Each requirement lands at exactly one trace level, with three percentages" | (b): `traced 100%, judged 66%, evidenced 33%; requirements: 3` |
| "After the evidence check, the plan shows the evidenced task and its unit as done" | (c), through `earnest plan` |
| "An edit under an evidenced requirement drops it below evidenced until the check reruns" | (c), the stale key of E1 |
| "Without --evidence the check runs no test and no mutant" | a guard, green from Task 1 on |

| Task | Content | Depends on | Scenarios green after it |
| --- | --- | --- | --- |
| 0 | This plan, committed with the docs | none | none |
| 1 | The ratified `04` M5 section and the `evidence_check` behavior gate, red | maintainer ratification of the scenarios | "Without --evidence the check runs no test and no mutant" (the guard) |
| 2 | The mutmut run on a temporary copy, and its results, `impact.py` | T1 | none new; the guard stays green |
| 3 | The region filter and `evidence-failed`; the StrykerJS reader against a canned report | T2 | "Against the stub model …", "A surviving mutant outside every tagged region …" |
| 4 | The `evidenced` level, `cli.py`, `plan.py`, `reporter.py` | T3 | "Each requirement lands at exactly one trace level …" |
| 5 | The `evidence` slot, written by `check` and read by `plan` | T4 | "After the evidence check, the plan shows …" |
| 6 | Stale keys | T5 | "An edit under an evidenced requirement …"; all 6 |
| 7 | The full suite, lint and the pre-PR review | T6 | all 6 of M5, with M1 to M4 unchanged |

**Regression expectations:**

- **Tasks 1 to 6:** the regression run is `uv run pytest --ignore=tests/steps/test_evidence_check.py` in `packages/earnest/`, and it stays green, at the base commit's count plus the tests each task adds.
- **Task 1:** five M5 scenarios are red and the guard "Without --evidence …" is green, as plain `check` already runs no evidence; the sha pins pass.
- **Every task** records its exact count against that baseline.

## Fixture: what `seeded-change` adds for M5

Scenarios (a) and (b) read the base history of M2 and M3, and (c) and the stale-key scenario read the units variant of M2b, because of where each history puts the frontier (settled below). Each history gains one overlay, committed on `main` on top of it, and one canned-verdict file sits beside `judge-verdicts.json`, held by no commit. Both overlays and the mutant results below come from the spike of 2026-10-25 (mutmut 3.8.0, on scratch copies outside the repository).

`evidence/src/checkout/auth.py`, for the base history, 24 lines:

```python
"""Checkout authentication."""


def member_key(member: str) -> str:
    return member.strip().lower()


# [impl->req~rate-limit~1]
def count_failed_logins(window: int) -> int:
    return max(window, 0)


# [impl->req~lockout-notice~1]
def lockout_message() -> str:
    return f"Try again in {lockout_minutes(5)} minutes."


def lockout_minutes(failures: int) -> int:
    return 15 if failures >= 5 else 0


# [impl->req~audit-log~1]
def audit_lockout(member: str) -> str:
    return member_key(member)
```

`evidence-units/src/checkout/auth.py`, for the units variant: the same file, 29 lines, with five lines after line 7: `# [impl->dsn~window-counter~1]`, `def window_counter() -> None:`, its one-line docstring and two blank lines, so `task~add-limiter~1`'s design is traced. The `dsn` tag sits over a function of its own, because stacked tags with no code between them share one region (`index.py`, the Region rule), so a `dsn` tag directly above the `req` tag would cover the `req`'s code too; a function of its own keeps the two regions apart. The base history holds no `dsn~window-counter~1`, so its overlay leaves the tag out, which would otherwise be `orphaned`.

`evidence/tests/test_auth.py` (and the same file in `evidence-units/`): the base file with one line after line 6, `assert count_failed_logins(-1) == 0`, so the `req~rate-limit~1` region has mutants its test kills; the later tests move down one line, `test_lockout_message`'s assert to line 12 and `test_audit_lockout`'s to line 17. The spike's mutant results, on either overlay (15 mutants, 7 killed, 8 survived):

| Mutant | Line (base overlay) | Result | Region | Reading |
| --- | --- | --- | --- | --- |
| `x_member_key__mutmut_1` (`lower` to `upper`) | 5 | survived | none, above the first tag | raises nothing: the region filter |
| `x_count_failed_logins__mutmut_1` to `_5` | 10 | killed | `req~rate-limit~1` | none |
| `x_lockout_message__mutmut_1` | 15 | killed | `req~lockout-notice~1` | none |
| `x_lockout_message__mutmut_2` | 15 | survived | `req~lockout-notice~1` | `evidence-failed` |
| `x_lockout_minutes__mutmut_1` to `_6` | 19 | survived | `req~lockout-notice~1` | `evidence-failed`, one for the line |
| `x_audit_lockout__mutmut_1` | 24 | killed | `req~audit-log~1` | none |

`req~rate-limit~1` is evidenced by five killed mutants, not vacuously: a build that skips mutmut on its region would still pass, so the integration tier of Task 5, `tests/integration/test_evidence_check.py`, asserts the five killed results. The grain of `evidence-failed` is a reading `04` fixes; its ratified section gives one finding per line that holds a surviving mutant, so two rows, at lines 15 and 19.

`evidence-verdicts.json`: every question of the three requirements, `satisfied` for `req~rate-limit~1` and `req~lockout-notice~1`, and `req~audit-log~1 tested` `not-satisfied`, located at `tests/test_auth.py` line 17, the shifted assert of `test_audit_lockout`. Expected levels: `req~rate-limit~1` evidenced, `req~lockout-notice~1` judged (its evidence failed), `req~audit-log~1` traced, so the summary reads `traced 100%, judged 66%, evidenced 33%; requirements: 3`. In the units variant `task~add-limiter~1` and `unit~u1~1` are then done, and `task~notify-lockout~1` and `unit~u2~1` are not.

**Position, settled.** `01`, Frontier and position: a finding is current in "the frontier stage, its unit's frontier stage or the current task", and ahead (a note) after it. In the units variant `unit~u2~1`'s frontier is `construction/u2-notice/functional-design` (`unit_status.feature`, scenario "The plan prints each per-unit stage, each unit and each frontier"), so an `evidence-failed` counted against `construction/u2-notice/code-generation` is ahead, a note, and the check exits 0, as that feature's `gap` row in the same stage already shows. Moving the mutant to `req~rate-limit~1`, in `unit~u1~1`'s current frontier stage, would make it an error but leave `task~add-limiter~1` not done, which (c) needs done. In the base history the frontier is `construction/code-generation` (`stage_status.feature`), the stage both tasks share, so the finding is current, an error, and the check exits 1. Hence (a) and (b) on the base history, (c) on the units variant. This reads the placement rules and the existing features; `evidence-failed` itself does not exist yet, so Task 1's red scenarios confirm it.

## File Structure

| Path under `packages/earnest/` | Responsibility | Task |
| --- | --- | --- |
| `tests/fixtures/seeded-change/evidence/src/checkout/auth.py` | the base history's overlay: seeded surviving mutants inside and outside a region | 1 |
| `tests/fixtures/seeded-change/evidence-units/src/checkout/auth.py` | the units variant's overlay: the same, plus the `dsn~window-counter~1` tag | 1 |
| `tests/fixtures/seeded-change/evidence/tests/test_auth.py`, `tests/fixtures/seeded-change/evidence-units/tests/test_auth.py` | the base test file with the second `count_failed_logins` assert | 1 |
| `tests/fixtures/seeded-change/evidence-verdicts.json` | the stub's verdicts for M5 | 1 |
| `tests/features/evidence_check.feature` | M5's 6 scenarios, verbatim from `04` | 1 |
| `tests/steps/test_evidence_check.py` | pytest-bdd steps; the exit command | 1 |
| `tests/conftest.py` | `_OVERLAYS` gains `evidence`, `evidence-units` and `evidence-verdicts.json`, which the builders leave out; the two overlays committed through the existing `commit_on_main` | 1 |
| `tests/integration/test_seeded_change.py` | the units variant's sha and both overlays' lines pinned | 1 |
| `src/earnest/impact.py` | the mutmut run, its results, the region filter, the StrykerJS reader, the evidenced raise, the evidence keys | 2-6 |
| `src/earnest/cli.py`, `src/earnest/plan.py` | the call to the evidenced raise after the judge layer; `evidence` in `plan._layers` | 4 |
| `src/earnest/plan.py` | Computed status sees evidenced through the level; its tests cover done and stale | 5, 6 |
| `src/earnest/judge/__init__.py` | `Cache._hash` extracted into a free function the evidence key shares | 4 |
| `src/earnest/reporter.py` | `evidence-failed` in `RULES` and `RuleId`; the invocation's layers; the `evidence` slot (`Record.evidence`, `_KNOWN`) | 3-5 |
| `src/earnest/cli.py` | `--evidence`, implying `--judge`; exit 2 when mutmut cannot run; `cli._analyse` gains the `evidence` flag and runs the evidence layer (suite, then mutmut) after the judge layer, so its findings reach `plan.place`; the run's entries carried on `_Analysis` and written on both record-write paths | 2, 5 |
| `pyproject.toml` | mutmut in the `dev` group, `>=3.8,<4` (added by the spike) | spike, done |
| `tests/unit/test_impact.py`, `test_plan.py`, `test_judge.py`, `test_reporter.py`, `test_cli.py`; `tests/unit/stryker-report.json`; `tests/integration/test_evidence_check.py` | each task's tests | 2-6 |

Outside the package, `01`, `02` and `03` already record E1 and E2, and Task 1 only ratifies `04`'s M5 section. The docs commit that adds this plan also adds its link to M5's entry in `03`; marking M5 done there is outside this plan's scope.

## Known limits

- Python only end to end (E2); StrykerJS results are read but never produced by a test.
- Mutation testing is slow; M5 runs mutmut under `MAP_TIMEOUT`, and only on `--evidence`. The spike ran 15 mutants at about 74 per second.
- A tagged region with nothing to mutate is evidenced by its green tests alone.
- The evidence key hashes only the requirement's own regions and tagged tests (E1, approved). An edit to code the region calls from outside every region, such as `member_key`, or to `conftest.py` or `pytest.ini`, can change which mutants survive while the key still matches, so the stored result stays counted until `check --evidence` reruns. FLAGGED for the maintainer, not changed: widening the key changes the approved E1.
- mutmut mutates whole files and selects tests itself (D4); Earnest filters by region and never picks tests.
- `judge-uncalibrated` fires on every evidence run until M6.

---

## Tasks

### Task 1: Approved answers, the `04` scenarios, and the behavior gate, red

**Files:**

- Create: the `evidence/` and `evidence-units/` overlays and `evidence-verdicts.json` under `packages/earnest/tests/fixtures/seeded-change/`
- Create: `packages/earnest/tests/features/evidence_check.feature`, `packages/earnest/tests/steps/test_evidence_check.py`
- Modify: `packages/earnest/tests/conftest.py`, `packages/earnest/tests/integration/test_seeded_change.py`

- [x] **Step 1:** E1 and E2 approved 2026-10-25 and recorded in `01`, `02` and `03`. Stop here unless the maintainer has also ratified `04`'s M5 scenarios.
- [x] **Step 2:** Spike, done 2026-10-25: mutmut 3.8.0 in the `dev` group, pinned `>=3.8,<4`, run on scratch copies of the base and units fixtures (3 mutants, all killed, the same `src/` and `tests/` in both) and of the proposed overlay (15 mutants, 7 killed, 8 survived). Recorded under mutmut 3.8 and the Fixture section.
- [ ] **Step 3:** Write the two overlays and `evidence-verdicts.json` as the Fixture section gives them. `04`'s M5 section is ratified in the plan's own commit before this branch starts, so this task changes no doc.
- [ ] **Step 4:** Add `evidence`, `evidence-units` and `evidence-verdicts.json` to `_OVERLAYS` in `tests/conftest.py`, so the builders leave them out and every pinned sha of M1 to M4 stands. Add the steps that commit `evidence/` on `main` over the base commit and `evidence-units/` on `main` over the units variant through the existing `commit_on_main(repo, "seeded-change", <overlay>)`, and pin the units variant's sha and both overlays' lines in `test_seeded_change.py`.
- [ ] **Step 5:** Copy the M5 Gherkin of `04` into `evidence_check.feature` verbatim, and write the step module. The stub step sets `EARNEST_JUDGE` to `stub:` and the absolute path of `evidence-verdicts.json`.
- [ ] **Step 6:** Run the regression run, then `uv run pytest tests/steps/test_evidence_check.py`. Expected: the regression run is green, the guard passes, and the other 5 M5 scenarios fail.
- [ ] **Step 7:** Commit `test: RED evidence_check behavior gate and seeded-change M5 cases`.

### Task 2: The mutmut run and its results, `impact.py`; `--evidence` in `cli.py`

**Files:** Modify `packages/earnest/src/earnest/impact.py`, `cli.py`; Test `tests/unit/test_impact.py`, `tests/unit/test_cli.py`.

- [ ] **Step 1:** Write failing tests:
  - the files to mutate are the Python files holding an `impl` region of a traced requirement, and no others;
  - the run copies the listed files to a temporary directory, writes mutmut's configuration there, and leaves `git status --porcelain` unchanged;
  - the whole-suite run on the unmutated copy writes a JUnit report (`-o junit_family=xunit1`) whose failures Earnest reads as node ids in the form `tagged_tests` returns; a failing untagged test exits 2 naming it, and mutmut does not run;
  - mutmut missing, a timeout, an unreadable mutmut result, and a missing or unparsable JUnit report each exit 2;
  - the copy keeps the other sections of an existing `setup.cfg`; a `[tool.mutmut]` in the copy's `pyproject.toml` exits 2; a tracked file deleted from the work tree is left out of the copy;
  - a mutmut of another major version exits 2, and so does a mutmut under `python` whose version differs from the one in Earnest's interpreter;
  - `--evidence` implies `--judge`; one test runs `check --evidence` and asserts that the `--junitxml` suite run and the mutmut command reach `impact._run`, then runs `check` without it and asserts neither does (the coverage-map run of `check --stage` is unchanged), so it is red until this task.
- [ ] **Step 2:** Implement, running mutmut as `take_map` runs pytest: `python -m mutmut` under the `python` that `take_map` takes (default `sys.executable`, the interpreter whose environment holds the repository's tests), with the environment filter of `_map_run`. The `tool` of E1's key is `mutmut` and `importlib.metadata.version("mutmut")` in Earnest's own interpreter, so `plan` reads it without a subprocess; the run also reads the version under `python` (`python -c` with `importlib.metadata`, through a call that keeps stdout, since `_run` returns only the exit code) and exits 2 when the two differ, so the key names the mutmut that ran; in `plan` and plain `check`, with mutmut absent no entry matches, every requirement stays short of evidenced; under `--evidence` it exits 2. `cli._analyse` gains the `evidence` flag and runs the evidence layer after the judge layer, so its findings reach `plan.place`.
- [ ] **Step 3:** The scenario "Without --evidence the check runs no test and no mutant" passes. Commit `feat: the mutmut run for --evidence`.

### Task 3: The region filter and `evidence-failed`

**Files:** Modify `packages/earnest/src/earnest/impact.py`, `reporter.py`; Create `packages/earnest/tests/unit/stryker-report.json`; Test `tests/unit/test_impact.py`, `tests/unit/test_reporter.py`.

- [ ] **Step 1:** Write failing tests:
  - a surviving mutant on a tagged line raises `evidence-failed` against each requirement the region's tags cover, at the mutant's line;
  - a surviving mutant outside every region raises nothing, and one in a region tagged only for a `dsn` raises nothing;
  - the status map: no tests counts as surviving, timeout and caught by type check as killed, skipped raises nothing, and segfault, suspicious, interrupted, not checked and an unlisted code each exit 2;
  - a tagged test failing on the unmutated copy raises `evidence-failed` against each requirement its tag covers, located at the test's tag line (JUnit's 0-based `line` is not used);
  - the StrykerJS reader turns the canned report's `Survived` mutants into the same file-and-line list.
- [ ] **Step 2:** Implement. The message names the requirement, the file and line, and the mutation.
- [ ] **Step 3:** The two scenarios of Task 3 pass. Commit `feat: evidence-failed for surviving mutants in tagged regions`.

### Task 4: The `evidenced` level

**Files:** Modify `packages/earnest/src/earnest/impact.py`, `cli.py`, `plan.py`, `reporter.py`, `judge/__init__.py`; Test `tests/unit/test_impact.py`, `tests/unit/test_judge.py`, `tests/unit/test_cli.py`, `tests/unit/test_plan.py`, `tests/unit/test_reporter.py`.

- [ ] **Step 1:** Write failing tests: with a model, evidenced needs judged and a `passed` entry for its id and revision; with no model, a traced requirement with such an entry is evidenced; each requirement has exactly one level; the extracted hash function gives the same region hash as `Cache` did; the run header's, the stage assessment document's and the invocation's layers name `evidence`, and adding it changes the assessment hash.
- [ ] **Step 2:** Implement. Extract `Cache._hash` into the free function E1's key uses. `Run` gains a field that tells `reporter.sarif` the evidence layer ran, as `_layers` tells the header. In `check --evidence` the raise reads the run's own entries in memory, keyed as E1 gives; Task 5 persists them and lets `plan` read them.
- [ ] **Step 3:** The scenario "Each requirement lands at exactly one trace level …" passes. Commit `feat: the evidenced level`.

### Task 5: The `evidence` slot, written by `check` and read by `plan`

**Files:** Modify `packages/earnest/src/earnest/impact.py`, `cli.py`, `plan.py`, `reporter.py`; Test `tests/unit/test_reporter.py`, `tests/unit/test_cli.py`, `tests/unit/test_plan.py`, `tests/integration/test_evidence_check.py`.

- [ ] **Step 1:** Write failing tests: the slot round-trips in canonical JSON; a record without `evidence` reads as the empty slot; a rerun on the same tree writes the same record; a requirement a failing tagged test covers gets `failed`; a requirement the run reached no verdict on loses its old entry; entries of requirements outside the run are kept; `plan` reads it and shows `task~add-limiter~1` and `unit~u1~1` done and writes nothing. Also add a pinning test, green from the start, that the integration run reports the five killed `req~rate-limit~1` mutants.
- [ ] **Step 2:** Implement through the record's existing atomic write: a `Record.evidence` field and `evidence` in `reporter._KNOWN`, read in `reporter._record` as `data.get("evidence", {})` so a record M2 to M4 wrote still reads, written as an `"evidence"` entry in `write_record`'s body, an `_Analysis` field in `cli.py` that carries the run's entries, and `world.record.evidence` set on both write paths of `cli.py` (plain `check` and `_stage`). The reader matches an entry by requirement id and revision only; Task 6 adds the key comparison.
- [ ] **Step 3:** The scenario "After the evidence check, the plan shows …" passes. Commit `feat: the evidence slot and done from evidence`.

### Task 6: Stale keys

**Files:** Modify `packages/earnest/src/earnest/impact.py`, `plan.py`; Test `tests/unit/test_impact.py`, `tests/unit/test_plan.py`.

- [ ] **Step 1:** Write failing tests, red because Task 5's reader matches by id and revision alone: an edit to a covered region, to a covering test, or a different mutmut version each leaves the entry unmatched, so the requirement reads judged under `check --judge` and traced in `plan` and plain `check`, and its task is not done in all three.
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
  "packages/earnest/src/earnest/impact.py",
  "packages/earnest/src/earnest/plan.py",
  "packages/earnest/src/earnest/judge/__init__.py",
  "packages/earnest/src/earnest/reporter.py",
  "packages/earnest/src/earnest/cli.py",
  "packages/earnest/tests/conftest.py",
  "packages/earnest/tests/features/evidence_check.feature",
  "packages/earnest/tests/steps/test_evidence_check.py",
  "packages/earnest/tests/unit/test_impact.py",
  "packages/earnest/tests/unit/test_plan.py",
  "packages/earnest/tests/unit/test_judge.py",
  "packages/earnest/tests/unit/test_reporter.py",
  "packages/earnest/tests/unit/test_cli.py",
  "packages/earnest/tests/unit/stryker-report.json",
  "packages/earnest/tests/integration/test_seeded_change.py",
  "packages/earnest/tests/integration/test_evidence_check.py",
  "packages/earnest/tests/fixtures/seeded-change/evidence/",
  "packages/earnest/tests/fixtures/seeded-change/evidence-units/",
  "packages/earnest/tests/fixtures/seeded-change/evidence-verdicts.json"
]
```
