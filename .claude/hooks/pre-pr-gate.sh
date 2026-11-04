#!/usr/bin/env bash
# PreToolUse(Bash) pre-PR review gate. Blocks `gh pr create|new|ready` and POSTs to
# `gh api .../pulls` unless <git-dir>/pre-pr-review holds HEAD in every checkout the
# command may run in. No shell parsing: the candidates are the hook cwd plus the target
# of every `cd`/`pushd <word>` anywhere in the text. A target that is not an existing
# git checkout (`cd "$WT"`, `cd -`, `cd ~user`) blocks: use a literal path. Fail closed;
# a speed bump, not a boundary. Not covered: `--head <branch>` / `-R <repo>`, `eval`,
# `git -C`, and commands built at run time.
input=$(cat)
# Non-JSON input: jq fails, r is empty, nothing matches, exit 0.
r=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
r=${r//$'\\\n'/ } # join line continuations
c=${r//$'\n'/ }
gh='(^|[^A-Za-z0-9_-])gh[[:space:]]([^;&|]*[[:space:]])?'
pr='pr[[:space:]]+(create|new|ready)([^A-Za-z0-9_-]|$)'
pulls="pulls([[:space:]\"'?]|\$)"
post='(-X|--method)[[:space:]=]*[Pp][Oo][Ss][Tt]|[[:space:]](-f|-F|--field|--raw-field|--input)([[:space:]=]|$)'
[[ $c =~ ${gh}${pr} ]] || [[ $c =~ ${gh}api[[:space:]] && $c =~ $pulls && $c =~ $post ]] || exit 0

block() {
  echo "Pre-PR review required ($1): run the /pre-pr-review skill (code-review, ponytail:ponytail-review, simplify, security-review on the branch diff), fix or answer findings, commit, then retry." >&2
  exit 2
}
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
cwd=${cwd:-${CLAUDE_PROJECT_DIR:-$PWD}}
dirs=("$cwd")
cd_re='(^|[^A-Za-z0-9_.-])(cd|pushd)[[:space:]]+("([^"]*)"|'"'([^']*)'"'|([^[:space:];&|()<>]+))'
s=$r
while [[ $s =~ $cd_re ]]; do
  s=${s#*"${BASH_REMATCH[0]}"}
  p=${BASH_REMATCH[4]}${BASH_REMATCH[5]}${BASH_REMATCH[6]}
  # shellcheck disable=SC2088 # literal tilde match, expanded by hand
  case $p in "~") p=$HOME ;; "~/"*) p=$HOME/${p#"~/"} ;; esac
  case $p in /*) ;; *) p=$cwd/$p ;; esac
  dirs+=("$p")
done
for d in "${dirs[@]}"; do
  gd=$(git -C "$d" rev-parse --absolute-git-dir 2>/dev/null) ||
    block "$d is not a git checkout; cd to a literal path"
  sha=$(git -C "$d" rev-parse --verify -q HEAD)
  [ -n "$sha" ] && [ "$(cat "$gd/pre-pr-review" 2>/dev/null)" = "$sha" ] ||
    block "no review marker for HEAD ${sha:-<no commits>} in $d"
done
