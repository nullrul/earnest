# 00 — Project Intent

Status: draft for review, September 2026. Author: Raul Cajias.

## Vision

Humans direct, agents build, and every step from an idea to running software is linked, checked and explained, so anyone can see at any moment how far "done" is from "claimed".

## Why this matters

Agents now write most of the code in a growing number of projects. Delivery methods built for agents keep them on course with phases, plans and human approvals, and they record traceability from requirements to code. In those methods the agent that wrote the code also writes the trace. A link from a requirement to a function is a claim the agent makes about its own work.

A claim with nothing behind it is hearsay. An agent produces well-formed links on code that only loosely relates to the requirement, at scale, and the coverage report still reads complete. Requirement tracing tools check that a link exists, and leave open whether the linked code does what the requirement says or whether the linked test asserts it.

A delivery method is only as trustworthy as its trace. If the trace is derived from the work itself, checked without a model wherever possible, and judged by a calibrated reader where reading is needed, then every approval a human gives rests on evidence rather than on the agent's account of what it did.

## Who it's for

- **The maintainer** directs the work. They state the intent, the goals, the features, the requirements and the decisions, approve each stage, override verdicts they disagree with, and decide what counts as done.
- **The coding agent** does the work. It plans, designs, writes code and tests inside the task it was given, and learns from the trace what it got wrong before it asks for approval.

## What it is

Earnest is an end-to-end delivery framework with deterministic traceability. It carries a piece of work from an idea through requirements, design, planning, construction and testing to delivery and operation, in stages, with a human approval at each stage boundary.

Every artifact a stage produces is plain prose with a small shared syntax that gives each item an identity, a revision and links to the items it derives from. Code and tests carry the same identities in comments and tags. From those, Earnest derives one trace of the whole chain, and checks it in three layers, each more costly and more certain than the one before.

1. **Trace.** Every link resolves: nothing is missing, orphaned, stale or malformed. Decided without a model, identically on every run.
2. **Judge.** For each requirement, a calibrated reader answers fixed questions generated from the requirement's structure: does the code implement the response to the trigger, and does a test put the system in the stated state and assert the stated outcome. Every verdict carries its reasoning and a location, and a maintainer can override it.
3. **Evidence.** The linked tests run and pass, and altering the linked code makes them fail.

The plan is part of the same chain. Units deliver requirements through their tasks, tasks deliver requirements and decisions, both carry dependencies, and their done-status is computed from the verdicts below them. An agent's change outside its current task is reported with exactly three exits: link it to a requirement the task delivers, propose a new task, or declare the task blocked. Scope widens only through a record the maintainer ratifies. After any change, Earnest names the features it may affect and the tests worth running.

At each stage boundary the maintainer sees the trace, the verdicts and the evidence for that stage before approving it.

## Tenets

- **T1 — Humans direct, agents build.** The maintainer owns intent, goals, features, requirements, decisions and approvals. Agents work inside the task they are given.
- **T2 — The trace is derived, never authored.** Links come from the artifacts and the code themselves. Nothing an agent writes about its own work counts as evidence of that work.
- **T3 — Deterministic before probabilistic.** Everything the structure can decide is decided without a model. A model only gets questions that need reading comprehension, and those questions are fixed in advance.
- **T4 — Done is measured, never declared.** A requirement, a task, a unit or a stage is done when the evidence below it says so. No item carries a status someone typed.
- **T5 — Plain prose in.** Every artifact reads as prose and still parses. A small shared syntax gives items identity and links, inside files people already write.
- **T6 — Feedback is written for the agent.** Every finding is specific, located, and clear about what to change.
- **T7 — The judge shows its work.** Reasoning is visible, verdicts are overridable, and overrides are recorded next to the item they override.
- **T8 — Build on proven methods.** Adopt an established delivery lifecycle and established tracing conventions, and add only what deterministic traceability requires.

## Success criteria

Each criterion names a signal, a threshold, and where it is observed.

- **SC1** (serves T2, T3) — Signal: the trace across all stages. Threshold: regenerating it from the repository alone gives an identical result on every run, with no model involved and no agent-written trace file read. Observed in: two consecutive runs over an unchanged repository.
- **SC2** (serves T2, T6) — Signal: broken links. Threshold: 100% of missing links, orphaned items, stale revisions and malformed identifiers in a seeded fixture appear as findings with file and line. Observed in: the findings output against the fixture.
- **SC3** (serves T4, T7) — Signal: the level each requirement reaches. Threshold: every requirement lands at exactly one of untraced, traced, judged or evidenced, with a located reason for each level it missed, and the report shows the traced, judged and evidenced percentages separately. Observed in: the report.
- **SC4** (serves T3, T7) — Signal: judge agreement with the maintainer. Threshold: on one existing repository with ten hand-written requirements and hand-linked code and tests, the judge agrees with the maintainer on eight or more of ten. Observed in: the calibration record.
- **SC5** (serves T1, T4) — Signal: changes to the chain. Threshold: when a requirement or decision changes, every item linked to its old revision is flagged in the same run, and an item whose text changed without a new revision is flagged. Observed in: the findings output on a seeded change.
- **SC6** (serves T1, T6) — Signal: changes outside the current task. Threshold: 100% of changed regions whose requirement the current task does not deliver appear as findings offering exactly the three exits. Observed in: the findings output on a seeded fixture.
- **SC7** (serves T3, T6) — Signal: impact of a change. Threshold: the report names every feature whose tests executed the changed lines, and the tests worth running, without running the full suite. Observed in: the impact output against a fixture with known dependencies.
- **SC8** (serves T4) — Signal: plan and stage status. Threshold: every unit, task and stage shows a done-status computed from the verdicts below it, and no artifact carries a typed status. Observed in: the plan output and the artifacts.
- **SC9** (serves T1, T4) — Signal: stage approvals. Threshold: 100% of stage approvals are recorded together with the trace, verdicts and evidence they rest on. An approval is the maintainer's, or automatic only when the check reports no error at or behind the current stage, and an automatic approval is recorded as automatic. Observed in: the approval records.
- **SC10** (serves T6) — Signal: an agent's ability to act on findings. Threshold: from the output alone, the agent identifies the change needed for every finding, with no other source consulted. Observed in: the agent's session against the findings output.
- **SC11** (serves T7) — Signal: overrides. Threshold: every override carries a reason and the revision it applies to, persists in the repository, and stops applying when that revision changes. Observed in: the artifacts and the report after a revision change.

## Scope

- Every stage of delivery, from idea to operation, with a human approval at each stage boundary.
- Every artifact of those stages written as plain prose with the shared syntax: intent, goals, features, requirements in a structured sentence form, decisions, units and tasks.
- Links from code and tests to requirements, in the source kinds the first projects use: prose files, behavior specifications, and two general-purpose languages.
- The trace, judge and evidence layers, with a report per requirement and per stage.
- Plan status computed from the trace; the out-of-task check of an agent's change against its task; impact of a change on features and tests.
- Overrides recorded next to the item they override.
- The same results whichever agent tool drives the work.

## Vocabulary

- **Earnest** — the framework, and the verdict on a requirement whose code and tests match its intent.
- **Hearsay** — a link with nothing behind it: code that is linked yet leaves the response unimplemented, a test that exists yet never asserts the outcome, or a trace an agent wrote about its own work.
- **Near-miss** — text trying to be a link that fails to parse. Other tools treat it as a comment; Earnest reports it.
- **Stage** — one step of delivery, ending in a maintainer's approval.
- **Untraced, traced, judged, evidenced** — the four levels a requirement can reach, in order of cost and confidence.
- **Assessment** — one run of Earnest over a repository. It produces **observations**, what one check saw about one link, and **findings**, the located results a person or agent acts on. An **override** is a maintainer's observation that replaces the judge's for one item at one revision.

## Derivation and trace rule

- This document is the north star. The logic design names the tenet and success criterion each of its goals serves, and the behavior test plan asserts the success criteria. Anything that traces to none of them is scope creep.
- How the framework is built, including which existing delivery lifecycle it adopts and how it is adapted, belongs in the logic design.
- Changing a tenet or a success criterion is a scope change the maintainer ratifies in this document.
- Passing SC4, the calibration gate, is a precondition to executing the first unit.
