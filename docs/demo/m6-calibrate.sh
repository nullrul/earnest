#!/usr/bin/env bash
# M6 demo: the calibration gate, against the SYNTHETIC calibration-dev fixture and the stub model only.
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PKG="$here/../../packages/earnest"
FIXTURE="$PKG/tests/fixtures/calibration-dev"

earnest() { uv run --quiet --project "$PKG" earnest "$@"; }

# Same identity as _IDENTITY in tests/conftest.py; user hooks and signing stay off.
export GIT_AUTHOR_NAME="Earnest Fixture" GIT_AUTHOR_EMAIL="fixture@example.com" GIT_AUTHOR_DATE="2026-09-26T12:00:00+00:00"
export GIT_COMMITTER_NAME="Earnest Fixture" GIT_COMMITTER_EMAIL="fixture@example.com" GIT_COMMITTER_DATE="2026-09-26T12:00:00+00:00"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/out"
cp -R "$FIXTURE" "$tmp/calibration-dev"
rm -f "$tmp"/calibration-dev/stub-*.json
cd "$tmp/calibration-dev"
git init -q -b main
git add -A
git commit -q --no-verify -m fixture

PASS="stub:$FIXTURE/stub-pass.json"
FAIL="stub:$FIXTURE/stub-fail.json"

judge_run() {
  local code=0
  EARNEST_JUDGE=$1 earnest check --judge > "$tmp/out/sarif.json" 2> "$tmp/out/summary.txt" || code=$?
  echo "check --judge exit: $code"
  grep 'earnest/judge-uncalibrated' "$tmp/out/summary.txt" || echo "no earnest/judge-uncalibrated finding"
}

show_slot() {
  python3 -c 'import json;print("calibration slot:", json.dumps(json.load(open(".earnest/assessment.json"))["calibration"], sort_keys=True))' \
    2>&1 || true
}

calibrate() {
  local code=0
  EARNEST_JUDGE=$1 earnest calibrate . || code=$?
  echo "calibrate exit: $code"
}

echo "== 1. A judge run before any calibration"
judge_run "$PASS"

echo "== 2. Calibrate the stub model"
calibrate "$PASS"
show_slot

echo "== 3. The judge run after a passing calibration"
judge_run "$PASS"

echo "== 4. A failing calibration at seven matches"
calibrate "$FAIL"
show_slot
judge_run "$PASS"

echo "== 5. A calibration of another model"
calibrate "$PASS" > /dev/null
judge_run "$FAIL"

echo "== 6. Calibrate cannot run without a model"
code=0
env -u EARNEST_JUDGE uv run --quiet --project "$PKG" earnest calibrate . || code=$?
echo "calibrate exit: $code"

echo "== done"
