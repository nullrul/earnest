# M6 demo: the calibration gate

M6 adds `earnest calibrate <fixture>`, which runs the judge over ten requirements and compares its verdicts with the maintainer's, and the judge-uncalibrated gate: `earnest check --judge` raises `earnest/judge-uncalibrated` unless the record holds a passing calibration for the current model id and prompt hash.

> **SYNTHETIC fixture.** This demo runs on `packages/earnest/tests/fixtures/calibration-dev/`, which an agent wrote. It is not the SC4 calibration set, and a pass here is no SC4 evidence. The SC4 real-model run (`EARNEST_JUDGE=anthropic:claude-opus-5-5 uv run earnest calibrate tests/fixtures/calibration`, from `packages/earnest/`) is the maintainer's and is unrun. The demo uses the stub model only and never calls a real model.

## How to run

From the repository root, with `uv` and `git` installed:

```bash
bash docs/demo/m6-calibrate.sh
```

The script copies the fixture to a temporary directory, commits it there, runs the six steps below and deletes the directory. The output below is captured from a run.

## 1. A judge run before any calibration

No calibration exists yet, so `earnest check --judge` raises the `earnest/judge-uncalibrated` warning (UC8). The finding names the model id and the prompt hash, because a calibration binds to that pair. The run exits 1 here only because the fixture's own findings are present.

```text
== 1. A judge run before any calibration
check --judge exit: 1
.earnest/assessment.json:1: warning earnest/judge-uncalibrated: in scope: no passing calibration exists for the model stub:sha256:ab2a143ad3a33f00c283f730a9c21e58ca33b8de0c03305fa02d0c6379e07ca3 and the prompt sha256:22901574d53bdfcc716f8ba0742fddbfbbb379bde4aa9393028d49f2ce99bcfb: run earnest calibrate before relying on the judge's verdicts
```

## 2. Calibrating the stub model

`earnest calibrate .` asks the judge about all ten requirements and prints each verdict beside the maintainer's. Eight of ten match, which meets the pass line, so the exit code is 0 and the result is written to the calibration slot of the record. The slot holds the model id, the prompt hash, the match count and the verdict.

```text
== 2. Calibrate the stub model
calibration of stub:sha256:ab2a143ad3a33f00c283f730a9c21e58ca33b8de0c03305fa02d0c6379e07ca3 with the prompt sha256:22901574d53bdfcc716f8ba0742fddbfbbb379bde4aa9393028d49f2ce99bcfb
req~card-refusal~1   judge satisfied/satisfied  maintainer satisfied/satisfied  match
req~daily-cap~1      judge satisfied/satisfied  maintainer not-satisfied/satisfied  differs
    implemented judge: satisfied at src/meter.py:17: capped takes the smaller of the fare and the daily cap.
    implemented maintainer: not-satisfied at src/meter.py:17: capped lets a fare reach 25 dollars, above the twenty dollar cap.
req~entry-time~1     judge satisfied/satisfied  maintainer satisfied/satisfied  match
req~ev-discount~1    judge not-satisfied/satisfied  maintainer not-satisfied/satisfied  match
req~fare-rounding~1  judge satisfied/not-satisfied  maintainer satisfied/satisfied  differs
    tested judge: not-satisfied at tests/test_meter.py:47: test_fare_rounds_up checks one fare and never a fare already on a ten-cent step.
    tested maintainer: satisfied at tests/test_meter.py:47: test_fare_rounds_up checks the requirement.
req~full-sign~1      judge satisfied/satisfied  maintainer satisfied/satisfied  match
req~grace-period~1   judge satisfied/satisfied  maintainer satisfied/satisfied  match
req~lost-ticket~1    judge satisfied/not-satisfied  maintainer satisfied/not-satisfied  match
req~night-rate~1     judge satisfied/satisfied  maintainer satisfied/satisfied  match
req~receipt-total~1  judge satisfied/satisfied  maintainer satisfied/satisfied  match
matches: 8/10
pass
calibrate exit: 0
calibration slot: {"matches": 8, "model": "stub:sha256:ab2a143ad3a33f00c283f730a9c21e58ca33b8de0c03305fa02d0c6379e07ca3", "pass": true, "prompt": "sha256:22901574d53bdfcc716f8ba0742fddbfbbb379bde4aa9393028d49f2ce99bcfb", "total": 10}
```

## 3. The judge run after a passing calibration

The same judge run no longer raises `earnest/judge-uncalibrated`, since the record holds a pass for this model id and prompt hash (SC4 gate, UC8). The gate reads the record; it does not re-run the calibration.

```text
== 3. The judge run after a passing calibration
check --judge exit: 1
no earnest/judge-uncalibrated finding
```

## 4. A failing calibration at seven matches

A second stub model disagrees with the maintainer on a third requirement, giving 7/10 and exit 1. The slot holds the latest result, not the best one, so the earlier pass is replaced by this failure. The first model is therefore uncalibrated again.

```text
== 4. A failing calibration at seven matches
calibration of stub:sha256:e6164875282e3711950287ba47ef0061e79e643f066abd23a68b0728cd9076cc with the prompt sha256:22901574d53bdfcc716f8ba0742fddbfbbb379bde4aa9393028d49f2ce99bcfb
req~card-refusal~1   judge satisfied/satisfied  maintainer satisfied/satisfied  match
req~daily-cap~1      judge satisfied/satisfied  maintainer not-satisfied/satisfied  differs
    implemented judge: satisfied at src/meter.py:17: capped takes the smaller of the fare and the daily cap.
    implemented maintainer: not-satisfied at src/meter.py:17: capped lets a fare reach 25 dollars, above the twenty dollar cap.
req~entry-time~1     judge satisfied/satisfied  maintainer satisfied/satisfied  match
req~ev-discount~1    judge not-satisfied/satisfied  maintainer not-satisfied/satisfied  match
req~fare-rounding~1  judge satisfied/not-satisfied  maintainer satisfied/satisfied  differs
    tested judge: not-satisfied at tests/test_meter.py:47: test_fare_rounds_up checks one fare and never a fare already on a ten-cent step.
    tested maintainer: satisfied at tests/test_meter.py:47: test_fare_rounds_up checks the requirement.
req~full-sign~1      judge satisfied/satisfied  maintainer satisfied/satisfied  match
req~grace-period~1   judge not-satisfied/satisfied  maintainer satisfied/satisfied  differs
    implemented judge: not-satisfied at src/meter.py:47: fare charges a car that leaves at exactly ten minutes.
    implemented maintainer: satisfied at src/meter.py:47: fare meets the requirement.
req~lost-ticket~1    judge satisfied/not-satisfied  maintainer satisfied/not-satisfied  match
req~night-rate~1     judge satisfied/satisfied  maintainer satisfied/satisfied  match
req~receipt-total~1  judge satisfied/satisfied  maintainer satisfied/satisfied  match
matches: 7/10
fail
calibrate exit: 1
calibration slot: {"matches": 7, "model": "stub:sha256:e6164875282e3711950287ba47ef0061e79e643f066abd23a68b0728cd9076cc", "pass": false, "prompt": "sha256:22901574d53bdfcc716f8ba0742fddbfbbb379bde4aa9393028d49f2ce99bcfb", "total": 10}
check --judge exit: 1
.earnest/assessment.json:1: warning earnest/judge-uncalibrated: in scope: no passing calibration exists for the model stub:sha256:ab2a143ad3a33f00c283f730a9c21e58ca33b8de0c03305fa02d0c6379e07ca3 and the prompt sha256:22901574d53bdfcc716f8ba0742fddbfbbb379bde4aa9393028d49f2ce99bcfb: run earnest calibrate before relying on the judge's verdicts
```

## 5. A calibration of another model

Recalibrating the first model passes again (`calibrate exit: 0`), and a judge run under it is quiet: no `earnest/judge-uncalibrated` finding. A judge run under the second model is then uncalibrated. The finding names the second model's id: a pass for one model id never covers another. The record is also per repository, so this holds only in the repository whose record was written.

```text
== 5. A calibration of another model
calibrate exit: 0
check --judge exit: 1
no earnest/judge-uncalibrated finding
check --judge exit: 1
.earnest/assessment.json:1: warning earnest/judge-uncalibrated: in scope: no passing calibration exists for the model stub:sha256:e6164875282e3711950287ba47ef0061e79e643f066abd23a68b0728cd9076cc and the prompt sha256:22901574d53bdfcc716f8ba0742fddbfbbb379bde4aa9393028d49f2ce99bcfb: run earnest calibrate before relying on the judge's verdicts
```

## 6. Calibrate cannot run without a model

With no `EARNEST_JUDGE` set, `calibrate` cannot ask anything. It exits 2 with one line on stderr and writes nothing to the record.

```text
== 6. Calibrate cannot run without a model
earnest: earnest needs a model: set EARNEST_JUDGE to anthropic:<model> or stub:<path of a canned-verdict file>
calibrate exit: 2
```

## Known limits

- The record is per repository: a calibration quiets `--judge` only in the repository whose record it was written to.
- The slot holds one result, the latest. Calibrating a second model replaces the pass of the first.
- The slot binds the model id and the prompt hash, not the fixture's content. Editing the fixture after a pass leaves the judge calibrated until `calibrate` runs again.
- The match compares `result` alone, so a judge that is right for the wrong reason still matches. The SC4 gate stays unrun until the maintainer runs it on the real fixture.
