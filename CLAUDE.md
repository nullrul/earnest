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

`make` (install + build + lint + test), or one target: `install`, `build`, `lint`, `test`,
`package`, `clean`. `LINT_FILE=<path> make lint-file` lints one file. The only sub-project is
`packages/earnest` (Python 3.12+, `uv`); its settings live in its `pyproject.toml`.

Single test or scenario, from `packages/earnest`:

```bash
uv run pytest tests/unit/test_ears.py::<test_name>
uv run pytest tests/steps/test_judge_check.py -k "<scenario title>"
```

Any warning fails a test (`filterwarnings = error`). Coverage runs only under `make test`.

## Architecture

`uv run earnest check` (from `packages/earnest`, or `uv run --project packages/earnest` from the
root) writes SARIF to stdout and a summary to stderr. It exits 1 only for an
error-level finding at plan position behind or current, and 2 when it cannot run. `cli.py` reads
(git → adapters → intents), then analyses (index → trace levels → judge → plan stages →
structural and EARS checks, placed on the plan), then reports.
Module detail is in `docs/design/02-structural-design.md`, milestones in
`docs/design/03-implementation-plan.md`.

Non-obvious rules:

- An override sha resolves by object, never by ref (`git rev-parse --disambiguate`).
- Any `aidlc-state.md` in the work tree marks an intent.
- The judge's only model is `EARNEST_JUDGE=stub:<verdicts.json>`. Its cache key includes the code
  and test regions, so editing either re-asks.
- `tests/conftest.py` pins the git identity and dates so fixture commit shas stay stable.

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
