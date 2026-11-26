# M8 `typescript_evidence` Implementation Plan

Status: APPROVED-ready, 2026-11-25. The maintainer decided all six gating answers on 2026-11-25 (DECIDED (user, 2026-11-25) in each, recorded in Task 0 Step 1), so nothing here waits on him; the `04` scenarios of Task 0 stay PROPOSED text until he ratifies them. The plan rests on spike E of 2026-11-25 (one Node setup for M8 and M9, kept in `/tmp/earnest-swarm/spike-e/` and summarised under Spike E facts below) and on a read of `impact.py` at `ae4136c`. The `04` scenarios in Task 0 are PROPOSED text: approving this plan does not ratify them. No StrykerJS run of the drafted fixture exists yet. Task 2 Step 2 makes it, and the fixture's mutant table below is measured only where it says so. M8 depends on M5, which is done.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run `uv run pytest tests/steps/test_typescript_evidence.py` in `packages/earnest/`. It drives `earnest check --evidence` against `ts-evidence`, a TypeScript fixture with Jest and StrykerJS, and asserts these things:

- a surviving StrykerJS mutant inside a tagged region raises `earnest/evidence-failed` at the mutant's line (D4);
- a surviving mutant outside every tagged region raises nothing;
- each requirement lands at exactly one trace level with three separate percentages, and a requirement whose region holds killed mutants and no survivor is evidenced (SC3 for TypeScript);
- an evidenced TypeScript requirement stays evidenced for a plain `check` until an edit to its region or its test changes the key (E1);
- a plain `check` needs no Node tool, and an evidence run without StrykerJS exits 2 and names the tool.

The exit command turns green at Task 5.

**Architecture:**

- `impact.py` gains the StrykerJS run beside the mutmut run (`02`, `impact.py` in Module boundaries; the deliverable of `03`, M8):
  - the files to mutate: `mutation_files` keeps the `.py` files it returns today and adds the `.ts`, `.tsx`, `.mts` and `.cts` files that hold an `impl` region of a traced requirement; `evidence()` splits them by suffix;
  - the StrykerJS run on the temporary copy that `_copy` makes from `git.work_tree_files(root)`, through `_run` with `MAP_TIMEOUT` and the `_environment()` filter, with the command's `node_modules` linked into the copy by one `symlink_to` (see the Interface contract);
  - the report reader: `stryker_mutants` replaces `stryker_survivors`. M5's reader returns survivors only, and `entries()` marks a requirement `passed` only when a killed mutant lies in its regions (`_killed`), so the reader must return every mutant;
  - the evidence key's `tool`, `stryker <version>`, read from the installed `@stryker-mutator/core` without a subprocess, so the read-only `plan` still runs no test.
- The Python half (`pytest` suite, then mutmut) runs only when the index holds a `.py` file to mutate or a Python test tag. A TypeScript-only repository runs no pytest and needs no mutmut.
- The region filter, `evidence_failed`, `evidenced`, `merged` and the Region rule are unchanged: they work on `Mutant(path, line, key, code)` and `Region`, whatever the language.
- The tests: a TypeScript fixture under `tests/fixtures/ts-evidence/`, `typescript_evidence.feature` with its step module, `tests/node.py` for the Node tools' PATH, `tests/tools.py` for the one fail-not-skip `require`, and a fake `stryker` script (written by `fake_executable` of `tests/conftest.py`) so that the unit tier keeps Node out (L5).
- One Node toolchain under `packages/earnest/`, shared with M9's #26 (see Shared with M9).

**Tech Stack:**

- Python 3.12 standard library at runtime (L4), unchanged. Nothing new is imported.
- Node tools, as dev tooling only, run as subprocesses: StrykerJS 10.1.1 (`@stryker-mutator/core` and `jest-runner`), Jest 30.5.2, ts-jest 29.4.15, TypeScript 6.0.3, `@types/jest` 30.0.0. These are the exact pins of spike E, all DECIDED (user, 2026-11-25) with questions 1 to 5 below.

**Spec:**

- `docs/design/03-implementation-plan.md`, milestone M8.
- `01`: the Evidence rule, D4, the Region rule, Trace levels, Computed status, the Assessment record, E1 of the M5 task plan, and the Open questions row on the TypeScript fixture.
- `02`: `impact.py` in Module boundaries; L1, L4, L5, L6.
- `04`: the M8 row of the milestone table, and the M8 section that Task 0 writes.
- Issues #36 (the Node decision), #37 (this plan and its `04` scenarios) and #38 (the exit gate). #26 (M9) shares #36's answer.

## Spike E facts (2026-11-25)

Source: `/tmp/earnest-swarm/spike-e/REPORT.md` and the logs and sketches beside it (`setup1-lockfile/`, `setup1b-pnpm/`, `fixture-src/`, `logs/`). The spike ran on a 48-core host, with timings the mean of three in seconds. The report says to read the order, not the absolute times.

| #   | Fact                                                                                                                                                                                                                                                                                                                                                    | Evidence                                                                                                                      |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| S1  | One `package.json` and lockfile give `jest`, `stryker` and `openspec` in `node_modules/.bin`. Jest passes 4 tests, Stryker kills 9 of 11 mutants of the spike's fixture, and `openspec validate` exits 0 on a valid spec and 1 on an invalid one.                                                                                                       | REPORT, Answers; `logs/summary.tsv`; `logs/openspec-invalid.out`                                                              |
| S2  | Earnest runs Stryker on a temporary copy of the work tree, and `git.work_tree_files` leaves ignored files such as `node_modules` out of it. Stryker then fails: `Could not inject ... jestWrapper ... Cannot find module 'jest'`. Setting `NODE_PATH` to the `node_modules`, or symlinking it into the copy, fixes it.                                  | REPORT, Answers; `logs/s2c-pnpm-dlx-plain-cold.out` line 52 (the failure); `logs/times-s2c.tsv` (the `NODE_PATH` runs exit 0) |
| S3  | `earnest.impact.stryker_survivors` reads a real Stryker 10.1.1 report and gives `[('src/limits.ts', 3), ('src/limits.ts', 11)]`.                                                                                                                                                                                                                        | REPORT, Answers                                                                                                               |
| S4  | Node must be 22.20.0 or later, from the `engines` field of `@fission-ai/openspec`. `npm ci` fails with EBADENGINE on 20.19.5 and 22.19.0, and passes on 22.20.0 and 24.22.3. CI's `lint-docs` job uses Node 20.                                                                                                                                         | `logs/node-matrix.tsv`; `.github/workflows/ci.yml` line 28                                                                    |
| S5  | Pins: jest 30.5.2, `@stryker-mutator/core` and `jest-runner` 10.1.1, `@fission-ai/openspec` 2.1.1, ts-jest 29.4.15, typescript 6.0.3 (ts-jest needs below 7), `@types/jest` 30.0.0.                                                                                                                                                                     | REPORT, Pins; `setup1-lockfile/package.json`                                                                                  |
| S6  | Install cold: npm lock 3.57, pnpm lock 1.39, mise 2.61. Install warm: npm 2.63, pnpm 0.76, mise 0.02. Stryker hot: npm 3.42, pnpm 3.31. Fetch plus Stryker through `npx` on demand: 11.51 cold, 3.83 warm; through `pnpm dlx`: 5.59 cold, 3.57 warm.                                                                                                    | `logs/summary.tsv`                                                                                                            |
| S7  | Stryker defaults to the core count less one workers: its log reads `Creating 47 test runner process(es)` for 11 mutants on the 48-core host. With `--concurrency 2`, Stryker takes 6.52 s on 1 CPU, 3.91 s on 2 CPUs and 3.13 s on 4 CPUs (`taskset`). The fixture's own Jest run takes 1.0 to 1.5 s.                                                   | `logs/s2c-pnpm-dlx-plain-cold.out` line 51; `logs/times-cpu.tsv`; `scripts/cpu-limit.sh`                                      |
| S8  | Offline, `npx --offline` fails fast when nothing is cached (0.22 s, exit 1, for an empty `npx` cache). `npx` on a dead network without `--offline` stalls 73.69 s. This is setup 2 only: the spike ran no offline `npm ci` or `pnpm install --frozen-lockfile`.                                                                                         | `logs/times-s2-offline.tsv`; `logs/summary.tsv`                                                                               |
| S9  | `npm audit` reports 22 moderate and no high or critical findings (minimatch, qs, glob). One dependency has an install script, `@parcel/watcher`. `npm ci --ignore-scripts` works, and pnpm 10 skips dependency build scripts by default.                                                                                                                | REPORT, Measurements; `logs/audit.json`                                                                                       |
| S10 | The npm lockfile pins 633 packages with integrity hashes. `npx` pins 6 top-level packages. mise pins Node by sha, while OpenSpec's own dependencies float. mise installs each tool in its own prefix, so `jest-runner` could not see `jest` (inferred, not run).                                                                                        | REPORT, Tradeoffs                                                                                                             |
| S11 | The lockfile detects drift: `npm ci` refuses a manifest that names `@fission-ai/openspec@2.2.0` against a lock that holds 2.1.1.                                                                                                                                                                                                                        | `logs/drift-npm.out` line 350                                                                                                 |
| S12 | pnpm is already the repository's precedent: the `lint-docs` job runs `pnpm/action-setup` with `version: 10`, and `make lint-file` and the pre-commit hook run `pnpm dlx markdownlint-cli2`. pnpm is not installed on this host.                                                                                                                         | `.github/workflows/ci.yml` lines 23-25; `Makefile` line 33; `.pre-commit-config.yaml`                                         |
| S13 | Both installs print peer warnings for `babel-jest` 30.5.2: `unmet peer @babel/core@^7.0.0-0: found 8.0.10` from pnpm, and `ERESOLVE overriding peer dependency` from npm. The installs succeed.                                                                                                                                                         | `logs/s2c-pnpm-dlx-plain-cold.out`; `logs/drift-npm.out`                                                                      |
| S14 | Not verified by the spike: real runner timings, Dependabot, macOS and Windows, a real `impact.py` Stryker runner (none exists), the `node_modules` link on a pnpm layout, and the offline behavior of `npm ci` and `pnpm install --frozen-lockfile` (S8 measured `npx` only). The `NODE_PATH` and symlink fixes of S2 are reported for the npm install. | REPORT, Not verified                                                                                                          |

## What the code does today (read 2026-11-25 at `ae4136c`)

| #   | Reading                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Where                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| C1  | `mutation_files` keeps `.py` files only, and `_test_tags` skips test tags in any other file.                                                                                                                                                                                                                                                                                                                                                            | `impact.py` lines 396-399, 282     |
| C2  | On the drafted fixture, `check --evidence` with stub verdicts exits 0, prints `traced 100%, judged 100%, evidenced 0%`, raises only `judge-uncalibrated`, and writes `"evidence": {}`. It runs pytest on the copy, collects nothing, and mutates nothing. This is the red state of the gate: no scenario of it has a finding to match. Observed in a scratch repository with the package's venv.                                                        | `impact.evidence`                  |
| C3  | `evidence()` calls `_tool(python)` first, so a repository without mutmut gets an `EvidenceError` even when no `.py` file is mutated.                                                                                                                                                                                                                                                                                                                    | `impact.py` line 425               |
| C4  | `stryker_survivors` returns the file and line of `Survived` and `NoCoverage` mutants only.                                                                                                                                                                                                                                                                                                                                                              | `impact.py` lines 776-794          |
| C5  | The evidence key's `tool` is `mutmut <version>` from `importlib.metadata`, and `keys()` returns `{}` without mutmut. A TypeScript requirement could never match a key.                                                                                                                                                                                                                                                                                  | `impact.py` lines 388-393, 656-667 |
| C6  | `_surviving` hard-codes `mutmut` in the message of an incomplete run.                                                                                                                                                                                                                                                                                                                                                                                   | `impact.py` line 732               |
| C7  | `impact.py` is 794 lines. The global coding style puts 800 as the ceiling, and this milestone adds about a hundred. See plan choice P5.                                                                                                                                                                                                                                                                                                                 | `wc -l`                            |
| C8  | A lean fixture with no AI-DLC record needs the whole chain in its requirements file, or `check` raises `orphaned` and `gap` errors: the `req` needs a `Covers:` line to a `feat`, the `feat` one to a `goal`, the `goal` one to a `tenet`, and the `feat` needs only `req`, so it carries `Needs: req`. Observed on the drafted fixture: with the chain, a plain `check` exits 0 with no finding, and `check --judge` raises only `judge-uncalibrated`. | `structural.py` lines 9-22         |

## Gating open questions

Issue #36 asks where Node, Jest and StrykerJS come from in `make test` and CI, and the M8 entry of `03` names it as the gating row. Spike E cut that question into the six choices below, and #26 asks the same of the `openspec` CLI, so each answer serves both milestones. Every answer is DECIDED (user, 2026-11-25). A recommendation was the spike's evidence read once; the decision is the maintainer's.

### 1. npm or pnpm

Row as asked: how the Node tools are installed and pinned for `make test` and the CI `test-python` job (#36).

**DECIDED (user, 2026-11-25): A. pnpm with `pnpm-lock.yaml`**, pinned by `"packageManager": "pnpm@10.34.9"` in the manifest. The install is `pnpm install --frozen-lockfile`. Ruled out: npm with `package-lock.json`, no lockfile, and mise.

Evidence (S6, S9, S12): cold install 1.39 s against npm's 3.57 s, warm 0.76 s against 2.63 s, and the same Stryker time; it is the repository's precedent (`lint-docs`, `make lint-file` and pre-commit already use pnpm); and pnpm 10 skips dependency build scripts by default. The accepted cost is a second package manager on every machine that runs `make test`, and a `pnpm/action-setup` step in the CI job.

### 2. Where the manifest lives

Row as asked: where the manifest, its lockfile and the Node version file sit.

**DECIDED (user, 2026-11-25): A. `packages/earnest/`**: `package.json`, the lockfile, `.nvmrc`, `.npmrc`. Ruled out: the repository root and `tests/fixtures/ts-evidence/`.

**Separate, deliberate exception:** commit `6d9792f` put a root `package.json` (`earnest-repo-tools`, `prettier` 3.10.1, no `packageManager` key) and a root `pnpm-lock.yaml` at the repository root, for repository tooling. It is not the evidence toolchain. M8 Task 1 still creates `packages/earnest/package.json` and its own lockfile, so two pnpm manifests and two lockfiles exist. The root manifest is deliberately unpinned: CI's `lint-docs` job pins pnpm with `version: 10` in `pnpm/action-setup@v4`, and that action fails when a `packageManager` field is also set, so the key must not be re-added at the root. Task 1's `packageManager` pin in `packages/earnest/package.json` must be compatible with `version: 10`, and the `test-python` job reads it through `package_json_file: packages/earnest/package.json`. `02`'s file tree lists neither manifest and needs the root one added.

Evidence: CI's entry is `make -C packages/earnest install test`; the exit command runs in `packages/earnest/`; `pyproject.toml` and `uv.lock` already sit there; and the spike's sketches use this layout (S1).

### 3. The Node line

Row as asked: which Node the tools run on, and whether `lint-docs` shares it.

**DECIDED (user, 2026-11-25): A. `.nvmrc` holds `24`, and `engines` says `>=22.20.0`.** A runner takes the latest 24, and the floor admits 22.20.0. **`lint-docs` stays on Node 20**: it runs `pnpm dlx markdownlint-cli2`, which needs no particular line, and moving it is a change of its own. Ruled out: an exact patch in `.nvmrc`, and `22.20.0`.

Evidence (S4): 22.20.0 and 24.22.3 pass, 20.19.5 and 22.19.0 fail with EBADENGINE, and the floor comes from the `engines` field of OpenSpec alone.

### 4. When the OpenSpec pin enters the manifest

Row as asked: #26's "pin one OpenSpec version, in one place", and the M8 setup it shares. **The version is not asked here: M9's answer 12 owns it, and the maintainer decided it on 2026-11-25 as 2.1.1.** The drafted manifest holds 2.1.1, the version spike E measured (S1, S5), and the drift run of S11 shows the lockfile refusing a manifest that names another version, so a later bump is deliberate.

**DECIDED (user, 2026-11-25): the OpenSpec CLI is pinned at 2.1.1** (M9's answer 12). The timing follows this plan's own rule: M9's ratification (#19, M9's answer 14) is decided, so **option A**, the pin enters with Task 1 and one install and one lock land once. Ruled out: B, M8 landing without it.

Constraint from the spike: the pin comes from the manifest, and nothing runs `openspec install` or a global install, which fetch unpinned code.

### 5. The TypeScript transform

Row as asked: how Jest compiles TypeScript.

**DECIDED (user, 2026-11-25): A. ts-jest 29.4.15 with typescript 6.0.3**, the one combination spike E measured: Jest passes 4 tests and Stryker kills 9 of 11 mutants (S1). It type-checks, so a mutant that breaks the types fails its suite and counts as killed, as mutmut's code 37 (caught by type check) does under M5. Ruled out: `@swc/jest` and `babel-jest`.

The transform is a line of the fixture's `jest.config.js` and a devDependency. Earnest never reads it, so a later change touches the fixture and the manifest, not `impact.py`.

### 6. Fail or skip when the Node tools are missing

Row as asked: whether the M8 feature fails or skips when Node, Jest or StrykerJS is missing.

**DECIDED (user, 2026-11-25): A. Fail, never skip.** `make test` depends on `node-install` and `node-check`, which exit 2 naming the missing piece. The step module's first step calls `pytest.fail` with the same line. Ruled out: skipping with a reason, and failing outside `make test` through `addopts`.

Evidence:

- `03`'s M7 exit behavior "fails rather than skips" when the fork or Bun is missing, and a skip would let the exit command pass with no TypeScript evidence run.
- The exit command is a pytest file, so Node must be on the PATH of the job that runs pytest.
- The lockfile install costs 0.76 to 3.57 s (S6), so requiring it costs little. Its offline behavior is UNVERIFIED: S8 measured `npx --offline`, not a lockfile install (S14).
- L5 kept Node out of the package's tests because the cookiecutter's Cucumber scaffold "needs Node to test a Python package". A lockfile install under `packages/earnest/` is a different cost from a scaffold, and Task 0 revises L5 to say so.

The two guard scenarios (a plain `check` with no Node tool on the PATH, and an evidence run without StrykerJS) need no Node tool, so they stay runnable everywhere.

## Shared with M9

Issues #26 and #36 ask one question. **This plan owns the recipe and is the only copy of this section: Task 1 is the one recipe for the toolchain, and Task 2 Step 3 is the one Python helper, `tests/node.py`.** M8 is in v1 and lands first, so it creates every file below; M9's plan points here and copies nothing. One toolchain lands, and these files belong to both milestones:

- `packages/earnest/package.json`, the lockfile, `.nvmrc`, and `.npmrc` (one file, with `engine-strict=true` and `save-exact=true`);
- the `node-install` and `node-check` targets of `packages/earnest/Makefile`, where `node-check` loops over every `devDependencies` entry of the manifest, so it covers `openspec` with no line of its own;
- the Node setup steps of the CI `test-python` job;
- the `.gitignore` lines `.stryker-tmp/` and `reports/mutation/`, and the `**/node_modules/**` ignore of `.markdownlint-cli2.jsonc`;
- `packages/earnest/tests/node.py`.

| Piece           | M8                                                                                                                                      | M9 (#26)                                                                                         |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| devDependencies | `@stryker-mutator/core`, `@stryker-mutator/jest-runner`, `jest`, `ts-jest`, `typescript`, `@types/jest`                                 | `@fission-ai/openspec`, already in the manifest from Task 1 (question 4)                         |
| `node-check`    | one generic target: prints Node and each manifest tool's installed version, and exits 2 naming each tool that is missing or off its pin | the same target, with no line of its own                                                         |
| Environment     | `export OPENSPEC_TELEMETRY := 0` in the Makefile, written by Task 1 from the start (harmless while `openspec` is absent)                | none to add                                                                                      |
| Python helper   | `tests/node.py`: `tools_path`, `require_tools(*names)`, `without_node_tools`                                                            | `openspec_env(home)`, added to the same file                                                     |
| Done when       | `make test` and CI run the TypeScript feature                                                                                           | `make test` and CI print the pinned `openspec --version`, and a missing CLI fails the M9 feature |

Order. M8 creates the files with all seven devDependencies (question 4), so M9 adds no dependency and regenerates no lock. A later pin change regenerates the lock with the package manager's lock-only command (`pnpm install --lockfile-only`), and never hand-merges a lockfile. #36's done-when also needs the decision recorded in `01` or `02` and #26 to reference it, which Task 0 Step 3 does.

## Plan choices that are not gating

These are this plan's own readings, open to the maintainer's objection when reviewing it. None is recorded as decided.

- **P1. The fixture is `tests/fixtures/ts-evidence/`.** It follows `calibration-dev`: a requirements file, source, tests and a canned verdicts file, with no AI-DLC record. Spike E used the same path for its sketch. This names the fixture that the M8 row of `04` leaves open (#37).
- **P2. `node-install` is a prerequisite of `test` only.** The spike's sketch hangs it on `install`. But `lint-python` and `build-earnest` also run `install` (`ci.yml` lines 17 and 48), and would need Node for nothing. `node-install` is a stamp target on `package.json` and `pnpm-lock.yaml`, so `make test` skips the install when neither changed. The cost: the exit command, run by hand, needs one `make node-install` first, and the step module's failure line says so.
- **P3. Earnest passes StrykerJS two options, `--mutate` and `--reporters json`, and no `concurrency`.** The repository's own `stryker.config.json` owns the setting (D4 and L4 leave each tool's configuration to the repository), and the fixture's sets `"concurrency": 2`. A repository that sets none gets Stryker's default of the core count less one (S7). The report is read from Stryker's default path, `reports/mutation/mutation.json`, because the JSON reporter's file name has no command-line option (to be confirmed in Task 2 Step 2).
- **P4. A failing Jest test exits 2.** Stryker's initial dry run fails when a test fails on the unmutated code, so no report exists. The M5 behavior for Python, where a failing tagged test raises `evidence-failed` at its tag, has no TypeScript counterpart in M8: it would need a TypeScript test-name scan, and the exit behavior of `03` asks only for mutants. FLAGGED in Known limits.
- **P5. The StrykerJS code stays in `impact.py`**, as `03` and #38 say. The file passes 800 lines (C7). Extracting the mutmut and StrykerJS halves into a module of their own would revise the module list of `02`, and would be a refactor with its own diff. Not proposed here.
- **P6. A key names the tool per requirement.** A requirement with Python regions only keeps `mutmut <version>` byte for byte, so every M5 record stays valid. A TypeScript-only one gets `stryker <version>`, and a requirement with both gets the two names joined by a comma and a space.

## Interface contract with StrykerJS

This is what Earnest calls and reads. `<copy>` is the temporary directory that `_copy` fills from `git.work_tree_files(root)`, as it does for mutmut. Task 2 Step 2 checks each form below against the pinned StrykerJS and records any difference in this plan before Task 3 starts.

1. **Locate the command.** `<root>/node_modules/.bin/stryker` when that is a file, else `shutil.which("stryker")` over the `PATH` of `_environment()`. Neither: `EvidenceError`, "evidence: StrykerJS is not installed", and exit 2. The command is never `resolve()`d: its parent is `.bin`, and `<modules>`, the `node_modules` directory, is the parent of `.bin`. That holds for npm's symlinks and for pnpm's wrapper scripts alike.
2. **Environment.** `_environment()` as it is: no `NODE_PATH`. The copy holds no `node_modules` (S2), so without one Stryker fails to inject `jestWrapper`. The run links `<modules>` into the copy with one `symlink_to` (`<copy>/node_modules`), before it starts Stryker, so Node resolves as normal for both CommonJS and ES modules, which `NODE_PATH` does not serve (ESM resolution ignores it). The link is made in the Stryker run, not in `_copy`, because `<modules>` comes from the located command and need not lie under the repository (the fixture holds no `node_modules`, and its tools come through the PATH).
3. **Command, run in `<copy>`.** `<command> run --mutate <files> --reporters json`, where `<files>` are the mutated paths relative to the copy, joined by commas. A path that holds a comma or a glob character (`*`, `?`, `[`, `{`, `!`) exits 2 naming the file. The repository's own `stryker.config.json` supplies everything else, the test runner, the plugins and `concurrency` (P3). Earnest never passes `--concurrency` or `--configFile`.
4. **Result.** `<copy>/reports/mutation/mutation.json`. The exit code is no verdict: Stryker exits 0 when mutants survive unless the repository sets `thresholds.break`, and 1 on an error such as a failing dry run. `_run` deletes `<copy>/reports/mutation/mutation.json` before it runs Stryker, because `_copy` copies untracked, non-ignored files and a stale report from the repository under check would otherwise pass for this run's result. A missing report is "no result": `EvidenceError` naming the exit code and the last line Stryker printed, exit 2. A timeout after `MAP_TIMEOUT` is the same, as for mutmut.
5. **Version.** `<modules>/@stryker-mutator/core/package.json`, key `version`. It is read as JSON, with no subprocess, and gives the key's `tool`: `stryker 10.1.1`.

The reader maps each mutant of the report to `Mutant(path, line, key, code)`. `path` is the file's key in the report, `line` is `location.start.line`, and `key` is `<mutatorName>#<id>`, which holds no dot, so `_mutant_findings` prints it whole. `code` borrows mutmut's exit-code domain, so `_SURVIVING`, `_KILLED` and `_SKIPPED` serve both tools. The mapping is PROPOSED, and Task 2 Step 2 reads the schema's own wording before Task 3:

| StrykerJS status                     | `code` | Reading                                                                                  |
| ------------------------------------ | ------ | ---------------------------------------------------------------------------------------- |
| `Killed`                             | 1      | killed                                                                                   |
| `Timeout`                            | 24     | killed: the mutant hangs the suite, as mutmut's timeout                                  |
| `CompileError`                       | 37     | killed: a checker stopped it, as mutmut's code 37; only with a checker plugin            |
| `Survived`                           | 0      | surviving                                                                                |
| `NoCoverage`                         | 5      | surviving: no test reaches it, as mutmut's no tests                                      |
| `Ignored`                            | 34     | skipped, raises nothing; a `// Stryker disable` comment gives it                         |
| `RuntimeError`, `Pending`, any other | `None` | not checked: the run is incomplete, exit 2 naming the mutant, as mutmut's unlisted codes |

## Fixture: `tests/fixtures/ts-evidence/`

The fixture is plain files, as L6 says: `fixture_repo("ts-evidence")` copies it, less `_OVERLAYS` (the verdicts file `evidence-verdicts.json` is already listed there), and commits it on `main` with the fixture's pinned identity. It holds no AI-DLC record, so no stage, task or plan finding appears. It holds no `node_modules` and no `package.json`: the tools come from `packages/earnest/` through the PATH (S2).

The spike's own fixture (`fixture-src/`) gave the code and tests of `clamp` and `isAtLimit`, and its measured results: 11 mutants, 9 killed, survivors at lines 3 and 11 (S3). The drafted fixture keeps those two functions at the same lines, replaces their `REQ` comments with one-line comments and tags (which Stryker does not mutate), and adds `remaining` for a requirement that reaches evidenced. `isAtLimit`'s test leaves its boundary open on purpose, and `clamp`'s `>` to `>=` mutant is equivalent, so no test can kill it.

`requirements.md` carries the whole chain, since a `req` with no parent is `orphaned` and a `feat` that needs a `stest` has a `gap` (C8). A plain `check` of it exits 0 with no finding, and `check --judge` with the stub raises only `judge-uncalibrated` (observed on 2026-11-25):

```markdown
# Requirements

`tenet~dependable-limits~1`

A limit holds the same way every time it is checked.

`goal~enforce-limits~1`

Callers learn where they stand against a limit.

Covers: tenet~dependable-limits~1

`feat~limit-checks~1`

The limiter answers where a value stands against a limit.

Covers: goal~enforce-limits~1
Needs: req

`req~limit-boundary~1`

The limiter shall treat a value at or above the limit as at the limit.

Covers: feat~limit-checks~1

`req~remaining~1`

The limiter shall report the headroom left under the limit.

Covers: feat~limit-checks~1
```

`src/limits.ts`, 17 lines:

```typescript
// A clamp that no requirement claims, so it sits above the first tag.
export function clamp(value: number, max: number): number {
  if (value > max) {
    return max;
  }
  return value;
}

// [impl->req~limit-boundary~1]
export function isAtLimit(value: number, max: number): boolean {
  return value >= max;
}

// [impl->req~remaining~1]
export function remaining(max: number, used: number): number {
  return max - used;
}
```

`tests/limits.test.ts`, 27 lines. The tests of `clamp` and `isAtLimit` are the spike's. The `describe` lines are 13 and 23:

```typescript
import { clamp, isAtLimit, remaining } from "../src/limits";

describe("clamp", () => {
  it("returns the maximum for a value above it", () => {
    expect(clamp(5, 3)).toBe(3);
  });
  it("returns the value when below the maximum", () => {
    expect(clamp(2, 3)).toBe(2);
  });
});

// [utest->req~limit-boundary~1]
describe("isAtLimit", () => {
  it("is true above the limit", () => {
    expect(isAtLimit(4, 3)).toBe(true);
  });
  it("is false below the limit", () => {
    expect(isAtLimit(1, 3)).toBe(false);
  });
});

// [utest->req~remaining~1]
describe("remaining", () => {
  it("is the limit less what is used", () => {
    expect(remaining(5, 2)).toBe(3);
  });
});
```

The configuration files are the spike's, less what Earnest now passes (`mutate`, `tempDirName`, `jsonReporter`), plus `concurrency` (P3, S7). They are given in full here, so no task reads `/tmp`. `jest.config.js`:

```javascript
module.exports = {
  testEnvironment: "node",
  transform: { "^.+\\.ts$": ["ts-jest", { tsconfig: "tsconfig.json" }] },
};
```

`tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "strict": true,
    "esModuleInterop": true,
    "types": ["jest"]
  },
  "include": ["src", "tests"]
}
```

`stryker.config.json`:

```json
{
  "testRunner": "jest",
  "plugins": ["@stryker-mutator/jest-runner"],
  "coverageAnalysis": "perTest",
  "concurrency": 2,
  "reporters": ["json", "clear-text"],
  "jest": { "configFile": "jest.config.js" }
}
```

`evidence-verdicts.json`, which no commit holds. The locations are the `def` or `describe` line, as M5's verdicts use the `def` line. The stub model with this file passed `check --judge` on the drafted tree (both requirements judged):

```json
{
  "req~limit-boundary~1": {
    "implemented": {
      "location": { "file": "src/limits.ts", "line": 10 },
      "reasoning": "isAtLimit is true at and above the limit.",
      "result": "satisfied"
    },
    "tested": {
      "location": { "file": "tests/limits.test.ts", "line": 13 },
      "reasoning": "The tests check a value above and a value below the limit.",
      "result": "satisfied"
    }
  },
  "req~remaining~1": {
    "implemented": {
      "location": { "file": "src/limits.ts", "line": 15 },
      "reasoning": "remaining returns the limit less what is used.",
      "result": "satisfied"
    },
    "tested": {
      "location": { "file": "tests/limits.test.ts", "line": 23 },
      "reasoning": "The test checks the headroom of a limit of five with two used.",
      "result": "satisfied"
    }
  }
}
```

`README.md` states that the fixture is SYNTHETIC, names the table below, and gives the by-hand run: `ln -s <package>/node_modules node_modules && <package>/node_modules/.bin/stryker run` from a copy of the fixture.

The expected StrykerJS results. Task 2 Step 2 replaces this table with the measured one, and amends the fixture or the Gherkin if a row differs:

| Mutant                                        | Line  | Status                | Region                          | Reading            | Basis                                                                  |
| --------------------------------------------- | ----- | --------------------- | ------------------------------- | ------------------ | ---------------------------------------------------------------------- |
| `clamp`: `>` to `>=`                          | 3     | Survived (equivalent) | none, above the first tag       | raises nothing     | measured: the spike's survivor at line 3 (S3); the mutator by reading  |
| `isAtLimit`: `>=` to `>`                      | 11    | Survived              | `req~limit-boundary~1`          | `evidence-failed`  | measured: the spike's survivor at line 11 (S3); the mutator by reading |
| the other nine of those two functions' eleven | 2-11  | Killed                | none, or `req~limit-boundary~1` | none               | measured: 9 of 11 killed (S1)                                          |
| `remaining`: its block, and `-` to `+`        | 15-16 | Killed                | `req~remaining~1`               | none, so evidenced | DERIVED, not run                                                       |

Expected levels, with the stub verdicts above: `req~limit-boundary~1` judged (its evidence failed), `req~remaining~1` evidenced, so the summary reads `traced 100%, judged 100%, evidenced 50%; requirements: 2`.

## Global Constraints

- **Layout and lint.**
  - Paths follow the File and directory tree of `02`, as Task 0 revises it.
  - The runtime is the standard library alone (L4). No Node package is imported or required by `src/earnest`.
  - The lint bar is M2's: ruff (line length 120, complexity 10, five arguments, Google docstrings), `ruff format`, `mypy --strict` and vulture at 80. `impact.py` keeps its complexity and argument limits, so the new functions are small and few.
- **No key, no network at test time.** The stub is the only model. The registry is reached once, by `make node-install`; after it, no test needs the network.
- **Writes.** StrykerJS runs on the temporary copy, removed after. Its `.stryker-tmp/` and `reports/` stay inside it. Earnest's only write stays `.earnest/` (`01`, Runtime and permission model).
- **Trust.** `--evidence` runs the repository's tests against mutated code, and for TypeScript runs its `jest.config.js` and `stryker.config.json`, which are code. That is the trust of running its test suite, as `01` says for mutmut.
- **Plain `check` and `plan` start no Node tool.** `keys()` reads the installed StrykerJS version as a file, and only for a held requirement whose regions are TypeScript.
- **Failures exit 2.** StrykerJS missing, not startable, timed out, with no report, or with an unlisted status in its report: `EvidenceError`, one line naming StrykerJS and the cause.
- **Region filter.** A surviving mutant counts only when its line lies in an `impl` region (the Region rule), through the same `_mutant_findings` as mutmut's. The status mapping above is the only place that reads StrykerJS statuses.
- **Evidenced.** As in M5: judged, and an evidence result `passed` under a key that matches the tree. `passed` needs a killed mutant on a line of the requirement's `impl` regions. A region with nothing to mutate is not evidenced.
- **Pins live in one place per manifest.** Versions are in `packages/earnest/package.json` (the root manifest pins only repository tooling, see decision 2), and the lockfile holds the rest. No script, Makefile or CI line repeats a version, except `node-check`, which reads it from `package.json`.
- **Lockfile.** Regenerated with the package manager's lock-only command, never merged by hand. CI installs with the frozen form, so a manifest that drifts from its lock fails (S11).
- **Process.**
  - No agent `rm`s a path it did not create.
  - `.pi-herdsman/` stays untracked.
  - Each commit stages its task's paths by name, with no `--no-verify`.
  - `node_modules/` is never committed. Nothing runs `openspec install` (question 4).
  - No push, pull request or GitHub write until the pre-PR review of the branch passes (CLAUDE.md).

## Review Focus

- **The silent no-op is gone (C2).** A requirement with TypeScript regions never stays at `judged` after an evidence run that produced no report: the run either has a report or exits 2.
- **M5 records stay valid.** A Python-only requirement's key is `mutmut <version>` byte for byte (P6), so the M5 scenarios and their sha pins do not move.
- **No Python half for a TypeScript-only repository.** The test with a `python` that fails when called proves it. No mutmut is needed there either (C3).
- **The linked `node_modules` reaches Stryker's workers.** The unit test with the fake `stryker` asserts that `<copy>/node_modules` is a symlink to the command's `node_modules`, and the feature runs the real one.
- **The work tree stays clean.** After `check --evidence`, `git status --porcelain` is unchanged, with no `.stryker-tmp/` or `reports/` in it.
- **Evidence is not vacuous.** The integration test asserts killed mutants on `remaining`'s lines, so a build that never ran Stryker on that region cannot pass.
- **One status table.** The mapping above is the only place that reads StrykerJS statuses, and `_surviving`'s incomplete-run message names the tool of the mutant's file, not `mutmut`.
- **The equivalent mutant stays outside every region.** Moving `clamp` under a tag makes `req~clamp~1` unevidenceable by construction.
- **One toolchain.** The files of Shared with M9 are created once, here, and M9 edits none of them.

## Task order and the scenarios each turns green

The scenario titles are PROPOSED, and Task 0 writes them into `04`. The clause column maps each to the M8 exit behavior of `03`, with its levels clause from #38:

- (a) `check --evidence` raises `evidence-failed` for a surviving StrykerJS mutant in a tagged region;
- (b) it raises nothing for a mutant outside every region;
- (c) the requirement gets its level (SC3 for TypeScript).

| Scenario                                                                                              | Clause                           |
| ----------------------------------------------------------------------------------------------------- | -------------------------------- |
| "The evidence check reports a surviving StrykerJS mutant in a tagged region (SC3)"                    | (a), in one exact findings table |
| "A surviving mutant outside every tagged region raises nothing (SC3)"                                 | (b)                              |
| "Each requirement lands at exactly one trace level, with three percentages (SC3)"                     | (c)                              |
| "After the evidence check, a plain check keeps the TypeScript requirement evidenced (SC3)"            | (c), the key of E1               |
| "An edit to the tested TypeScript drops the requirement below evidenced until the check reruns (SC3)" | (c), the stale key               |
| "Without --evidence the check needs no Node tool (SC3)"                                               | a guard, green from Task 2 on    |
| "Without StrykerJS the evidence check exits 2 and names the tool (SC3)"                               | a guard on "cannot run"          |

| Task | Content                                                                                      | Depends on                 | Scenarios green after it                   |
| ---- | -------------------------------------------------------------------------------------------- | -------------------------- | ------------------------------------------ |
| 0    | The docs commit: the decisions, `04`'s M8 section, the rows of `01`, `02` and `03`, the link | the maintainer's decisions | none                                       |
| 1    | The shared Node toolchain: manifest, lock, Make targets, CI, ignores                         | T0                         | none                                       |
| 2    | The fixture, `tests/node.py`, the feature and step module, red; the StrykerJS spike          | T1                         | the guard "Without --evidence ..."         |
| 3    | The StrykerJS reader gives every mutant, with the status table                               | T2                         | none new                                   |
| 4    | The StrykerJS run on the copy, and `evidence()` by language                                  | T3                         | 1, 2 and the guard "Without StrykerJS ..." |
| 5    | The evidence key per language                                                                | T4                         | 3, 4 and 5; all 7                          |
| 6    | The full suite, lint, CI, the clean-tree check and the pre-PR review                         | T5                         | all 7, with M1 to M7 unchanged             |

**Regression expectations:**

- **Tasks 1 to 5:** the regression run is `rtk proxy uv run pytest --ignore=tests/steps/test_typescript_evidence.py; echo $?` in `packages/earnest/`, and its evidence is the printed code. It stays green at the count the M8 branch records at the start of Task 1, plus the tests each task adds. If the maintainer picks option C of question 6, `addopts` carries the `--ignore` and a bare run needs no flag.
- **Task 2:** under question 6 (fail, never skip), a bare `uv run pytest` is red from here to Task 5 on the M8 module alone. Task 2 records which 6 of the 7 scenarios fail (1 to 5 and 7), and the one guard that passes.
- **Every task** records its exact count against that baseline.

## File Structure

| Path                                                                                                                                                 | Responsibility                                                                                                                                                           | Task |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---- |
| `docs/superpowers/plans/2026-11-25-typescript-evidence.md`                                                                                           | this plan: the decisions (Task 0), then each task's counts and notes                                                                                                     | 0-6  |
| `docs/design/01-logic-design.md`, `02-structural-design.md`, `03-implementation-plan.md`, `04-bdd-test-plan.md`                                      | the decisions, the resolved rows, L5, `04`'s M8 section, the link                                                                                                        | 0    |
| `packages/earnest/package.json`, the lockfile, `.nvmrc`, `.npmrc`                                                                                    | the shared Node toolchain and its pins                                                                                                                                   | 1    |
| `packages/earnest/Makefile`                                                                                                                          | `node-install`, `node-check`, and `test` depending on both                                                                                                               | 1    |
| `.github/workflows/ci.yml`                                                                                                                           | the Node setup steps of `test-python`                                                                                                                                    | 1    |
| `.gitignore`, `.markdownlint-cli2.jsonc`                                                                                                             | `.stryker-tmp/` and `reports/mutation/`; `**/node_modules/**`                                                                                                            | 1    |
| `packages/earnest/tests/fixtures/ts-evidence/`                                                                                                       | the fixture: `requirements.md`, `src/limits.ts`, `tests/limits.test.ts`, `jest.config.js`, `tsconfig.json`, `stryker.config.json`, `evidence-verdicts.json`, `README.md` | 2    |
| `packages/earnest/tests/node.py`                                                                                                                     | the one Node helper, shared with M9: the Node tools' `PATH`, `require_tools(*names)` (fails, never skips), `without_node_tools` (a PATH of `git` alone)                  | 2    |
| `packages/earnest/tests/unit/test_node.py`                                                                                                           | fail-not-skip and PATH tests                                                                                                                                             | 2    |
| `packages/earnest/tests/tools.py`, `tests/unit/test_tools.py`                                                                                        | the one `require(name, hint)` that fails, never skips, shared with M7, and the one never-skips guard                                                                     | 2    |
| `packages/earnest/tests/features/typescript_evidence.feature`                                                                                        | M8's 7 scenarios, verbatim from `04`                                                                                                                                     | 2    |
| `packages/earnest/tests/steps/test_typescript_evidence.py`                                                                                           | the steps; the exit command                                                                                                                                              | 2    |
| `packages/earnest/src/earnest/impact.py`                                                                                                             | `mutation_files` by suffix, `stryker_mutants`, the Stryker run, `evidence()` by language, `stryker_tool`, `key_tool`, per-requirement keys                               | 3-5  |
| `packages/earnest/src/earnest/cli.py`                                                                                                                | the `--evidence` help text                                                                                                                                               | 4    |
| `packages/earnest/tests/unit/test_impact.py`, `tests/unit/stryker-report.json`, `tests/unit/stryker-report-<version>.json`, `tests/unit/test_cli.py` | each task's tests; the real report of Task 2 Step 2                                                                                                                      | 3-5  |
| `packages/earnest/tests/integration/test_typescript_evidence.py`                                                                                     | the real run: the mutant table, the clean tree                                                                                                                           | 4    |
| `CLAUDE.md`                                                                                                                                          | the Build section names `make node-install` and the Node line                                                                                                            | 6    |

Outside the package, only Task 0's docs, `ci.yml`, `.gitignore`, `.markdownlint-cli2.jsonc` and `CLAUDE.md` change. `tests/conftest.py` gains `fake_executable` (Task 2 Step 3, hoisted from `fake_python` of `test_impact.py`, unless M7 landed first and did it) and nothing else: `evidence-verdicts.json` is already in `_OVERLAYS`.

## Known limits

- **TypeScript test failures are not attributed (P4).** A failing Jest test exits 2 through Stryker's dry run. It raises no `evidence-failed` at its tag, as a failing Python test does. FLAGGED for the maintainer: it needs a TypeScript test-name scan, and `01`'s Evidence rule says "a failing tagged test" without a language.
- **Impact stays Python.** `01` mentions Jest with `--findRelatedTests` for the coverage map. `03`'s M8 deliverable is evidence only, and no Jest code exists in `src/earnest`. FLAGGED, not changed.
- **A multi-line mutant counts at its start line.** A block mutant over a whole function sits on the signature line, so a region that holds the signature holds it.
- **The reader parses one report schema.** Task 2 Step 2 records the `schemaVersion` of Stryker 10.1.1, and the reader exits 2 on another major, as M5's does for mutmut.
- **The repository owns Stryker's configuration.** A repository with no `stryker.config.json` gets Stryker's defaults, which by its documentation run `npm test` for each mutant (from its documentation, not run here). One that overrides `jsonReporter.fileName` has no report at the default path, and the run exits 2.
- **An equivalent mutant cannot be killed.** Stryker's own `// Stryker disable` comment makes it `Ignored`, which raises nothing (the mapping above, from Stryker's documentation, not run here).
- **Platforms.** Linux only, as the spike ran (S14). On Windows `.bin/stryker` is a `.cmd` shim, and a symlink needs a privilege. The `node_modules` link on the copy is reported for the npm layout only, and Task 2 Step 2 checks the pnpm one.
- **Sequential halves.** A repository with both languages runs the Python half, then StrykerJS.
- **`impact.py` passes 800 lines (P5).**
- **The lockfile holds 633 packages, and `npm audit` reports 22 moderate findings (S9).** They are dev dependencies of a test toolchain and reach no shipped code. Dependabot is not configured (S14).

---

## Tasks

### Task 0: The docs commit

**Files:** Modify this plan, `docs/design/01-logic-design.md`, `docs/design/02-structural-design.md`, `docs/design/03-implementation-plan.md` and `docs/design/04-bdd-test-plan.md`.

- [x] **Step 1:** Record the six decisions (DECIDED (user, 2026-11-25), each in its question above):
  1. pnpm with `pnpm-lock.yaml`.
  2. The manifest in `packages/earnest/`.
  3. `.nvmrc` 24 with `engines` `>=22.20.0`; `lint-docs` stays on Node 20.
  4. The OpenSpec CLI pinned at 2.1.1; it enters with Task 1 (option A, by the plan's rule, because M9 is ratified).
  5. ts-jest 29.4.15 with typescript 6.0.3.
  6. Feature tests fail, never skip, when the Node tools are missing.
- [ ] **Step 2:** The M8 section of `04` is already drafted on this branch (after M6's, with M9's following; M7's is not written yet). Read it against the decisions: change a scenario only to match a decision, and keep its title. It holds:
  - the feature path, `packages/earnest/tests/features/typescript_evidence.feature`, bound by `tests/steps/test_typescript_evidence.py`;
  - the fixture, `tests/fixtures/ts-evidence/`, with its canned verdicts `evidence-verdicts.json`, which no commit holds;
  - SC3 for TypeScript;
  - the readings table and the Gherkin, marked PROPOSED until the maintainer ratifies them. Both are also given below, as the source of that draft.

  Its three other edits to `04` are in place too: the M8 row of the milestone table names `ts-evidence`; the sentence under the table and the Future directions bullet were reworded to name M7 alone (M7's Task 0 Step 2 rewords them again when its section lands); and the Scope (v1) bullet names `ts-evidence`. Nothing is left to write here. If a decision changes a reading, edit the section in place.

- [ ] **Step 3:** Resolve the row and make the edits the decisions call for:
  - `01`, Open questions: the row "A TypeScript fixture for evidence through StrykerJS and Jest" is resolved by this plan, with the date. If plan choice P4 stands, add one sentence to the Evidence rule: for TypeScript a failing test stops the StrykerJS run, which exits 2.
  - `02`, L5: Node tools enter the package's tests through a committed lockfile under `packages/earnest/`, for the TypeScript evidence fixture of M8 and the `openspec` CLI of M9. The unit tier stays Node-free, with a fake `stryker` script. Its rationale sentence about the Cucumber scaffold still stands.
  - `02`, L4's table row "Coverage, tests and mutants": it gains `subprocess` running StrykerJS and `json` reading its report.
  - `02`, the File and directory tree: `package.json`, the lockfile, `.nvmrc` and `.npmrc` under `packages/earnest/`, `tests/node.py`, and `fixtures/ts-evidence/`; and `package.json` and `pnpm-lock.yaml` at the repository root, which the tree lists neither of today.
  - `03`, M8: drop the gating row, add the toolchain and `tests/node.py` to the deliverable, and link this plan on the task-plan line.
  - Tell the maintainer that #26 is to reference the recorded decision. The comment on the issue is a GitHub write, so the maintainer approves it.
- [ ] **Step 4:** Run `LINT_FILE=<path> make lint-file` on each changed file and check the exit code with `rtk proxy`. Commit `docs: M8 typescript_evidence plan and gating answers`.

The readings the M8 scenarios pin, for `04`:

| Reading                                                                                                                                                       | Basis                                                                     |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| A surviving StrykerJS mutant raises one `evidence-failed`, an error, per line that holds one, against each requirement the region's tags cover                | the Evidence rule and the findings table in `01`; M5's reading            |
| A surviving mutant on a line outside every region raises nothing                                                                                              | the Evidence rule and D4: Earnest filters the tool's results by region    |
| `Survived` and `NoCoverage` surviving, `Killed`, `Timeout` and `CompileError` killed, `Ignored` skipped; any other status makes the run incomplete, exit 2    | M5's mapping of mutmut's statuses, carried over by the table of this plan |
| Evidenced is judged with a passing result under a key that matches the tree; a plain `check` reads the key without running a tool                             | E1; Trace levels in `01`                                                  |
| The key's `tool` for a TypeScript requirement is `stryker <version>`, so an upgrade of StrykerJS drops the requirement below evidenced until the check reruns | E1                                                                        |
| An evidence run without StrykerJS, or one that gives no report, exits 2 with one line naming it; a plain `check` needs no Node tool                           | the Command surface of `01`: a check that fails to run exits 2            |

The Gherkin for `04`, PROPOSED. The line numbers come from the Fixture section: 3 is `clamp`'s equivalent mutant, 11 is `isAtLimit`'s open boundary, and both are the spike's measured survivors (S3). The `evidenced 50%` and `remaining` rows rest on the DERIVED row of the mutant table, so Task 2 Step 2 confirms them before this text is ratified. The `Given` that names the Node tools fails, never skips, when one is missing (question 6, option A). The other steps are `conftest.py`'s or M5's.

```gherkin
Feature: TypeScript evidence
  Against the stub model, the coding agent learns from the check which tagged
  regions of a TypeScript repository hold a surviving StrykerJS mutant, and
  which level each requirement reaches, with the same three separate
  percentages as for Python (SC3). The feature runs Jest and StrykerJS from
  the package's Node toolchain, and fails when they are missing.

  Scenario: The evidence check reports a surviving StrykerJS mutant in a tagged region (SC3)
    Given the repo maintainer's "ts-evidence" repository, with Node, Jest and StrykerJS on the path
    And the judge is the stub model with the canned evidence verdicts of "ts-evidence"
    When the coding agent runs earnest check --evidence
    Then the SARIF log holds exactly these findings:
      | rule                       | file                     | line | level   | position | stage |
      | earnest/judge-uncalibrated | .earnest/assessment.json | 1    | warning | current  | -     |
      | earnest/evidence-failed    | src/limits.ts            | 11   | error   | current  | -     |
    And the check exits non-zero

  Scenario: A surviving mutant outside every tagged region raises nothing (SC3)
    Given the repo maintainer's "ts-evidence" repository, with Node, Jest and StrykerJS on the path
    And the judge is the stub model with the canned evidence verdicts of "ts-evidence"
    When the coding agent runs earnest check --evidence
    Then the SARIF log holds no finding at "src/limits.ts" line 3
    And the SARIF log holds an earnest/evidence-failed finding at "src/limits.ts" line 11

  Scenario: Each requirement lands at exactly one trace level, with three percentages (SC3)
    Given the repo maintainer's "ts-evidence" repository, with Node, Jest and StrykerJS on the path
    And the judge is the stub model with the canned evidence verdicts of "ts-evidence"
    When the coding agent runs earnest check --evidence
    Then the SARIF log gives each requirement one trace level:
      | requirement          | level     |
      | req~limit-boundary~1 | judged    |
      | req~remaining~1      | evidenced |
    And the summary leads with "traced 100%, judged 100%, evidenced 50%; requirements: 2"

  Scenario: After the evidence check, a plain check keeps the TypeScript requirement evidenced (SC3)
    Given the repo maintainer's "ts-evidence" repository, with Node, Jest and StrykerJS on the path
    And the judge is the stub model with the canned evidence verdicts of "ts-evidence"
    And the coding agent has run earnest check --evidence
    When the coding agent runs earnest check
    Then the SARIF log gives each requirement one trace level:
      | requirement          | level     |
      | req~limit-boundary~1 | traced    |
      | req~remaining~1      | evidenced |
    And the summary leads with "traced 100%, judged 50%, evidenced 50%; requirements: 2"

  Scenario: An edit to the tested TypeScript drops the requirement below evidenced until the check reruns (SC3)
    Given the repo maintainer's "ts-evidence" repository, with Node, Jest and StrykerJS on the path
    And the judge is the stub model with the canned evidence verdicts of "ts-evidence"
    And the coding agent has run earnest check --evidence
    And the coding agent has an uncommitted edit to the TypeScript test of "req~remaining~1"
    When the coding agent runs earnest check
    Then the SARIF log gives each requirement one trace level:
      | requirement          | level  |
      | req~limit-boundary~1 | traced |
      | req~remaining~1      | traced |
    And the summary leads with "traced 100%, judged 0%, evidenced 0%; requirements: 2"

  Scenario: Without --evidence the check needs no Node tool (SC3)
    Given the repo maintainer's "ts-evidence" repository, with no Node tools on the path
    When the coding agent runs earnest check
    Then the check exits zero
    And the summary leads with "traced 100%, judged 0%, evidenced 0%; requirements: 2"

  Scenario: Without StrykerJS the evidence check exits 2 and names the tool (SC3)
    Given the repo maintainer's "ts-evidence" repository, with no Node tools on the path
    And the judge is the stub model with the canned evidence verdicts of "ts-evidence"
    When the coding agent runs earnest check --evidence
    Then the check exits with code 2, with empty stdout
    And the one line on stderr names "StrykerJS"
```

### Task 1: The shared Node toolchain

**Files:**

- Create: `packages/earnest/package.json`, the lockfile (`pnpm-lock.yaml`), `packages/earnest/.nvmrc`, `packages/earnest/.npmrc`
- Create: `packages/earnest/tests/integration/test_node_toolchain.py`
- Modify: `packages/earnest/Makefile`, `.github/workflows/ci.yml`, `.gitignore`, `.markdownlint-cli2.jsonc`

The commands below are for pnpm (question 1, decided).

- [ ] **Step 1:** Write a failing test, `tests/integration/test_node_toolchain.py`, that needs no Node. It reads `package.json`, `.nvmrc`, `.npmrc` and the lockfile and asserts:
  - every `devDependencies` value is an exact version (no `^`, `~` or range);
  - `engines.node` and `.nvmrc` exist and agree with question 3's answer;
  - `.npmrc` holds `engine-strict=true` and `save-exact=true`, each once;
  - `.markdownlint-cli2.jsonc` ignores `**/node_modules/**`;
  - the Makefile's `node-install` is a stamp target: a rule `node_modules/.stamp: package.json pnpm-lock.yaml`, so `make test` skips the install when neither changed;
  - the `node-check` recipe of the Makefile names no tool: it reads the manifest (the test greps the recipe, case-sensitively, for `stryker`, `jest` and `openspec` and expects none);
  - the lockfile names each pinned package at its pinned version;
  - `ci.yml`'s `test-python` job reads `packages/earnest/.nvmrc` through `node-version-file`.

  Run it from `packages/earnest/`: `rtk proxy uv run pytest tests/integration/test_node_toolchain.py; echo $?`. Expected: red, the files do not exist.

- [ ] **Step 2:** Create the toolchain files. This step and the next are the one recipe that M9's Task 2 refers to. `package.json`, with the exact `devDependencies` of S5 and `@fission-ai/openspec` at 2.1.1 (question 4; the OpenSpec version is M9's answer 12):

  ```json
  {
    "name": "earnest-node-tools",
    "private": true,
    "version": "0.0.0",
    "description": "Node tools earnest's tests and CI need: Jest and StrykerJS for the TypeScript evidence fixture (M8), and the openspec CLI (M9).",
    "engines": { "node": ">=22.20.0" },
    "devDependencies": {
      "@fission-ai/openspec": "2.1.1",
      "@stryker-mutator/core": "10.1.1",
      "@stryker-mutator/jest-runner": "10.1.1",
      "@types/jest": "30.0.0",
      "jest": "30.5.2",
      "ts-jest": "29.4.15",
      "typescript": "6.0.3"
    },
    "packageManager": "pnpm@10.34.9"
  }
  ```

  `engines.node` per question 3 and `packageManager` for pnpm. `.nvmrc` holds `24` (question 3). `.npmrc` holds both lines, once:

  ```text
  engine-strict=true
  save-exact=true
  ```

  Generate the lock with `pnpm install --lockfile-only` and record its size and package count in this plan. M8 lands first and creates all of it, so #26 adds no dependency and `node-check` needs no edit.

- [ ] **Step 3:** Edit `packages/earnest/Makefile`. `test` gains the prerequisites `node-install` and `node-check` (P2), `install` stays `uv sync`, and `node-install node-check` join `.PHONY`; `node-install` is the phony name of the stamp file `node_modules/.stamp`, which depends on `package.json` and `pnpm-lock.yaml`, so the install runs only when one of them is newer. `OPENSPEC_TELEMETRY` is exported from the start, which is harmless while `openspec` is absent. `node-check` loops over every `devDependencies` entry of the manifest and compares the installed version with the pin, so it covers `openspec` and needs no line per tool. The recipe lines are indented by one tab in the file:

  ```make
  NODE_MODULES := $(CURDIR)/node_modules
  export OPENSPEC_TELEMETRY := 0

  test: install node-install node-check

  node-install: node_modules/.stamp

  node_modules/.stamp: package.json pnpm-lock.yaml
      pnpm install --frozen-lockfile
      touch $@

  node-check:
      @command -v node >/dev/null || { echo "node is missing: see .nvmrc" >&2; exit 2; }
      @echo "node $$(node --version)"
      @NODE_MODULES=$(NODE_MODULES) node -e 'let bad = 0; for (const [name, pin] of Object.entries(require("./package.json").devDependencies)) { let got; try { got = require(process.env.NODE_MODULES + "/" + name + "/package.json").version; } catch { console.error(name + " is missing: run make node-install"); bad = 2; continue; } if (got !== pin) { console.error(name + " is " + got + ", not the pinned " + pin); bad = 2; } else { console.log(name + " " + got); } } process.exit(bad)'
  ```

  The recipe was run against a scratch manifest of two packages on 2026-11-25: exit 0 and a line per package when installed at the pin; exit 2 with `<name> is missing: run make node-install` per package when `NODE_MODULES` is wrong; exit 2 with `<name> is <got>, not the pinned <pin>` for an off-pin one; exit 2 with `node is missing: see .nvmrc` with no `node` on the `PATH`.

- [ ] **Step 4:** Edit `.gitignore` (`.stryker-tmp/` and `reports/mutation/`, under the Node heading) and `.markdownlint-cli2.jsonc` (add `**/node_modules/**` to `ignores`, since `node_modules/**` matches the root only and `packages/earnest/node_modules` holds Markdown). Edit the CI `test-python` job, and leave `lint-python`, `lint-docs` and `build-earnest` as they are (P2, question 3):

  ```yaml
  test-python:
    needs: lint-python
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - uses: pnpm/action-setup@v4
        with:
          package_json_file: packages/earnest/package.json
      - uses: actions/setup-node@v4
        with:
          node-version-file: packages/earnest/.nvmrc
          cache: pnpm
          cache-dependency-path: packages/earnest/pnpm-lock.yaml
      - run: make -C packages/earnest install test
  ```

  The inputs come from the actions' documentation and the spike's sketch, which no runner has run (S14). The pull request's `test-python` run is their test (Task 6).

- [ ] **Step 5:** Run, from the repository root and `packages/earnest/`:
  - `rtk proxy uv run pytest tests/integration/test_node_toolchain.py; echo $?`, expected 0;
  - `rtk proxy make -C packages/earnest node-install; echo $?`, expected 0, then `rtk proxy make --no-print-directory -C packages/earnest -n node-install | grep -c pnpm`, expected 0 (the stamp is current, so a second `make test` installs nothing);
  - `rtk proxy make -C packages/earnest node-check; echo $?`, expected 0, with `node v24...` followed by one `<name> <pin>` line per `devDependencies` entry, counted like the negative control: `rtk proxy make --no-print-directory -C packages/earnest node-check 2>/dev/null | grep -vc '^node '` (`--no-print-directory` keeps GNU make's `Entering directory` and `Leaving directory` lines, which `-C` turns on, out of the count), expected `7`;
  - the negative control, which asserts the message because `make` exits 2 for any failed recipe, so the code alone would pass for another cause: `rtk proxy make -C packages/earnest node-check NODE_MODULES=/nonexistent 2>&1 | grep -c "is missing: run make node-install"`, expected one line per manifest tool (`7`), and `rtk proxy make -C packages/earnest node-check NODE_MODULES=/nonexistent >/dev/null 2>&1; echo $?`, expected 2;
  - `rtk proxy uv run pytest --ignore=tests/steps/test_typescript_evidence.py; echo $?`, expected 0 at the baseline count (the feature does not exist yet, so the `--ignore` is a no-op here);
  - `LINT_FILE=.github/workflows/ci.yml make lint-file`, expected exit 0.
- [ ] **Step 6:** Commit `chore: shared Node toolchain for the TypeScript evidence fixture and the openspec CLI`, staging the files by name.

### Task 2: The `ts-evidence` fixture, `tests/node.py`, the feature, red, and the StrykerJS spike

**Files:**

- Create: the fixture of the Fixture section, under `packages/earnest/tests/fixtures/ts-evidence/`
- Create: `packages/earnest/tests/node.py`, `packages/earnest/tests/unit/test_node.py`
- Create, unless M7 landed first and made them: `packages/earnest/tests/tools.py`, `packages/earnest/tests/unit/test_tools.py`
- Modify, unless M7 landed first and did it: `packages/earnest/tests/conftest.py` and `tests/unit/test_impact.py` (the `fake_executable` hoist of Step 3)
- Create: `packages/earnest/tests/features/typescript_evidence.feature`, `packages/earnest/tests/steps/test_typescript_evidence.py`
- Create: `packages/earnest/tests/unit/stryker-report-<version>.json`, the real report of Step 2
- Modify: this plan, where Step 2 records what it measured

- [ ] **Step 1:** Write the fixture files exactly as the Fixture section gives them: `requirements.md`, `src/limits.ts`, `tests/limits.test.ts`, `jest.config.js`, `tsconfig.json`, `stryker.config.json`, `evidence-verdicts.json` and `README.md`. Run the regression run: no other fixture's sha moves, since `ts-evidence` is a separate directory.
- [ ] **Step 2: Spike.** In a scratch directory that this step creates (`mktemp -d`), copy the fixture, and run StrykerJS on it the way Earnest will, from `packages/earnest/`'s install:

  ```bash
  S=$(mktemp -d) && cp -R tests/fixtures/ts-evidence/. "$S" && cd "$S" \
    && ln -s "<package>/node_modules" node_modules \
    && "<package>/node_modules/.bin/stryker" run --mutate src/limits.ts --reporters json; echo $?
  ```

  Record in this plan, each as a short list:
  - the measured mutant table: mutator, line, status. If a row differs from the Fixture section's table, amend the fixture (not Earnest), the table and the Gherkin's line numbers, and tell the maintainer before Task 3;
  - the report's `schemaVersion`, its file keys (relative, forward slashes), and the status names it holds, with the schema's wording for `RuntimeError`, `CompileError`, `Ignored` and `Pending`, which settles the mapping table of the Interface contract;
  - whether `--mutate` takes the comma-joined form, whether `--reporters json` leaves the default path `reports/mutation/mutation.json`, and the line of the log that shows `concurrency` 2 applied (S7);
  - whether the `node_modules` symlink alone suffices on this install's layout (S14), and if the copy is run without it, the error;
  - a run with the fixture's `jest.config.js` pointing at a missing module, for the "no report" error text.

  Copy the real report to `tests/unit/stryker-report-<version>.json`. The step creates one scratch directory and removes only that one.

- [ ] **Step 3:** First the two shared helpers, each made by whichever of M7 and M8 lands first and reused by the other:
  - `fake_executable(directory, name, script)` in `tests/conftest.py`, hoisted from `fake_python` of `tests/unit/test_impact.py` (lines 91-95): it makes `directory` if needed, writes `#!/bin/sh` and `script` to `directory/name`, marks it executable (`0o755`) and returns its `Path`. `fake_python(tmp_path, script)` becomes `str(fake_executable(tmp_path, "python", script))`, and `test_impact.py` imports it with `from tests.conftest import fake_executable`. The fake `.bin` scripts below, and Task 4's fake `stryker`, use it;
  - `tests/tools.py`: `require(name, hint, path=None) -> Path` returns `shutil.which(name, path=path)`, and calls `pytest.fail(f"{name} is missing: {hint}", pytrace=False)` when there is none. This is the one "missing tool" helper: M7's `fork_checkout` calls it for `bun`, and `require_tools` below calls it for `node` and each Node tool, so a missing tool fails, never skips, in one place. `tests/unit/test_tools.py` holds the tests of `require` (found: the path; missing: `pytest.fail.Exception` naming the tool and the hint) and the one never-skips guard, which scans each gate file that exists (`tools.py`, `fork.py`, `node.py`, the step modules and features of M7 and M8, and the integration module of Task 4) for `\.skip\b|skipif|importorskip|xfail|@skip\b`. Add this plan's files to its list; do not write a second guard.

  Then write the failing tests of `tests/unit/test_node.py`, then `tests/node.py`. This is the one helper of the Node toolchain: M9's Task 2 refers here and adds no helper of its own. Each test uses a temporary package directory with fake `node_modules/.bin` scripts made by `fake_executable`:
  - `tools_path(path)` puts `<package>/node_modules/.bin` first on a PATH string;
  - `require_tools(*names)` calls `tools.require` for `node` on the PATH, and again for each name on `node_modules/.bin`, so it fails (the test asserts `pytest.fail.Exception`, never `pytest.skip.Exception`) when any is missing. The message names the missing piece and says `make node-install`. M8's steps call `require_tools("stryker", "jest")`, M9's `require_tools("openspec")`. The pin is `node-check`'s to enforce, which `make test` runs before pytest; the helper checks presence;
  - `without_node_tools(directory)` fills `directory` with one symlink, to `git`, and returns it as the whole PATH string. Earnest needs `git` and nothing else, and no `node` or `stryker` is then reachable on any host, whichever directory a distribution keeps them in;

  The module, as a sketch that the three tests check:

  ```python
  """The Node tools under `packages/earnest/node_modules`, for the tests: found by path, and a failure, never a skip."""

  import os
  import shutil
  from pathlib import Path

  from tests.tools import require

  PACKAGE = Path(__file__).resolve().parents[1]  # packages/earnest


  def tools_path(path: str, package: Path = PACKAGE) -> str:
      """Return the PATH string `path` with `<package>/node_modules/.bin` first."""
      return os.pathsep.join([str(package / "node_modules" / ".bin"), path])


  def require_tools(*names: str, package: Path = PACKAGE) -> None:
      """Fail with one line that names the cause unless `node` and each named tool of `.bin` are there."""
      require("node", "see packages/earnest/.nvmrc")
      for name in names:
          require(name, "run `make node-install`", path=str(package / "node_modules" / ".bin"))


  def without_node_tools(directory: Path) -> str:
      """Fill `directory` with a symlink to `git` alone, and return it as the whole PATH string."""
      git = shutil.which("git")
      assert git is not None, "git is not on the PATH"
      (directory / "git").symlink_to(git)
      return str(directory)

  ```

- [ ] **Step 4:** Copy the Gherkin of `04`'s M8 section into `typescript_evidence.feature` verbatim. Write the step module:
  - `scenarios("typescript_evidence.feature")`;
  - rebind, as `test_evidence_check.py` does, the steps of other modules that M8 reuses: the stub verdicts, `the coding agent runs earnest check --evidence`, `the coding agent has run earnest check --evidence`, `finding_at`, `no_finding_at`, `trace_levels` and `summary_leads`;
  - new: the two `Given`s that build `fixture_repo(name)` and set the PATH with `monkeypatch.setenv` (the first through `node.tools_path` and `node.require_tools("stryker", "jest")`, the second through `node.without_node_tools`, given a directory in pytest's temporary space), the edit step (the line after the `describe` that follows the `// [utest->req~...]` tag gets a `// edited` comment appended), and `the one line on stderr names "{text}"` (one line, begins with the word `earnest` and a colon, holds the text).
- [ ] **Step 5:** Run the regression run, then the exit command. Expected: the regression run is green; the exit command fails 6 of 7 scenarios (1 to 5 and 7, all red against the no-op of C2), and the guard "Without --evidence the check needs no Node tool" passes. Record the counts here.
- [ ] **Step 6:** Commit `test: RED typescript_evidence behavior gate and the ts-evidence fixture`.

### Task 3: The StrykerJS reader gives every mutant

**Files:** Modify `packages/earnest/src/earnest/impact.py`; Test `packages/earnest/tests/unit/test_impact.py`, `tests/unit/stryker-report.json`.

- [ ] **Step 1:** Write failing tests:
  - `stryker_mutants(report)` over the canned `stryker-report.json`, extended with one mutant of each status (`Killed`, `Timeout`, `CompileError`, `Survived`, `NoCoverage`, `Ignored`, `RuntimeError`, `Pending`), returns a `Mutant` for each, sorted by path, line and key, with the `code` of the mapping table and `None` for the last two;
  - `key` is `<mutatorName>#<id>`, and `line` is `location.start.line`;
  - over the real report of Task 2 (`stryker-report-<version>.json`), the survivors are exactly the measured two, and the killed are the measured count (so the reader is tested on a real artifact, not a hand-written one);
  - a report with another `schemaVersion` major, a missing `files`, or a status that is not a string raises `EvidenceError` ("the StrykerJS report ... cannot be read"), as M5's `stryker_survivors` test pins;
  - `_surviving` raises for a `None` code with a message that names `StrykerJS` for a `.ts` path and `mutmut` for a `.py` one. M5's test of the mutmut message stays as it is.
- [ ] **Step 2:** Implement: `_STRYKER_CODES` (the table), `stryker_mutants`, and the one-word tool name in `_surviving`'s message. Delete `stryker_survivors` and replace its test with the mapped one above. `_surviving`, `_SURVIVING`, `_KILLED` and `_SKIPPED` do not change.
- [ ] **Step 3:** Run the unit tests of `test_impact.py`, then `make lint` (ruff, `mypy --strict`, vulture, which no longer sees `stryker_survivors`), each with `rtk proxy ...; echo $?`.
- [ ] **Step 4:** Commit `feat: StrykerJS reader returns every mutant with mutmut's status codes`.

### Task 4: The StrykerJS run on the copy, and `evidence()` by language

**Files:** Modify `packages/earnest/src/earnest/impact.py`, `cli.py`; Create `packages/earnest/tests/integration/test_typescript_evidence.py`; Test `tests/unit/test_impact.py`, `tests/unit/test_cli.py`.

- [ ] **Step 1:** Write failing unit tests. A fake `stryker` is an `sh` script that the test writes in `tmp_path` with `fake_executable`: it records its argv, its working directory and `readlink node_modules` to a file, and copies a canned report to `reports/mutation/mutation.json` under its working directory. No Node is involved.
  - `mutation_files`, parametrized over `.ts`, `.tsx`, `.mts` and `.cts`, returns the file of a traced requirement beside the `.py` files, and a `.js` file or a file with no tag is not returned;
  - the command is the repository's `node_modules/.bin/stryker` when that file exists, else the first `stryker` on the PATH; with neither, `EvidenceError` names StrykerJS;
  - the run: the working directory is a copy, not the repository; argv is exactly `run --mutate <files> --reporters json`; `<copy>/node_modules` is a symlink to the `node_modules` of the command (the record's `readlink`), and the environment holds no `NODE_PATH` that Earnest set; the mutants are the report's, read through Task 3's reader;
  - a path holding a comma or a glob character exits 2 naming the file;
  - the work tree holds a stale `reports/mutation/mutation.json` and the fake exits 1 without writing one: `EvidenceError`, exit 2, and the stale mutants are not returned;
  - the fake exits 1 and writes no report: `EvidenceError` holds the exit code and the last line it printed. A fake that sleeps past a patched `MAP_TIMEOUT` gives the timeout error;
  - the run leaves `git status --porcelain` unchanged, with no `.stryker-tmp/` or `reports/` in the work tree;
  - a TypeScript-only index calls neither pytest nor mutmut: `python=` is a script that fails when run, and `version` is patched to raise `PackageNotFoundError`, and `evidence()` still returns the Stryker result (C3);
  - a mixed index (one `.py` and one `.ts` region) runs both halves, and `Evidence.mutants` holds both, in path order. The Python half runs when the index holds a `.py` file to mutate or a Python test tag (`tagged_tests` is not empty);
  - `stryker_tool(root)` reads the version from `<modules>/@stryker-mutator/core/package.json` of the located command and gives `stryker 10.1.1`; it gives `None` with no command, and with an unreadable or version-less file; and `evidence()` returns it in `Evidence.stryker`;
  - `--evidence`'s help text in `cli.py` names mutmut and StrykerJS (`test_cli.py`).
- [ ] **Step 2:** Implement in `impact.py`:
  - `mutation_files` returns the `.py` files and the files of the suffix set `.ts .tsx .mts .cts`;
  - `Evidence` gains `stryker: str = ""`, a new last field with a default, so every M5 construction stands;
  - `_stryker(root)` locates the command (Interface contract, 1), `_stryker_run(copy, files, command)` links the command's `node_modules` into the copy with one `symlink_to`, runs it (2 to 4) and returns `stryker_mutants` of the report, and `stryker_tool(root)` gives the key's tool name (5);
  - `evidence()` runs the Python half as before when it is involved (see Step 1), skipping `_tool(python)`, `_configure` and `_suite` otherwise, then the StrykerJS half when the files include a TypeScript one. `Evidence.tool` is `""` for a TypeScript-only run;
  - `cli.py`: the help text.
- [ ] **Step 3:** Write `tests/integration/test_typescript_evidence.py`, which runs the real tools (question 6: it fails, never skips, through `node.require_tools()`). It builds `fixture_repo("ts-evidence")`, scans it, and calls `impact.evidence` with the PATH of `node.tools_path`. It asserts the measured table of Task 2 Step 2 exactly: the survivors at lines 3 and 11, and at least one killed mutant on a line of `remaining` (so a build that never ran Stryker on that region fails).
- [ ] **Step 4:** Run the unit and integration tests, the regression run, then the exit command. Expected: scenarios 1, 2, 6 and 7 green; 3, 4 and 5 red, since the key still names mutmut only (C5). Record the counts.
- [ ] **Step 5:** Run `make lint`: `impact.py` stays within ruff's complexity and argument limits and `mypy --strict`. Commit `feat: run StrykerJS on a copy of the work tree and filter its mutants by region`.

### Task 5: The evidence key per language

**Files:** Modify `packages/earnest/src/earnest/impact.py`; Test `packages/earnest/tests/unit/test_impact.py`.

- [ ] **Step 1:** Write failing tests:
  - `key_tool` over a requirement's `impl` regions: Python regions only give `mutmut <version>`, byte for byte as M5's keys; TypeScript only give `stryker <version>`; both give the two names joined by a comma and a space; a region whose tool is not installed gives `None`;
  - `entries()` writes each requirement's key with its own tool: a TypeScript requirement `passed` only when a killed mutant lies on a line of its `impl` regions, `failed` when `evidence_failed` holds a finding against it, and no entry otherwise;
  - `keys()` returns the current key of each held requirement under the installed tools, and no key for a requirement whose tool is missing, so a held TypeScript entry is stale when StrykerJS is gone or of another version;
  - M5's tests that build `impact.Evidence("mutmut 3.8.0", ...)` pass unchanged;
  - an end-to-end of the pieces on the canned report: `entries`, then `merged`, then `keys`, then `evidenced`, raises a TypeScript requirement to evidenced, and an edit to its test region drops it.
- [ ] **Step 2:** Implement `key_tool` and the per-requirement tool in `entries()`, from `Evidence.stryker`, and in `keys()`, from `stryker_tool` (P6). `key()` takes the tool name it is given, as today. `evidenced()` and `merged()` do not change.
- [ ] **Step 3:** Run the unit tests, the regression run, then the exit command `uv run pytest tests/steps/test_typescript_evidence.py`. Expected: all 7 scenarios green. Record the counts.
- [ ] **Step 4:** Run `make lint`. Commit `feat: key TypeScript evidence by the installed StrykerJS version`.

### Task 6: The full suite, lint, CI, the clean tree, and the pre-PR review

**Files:** Modify `CLAUDE.md`, `docs/design/03-implementation-plan.md`, and this plan.

- [ ] **Step 1:** Run `make` from the repository root, with `rtk proxy make; echo $?`, so that install, build, lint and test run in order, with the Node install and its check before the tests. Expected: 0, and the coverage report of `make test` shows `impact.py`'s new lines covered.
- [ ] **Step 2:** The clean tree. After `rtk proxy uv run pytest tests/steps/test_typescript_evidence.py; echo $?`, `git status --porcelain` shows only the files of this plan's tasks. In a fixture repository run by hand, `git status --porcelain` is the same before and after `earnest check --evidence`, apart from `.earnest/`.
- [ ] **Step 3:** The package still builds without the Node files. Run `make -C packages/earnest build`, then list the sdist and confirm it holds no `node_modules` (`tar tzf dist/*.tar.gz` and a count of the lines that hold `node_modules`, expected 0).
- [ ] **Step 4:** Edit `CLAUDE.md`'s Build section: `make` now needs Node on the PATH (the line of `.nvmrc`) and pnpm, `make node-install` installs the tools, and the exit command of M8 needs it once. Run `LINT_FILE=CLAUDE.md make lint-file`.
- [ ] **Step 5:** Run the `/pre-pr-review` skill on the branch (review, ponytail review, simplify, security review of the diff). It unlocks the PR gate. The branch's push and pull request need the maintainer's go-ahead, and until the pull request's `test-python` job runs green on a real runner, the CI steps of Task 1 and the Node line are unproven (S14). Report the branch, the pushed sha and the pull request URL.
- [ ] **Step 6:** After the exit command is green and the pull request has merged, give M8's node in `03`'s DAG the `done` class, as #38 asks.

Each task ends with an evidence block: `git diff --stat`, `wc -c` of each file it claims written, and one grep hit for a distinctive new line. An empty one makes the task failed.
