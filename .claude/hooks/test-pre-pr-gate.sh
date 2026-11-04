#!/usr/bin/env bash
# Tests for pre-pr-gate.sh. Run: bash .claude/hooks/test-pre-pr-gate.sh
set -u
# Isolate fixtures from the user's git config (gpgsign, hooksPath, ...).
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
gate="$(cd "$(dirname "$0")" && pwd)/pre-pr-gate.sh"
t=$(mktemp -d "${TMPDIR:-/tmp}/prgate.XXXXXX"); trap 'rm -rf "$t"' EXIT
g() { git -c user.name=t -c user.email=t@t "$@"; }
main="$t/main"; wt="$t/wt"; plain="$t/plain"
git init -q "$main" && g -C "$main" commit -q --allow-empty -m init
g -C "$main" worktree add -q -b feat "$wt"
g -C "$wt" commit -q --allow-empty -m work
mkdir "$plain"
fresh() { git -C "$1" rev-parse HEAD > "$(git -C "$1" rev-parse --absolute-git-dir)/pre-pr-review"; }
stale() { echo stale > "$(git -C "$1" rev-parse --absolute-git-dir)/pre-pr-review"; }
fail=0
# check NAME EXPECTED_RC JSON
check() {
  CLAUDE_PROJECT_DIR=$main bash "$gate" <<<"$3" >/dev/null 2>&1; rc=$?
  if [ "$rc" = "$2" ]; then echo "ok   $1"; else echo "FAIL $1 (rc=$rc want $2)"; fail=1; fi
}
j() { jq -n --arg c "$1" --arg d "${2:-}" '{tool_input:{command:$c}} + (if $d=="" then {} else {cwd:$d} end)'; }

check "ungated command"               0 "$(j 'git status' "$main")"
check "non-JSON input"                0 'not json'
fresh "$main"; stale "$wt"
check "cwd fresh"                     0 "$(j 'gh pr create' "$main")"
check "cwd stale"                     2 "$(j 'gh pr create' "$wt")"
check "cd WT stale, cwd fresh"        2 "$(j "cd $wt && gh pr create" "$main")"
check "multi-line cd WT stale"        2 "$(j "cd $wt"$'\n'"gh pr create" "$main")"
check "cd stale after gh (stricter)"  2 "$(j "gh pr create && cd $wt" "$main")"
check "gh api POST pulls, cd stale"   2 "$(j "cd $wt && gh api repos/o/r/pulls -X POST" "$main")"
check "cd \"\$VAR\" blocks"           2 "$(j "cd \"\$WT\" && gh pr create" "$main")"
check "cd non-repo blocks"            2 "$(j "cd $plain && gh pr create" "$main")"
fresh "$wt"
check "cd WT fresh, cwd fresh"        0 "$(j "cd $wt && gh pr create" "$main")"
check "quoted body cd fresh"          0 "$(j "gh pr create --body 'see: cd \"$wt\" first'" "$main")"
HOME=$t check "cd ~/wt expands"       0 "$(j "cd ~/wt; gh pr create" "$main")"
stale "$main"
out=$(bash "$gate" <<<"$(j 'gh pr create' "$main")" 2>&1)
sha=$(git -C "$main" rev-parse HEAD)
case $out in *"$sha in $main"*) echo "ok   message names sha and dir" ;; *) echo "FAIL message: $out"; fail=1 ;; esac
exit $fail
