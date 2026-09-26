# Earnest: intention

Status: intention. This document says why Earnest exists and what it must do.
The design document that follows decides how.

Raul Cajias, September 2026.

## The problem

Requirement tracing tools check that a link exists. OpenFastTrace reads
`[impl->req~login-rate-limit~1]` in a comment, finds the matching item in a
Markdown spec, and reports the requirement as covered. StrictDoc, sphinx-needs,
LOBSTER and the commercial tools do the same with different syntax. None of them
ask whether the linked code does what the requirement says, or whether the
linked test asserts it.

That was fine when people wrote the tags. Someone typing `[impl->req~x~1]`
usually meant it.

Agents break that assumption. An LLM writing code will produce well-formed,
correctly revisioned tags on functions that only loosely relate to the
requirement, and it will do so at scale. The coverage report says 100% and
nobody can tell how far "traced" has drifted from "done". A coverage tag with
nothing behind it is hearsay.

## What we intend to build

Earnest is a CLI that answers one question for every requirement in a repo: is
it earnestly implemented and tested? It answers in layers, each cheaper and more
certain than the next.

1. Trace. Requirements live in plain Markdown, written as EARS sentences with
   an OpenFastTrace-style ID. Code and tests carry coverage tags in comments
   (Python, TypeScript) or native tags (Gherkin, `@stest:req~...`). Earnest
   finds every tag, resolves it against the spec, and reports missing coverage,
   stale revisions, unknown IDs and near-miss syntax that other tools silently
   ignore. Output is SARIF, so the same findings show up in any editor or PR
   view.

2. Judge. For each requirement, an LLM reads the EARS clause, the tagged code
   and the tagged tests, and answers narrow questions: does the code implement
   the response to the trigger? Does any test put the system in the WHEN state
   and assert the SHALL outcome? Every verdict carries its reasoning and a file
   and line, and can be overridden per requirement.

3. Evidence. The tagged tests run and pass. Mutating the tagged code makes
   them fail. "Tested" becomes something measured rather than claimed.

The output is a report with several numbers where other tools give one: 80%
traced, 71% judged implemented, 64% with a passing test that kills mutants. Each
"no" says why, and where.

## Principles

- Plain Markdown in. A spec should read as prose and still parse. EARS gives
  the sentences structure; the OFT item syntax gives them identity. No new
  file format.
- Build on OpenFastTrace, don't replace it. OFT stays the reference for
  coverage semantics and ID syntax. Earnest adds what OFT can't: malformed-tag
  detection, Gherkin support, SARIF, judgment and evidence.
- Works on any repo. No IDE, no workflow, no vendor. One command in CI and in
  a pre-commit hook.
- Agents are the primary users. An agent should be able to write code, tag it,
  run `earnest check` and learn what it got wrong before it claims a task is
  done. Errors are written for that reader: specific, located, and clear about
  what to change.
- The judge shows its work. A score nobody trusts is worse than no score.
  Reasoning is visible, verdicts are overridable, and overrides are recorded in
  the repo next to the spec.
- Deterministic before probabilistic. Everything the structural layer can
  decide, it decides without a model. The model only gets questions that need
  reading comprehension.

## Not in scope

- Requirements management: editing UIs, approval workflows, ReqIF export.
  Other tools do this.
- Generating requirements or tests. Earnest checks; it doesn't write.
- Languages beyond Python, TypeScript, Markdown and Gherkin in the first
  version.
- Replacing line-coverage tools. Line coverage and requirement coverage are
  different questions.

## Vocabulary

- Earnest: the tool, and the verdict on a requirement whose code and tests
  match its intent.
- Hearsay: a coverage tag with nothing behind it. A test that exists but never
  asserts the outcome. Code that is tagged but doesn't implement the response.
- Near-miss: text that is trying to be a tag but doesn't parse, such as
  `[impl-req~x~1]` or `[impl->req~x]`. Other tools treat it as a comment.
- Traced, judged, evidenced: the three levels a requirement can reach, in
  order of cost and confidence.

## Before designing

Validate the judge by hand. Take one existing repo, write ten EARS requirements
for it, tag code and tests manually, and have a model act as judge with a fixed
prompt. If its verdicts match ours on eight or more, the design is worth doing.
If it's closer to five, this intention needs rethinking before anything is
built.

## Open questions for the design

- Consume OFT's trace output (Java dependency) or reimplement the tag scan (a
  few hundred lines) and stay compatible at the file-format level only?
- How strict on EARS: reject non-EARS sentences, warn, or accept and parse
  less?
- Where do judge overrides live, and how do they expire when a requirement's
  revision changes?
- Mutation testing scope: per requirement (slow, precise) or per file (fast,
  coarse)?
- Is a language server worth it in v1, or is SARIF plus the existing OFT LSP
  enough?

## Prior art

- OpenFastTrace: Markdown items, comment tags, revision checks, LSP. Java. No
  Gherkin, no malformed-tag detection.
  <https://github.com/itsallcode/openfasttrace>
- StrictDoc: fuller requirements tool, own `.sdoc` format, `@relation`
  markers in source. <https://strictdoc.readthedocs.io>
- LOBSTER and TRLC (BMW): serious tracing, config-language DSL, heavier than
  we want.
- EARS (Mavin, Rolls-Royce): five sentence templates. Kiro, spec-kit and
  several MCP servers generate or validate it; none trace it to code.
