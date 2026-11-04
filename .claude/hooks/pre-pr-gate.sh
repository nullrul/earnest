#!/usr/bin/env bash
# PreToolUse(Bash) pre-PR review gate. Blocks `gh pr create|new|ready` and POSTs to
# `gh api .../pulls` unless <git-dir>/pre-pr-review holds HEAD in every checkout the
# command may run in. No shell parsing: the candidates are the hook cwd plus the target
# of every `cd`/`pushd <word>` anywhere in the text. A relative target, or one that is not
# an existing git checkout (`cd "$WT"`, `cd -`), blocks: use a literal absolute path. Fail closed;
# a speed bump, not a boundary. Not covered: `--head <branch>` / `-R <repo>`, `eval`,
# `git -C`, and commands built at run time.
input=$(cat)
# Fail closed: no jq or non-JSON input blocks.
r=$(printf '%s' "$input" | jq -r '.tool_input.command // empty') || {
  echo "pre-PR gate: jq missing or input not JSON" >&2
  exit 2
}
r=${r//$'\\\n'/} # the shell deletes a line continuation: `c\<newline>d` runs cd
r=${r//\\/}        # the shell drops a backslash inside a word: `g\h` runs gh
c=${r//$'\n'/ }
c=${c//[\"\']/} # and quotes: `"gh" pr create`, `c''d`
gh='(^|[^A-Za-z0-9_-])gh[[:space:]]([^;&|]*[[:space:]])?'
pr='pr[[:space:]]+(create|new|ready)([^A-Za-z0-9_-]|$)'
pulls='pulls/?([^A-Za-z0-9_/-]|$)'
post='(-X|--method)[[:space:]=]*[Pp][Oo][Ss][Tt]|[[:space:]](-[fF]|--field|--raw-field|--input)'
[[ $c =~ ${gh}${pr} ]] || [[ $c =~ ${gh}api[[:space:]] && $c =~ $pulls && $c =~ $post ]] || exit 0

block() {
  echo "Pre-PR review required ($1): run the /pre-pr-review skill (code-review, ponytail:ponytail-review, simplify, security-review on the branch diff), fix or answer findings, commit, then retry." >&2
  exit 2
}
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
cwd=${cwd:-${CLAUDE_PROJECT_DIR:-$PWD}}
dirs=("$cwd")
[[ $c == *CDPATH* ]] && block "command sets CDPATH"
# Directory changes without cd: `env -C<dir>`, `env --chd=` (getopt abbreviation),
# `uv run --directory`, `GIT_DIR=`. Any token starting with these blocks.
[[ $c =~ (^|[[:space:]])(-C|--c|--dir)|GIT_(DIR|WORK_TREE)= ]] &&
  block "command changes directory without cd; cd to a literal path"
nl=$'\n'
# cd/pushd (keyword optionally quoted), then a target word or none (cd to $HOME).
cd_re='(^|[^A-Za-z0-9_.-])(cd|pushd|chdir)["'"'"']?([[:blank:]]+("([^"]*)"|'"'([^']*)'"'|([^[:space:];&|()<>]+))|[[:blank:]]*([;&|()<>'"$nl"']|$))'
end_re="^[[:blank:]]*([;&|()<>$nl]|\$)"
s=$r
k=0
while [[ $s =~ $cd_re ]]; do
  m=("${BASH_REMATCH[@]}")
  k=$((k + 1))
  s=${s#*"${m[0]}"}
  p=${m[5]}${m[6]}${m[7]}
  if [ -n "${m[4]}" ]; then
    # Anything else before the next separator (zsh `cd OLD NEW`, `cd "a"b`) is unresolvable.
    [[ $s =~ $end_re ]] || block "cd target followed by more text"
  else
    p=$HOME
  fi
  # shellcheck disable=SC2088 # literal tilde match, expanded by hand
  [ -n "${m[7]}" ] && case $p in "~") p=$HOME ;; "~/"*) p=$HOME/${p#"~/"} ;; esac
  # A relative cd may run any number of times (loop, function): only absolute targets are fixed.
  [[ $p == /* ]] || block "relative cd; use a literal absolute path"
  dirs+=("$p")
done
# A cd keyword the scan missed (spliced with quotes, `c''d`) blocks.
kw_re='(^|[^A-Za-z0-9_.-])(cd|pushd|chdir)([^A-Za-z0-9_.-]|$)'
kw() {
  local s=$1 n=0
  while [[ $s =~ $kw_re ]]; do
    s=${s#*"${BASH_REMATCH[0]}"}
    n=$((n + 1))
  done
  echo "$n"
}
[ $k -ge "$(kw "$c")" ] || block "cd spelled with quotes; write it plainly"
# A quote touching a cd keyword (`x"cd"`, `c''d`) blocks, so a miss cannot cancel a false hit.
q=${r//$'\n'/ }
[ "$(kw "${q//[\"\']/x}")" = "$(kw "$c")" ] || block "cd keyword touches a quote; write it plainly"
for d in "${dirs[@]}"; do
  gd=$(git -C "$d" rev-parse --absolute-git-dir 2>/dev/null) ||
    block "$d is not a git checkout; cd to a literal path"
  sha=$(git -C "$d" rev-parse --verify -q HEAD)
  [ -n "$sha" ] && [ "$(cat "$gd/pre-pr-review" 2>/dev/null)" = "$sha" ] ||
    block "no review marker for HEAD ${sha:-<no commits>} in $d"
done
