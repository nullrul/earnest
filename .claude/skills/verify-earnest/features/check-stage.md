# check-stage

`earnest check --stage <stage>` assesses one stage of the route, and `--intent <record dir>` picks the intent. A stage run writes a run header into the record.

## Sub-features

- `stage-run` checks the named stage and exits with the usual codes.
- `stage-record` writes `.earnest/assessment.json` with a header keyed `<record dir>/<stage>`.
- `stage-slug`: `--stage` also takes a stage's last path segment when it is unambiguous (`requirements-analysis`), and names the same header and hash.
- `stage-coverage`: the stage run also runs the repo's tests under pytest-cov and writes the map to `.earnest/coverage/<commit sha>` plus `<commit sha>.json`; the record's `coverage.commit` names that sha.
- `stage-bad-stage` exits 2 for a stage not on the route.
- `stage-bad-intent` exits 2 for an unknown record directory.

## How to get to it (user POV)

- Run `earnest check --stage inception/requirements-analysis` in a committed repo.
- Run `earnest check --stage <stage> --intent aidlc/spaces/default/intents/260926-checkout`.

## Driving it with run-earnest.sh

Preconditions: `build-fixture.sh base` repo at `89f3937`, `EARNEST_JUDGE` unset, no `.earnest/` yet.

- **Stage run.** `run-earnest.sh "$REPO" "$EV" stage check --stage inception/requirements-analysis`. Exit `0`; `stage.stdout` has no results; `stage.stderr` ends `findings: 0, errors: 0`.
- **Header line.** `stage.stderr` has `assessment aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis: sha256:341675c6b680d9c0d2557b501ea04d443f76b923bf4706155b84373f058c8ba7 (done)`.
- **Record.** `stage.record.json` has `runs` with the one key `aidlc/spaces/default/intents/260926-checkout/inception/requirements-analysis`, whose `hash` equals that sha256, `status` `done`, and `items` the three requirement ids; the top-level `bodies` key holds the same three.
- **Slug.** After the stage run, `run-earnest.sh "$REPO" "$EV" stageslug check --stage requirements-analysis`. Exit `0`, and `stageslug.stderr` has the same `assessment ...` header line.
- **Coverage.** After the stage run, `ls -A "$REPO/.earnest/coverage"` lists `89f3937ccb7ed781575a2955dbde2a52b1f3df29` and `89f3937ccb7ed781575a2955dbde2a52b1f3df29.json`, and `stage.record.json` has `coverage.commit` equal to `89f3937ccb7ed781575a2955dbde2a52b1f3df29`.
- **Bad stage.** `run-earnest.sh "$REPO" "$EV" badstage check --stage nope`. Exit `2`, empty stdout, stderr `earnest: nope is not a stage on the route: inception/requirements-analysis, construction/code-generation, construction/build-and-test`.
- **Bad intent.** `run-earnest.sh "$REPO" "$EV" badintent check --intent nope`. Exit `2`, empty stdout, stderr `earnest: no record directory nope: the record directories are aidlc/spaces/default/intents/260926-checkout`.

## Gotchas

- Exit 2 runs still copy a `.record.json` if an earlier run left `.earnest/`; read the `.exit` file, not the presence of the record.
- The `.earnest/` directory appears only after the stage run, so the bad-input runs do not create it on a fresh repo.
- The `hash` depends on the fixture bytes; if it differs, the doctor sha will differ too.
