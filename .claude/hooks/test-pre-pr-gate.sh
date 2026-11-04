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
check "non-JSON input blocks"         2 'not json'
PATH=/nonexistent "$BASH" "$gate" <<<"$(j 'git status' "$main")" 2>/dev/null
[ $? = 2 ] && echo "ok   no jq blocks" || { echo "FAIL no jq blocks"; fail=1; }
fresh "$main"; stale "$wt"
check "cwd fresh"                     0 "$(j 'gh pr create' "$main")"
check "cwd stale"                     2 "$(j 'gh pr create' "$wt")"
check "cd WT stale, cwd fresh"        2 "$(j "cd $wt && gh pr create" "$main")"
check "multi-line cd WT stale"        2 "$(j "cd $wt"$'\n'"gh pr create" "$main")"
check "cd stale after gh (stricter)"  2 "$(j "gh pr create && cd $wt" "$main")"
check "gh api POST pulls, cd stale"   2 "$(j "cd $wt && gh api repos/o/r/pulls -X POST" "$main")"
check "cd \"\$VAR\" blocks"           2 "$(j "cd \"\$WT\" && gh pr create" "$main")"
check "cd non-repo blocks"            2 "$(j "cd $plain && gh pr create" "$main")"
# $main/b fresh, $main/sub/b stale: the gate must not resolve b against $main.
for r in b sub/b; do git init -q "$main/$r" && g -C "$main/$r" commit -q --allow-empty -m x; done
fresh "$main/b"; stale "$main/sub/b"
check "chained relative cd blocks"    2 "$(j "cd sub && cd b && gh pr create" "$main")"
check "attached -fkey=val is a POST"  2 "$(j "gh api repos/o/r/pulls -fhead=x" "$wt")"
HOME=$wt check "bare cd checks HOME"  2 "$(j "cd && gh pr create" "$main")"
check "CDPATH blocks"                 2 "$(j "CDPATH=$main/sub cd b && gh pr create" "$main")"
check "zsh cd OLD NEW blocks"         2 "$(j "cd $main $wt && gh pr create" "$main")"
check "backslash in gh word"          2 "$(j 'gh \pr create' "$wt")"
check "backslash in pr word"          2 "$(j 'gh pr \create' "$wt")"
check "quoted cd keyword"             2 "$(j "\"cd\" $wt && gh pr create" "$main")"
check "single-quoted cd keyword"      2 "$(j "'cd' $wt && gh pr create" "$main")"
check "backslash mid gh word"         2 "$(j 'g\h pr create' "$wt")"
check "backslash mid create word"     2 "$(j 'gh pr cr\eate' "$wt")"
check "backslash mid cd word"         2 "$(j "c\\d $wt && gh pr create" "$main")"
check "quoted gh word"                2 "$(j '"gh" pr create' "$wt")"
check "quoted pr word"                2 "$(j "gh 'pr' create" "$wt")"
check "quoted create word"            2 "$(j 'gh pr "create"' "$wt")"
check "cd spliced with ''"            2 "$(j "c''d $wt && gh pr create" "$main")"
check "cd spliced with \"\""            2 "$(j "\"c\"d $wt && gh pr create" "$main")"
check "zsh chdir"                     2 "$(j "chdir $wt && gh pr create" "$main")"
CDPATH=$main/sub check "env CDPATH, relative cd" 2 "$(j "cd b && gh pr create" "$main")"
fresh "$wt"
check "cd WT fresh, cwd fresh"        0 "$(j "cd $wt && gh pr create" "$main")"
check "quoted body cd fresh"          0 "$(j "gh pr create --body 'see: cd $wt; then retry'" "$main")"
HOME=$t check "cd ~/wt expands"       0 "$(j "cd ~/wt; gh pr create" "$main")"
HOME=$t check "quoted ~ not expanded" 2 "$(j "cd \"~/wt\"; gh pr create" "$main")"
CDPATH=$main/sub check "env CDPATH, no cd"  0 "$(j 'gh pr create' "$main")"
stale "$main"
out=$(bash "$gate" <<<"$(j 'gh pr create' "$main")" 2>&1)
sha=$(git -C "$main" rev-parse HEAD)
case $out in *"$sha in $main"*) echo "ok   message names sha and dir" ;; *) echo "FAIL message: $out"; fail=1 ;; esac
exit $fail
