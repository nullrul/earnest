#!/usr/bin/env bash
# PreToolUse(Bash) pre-PR review gate. Blocks `gh pr create|new|ready` and POSTs to
# `gh api .../pulls` unless <git-dir>/pre-pr-review holds HEAD of the checkout the
# command runs in: hook input .cwd, moved by each `cd`/`pushd` before the gated gh call.
# A cd target it cannot resolve to a repo fails closed: `$VAR`, `$(...)`, `cd -`, `popd`,
# `cd X |`, `~user`, flags, a non-repo dir, or quoted text that splits into a cd-like line.
# Speed bump, not a boundary. Not covered: `--head <branch>` / `-R <repo>` (the PR need
# not be the checked HEAD), `env -C <dir> gh ...`, shell quoting beyond one plain or
# quoted cd argument.
input=$(cat)
# Non-JSON input: jq fails, r is empty, nothing matches, exit 0.
r=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
r=${r//$'\\\n'/ } # join line continuations
c=${r//$'\n'/ }
gh='(^|[^A-Za-z0-9_-])gh[[:space:]]([^;&|]*[[:space:]])?'
pr='pr[[:space:]]+(create|new|ready)([^A-Za-z0-9_-]|$)'
pulls="pulls([[:space:]\"'?]|\$)"
post='(-X|--method)[[:space:]=]*[Pp][Oo][Ss][Tt]|[[:space:]](-f|-F|--field|--raw-field|--input)([[:space:]=]|$)'
gated() { [[ $1 =~ ${gh}${pr} ]] || [[ $1 =~ ${gh}api[[:space:]] && $1 =~ $pulls && $1 =~ $post ]]; }
gated "$c" || exit 0

block() {
  echo "Pre-PR review required (checked $1): run the /pre-pr-review skill (code-review, ponytail:ponytail-review, simplify, security-review on the branch diff), fix or answer findings, commit, then retry." >&2
  exit 2
}
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
cwd=${cwd:-${CLAUDE_PROJECT_DIR:-$PWD}}
dir=$cwd cds=0 gd=
anycd='^[[:space:](]*(cd|pushd|popd)([[:space:]]|$)'
cdre='^[[:space:](]*(cd|pushd)[[:space:]]+("([^"]*)"|'"'([^']*)'"'|([^[:space:];&|"'"'"']+))[[:space:]]*(&&|;)?[[:space:]]*$'
# One line per command (split after && ; | and at newlines); apply each cd before the first gated gh.
s=${r//&&/"&&"$'\n'}; s=${s//;/";"$'\n'}; s=${s//|/"|"$'\n'} # quoted: bash 5.2 expands & in replacements
while IFS= read -r line; do
  gated "$line" && break
  [[ $line =~ $anycd ]] || continue
  cds=1
  [[ $line =~ $cdre ]] || block "unparsed cd: $line"
  p=${BASH_REMATCH[3]}${BASH_REMATCH[4]}${BASH_REMATCH[5]}
  # shellcheck disable=SC2088 # literal tilde match, expanded by hand
  case $p in "~") p=$HOME ;; "~/"*) p=$HOME/${p#"~/"} ;; esac
  case $p in /*) dir=$p ;; *) dir=$dir/$p ;; esac
done <<<"$s"
# A cd target must be a repo; with no cd, a non-repo cwd falls back to the project checkout.
cands=("$dir"); [ "$cds" = 1 ] || cands+=("$CLAUDE_PROJECT_DIR")
for d in "${cands[@]}"; do gd=$(git -C "$d" rev-parse --absolute-git-dir 2>/dev/null) && break; done
[ -n "$gd" ] || block "$dir (not a git repo)"
sha=$(git -C "$d" rev-parse --verify -q HEAD)
saved=$(cat "$gd/pre-pr-review" 2>/dev/null)
[ -n "$sha" ] && [ "$saved" = "$sha" ] && exit 0
block "$d, HEAD ${sha:-<no commits>}"
