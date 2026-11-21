#!/usr/bin/env bash
set -uo pipefail

repo="${1:?usage: run-earnest.sh <repo> <evidence-dir> <label> <earnest args...>}"
out="${2:?evidence dir}"; label="${3:?label}"; shift 3
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
pkg=$(cd "$here/../../../../packages/earnest" && pwd)

mkdir -p "$out"
out=$(cd "$out" && pwd)
cd "$repo" || { echo "run-earnest: cannot enter $repo" >&2; exit 3; }
for v in $(env | sed -n 's/^\(GIT_[A-Za-z_]*\)=.*/\1/p'); do [ "$v" = GIT_EXEC_PATH ] || unset "$v"; done
rm -f "$out/$label.record.json"
{ printf 'cd %q && EARNEST_JUDGE=%s uv run --quiet --project %q earnest' "$repo" "${EARNEST_JUDGE:-<unset>}" "$pkg"; printf ' %q' "$@"; echo; } > "$out/$label.cmd"
uv run --quiet --project "$pkg" earnest "$@" > "$out/$label.stdout" 2> "$out/$label.stderr"
code=$?
echo "$code" > "$out/$label.exit"
[ -f .earnest/assessment.json ] && cp .earnest/assessment.json "$out/$label.record.json"
echo "exit=$code stdout=$(wc -c < "$out/$label.stdout")B stderr=$(wc -c < "$out/$label.stderr")B"
exit "$code"
