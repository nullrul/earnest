#!/usr/bin/env bash
# Spike G live check for Task 7b of the M6 plan: ONE real `claude -p` call through the `claude-code:` backend, on one
# question of the synthetic `calibration-dev` fixture. It is the step before the 20-call SC4 run (issue #29).
#
# usage, from packages/earnest/, logged in to the provider Claude Code uses (Amazon Bedrock on the SC4 host):
#   EARNEST_JUDGE=claude-code:<model> bash ../../docs/superpowers/plans/2026-11-25-spikes/spike-g-live-check.sh
#
# It prints the harness, the argv, the NAMES (never the values) of the variables that reach `claude`, the exit and wall
# time, the `modelUsage` keys that answered, the token usage, the verdict beside the maintainer's, and the path of the
# raw `claude` stdout. Exit 0 when `claude` returned a verdict (whatever it was), 1 on a JudgeError (the model
# did not load, `claude` did not start or did not answer), 2 on a bad call, or a verdict with no `claude` call behind it.
# It reads and writes no record, and it calls the model once.
set -u
case "${EARNEST_JUDGE:-}" in
  claude-code:?*) ;;
  *) echo "set EARNEST_JUDGE=claude-code:<model>" >&2; exit 2 ;;
esac
[ -d tests/fixtures/calibration-dev ] || { echo "run from packages/earnest/" >&2; exit 2; }
exec uv run python - <<'PY'
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from earnest import adapters, git, judge, structural
from earnest.index import build_index

SUBJECT, KIND = "req~daily-cap~1", "implemented"
fixture = Path("tests/fixtures/calibration-dev").resolve()
index = build_index(adapters.scan(fixture, git.work_tree_files(fixture)))
(asked,) = [q for q in judge.questions(index, structural.traced(index)) if (q.subject, q.kind) == (SUBJECT, KIND)]
try:
    model = judge.load_model(os.environ["EARNEST_JUDGE"], fixture)
except judge.JudgeError as error:
    sys.exit(f"JudgeError: {error}")  # exit 1, one line, no traceback
out = Path(tempfile.mkdtemp(prefix="earnest-live-check-"))
print(f"model    {model.id}")

real_run, seen = subprocess.run, {}


def timed(argv, **kw):
    start = time.monotonic()
    seen.update(argv=argv, env=sorted(kw["env"]))  # recorded first, so a timeout or OSError still leaves the call
    try:
        seen["done"] = real_run(argv, **kw)
        return seen["done"]
    finally:
        seen["wall"] = time.monotonic() - start


subprocess.run = timed  # judge calls subprocess.run once per question, so this sees that one call
try:
    verdict = model.ask(asked)
except judge.JudgeError as error:
    print(f"JudgeError: {error}")
    status = 1
else:
    maintainer = judge.load_verdicts(fixture / "verdicts.json")[SUBJECT][KIND]
    print(f"verdict    {verdict}\nmaintainer {maintainer}\nmatch      {verdict.result == maintainer.result}")
    status = 0

if "argv" not in seen:
    print("no claude call was made")
    sys.exit(status or 2)
shown = ["<schema>" if arg.startswith("{") else arg for arg in seen["argv"]]
print(f"argv     {shown}\nenv names {seen['env']}")
if "done" not in seen:
    print(f"claude did not return (timeout or exec failure) wall={seen['wall']:.1f}s")
    sys.exit(status)
done = seen["done"]
print(f"claude exit={done.returncode} wall={seen['wall']:.1f}s stdout={len(done.stdout)}B stderr={len(done.stderr)}B")
(out / "claude-stdout.json").write_text(done.stdout)
(out / "claude-stderr.txt").write_text(done.stderr)
print(f"raw output in {out}")
try:
    reply = json.loads(done.stdout)
except ValueError:
    reply = {}
keys = ("modelUsage", "num_turns", "terminal_reason", "stop_reason", "is_error", "duration_ms", "total_cost_usd", "usage")
print(json.dumps({key: reply.get(key) for key in keys} if isinstance(reply, dict) else reply, indent=2))
sys.exit(status)
PY
