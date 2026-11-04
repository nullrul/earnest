#!/usr/bin/env bash
# PreToolUse(Bash) pre-PR review gate. Blocks `gh pr create|new|ready` and POSTs to
# `gh api .../pulls` unless <git-dir>/pre-pr-review holds HEAD of the checkout the
# command runs in (hook input .cwd, or a leading `cd <path> &&|;`), so worktrees work.
input=$(cat)
printf '%s' "$input" | python3 -c 'import json,sys; json.load(sys.stdin)' >/dev/null 2>&1 || exit 0
# shellcheck disable=SC1003 # tr set is newline and backslash
c=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' | tr '\n\\' '  ')
gh='(^|[^A-Za-z0-9_-])gh[[:space:]]([^;&|]*[[:space:]])?'
if printf '%s' "$c" | grep -Eq "${gh}pr[[:space:]]+(create|new|ready)([^A-Za-z0-9_-]|\$)"; then :
elif printf '%s' "$c" | grep -Eq "${gh}api[[:space:]]" \
  && printf '%s' "$c" | grep -Eq "pulls([[:space:]\"'?]|\$)" \
  && printf '%s' "$c" | grep -Eiq "(-X|--method)[[:space:]=]*POST|[[:space:]](-f|-F|--field|--raw-field|--input)([[:space:]=]|\$)"; then :
else exit 0; fi

dir=$(printf '%s' "$input" | jq -r '.cwd // empty')
dir=${dir:-$CLAUDE_PROJECT_DIR}
cdre='^[[:space:]]*cd[[:space:]]+("([^"]*)"|'"'([^']*)'"'|([^[:space:];&|"'"'"']+))[[:space:]]*(&&|;)'
if [[ $c =~ $cdre ]]; then
  p=${BASH_REMATCH[2]}${BASH_REMATCH[3]}${BASH_REMATCH[4]}
  # shellcheck disable=SC2088 # literal tilde match, expanded by hand
  case $p in "~") p=$HOME ;; "~/"*) p=$HOME/${p#"~/"} ;; esac
  case $p in /*) dir=$p ;; *) dir=$dir/$p ;; esac
fi
# Not a repo (or unreadable): fall back to the project checkout.
git -C "$dir" rev-parse --git-dir >/dev/null 2>&1 || dir=$CLAUDE_PROJECT_DIR
cd "$dir" || exit 0
dir=$(pwd -P)
sha=$(git rev-parse --verify -q HEAD)
saved=$(cat "$(git rev-parse --absolute-git-dir)/pre-pr-review" 2>/dev/null)
[ -n "$sha" ] && [ "$saved" = "$sha" ] && exit 0
echo "Pre-PR review required for HEAD ${sha:-<no commits>} (checked $dir): run the /pre-pr-review skill (code-review, ponytail:ponytail-review, simplify, security-review on the branch diff), fix or answer findings, commit, then retry." >&2
exit 2
