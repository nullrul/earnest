# judge

`earnest check --judge` asks the judge whether each requirement is implemented and tested. The only model is the stub, `EARNEST_JUDGE=stub:<verdicts.json>`, which answers from a canned file. Answers are cached in the record.

## Sub-features

- `judge-verdicts` turns canned answers into `earnest/judge-not-satisfied` findings.
- `judge-uncalibrated` warns that the model has no passing calibration.
- `judge-cache` stores answers in `.earnest/assessment.json` and reuses them on a rerun.
- `judge-no-model` exits 2 when `EARNEST_JUDGE` is unset.
- `judge-missing-answer` exits 2 when the canned file lacks an answer.

## How to get to it (user POV)

- Run `EARNEST_JUDGE=stub:<verdicts.json> earnest check --judge` inside a committed repo.

## Driving it with run-earnest.sh

Preconditions: `build-fixture.sh base override` repo; `V=packages/earnest/tests/fixtures/seeded-change/judge-verdicts.json` as an absolute path; `export EARNEST_JUDGE=stub:$V`.

- **Run.** `run-earnest.sh "$REPO" "$EV" judge1 check --judge`. Exit `1`.
- **Findings.** `judge1.stdout` results are, in order: `earnest/judge-uncalibrated` (warning), `earnest/req-not-ears` (error, on `req~audit-log~1`, the reason for exit 1), `earnest/unplanned` (warning), `earnest/judge-not-satisfied` (warning, `tests/test_auth.py:6`, `req~rate-limit~1` tested). `judge1.stderr` starts `traced 100%, judged 33%, evidenced 0%` and ends `findings: 4, errors: 1`.
- **Cache.** `judge1.record.json` has `judge.cache` with two sha256 keys. A second run (`judge2`) exits `1` with a byte-identical `.stdout` (`rtk proxy diff` exit `0`).
- **No model.** `unset EARNEST_JUDGE`, then `run-earnest.sh "$REPO" "$EV" nojudge check --judge`. Exit `2`, empty stdout, stderr `earnest: earnest needs a model: set EARNEST_JUDGE to anthropic:<model> or stub:<path of a canned-verdict file>`.

## Gotchas

- The canned `judge-verdicts.json` is keyed to the `override` overlay. On a plain `base` repo the run exits 2 with `the stub model's file holds no answer to ... implemented`; that is a failed precondition, not a feature bug.
- Use only `stub:`; never an `anthropic:` model.
- The judge cache key includes the code and test regions, so editing either re-asks.
- The sha in the uncalibrated message is the stub file's hash and changes if the verdicts file changes.
