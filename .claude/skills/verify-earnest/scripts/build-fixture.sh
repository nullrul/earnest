#!/usr/bin/env bash
set -euo pipefail

ROOT="${TMPDIR:-/tmp}"; ROOT="${ROOT%/}/verify-earnest"
MARK=.verify-earnest-scratch
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SRC=$(cd "$here/../../../../packages/earnest/tests/fixtures/seeded-change" && pwd)
RECORD=aidlc/spaces/default/intents/260926-checkout

if [ "${1:-}" = "--clean" ]; then
  # Resolve both sides physically (symlinks, ..): on macOS /var is /private/var, so one side alone breaks.
  root=$(cd -P "$ROOT" 2>/dev/null && pwd -P) || { echo "refusing: $ROOT does not exist" >&2; exit 1; }
  scratch=$(cd -P "$(dirname "${2:?usage: --clean <repo-path>}")" 2>/dev/null && pwd -P) || { echo "refusing: cannot resolve the parent of $2" >&2; exit 1; }
  rest=${scratch#"$root"/}
  case "$rest" in scratch.*/*) rest= ;; scratch.*) ;; *) rest= ;; esac
  [ -n "$rest" ] || { echo "refusing: $scratch is not a scratch dir of this skill" >&2; exit 1; }
  [ -f "$scratch/$MARK" ] || { echo "refusing: no $MARK in $scratch" >&2; exit 1; }
  rm -rf "$scratch"; echo "removed $scratch"; exit 0
fi

variant="${1:?usage: build-fixture.sh base|units [overlay ...] | --clean <repo-path>}"; shift
case "$variant" in base|units) ;; *) echo "variant must be base or units" >&2; exit 2 ;; esac

seen=" "
for overlay in "$@"; do
  case "$variant:$overlay" in base:override|base:override-change|base:evidence|units:evidence-units) ;;
    *) echo "overlay $overlay is not one conftest commits on main for $variant (base: override, override-change, evidence; units: evidence-units)" >&2; exit 2 ;; esac
  case "$seen" in *" $overlay "*) echo "overlay $overlay given twice" >&2; exit 2 ;; esac
  [ "$overlay" != override-change ] || case "$seen" in *" override "*) ;; *) echo "override-change goes on top of override" >&2; exit 2 ;; esac
  seen="$seen$overlay "
done

mkdir -p "$ROOT"
scratch=$(mktemp -d "$ROOT/scratch.XXXXXX")
touch "$scratch/$MARK"
trap 'rm -rf "$scratch"' ERR
repo="$scratch/seeded-change"

for v in $(env | sed -n 's/^\(GIT_[A-Za-z_]*\)=.*/\1/p'); do [ "$v" = GIT_EXEC_PATH ] || unset "$v"; done
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 XDG_CONFIG_HOME=/dev/null GIT_ATTR_NOSYSTEM=1
export GIT_AUTHOR_NAME="Earnest Fixture" GIT_AUTHOR_EMAIL="fixture@example.com" GIT_AUTHOR_DATE="2026-09-26T12:00:00+00:00"
export GIT_COMMITTER_NAME="Earnest Fixture" GIT_COMMITTER_EMAIL="fixture@example.com" GIT_COMMITTER_DATE="2026-09-26T12:00:00+00:00"

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
  rsync -a --exclude=__pycache__ --exclude='*.pyc' "$SRC/$overlay/" "$repo/"
  git add -A
  git commit -q --no-verify -m "$overlay"
done
echo "$repo"
