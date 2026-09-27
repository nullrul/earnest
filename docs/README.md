# Documentation

Project documentation for earnest.

- [00 — Project Intent](design/00-project-intent.md) — the ratifiable north star: vision, tenets `T#` and success criteria `SC#` that every later design doc traces to.
- [01 — Logic Design](design/01-logic-design.md) — what and why plus architecture: how Earnest adopts AI-DLC, taxonomy, grammar, stages and approvals, decisions, C4 diagrams, interfaces.
- [02 — Structural Design](design/02-structural-design.md) — the code level: the engine's file tree, module boundaries keyed to the C4 components, test tiers and fixtures, and the AI-DLC fork's delta.
- [03 — Implementation Plan](design/03-implementation-plan.md) — the milestone DAG: seven milestones from the trace spine to the AI-DLC fork's integration gate, each exiting on one behavior feature, with the context to load and the open questions that gate it.
- [04 — BDD Test Plan](design/04-bdd-test-plan.md) — behavior as the primary gate: three test tiers, one Gherkin feature per milestone with the success criteria it asserts, and M1's scenarios in full over the `broken-links` fixture.
