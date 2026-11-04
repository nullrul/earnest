#!/usr/bin/env bash
# PreToolUse(Bash) pre-PR review gate. Blocks `gh pr create|new|ready` and POSTs to
# `gh api .../pulls` unless <git-dir>/pre-pr-review holds HEAD of the checkout the
# command runs in (hook input .cwd, or the last `cd <path> &&|;`), so worktrees work.
# Speed bump, not a boundary. Not covered: `--head <branch>` / `-R <repo>` (the PR need
# not be the checked HEAD), chained relative cds, `cd -`, `~user`, backslash-escaped paths.
input=$(cat)
# Non-JSON input: jq fails, c is empty, nothing matches, exit 0.
# shellcheck disable=SC1003 # tr set is newline and backslash
c=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null | tr '\n\\' '  ')
gh='(^|[^A-Za-z0-9_-])gh[[:space:]]([^;&|]*[[:space:]])?'
if printf '%s' "$c" | grep -Eq "${gh}pr[[:space:]]+(create|new|ready)([^A-Za-z0-9_-]|\$)"; then :
elif printf '%s' "$c" | grep -Eq "${gh}api[[:space:]]" \
  && printf '%s' "$c" | grep -Eq "pulls([[:space:]\"'?]|\$)" \
  && printf '%s' "$c" | grep -Eiq "(-X|--method)[[:space:]=]*POST|[[:space:]](-f|-F|--field|--raw-field|--input)([[:space:]=]|\$)"; then :
else exit 0; fi

cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
cwd=${cwd:-$CLAUDE_PROJECT_DIR}
dir=$cwd
cdre='^[[:space:](]*cd[[:space:]]+("([^"]*)"|'"'([^']*)'"'|([^[:space:];&|"'"'"']+))[[:space:]]*(&&|;)'
# One line per command (split after && ; |), so each cd starts a line; take the last.
s=${c//&&/&&$'\n'}; s=${s//;/;$'\n'}; s=${s//|/|$'\n'}
last=$(printf '%s\n' "$s" | grep -oE "$cdre" | tail -n1)
if [[ $last =~ $cdre ]]; then
  p=${BASH_REMATCH[2]}${BASH_REMATCH[3]}${BASH_REMATCH[4]}
  # shellcheck disable=SC2088 # literal tilde match, expanded by hand
  case $p in "~") p=$HOME ;; "~/"*) p=$HOME/${p#"~/"} ;; esac
  case $p in /*) dir=$p ;; *) dir=$dir/$p ;; esac
fi
# Not a repo (or unreadable): fall back to the hook cwd, then the project checkout.
git -C "$dir" rev-parse --git-dir >/dev/null 2>&1 || dir=$cwd
git -C "$dir" rev-parse --git-dir >/dev/null 2>&1 || dir=$CLAUDE_PROJECT_DIR
cd "$dir" || exit 0
dir=$(pwd -P)
sha=$(git rev-parse --verify -q HEAD)
saved=$(cat "$(git rev-parse --absolute-git-dir)/pre-pr-review" 2>/dev/null)
[ -n "$sha" ] && [ "$saved" = "$sha" ] && exit 0
echo "Pre-PR review required for HEAD ${sha:-<no commits>} (checked $dir): run the /pre-pr-review skill (code-review, ponytail:ponytail-review, simplify, security-review on the branch diff), fix or answer findings, commit, then retry." >&2
exit 2
