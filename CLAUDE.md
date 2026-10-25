# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**earnest**: requirements traceability and verification for LLM-written code: EARS requirements in Markdown, traced to code and tests, judged for earnest implementation.

## Working model

- Act as an orchestrator. Decompose work, delegate each piece to a subagent, verify what comes back, then report. Do not write code or investigate at length yourself when a subagent can do it; read files only to verify.
- Pick each subagent's model by consequence if wrong, not task size: `haiku` for mechanical work with self-evident output (run a command, rename, reformat); `sonnet` for bounded work against a spec (implement a stub, write tests, draft docs); `opus` for design decisions, infra, adversarial review, or when the agent is the only check on a result. Always set the model explicitly.
- Spawn independent subagents in one message so they run in parallel. Give each a narrow scope, the paths it owns, and the evidence it must return.
- Track all work in the Task List: create a task per work item before dispatching, mark it in progress when its agent starts, and completed only after you have verified the agent's evidence. Keep the list current as scope changes; add follow-ups as new tasks.
- Never let a subagent `rm` a path it did not create. Say so in every delegation prompt.
- When an exit code is the evidence, run `rtk proxy <cmd>` and capture `$?` yourself; RTK filtering can make a red run look green.

## Build

```bash
make              # install + build + lint + test (all sub-projects)
make install      # install dependencies for all sub-projects
make build        # build all sub-projects
make lint         # lint all sub-projects
make test         # test all sub-projects
make package      # package distributable artifacts
make deploy       # root-only no-op: nothing is deployable yet
make clean        # clean build artifacts
make lint-file    # lint one file: LINT_FILE=<path> make lint-file
```

The only sub-project is `packages/earnest`, a Python 3.12+ package: `uv`, hatchling, no runtime
dependencies. Lint is `ruff check` + `ruff format --check` (line length 120, max complexity 10),
`mypy` strict, and `vulture` (min confidence 80). Run targets for it with `make -C packages/earnest <target>`.

Run single tests from `packages/earnest`. Ad-hoc `uv run` needs `--all-extras`; without it the
dev extras (pytest 9, pytest-bdd) are missing and collection fails:

```bash
uv run --all-extras pytest tests/unit/test_ears.py::<test_name> --no-cov
uv run --all-extras pytest tests/steps/test_judge_check.py -k "<scenario title>" --no-cov
uv run --all-extras earnest check [--stage S] [--intent DIR] [--task ID] [--judge]
```

`filterwarnings = error`: any warning fails a test. Coverage is on by default with no threshold (`--no-cov` silences it).

## Architecture

`earnest check` writes SARIF 2.1.0 to stdout and a summary to stderr. Exit codes: 1 means an
error-level finding sits at plan position behind or current, 0 means none does (errors at later
stages do not fail), 2 means the check could not run. `earnest plan` prints
the stage plan. The pipeline lives in `cli.py`:

1. `git.py` finds the repo root, HEAD, work-tree files and changed lines.
2. `adapters/` pick a scanner by file suffix and pass lines to the grammar: Gherkin `@` tags,
   Python `#` comments, TypeScript comments, and every Markdown line (lines inside code fences
   are marked as fenced).
3. `index.py` holds the link grammar (`Needs`, `Covers`, `Drivers`, `Delivers`, `Depends`,
   `Override`) and builds items, links and near-misses. An `Override:` line sits under the item it names.
4. `plan.py` is the AI-DLC stage engine. It reads an intent's `aidlc-state.md`, the audit shards,
   the approvals and the units. Any `aidlc-state.md` in the work tree marks an intent; the fixtures
   use `aidlc/spaces/<space>/intents/<id>/{inception,construction,audit}/`.
5. `structural.py` runs the link checks that need no model and sets trace levels. `ears.py`
   parses EARS clauses.
6. `judge/` asks one question per traced requirement. `EARNEST_JUDGE` names the model, and only
   `stub:<verdicts.json>` exists so far. Verdicts are cached, keyed by the item, question kind,
   code-region and test-region hashes, model id, and the hash of `judge/prompt.txt`, so editing the
   code or tests re-asks.
7. `reporter.py` builds the SARIF output and reads and writes the record in
   `.earnest/assessment.json` (atomic write). `impact.py` keeps a pytest coverage map in
   `.earnest/coverage/<commit>` for `check --stage`.

Invariants:

- An override sha resolves by object, never by ref: `git rev-parse --disambiguate`, at least 4 hex
  digits, exactly one commit.
- Rule ids are `earnest/<rule>`.

Tests:

- `tests/unit`, `tests/integration`, `tests/features/*.feature` (bound in `tests/steps`), and
  fixture repos in `tests/fixtures`.
- `conftest.py` pins the git author, committer and dates so fixture commit shas stay stable, and
  it strips `GIT_*` env and global config.
- The five feature files match milestones M1, M2, M2b, M3 and M4 in `docs/design/03-implementation-plan.md`. Each
  milestone has a plan in `docs/superpowers/plans/`. `docs/design/00-04` hold the intent, logic,
  structural, plan and BDD docs.

## Project hooks

`.claude/settings.json` wires these hooks:

- PostToolUse on Edit/Write/MultiEdit: runs `LINT_FILE=<path> make lint-file`
  on any `.py`, `.md`, `.yml`/`.yaml`, or `.sh` file touched inside the repo.
  Paths outside the repo, or with characters outside `[A-Za-z0-9._/-]` or a
  `..`, are skipped. The path travels only through the environment, never as a
  make variable, so it cannot inject shell or make code. Symlinks are skipped.
  Bash heredoc writes bypass this hook; the git pre-commit hook still catches
  those.
- PostToolUse on Agent: reminds the orchestrator to update the Task List and
  dispatch the next pending task after a subagent finishes.
- PreToolUse on Bash, pre-PR review gate: blocks `gh pr create`/`new`/`ready`
  (any path to `gh`, global flags such as `-R`, env prefixes, `bash -c`,
  subshells) and POSTs to `gh api .../pulls`, unless `$(git rev-parse --git-dir)/pre-pr-review` holds the current HEAD sha
  (works in worktrees). Run the `/pre-pr-review` skill, then retry. It is a
  best-effort speed bump (GraphQL `createPullRequest` or `eval` tricks get past
  it); real enforcement would be a branch-protection required check.
- Stop: prints `git status --short` and `git diff --stat`.

The git `pre-commit` hook (config `.pre-commit-config.yaml`) is the real guard:
`ruff check`/`ruff format` and `mypy --strict` on the Python package, `vulture`
dead-code check, `markdownlint` on staged Markdown, `yamllint` on staged YAML.
Install it once with `pip install pre-commit && pre-commit install` (see
README). Formatting hooks rewrite files in place and fail the commit on
purpose; re-stage and commit again.

## Docs and config

Markdown is linted with `markdownlint-cli2` (MD013 off, config
`.markdownlint-cli2.jsonc`), YAML with `yamllint` (config `.yamllint.yml`).

## CI/CD

GitHub Actions pipeline (`.github/workflows/ci.yml`) jobs: `lint-python` → `test-python` →
`build-earnest`. `lint-docs` runs `markdownlint-cli2` and `yamllint` over the whole
repo as a backstop for `git commit --no-verify`. Nothing is published,
uploaded or deployed yet — add a `publish` stage once there is a package
worth releasing.
