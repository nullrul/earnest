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
wtgit=$(git -C "$wt" rev-parse --absolute-git-dir)
maingit=$(git -C "$main" rev-parse --absolute-git-dir)
fail=0
# check NAME EXPECTED_RC JSON
check() {
  CLAUDE_PROJECT_DIR=$main bash "$gate" <<<"$3" >/dev/null 2>&1; rc=$?
  if [ "$rc" = "$2" ]; then echo "ok   $1"; else echo "FAIL $1 (rc=$rc want $2)"; fail=1; fi
}
j() { jq -n --arg c "$1" --arg d "${2:-}" '{tool_input:{command:$c}} + (if $d=="" then {} else {cwd:$d} end)'; }

check "non-JSON input"            0 'not json'
check "ungated command"           0 "$(j 'git status')"
check "gated, main, no marker"    2 "$(j 'gh pr create --fill')"
check "gated, cd wt, no marker"   2 "$(j "cd $wt && gh pr create" "$main")"
git -C "$wt" rev-parse HEAD > "$wtgit/pre-pr-review"
check "cd wt &&, marker fresh"    0 "$(j "cd $wt && gh pr create" "$main")"
check "cd quoted ;, marker fresh" 0 "$(j "cd \"$wt\"; gh pr ready" "$main")"
check "cd relative to cwd"        0 "$(j "cd ../wt && gh pr create" "$main")"
check "cwd=wt, no cd"             0 "$(j 'gh pr create' "$wt")"
check "main still blocked"        2 "$(j 'gh pr create' "$main")"
echo stale > "$wtgit/pre-pr-review"
check "cd wt, marker stale"       2 "$(j "cd $wt && gh pr create" "$main")"
check "cwd=wt, marker stale"      2 "$(j 'gh pr create' "$wt")"
git -C "$main" rev-parse HEAD > "$maingit/pre-pr-review"
check "later cd after other cmd"  2 "$(j "git fetch && cd $wt && gh pr create" "$main")"
check "cd in subshell"            2 "$(j "(cd $wt && gh pr create)" "$main")"
check "last of two cds wins"      2 "$(j "cd $main && cd $wt && gh pr create" "$main")"
check "cd non-repo falls back to cwd" 2 "$(j "cd \$WT && gh pr create" "$wt")"
check "cd non-repo, cwd=main"     0 "$(j "cd $plain && gh pr create" "$main")"
check "cwd non-repo falls back to project" 0 "$(j 'gh pr create' "$plain")"
exit $fail
