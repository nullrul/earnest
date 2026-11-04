#!/usr/bin/env bash
# PreToolUse(Bash) pre-PR review gate. Blocks `gh pr create|new|ready` and POSTs to
# `gh api .../pulls` unless <git-dir>/pre-pr-review holds HEAD in every checkout the
# command could run in. Text order is not shell order (heredocs, quoted separators), so
# the candidates are a superset: the hook cwd (or the target of a leading `cd X &&|;|\n`),
# plus every cd/pushd target anywhere in the command, relative ones resolved against
# every earlier candidate. Missing dirs and non-repos are skipped; no repo at all, or a
# cd target the shell would expand (`$`, backtick, glob, `~user`, `-`, `popd`, none),
# fails closed. Speed bump, not a boundary. Not covered: `--head <branch>` / `-R <repo>`
# (the PR need not be the checked HEAD), `env -C <dir> gh ...`, cd hidden by eval/functions.
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
  echo "Pre-PR review required (checked $1): run the /pre-pr-review skill (code-review, ponytail:ponytail-review, simplify, security-review on the branch diff), fix or answer findings, commit, then retry." >&2
  exit 2
}
arg='("([^"]*)"|'"'([^']*)'"'|([^[:space:];&|"'"'"']+))'
# target DQ SQ BARE: set p to the cd target, or block when the shell would expand it.
target() {
  p=$1$2$3
  case $p in -* | "~"[!/]*) block "unparsed cd target: $p" ;; esac
  [[ $p == *[\$\`]* || $3 == *[*?[]* ]] && block "unparsed cd target: $p"
  # shellcheck disable=SC2088 # literal tilde match, expanded by hand
  case $3 in "~") p=$HOME ;; "~/"*) p=$HOME/${3#"~/"} ;; esac # bash expands ~ only unquoted
}
# add P: P, or P under each candidate when relative, for each such dir that exists.
add() {
  local d new=()
  case $1 in /*) new=("$1") ;; *) for d in "${dirs[@]}"; do new+=("$d/$1"); done ;; esac
  for d in "${new[@]}"; do [ -d "$d" ] && dirs+=("$d"); done
  ((${#dirs[@]} <= 32)) || block "too many cd targets"
}
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
dirs=("${cwd:-$PWD}")
# A leading cd runs before anything else, so it replaces the cwd (when it can succeed).
lead='^[[:space:]]*(cd|pushd)[[:space:]]+'"$arg"'[[:space:]]*(&&|;|'$'\n'')'
if [[ $r =~ $lead ]]; then
  m=${BASH_REMATCH[0]}
  target "${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}" "${BASH_REMATCH[5]}"
  case $p in /*) ;; *) p=${dirs[0]}/$p ;; esac
  [ -d "$p" ] && dirs=("$p")
  r=${r#"$m"}
fi
pre='^([[:space:](){!]|(then|do|else)[[:space:]])*'
s=${r//&/"&"$'\n'}; s=${s//;/";"$'\n'}; s=${s//|/"|"$'\n'} # quoted: bash 5.2 expands & in replacements
while IFS= read -r line; do
  [[ $line =~ ${pre}(cd|pushd|popd)([[:space:]]|$) ]] || continue
  [[ $line =~ ${pre}(cd|pushd)[[:space:]]+${arg}[[:space:]]*[\;\&\|]?[[:space:]]*$ ]] || block "unparsed cd: $line"
  target "${BASH_REMATCH[5]}" "${BASH_REMATCH[6]}" "${BASH_REMATCH[7]}"
  add "$p"
done <<<"$s"
found=
for d in "${dirs[@]}"; do
  gd=$(git -C "$d" rev-parse --absolute-git-dir 2>/dev/null) || continue
  found=1
  sha=$(git -C "$d" rev-parse --verify -q HEAD)
  saved=$(cat "$gd/pre-pr-review" 2>/dev/null)
  [ -n "$sha" ] && [ "$saved" = "$sha" ] || block "$d, HEAD ${sha:-<no commits>}"
done
[ -n "$found" ] || block "${dirs[*]} (not a git repo)"
