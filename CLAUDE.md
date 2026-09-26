# earnest

Requirements traceability and verification for LLM-written code: EARS requirements in Markdown, traced to code and tests, judged for earnest implementation

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
make deploy       # deploy CDK infra and publish web-app bundles to GitHub Pages
make clean        # clean build artifacts
make lint-file    # lint one file: LINT_FILE=<path> make lint-file
```

### Single sub-project

```bash
make -C packages/<name> install
make -C packages/<name> build
make -C packages/<name> lint
make -C packages/<name> test
make -C packages/<name> package
```

## Structure

All sub-projects live under `packages/`. Each has its own Makefile with standardized targets: `install`, `build`, `lint`, `test`, `package`, `clean`.

```text
packages/         # all sub-projects
docs/             # documentation
```

## Language Toolchains

### TypeScript

- **Build**: `tsc` (SDKs, CDK infra), `vite build` (web apps)
- **Lint**: `eslint` (shared flat config `@lint-configs/eslint-config`), `knip` (dead code), `prettier` (formatting)
- **Test**: `vitest` with `@vitest/coverage-v8` (SDKs, web apps), `jest` with `ts-jest` (CDK infra)
- **Package manager**: pnpm workspaces (root `package.json`)

Web-app packages own their React lint rules in `packages/<name>/eslint.config.mjs`,
which extends the root config and adds the React, hooks, and jsx-a11y plugins plus
the TypeScript parser for `.tsx`. Do not move those rules to the root config —
SDK, infra, and service packages have no JSX.

### Python

- **Build**: `uv build` (hatchling backend)
- **Lint**: `ruff check` + `ruff format`, `mypy --strict`, `vulture` (dead code, >=80% confidence)
- **Test**: `pytest` with `pytest-cov` (>=80% coverage)
- **Package manager**: `uv` (standalone per sub-project)

### Rust

- **Build**: `cargo build` (SDKs), `cargo build --release` (CLIs)
- **Lint**: `cargo fmt --check`, `cargo clippy -- -D warnings` (pedantic + nursery)
- **Test**: `cargo test`, `cargo-tarpaulin` (coverage)
- **Package manager**: Cargo workspace (root `Cargo.toml`)

### Go

- **Build**: `go build` into `packages/<name>/bin/`
- **Lint**: `golangci-lint fmt --diff` (gofmt + goimports) and `golangci-lint run`
- **Test**: `go test -race -cover ./...`
- **Package manager**: Go workspace (root `go.work`)

The `.golangci.yml` thresholds deliberately match the ESLint and clippy ones:
cognitive complexity 15, cyclomatic 20, 80 lines and 30 statements per function,
nesting depth 4, 5 arguments. Keep them in sync when changing any of the three.

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

GitHub Actions pipeline (`.github/workflows/ci.yml`) stages: `lint` → `test` →
`build`. `lint-docs` runs `markdownlint-cli2` and `yamllint` over the whole
repo as a backstop for `git commit --no-verify`. Nothing is published,
uploaded or deployed yet — add a `publish` stage once there is a package
worth releasing.
