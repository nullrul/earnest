# 02 — Structural Design

Status: draft, derived from `01-logic-design.md`, September 2026.

This document is the code level of the C4 model
([[c4-model-describes-systems-at-four-abstraction-levels-context-containers]])
that the Architecture (C4 model) section of `01-logic-design.md` leaves to it.
`00-project-intent.md` and `01` ratify intent and mechanism, and implementation
detail starts here
([[hld-documents-separate-solution-intent-from-implementation-detail-via-a-fixed-7]]):
where each component of the Component section of `01` lives on disk, and where
its tests and fixtures live. Interfaces, data contracts and the runtime model
stay in `01`. The implementation plan (`03`) and the BDD test plan (`04`) build
on this layout.

Two repositories carry Earnest. This one holds the engine, the Python package
`packages/earnest`, drawn in full below. The AI-DLC fork that the Adopting
AI-DLC section of `01` describes lives in its own repository, and this document
lists only the paths the fork adds or changes.

## File and directory tree

```text
earnest/
  .claude/
    settings.json
    skills/pre-pr-review/SKILL.md
  .github/workflows/ci.yml
  .editorconfig
  .gitignore
  .markdownlint-cli2.jsonc
  .pre-commit-config.yaml
  .prettierignore
  .prettierrc
  .yamllint.yml
  CLAUDE.md
  Makefile
  README.md
  docs/
    README.md
    design/
      00-project-intent.md
      01-logic-design.md
      02-structural-design.md
      03-implementation-plan.md
      04-bdd-test-plan.md
    superpowers/plans/
      <date>-<slug-with-hyphens>.md
  packages/earnest/
    .python-version
    Makefile
    pyproject.toml
    uv.lock
    src/earnest/
      __init__.py
      cli.py
      git.py
      adapters/
        __init__.py
        markdown.py
        python.py
        typescript.py
        gherkin.py
      index.py
      structural.py
      ears.py
      plan.py
      impact.py
      judge/
        __init__.py
        prompt.txt
      reporter.py
    tests/
      __init__.py
      conftest.py
      sarif.py
      unit/
        __init__.py
        test_<module>.py
        adapters/
          __init__.py
          test_<language>.py
      integration/
        __init__.py
        test_<flow>.py
      features/
        <milestone>.feature
      steps/
        __init__.py
        test_<milestone>.py
      fixtures/
        broken-links/
        seeded-change/
          change/
        calibration/
```

`03` and `04` follow this document. A name in angle brackets stands for one
file per module, language, flow or milestone. The units variant of
`seeded-change` that M2b of `03` adds (a `units-generation` row on the route,
Unit Progress, `Unit`-scoped approval rows) is a second history of the same
directory, so the tree lists `seeded-change/` once.

## Fork delta

The fork's changes are listed against `awslabs/aidlc-workflows` at commit
`fe563195d827679cf166e97ef10c07c80a8d1312` on `main` (2026-09-26). Each changed
path exists at that commit, and each new file sits beside the existing sibling
named below. Every other upstream path, `docs/` and `harness/` included,
arrives unchanged with each merge.

```text
aidlc-workflows fork, delta against upstream fe563195d827
core/
  aidlc-common/stages/
    ideation/
      intent-capture.md                   changed
      scope-definition.md                 changed
      approval-handoff.md                 changed
    inception/
      requirements-analysis.md            changed
      domain-design.md                    changed
      units-generation.md                 changed
      delivery-planning.md                changed
    construction/
      functional-design.md                changed
      nfr-requirements.md                 changed
      nfr-design.md                       changed
      code-generation.md                  changed
      build-and-test.md                   changed
      ci-pipeline.md                      changed
  knowledge/aidlc-shared/
    audit-format.md                       changed
    verification.md                       changed
  scopes/
    aidlc-express.md                      changed
  sensors/
    aidlc-earnest.md                      new
  tools/
    aidlc.ts                              changed
    aidlc-sensor.ts                       changed
    aidlc-sensor-earnest.ts               new
    aidlc-state.ts                        changed
    data/templates/
      <artifact>.md                       new
tests/
  .coverage-registry.json                 changed
  unit/
    t-gate-approved-assessment.test.ts    new
    t-sensor-earnest.test.ts              new
```

- `core/aidlc-common/stages/`: the ten stages whose artifacts carry items in
  the mapping table of the Adopting AI-DLC section of `01`, and
  `construction/build-and-test.md`, list `earnest` in their `sensors:`
  frontmatter in place of `traceability` and `upstream-coverage`. The
  phase-boundary verification steps that write `verification/phase-check-*.md`
  sit in `ideation/approval-handoff.md`, `inception/delivery-planning.md` and
  `construction/ci-pipeline.md`, and the `earnest` sensor takes their place.
- `core/knowledge/aidlc-shared/`: the agents' reference. `audit-format.md`
  lists the `GATE_APPROVED` fields and gains `Assessment Hash`, `Items` and
  `Approved By`. `verification.md`, which describes the agent-written
  `traceability.json` and the phase checks, is rewritten for the derived trace
  and the `earnest` gate.
- `core/scopes/aidlc-express.md`: switches `sensors: off` to `on`; the other
  ten scopes already run sensors, so every profile shows the check.
- `core/sensors/aidlc-earnest.md`: the manifest that "The `earnest` sensor and
  the approval gate" in `01` specifies, beside `aidlc-traceability.md`.
- `core/tools/aidlc-sensor-earnest.ts`: the sensor script, beside
  `aidlc-sensor-traceability.ts`. It maps the exit code of `earnest check` to
  the sensor's `pass`: exit 0 is `pass: true`, and exit 1 or 2 is
  `pass: false`. It derives `--intent` from `output_path`.
- `core/tools/aidlc.ts` and `core/tools/aidlc-sensor.ts`: the registration
  behind "AI-DLC resolves to the script" in `01`. Upstream names each bundled
  sensor in the `TOOLS` map, `SENSOR_WORKERS`, the `__sensor-script` table of
  `resolveAlias` and the lazy-import map of `aidlc.ts`, and in
  `BUNDLED_SENSOR_IDS` of `aidlc-sensor.ts`, which a compiled engine needs to
  run a sensor from inside its binary.
- `core/tools/aidlc-state.ts`: `handleApprove`, the approve transition, writes
  the three fields into its `GATE_APPROVED` row at the emit site of the approve
  path, and reads the stage's run header, `runs[<intent dir>/<stage>]`, from
  `.earnest/assessment.json` at the repository root. AI-DLC's audit validator in
  `core/tools/aidlc-audit.ts` accepts the three field names, so that file needs
  no change. The fork also holds a gate when an artifact changes during the
  sensor run, and the approve transition confirms before approving that the
  stage's artifacts are unchanged since the sensor ran; the Fork-delta path that
  holds those two checks is an open question of `01`. The unit gate's emit site
  (`core/tools/aidlc-unit.ts`) and the team gates of `aidlc-state.ts` join this
  delta with M2b of `03`.
- `core/tools/data/templates/<artifact>.md`: one template per artifact that the
  mapping table of `01` marks adapted, written in Earnest's item syntax.
  Upstream reserves this directory, holding only a `.gitkeep`, for
  framework-default templates that both the stage agent and the
  `required-sections` sensor read. The unit-of-work template generates the
  `depends_on` yaml of `unit-of-work-dependency.md` from the `Depends:` lines,
  so the unit DAG has one source.
- `tests/unit/t-sensor-earnest.test.ts` and
  `tests/unit/t-gate-approved-assessment.test.ts`: tests for the script and the
  approve transition, beside `t281-sensor-traceability.test.ts` and
  `t-sdk-approval-gate.test.ts`. They take upstream's unnumbered `t-` form, so
  upstream's numbering and the fork's tests stay independent across merges.
- `tests/.coverage-registry.json`: regenerated with
  `bun tests/gen-coverage-registry.ts` from the new tests' `covers:` headers,
  as upstream's `tests/README.md` directs.

## Module boundaries

Module paths are relative to `packages/earnest/src/earnest/`, test paths to
`packages/earnest/tests/`. Each module names the component of the Component
section of `01` it realizes, and the headings from Scanner to Reporter follow
the Container section's pipeline. Where a module owns a rule that `01` states,
its line says "Owns", and each such rule has exactly one owner.

### Repository

- `.claude/settings.json`: the project hooks that `CLAUDE.md` lists, among
  them lint on edit and the pre-PR review gate.
- `.claude/skills/pre-pr-review/SKILL.md`: the review that gate asks for.
- `.github/workflows/ci.yml`: the lint, test and build stages, and `lint-docs`
  over the whole repository.
- `.editorconfig`, `.gitignore`, `.markdownlint-cli2.jsonc`,
  `.pre-commit-config.yaml`, `.prettierignore`, `.prettierrc`, `.yamllint.yml`:
  editor, ignore, lint and pre-commit settings from the cookiecutter.
- `CLAUDE.md`: the working model and build commands for agents.
- `Makefile`: runs each standard target across `SUBPROJECTS`, plus `lint-file`
  for the edit hook.
- `README.md`: the project overview and getting-started commands.
- `docs/README.md`: the index of the design documents.
- `docs/design/`: the design set from `00` to `04`, this document third.
- `docs/superpowers/plans/`: one writing-plans task plan per milestone, named
  `<date>-<slug-with-hyphens>.md`.

### Package

- `packages/earnest/`: the Earnest command-line process, the only runtime
  container Earnest owns in the Container section of `01`.
- `packages/earnest/.python-version`, `Makefile`, `pyproject.toml`, `uv.lock`:
  the interpreter pin, the cookiecutter's standard targets, package metadata
  with tool settings, and the locked dependencies.
- `__init__.py`: the package version.
- `cli.py`: the Command surface of `01`, `earnest check`, `earnest plan` and
  `earnest calibrate`, through `argparse`. It wires the pipeline, hands each
  assessor the part of the record it reads, and sets the exit code; the logic
  lives in the modules below
  ([[library-plus-thin-cli-keeps-the-api-as-the-system]]). Container entry
  point.
- `git.py`: reads through Git the commit, the current branch, the lines changed
  since a commit, and the files Git lists for the work tree: tracked files plus
  untracked files that are not ignored. Container input, shared by the scanner,
  the out-of-task check, impact, override drift and the run header. Lists no
  path under `.earnest/`, and reports the changed paths from one `git
  --no-optional-locks status --porcelain=v1 -z --untracked-files=all
  --no-renames` over the work tree as untracked, differing from HEAD or the
  index, or missing, so `plan` and plain `check` leave `.git/index` alone.
  `plan.py` decides `dirty` over the evaluated tree from those paths, as the
  Assessment hash section of `01` defines it; a call that passes paths to Git
  uses `--literal-pathspecs`.

### Scanner

- `adapters/`: Host adapters. Each yields the lines of its language that can
  hold an item or a tag, with their line numbers, and the grammar decides what
  parses.
- `adapters/__init__.py`: picks the adapter by file suffix for each file that
  `git.py` lists. Each `Source` carries the SHA-256 of the bytes read and, for
  the comment adapters, the lines that hold code, which the Region rule needs.
  In a record directory, the parent of a listed `aidlc-state.md`, it skips that
  file, `audit/**`, `.aidlc-engine/**`, the sibling entries that begin
  `.aidlc-`, and `memory.md` files under a stage directory; `plan.py` reads the
  first two itself. The skipped files never enter the evaluated tree.
- `adapters/markdown.py`: every line of a Markdown stage artifact, and the
  numbers of its fenced lines; `index.py` recognizes headings.
- `adapters/python.py`: `#` comments, through `tokenize`.
- `adapters/typescript.py`: `//` and block comments outside string, template
  and regular-expression literals.
- `adapters/gherkin.py`: `@` tag lines, under the doc-string and comment rules
  of the Grammar section of `01`.

### Index

- `index.py`: Grammar and index. The grammar of the Grammar section of `01`
  (ids, item blocks, key and `Override:` lines, both tag surfaces) and the index
  built from adapter output: items, edges, tags and their regions. Owns the
  Region rule, Reference resolution and the Near-miss table, so the check and
  the judge read one graph (G7). The Region rule arrives with M2 of `03`.
  Computes each item's body hash from the item's body lines, as the Revision
  lifecycle of `01` specifies, and the SHA-256 digest of each source's bytes.
  `index.py` is the seam D5 names: an editor language server reads the same
  index through it.

### Assessor

- `structural.py`: Structural checks. `gap` from the Default Needs, `unwanted`
  covers, duplicate ids, and `outdated`, `predated` and `orphaned` from
  Reference resolution. Owns the Revision lifecycle: `unbumped-change`, by
  comparing each item's body hash with the hash the record froze, and staleness
  one edge down. The lifecycle's later steps, expired overrides and outdated
  approvals, are computed under the Override rule in `judge/` and under Frontier
  and position in `plan.py`. Owns each requirement's trace level, and applies
  the route rule of Stages to the Default Needs and to parentless items.
- `ears.py`: EARS parser. Each `req` body becomes its clauses with text spans,
  the spans the judge asks about (D14), or a `req-not-ears` finding (D2).
- `plan.py`: Plan and stage engine. The route from the state file's Stage
  Progress less the audited skips, each prose file's stage from its record path,
  approvals from the `GATE_APPROVED` rows of the audit shards, and the
  `unplanned`, `cycle` and `route-mismatch` findings. Owns Stages, Computed
  status, Frontier and position, and the Out-of-task rule. The out-of-task check
  lives here because the current task, its `Delivers:` ids and the position of
  its findings are all plan state. Positions each finding behind, at or ahead of
  the frontier, including `unplanned` and `cycle` as Frontier and position
  gives them and the stale-approval note. Reads each record directory's
  `aidlc-state.md` and `audit/*.md` shards itself, by raw read, because the
  scanner skips them; builds the route from Stage Progress and the counting
  `STAGE_SKIPPED` rows; orders the audit rows by timestamp, shard name and
  position; applies the attempt, jump and rejection rules of Frontier and
  position to read each stage's approval; refuses a route that holds
  `units-generation` (exit 2); and raises `earnest/route-mismatch`. Computes
  each stage's status and reasons, `dirty`, and the assessment document of the
  Assessment hash section of `01`.
- `impact.py`: Impact and evidence. Owns the Impact rule and the Evidence rule.
  It runs the repository's own coverage, test and mutation tools as
  subprocesses and reads their JSON reports.
- `judge/__init__.py`: Judge. Questions from the EARS spans (D14) and the model
  call. Owns the Override rule, calibration, which `earnest calibrate` runs, and
  the judge cache. The cache belongs here because every part of its key, from
  the item's id and revision to the model id and prompt hash, is judge state;
  the cache itself rides in the record.
- `judge/prompt.txt`: the judge's fixed prompt. Its hash is the prompt hash in
  the run header and in the cache key. Plain text keeps it outside the Markdown
  linters, so no formatter touches the hashed bytes.

### Reporter

- `reporter.py`: Reporter. SARIF 2.1.0, the summary that leads with three
  percentages, and the rendering of each requirement's trace level, which
  `structural.py` computes. Owns the assessment record, reader and writer, with
  its five contents, the canonical JSON form shared by the record, the SARIF log
  and the assessment hash, and the plan and assessment properties of the SARIF
  run. The Container section of `01` draws the Reporter as the record's only
  writer, and one owner keeps the read and write sides in step. `reporter.py`
  receives plain data from `structural.py` and `plan.py` and imports from
  neither.

### Tests

- `__init__.py`, and one in each test directory that holds Python: the package
  markers that ruff's `INP` rule asks for, which also keep test module names
  unique across tiers.
- `conftest.py`: shared fixtures. It copies a fixture's files, less its
  `change/` overlay, into `tmp_path` and commits them with `git` as a base
  commit on `main`, and a separate step commits the overlay on a `task/…`
  branch when there is one, because the record must be written between the two
  commits. Steps that two or more features share live here too.
- `sarif.py`: the SARIF helpers shared by the step module and the unit and
  integration tests.
- `unit/test_<module>.py`: one test module per module of `src/earnest/`.
- `unit/adapters/test_<language>.py`: one per host adapter.
- `integration/test_<flow>.py`: two or more modules wired over a fixture
  repository, with real files and `git`.
- `features/<milestone>.feature`: behavior at the command-line boundary, one
  file per milestone of `03`, with scenarios from `04`.
- `steps/test_<milestone>.py`: pytest-bdd steps binding the feature of the same
  snake_case slug. `uv run pytest tests/steps/test_<milestone>.py` is that
  milestone's exit command.
- `fixtures/broken-links/`: SC2 and SC1. One commit with seeded missing links,
  orphaned items, stale revisions, malformed ids and near-misses across
  Markdown, Python, TypeScript and Gherkin.
- `fixtures/seeded-change/`: SC5, SC6, SC7, SC9, SC11 and SC1. An
  AI-DLC-shaped repository: stage artifacts in a record directory with its
  `Scope`, `GATE_APPROVED` rows, overrides, and Python code whose tests give
  per-test coverage contexts, the known dependencies of SC7. In M2 its record
  directory holds a state file, an audit log with one `GATE_APPROVED` row and the
  artifacts of a three-stage route; the base commit's tags and edges give the
  known dependencies the stage feature reads.
- `fixtures/seeded-change/change/`: the second commit, on a `task/…` branch: a
  revision bump that leaves a tag, an edge and an approval at the old revision,
  a body edit without a bump, code changed inside and outside the task, and a
  region changed under an override. The overlay's branch is named after a task
  the base commit holds, `task/add-limiter-window` (`01` names the convention
  `task/<name>-…`), so M3's out-of-task check finds a current task. M2's
  overlay holds the bump and the body edit; M3 adds code changed inside and
  outside the task to the overlay, and those findings enter plain `check`; how
  they meet M2's exact findings tables is an open question of `04`.
- `fixtures/calibration/`: SC4. The existing repository with ten hand-written
  requirements, hand-linked code and tests, and the maintainer's verdicts, read
  by `earnest calibrate`; its format is an open question.

## Layout and reuse-scaffolds decision

Each decision refers to the tree in the File and directory tree section.

### L1 Keep the monorepo cookiecutter's conventions

- Decision: the repository keeps the layout that
  `~/Projects/workspace/monorepo-cookiecutter` generated: sub-projects under
  `packages/<name>/` with the targets `install`, `build`, `lint`, `test`,
  `package` and `clean`; a root `Makefile` that delegates over `SUBPROJECTS`;
  and the Python SDK template's src layout, uv with hatchling, ruff,
  `mypy --strict` and vulture, and pytest with pytest-cov.
  `packages/earnest/Makefile` matches the template's
  `_templates/python_sdk/Makefile` byte for byte, and `pyproject.toml` differs
  from the template by its substitutions and by dropping the template's
  `fail_under = 80`, so every test run reports coverage with no threshold and
  passes or fails on its tests alone. The template's TypeScript, Rust
  and Go packages stay unselected: the engine is Python, and the fork's
  TypeScript lives in the fork under upstream's Bun and Biome toolchain. From
  `~/Projects/workspace/lint-configs`, `python/ruff.toml` sets the bar the
  template already inlines (line length 120, complexity 10, five arguments,
  Google docstrings), so the package keeps its inline settings; the ESLint and
  markdownlint packages there serve TypeScript and Markdown projects, and this
  repository lints Markdown through `.markdownlint-cli2.jsonc`. From
  `~/Projects/workspace/claude-skills`, the `dev-process` plugin supplies the
  process: `design-plan-docs` fixes the set in `docs/design/`, and
  `iterative-build-loop` gates each milestone on one behavior test, which L5
  gives a runnable command.
- Alternatives considered: a bespoke layout; the package at the repository
  root, without `packages/`.
- Rationale: T8 favors proven methods, and the template already wires CI,
  hooks and linters to this shape. `packages/<name>/` is the domain-first
  monorepo layout of [[monorepo-layout-for-multi-service-platform]], so a later
  package lands beside `earnest` with the same targets.

### L2 One module per component, grouped by the pipeline

- Decision: `src/earnest/` holds one module per component of the Component
  section of `01`, grouped by the Container section's pipeline as the Module
  boundaries section shows. A component gets a subpackage only when it needs
  several files: `adapters/` for four languages, `judge/` for code and its
  prompt. Two modules serve the container as a whole: `cli.py`, the entry
  point, and `git.py`, the repository reader that five parts share.
- Alternatives considered: layer folders such as `models/`, `services/` and
  `utils/`; a subpackage per component; one module for the whole Assessor.
- Rationale: code grouped by component stays findable in one place
  ([[vertical-codebase-organization-by-domain]]), where layer folders scatter
  each concern across several
  ([[horizontal-folder-layout-components-types-utils-is-the-wrong-default]]).
  Each module is one test boundary behind a small interface
  ([[design-deep-modules-with-small-interfaces-so-agents-can-test-around-one-boundary]]),
  which `tests/unit/` mirrors file for file. A new language adds one file under
  `adapters/`, as the Component section of `01` intends.

### L3 The AI-DLC fork is its own repository, downstream only

- Decision: the fork lives in a standalone repository, created by
  mirror-pushing `awslabs/aidlc-workflows` into a new repository as GitHub's
  "Duplicating a repository" guide describes, so it sits outside GitHub's fork
  network and its visibility is the owner's choice. Its `upstream` remote is
  fetch-only: `git remote set-url --push upstream no-push` gives it a push URL
  that resolves nowhere. Each upstream release arrives by `git fetch upstream`
  and a merge, with the Fork delta reapplied. The two repositories meet at the
  Command surface of `01`: the fork's sensor script runs
  `earnest check --stage` and reads its exit code and the SARIF log on its
  stdout.
- Alternatives considered: vendoring AI-DLC into this repository as a subtree
  under `packages/`; a fork inside GitHub's fork network, with
  `gh repo set-default` pointing at the fork.
- Rationale: GitHub's REST reference defines cross-repository pull requests
  within one network (the `head` parameter of "Create a pull request"), so a
  repository outside the network has no pull-request path to upstream, and the
  fetch-only remote closes the push path. Inside the network, `gh repo clone`
  of a fork sets the parent as the default repository (the `gh repo clone`
  manual), which `gh` uses for creating pull requests
  (`gh help repo set-default`); `gh repo set-default` is per clone, so each
  fresh `gh repo clone` starts out aimed at upstream. A fork of a public
  repository stays public, and a network shares Git data with the upstream
  repository (GitHub's "Forks" reference). The default target of the web "Contribute" button stays
  unverified. Vendoring would put upstream's Bun and TypeScript toolchain,
  packager and test suite into this repository's CI on every merge. A fork
  doubles maintenance
  ([[wrapper-plus-white-label-integration-pattern-versus-fork-for-combining]]),
  so the delta keeps to what `01` changes, plus the registrations, agent
  references and tests those changes need.

### L4 Standard library first

- Decision: the engine's runtime uses the standard library alone, plus the
  judge's model SDK once "Judge model choice and prompt" in the Open questions
  section of `01` settles; that SDK lands inside `judge/`. The table gives each
  choice, and `hashlib` computes the body, region and prompt hashes.
  `pyproject.toml` gains `[project.scripts] earnest = "earnest.cli:main"` for
  the command.
- Alternatives considered: the right-hand column of the table.
- Rationale: T3 favors one dependency-free command whose structural answers
  are deterministic, as D1 argues when it reimplements OFT's tag scan; the
  three hand scans are line and comment scans of a few dozen lines each.
  Running the repository's own tools keeps their versions the repository's
  choice, as the Evidence rule of `01` leaves test selection to those tools.

| Need | Choice | Alternative considered |
| --- | --- | --- |
| Command surface | `argparse` | `click` or `typer`, a dependency for three commands |
| Python comments | `tokenize` | `ast`, which drops comments |
| TypeScript comments | a string-aware scan for `//` and block comments | the TypeScript compiler, which brings Node |
| Markdown items | a line scan for code fences, headings, id lines and key lines | a CommonMark parser |
| Gherkin tags | a line scan for `@` lines | the official Gherkin parser |
| SARIF output | `json` | a SARIF object-model package |
| Coverage, tests and mutants | `subprocess` running the repository's tools, `json` reading their reports | importing coverage.py and mutmut as libraries |
| Closest id for `orphaned` | `difflib` | an edit-distance package |

### L5 Three test tiers, with pytest-bdd for behavior

- Decision: one runner, pytest, over three tiers: `tests/unit/`,
  `tests/integration/`, and Gherkin features in `tests/features/` bound by
  pytest-bdd step modules in `tests/steps/`. A milestone's feature and step
  module share one snake_case slug, since the slug also names a Python module,
  and the milestone's exit command,
  `uv run pytest tests/steps/test_<milestone>.py`, passes exactly when its
  scenarios pass. `pyproject.toml` gains `pytest-bdd` in the
  `dev` extra and `bdd_features_base_dir = "tests/features"` under
  `[tool.pytest.ini_options]`.
- Alternatives considered: behave, a second runner outside pytest and its
  coverage report;
  the cookiecutter's Cucumber scaffold, which it emits under
  `tests/integration/` for TypeScript packages and which needs Node to test a
  Python package; pytest without Gherkin.
- Rationale: behavior features are the primary milestone gate, one per
  milestone, over integration and unit tiers
  ([[three-tier-testing-behavior-integration-unit-with-behavior-as-primary-gate]]),
  arranged as `unit/` and `integration/` with a shared `conftest.py`
  ([[python-testing-with-pytest-fixtures-parametrization-and-mocking]]). `04`
  writes each feature before its code
  ([[write-gherkin-before-code-not-after]]). The template's split into
  features, step definitions and fixtures carries over under the Python
  package, and each step module gives `iterative-build-loop` a milestone exit
  command.

### L6 Fixture repositories as plain files, with history built at test time

- Decision: seeded fixtures are plain repositories under `tests/fixtures/`,
  the fewest that cover the success criteria that the Success criteria section
  of `00` observes on a fixture. `tests/conftest.py` builds each one's history
  in `tmp_path`. Fixture files are data, so `pyproject.toml` gains a ruff
  `extend-exclude` for `tests/fixtures`, `tests/conftest.py` keeps them out of
  pytest's collection with `collect_ignore = ["fixtures"]`, and
  `.markdownlint-cli2.jsonc` ignores `packages/earnest/tests/fixtures/**`. CI
  then passes over the seeded defects, and pre-commit and the edit hook's
  `--fix` leave them as written.
- Alternatives considered: one fixture per success criterion; fixtures stored
  as git bundles; fixtures generated in test code.
- Rationale: a fixture with known defects and a known change makes each
  expected finding reviewable
  ([[e2e-test-plan-uses-real-sample-mrs-with-known-defects-as-golden-fixtures]]).
  `broken-links` needs one commit. Revisions, out-of-task, impact, approvals
  and override drift all need a base commit and a change, so they share
  `seeded-change`. Plain files keep each seeded defect in view at review, where
  a bundle holds it in binary and a generated fixture holds it in code. The
  units variant of `seeded-change` is a second history of the same files, built
  by `conftest.py` from the same files plus a `units/` overlay, so it adds no
  fixture directory.

### L7 Where the assessment record lives

- Decision: the record is `.earnest/assessment.json` at the root of the work
  tree, one JSON file written by the standard library (L4). The Reporter
  replaces it whole, by writing a temporary file in `.earnest/` and renaming it
  over the record. When Earnest creates `.earnest/` it writes
  `.earnest/.gitignore` holding `*`, so Git ignores the record by default; a
  repository that wants the record in its history deletes the marker and
  commits the file. `git.py` lists nothing under `.earnest/`, so the scanner and
  the assessment hash never read it, whether or not Git ignores it.
- Alternatives considered: the record inside the intent's record directory,
  beside the stage artifacts; the same path tracked from the start;
  `<git-common-dir>/earnest/assessment.json`; a tracked `bodies` file plus an
  ignored remainder; TOML or Markdown in place of JSON.
- Rationale: the work-tree root lies outside the sensor's `matches`, so a
  header write during a sensor run changes no artifact that AI-DLC watches. The
  marker inside `.earnest/` keeps the repository's own `.gitignore` untouched,
  keeps the tree clean after a gate and is reversible per repository. A fresh
  clone runs `earnest plan` from files in the repository alone, and `earnest
  check` prints `record: absent, body-hash baseline unavailable` where the
  record is missing and the index holds items, so the absence is visible; a CI
  job can restore `.earnest/`
  from a cache or an artifact written at the gate, and a repository that wants
  the baseline across clones tracks the record. JSON is the format the standard
  library both reads and writes, SARIF is JSON already, and the fork's Bun reads
  it natively; TOML has no standard-library writer, and a Markdown record would
  be scanned as a stage artifact. Linked worktrees each hold their own
  `.earnest/`.

## Scope (v1)

- This repository: the `earnest` package as the File and directory tree
  section draws it.
- The AI-DLC fork, changed at exactly the paths of the Fork delta section.
- Platforms: macOS and Linux.

## Future directions

- An editor language server (D5) that reads the index through `index.py`.
- Further host adapters, one file each under `adapters/`.
- The `earnest` sensor documented in the fork's `docs/` tree once the delta
  settles.
- A `publish` stage for the `earnest` package, so the fork installs a released
  version.

## Open questions

| Question | Owner | Resolved by |
| --- | --- | --- |
| The file format of `tests/fixtures/calibration/`: the ten requirements, their hand links and the maintainer's verdicts | maintainer | a revision of `01`, before the calibration gate runs |
| The fork repository's name and owner; this repository is `cajias/earnest` | maintainer | creating the fork |
| How the fork's sensor script finds the `earnest` command: an installed tool on the path, or a pinned invocation | maintainer | the milestone of `03` that wires the sensor |
| `01` replaces each unit's `source-manifest.json`, and seven upstream tools read it: `aidlc-attest.ts`, `aidlc-construction-checkpoints.ts`, `aidlc-log.ts`, `aidlc-review-brief.ts`, `aidlc-state.ts`, `aidlc-swarm.ts` and `aidlc-swarm-checkpoints.ts` in `core/tools/`. Keep writing it as AI-DLC input that Earnest never counts as evidence, or extend the Fork delta to those tools? | maintainer | a revision of `01` |
| Upstream artifacts the mapping table leaves unnamed: NFR Requirements' `scalability-requirements`, `reliability-requirements` and `tech-stack-decisions`, NFR Design's `scalability-design`, `reliability-design` and `logical-components`, and Build and Test's agent-written `cross-unit-traceability.md` | maintainer | a revision of `01` |
| User Stories keeps AI-DLC's `traceability` sensor, which finds requirement ids in `requirements.md` by the pattern `FR\d+(?:\.\d+)?`, while the adapted file names them like `req~fr1-2~1`. Keep the AI-DLC id in each item's prose, or move User Stories to `earnest`? | maintainer | a revision of `01` |
| Whether the fork holds the `earnest` sensor on through the per-intent `/aidlc --sensors off` and the `AIDLC_DISABLE_SENSORS=1` kill switch, which turn the sensors ceremony off under every scope | maintainer | a revision of `01` |
| Which upstream tests pin the bundled sensor ids, the dispatcher routes or a stage's `sensors:` list, and so change with the Fork delta; a search names `t86-sensor-manifest-schema`, `t227-tool-entrypoint-exports`, `t230-dispatcher-routes` and `t349-gate-sensor-reachability` in `tests/unit/`, and `t48` may pin the `audit-format.md` table | maintainer | the first run of upstream's suite on the fork |
| Whether the units variant of `seeded-change` is a second history built from a `units/` overlay, as L6 states, or a fourth fixture directory | maintainer | the task plan of M2b of `03` |
