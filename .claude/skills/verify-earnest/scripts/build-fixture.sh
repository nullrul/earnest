#!/usr/bin/env bash
# Build or remove a committed earnest fixture repo, mirroring packages/earnest/tests/conftest.py.
#   build-fixture.sh base|units [overlay ...]   build under $TMPDIR/verify-earnest/scratch.XXXXXX, print the repo path
# Each overlay is committed on main. Only base, units and base+override were verified; other overlays are unverified,
# and conftest commits change and task on a new branch (commit_overlay, commit_task_change), which is not mirrored.
#   build-fixture.sh --clean <repo-path>        remove the scratch directory that build made (nothing else)
set -euo pipefail

ROOT="${TMPDIR:-/tmp}"; ROOT="${ROOT%/}/verify-earnest"
MARK=.verify-earnest-scratch
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SRC=$(cd "$here/../../../../packages/earnest/tests/fixtures/seeded-change" && pwd)
RECORD=aidlc/spaces/default/intents/260926-checkout

if [ "${1:-}" = "--clean" ]; then
  scratch=$(dirname "${2:?usage: --clean <repo-path>}")
  case "$scratch" in "$ROOT"/scratch.*) ;; *) echo "refusing: $scratch is not a scratch dir of this skill" >&2; exit 1 ;; esac
  [ -f "$scratch/$MARK" ] || { echo "refusing: no $MARK in $scratch" >&2; exit 1; }
  rm -rf "$scratch"; echo "removed $scratch"; exit 0
fi

variant="${1:?usage: build-fixture.sh base|units [overlay ...]}"; shift
case "$variant" in base|units) ;; *) echo "variant must be base or units" >&2; exit 2 ;; esac

mkdir -p "$ROOT"
scratch=$(mktemp -d "$ROOT/scratch.XXXXXX")
touch "$scratch/$MARK"
repo="$scratch/seeded-change"

# Same git isolation and pinned identity as conftest.py (_isolated_git, _IDENTITY).
for v in $(env | sed -n 's/^\(GIT_[A-Za-z_]*\)=.*/\1/p'); do [ "$v" = GIT_EXEC_PATH ] || unset "$v"; done
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 XDG_CONFIG_HOME=/dev/null GIT_ATTR_NOSYSTEM=1
export GIT_AUTHOR_NAME="Earnest Fixture" GIT_AUTHOR_EMAIL="fixture@example.com" GIT_AUTHOR_DATE="2026-09-26T12:00:00+00:00"
export GIT_COMMITTER_NAME="Earnest Fixture" GIT_COMMITTER_EMAIL="fixture@example.com" GIT_COMMITTER_DATE="2026-09-26T12:00:00+00:00"

# _OVERLAYS, anchored to the fixture root, plus bytecode. Must match conftest's _OVERLAYS.
EXCL=(--exclude=/change --exclude=/task --exclude=/units --exclude=/override --exclude=/override-change
      --exclude=/evidence --exclude=/evidence-units --exclude=/judge-verdicts.json --exclude=/evidence-verdicts.json
      --exclude=/stub-pass.json --exclude=/stub-fail.json --exclude=__pycache__ --exclude='*.pyc')
[ "$variant" = units ] && EXCL+=("--exclude=/$RECORD")
rsync -a "${EXCL[@]}" "$SRC/" "$repo/"
[ "$variant" = units ] && rsync -a --exclude=__pycache__ --exclude='*.pyc' "$SRC/units/aidlc/" "$repo/aidlc/"

cd "$repo"
git init -q -b main
git add -A
git commit -q --no-verify -m fixture

for overlay in "$@"; do
  [ -d "$SRC/$overlay" ] || { echo "no overlay $overlay" >&2; exit 2; }
  (cd "$SRC/$overlay" && find . -type f ! -name '*.pyc' ! -path '*/__pycache__/*' | sed 's|^\./||' | sort) > "$scratch/files"
  rsync -a --exclude=__pycache__ --exclude='*.pyc' "$SRC/$overlay/" "$repo/"
  xargs git add -- < "$scratch/files"
  git commit -q --no-verify -m "$overlay"
done
echo "$repo"
