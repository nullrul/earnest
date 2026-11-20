# plan

`earnest plan` prints the route for each intent: every stage's status and approval, the frontier, and the tasks. It emits the same SARIF envelope as `check`, with the plan under `runs[0].properties.plan`.

## Sub-features

- `plan-route` lists the stages in route order with status and approval.
- `plan-frontier` names the first stage not done.
- `plan-tasks` lists each task and whether it is done.
- `plan-no-record` writes no `.earnest/`.

## How to get to it (user POV)

- Run `uv run --quiet --project <repo>/packages/earnest earnest plan` inside a committed repo that holds an AI-DLC record.

## Driving it with run-earnest.sh

Preconditions: `build-fixture.sh base` repo at `89f3937`, `EARNEST_JUDGE` unset.

- **Run.** `run-earnest.sh "$REPO" "$EV" plan plan`. Exit `0`.
- **Route.** `plan.stderr` has, in order, `inception/requirements-analysis: done, approval current, human`, `construction/code-generation: not done, approval none`, `construction/build-and-test: not done, approval none`.
- **Frontier and tasks.** `plan.stderr` has `frontier: construction/code-generation`, `task task~add-limiter~1: not done`, `task task~notify-lockout~1: not done`.
- **SARIF.** `plan.stdout` `runs[0].properties.plan.intents[0].frontier` is `construction/code-generation`, with three `stages` and two `tasks`; `results` holds one `earnest/unplanned` warning.
- **No record.** `ls -a "$REPO"` shows no `.earnest/`, and `plan.record.json` is not written by the helper.

## Gotchas

- A `plan` run following a `check --stage` run in the same repo sees the earlier `.earnest/`; start from a fresh build for the no-record step.
- The base build has an empty `plan.units` array; the `units` build was not driven for this map.
