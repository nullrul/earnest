# 00 — Project Intent

Status: ratifiable north star, derived from `docs/intention.md`, September 2026. Author: Raul Cajias.

## Vision

A repository carries a checkable chain from intent to code, and every link in it, including the plan that delivers it, carries a verdict with located reasons.

## Why this matters

Requirement tracing tools check that a link exists. They read a coverage tag in a comment, find the matching item in the requirement set, and report the requirement as covered. They leave open whether the linked code does what the requirement says, and whether the linked test asserts it.

That worked while people wrote the tags. A person who typed a coverage tag usually meant it.

Automated code authors change that. They produce well-formed, correctly revisioned tags on code that only loosely relates to the requirement, and they do it at scale. The coverage report reads 100%, and nobody can tell how far "traced" has drifted from "done". A coverage number built on such tags is hearsay.

## Who it's for

- **The coding agent** — the primary user. It writes code and tests, tags them, runs the check, and learns what to fix before it claims a task done.
- **The repo maintainer** — writes intent, goals, features, requirements and decisions; ratifies changes to them; reads the report; overrides verdicts; and decides what counts as done.

## What it is

Earnest steers development. Humans own the intent, goals, features, requirements and decisions of a repository; agents implement them and use Earnest to see where their work has drifted from that chain and from the task they are on. For every requirement it answers one question: is it earnestly implemented and tested? It answers in three layers, each cheaper and more certain than the next.

1. **Trace.** Find every coverage tag, resolve it against the requirement set, and report missing coverage, stale revisions, unknown IDs and near-miss syntax.
2. **Judge.** For each requirement, a reader with reading comprehension reads the requirement clause, the tagged code and the tagged tests, and answers narrow questions: does the code implement the response to the trigger; does any test put the system in the stated state and assert the stated outcome. Every verdict carries reasoning and a location, and can be overridden per requirement.
3. **Evidence.** The tagged tests run and pass, and altering the tagged code makes them fail, so "tested" is measured rather than claimed.

The same chain covers the plan. Milestones deliver features, tasks deliver requirements or decisions, both carry dependencies, and their done-status is computed from the verdicts below them, never declared. A change an agent makes outside its current task is reported with exactly three exits: tag it under a requirement the task delivers, propose a task, or declare it blocked, so scope widens only through a record a human ratifies. After a change, Earnest names the features that may be affected and the tests worth running, without running everything.

The report gives several numbers where other tools give one, and every "no" says why and where. Earnest checks; authoring stays with the author and their tools.

## Tenets

- **T1 — Plain prose in.** A requirement set reads as prose and still parses. EARS gives the sentences structure and a stable item identity gives them a name, all within files the author already writes.
- **T2 — Extend the existing tracing ecosystem.** Its coverage semantics and identity syntax stay the reference. Earnest adds what it lacks: near-miss detection, behavior-spec tags, machine-readable findings, judgment and evidence.
- **T3 — Works on any repository.** One command runs the whole check from any editor or agent session, independent of any editor, workflow or vendor.
- **T4 — Agents are the primary users.** An agent writes, tags, runs the check, and learns what it got wrong before claiming done. Every error is specific, located, and clear about what to change.
- **T5 — The judge shows its work.** Reasoning is visible, verdicts are overridable, and overrides are recorded in the repository next to the requirement set.
- **T6 — Deterministic before probabilistic.** Everything the structural layer can decide, it decides without a reader. The reader only gets questions that need reading comprehension.
- **T7 — Done is measured, never declared.** A requirement, a task or a milestone is done when the evidence below it says so. No item carries a status someone typed.

## Success criteria

Each criterion names an observable signal, a threshold, and where it is observed, following [[smart-goals-make-agent-objectives-measurable-and-bound-the-monitoring-loop]].

- **SC1** (serves T4, T5) — Signal: the level each requirement reaches. Threshold: 100% of requirements in the set land at exactly one of traced, judged or evidenced, and each carries a located reason for every level above it that it missed. Observed in: the report.
- **SC2** (serves T2, T4) — Signal: near-miss tags in the scanned sources. Threshold: 100% of near-miss tags in a seeded fixture appear as findings with file and line; zero are dropped. Observed in: the findings output.
- **SC3** (serves T3, T4) — Signal: a coding agent's ability to act on the check. Threshold: from one command's output alone, the agent identifies the change needed for every finding before claiming a task done, with no other source consulted. Observed in: the agent's session transcript against the findings output.
- **SC4** (serves T5) — Signal: verdict provenance and override persistence. Threshold: 100% of judge verdicts carry reasoning plus a file and line; 100% of per-requirement overrides are stored in the repository and survive into the next run. Observed in: the report and the repository's override records.
- **SC5** (serves T6) — Signal: structural-layer findings across repeated runs. Threshold: identical findings on every run over an unchanged repository, with no reader involved. Observed in: a comparison of consecutive structural-layer outputs.
- **SC6** (serves T5, T6) — Signal: judge agreement with the maintainer, the calibration gate. Threshold: on one existing repository with ten hand-written EARS requirements and hand-tagged code and tests, the judge's verdicts agree with the maintainer's on eight or more of ten. Five or fewer means this intent is rethought before build. Observed in: the calibration record kept with the design documents.
- **SC7** (serves T4, T5) — Signal: the report's headline numbers. Threshold: three separate percentages always shown — traced, judged implemented, evidenced — so a reader sees how far "traced" has drifted from "done". Observed in: the report summary.
- **SC8** (serves T4, T7) — Signal: changes outside the current task's scope. Threshold: 100% of changed regions whose requirement the current task does not deliver appear as findings, each offering exactly the three exits. Observed in: the findings output on a seeded fixture.
- **SC9** (serves T4, T6) — Signal: impact of a change. Threshold: after a change, the report names every feature whose tests executed the changed lines and the tests worth running, without running the full suite; on a seeded fixture the named set includes every truly affected feature. Observed in: the impact output against the fixture's known dependencies.
- **SC10** (serves T7) — Signal: plan status. Threshold: every milestone and task shows a done-status computed from the verdicts of what it delivers, and no item in the plan carries a typed status field. Observed in: the plan output and the plan files.

## Scope (v1)

- Requirements as EARS sentences in plain prose files, each with a stable item ID.
- Coverage tags in code comments and in behavior-spec files for the four v1 source kinds: two general-purpose languages, prose requirement files, and behavior-spec files.
- The Trace, Judge and Evidence layers.
- A report with separate numbers per level and a located reason for every "no".
- Findings consumable by editor and review surfaces.
- Per-requirement verdict overrides stored in the repository.
- Decisions recorded as items in the same prose files, with their drivers and alternatives.
- Plan items, milestones and tasks, with dependencies and computed done-status.
- A scope check of an agent's change against its current task.
- Reading a repository's existing line-coverage data to name impacted features and select tests.

## Future directions

- Additional source languages beyond the v1 set.
- Editor integration beyond findings, such as live diagnostics while writing.
- Interchange with fuller requirements-management tools, for teams that need approval workflows and export.

Authoring of requirements and tests stays with the author and their tools; Earnest checks.

## Vocabulary

- **Earnest** — the tool, and the verdict on a requirement whose code and tests match its intent.
- **Hearsay** — a coverage tag with nothing behind it: a test that exists yet never asserts the outcome, or code that is tagged yet leaves the response unimplemented.
- **Near-miss** — text that is trying to be a tag and fails to parse, such as `[impl-req~x~1]` or `[impl->req~x]`. Other tools treat it as a comment; Earnest reports it.
- **Traced, judged, evidenced** — the three levels a requirement can reach, in order of cost and confidence.
- **Assessment** — one run of Earnest over a repository, producing observations and findings.
- **Observation** — what one check saw about one link in the chain, with method, result, reasoning and location.
- **Finding** — the verdict on one item, rolled up from its observations.
- **Override** — a human-authored observation that replaces the judge's for one item at one revision.

## Derivation & trace rule

- Source: `docs/intention.md`, which stays as the author's prose origin.
- This document is the immutable north star for the build, per [[goals-must-be-immutable-during-execution]]. Changing a tenet or success criterion is a formal scope change, recorded here with a dated changelog line.
- `01-logic-design.md` names the `T#` and `SC#` each of its goals serves. The behavior test plan asserts the `SC#`s. Anything that traces to none of them is scope creep.
- Mechanism, the how, lives in the logic design, keeping solution intent separate from implementation detail, per [[hld-documents-separate-solution-intent-from-implementation-detail-via-a-fixed-7]].
- The "Open questions for the design" listed in `docs/intention.md` are owned by the Open questions section of `01-logic-design.md`.
- Passing the calibration gate, SC6, is a precondition to executing the first milestone of the implementation plan.

## Changelog

- v1.0 (2026-09-26): derived from docs/intention.md.
- v1.1 (2026-09-26): steering purpose replaces gating; unattended automation actor removed; whole-chain and plan scope; T3 rewritten; T7, SC8–SC10 added; line-coverage reading moved to v1; assessment vocabulary added; calibration gate moved to first-milestone precondition.
