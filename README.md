# earnest

Requirements traceability and verification for LLM-written code: EARS requirements in Markdown, traced to code and tests, judged for earnest implementation

## Getting Started

```bash
make install  # install all dependencies
make          # full build: install + build + lint + test
```

## Structure

```text
packages/     # all sub-projects
docs/         # documentation
```

## Development

| Command | Description |
| --- | --- |
| `make` | Full build (install + build + lint + test) |
| `make lint` | Lint all sub-projects |
| `make test` | Test all sub-projects |
| `make -C packages/<name> <target>` | Run target for single sub-project |
| `make package` | Package all distributable artifacts |

## Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```
