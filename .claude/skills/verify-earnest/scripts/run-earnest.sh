#!/usr/bin/env bash
# Run one earnest command inside a fixture repo and record the proof, with the exit code taken directly from `$?`.
#   run-earnest.sh <repo> <evidence-dir> <label> <earnest args...>
# Writes <evidence-dir>/<label>.{cmd,stdout,stderr,exit} and a copy of .earnest/assessment.json as <label>.record.json
# as it stands after the run (it may come from an earlier run). Honours EARNEST_JUDGE from the environment. Exits with earnest's own exit code.
set -uo pipefail

repo="${1:?usage: run-earnest.sh <repo> <evidence-dir> <label> <earnest args...>}"
out="${2:?evidence dir}"; label="${3:?label}"; shift 3
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
pkg=$(cd "$here/../../../../packages/earnest" && pwd)

mkdir -p "$out"
out=$(cd "$out" && pwd)
cd "$repo" || exit 2
printf 'EARNEST_JUDGE=%s uv run --quiet --project %s earnest %s\n' "${EARNEST_JUDGE:-<unset>}" "$pkg" "$*" > "$out/$label.cmd"
uv run --quiet --project "$pkg" earnest "$@" > "$out/$label.stdout" 2> "$out/$label.stderr"
code=$?
echo "$code" > "$out/$label.exit"
[ -f .earnest/assessment.json ] && cp .earnest/assessment.json "$out/$label.record.json"
echo "exit=$code stdout=$(wc -c < "$out/$label.stdout")B stderr=$(wc -c < "$out/$label.stderr")B"
exit "$code"
