# M9 `openspec_host` Implementation Plan

Status: APPROVED-ready, 2026-11-25; M9 is OUTSIDE v1 (answer 14). All fourteen gating answers are DECIDED (user, 2026-11-25), recorded in Task 0 Step 1, and the plan executes from Task 0; its `04` scenarios stay PROPOSED text until the maintainer ratifies them.
The plan rests on five spikes of 2026-11-25 (A to E) and a read-only run on a private repository (Real-world run); M9 depends on M5, which is done, and shares M8's Node toolchain.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** earnest runs over an OpenSpec repository, from this repository alone and with the pinned `openspec` CLI. Run `uv run pytest tests/steps/test_openspec_host.py` in `packages/earnest/`. It drives `earnest check` and `earnest plan` against `openspec-change`, a synthetic fixture with main specs, one change in flight, one archived change and tagged code and tests, and asserts these things (the "Done when" of #27):

- `openspec validate --all --strict` passes on the fixture, and two `earnest check` runs give identical SARIF;
- each requirement lands at exactly one trace level, with a located reason for every level it missed;
- a tag that names a missing requirement, and a requirement that no tag reaches, both appear at file and line;
- a MODIFIED requirement changed without a new revision raises `unbumped-change`, once a gate row has approved the stage's items by name (answer 6);
- a requirement of more than one sentence raises `req-not-ears` at its file and line;
- a missing `openspec` CLI or Node fails the feature, and never skips it.

Along the way the feature also pins what #20 to #25 each settle: a change as an intent (#22), the delta and archive copies of a requirement (#23), a ticked box against a requirement below evidenced (#24), and OpenSpec's own apply instructions carrying earnest's guidance (#25). The exit command turns green at Task 9.

**Architecture:**

- Specs carry earnest ids inline (#20, option A, with the corrections of answer 3): each `### Requirement:` heading is followed at once by a `` `req~<name>~<n>` `` line and a `Covers:` line. The `feat`, `goal` and `tenet` items live in one earnest-owned file, `docs/intent.md`, because a capability that exists only in a delta has no place for a `feat` line that passes `openspec validate --strict` (R7). Earnest keeps reading the Markdown itself, because `openspec show --json` carries no line numbers and SC2 needs file and line.
- `ears.py` accepts `SHALL` beside `shall` through one constant (Task 1; spike B, the recommended scope of answer 1). Nothing else loosens.
- `adapters/__init__.py` skips `openspec/changes/archive/` (Task 4), and tags each source with its layer, `main` or `delta`; `index.py` holds the one rule that says which change a file belongs to, `change_of` (Task 5). `index.py` and `structural.py` let a delta copy at a higher revision overlay the copy beneath it, main or another change's (Task 6; spike C's design C, plus the two-line stacked-change extension of Q8).
- `openspec.py` (new) names the changes, builds the intent of a change (`load_openspec`), runs `openspec status --change <id> --json` for the route, reads the boxes of `tasks.md` as upstream counts them, and fails with exit 2 when the CLI is missing (Tasks 5 and 7; spike D). `plan.py` gains a stage-to-glob mapping, so the flat OpenSpec files belong to stages. `reporter.py` gains two rule ids.
- `integrations/openspec/` holds the guidance that `openspec/config.yaml` carries into OpenSpec's apply step (Task 8).
- The tests: a synthetic fixture `tests/fixtures/openspec-change/` with overlays, `openspec_host.feature` and its step module, `tests/node.py` (M8 Task 2 Step 3's helper for the Node tools, to which Task 2 adds `openspec_env`), and unit tests that keep the CLI out of the unit tier with a fake `openspec` script from the shared `fake_executable` (L5). The tests that run the real CLI sit in `tests/integration/test_openspec_ids.py`, which `addopts` leaves out of a bare run until Task 9 (P5).
- One Node toolchain under `packages/earnest/`, owned by M8 Task 1 and shared with M9 (Task 2, Shared with M8).

**Tech Stack:**

- Python 3.12 standard library at runtime (L4), unchanged. `impact._process` (`subprocess`) now also runs `openspec`; `json` reads its output.
- Node tools, as dev tooling only: `@fission-ai/openspec` 2.1.1, from the same manifest as M8's Jest and StrykerJS (DECIDED (user, 2026-11-25), answer 12).

**Spec:**

- `docs/design/03-implementation-plan.md`, milestone M9.
- `00`: T8 and Scope (the scope change that #19 asks the maintainer to ratify), SC1 to SC3, SC5, SC8 to SC10.
- `01`: Adopting AI-DLC (the shape Task 0 mirrors in "Adopting OpenSpec"), Grammar, Findings, Trace levels, Stages, Frontier and position, Revision lifecycle, Region rule, D2, D15, Command surface, Open questions.
- `02`: `ears.py`, `index.py`, `structural.py`, `plan.py`, `reporter.py` and `adapters/` in Module boundaries; L4, L5, L6.
- `04`: the M9 row of the milestone table, and the M9 section that Task 0 writes (already drafted on this branch).
- Issues #19 to #27. #36 (M8's Node decision) shares #26's answer.

## Spike facts (2026-11-25)

Sources: the five spike reports of 2026-11-25 (A to E), with their logs and scratch repositories. They did not survive, so each fact below names the spike that measured it. All spikes ran at earnest `ae4136c`. The spikes pinned OpenSpec 2.1.1 (`0c737dc`), and C also read the 2.2.0 source (`f1cd852`). The code that Tasks 4 to 7 and 10 build on is inlined in those tasks.

| #   | Fact                                                                                                                                                                                                                                                                                                                                                                                                                                                | Evidence                                |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| S1  | A plain OpenSpec repository gives `earnest check` rc 0 with `requirements: 0`: a silent false green. Upstream's own source gives rc 1 from 7 `near-miss` errors on `[~]` in `.ts` comments.                                                                                                                                                                                                                                                         | spike A, Findings                       |
| S2  | Option A ids (#20) pass `openspec validate --strict`, survive `show --json` and archive, and a MODIFIED block carries its bumped id. The id line must come first under `### Requirement:`. A `feat` needs `Needs: req` and a tenet and goal chain to reach no finding.                                                                                                                                                                              | spike A, `out/`, probe p4c              |
| S3  | OpenSpec's validator needs `SHALL`, case-sensitive, and earnest parses only `shall`. On OpenSpec's own repository, 318 requirements: 0 parse today, 246 with the one-constant change. Of the other 72, spike B counts 37 multi-sentence bodies, which stay `req-not-ears`; spike A counts 36 that open with a bare subject (`OpenSpec shall`), 33 multi-sentence and 3 other, so the first two counts overlap by 4. `MUST` adds nothing (0 of 318). | spike B, `corpus.py`; spike A, Findings |
| S4  | The exact keyword `(?:shall\|SHALL)` is right. `re.IGNORECASE` loosens `Where`, `When` and `The`; normalising `SHALL` to `shall` rewrites the sentence the judge reads and hashes. Changing only the final match leaves the `(?! shall )` lookahead blind to `SHALL`, and the response span comes out wrong (`retry` for `reply that clients SHALL retry`).                                                                                         | spike B, `variants/`                    |
| S5  | A stage is a directory prefix (`stage_of`), but OpenSpec artifacts are flat files, so every stage has `items: []` until a stage-to-glob mapping exists. `openspec status --json` is a DAG, not a linear route. `PRODUCES` is keyed by AI-DLC slugs. `--stage` and `--intent` on a change directory exit 2: there is no record directory.                                                                                                            | spike A, #22                            |
| S6  | Identity is (type, name), and the first definer in sorted path order wins. A delta and its main spec collide (`duplicate`), and the winner depends on the change id. After `openspec archive` there are 6 duplicates, because `skipped()` knows only AI-DLC paths. On OpenSpec's corpus 299 of 318 main requirements have an archive copy, and one has 14.                                                                                          | spike A and C                           |
| S7  | Upstream applies a delta in the order RENAMED, REMOVED, MODIFIED, ADDED. MODIFIED replaces the whole block, id line included. Requirement names match exactly and case-sensitively. There is no cross-change conflict check. `archive` writes the merged specs, then moves the change to `changes/archive/YYYY-MM-DD-<id>`.                                                                                                                         | spike C, `specs-apply.ts`               |
| S8  | Design C (skip `archive/`; a delta at a higher revision overlays main; REMOVED headings drop the main id) passes 1068 tests with no existing test changed, leaves 0 corpus duplicates (base 393), and is clean on the in-flight, early-sync and after-archive cases. Design A (overlay and skip) leaves 4 false gaps and a dirty early-sync. Design B (projection by heading) costs +196/-19 lines and gives a false duplicate on early-sync.       | spike C, matrix                         |
| S9  | A change directory is each directory directly under `openspec/changes/` except `archive` and dot-names, as upstream's `getActiveChangeIds` has it. The route comes from `openspec status --change <id> --json`: a forked schema that adds `review` gave 5 stages from the CLI and 4 from a constant. A missing CLI is `PlanError`, exit 2, with no silent fallback.                                                                                 | spike D, findings 1 and 3               |
| S10 | `tasks.md` layout L2: the id line and `Delivers:` go directly above the checkbox. Ids after the box caused near-misses and hashed the wrong item. Done means `x` or `X` only; a Python port of upstream's `TASK_LINE_PATTERN` has 0 mismatches over 2,633 tasks. A tick changes the body hash and raises `unbumped-change`, so the body hash must ignore the box.                                                                                   | spike D, findings 5 to 7                |
| S11 | Without ids a box is `untracked`, and without a rule it left `tasks: done` vacuously true. Upstream's own repository gives 154 `untracked-box` findings. With several changes in flight there is no current task.                                                                                                                                                                                                                                   | spike D, findings 10 and 11             |
| S12 | `openspec archive --yes` with open boxes still exits 0: OpenSpec's task gate is advisory. Strict validation fails text above a delta's first `##`, and a Purpose under 50 characters.                                                                                                                                                                                                                                                               | spike D, Gotchas                        |
| S13 | `operations.apply.guidance` in `openspec/config.yaml` surfaces as `operationGuidance` in `openspec instructions apply --json`. `apply --json` omits ids, so the guidance must point the agent at `tasks.md`. A default `openspec init` writes skills to `~/.agents/skills`, outside the repository; `init --tools claude --scope project --no-animation` stays inside it.                                                                           | spike A (#25, #26); spike D, finding 5  |
| S14 | One `package.json` and lockfile give `jest`, `stryker` and `openspec` in `node_modules/.bin`; Node must be 22.20.0 or later (OpenSpec's `engines`); CI's `lint-docs` pins Node 20. The lockfile pins 633 packages; `npx` pins 6.                                                                                                                                                                                                                    | spike E                                 |
| S15 | Not run by any spike: a real `openspec archive`, `validate` of REMOVED and RENAMED deltas in an earnest fixture, namespaced change folders, `openspec sync`, custom task files, a real judge, and OpenSpec 2.2.0 against the prototypes.                                                                                                                                                                                                            | the reports' "Not checked"              |

## Real-world run: `nullrul/apartment-twin` (2026-11-25)

Approved by the maintainer. A read-only blobless clone, kept outside this repository, was the only input; nothing was written into it (`git status` clean after every run). The repository is private, so this plan publishes counts and rule names only: no commit, date, file, requirement or change name, message text, or description of what one change holds or does to another. The M6 plan's vendoring approval for the 3d-pipe excerpts is a separate approval and does not extend to this plan.

What the repository holds under `openspec/`, by count: 29 files; 7 main specs with 125 requirement headings; 2 changes in flight (28 ADDED and 9 MODIFIED headings in the first, 7 and 7 in the second; 82 of 82 and 0 of 6 boxes ticked); 0 archived changes. That is 176 requirement blocks and 160 distinct (capability, name) definitions. All 176 contain `SHALL` and none contains `MUST`. No file carries an earnest id or tag.

| #   | Run (exit code captured with `$?`; R1 and R2 under `rtk proxy`)                                  | Exit   | Result                                                                                                                                                                                                                     |
| --- | ------------------------------------------------------------------------------------------------ | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | current `earnest check`                                                                          | 0      | `requirements: 0`, 0 findings. A silent false green (S1).                                                                                                                                                                  |
| R2  | current `earnest plan`                                                                           | 0      | `no plan`                                                                                                                                                                                                                  |
| R3  | `openspec validate --all --strict` (2.1.1)                                                       | 1      | 8 of 9 items pass. The one that fails raises 4 WARNINGs of the requirement-length rule (500 characters); another raises 3 INFOs.                                                                                           |
| R4  | spike D prototype `plan`, default approvals                                                      | 0      | 2 intents of 4 stages; both at frontier `proposal`.                                                                                                                                                                        |
| R5  | the same with `EARNEST_OPENSPEC_APPROVAL=artifact`                                               | 0      | One intent reaches frontier none, with `tasks` the only stage not done. The other stays at frontier `design`: it has a `tasks.md` and no `design.md`, and `openspec status` calls its `tasks` done and its `design` ready. |
| R6  | the same prototype's `check`                                                                     | 0      | 88 `untracked-box` notes (82 and 6), and `no current task` (two changes in flight).                                                                                                                                        |
| R7  | `check --stage specs`, then `--stage tasks`, on a working copy                                   | 0, 0   | `specs`: 0 findings and an assessment hash. `tasks`: 82 `untracked-box` warnings.                                                                                                                                          |
| R8  | ids injected on all 176 blocks of a copy (MODIFIED at revision 2), `check` by variant            | 1 each | base: `duplicate` 16. Spike C designs A and C: 7. Design B: 0. Design C plus the stacked-change extension of Q8: 0. All carry `gap` 320 and `orphaned` 160, which the missing `feat` chain causes and no variant touches.  |
| R9  | the same copy, spike B's `SHALL`                                                                 | 1      | `req-not-ears` 160 down to 104: 56 of 160 definitions parse.                                                                                                                                                               |
| R10 | the same ids in the real files, then `openspec validate --all --strict`                          | 1      | 4 of 9 items fail, against 1 before: the id line pushed 7 more requirement texts over 500 characters.                                                                                                                      |
| R11 | `feat` line under `## ADDED Requirements` in a delta that adds a new capability, strict validate | 1      | a new WARNING of the text-before-the-first-requirement rule.                                                                                                                                                               |
| R12 | design C twice on the same copy                                                                  | 1, 1   | the SARIF files are byte-identical.                                                                                                                                                                                        |

Of the 176 requirement blocks, 60 parse as one EARS sentence once `SHALL` is accepted; 98 are multi-sentence, 14 open with a bare subject, and 4 are other. The residual 7 `duplicate` findings of design C (R8) are 7 requirements that both changes in flight define.

### Where the real repository contradicts a spike

| #   | Spike said                                                                              | The repository shows                                                                                                                                     | What this plan does                                                                                                                                                                                                                                                                  |
| --- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| X1  | C: two changes defining one id stay `duplicate` (C's decision 4); design C recommended. | Two changes in flight define 7 requirements between them, so stacked changes are real here. Design C raises 7 false `duplicate` errors for them (R8).    | Q8 recommends a two-line extension: among delta copies the higher revision wins, and only an equal revision is a duplicate. Measured: 7 down to 0, with spike C's 14 layer tests and the rest of the 1068-test suite unchanged except one test that reads `docs/demo` from the copy. |
| X2  | A: option A ids pass `validate --strict`.                                               | An id line costs about 30 characters of the 500 that strict allows: 7 of 176 blocks cross the limit, and 3 of 7 main specs flip from pass to fail (R10). | Q3 records it. The fixture keeps bodies short, and Task 3 asserts strict on the fixture.                                                                                                                                                                                             |
| X3  | A and B: `SHALL` is the blocker (246 of 318 parse after the change).                    | 98 of 176 blocks are multi-sentence: case is not the dominant blocker here (R9).                                                                         | Q1's acceptance of `SHALL` stands. Q2 asks the question the change leaves open.                                                                                                                                                                                                      |
| X4  | A: each `spec.md` gets a `feat~<capability>~1` line.                                    | 5 of 9 capabilities in flight here exist only in a delta, with no main spec to hold the line, and a `feat` line in a delta fails strict (R11).           | Answer 3's recommendation: `feat` ids live in `docs/intent.md`.                                                                                                                                                                                                                      |
| X5  | D: the route's frontier is the first stage not done.                                    | One change has a `tasks.md` and no `design.md`, so its frontier is `design` and every later finding of it is downgraded to a note (R5).                  | Q7 recommends treating a skipped stage as passed.                                                                                                                                                                                                                                    |
| X6  | D: the current task is the first unchecked box of the single change in flight.          | There are two changes in flight, and one has all 82 boxes ticked yet is not archived. The prototype finds no current task (R6).                          | Q10 recommends counting only changes that still hold an unchecked box.                                                                                                                                                                                                               |
| X7  | C: `archive/` is skipped, and "after archive" is clean.                                 | This repository has no archived change, so the skip is unexercised; its stack (R3) is what `openspec archive` would reorder.                             | Task 4 tests the skip on a fixture, and the exit gate holds an archived change.                                                                                                                                                                                                      |

## Gating open questions

Issues #19 to #27 and the spikes cut M9's open questions into the fourteen answers below. All fourteen are DECIDED (user, 2026-11-25), each below with its evidence. Each follows the plan's recommendation ("as recommended"), and answer 6 adds who writes the approval rows. A recommendation was the evidence read once. Task 1 needs only the decision of answer 1 and builds its recommended scope; Task 2 needs answer 12 and M8's six, so it waits for Task 0 Step 1; Task 3 needs 3 and 4; Task 4 needs 8; Task 5 needs 6, 7 and 11, and 5 for its Step 4 rule; Task 6 needs 8 and 9; Task 7 needs 10; Task 8 needs 13.

### 1. The keyword of #21 (DECIDED 2026-11-25)

**Decided, 2026-11-25:** the maintainer said "we can accept SHALL". That is the whole decision: `SHALL` is accepted as an EARS keyword.

**DECIDED (user, 2026-11-25), A):** the exact keyword, `shall` or `SHALL`, and no other letter case (`Shall`, `sHALL`), and no `MUST`, with the five templates left lowercase (plan choice P2). OpenSpec's validator wants `SHALL` in that exact case, and a case-folded parse would accept bodies that `openspec validate --strict` rejects (S3, S4). Ruled out: any letter case (`re.IGNORECASE` loosens `Where`, `When` and `The` as well, S4), and adding `MUST` (0 of OpenSpec's 318 bodies and 0 of the 176 of apartment-twin need it). Widening it later is one constant.

Decided as recommended. The `req-not-ears` message gains the suffix "(the keyword is `shall` or `SHALL`)". The Grammar and D2 edits in `01` are ratified with #19 (answer 14).

### 2. Multi-sentence requirement bodies (spike A, decision A)

Row as asked: what earnest does with an OpenSpec requirement whose body runs to several sentences.

**DECIDED (user, 2026-11-25), A):** keep `req-not-ears` an error (D2 stands). The author rewrites the body as one EARS sentence and moves the rest into scenarios, which is also what OpenSpec's own limit asks for (R3, X2). Ruled out: a warning ramp, and judging the first sentence only.

Evidence: with `SHALL` accepted, 98 of apartment-twin's 176 blocks are multi-sentence, 14 more open with a bare subject, and only 60 parse (R9). On OpenSpec's own repository 37 of 318 are multi-sentence (S3). The M6 plan counts the same on its 15 SC4 candidates: 6 parse. So the finding will be common on adopting repositories, and D2 says it is an error on purpose.

Decided as recommended. The fixture and exit gate assume it. A warning ramp for adopters can follow without touching the grammar (a severity, not a parse).

### 3. Where the ids sit (#20)

Row as asked: option A (inline id lines) or B (ids derived from names), and the corrections the spikes found.

**DECIDED (user, 2026-11-25), A):** inline ids as #20 recommends, with the `feat` items in one earnest-owned file, `docs/intent.md` (A'). Ruled out: a `feat~<capability>~1` line in each main `spec.md` (A0), and ids derived from requirement names (B: a name carries no revision, so `unbumped-change` has nothing to compare, and a rename changes the id; OpenSpec issue #1697 shows renames already break MODIFIED merges, and #2167 proposes stable ids upstream, so revisit B if it lands).

Evidence for A over A0 (the corrections to #20's text):

- The `feat` id of a capability that a change creates has no main spec yet. A `feat` line under `## ADDED Requirements` fails strict validation (R11), and spike D found text above a delta's first `##` fails too (S12). 5 of the 9 capabilities that apartment-twin's two changes touch are new (X4).
- A `feat` needs `Needs: req` and a tenet and goal chain above it, or the check raises `orphaned` and `gap` (S2).
- The id line must come first under the heading (S2), and costs about 30 characters of strict's 500-character requirement limit: 7 of 176 blocks cross it (R10, X2). A fixture, and an adopter's specs near the limit, must stay under about 470.
- Both options keep earnest reading the Markdown itself: `show --json` carries no line numbers and SC2 needs file and line.

Decided as recommended. Record the three corrections in `01` through #19 and in #20's text.

### 4. The chain root (spike A, decision B)

Row as asked: what stands above a `feat` in an OpenSpec repository, which has no tenets or goals.

**DECIDED (user, 2026-11-25), A):** require a tenet and goal, as today, in `docs/intent.md`. No code. It costs a file the maintainer owns anyway (T1: humans own intent and goals), and it needs no change to `structural.py`. Ruled out: a route profile without them, and defaulting a `feat` to `Needs: req` (both change the Default Needs table of `01` for a convenience).

### 5. A repository with no requirement (spike A, decision C)

Row as asked: whether a repository with an `openspec/` directory and 0 requirements gets a finding, and at what level.

**DECIDED (user, 2026-11-25), B):** a warning, `earnest/no-requirements`, when `openspec/` exists at the root and the index holds no `req`. It sits at `openspec/config.yaml` line 1, or at the first main spec's line 1 when there is no `config.yaml`; an `openspec/` with neither has no file to point at and raises none. A nested `openspec/` (this repository's own fixture) raises none. Task 5 builds it beside the change discovery that finds `openspec/`. Ruled out: no finding, and an error.

Evidence: R1. Current earnest exits 0 on apartment-twin, which holds 176 requirement blocks, and the only trace is a summary line (S1). SC1 asks for the same result every run, and says nothing of a result that hides a repository.

Decided as recommended (confidence was medium; the rule is new). Task 5 Step 2's unit test and Step 4's sentence stand.

### 6. Where OpenSpec stage approvals live (#22, SC9)

Row as asked: OpenSpec records no approvals ("no approval gate"). Who approves a stage, and where is the approval written.

**DECIDED (user, 2026-11-25), B, the hybrid):** an existing artifact counts as approved "by openspec", with no items named. Explicit `GATE_APPROVED` rows in `<change>/audit/*.md` override it and name items. **The rows are written by the AGENT, through the #25 guidance (answer 13, Task 8), after the human approves**: the agent never writes a row before the human has said yes, and earnest itself writes none. Ruled out: shard rows only, and SC9 staying with AI-DLC.

Evidence: under A the frontier stays at `proposal` for both of apartment-twin's changes, and every later finding is a note, so a run of 88 findings reports none above note level (R4, R6). Under B, one change reaches frontier none (R5). Spike D wrote the explicit-row path with the same parser as AI-DLC (`parse_audit`, `_approval`, `_named`), so A and B share code. An `audit/` directory inside the change is bookkeeping and is never scanned.

Consequence for `unbumped-change`: `plan.next_bodies` freezes a body hash only for an item that a counting approval row names with its revision (`_named` reads the row's `Items` field, and gives none for a row without one). Under B an artifact approved "by openspec" names no items, so nothing is frozen and `unbumped-change` stays silent until a gate row with `Items` exists. Scenario 9 therefore commits one, in the `approved` overlay, after the stage check and before the edit, as the M2 scenarios approve at the gate before their change commit.

Decided as recommended, with the writer fixed. The environment variable of the prototype, `EARNEST_OPENSPEC_APPROVAL`, is a spike device and is not carried over; B is the default. Consequences of the agent as the writer:

- Task 8's guidance carries a line that tells the agent to append the row after the human approves a stage (its text is in Task 8 Step 2).
- The `approved` overlay of the fixture is a fixture file that stands for the row the agent writes after the human's approval.
- This plan's tasks write no row and no code that writes one: the writer is an agent following advisory text, not earnest.
- The row's `Approved By: human` is the agent's claim. Nothing in OpenSpec or earnest checks that the human approved first (Known limits).

### 7. The route, and the frontier of a skipped stage (#22)

Row as asked: where the route comes from, and what the frontier is when a stage has no artifact.

**DECIDED (user, 2026-11-25), two parts):**

- **Source, A:** `openspec status --change <id> --json`, from the CLI. It needs Node even for `earnest plan`, and exits 2 when the CLI is missing. Ruled out: a constant for `spec-driven`, and a file read of the schema YAML.
- **Frontier, B:** a stage with no artifact counts as skipped, not as the frontier, when a later artifact exists.

Evidence: S9 (a forked schema got 5 stages from the CLI and 4 from the constant). One change has a `tasks.md` and no `design.md`; `openspec status` calls `tasks` done and `design` ready, and the prototype's frontier is `design` (R5, X5). Under frontier A every `tasks` finding of that change is a note while its tasks are being done.

The constant route (ruled out) would have fitted L4 best, with no Node at runtime, and goes stale at the first schema change (S9). Decided as recommended; confidence on the frontier was medium, from one repository and one change.

### 8. Archive, delta overlay and stacked changes (#23)

Row as asked: which copy of a requirement defines it while a change is in flight, how an archived copy is read, and what two changes defining one id mean.

**DECIDED (user, 2026-11-25)):**

- **Archive, A:** skip `openspec/changes/archive/**` below the root `openspec/`, the one place answer 11 reads (spike C, decision 2, skipped it at any depth). Skipping avoids 299 of 318 corpus requirements colliding with their archive copy, and the paths are fixed relative to the store root (S6, S7). Ruled out: reading it as history.
- **Overlay, B:** design C plus the stacked-change extension. A delta at a higher revision overlays main, a delta at the same revision loses to main, a lower one is `outdated`, and two changes at one revision are `duplicate`; and among delta copies the higher revision overlays the lower silently, and only an equal revision is `duplicate`. Ruled out: design C alone, and design B (projection by heading, +196/-19).

Evidence: S8, and X1: two of apartment-twin's changes define 7 requirements between them, and design C raises 7 errors for them. The extension has two parts. `Index.defined` takes `item.layer == DELTA` as a reason to compare revisions (one clause). `_duplicates` must not report a base behind a stacked delta. What was measured, in spike C on 2026-11-25, is a structural rule that skips any delta copy behind the overlay winner: 7 down to 0 on the repository's injected copy, the same layer tests green, and an equal revision (MODIFIED without a bump) still `duplicate`. Task 6 replaces that structural rule with a comparison per revision (a delta copy against the first delta copy at its own revision), because that rule would also skip B when A and B share a revision and C stacks above them. The replacement was not measured: the new test `test_two_changes_at_one_revision_stay_duplicate_when_a_third_stacks_above_them` checks it, and R8's count is that rule's own.

Decided as recommended. Task 6 writes the stacked-change test first.

### 9. REMOVED, RENAMED and what else #23 leaves (spike C, decisions 1, 3, 5, 6, 7, 8)

Row as asked: the smaller choices of #23.

**DECIDED (user, 2026-11-25), the bundle as written):** each line below is accepted with the spike's recommendation.

- A tag on a requirement that a change in flight REMOVES is flagged: `orphaned`, naming the heading (recommended; built in Task 10, deferred).
- A stale delta (behind main) is reported as `earnest/outdated`, as prototyped, not as a new rule (recommended).
- A REMOVED block carries no id line; both work (recommended: none, as OpenSpec's REMOVED asks for a name, a reason and a migration).
- A RENAMED requirement needs nothing while ids are stable (S2, option A).
- A same-revision changed body is left to #22: `unbumped-change` against the record's baseline catches it. Scenario headings end an earnest item, so scenario edits never trip it.
- The id-drift check (an id that changed without a rename), about 6 lines: **defer**.
- Sequencing: land the archive skip before #22 (Task 4), and the overlay after it (Task 6). #23 needs #20's id syntax only, not #22; the order here follows spike A's. REMOVED handling is Task 10, deferred and outside the exit path, because `03` defers it and no exit bullet needs it.

Decided as written. REMOVED, RENAMED and namespaced change folders were not exercised by any fixture, and spike C ran no real `openspec archive` (S15), so Known limits states them.

### 10. Done-status of `tasks.md` (#24)

Row as asked: how a ticked box becomes a computed status.

**DECIDED (user, 2026-11-25), A):**

- **Body hash:** the body hash of a `task` ignores the checkbox state, and the Revision lifecycle step 2 of `01` says so. Ruled out: a tick as a body change.
- **Rules:** `earnest/checked-unevidenced` (warning) at the box line, when a box is ticked and a requirement the task delivers is below `evidenced`; and `earnest/untracked-box` (warning), which also keeps the `tasks` stage open, for a box with no `task` id line above it. Both are warnings. Ruled out: notes only.
- **Current task:** the first unchecked box of the one change in flight that still holds an unchecked box, and none when there are several (spike D, finding 11), counting only changes with an unchecked box.

Evidence: S10, S11; a tick after approval raised `unbumped-change` without A (spike D, finding 6); `untracked-box` is 88 findings on apartment-twin's two changes (R6), so it is per box, as SC2 asks for file and line; one change has all its boxes ticked and is not archived, so counting it as in flight leaves no current task (R6, X6).

Decided as recommended. Notes only for the rules would have made T4 a label.

### 11. Where `openspec/` is (spike D, decision 5)

**DECIDED (user, 2026-11-25), A):** `openspec/` at the repository root only. Spike D found a false intent in upstream's own test fixtures at any depth. apartment-twin has it at the root. Task 5's `change_of` therefore tests that a path begins at `openspec/changes/`, where the prototype matched any depth, and the archive skip (Task 4) and `layer` (Task 6) use the same root-only rule, so one rule says where `openspec/` is. Ruled out: any depth.

### 12. The pin, Node, and failing when the CLI is missing (#26)

Row as asked: one OpenSpec version, in one place, and Node and the CLI for `make test` and CI, sharing M8's answer.

M8's plan holds six questions that this one shares: npm or pnpm (its question 1), where the manifest lives (2), the Node line (3), when the OpenSpec pin enters the manifest (4, its timing alone), the TypeScript transform (5) and failing or skipping when the tools are missing (6). Their answers serve M9 unchanged, so they are not repeated here. The OpenSpec version has one owner, this answer, and M8's question 4 defers to it. M9 adds two:

**DECIDED (user, 2026-11-25), pin 2.1.1; fail, never skip):**

- **Version: 2.1.1.** Every spike but C measured it, and C found 2.2.0 identical on the surfaces used (npm latest is 2.2.0, 2026-11-24). The lockfile refuses a mismatch, so a bump is deliberate (spike E). Ruled out: 2.2.0, not run against the prototypes.
- **Failing:** the M9 feature fails, never skips, when Node or the CLI is missing, as #26 asks and as M7 and M8 do. The unit tier stays Node-free.

Constraints from spike E: the pin comes from the manifest and nothing runs `openspec install` or a global install; `OPENSPEC_TELEMETRY=0` is set in the Makefile; the install is `--ignore-scripts` or pnpm's default, since one dependency has an install script.

Decided as recommended. M8's six answers are decided too (pnpm with `pnpm-lock.yaml`, the manifest in `packages/earnest/`, `.nvmrc` 24 with `engines` `>=22.20.0` and `lint-docs` left on Node 20, the pin entering with M8 Task 1, ts-jest 29.4.15 with typescript 6.0.3, fail not skip). M8 lands first, so M8 Task 1 creates the files, by its recipe and with the pin (Shared with M8, below).

### 13. How earnest reaches OpenSpec's workflow (#25)

Row as asked: guidance, a custom schema or a skill.

**DECIDED (user, 2026-11-25), A):** `operations.apply.guidance` and `operations.archive.guidance` in `openspec/config.yaml`, shipped as a snippet under `integrations/openspec/`, with install docs. Advisory, and it reaches the apply and archive steps (S13). It also carries the approval-row guidance of answer 6. Ruled out: a custom schema, and a skill (`openspec-verify-change` has no config hook); both can follow on the same text.

Evidence: S13, and that `apply --json` omits ids, so the text must send the agent to `tasks.md`. A is the smallest surface that reaches both steps.

Decided as recommended.

### 14. Ratifying the scope (#19), and what the fixture may hold

Row as asked: `00` says the maintainer ratifies a scope change, and T8 and Scope name one delivery lifecycle.

**DECIDED (user, 2026-11-25)):** ratify OpenSpec as a second host in `00`'s Scope and T8, add "Adopting OpenSpec" to `01`, the OpenSpec rows to `02`, and M9 to `03`, and drop M9's "proposed" label (#19). **M9 is OUTSIDE v1**: `04` stays "nine in all", and M9's scenarios sit beside the nine without joining the v1 count (as M8 is part of v1 and M9 is not). The exit fixture is written fresh and synthetic: no line, name or number of apartment-twin enters this repository (plan choice P1).

Decided as recommended on the ratification and the fixture, with M9's place outside v1 stated.

## Shared with M8

M8 lands first (it is in v1, and M9 is not). Its Task 1 is the one recipe for the toolchain and pins `@fission-ai/openspec` 2.1.1 (answer 12); its Task 2 Step 3 is the one Python helper, `tests/node.py`, with `fake_executable` and `tests/tools.py`.
M9 copies none of it: Task 2 here adds only `openspec_env(home)` to that helper, and the M9 feature calls `require_tools("openspec")`. #26's done-when also asks it to reference the decision M8's Task 0 records; that comment on the issue is a GitHub write, so the maintainer approves it.

## Interface contract with OpenSpec 2.1.1

Everything earnest takes from OpenSpec is one of these surfaces. Each was run by a spike or by the real-world run, and the pin makes them stable until a deliberate bump.

| Surface                                            | What earnest reads                                                                                                                                                                | Where                                                 |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `openspec --version`                               | the pin, compared with `package.json`                                                                                                                                             | `node-check`                                          |
| `openspec status --change <id> --json`             | `schemaName`, and per artifact `id`, `outputPath`, `requires` and `status` (`done`, `ready`, `blocked`)                                                                           | `openspec.route_cli` (Task 5)                         |
| `openspec validate --all --strict [--json]`        | exit code; per item `valid` and `issues` (`level`, `message`)                                                                                                                     | `tests/integration/test_openspec_ids.py`, the feature |
| `openspec instructions apply --change <id> --json` | `operationGuidance`                                                                                                                                                               | the feature (Task 8)                                  |
| `openspec list --json`                             | `completedTasks` and `totalTasks` per change, as a cross-check of earnest's own box count                                                                                         | Task 7's unit test                                    |
| `openspec/config.yaml`                             | `operations.apply.guidance` and `operations.archive.guidance`, as text the CLI echoes                                                                                             | `integrations/openspec/`                              |
| The upstream task line                             | `TASK_LINE_PATTERN` of `src/utils/task-progress.ts`: any list marker, one non-space marker in the box, only `x` or `X` is done, and `[x](...)` or `[x][...]` is a link, not a box | `index._BOX`, read by `openspec.box` (Task 7)         |
| The archive path                                   | `openspec/changes/archive/YYYY-MM-DD-<id>/`, fixed relative to the store root                                                                                                     | `adapters.skipped` (Task 4)                           |

The environment of every call sets `OPENSPEC_TELEMETRY=0`. `route_cli` adds it to `impact._environment()` (Earnest's environment less the variables of a test run already going). The tests' own calls use `tests/node.py`'s `openspec_env`, which also keeps OpenSpec's configuration and data directories out of the user's home: `XDG_CONFIG_HOME`, `XDG_DATA_HOME` and `XDG_CACHE_HOME` under `tmp_path`. Spike A found those variables break `mise` shims, so the tests set them for the `openspec` call only.

## Plan choices that are not gating

These are this plan's own readings, open to the maintainer's objection when reviewing it. None is recorded as decided.

- **P1. The fixture is `tests/fixtures/openspec-change/`, and it is synthetic.** It is the name #27 gives. A lockout feature, written for this repository, as the issues' own examples have it. No requirement, name or number comes from apartment-twin. The slugs are unique across fixtures, because the repository-level index reads every tracked file (M6 plan, Where the source is): `lockout-message` and `idle-timeout` replace `lockout-notice` and `session-expiry`, which `broken-links` and `seeded-change` already define, and a `git grep` of each `req~`, `feat~`, `goal~` and `tenet~` name of this fixture finds none outside it.
- **P2. The five EARS templates stay lowercase** in D2 and in the message. Only the keyword takes the second spelling (answer 1), and the suffix tells an agent in an OpenSpec repository that `SHALL` is also valid.
- **P3. The `feat`, `goal` and `tenet` items sit in `docs/intent.md`** of the fixture, as answers 3 and 4 recommend.
- **P4. Earnest adds nothing to OpenSpec's files except id lines and `Covers:` lines** under a requirement heading, and an id line and `Delivers:` line above a checkbox. `openspec/config.yaml` changes only through the snippet of Task 8.
- **P5. The gate and the real-CLI tests stay out of a bare `pytest` until Task 9,** by `--ignore=tests/steps/test_openspec_host.py` and `--ignore=tests/integration/test_openspec_ids.py` in `addopts`, as M7's Task 3 does for its module (E7 there). `test_openspec_ids.py` holds every test that runs the real CLI (strict validation of the fixture, `openspec list`), so the unit tier and a bare run stay Node-free. Run by path, either file still runs: checked on this branch's pytest with a scratch `addopts --ignore` and an explicit path. M7 (in v1) lands first and adds `addopts` to `pyproject.toml` as a list, so Task 3 extends that list to `addopts = ["--ignore=tests/steps/test_aidlc_fork.py", "--ignore=tests/steps/test_openspec_host.py", "--ignore=tests/integration/test_openspec_ids.py"]`. Task 9 removes M9's two entries, because the Node toolchain then belongs to `make test`, and leaves M7's.
- **P6. `openspec.py` is new and small.** `plan.py` is 1597 lines and `index.py` 466 already, so the OpenSpec logic goes in its own module, as the spike prototyped it (112 lines), and `plan.py` gains one seam, not a host flag tested in several functions: `Host` (`holds(intent, stage, path)`, `route_findings(intent)` and `produces`, the item types each stage slug holds, and from Task 7 `boxes(sources, intent)` and an optional `current_task(tasks, plans)` hook), `AIDLC` (the directory-prefix `holds`, the existing `route_findings` and `PRODUCES`, and the defaults of the last two: no boxes and no hook), and `Intent.host`, which defaults to `AIDLC` and which `stage_of`, `build`, `plan_findings` and `cli.py` call without asking which host it is. Box state is one precomputed value, `Boxes` (`marks`: the `Box` of each task id; `loose`: the boxes no task id line claims; both empty for an AI-DLC intent, whose host reads no boxes), carried on `Plan.boxes`, so `statuses` and `properties` read it from the plan they already take and no signature grows. `produces` is per-host data: the OpenSpec rows sit in the OpenSpec `Host`, the shared AI-DLC `PRODUCES` dict keeps only AI-DLC's, and `produces()` and the gap placer read `intent.host.produces`. The `tasks` first stage is data. `current_task` is unchanged: when it returns no task and no state file names one, `cli.py` calls the hook that an intent's host carries (`Host.current_task`, which is `openspec.in_flight` for OpenSpec and absent for AI-DLC, whose own reason then stands). `Box` and `Boxes` are value types in `plan.py`. The loader (with the `Host` it builds), `matches` (with `_glob`, the one glob matcher), `box`, `boxes`, `in_flight`, `checked_findings` and `untracked_findings` live in `openspec.py`, which imports `Host`, `Intent`, `Box`, `Boxes`, `parse_audit`, `_approval` and `_named` from `plan`. `plan.py` never imports `openspec.py`, and neither `adapters` nor `index` imports it or `plan`, so `change_of`, the one rule that says which change a file belongs to, lives in `index.py` (where `adapters` and `openspec` both read it, and where Task 10's `_spec_key` needs it), `change_dirs` in `adapters/__init__.py`, and no import cycle arises (`plan` imports `adapters`).
- **P7. One commit per task,** each staging its task's paths by name.
- **P8. `checked-unevidenced` runs under `--stage tasks` only.** A tick is a claim made at the `tasks` stage, so the stage check judges it. Raised by a plain `check`, the rule would add two warnings to the exact four-row table of the "supersedes" scenario, which goes green at Task 6 and must stay green at Task 7; the other fix, two more rows in that table, ties an overlay scenario to the box rule. `earnest plan` still shows each box beside its computed status, and `untracked-box` runs in every check: a box with no id line never reaches a stage.

## Fixture: `tests/fixtures/openspec-change/`

A synthetic lockout repository. Plain files, committed once on `main` at test time by `tests/conftest.py` (L6), with the overlays below left out of the base commit through `_OVERLAYS`. Drafted and run on 2026-11-25 against the spike prototypes (see "What was measured"), so the line numbers below are real; the findings tables in `04` are DERIVED from those runs, and Task 9 Step 2 confirms them against the combined tree.

| Path                                                                  | Holds                                                                                                             | Layer              |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------ |
| `docs/intent.md`                                                      | `tenet~safe-accounts~1`, `goal~stop-guessing~1`, `feat~lockout~1`                                                 | base               |
| `openspec/config.yaml`                                                | `schema: spec-driven` (Task 8's builder appends the snippet)                                                      | base               |
| `openspec/specs/lockout/spec.md`                                      | two requirements: lines 1 to 26 of the file below                                                                 | base               |
| `src/lockout.py`, `tests/test_lockout.py`                             | two tagged functions and two tagged tests                                                                         | base               |
| `defects/openspec/specs/lockout/spec.md`, `defects/src/lockout.py`    | the full files below: two more requirements, and a mistyped tag                                                   | overlay `defects`  |
| `archive/openspec/changes/archive/2026-11-01-add-lockout/`            | `proposal.md`, `specs/lockout/spec.md` (an `ADDED` block of the first two requirements at revision 1), `tasks.md` | overlay `archive`  |
| `change/openspec/changes/lockout-window/`                             | `.openspec.yaml`, `proposal.md`, `design.md`, `specs/lockout/spec.md`, `tasks.md`                                 | overlay `change`   |
| `approved/openspec/changes/lockout-window/audit/fixture-approvals.md` | one `GATE_APPROVED` row for `specs` that names its two items (below)                                              | overlay `approved` |
| `unbumped/openspec/changes/lockout-window/specs/lockout/spec.md`      | the delta with the first requirement's body edited and its revision left at 2                                     | overlay `unbumped` |
| `judge-verdicts.json`                                                 | canned stub verdicts for `lockout-message` and `lock-after-failures`, as in `seeded-change`                       | package only       |

The main spec, defects state (the base is its first 26 lines). Line 32 holds two sentences, and line 42 has no tag:

`openspec/specs/lockout/spec.md`:

<!-- prettier-ignore -->
```markdown
# lockout Specification

## Purpose
Lock an account that sees repeated failed logins, and tell its member.

## Requirements

### Requirement: Lock after failures
`req~lock-after-failures~1`
Covers: feat~lockout~1

When a member fails to log in three times, the system SHALL lock the account.

#### Scenario: Third failure
- **WHEN** a member fails to log in three times
- **THEN** the account is locked

### Requirement: Lockout message
`req~lockout-message~1`
Covers: feat~lockout~1

When an account is locked, the system SHALL send the member a notice.

#### Scenario: Notice sent
- **WHEN** an account is locked
- **THEN** the member receives a notice

### Requirement: Lockout audit
`req~lockout-audit~1`
Covers: feat~lockout~1

The system SHALL record each lockout in the audit log. The record names the member and the time.

#### Scenario: Audit entry
- **WHEN** an account is locked
- **THEN** the audit log holds an entry

### Requirement: Idle timeout
`req~idle-timeout~1`
Covers: feat~lockout~1

While a session is idle, the system SHALL expire it after ten minutes.

#### Scenario: Idle session
- **WHEN** a session is idle for ten minutes
- **THEN** it expires
```

The source, defects state (the base is its first 16 lines). Line 18 mistypes `lockout-message`:

`src/lockout.py`:

```python
"""SYNTHETIC lockout rules."""

FAILURE_LIMIT = 3


# [impl->req~lock-after-failures~1]
def is_locked(failures: int) -> bool:
    """Lock the account at the failure limit."""
    return failures >= FAILURE_LIMIT


# [impl->req~lockout-message~1]
def notice(member: str) -> str:
    """Name the member in the lockout notice."""
    return f"{member}: your account is locked"


# [impl->req~lock-message~1]
def unlock(member: str) -> str:
    """Unlock a member."""
    return f"{member}: unlocked"
```

The base tests (`tests/test_lockout.py`):

`tests/test_lockout.py`:

```python
"""SYNTHETIC lockout tests."""

from src.lockout import is_locked, notice


# [utest->req~lock-after-failures~1]
def test_the_third_failure_locks():
    assert is_locked(3)
    assert not is_locked(2)


# [utest->req~lockout-message~1]
def test_the_notice_names_the_member():
    assert "ada" in notice("ada")
```

The chain, `docs/intent.md`:

`docs/intent.md`:

<!-- prettier-ignore -->
```markdown
# Intent

`tenet~safe-accounts~1`
Needs: goal

Members' accounts stay safe from guessing.

`goal~stop-guessing~1`
Covers: tenet~safe-accounts~1
Needs: feat

An attacker cannot guess a password at speed.

`feat~lockout~1`
Covers: goal~stop-guessing~1
Needs: req

Repeated failed logins lock the account.
```

The in-flight change's delta, `change/openspec/changes/lockout-window/specs/lockout/spec.md`. Its MODIFIED block takes revision 2 and its ADDED block adds a requirement that nothing implements yet:

`openspec/changes/lockout-window/specs/lockout/spec.md`:

<!-- prettier-ignore -->
```markdown
## MODIFIED Requirements

### Requirement: Lock after failures
`req~lock-after-failures~2`
Covers: feat~lockout~1

When a member fails to log in three times, the system SHALL lock the account for the lockout window.

#### Scenario: Third failure
- **WHEN** a member fails to log in three times
- **THEN** the account is locked for the window

## ADDED Requirements

### Requirement: Lockout reset
`req~lockout-reset~1`
Covers: feat~lockout~1

When the lockout window ends, the system SHALL unlock the account.

#### Scenario: Window ends
- **WHEN** the lockout window ends
- **THEN** the account is unlocked
```

Its `tasks.md` (L2 layout: the id line and `Delivers:` directly above the box). Boxes sit at lines 5, 9 and 13:

`openspec/changes/lockout-window/tasks.md`:

<!-- prettier-ignore -->
```markdown
## 1. Lock window

`task~lock-for-window~1`
Delivers: req~lock-after-failures~2
- [x] 1.1 Lock the account for the window

`task~unlock-at-end~1`
Delivers: req~lockout-reset~1
- [x] 1.2 Unlock the account when the window ends

`task~window-docs~1`
Delivers: req~lockout-reset~1
- [ ] 1.3 Document the window
```

`proposal.md` holds `## Why` and `## What Changes` (3 lines each); `design.md` holds `## Context` and `## Decisions` (2 lines each); `.openspec.yaml` holds `schema: spec-driven`. The archived change is the same two requirements at revision 1 under `## ADDED Requirements`, with `tasks.md` of one ticked box, so that without the skip every one of its ids is a `duplicate` of the main copy.

The `approved` overlay is the approval of the `specs` stage with its two items named, in the shape of `seeded-change`'s own gate row. It is a fixture file that stands for the row the agent writes, through Task 8's guidance, after the human approves (answer 6). `next_bodies` freezes a body hash only for an item that a counting approval row names (answer 6), and an artifact approved "by openspec" names none, so without this row `unbumped-change` cannot fire on the fixture. The hash is the dummy of `seeded-change`'s row, and nothing in the scenario reads it.

`approved/openspec/changes/lockout-window/audit/fixture-approvals.md`:

<!-- prettier-ignore -->
```markdown
## Gate Approved
**Timestamp**: 2026-11-25T10:00:00Z
**Event**: GATE_APPROVED
**Stage**: specs
**User Input**: Approve
**Assessment Hash**: sha256:0000000000000000000000000000000000000000000000000000000000000000
**Items**: req~lock-after-failures~2, req~lockout-reset~1
**Approved By**: human
---
```

**Seeded defects**, each at a known file and line, in the `defects` state:

| Defect                         | File and line                                     | Finding                                                  |
| ------------------------------ | ------------------------------------------------- | -------------------------------------------------------- |
| A tag names no requirement     | `src/lockout.py:18`                               | `orphaned`, with "did you mean `req~lockout-message~1`?" |
| A requirement of two sentences | `openspec/specs/lockout/spec.md:29` (its id line) | `req-not-ears`, and 2 `gap` (no `impl`, no `utest`)      |
| A requirement no tag reaches   | `openspec/specs/lockout/spec.md:39`               | 2 `gap`, and the requirement lands untraced              |

**What was measured (2026-11-25).** The fixture was run in all its layers at once, against a scratch tree that combines spike B's `SHALL` patch with spike C's design C and the stacked-change extension: exit 1, 10 findings (`gap` 6, `orphaned` 1, `outdated` 2, `req-not-ears` 1) and no `duplicate`. The `outdated` findings sit at `src/lockout.py:6` and `tests/test_lockout.py:6`, because the delta's `lock-after-failures~2` overlays the main copy. Run on its own, the unmodified earnest gives 16 findings on the same tree, 3 of them `duplicate` and 1 `predated`, because of the archive, and spike D's prototype printed the intent and the two `checked-unevidenced` findings at `tasks.md:5` and `tasks.md:9` from a plain `check`. Plan choice P8 limits that rule to `--stage tasks`, so a plain `check` of the `change` state keeps the 4 findings above. The `approved` layer was not run: spike D's finding 6 ran the same freeze with an explicit row. `openspec validate --all --strict` exits 0, `openspec status --change lockout-window --json` reports all four artifacts done, and `openspec list --json` reports 2 of 3 tasks. No tree holding all four prototypes together was built: Task 9 Step 2 builds it by the tasks and confirms the DERIVED rows.

## Global Constraints

- **Layout and lint.** M2's bar applies: ruff (line length 120, complexity 10, five arguments, Google docstrings), `ruff format`, `mypy --strict`, and vulture at 80. A new module carries a module docstring that says what it reads.
- **No new runtime dependency** (L4). `openspec.py` uses `json`, `re`, `shutil` and `pathlib`, and runs the CLI through `impact._process`. The `openspec` CLI is a dev tool and a runtime tool of `plan`, found on `PATH` and never installed by earnest.
- **Fail, never skip.** A missing Node, a missing `openspec` or a missing `package.json` calls `pytest.fail` with a one-line message that names the cause. Neither `tests/node.py` nor the step module uses `pytest.skip`, `skipif` or `importorskip`. A CLI off its pin is `make node-check`'s to catch, which `make test` runs before pytest; the one helper checks presence, as M8's does. A route read with no CLI exits 2 and names `openspec`.
- **The unit tier stays Node-free.** Unit tests put a fake `openspec` script on a temporary `PATH`, as M8's plan does for `stryker`.
- **One fake-executable helper.** Every fake comes from `fake_executable(directory, name, script)` in `tests/conftest.py`: it makes `directory` if needed, writes `#!/bin/sh` and `script`, marks it `0o755` and returns its `Path`. It is hoisted from `fake_python` (`tests/unit/test_impact.py`, lines 91-95), which becomes `str(fake_executable(tmp_path, "python", script))`. M8 Task 2 Step 3 specifies it and the first plan to land hoists it; M9 imports it and writes no fake by hand, except the one whose shebang is the point of its test.
- **A scrubbed environment for every `openspec` call.** `OPENSPEC_TELEMETRY=0` always (`route_cli` adds it to `impact._environment()`). The tests' `openspec_env` is an allowlist, `PATH` with `node_modules/.bin` first and `HOME`, so no `PYTEST_*` or `GIT_*` variable of the test run reaches the CLI, plus `OPENSPEC_TELEMETRY=0`, `DO_NOT_TRACK=1`, `CI=1`, `NO_COLOR=1`, and the three `XDG_*` directories under the test's temporary directory. Never `openspec init` or `openspec install` against the user's home or this repository.
- **Stub judge only.** No `anthropic:` model, no network, no mutmut run in the M9 feature. `--judge` reads `judge-verdicts.json`.
- **Nothing from apartment-twin enters this repository** beyond the counts and rule names of this plan: no commit, date, file, requirement text, name, line number, SARIF, validator message, or description of what one change holds or does to another. The clone and the runs stay outside this repository.
- **Process.**
  - No agent `rm`s a path it did not create.
  - Each commit stages its task's paths by name, with no `--no-verify`.
  - `.pi-herdsman/` stays untracked.

## Review Focus

- **The exact keyword.** `tests/unit/test_ears.py` asserts that `Shall`, `sHALL`, `MUST`, `THE SYSTEM SHALL LOG IN.` and `The system SHALLOW log in.` do not parse, and that `The system SHALL reply that clients SHALL retry.` has the response `reply that clients SHALL retry`. The last row fails for an edit that changes only the final match (S4).
- **The judge reads what the file says.** The `SHALL` sentence reaches `question_text` unchanged, so `Requirement: When a member logs in, the system SHALL greet them.` appears with its case.
- **Fail, not skip.** `tests/unit/test_node.py` (written by M8 Task 2 Step 3) asserts `pytest.fail.Exception` for a missing Node and for a missing tool.
- **The bare run stays Node-free.** `addopts` leaves the step module and `tests/integration/test_openspec_ids.py` out until Task 9 (P5), and no test of the unit tier runs the real CLI.
- **`unbumped-change` rests on an approval row.** The scenario commits the `approved` overlay before the edit; the artifact's own approval "by openspec" names no item and freezes nothing. In use the row is written by the agent after the human approves (answer 6).
- **The overlay does not depend on order.** The result is the same for the sources in any order when no two delta copies share a revision (spike C's test, extended here to the findings). At a tie between two changes, the earlier copy in source order wins and the later one is the `duplicate`; that order is the sorted paths of `adapters.scan`, so two runs agree (a Task 6 test goes through `scan`). An equal revision across two changes is still `duplicate`. A delta never hides a duplicate among the main copies, a stale delta is compared with the main copy, not with the winner, and a delta copy with the first delta copy at its own revision, not with the winner, so the stacked-change reading never hides a missing bump.
- **One rule about where `openspec/` is.** The archive skip (Task 4), `layer` (Task 6) and a change as an intent (Task 5) all begin at the root `openspec/` (answers 8 and 11); a nested `openspec/` is plain files. A fixture of this repository that holds its own `openspec/` must not become an intent of this repository, which Task 5's `earnest check` run on the repository root checks.
- **A tick is not an edit, a changed title is.** The task body hash ignores the box and nothing else.
- **No CLI for non-OpenSpec repositories.** `earnest check` and `plan` on the existing fixtures never call `openspec`. A test runs the whole suite with no `openspec` on `PATH`.
- **Determinism.** Two runs give byte-identical SARIF, including the order of intents and tasks.
- **One runner.** `route_cli` goes through `impact._process` and `impact._environment()`, so it keeps the process-group kill and the environment filter of Earnest's other runs. `_process` reads its `timeout` default when it runs, so the patches of `MAP_TIMEOUT` in `test_impact.py` still bite.
- **Earnest reads the Markdown.** No finding takes its location from OpenSpec's JSON (SC2).

## Task order and the scenarios each turns green

The scenario titles are PROPOSED, and Task 0 writes them into `04`. They map to the exit behavior of `03` and to the done-when of the issues:

| Scenario                                                                                          | Done when of |
| ------------------------------------------------------------------------------------------------- | ------------ |
| "An OpenSpec repository with earnest ids passes OpenSpec's strict validation and earnest's check" | #20, #27     |
| "Two checks of an unchanged OpenSpec repository give identical SARIF"                             | #27 (SC1)    |
| "Each requirement lands at one trace level, with a located reason for each level it missed"       | #27 (SC3)    |
| "A tag naming a missing requirement and a requirement no tag reaches appear at file and line"     | #27 (SC2)    |
| "A requirement of more than one sentence raises req-not-ears at its line, and SHALL is accepted"  | #21, #27     |
| "An archived change is not read"                                                                  | #23          |
| "A change in flight supersedes the main copy, and tags at the old revision are flagged"           | #23 (SC5)    |
| "A change in flight is an intent with its stages and their status"                                | #22          |
| "A body edited without a new revision raises unbumped-change after the stage check"               | #22, #27     |
| "A ticked box whose requirement is below evidenced raises checked-unevidenced at the box"         | #24          |
| "OpenSpec's apply instructions carry earnest's guidance"                                          | #25          |

The guard "fails rather than skips" is tested at the unit tier, in `tests/unit/test_node.py`, because a scenario cannot remove its own Background.

| Task | Issue | Content                                                                                          | Depends on                                  | Answers     | Scenarios green after it                      |
| ---- | ----- | ------------------------------------------------------------------------------------------------ | ------------------------------------------- | ----------- | --------------------------------------------- |
| 0    | #19   | The docs commit: decisions, `04`'s M9 section is already drafted, rows of `00`, `01`, `02`, `03` | the maintainer                              | all         | none                                          |
| 1    | #21   | `SHALL` in `ears.py`, with tests and the `01` Grammar and D2 edits                               | none                                        | 1           | none (unit tier)                              |
| 2    | #26   | `openspec_env` and the `openspec` checks, on M8's toolchain (M8 Task 1 pins the CLI)             | Task 0 Step 1 (answer 12); M8 Tasks 1 and 2 | 12          | none                                          |
| 3    | #20   | The fixture's base and `defects` layers, ids and the chain, the gate red                         | 1, 2                                        | 3, 4        | scenarios 1 to 5                              |
| 4    | #23   | `openspec/changes/archive/` skipped                                                              | 3                                           | 8           | "An archived change is not read"              |
| 5    | #22   | A change as an intent: route, stage mapping, approvals, record                                   | 3, 4                                        | 5, 6, 7, 11 | scenarios 8 and 9                             |
| 6    | #23   | Delta overlay and stacked changes                                                                | 4                                           | 8           | "A change in flight supersedes the main copy" |
| 7    | #24   | `tasks.md` boxes, the two rules, the current task                                                | 5, 6                                        | 10          | the `checked-unevidenced` scenario            |
| 8    | #25   | The guidance snippet and its scenario                                                            | 2, 5                                        | 13          | the apply-instructions scenario               |
| 9    | #27   | The exit gate: all 11 green, the two `addopts` entries removed, CI, lint, the pre-PR review      | 6, 7, 8                                     | none new    | all 11                                        |
| 10   | #23   | Deferred, outside the exit path: REMOVED handling                                                | 6                                           | 9           | none                                          |

Order. Task 1 needs no wait (answer 1 is accepted) and runs beside Task 0. Task 2 waits for Task 0 Step 1 and for M8 Tasks 1 and 2, whose toolchain and helper it builds on. Tasks 6 and 7 both edit `index.py` (6 the layer overlay, 7 `_body_hash`) and run one after the other, 6 then 7. Task 8 needs only the `change` overlay that Task 5 writes, so it may run beside Tasks 6 and 7. Task 10 is not on the exit path: Task 9 does not wait for it.

**Regression expectations:** for Tasks 1 to 8 the regression run is `rtk proxy uv run pytest; echo $?` in `packages/earnest/`, and its evidence is the printed code. From Task 3 on, `addopts` leaves the M9 module and `tests/integration/test_openspec_ids.py` out of it. It stays green at the count the M9 branch records at the start of Task 1, plus the tests each task adds. Each task records its exact count in this plan.

## File Structure

| Path                                                                                                                                    | Responsibility                                                                                                                                                                                                                                                                                                                                                                               | Task       |
| --------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `docs/superpowers/plans/2026-11-25-openspec-host.md`                                                                                    | this plan: the decisions (Task 0), then each task's counts and notes                                                                                                                                                                                                                                                                                                                         | 0 to 9     |
| `docs/design/00-project-intent.md`, `01-logic-design.md`, `02-structural-design.md`, `03-implementation-plan.md`, `04-bdd-test-plan.md` | the ratification, "Adopting OpenSpec", the module rows, M9 in `03`, `04`'s M9 section                                                                                                                                                                                                                                                                                                        | 0, 1       |
| `packages/earnest/src/earnest/ears.py`                                                                                                  | `_SHALL`, the message suffix                                                                                                                                                                                                                                                                                                                                                                 | 1          |
| `packages/earnest/tests/unit/test_ears.py`, `tests/unit/test_judge.py`                                                                  | the `SHALL` rows and the judge's span                                                                                                                                                                                                                                                                                                                                                        | 1          |
| `CLAUDE.md`                                                                                                                             | the Build section: the M9 feature runs the pinned `openspec` and needs Node 22.20 or later (M8 Task 6 Step 4 words the Node line)                                                                                                                                                                                                                                                            | 2          |
| `packages/earnest/tests/node.py`, `tests/unit/test_node.py`                                                                             | `openspec_env` and its test; the rest of the helper is M8 Task 2 Step 3's                                                                                                                                                                                                                                                                                                                    | 2          |
| `packages/earnest/tests/fixtures/openspec-change/`                                                                                      | the base and the overlays `defects`, `archive`, `change`, `approved`, `unbumped`, and `judge-verdicts.json`                                                                                                                                                                                                                                                                                  | 3 to 8     |
| `packages/earnest/tests/conftest.py`                                                                                                    | the overlay names `defects`, `archive`, `approved` and `unbumped` added to `_OVERLAYS` (`change` and `judge-verdicts.json` are there already); no new builder, the steps use `fixture_repo` and `commit_on_main`                                                                                                                                                                             | 3          |
| `packages/earnest/tests/integration/test_openspec_ids.py`                                                                               | the tests that run the real CLI: strict validation and `check` on the base and `defects` layers, and `openspec list` against the box count; left out of a bare run by `addopts` until Task 9                                                                                                                                                                                                 | 3, 7       |
| `packages/earnest/tests/features/openspec_host.feature`                                                                                 | the 11 scenarios, copied verbatim from `04`                                                                                                                                                                                                                                                                                                                                                  | 3          |
| `packages/earnest/tests/steps/test_openspec_host.py`                                                                                    | the steps; the exit command                                                                                                                                                                                                                                                                                                                                                                  | 3 to 9     |
| `packages/earnest/pyproject.toml`                                                                                                       | M9's two `--ignore` entries in `addopts` (merged with M7's), added and then removed                                                                                                                                                                                                                                                                                                          | 3, 9       |
| `packages/earnest/src/earnest/adapters/__init__.py`                                                                                     | `skipped` for the archive, `layer`, `change_dirs` (from `index.change_of`) and the change directories as record directories                                                                                                                                                                                                                                                                  | 4, 5, 6    |
| `packages/earnest/src/earnest/openspec.py`                                                                                              | `route_cli`, `matches`, `load_openspec` (and its `Host`, with the OpenSpec `produces` rows, `boxes` and `in_flight`), `box`, `boxes`, `in_flight`, `checked_findings`, `untracked_findings`                                                                                                                                                                                                  | 5, 7       |
| `packages/earnest/src/earnest/plan.py`, `cli.py`                                                                                        | `Host` (with `produces`; Task 7: `boxes`, `current_task`), `AIDLC`, `Intent.host` (read by `stage_of`, `build`, `plan_findings`, `produces`), `Box`, `Boxes`, `Plan.boxes` (read by `statuses`, `properties`), the `tasks` first stage, the `aidlc-state.md` messages; in `cli.py` the boxes, the host's `current_task` fallback and the `--stage tasks` scope of `checked-unevidenced` (P8) | 5, 7       |
| `packages/earnest/src/earnest/index.py`, `structural.py`                                                                                | `archived` (Task 4) and `change_of` (Task 5), the layer overlay and `_duplicates` (Task 6), `_BOX` and `_body_hash` (Task 7); `Removal`, `Item.heading`, `Item.section`, `Index.removed` and the REMOVED branches of `defined`, `_duplicates` and `_links` (Task 10)                                                                                                                         | 6, 7, 10   |
| `packages/earnest/src/earnest/reporter.py`                                                                                              | `earnest/checked-unevidenced`, `earnest/untracked-box`, `earnest/no-requirements` in `RULES`                                                                                                                                                                                                                                                                                                 | 5, 7       |
| `packages/earnest/tests/unit/test_openspec_layers.py`, `tests/unit/test_openspec.py`                                                    | skip, layers (REMOVED in Task 10); change directories, route, boxes                                                                                                                                                                                                                                                                                                                          | 4 to 7, 10 |
| `integrations/openspec/`                                                                                                                | `config.snippet.yaml` and `README.md`                                                                                                                                                                                                                                                                                                                                                        | 8          |

## Known limits

- **One pin, one repository's worth of evidence.** Every prototype ran at OpenSpec 2.1.1, and 2.2.0 was read for its source only (S8, answer 12). The real-world run is one repository.
- **Not exercised end to end:** a real `openspec archive` against the fixture (the archived layer is written the way OpenSpec leaves it, and spike A counted the 6 duplicates a real archive left), RENAMED followed by REMOVED, namespaced change folders, `openspec sync`, custom task files (S15). REMOVED is deferred to Task 10, outside the exit path (`03` defers it too): until it lands a REMOVED block with an id line at the main revision is no duplicate (main stands), and a tag on a removed requirement is not flagged.
- **The gate uses the stub judge and no mutmut.** `checked-unevidenced` fires on any requirement below `evidenced`, and the fixture's are below it. The first real `check --judge --evidence` over an OpenSpec repository is the maintainer's act after this plan.
- **Node is needed for `earnest plan` on an OpenSpec repository** (answer 7, source A). `earnest check` on one needs it only to name the route of a change.
- **`checked-unevidenced` comes from a stage check of `tasks` only** (P8): a plain `check` shows the box beside the computed status in `plan` and raises `untracked-box`, and nothing else about a tick.
- **Several changes in flight give no current task** (answer 10): the out-of-task check and impact need `--task`.
- **`req-not-ears` will dominate adopting repositories** (answer 2, R9). The finding is correct by D2, and the count is the adopter's to work down.
- **Earnest writes no approval, and the agent's row is a claim.** Under answer 6 (B) an artifact's presence is the approval "by openspec", and a `GATE_APPROVED` row in `<change>/audit/*.md` overrides it. The agent writes the row, through the #25 guidance, after the human approves; the guidance is advisory, and neither OpenSpec nor earnest checks that the human approved first, so `Approved By: human` is only what the agent wrote.
- **Strict's 500-character limit** counts the id line (X2). Earnest cannot lengthen a requirement past it for the author.
- **No id-drift check** (answer 9): an id changed without the rename it implies is not flagged.
- **Pins and hosts.** Only CI pins Node (answer 12). The host this plan was written on has no `pnpm`, so `make lint-file` for `.md` cannot run here; this plan was linted with `npx --yes markdownlint-cli2` for that reason alone, and its tasks use `make lint-file`, as M8's do.

## Tasks

### Task 0: The docs commit (#19)

**Files:** Modify this plan, `docs/design/00-project-intent.md`, `docs/design/01-logic-design.md`, `docs/design/02-structural-design.md`, `docs/design/03-implementation-plan.md` and `docs/design/04-bdd-test-plan.md`.

This task is paper. It runs beside Task 1, Task 2 waits for its Step 1 (answer 12), and Tasks 3 to 10 wait for it.

- [x] **Step 1:** Record the fourteen decisions (DECIDED (user, 2026-11-25), each in its answer above). `SHALL` is accepted and the rest follow:
  1. The scope: A, exactly `shall` or `SHALL`, no `MUST`.
  2. Multi-sentence: A, `req-not-ears` stays an error.
  3. Ids: A, inline req ids, with the `feat` items in `docs/intent.md`.
  4. Chain root: A, tenet and goal required in `docs/intent.md`.
  5. Zero requirements: B, a warning `earnest/no-requirements`.
  6. Approvals: B, hybrid; the `GATE_APPROVED` rows are written by the agent, through the #25 guidance, after the human approves.
  7. Route from the CLI (`openspec status --json`); frontier B, a skipped stage is not the frontier.
  8. Skip the archive; the overlay is design C plus the stacked-change extension.
  9. The bundle as written (stale delta reported as outdated, duplicate kept, REMOVED deferred to Task 10, id-drift deferred).
  10. A, the task body hash ignores the box; `checked-unevidenced` and `untracked-box` are warnings.
  11. A, `openspec/` at the repository root only.
  12. Pin 2.1.1; fail, never skip.
  13. A, `operations.*.guidance` in `config.yaml`.
  14. Ratify OpenSpec as the second host; M9 is outside v1 (`04` stays "nine in all"); the fixture stays synthetic.
- [ ] **Step 2:** Read `04`'s M9 section against the decisions. It is already written, with its Gherkin marked PROPOSED. The scenarios that depend on an answer: "an intent with its stages" and "unbumped-change after the stage check" on answers 6 and 7; the `checked-unevidenced` scenario on answer 10; "supersedes the main copy" on answers 8 and 9; "more than one sentence" on answer 2. Change a scenario only to match a decision, and keep its title. The maintainer's approval of the plan is not the ratification `04`'s "Fixed for the loop" asks for.
- [ ] **Step 3:** `00`. In T8, "an established delivery lifecycle" becomes "established delivery lifecycles, AI-DLC and OpenSpec as a second host". In Scope, add the bullet "A second delivery method, OpenSpec, read as a host: its main specs, change deltas, archive and `tasks.md`, under the same trace, judge and evidence layers." Ratification is the maintainer's act; this edit records it with its date.
- [ ] **Step 4:** `01`. Add the section "Adopting OpenSpec" after "Adopting AI-DLC", in the same shape. It states, one short paragraph each, the answers to: ids and where `feat` items sit (answer 3, with its three corrections), the chain root (4), the layers and the archive skip (8, 9), a change as an intent, its route and approvals (6, 7, 11), the box and the two rules (10), the guidance (13). Add a table of what earnest reads: `openspec/specs/<capability>/spec.md` is the main layer; `openspec/changes/<id>/specs/**` is the delta layer; `openspec/changes/archive/**` is skipped; `openspec/changes/<id>/` is an intent's record directory; `tasks.md` boxes are `task` items. Also: the three rule ids in the Findings table (`earnest/checked-unevidenced`, raised by a stage check of `tasks` only (P8), `earnest/untracked-box`, and `earnest/no-requirements`, answer 5); step 2 of the Revision lifecycle, for answer 10's body hash ("a task's body hash ignores its checkbox"); and Open questions rows resolved by the answers. Task 1 has already changed Grammar and D2.
- [ ] **Step 5:** `02`. In Module boundaries: a row for `openspec.py`; the archive skip, `layer` and change record directories under `adapters/`; the stage-to-glob mapping under `plan.py`; the layer overlay under `index.py` and `structural.py`; the three rules under `reporter.py`. In the File and directory tree: `openspec.py`, `integrations/openspec/`, `fixtures/openspec-change/`, and `tests/node.py` if M8's Task 0 has not already listed it. L5 needs no edit: M8's Task 0 already says that Node tools enter the tests through a lockfile, for Jest, StrykerJS and the `openspec` CLI of M9.
- [ ] **Step 6:** `03`, M9: the status line says DECIDED 2026-11-25 (ratified, outside v1) and the Critical path names the decisions (both written with this plan's decisions; check them), and link this plan on the task-plan line. In `04`'s milestone table the M9 row and the Scope (v1) edits are already in place.
- [ ] **Step 7:** Check #19's done-when: `rtk proxy grep -n 'Adopting OpenSpec' docs/design/01-logic-design.md; echo $?` prints a hit and `0`, and every section that M9's "Context to load" in `03` names exists (grep each heading).
- [ ] **Step 8:** Run `LINT_FILE=<path> make lint-file` on each changed file and check each exit code with `rtk proxy`. Commit `docs: M9 openspec_host plan and gating answers`.

### Task 1: `SHALL` in the EARS parser (#21)

**Files:** Modify `packages/earnest/src/earnest/ears.py`, `packages/earnest/tests/unit/test_ears.py`, `packages/earnest/tests/unit/test_judge.py`, `docs/design/01-logic-design.md` and `docs/design/04-bdd-test-plan.md`.

Built on spike B (measured 2026-11-25 at `ae4136c`). The code below is spike B's core, and Steps 2 and 6 hold every test and doc edit, so this task needs nothing else. It builds answer 1's scope (option A, DECIDED 2026-11-25).

- [ ] **Step 1:** Run `rtk proxy uv run pytest tests/unit/test_ears.py tests/unit/test_judge.py -q; echo $?` from `packages/earnest/`. Expected: `0`. Record the counts here.
- [ ] **Step 2:** Write the failing tests. In `test_ears.py`, after `test_each_template_parses_with_its_clauses`:

  ```python
  @pytest.mark.parametrize(
      ("body", "expected"),
      [
          ("The system SHALL log in.", {"response": "log in"}),
          ("When a member logs in, the system SHALL greet them.", {"when": "a member logs in", "response": "greet them"}),
          ("While the shop is closed, the system SHALL refuse orders.", {"while": "the shop is closed", "response": "refuse orders"}),
          ("If the card fails, then the system SHALL say so.", {"if": "the card fails", "response": "say so"}),
          ("Where coupons are on, the system SHALL take them.", {"where": "coupons are on", "response": "take them"}),
          (
              "Where coupons are on, while the cart is open, when a code is typed, the system SHALL apply it.",
              {"where": "coupons are on", "while": "the cart is open", "when": "a code is typed", "response": "apply it"},
          ),
          ("The system SHALL NOT log in.", {"response": "NOT log in"}),
      ],
  )
  def test_each_template_parses_with_shall_in_capitals(body, expected):
      assert kinds(body) == expected


  @pytest.mark.parametrize(
      ("body", "response"),
      [
          ("The system SHALL do x and the cache SHALL do y.", "do x and the cache SHALL do y"),
          ("The system SHALL do x and the cache shall do y.", "do x and the cache shall do y"),
          ("The system shall do x and the cache SHALL do y.", "do x and the cache SHALL do y"),
          ("The system SHALL reply that clients SHALL retry.", "reply that clients SHALL retry"),
      ],
  )
  def test_the_response_starts_after_the_first_keyword_in_either_case(body, response):
      assert kinds(body) == {"response": response}


  def test_a_sentence_keeps_the_keyword_case_it_was_written_in():
      sentence = ears.parse("When the word SHALL is typed, the system SHALL echo it.")
      assert sentence is not None
      assert sentence.text == "When the word SHALL is typed, the system SHALL echo it."
  ```

  Add these rows to the list of `test_a_body_that_is_not_one_ears_sentence_does_not_parse`: `"The system MUST log in."`, `"The system Shall log in."`, `"The system sHALL log in."`, `"THE SYSTEM SHALL LOG IN."`, `"WHEN a member logs in, the system SHALL greet them."`, `"The system SHALL log in. The system SHALL log out."`, `"When a member logs in the system SHALL greet them."`, `"The system SHALLOW log in."`. In `test_req_not_ears_sits_at_the_id_line_and_lists_the_five_templates_in_order` add:

  ```python
  assert "`shall` or `SHALL`" in found.message
  ```

  In `test_judge.py`, add `test_a_requirement_written_with_shall_in_capitals_is_asked_with_its_clause_spans`: the `REQS` of that module with `the system shall greet them` replaced by `the system SHALL greet them`; assert `question_text` holds `Requirement: When a member logs in, the system SHALL greet them.\nClauses:\n` and `\nwhen: a member logs in\nresponse: greet them\nCode regions:\n`.

- [ ] **Step 3:** Run `rtk proxy uv run pytest tests/unit/test_ears.py tests/unit/test_judge.py -q; echo $?`. Expected: the `SHALL` rows and the message and judge tests fail, and a non-zero code.
- [ ] **Step 4:** In `ears.py` add the constant above `_EARS` and use it in the two places the regex names the keyword. A change to the match alone leaves the lookahead blind to `SHALL` (S4):

```python
# The keyword is `shall`, or `SHALL` as OpenSpec writes it; no other case (`Shall`) counts.
_SHALL = "(?:shall|SHALL)"
_EARS = re.compile(
    rf"(?:Where (?P<where>{_CLAUSE}), )?"
    rf"(?:(?<![^ ])[Ww]hile (?P<while>{_CLAUSE}), )?"
    rf"(?:(?<![^ ])[Ww]hen (?P<when>{_CLAUSE}), |(?<![^ ])[Ii]f (?P<if>{_CLAUSE}), then )?"
    rf"(?<![^ ])[Tt]he (?P<system>(?:(?! {_SHALL} )[^,.!?]|[.!?](?! ))+) {_SHALL} (?P<response>[^.!?]*(?:[.!?](?! )[^.!?]*)*)\."
)
```

The `parse` docstring says "a `shall` or `SHALL` with no system before it". The message in `findings` ends with the suffix "(the keyword is `shall` or `SHALL`)" after the templates, as one more string in the f-string's parentheses. `TEMPLATES` stays as it is.

- [ ] **Step 5:** Run Step 3's command, then `rtk proxy uv run mypy --strict src/; echo $?`, `rtk proxy uv run ruff check src/ tests/; echo $?`, `rtk proxy uv run ruff format --check src/ tests/; echo $?`, `rtk proxy uv run vulture; echo $?` and the regression run. Expected: `0` from each, at Step 1's count plus 21 (7 and 4 parametrized rows, 1 test, 8 rows, 1 judge test; the message assertion adds none).
- [ ] **Step 6:** The docs. The maintainer decided on 2026-11-25 that the scope is the exact keyword, no `MUST` (answer 1, A), and ratified M9 (answer 14), so the `01` edits below carry no PROPOSED mark; the wording of D2's Decision, Alternatives and Rationale sentences and of the Grammar line is still this plan's, for him to read in the commit. In `01`: the Grammar line becomes `"the" , system , ( "shall" | "SHALL" ) , response , "." ;`; after "those spans are what the judge asks about." add "The keyword is `shall` or `SHALL`, so a body written the OpenSpec way parses; any other case (`Shall`) and `MUST` are not the keyword, and every other word keeps its case rule. The parse keeps the case the author wrote, so the judge reads the sentence as the file has it."; the findings-table row for `earnest/req-not-ears` ends "the message lists the five templates and says the keyword is `shall` or `SHALL`"; D2's Decision gains "The message adds that the keyword is `shall` or `SHALL`.", its Alternatives "read the keyword in any letter case.", and its Rationale "The keyword takes `SHALL` as well as `shall` because OpenSpec's validator requires `SHALL` in that exact case, and no other case, so one body satisfies both tools; `MUST` stays out until a corpus needs it." In `04`: the table row 19 of the M4 `seeded-change` list reads "not EARS: no `shall` or `SHALL`; `req-not-ears` at line 17"; the Messages bullet says the message "lists the five templates of D2 in that order, and says the keyword is `shall` or `SHALL`"; the unit-tier bullet starts "each EARS template with `shall` and with `SHALL`, and its spans, a keyword in another case or `MUST` (not EARS), a body broken over lines, ...". Find each place with `grep -n`, since line numbers have moved. The five templates in D2 and in `04`'s scenario table stay lowercase.
- [ ] **Step 7:** Run `LINT_FILE=<path> make lint-file` on both docs, and commit `feat: accept SHALL as the EARS keyword, as OpenSpec writes it`.

**Done when:** `test_ears.py` covers every template with `SHALL`, the lowercase tests stay green, and `make test` is green. `01`'s edits carry no PROPOSED mark, as Step 6 says: the maintainer ratified M9 on 2026-11-25.

### Task 2: `openspec_env` and the pinned CLI on M8's toolchain (#26)

**Files:** Modify `packages/earnest/tests/node.py`, `packages/earnest/tests/unit/test_node.py` and `CLAUDE.md`.

M8 lands first, so its files exist. M8 Task 1 made the manifest with `@fission-ai/openspec` at 2.1.1, the lockfile, `.nvmrc`, `.npmrc`, the `node-install` and `node-check` targets, the CI steps and the ignores. M8 Task 2 Step 3 made `tests/node.py` (`tools_path`, `require_tools`, `without_node_tools`), `tests/tools.py` and `fake_executable`. This task copies none of it and adds `openspec_env` alone (Shared with M8).

- [ ] **Step 1:** Run `rtk proxy make -C packages/earnest node-install; echo $?` (`0`) and `rtk proxy make -C packages/earnest node-check; echo $?` (a line `@fission-ai/openspec 2.1.1`, `0`). If either fails, M8 Tasks 1 and 2 have not landed: stop, and do not recreate them here. The negative control asserts the message, since `make` exits 2 for any failed recipe and the code alone would pass for another cause: `rtk proxy make -C packages/earnest node-check NODE_MODULES=/nonexistent 2>&1 | grep -c "@fission-ai/openspec is missing: run make node-install"` prints `1`.
- [ ] **Step 2:** Write the failing tests in `tests/unit/test_node.py`, each against a temporary package directory whose `node_modules/.bin/openspec` comes from `fake_executable`:
  - `test_a_missing_openspec_fails_and_names_the_cause` (`require_tools("openspec")` raises `pytest.fail.Exception`; the message names `openspec` and `make node-install`);
  - `test_the_environment_turns_telemetry_off_and_keeps_openspec_out_of_home` (`OPENSPEC_TELEMETRY=0`, `DO_NOT_TRACK=1`, `CI=1`, `NO_COLOR=1`, the three `XDG_*` paths below the given directory, `node_modules/.bin` first on `PATH`, and no `PYTEST_CURRENT_TEST` of the running test).
- [ ] **Step 3:** Add `openspec_env` to `tests/node.py`. It is an allowlist built on `tools_path`, not a copy of `os.environ`, so no variable of the test run reaches the CLI:

  ```python
  def openspec_env(home: Path) -> dict[str, str]:
      """Return the environment of an `openspec` call: telemetry off, its configuration and data below `home`, nothing else inherited."""
      return {
          "PATH": tools_path(os.environ["PATH"]),
          "HOME": os.environ["HOME"],
          "OPENSPEC_TELEMETRY": "0",
          "DO_NOT_TRACK": "1",
          "CI": "1",
          "NO_COLOR": "1",
          "XDG_CONFIG_HOME": str(home / "config"),
          "XDG_DATA_HOME": str(home / "data"),
          "XDG_CACHE_HOME": str(home / "cache"),
      }
  ```

- [ ] **Step 4:** Run `rtk proxy uv run pytest tests/unit/test_node.py -q; echo $?`: red before Step 3, `0` after. `CLAUDE.md`'s Build section (M8 Task 6 Step 4 words the Node line) also says that the M9 feature runs the pinned `openspec` and needs Node 22.20 or later. Run the regression run, then commit `chore: openspec_env, the environment of an openspec call`.

**Done when:** `make test` prints `@fission-ai/openspec 2.1.1` through `node-check`, and the CI `test-python` job runs the same line (both M8 Task 1's); a missing CLI makes `node-check` name it and exit 2, and `require_tools("openspec")` fails with the same cause; the pin is read from `package.json` alone. The M9 feature's own failure on a missing CLI is Task 3's first step.

### Task 3: Ids in specs, the fixture, and the gate, red (#20)

**Files:** Create `packages/earnest/tests/fixtures/openspec-change/` (the base, the `defects/` overlay and `judge-verdicts.json`), `packages/earnest/tests/integration/test_openspec_ids.py`, `packages/earnest/tests/features/openspec_host.feature` and `packages/earnest/tests/steps/test_openspec_host.py`. Modify `packages/earnest/tests/conftest.py` and `packages/earnest/pyproject.toml`.

- [ ] **Step 1:** Run `rtk proxy grep -n '@given\|@when\|@then\|_OVERLAYS\|def fixture_repo\|def _commit' packages/earnest/tests/conftest.py; echo $?` and read one M5 step module (`tests/steps/test_evidence_check.py`). List here the shared steps this feature reuses: the SARIF-table step, the summary step, the exit-code steps and the stub judge step. Nothing new is invented for a step that already exists.
- [ ] **Step 2:** Write the failing integration tests in `tests/integration/test_openspec_ids.py`, each building the fixture with `fixture_repo("openspec-change")` and `commit_on_main(repo, "openspec-change", layer)` of `conftest.py` (no new builder) and calling `require_tools("openspec")` first. The file holds every test that runs the real CLI, which is why `addopts` leaves it out of a bare run (Step 5, P5):
  - `test_the_base_fixture_passes_strict_validation`: `openspec validate --all --strict` in the base repository, with `openspec_env(tmp_path)`; exit 0.
  - `test_the_base_fixture_has_both_requirements_traced_and_no_finding`: `earnest check` exits 0, the SARIF holds no result, the summary reads `traced 100%, judged 0%, evidenced 0%; requirements: 2`.
  - `test_the_defects_layer_raises_exactly_the_seeded_findings`: with `defects` committed, the SARIF holds exactly these six: `earnest/orphaned` at `src/lockout.py:18`; `earnest/req-not-ears` at `openspec/specs/lockout/spec.md:29`; `earnest/gap` twice at `:29` and twice at `:39` of the same file. Every one is an error.
  - `test_a_feat_line_in_a_delta_is_not_needed`: the chain lives in `docs/intent.md`, so no file under `openspec/changes/` holds a `feat~` line (a text search of the committed tree).

- [ ] **Step 3:** Run `rtk proxy uv run pytest tests/integration/test_openspec_ids.py -q; echo $?`. Expected: fail on the missing fixture, non-zero.
- [ ] **Step 4:** Write the fixture from the Fixture section above, with the exact files: the base (`docs/intent.md`, `openspec/config.yaml`, the first 26 lines of the spec, the first 16 lines of `src/lockout.py`, the base tests), and `defects/openspec/specs/lockout/spec.md` and `defects/src/lockout.py` as full files. Add `"defects"`, `"archive"`, `"approved"` and `"unbumped"` to `_OVERLAYS` (conftest.py:99-111); `"change"` and `"judge-verdicts.json"` are in it already, and `_OVERLAYS` applies to every fixture by its top-level names. Write `judge-verdicts.json` as in `seeded-change`, with an `implemented` and `tested` verdict `satisfied` for `lockout-message` and `lock-after-failures`. No builder is added: `fixture_repo("openspec-change")` copies the base less the overlays and commits it, and `commit_on_main(repo, "openspec-change", layer)` copies one overlay over the tree and commits it on top, which is the loop a new builder would repeat. Run Step 3's command: expect `0`.
- [ ] **Step 5:** Copy the 11 scenarios of `04`'s M9 section verbatim into `tests/features/openspec_host.feature`. Write `tests/steps/test_openspec_host.py` with `scenarios("openspec_host.feature")`, the Background's step (which calls `require_tools("openspec")` and fails, never skips, naming the cause), and the steps for scenarios 1 to 5. Extend the `addopts` list that M7's Task 3 added to `pyproject.toml`'s `[tool.pytest.ini_options]` with the two M9 entries (the single list is in P5).
- [ ] **Step 6:** Run `rtk proxy uv run pytest tests/steps/test_openspec_host.py -q; echo $?`. Expected: scenarios 1 to 5 pass, 6 to 11 fail on an undefined step, non-zero. Then `rtk proxy uv run pytest; echo $?`, which ignores the module and the integration file: expect `0` with no Node on the `PATH`. Run the repository-level `rtk proxy uv run --project packages/earnest earnest check 2>&1 >/dev/null | grep -c '^intent '` before and after the fixture lands: the count of intents must not rise (the fixture's `openspec/` is not at the root).
- [ ] **Step 7:** Record the counts here. Tell the maintainer the three corrections of answer 3 (they belong in #20's text, a GitHub write). Commit `test: the openspec-change fixture, with earnest ids that OpenSpec's strict validation accepts`.

**Done when** (#20): the base spec passes `openspec validate --all --strict`, and passes `earnest check` with each requirement at `traced` and no `orphaned` finding; scenarios 1 to 5 are green and 6 to 11 are red.

### Task 4: Skip the archive (#23, first half)

**Files:** Modify `packages/earnest/src/earnest/index.py` and `packages/earnest/src/earnest/adapters/__init__.py`. Create `packages/earnest/tests/unit/test_openspec_layers.py`. Create the fixture overlay `packages/earnest/tests/fixtures/openspec-change/archive/`. Modify `packages/earnest/tests/steps/test_openspec_host.py`.

Built on spike C's design A and C, measured on 2026-11-25 (the code below is its skip half, narrowed to the root (answer 11); `layer` waits for Task 6). The archived copy of a requirement is the main copy's own history, and 299 of 318 corpus requirements have one (S6), so skipping it is what turns 393 corpus duplicates into 0. On the drafted fixture, base plus the archive, spike B's tree gives exit 1 and 2 `duplicate`, and the same tree with the skip gives exit 0 and no finding.

- [ ] **Step 1:** Write the failing test in `tests/unit/test_openspec_layers.py`:

```python
@pytest.mark.parametrize(
    ("path", "skipped"),
    [
        ("openspec/changes/archive/2026-11-01-add-lockout/specs/lockout/spec.md", True),
        ("openspec/changes/archive/2026-11-01-add-lockout/tasks.md", True),
        ("packages/x/openspec/changes/archive/2026-11-01-a/proposal.md", False),
        ("openspec/changes/lockout-window/specs/lockout/spec.md", False),
        ("openspec/specs/lockout/spec.md", False),
        ("docs/archive/notes.md", False),
        ("openspec/changes/archived-notes.md", False),
    ],
)
def test_only_files_below_the_root_openspec_archive_are_skipped(path, skipped):
    assert adapters.skipped(path, ()) is skipped
```

- [ ] **Step 2:** Add the fixture overlay `archive/openspec/changes/archive/2026-11-01-add-lockout/` from the Fixture section, and bind scenario 6's steps: Given the repository with the `archive` layer; When the coding agent runs `earnest check`; Then the check exits zero, the SARIF log holds no finding, and the summary leads with "traced 100%, judged 0%, evidenced 0%; requirements: 2". Run `rtk proxy uv run pytest tests/unit/test_openspec_layers.py tests/steps/test_openspec_host.py -k "archive" -q; echo $?`. Expected: the two `True` rows fail, the scenario fails with 2 `duplicate` findings (the red measured above), and a non-zero code.
- [ ] **Step 3:** In `index.py` (add `from pathlib import PurePosixPath` to its imports), beside the module's constants:

```python
_CHANGES = ("openspec", "changes")  # the root only (answer 11): `archived` and Task 5's `change_of` both read it
_ARCHIVE = (*_CHANGES, "archive")


def archived(path: str) -> bool:
    """Return whether path lies in `openspec/changes/archive/`, where `openspec archive` moves a change it has applied."""
    return PurePosixPath(path).parts[: len(_ARCHIVE)] == _ARCHIVE
```

and in `adapters/__init__.py` (add `archived` to its `earnest.index` import) `skipped` returns:

```python
    return archived(path) or any(parts[: len(base)] == base and _is_bookkeeping(parts[len(base) :]) for base in bases)
```

The skip begins at the repository root, as `change_of` (Task 5) and `layer` (Task 6) do (answer 11), so one rule says where `openspec/` is. A nested `openspec/` is plain files, as this repository's own fixtures are to its repository-level check, which already exits 1 with `duplicate` findings among them (18 on 2026-11-26).

- [ ] **Step 4:** Run Step 2's command again: expect `0`.
- [ ] **Step 5:** Run `rtk proxy uv run mypy --strict src/; echo $?`, ruff, vulture and the regression run. Expected `0`, at the recorded count plus 7 and 1.
- [ ] **Step 6:** Commit `fix: skip openspec/changes/archive, the copy a change leaves behind when it is archived`.

**Done when:** the archive scenario is green, and a repository with an archived change raises no `duplicate` from it.

### Task 5: A change as an intent (#22)

**Files:** Create `packages/earnest/src/earnest/openspec.py` and `packages/earnest/tests/unit/test_openspec.py`. Modify `packages/earnest/src/earnest/index.py`, `adapters/__init__.py`, `impact.py`, `plan.py`, `cli.py`, `reporter.py`, `tests/unit/test_impact.py`, `tests/unit/test_reporter.py`, `tests/unit/test_plan.py`, `tests/integration/test_openspec_ids.py` and `tests/steps/test_openspec_host.py`. Create the fixture overlays `change/`, `approved/` and `unbumped/` (their names are in `_OVERLAYS` since Task 3).

Built on spike D, measured on 2026-11-25 (+265/-18 over 7 files, a 112-line `openspec.py`, 25 tests). The prototype put the loader and the boxes in `plan.py` and imported `openspec` from `adapters`. This task keeps OpenSpec out of `plan.py` behind a `Host` seam (Step 4), because `openspec.py` imports `plan`, `plan` imports `adapters`, and `adapters` importing `openspec` would be a circular import: `change_of` therefore goes in `index.py`, beside Task 4's `archived`, which `adapters` and `openspec` both import, and `change_dirs`, derived from it, in `adapters/__init__.py`, beside `skipped`. `matches` and `_glob` stay in `openspec.py`, behind the `Host` it builds, so `plan.py` holds no glob. Task 7 adds the boxes and the two rules in `reporter.py`; the prototype's `EARNEST_OPENSPEC_ROUTE` and `EARNEST_OPENSPEC_APPROVAL` variables of `cli.py` are spike devices and are not carried over. The module is inlined in Step 4. Three changes from the prototype, each an answer: `change_of` matches below the root only (answer 11); the default approval is the hybrid (answer 6, no environment variable); a stage with no artifact before a later artifact is skipped (answer 7). The prototype's `RuntimeError` for a missing CLI becomes `PlanError`, which `cli.py` already turns into exit 2.

- [ ] **Step 1:** Run `rtk proxy uv run pytest -q; echo $?` with no `openspec` on `PATH` and record the count: the suite must need no Node here, and it still must not after this task.
- [ ] **Step 2:** Write the failing tests in `tests/unit/test_openspec.py`, with a fake `openspec` from `fake_executable` in `tmp_path` that prints a canned `status --json` for `spec-driven` and appends each call, with its `OPENSPEC_TELEMETRY`, to a log:
  - `test_a_change_is_a_directory_below_the_root_changes_outside_archive_and_hidden_ones`, calls `index.change_of` and `adapters.change_dirs`, rows: `openspec/changes/a/proposal.md` gives `openspec/changes/a` (and `change_dirs` `{"openspec/changes/a"}`); `openspec/changes/archive/x/proposal.md`, `openspec/changes/.hidden/p.md`, `openspec/changes/a` and `openspec/changes/README.md` (no file inside a change), `pkg/openspec/changes/a/p.md` (answer 11) and `openspec/specs/x/spec.md` give none;
  - `test_an_artifact_glob_matches_nested_specs_only_inside_its_change` (calls `openspec.matches`);
  - `test_stage_of_asks_the_host_the_intent_carries` (an `Intent` whose `host` is a stub `Host` with its own `holds`: `plan.stage_of` returns the stage that `holds` accepts, and a plain AI-DLC intent still reads the directory prefix);
  - `test_a_change_directory_bookkeeping_is_never_scanned` (`<change>/audit/` and `.earnest/`);
  - `test_plan_prints_the_change_as_an_intent_with_its_route`: the intent line, the four stages in the route's order, each with status and approval, and `frontier:`;
  - `test_an_existing_artifact_is_approved_by_openspec_and_a_shard_row_overrides_it` (answer 6);
  - `test_a_stage_with_no_artifact_before_a_later_artifact_is_not_the_frontier` (answer 7);
  - `test_a_body_edit_raises_unbumped_change_only_after_a_gate_row_names_the_item` (answer 6: with the artifact's approval alone, a body edited at the same revision raises none; with a `GATE_APPROVED` row whose `Items` names the item, it raises one);
  - `test_a_missing_openspec_cli_stops_the_run_with_exit_two` (empty `PATH`; one line on stderr naming `openspec`; empty stdout);
  - `test_an_unreadable_route_answer_stops_the_run_with_exit_two` (rows: a fake CLI that prints text that is not JSON; JSON with no `artifacts`; JSON with an empty `artifacts` list, which is no route);
  - `test_a_failing_openspec_cli_stops_the_run_with_exit_two` (a fake CLI that exits 1 and writes its cause on stderr: exit 2, and the one line on stderr holds the cause);
  - `test_an_openspec_cli_that_does_not_answer_in_time_stops_the_run_with_exit_two` (a fake CLI that sleeps, with `openspec._TIMEOUT` patched to a fraction of a second);
  - `test_an_openspec_that_cannot_start_stops_the_run_with_exit_two` (an executable `openspec` on `PATH`, written by hand because its shebang is the point and names no interpreter, so the start raises `OSError`: exit 2, no traceback);
  - `test_the_call_environment_turns_telemetry_off` (the fake logs `OPENSPEC_TELEMETRY` with each call, and the log holds `0`);
  - `test_the_call_environment_drops_the_variables_of_the_test_run` (the fake logs `PYTEST_CURRENT_TEST`, which `impact._environment()` removes, and the log holds none);
  - `test_a_process_takes_its_own_timeout`, in `tests/unit/test_impact.py`: `impact._process` of a `sleep` with `timeout=0.5` gives None, and with no `timeout` it still reads the patched `MAP_TIMEOUT`;
  - `test_check_stage_writes_the_run_header_and_the_body_baseline_for_a_change`;
  - `test_no_openspec_call_is_made_for_a_repository_with_no_change` (the log stays empty on the AI-DLC fixtures);
  - `test_a_repository_with_openspec_and_no_requirement_raises_no_requirements` (answer 5), rows: a root `openspec/` with `config.yaml` and a main spec holding no `req` gives one `earnest/no-requirements` finding at `openspec/config.yaml` line 1, and `check` exits 0; the same without `config.yaml` gives it at the first main spec's line 1; a root `openspec/` with a `req` gives none; a nested `pkg/openspec/` gives none; a root `openspec/` with neither `config.yaml` nor a main spec gives none;
  - `test_no_requirements_is_a_warning_and_in_rules` (`reporter`, in `tests/unit/test_reporter.py`): `earnest/no-requirements` is in `RULES` with level `warning`. `test_each_rule_has_its_sarif_level` (`tests/unit/test_reporter.py:23`) pins the exact rule set, so extend its table with `earnest/no-requirements` here, and with `earnest/checked-unevidenced` and `earnest/untracked-box` (both `warning`) in Task 7;
  - `test_find_intent_messages_name_an_openspec_change_beside_aidlc_state` (in `tests/unit/test_plan.py`; the existing tests there match only the `aidlc-state\.md` part, so they pass with or without the new wording), rows: `plan.find_intent([], None)` and `plan.find_intent([two intents], None)` each raise a `PlanError` whose text matches `openspec/changes/` and still names `aidlc-state.md`.

- [ ] **Step 3:** Run `rtk proxy uv run pytest tests/unit/test_openspec.py tests/unit/test_reporter.py tests/unit/test_plan.py::test_find_intent_messages_name_an_openspec_change_beside_aidlc_state tests/unit/test_impact.py::test_a_process_takes_its_own_timeout -q; echo $?`. Expected: the `test_openspec.py` tests fail on the missing module, the impact test on the missing argument, the reporter test on the missing rule and the `find_intent` test on the old message wording, non-zero.
- [ ] **Step 4:** Write `src/earnest/openspec.py`, add `change_of` to `index.py` and `change_dirs` to `adapters/__init__.py` (the block after it). The module is the prototype's module with the three changes above, a timeout, a failed start and an unreadable answer turned into `PlanError` (`route_cli` raises it itself, with the prefix `earnest needs the openspec CLI to read the route of <change>:`), `status` read into `Artifact.status`, and the call routed through `impact._process` under `impact._environment()` plus `OPENSPEC_TELEMETRY=0`, so it has the process-group kill and the environment filter of Earnest's other runs, not a second `subprocess.run`. The prerequisite edit is in `impact.py`: `_process` gains `timeout: float | None = None` and calls `child.communicate(timeout=MAP_TIMEOUT if timeout is None else timeout)`, and its docstring reads "for at most `timeout` seconds, `MAP_TIMEOUT` by default". The default is read when the function runs, not bound where it is defined, because `test_impact.py` patches `impact.MAP_TIMEOUT` (lines 110 and 132) and a bound default would ignore the patch. Step 3's tests check it; Task 7 adds `box` to it:

```python
"""The OpenSpec host: a change below `openspec/changes/<id>/` as an intent, and its route from the CLI."""

import json
import re
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath

from earnest import impact
from earnest.plan import Intent, PlanError

_TIMEOUT = 60  # seconds


@dataclass(frozen=True)
class Artifact:
    """One artifact of a schema: its id, the glob its output matches (relative to the change), and what it needs."""

    id: str
    generates: str
    requires: tuple[str, ...] = ()
    status: str = "ready"


def route_cli(directory: str, root: str) -> tuple[tuple[Artifact, ...], str]:
    """Return the artifacts and the schema name of `openspec status --change <id> --json`, run at `root`.

    The run goes through `impact._process`, with the process-group kill and the environment filter of Earnest's other runs.

    Raises:
        PlanError: `openspec` is not on PATH, cannot start, fails, does not answer in time, or answers no route (#26: fail loud).
    """
    name = PurePosixPath(directory).name
    need = f"earnest needs the openspec CLI to read the route of {name}:"
    exe = shutil.which("openspec")
    if exe is None:
        msg = f"{need} openspec is not on PATH"
        raise PlanError(msg)
    env = {**impact._environment(), "OPENSPEC_TELEMETRY": "0"}
    try:
        done = impact._process([exe, "status", "--change", name, "--json"], Path(root), env, timeout=_TIMEOUT)
    except OSError as error:  # a start that failed
        msg = f"{need} openspec status could not run: {error}"
        raise PlanError(msg) from error
    if done is None:  # a timeout
        msg = f"{need} openspec status did not answer in {_TIMEOUT} s"
        raise PlanError(msg)
    if done.returncode != 0:
        msg = f"{need} openspec status failed: {done.stderr.decode(errors='replace').strip()[:200]}"
        raise PlanError(msg)
    try:
        data = json.loads(done.stdout)
        artifacts = tuple(
            Artifact(each["id"], each["outputPath"], tuple(each["requires"]), each["status"])
            for each in data["artifacts"]
        )
        schema = data["schemaName"]
    except (ValueError, KeyError, TypeError) as error:
        msg = f"{need} openspec status gave no usable route: {error}"
        raise PlanError(msg) from error
    if not artifacts:  # a route with no stage would read as nothing left to do
        msg = f"{need} openspec status gave no usable route: no artifacts"
        raise PlanError(msg)
    return artifacts, schema
```

In `index.py`, beside Task 4's `archived`, `change_of` is the one rule that says which change a file belongs to:

```python
def change_of(path: str) -> str | None:
    """Return `openspec/changes/<id>` when path is a file of a change, else None.

    A change is a directory directly below the root `openspec/changes/` (answer 11), other than `archive/` and a hidden
    one, as upstream's `getActiveChangeIds` has it.
    """
    parts = PurePosixPath(path).parts
    change = parts[: len(_CHANGES) + 1]  # `openspec/changes/<id>`, when the path goes that deep
    if len(parts) == len(change) or change[:-1] != _CHANGES or change[-1].startswith(".") or archived(path):
        return None  # a path no deeper than the change is no file of it
    return "/".join(change)
```

`adapters/__init__.py` (add `change_of` to its `earnest.index` import; `Iterable` is imported there already) derives `change_dirs` beside `skipped`. `index.py` imports neither `adapters`, `plan` nor `openspec`, so there is no cycle:

```python
def change_dirs(paths: Iterable[str]) -> frozenset[str]:
    """Return `openspec/changes/<id>` for each change among the paths."""
    return frozenset(found for path in paths if (found := change_of(path)) is not None)
```

`openspec.py` also holds `matches` and `_glob` (the prototype's, kept there; `plan.py` holds no glob). `_glob` is cached, because `matches` asks it for the same few patterns once per path:

```python
@lru_cache
def _glob(pattern: str) -> re.Pattern[str]:
    out, at = "", 0
    while at < len(pattern):
        if pattern.startswith("**/", at):
            out, at = out + "(?:.*/)?", at + 3
        elif pattern.startswith("**", at):
            out, at = out + ".*", at + 2
        elif pattern[at] == "*":
            out, at = out + "[^/]*", at + 1
        else:
            out, at = out + re.escape(pattern[at]), at + 1
    return re.compile(out)


def matches(directory: str, generates: str, path: str) -> bool:
    """Return whether path is an output of the artifact that `generates` names, inside the change directory."""
    prefix = directory + "/"
    return path.startswith(prefix) and _glob(generates).fullmatch(path[len(prefix) :]) is not None
```

The rest of the step is `plan.py`, `adapters/__init__.py` and `cli.py`, where the prototype's `stage_files` branch becomes a `Host` seam (`Callable` from `collections.abc`):

```python
@dataclass(frozen=True)
class Host:
    """How a host reads an intent: which files a stage holds, the route check it keeps, and what each stage produces."""

    holds: Callable[[Intent, str, str], bool]  # intent, stage, path
    route_findings: Callable[[Intent], list[Finding]]
    produces: Mapping[str, frozenset[str]]  # stage slug -> the item types its artifacts hold


AIDLC: Host = Host(
    lambda intent, stage, path: path.startswith(posixpath.join(intent.directory, stage) + "/"), route_findings, PRODUCES
)
```

`Intent` gains `host: "Host" = field(default_factory=lambda: AIDLC)` (`field` is already imported in `plan.py`). `plan.py` has no `from __future__ import annotations` and a class body evaluates its annotations when it runs, so the order matters: define `Host` after `Plan` (its `Callable[[Intent, ...]]` then resolves, and so does Task 7's hook, which names `Plan`), quote the annotation inside `Intent` (`Host` does not exist yet), and define `AIDLC` after `route_findings` and `PRODUCES` (the default factory defers the name `AIDLC`, and `AIDLC`'s own arguments need both), annotated as `AIDLC: Host`, because `mypy --strict` cannot infer the type of a name that the factory reads above its assignment. No function tests which host it has; each of these four sites asks the intent's own:

```python
# build(), the item grouping (the line that tests `item.path.startswith(posixpath.join(intent.directory, stage) + "/")`)
            if intent.host.holds(intent, stage, item.path)

# stage_of()
    return next((stage for stage in intent.route if intent.host.holds(intent, stage, path)), None)

# plan_findings()
    route = plan.intent.host.route_findings(plan.intent)
    return [*_unplanned(plan, index), *_cycle_findings(plan, index), *route, *plan.join]

# produces(), and the `wanted` line of the gap placer, which read `PRODUCES` today
        *(current.host.produces.get(_slug(stage), frozenset()) for current in intents for stage in current.executed)
    wanted = (
        stage for stage in owner.intent.executed if finding.child in owner.intent.host.produces.get(_slug(stage), ())
    )
```

The shared `PRODUCES` dict stays AI-DLC's, and `test_a_host_with_its_own_produces_leaves_the_aidlc_table_alone` (in `tests/unit/test_plan.py`) pins that `PRODUCES` holds no `specs` key while an OpenSpec intent's `specs` stage produces `feat` and `req`.

`openspec.py` holds the OpenSpec `Host` and the loader (add `import posixpath`, `from collections.abc import Mapping, Sequence`, `from earnest.index import change_of`, and `AUDIT`, `Approval`, `Host`, `_approval`, `_events`, `_named` and `counting` to the header's `earnest.plan` import, which holds `Intent` and `PlanError`). The loader buckets the listed paths once by change directory, so each change reads its own bucket for its `audit/` rows and for its artifact globs, not the whole list per change and per artifact. Each existing artifact gets the approval `current, openspec` with no items named (so `_named` is empty and nothing is frozen: `unbumped-change` needs a `GATE_APPROVED` row with `Items`, which the `approved` overlay holds), and the rows of the change's `audit/*.md`, read with AI-DLC's own `_events`, `counting`, `_approval` and `_named`, override it. A stage with no artifact before a later stage's artifact is left off the route, as AI-DLC leaves off a skipped stage, so the frontier passes it (answer 7). `route_cli`'s `PlanError` goes through (`openspec.py` already imports `plan`, so the import adds no cycle), and the route check returns `[]`, because a route read from the CLI cannot mismatch a state file:

```python
_PRODUCES = {  # the item types a stage's artifacts hold: `proposal` holds none, and no stage holds an `stest`
    "specs": frozenset({"feat", "req"}),
    "design": frozenset({"dsn"}),
    "tasks": frozenset({"task", "impl", "utest", "itest"}),
}


def _host(globs: Mapping[str, str]) -> Host:
    return Host(lambda intent, stage, path: matches(intent.directory, globs[stage], path), lambda _: [], _PRODUCES)


def load_openspec(root: Path, files: Sequence[str]) -> list[Intent]:
    """Read each change below the root `openspec/changes/` among the listed files as an intent, its route from the CLI."""
    owned: dict[str, list[str]] = {}
    for path in files:
        if (directory := change_of(path)) is not None:
            owned.setdefault(directory, []).append(path)
    found: list[Intent] = []
    for directory, own in sorted(owned.items()):
        artifacts, _ = route_cli(directory, str(root))
        present = [each for each in artifacts if any(matches(directory, each.generates, path) for path in own)]
        # a stage with no artifact stays on the route only past the last artifact, where the frontier can reach it
        after = artifacts[artifacts.index(present[-1]) + 1 :] if present else artifacts
        route = tuple(each.id for each in (*present, *after))
        audit = posixpath.join(directory, AUDIT)
        shards = [path for path in own if posixpath.dirname(path) == audit and path.endswith(".md")]
        events = counting(sorted(event for shard in shards for event in _events(root, shard)), ())
        gates = [event for event in events if event.name in {"GATE_APPROVED", "GATE_REJECTED"}]
        approvals = {each.id: Approval(each.id, None, "openspec", None) for each in present}
        approvals |= {stage: row for stage in route if (row := _approval(stage, gates)) is not None}
        host = _host({each.id: each.generates for each in artifacts})
        found.append(
            Intent(
                directory, "", (), route, approvals, _named(gates), (), executed=route, events=tuple(events), host=host
            )
        )
    return found
```

`adapters/__init__.py`: `scan` adds each change directory to the record directories, so `<change>/audit/` and `.earnest/` stay bookkeeping: `directories = record_directories(listed) | change_dirs(listed)`. `cli._read` loads the changes beside the state files, `intents += openspec.load_openspec(root, files)` after the `plan.intent(record)` line; the messages of `find_intent` that name `aidlc-state.md` also name `openspec/changes/<id>/`. `cli.py` adds `earnest/no-requirements` (a warning, `RULES` in `reporter.py`) at `openspec/config.yaml` line 1, or at the first main spec's line 1, when `openspec/` exists at the root and the index holds no `req` (answer 5; no file to point at, no finding), and the message says to write an id line under each heading.

- [ ] **Step 5:** Run Step 3's command: expect `0`. Then add the overlays and bind scenarios 8 and 9. `change/` holds the change of the Fixture section; `approved/` holds the gate row of the Fixture section, which scenario 9 commits after its stage check (the "approved" layer step is the one that commits any layer); `unbumped/` holds the delta with the first requirement's body edited ("...for the lockout window, which starts at the third failure.") and its revision left at 2. Run `rtk proxy uv run pytest tests/steps/test_openspec_host.py -k "intent or unbumped" -q; echo $?`: expect `0`. Add `test_the_change_approved_and_unbumped_layers_pass_strict_validation` to `tests/integration/test_openspec_ids.py` and run it by path: expect `0`. No spike ran `openspec validate` over an `audit/` directory inside a change (S15), so if OpenSpec rejects it, stop and tell the maintainer; do not move the row without that answer.
- [ ] **Step 6:** The repository-level check: `rtk proxy uv run --project packages/earnest earnest check 2>&1 >/dev/null | grep -c '^intent '` equals Step 6 of Task 3's count (the fixture's `openspec/` is not at the root). Then the regression run, `mypy --strict`, ruff and vulture: expect `0`, at the Step 1 count plus this task's tests.
- [ ] **Step 7:** Commit `feat: an OpenSpec change is an intent, with its route from the CLI and its stages from the files`.

**Done when** (#22): on the fixture `earnest plan` prints the change as an intent with its stages and computed status, `check --stage specs --intent openspec/changes/lockout-window` writes the run header and the record, and `unbumped-change` fires on a body edited without a bump once a gate row has named its stage's items.

### Task 6: Delta overlay and stacked changes (#23, second half)

**Files:** Modify `packages/earnest/src/earnest/adapters/__init__.py`, `index.py`, `structural.py`. Test `packages/earnest/tests/unit/test_openspec_layers.py`. Modify `packages/earnest/tests/steps/test_openspec_host.py`.

Built on spike C's design C, measured on 2026-11-25 (+113/-20 over 3 files and 14 tests; 1068 tests passed, no existing test changed), and on answer 8's extension. Step 3 inlines the layer code, including the `item.layer == DELTA` clause of `Index.defined`. Its `_duplicates` is not spike C's: that one compared a copy with the overlay winner, and the stacked-change extension skipped any delta behind the winner, which hides a duplicate when a third change stacks above two at one revision. Write `_duplicates` from the text in Step 3. The spike also handled REMOVED (`Removal`, `Item.heading`, `Item.section`, `Index.removals` and `removed`, `_retitle`, `_capability`, `_REQ_HEADING`, `_SECTION`, the longer returns of `_Parsed` and `_spans`, the removed-tag branch of `_links`, and the two REMOVED skips): that is Task 10's, which has its code. No exit bullet of `03` needs it, and `03` defers it.

This task runs after Task 5 and before Task 7, which also edits `index.py`. The stacked-change count on the real repository is R8's (7 down to 0), cited and not re-run: the clone stays outside this repository.

- [ ] **Step 1:** Write the failing tests in `test_openspec_layers.py` (add `from earnest import structural` and `from earnest.index import build_index` to Task 4's imports), each building a small `Index` from `Source`s with a layer (`main` or `delta`). The helpers, which Task 10's tests use too:

  ```python
  MAIN_PATH = "openspec/specs/greeting/spec.md"
  DELTA_PATH = "openspec/changes/refine/specs/greeting/spec.md"
  OTHER_PATH = "openspec/changes/other/specs/greeting/spec.md"
  ARCHIVE_PATH = "openspec/changes/archive/2026-10-01-add/specs/greeting/spec.md"
  CODE = "src/greeting.py"


  def spec(heading, revision, section=None):
      top = f"## {section} Requirements\n\n" if section else "## Requirements\n\n"
      return f"{top}### Requirement: {heading}\n`req~{heading.lower().replace(' ', '-')}~{revision}`\n\nThe system shall x.\n"


  def run(files, tag=None):
      sources = [adapters.source(path, text.encode()) for path, text in files.items()]
      if tag:
          sources.append(adapters.source(CODE, f"# [impl->req~{tag}]\n".encode()))
      index = build_index(source for source in sources if source and not adapters.skipped(source.path, ()))
      found = [(f.rule, f.path) for f in structural.check(index)]
      # a spec with no `Covers:` line also raises orphaned and gap: only the code's links and these two rules are under test
      return index, [
          (rule, path) for rule, path in found if rule in ("earnest/duplicate", "earnest/outdated") or path == CODE
      ]


  def test_a_modified_delta_overlays_the_main_copy_and_outdates_links_to_the_old_revision():
      index, found = run({MAIN_PATH: spec("Greet", 1), DELTA_PATH: spec("Greet", 2, "MODIFIED")}, tag="greet~1")
      assert str(index.defined[("req", "greet")].id) == "req~greet~2"
      assert not [rule for rule, _ in found if rule == "earnest/duplicate"]
      assert ("earnest/outdated", CODE) in found


  def test_a_delta_at_the_main_revision_is_no_duplicate_and_main_stands():
      index, found = run({MAIN_PATH: spec("Greet", 1), DELTA_PATH: spec("Greet", 1, "MODIFIED")})
      assert index.defined[("req", "greet")].path == MAIN_PATH
      assert found == []


  def test_a_delta_behind_the_main_copy_is_outdated():
      _, found = run({MAIN_PATH: spec("Greet", 3), DELTA_PATH: spec("Greet", 2, "MODIFIED")})
      assert ("earnest/outdated", DELTA_PATH) in found
  ```

  The rest follow the shape of these three:

  - `test_the_result_does_not_depend_on_the_order_of_the_sources` (a main copy at revision 1, a delta at revision 2 and a skipped archive copy, built forward and reversed: assert that `index.defined` and the sorted `(rule, path, message)` of the `structural.check` findings are equal; there is no tie in this set, so the claim holds for raw `build_index` order);
  - `test_a_tie_between_two_changes_follows_the_sorted_path_order` (changes A and B hold `req~x~2`, no main copy; the test writes the files under `tmp_path` and goes through `adapters.scan` with the paths sorted, as `git.work_tree_files` lists them, in two creation orders: assert that `index.defined` holds A's copy and that the one `duplicate` is B's, against A's. A tie is the one case where the result follows the order of the sources: `Index.defined` keeps the earlier copy and `_duplicates` reports the later, so the order comes from the sorted paths, not from `build_index`);
  - `test_two_changes_that_define_one_id_at_one_revision_are_duplicates`;
  - `test_a_change_stacked_on_another_overlays_it_at_a_higher_revision_and_is_no_duplicate` (answer 8, option B: an ADDED copy at revision 1 in one change and a MODIFIED copy at revision 2 in another give no finding, and the id resolves to revision 2);
  - `test_two_main_copies_stay_duplicate_while_a_delta_overlays_them` (two main specs define `req~x~1` and a change holds `req~x~2`: the second main copy is still `duplicate`, against the first main copy);
  - `test_a_delta_behind_main_stays_outdated_when_another_change_stacks_above_it` (main at revision 2, change A holds revision 1, change B holds revision 3: A's copy is `outdated`, against the main copy);
  - `test_two_changes_at_one_revision_stay_duplicate_when_a_third_stacks_above_them` (no main copy; changes A and B hold `req~x~1` and change C holds `req~x~2`: B's copy is `duplicate`, against A's, and A's and C's copies give no finding);
  - `test_the_layer_is_delta_only_for_a_file_inside_a_change` (rows: `openspec/changes/a/specs/x/spec.md` is `delta`; `openspec/specs/x/spec.md`, `openspec/changes/.hidden/specs/x/spec.md`, `openspec/changes/README.md` and `pkg/openspec/changes/a/specs/x/spec.md` are `main`).

- [ ] **Step 2:** Run `rtk proxy uv run pytest tests/unit/test_openspec_layers.py -q; echo $?`. Expected: fail, non-zero.
- [ ] **Step 3:** Implement:
  - `adapters/__init__.py` (import `DELTA`, `MAIN` and `change_of` from `earnest.index` beside `Source`): `layer(path)` returns `DELTA` when `change_of(path)` names a change (Task 5; the root only, answer 11, so neither `archive/` nor a hidden directory is one) and `MAIN` otherwise, and `source` passes `layer=layer(path)` to the `Source` it builds, which is how `scan` sets it:

  ```python
  def layer(path: str) -> str:
      """Return `delta` for a file of an in-flight OpenSpec change, else `main`: the layers an id's copies overlay in."""
      return MAIN if change_of(path) is None else DELTA
  ```

  - `index.py`: constants `MAIN = "main"` and `DELTA = "delta"  # a copy in an in-flight OpenSpec change, which overlays the main copy of its id`; `Source.layer: str = MAIN`; `Item.layer: str = field(default=MAIN, compare=False)`, set from `source.layer` in `_markdown` (`items.append(Item(item_id, source.path, number, needs, _body_hash(lines, source.fenced), body, overrides, source.layer))`). `Index.defined` becomes:

  ```python
          found: dict[tuple[str, str], Item] = {}
          for item in self.items:
              held = found.setdefault(item.id.key, item)
              if (item.layer != held.layer or item.layer == DELTA) and _overlay(item) > _overlay(held):
                  found[item.id.key] = item
          return found
  ```

  with `_overlay(item)` returning `(item.id.revision, item.layer != DELTA)`, so main wins a tie against a delta, and an earlier-sorted delta wins a tie against a later one. The `item.layer == DELTA` clause is the extension: without it a stacked change's copy is compared with nothing.
  - `structural.py` (import `MAIN` from `earnest.index`): `_duplicates` gains the layer branch, and compares each copy with the copy of its own layer, never with the overlay winner alone. A main copy other than the first main copy yields `duplicate`, whatever delta overlays them. A delta copy that sits behind the main copy yields `earnest/outdated` against the main copy, whichever delta wins. A delta copy above main, or with no main copy, yields `duplicate` against the first delta copy at its own revision, whatever delta overlays them (a lone copy at a lower revision is the base of a stacked change). A delta copy at the main revision gives no finding (main stands). The function reads:

  ```python
  def _duplicates(index: Index) -> Iterator[Finding]:
      mains: dict[tuple[str, str], Item] = {}
      deltas: dict[tuple[tuple[str, str], int], Item] = {}
      for item in index.items:
          if item.layer == MAIN:
              mains.setdefault(item.id.key, item)  # the copy that every other main copy is compared with
          else:
              deltas.setdefault((item.id.key, item.id.revision), item)  # likewise for the delta copies of one revision
      for item in index.items:
          if item.layer == MAIN:
              main = mains[item.id.key]
              if item != main:
                  message = f"`{item.id}` is already defined at {main.path}:{main.line}: give one of them another name"
                  yield Finding(item.path, item.line, "earnest/duplicate", str(item.id), message)
          elif (base := mains.get(item.id.key)) is not None and item.id.revision < base.id.revision:
              message = f"`{item.id}` is behind `{base.id}` in {base.path}:{base.line}: rebase the change onto it"
              yield Finding(item.path, item.line, "earnest/outdated", str(item.id), message)
          elif base is None or item.id.revision > base.id.revision:  # a delta at the main revision lets main stand
              first = deltas[(item.id.key, item.id.revision)]
              if item != first:
                  message = f"`{item.id}` is already defined at {first.path}:{first.line}: give one of them another name"
                  yield Finding(item.path, item.line, "earnest/duplicate", str(item.id), message)
  ```

- [ ] **Step 4:** Run Step 2's command: expect `0`. Then bind scenario 7 and run `rtk proxy uv run pytest tests/steps/test_openspec_host.py -k "supersedes" -q; echo $?`: expect `0`, with `outdated` at `src/lockout.py:6` and `tests/test_lockout.py:6` and no `duplicate`.
- [ ] **Step 5:** `mypy --strict`, ruff, vulture and the regression run: expect `0`, at the recorded count plus 11 and 1. The order-independence test checks a set with no tie; the sorted-path test checks the tie.
- [ ] **Step 6:** Commit `feat: a requirement in a change in flight overlays its main copy, and a stacked change its base`.

**Done when** (#23): on the fixture, with a main spec, an in-flight MODIFIED delta and an archived change, there is no `duplicate`, the items linked to the superseded revision are flagged (SC5), and two runs give identical SARIF.

### Task 7: Done-status from `tasks.md` (#24)

**Files:** Modify `packages/earnest/src/earnest/openspec.py`, `plan.py` (`Box`, `Boxes`, `Plan.boxes`, and the `boxes` and `current_task` fields of `Host`; `current_task` is unchanged, so its `tests/unit/test_plan.py` callers need none), `cli.py` (`_analyse` reads the boxes, and its `current_task` call site gains the host's fallback), `index.py`, `reporter.py`. Test `packages/earnest/tests/unit/test_openspec.py`, `tests/unit/test_reporter.py` and `tests/integration/test_openspec_ids.py`. Modify `packages/earnest/tests/steps/test_openspec_host.py`.

Built on spike D, measured on 2026-11-25 (findings 5 to 11; 10 of its 25 tests are this task's). Step 3 inlines the code. `boxes`, `checked_findings`, `untracked_findings` and `in_flight` (the prototype's `_in_flight`) go into `openspec.py`; `Box` and `Boxes`, which `Plan.boxes` holds for `statuses` and `properties` to read, stay in `plan.py` with the two fields that `Host` gains (the OpenSpec host fills them, and AI-DLC keeps their defaults, so no function tests which host it has), and so do the first-stage change and the plan line of `reporter.py`. The prototype's `boxes`, `loose` and `marks` parameters of `statuses`, `properties` and `current_task` are not taken, and `current_task` stays as it is. The box regex is defined once, as `_BOX` in `index.py`, and `openspec.py` imports it, with `_spans`, which gives each item's lines as the index reads them, so a task's span is the index's own (`openspec` imports `plan`, which imports `index`, so there is no cycle). This task runs after Task 6, which also edits `index.py`.

- [ ] **Step 1:** Write the failing tests:
  - `test_a_box_reads_as_upstream_counts_it`, rows: `- [x] a`, `- [X] a`, `* [x] a`, `1. [x] a` are checked; `- [ ] a`, `- [  ] a`, `- [ ](link)` and `- [-] a` are unchecked; `- [x](link)` and `- [x][ref]` are no box;
  - `test_ticking_a_box_leaves_the_task_body_hash_as_it_was`, `test_ticking_a_nested_sub_box_changes_the_body_hash` (a task line `- [ ] a` with an indented sub-box `- [ ] b` under it, against the same with `- [x] b`: the hashes differ), `test_changing_a_task_title_changes_the_body_hash`, and `test_a_bracket_in_the_middle_of_a_task_line_still_changes_the_body_hash` (rows: `Delivers: see 2. [a] and - [b] here` against `[c]`, and `Use a[1] - [k] lookup` against `[m]`);
  - `test_plan_prints_each_tasks_box_beside_its_computed_status` (`task task~lock-for-window~1: not done, box [x]`);
  - `test_a_checked_task_whose_requirement_is_below_evidenced_raises_the_finding_at_its_box` (a stage check of `tasks`);
  - `test_a_plain_check_raises_no_checked_unevidenced` (P8: the same tree, no `--stage`);
  - `test_an_unchecked_task_raises_no_checked_unevidenced`;
  - `test_a_checked_task_whose_design_has_no_impl_raises_the_finding_without_naming_a_requirement` (`task_done` is false for a delivered `dsn` with no `impl`, so the box is flagged and the message says what it delivers is not done); `test_a_checked_task_that_is_done_raises_none`;
  - `test_a_box_with_no_task_id_line_is_untracked_and_keeps_the_tasks_stage_open`;
  - `test_a_nested_sub_box_under_a_task_is_claimed_and_is_not_untracked` (a task id line, its box and an indented sub-box under it, ticked or not: `boxes.loose` is empty and no `untracked-box` finding is raised, so the tasks stage can be done; a box under a heading, or above the first id line, is still untracked);
  - `test_the_current_task_is_the_first_unchecked_box_of_the_one_change_that_has_one` (answer 10: a change with every box ticked is not counted);
  - `test_there_is_no_current_task_when_two_changes_have_unchecked_boxes`;
  - `test_an_aidlc_intent_at_the_repository_root_is_no_second_holder_of_a_change_task` (`openspec.in_flight` over the plan of an AI-DLC intent with directory `""` and the plan of a change with one unchecked box: the box's task comes back, not "several changes"; this fails if a holder is any intent whose directory contains the task's path, which the root directory does for every file);
  - `test_an_aidlc_only_check_with_no_current_task_keeps_the_reason_of_current_task` (through `cli.main` on an AI-DLC fixture whose state file names no task: the stderr reason is `current_task`'s, not "no OpenSpec task is unchecked"; this fails if the AI-DLC host carried a `current_task` hook);
  - `test_check_takes_the_first_unchecked_box_as_the_current_task` (through `cli.main` on the fixture with the fake `openspec`, no `--task`: the stderr task-change line names that box's task, and the out-of-task check runs; this fails if `cli.py` never passes the boxes to `openspec.in_flight`);
  - `test_check_with_a_task_flag_on_two_changes_holding_unchecked_boxes_uses_it_and_states_no_current_task_line` (the two-change fixture with `--task task~<name>~1`: the stderr task-change line names the given task, the out-of-task check runs, and no `no current task` line appears; this fails if `cli.py` calls `in_flight` before the flag or prints that line despite it);
  - `test_check_with_a_task_flag_beats_the_one_in_flight_unchecked_box` (a single change with an unchecked box and `--task` naming a different task: the given task wins, not the box's);
  - `test_check_with_two_changes_holding_unchecked_boxes_states_no_current_task_once` (two change directories, each with an unchecked box, no `--task`: one `no current task` line on stderr naming both changes);
  - `test_the_box_count_agrees_with_openspec_list`, in `tests/integration/test_openspec_ids.py`, which `addopts` leaves out of a bare run (P5): it runs the real CLI over the fixture, 2 of 3. It is not a unit test;
  - `test_checked_unevidenced_and_untracked_box_are_warnings_and_in_rules` (`reporter`).

- [ ] **Step 2:** Run `rtk proxy uv run pytest tests/unit/test_openspec.py tests/unit/test_reporter.py -q; echo $?`, and the integration test by path. Expected: fail, non-zero.
- [ ] **Step 3:** Implement. In `index.py`, upstream's box pattern (S10), defined once, and a body hash of a `task` item that blanks the box's marker, so `[x]` and `[ ]` hash alike (answer 10, option A), and nothing else; `_markdown` passes `item_id.type == "task"`:

  ```python
  # The checkbox at the start of a task line, as upstream counts it (src/utils/task-progress.ts, v2.1.1): any list marker, a box
  # holding at most one non-space marker (`[ ]` with spaces too), and a `[x](...)` or `[x][...]` link bullet is no box.
  # Group 1 is the line up to the `[`; group 2 is the marker, and only `x` or `X` is done.
  _BOX = re.compile(r"(\s*(?:[-*+]|\d{1,9}[.)])\s*\[)(?:\s*([^\]\s]?)\s*\](?![(\[])|\s+\])")


  def _body_hash(lines: Iterable[Line], fenced: frozenset[int], boxes: bool = False) -> str:
      stripped = [(line.number, line.text.removesuffix("\r").rstrip(" \t")) for line in lines]
      if boxes:  # ticking a task's box is progress, not a change of its body; only the leading box, so a nested sub-box still counts
          for at, (number, text) in enumerate(stripped):
              if found := _BOX.match(text):
                  stripped[at] = (number, f"{found.group(1)} ]{text[found.end():]}")
                  break
      kept = [text for number, text in stripped if text and (number in fenced or _KEY.match(text) is None)]
      return digest("\n".join(kept).encode("utf-8"))
  ```

  In `openspec.py` (add `from collections.abc import Iterable` and `from earnest.index import _BOX, Line`; the `openspec.py` block below adds the rest), the first box among a task's lines:

  ```python
  def box(path: str, lines: Iterable[Line]) -> Box | None:
      """Return the first checkbox among the lines of a file, or None: `x` or `X` is checked."""
      for line in lines:
          if found := _BOX.match(line.text):
              return Box(path, line.number, (found.group(2) or "").lower() == "x")
      return None
  ```

  (Keep the function's `stripped` line as it is. Add to its docstring that for a task item (`boxes`) the marker inside the leading checkbox is blanked, so ticking a box leaves the hash as it was, and reword "so only what Git and an editor add at a line's end leaves the hash as it was" so it no longer excludes that case.)

  `plan.py` gains two value types, so it imports nothing from `openspec.py`, and `Plan` gains `boxes: Boxes = field(default_factory=Boxes)` (define both, and `_no_boxes`, before `Plan`):

  ```python
  @dataclass(frozen=True)
  class Box:
      """A task's checkbox in `tasks.md`: where it sits, and whether it is checked (`x` or `X`, as upstream counts)."""

      path: str
      line: int
      checked: bool


  @dataclass(frozen=True)
  class Boxes:
      """The checkboxes of one change: each task's by id, and those that no task id line claims."""

      marks: Mapping[str, Box] = field(default_factory=dict)
      loose: tuple[Box, ...] = ()


  def _no_boxes(_sources: Sequence[Source], _intent: Intent) -> Boxes:
      return Boxes()
  ```

  `Host` (Task 5) gains the two fields that read them, after `produces` and with defaults, so `AIDLC` keeps its three arguments, with no boxes and no hook. The hook takes the plans, not the intents, because a plan knows which boxes are its own, where a record directory of `""` contains every path:

  ```python
      boxes: Callable[[Sequence[Source], Intent], Boxes] = _no_boxes  # the intent's checkboxes
      # the fallback for a current task, asked when no state file names one
      current_task: Callable[[Sequence[Item], Sequence[Plan]], tuple[Item | None, str | None]] | None = None
  ```

  `plan.py` reads them in three places, and `reporter.py` in one:

  ```python
  # statuses(), after `open_tasks = sum(...)`: a box with no task id line keeps the `tasks` stage open
          if state.stage == "tasks":
              open_tasks += len(plan.boxes.loose)

  # properties(), in each task's entry, with `marks = current.boxes.marks` set above the comprehension
                  {"id": str(item.id), "status": "done" if task_done(item, index, levels) else "not done"}
                  | ({"box": "x" if marks[str(item.id)].checked else " "} if str(item.id) in marks else {})

  # the first-stage check, which reads the Code Generation stage of an AI-DLC route and the `tasks` stage of an OpenSpec one
      first = next((each for each in plan.intent.executed if _slug(each) in {_CODE_GENERATION, "tasks"}), None)

  # reporter.py, the plan line of each task
      lines.extend(
          f"  task {task['id']}: {task['status']}" + (f", box [{task['box']}]" if "box" in task else "")
          for task in entry["tasks"]
      )
  ```

  `openspec.py` (add `Id`, `Index`, `Item`, `Source` and `_spans` to the `earnest.index` import that the `box` block began with `_BOX` and `Line`; add `Box`, `Boxes`, `Plan`, `stage_of` and `task_done` to the `earnest.plan` import, and `from earnest.reporter import Finding`) reads the boxes of one change, the findings they raise, and the current task:

  ```python
  _UNTRACKED = (
      "this checkbox has no task id line above it, so earnest cannot compute whether the task is done: write a"
      " `task~<name>~1` line and `Delivers: req~<name>~<n>` directly above it"
  )


  def boxes(sources: Sequence[Source], intent: Intent) -> Boxes:
      """Return the checkboxes of the change's `tasks` artifact: each task's first, and those that no task's span holds."""
      marks: dict[str, Box] = {}
      loose: list[Box] = []
      for source in sources:
          if stage_of(intent, source.path) != "tasks":
              continue
          tasks = [(item_id, body) for item_id, _number, body, *_rest in _spans(source)[0] if item_id.type == "task"]
          held = source.fenced.union(line.number for _, body in tasks for line in body)  # a nested sub-box is its task's
          for item_id, body in tasks:
              if (found := box(source.path, body)) is not None:
                  marks.setdefault(str(item_id), found)
          loose += [
              found
              for line in source.lines
              if line.number not in held and (found := box(source.path, [line])) is not None
          ]
      return Boxes(marks, tuple(loose))


  def untracked_findings(intent: Intent, found: Boxes) -> list[Finding]:
      """Return an `untracked-box` finding at each checkbox that no task item claims."""
      return [
          Finding(
              each.path,
              each.line,
              "earnest/untracked-box",
              f"{each.path}:{each.line}",
              _UNTRACKED,
              stage="tasks",
              intent=intent.directory,
          )
          for each in found.loose
      ]


  def checked_findings(plans: Sequence[Plan], index: Index, levels: Mapping[str, str]) -> list[Finding]:
      """Return a `checked-unevidenced` finding at the box of each checked task that is not done (`plan.task_done`)."""
      short: dict[Id, list[str]] = {}  # each task's delivered requirements below evidenced, from one pass over the links
      for link in index.links:
          level = levels.get(str(link.target))
          if link.key == "Delivers" and link.owner is not None and link.target.type == "req" and level != "evidenced":
              short.setdefault(link.owner, []).append(f"`{link.target}` is {level or 'untraced'}")
      found: list[Finding] = []
      for current in plans:
          for state in current.stages:
              for item in state.items:
                  mark = current.boxes.marks.get(str(item.id))
                  if mark is None or not mark.checked or task_done(item, index, levels):
                      continue
                  why = (
                      f"{'; '.join(sorted(short[item.id]))}, not evidenced"
                      if item.id in short
                      else "what it delivers is not done"
                  )
                  message = (
                      f"`{item.id}` is checked in tasks.md, but {why}: uncheck the box,"
                      " or tag and test the requirement until earnest check --judge --evidence reports it evidenced"
                  )
                  found.append(
                      Finding(
                          mark.path,
                          mark.line,
                          "earnest/checked-unevidenced",
                          str(item.id),
                          message,
                          stage=state.stage,
                          intent=current.intent.directory,
                      )
                  )
      return found


  def in_flight(tasks: Sequence[Item], plans: Sequence[Plan]) -> tuple[Item | None, str | None]:
      """Return the first unchecked task, in file order, of the one change that has an unchecked task."""
      open_boxes = {
          each.intent.directory: {name for name, mark in each.boxes.marks.items() if not mark.checked} for each in plans
      }
      holders = sorted(directory for directory, names in open_boxes.items() if names)
      if len(holders) > 1:
          return None, f"several changes have an unchecked task ({', '.join(holders)}): name one with --task"
      pending = [task for task in tasks if any(str(task.id) in names for names in open_boxes.values())]
      if not pending:
          return None, "no state file names one, and no OpenSpec task is unchecked"
      return min(pending, key=lambda task: (task.path, task.line)), None
  ```

  `_host` (Task 5) now passes the two hooks:

  ```python
  def _host(globs: Mapping[str, str]) -> Host:
      return Host(
          lambda intent, stage, path: matches(intent.directory, globs[stage], path),
          lambda _: [],
          _PRODUCES,
          boxes,
          in_flight,
      )
  ```

  A box outside every task's span is untracked: `_spans` gives a task the lines from its id line to the next ATX heading or id line, `box` takes its first box as the task's mark, and a nested sub-box inside it belongs to the task too (`_spans(source)[0]` and the `*_rest` of its unpacking stay valid when Task 10 widens the tuples that `_spans` returns). `checked_findings` asks `plan.task_done`, the rule that `statuses` and `properties` use, so a box is flagged when the plan line beside it reads `not done`: a delivered requirement below evidenced (the case the message names), and also a delivered `dsn` with no `impl`, which answer 10's wording leaves out. `cli.py` calls them: straight after `plan.build`, `_analyse` replaces each plan with `dataclasses.replace(each, boxes=each.intent.host.boxes(world.sources, each.intent))`; it takes the `--stage` text (`_analyse(..., stage=args.stage)` at both call sites) and, with the other structural findings, adds

  ```python
      checked += [found for each in plans for found in openspec.untracked_findings(each.intent, each.boxes)]
      if stage == "tasks":  # P8: a plain `check` and `plan` raise no checked-unevidenced
          checked += openspec.checked_findings(plans, index, levels)
  ```

  and the current-task step becomes:

  ```python
      tasks = plan.plan_tasks(analysis.index, world.intents)
      task, reason = plan.current_task(tasks, world.intents, option)  # `--task`, else the one Current Task line
      fallback = next((hook for each in world.intents if (hook := each.host.current_task) is not None), None)
      unnamed = not any(each.current for each in world.intents)  # no state file names one
      if task is None and fallback is not None and unnamed:
          task, reason = fallback(tasks, analysis.plans)
  ```

  So the current task is the first unchecked box in file order of the one change that has any, else `no current task, as several changes have an unchecked task (<changes>): name one with --task`. The fallback is the hook of an intent's host, so it runs only when some intent has one: on an AI-DLC-only run `current_task`'s own reason stands, and `in_flight`'s "no state file names one, and no OpenSpec task is unchecked" speaks only for a run that holds an OpenSpec change. `reporter.py`: `RULES` gains `earnest/checked-unevidenced` and `earnest/untracked-box`, both `warning` (and the `RuleId` literal both names). The messages are written for the agent (T6):
  - `checked-unevidenced`: `<task> is checked in tasks.md, but <req> is <level>, not evidenced: uncheck the box, or tag and test the requirement until earnest check --judge --evidence reports it evidenced`;
  - `untracked-box`: "this checkbox has no task id line above it, so earnest cannot compute whether the task is done: write a `` `task~<name>~1` `` line and `Delivers: req~<name>~<n>` directly above it".

- [ ] **Step 4:** Run Step 2's command: expect `0`. Bind the scenario of Task 7 and run `rtk proxy uv run pytest tests/steps/test_openspec_host.py -k "ticked" -q; echo $?`: expect `0`, with the two warnings at `tasks.md:5` and `tasks.md:9` of the change. Then run `-k "supersedes"` again: expect `0`, with the same four findings and no `checked-unevidenced` (P8).
- [ ] **Step 5:** Update `01`: the step 2 of the Revision lifecycle and the Findings table (Task 0 Step 4's text, if Task 0 has landed), and `04`'s Messages bullet for the new rules. `mypy --strict`, ruff, vulture, the regression run: expect `0`, at the recorded count plus this task's tests, less the one in the integration file that the bare run leaves out.
- [ ] **Step 6:** Commit `feat: compute a task's done-status from its box and the evidence below its requirements`.

**Done when** (#24): `earnest plan` shows the computed status beside each task's checkbox in the fixture, and a stage check of `tasks` raises `checked-unevidenced` at the file and line of a checked task whose requirement is unevidenced.

### Task 8: Earnest's guidance in OpenSpec's workflow (#25)

**Files:** Create `integrations/openspec/config.snippet.yaml` and `integrations/openspec/README.md`. Modify `packages/earnest/tests/steps/test_openspec_host.py`, whose builder copies the snippet into the fixture, so the fixture's own `openspec/config.yaml` stays as Task 3 wrote it.

Built on spike A and a run on the drafted fixture: with the snippet below in `openspec/config.yaml`, `openspec instructions apply --change lockout-window --json` exits 0 and returns the three lines as `operationGuidance`, `openspec instructions archive --change lockout-window --json` returns the archive line, and `openspec validate --all --strict` still exits 0. Answer 6 (the agent writes the approval rows) adds a fourth apply line, which that run did not include: Step 4 measures it.

- [ ] **Step 1:** Bind the failing scenario 11 first: Given the repository with the `change` layer; When the coding agent runs `openspec instructions apply --change lockout-window --json`; Then `operationGuidance` holds a line naming `earnest check --judge --evidence`, a line that sends the agent to `tasks.md`, and a line naming `GATE_APPROVED` that tells the agent to write the approval row after the human approves. Run `rtk proxy uv run pytest tests/steps/test_openspec_host.py -k "apply and instructions" -q; echo $?`: expect a failure, because the snippet that the builder copies does not exist yet, non-zero. (A `-k` expression with two names and no operator is a usage error, exit 4, and runs nothing.) The scenario's builder copies `integrations/openspec/config.snippet.yaml` into the repository's `openspec/config.yaml`, under `schema:`, in one commit, so the guidance has one copy, the shipped one, and no equality test is needed.
- [ ] **Step 2:** Create `integrations/openspec/config.snippet.yaml`:

```yaml
operations:
  apply:
    guidance:
      - Before the first task, read docs/intent.md and tasks.md. Write earnest's id lines directly under each requirement heading, with a Covers line, and a task id line and a Delivers line directly above each checkbox.
      - Tag the code and tests you write, as `# [impl->req~<name>~<n>]` and `# [utest->req~<name>~<n>]`, naming the revision of the requirement as it stands in the change.
      - Tick a box only after earnest check --judge --evidence reports the requirements the task delivers as evidenced, and act on its findings first.
      - When the human approves a stage, and only then, append a GATE_APPROVED row for that stage to openspec/changes/<id>/audit/approvals.md, with User Input, the Assessment Hash and Items from the stage's earnest check --stage run (earnest check --stage <stage> --intent openspec/changes/<id>), and Approved By set to human. Never write the row before the human has approved, and never on the human's behalf.
  archive:
    guidance:
      - Run earnest check --judge --evidence before archiving, and archive only when it reports no error.
```

The first line sends the agent to `tasks.md` because `apply --json` omits ids (S13).

- [ ] **Step 3:** `integrations/openspec/README.md` says what the snippet does, how to install it (merge the `operations` block into `openspec/config.yaml`; never run `openspec install`), that the guidance is advisory (S12: OpenSpec's archive gate does not stop an open box), that the agent, not earnest, writes the `GATE_APPROVED` rows after the human approves (answer 6) and what the row holds, and that nothing checks the human approved first, that the `feat`, `goal` and `tenet` live in `docs/intent.md`, and the pin. Check it with `LINT_FILE=integrations/openspec/README.md make lint-file`. The snippet is a YAML file: `yamllint -c .yamllint.yml integrations/openspec/config.snippet.yaml; echo $?` exits 0.
- [ ] **Step 4:** Run Step 1's command: expect `0`. Run `openspec validate --all --strict` in the repository the builder gave the snippet (a test added to `tests/integration/test_openspec_ids.py`, run by path): expect `0`.
- [ ] **Step 5:** Regression run, then commit `feat: guidance that puts earnest's checks into OpenSpec's apply and archive steps`.

**Done when** (#25): in the fixture, `openspec instructions apply --change <id> --json` returns the earnest guidance of the shipped snippet, which the scenario's builder copies in, and the README documents how to install it.

### Task 9: The exit gate, lint, CI and the pre-PR review (#27)

**Files:** Modify `packages/earnest/pyproject.toml`, `packages/earnest/tests/steps/test_openspec_host.py` and this plan.

- [ ] **Step 1:** Remove M9's two `addopts` entries of Task 3 Step 5 (P5), and leave M7's. Run the exit command, `rtk proxy uv run pytest tests/steps/test_openspec_host.py; echo $?`, from `packages/earnest/`. Expected: all 11 scenarios pass, `0`.
- [ ] **Step 2:** Confirm the DERIVED rows of `04`'s M9 section against the combined tree, which Tasks 1 to 8 now build: the six findings of the `defects` state; the two `outdated` at the tags and no `duplicate` in the `change` state; the intent's stage rows; the two `checked-unevidenced` warnings, which come from the `tasks` stage check only (P8), with a plain `check` of the `change` state still at four findings; the `unbumped-change` finding after the `approved` layer. If a row differs, correct `04` and say why here (a changed scenario needs the maintainer's ratification, `04`'s "Fixed for the loop").
- [ ] **Step 3:** The #27 checks, each with its exit code under `rtk proxy`: `openspec validate --all --strict` exits `0` on every layer combination the feature builds; two `earnest check` runs give identical SARIF (scenario 2); each requirement is at one level with a located reason (scenario 3); a missing CLI fails the feature, shown by running with an empty `PATH`: expect `pytest.fail` naming `openspec`, non-zero.
- [ ] **Step 4:** The full run, `rtk proxy make test; echo $?` (prints `@fission-ai/openspec 2.1.1`, `0`), `make lint` (`0`), and `make build` (`0`). Record the test count and the coverage line here.
- [ ] **Step 5:** `03`: M9's node gains the `done` class in the graph, once the maintainer confirms the exit command ran green. The pre-PR review is the repository's gate: run the `/pre-pr-review` skill (`/simplify`, `/code-review`, `/ponytail:ponytail-review`), fix every finding, and report them before any push. No push, PR or GitHub write is part of this plan.
- [ ] **Step 6:** Commit `test: the openspec_host exit gate`.

**Done when** (#27): `uv run pytest tests/steps/test_openspec_host.py` passes, which shows the six bullets of the Goal.

### Task 10: REMOVED handling (#23, rest), DEFERRED

**Files:** Modify `packages/earnest/src/earnest/index.py` and `structural.py`. Test `packages/earnest/tests/unit/test_openspec_layers.py`.

Outside the exit path. `03` defers REMOVED and RENAMED in the exit fixture, no bullet of the exit behavior needs REMOVED, and Task 9 does not wait for this task. It needs answer 9 and Task 6. Start it only when the maintainer asks for it. Built on the REMOVED handling of spike C's design C that Task 6 left out, measured on 2026-11-25 (three REMOVED tests).

- [ ] **Step 1:** Write the failing tests in `test_openspec_layers.py`, with Task 6's `spec` and `run` helpers (the REMOVED block is written out, because `spec` writes none):

  ```python
  def test_a_removed_heading_without_an_id_removes_the_main_requirement_from_the_definitions():
      removed = "## REMOVED Requirements\n\n### Requirement: Greet\n**Reason**: gone.\n"
      index, found = run({MAIN_PATH: spec("Greet", 1), DELTA_PATH: removed}, tag="greet~1")
      assert ("req", "greet") not in index.defined
      assert ("earnest/orphaned", CODE) in found


  def test_a_removed_block_that_keeps_its_id_line_is_no_duplicate():
      removed = "## REMOVED Requirements\n\n### Requirement: Greet\n`req~greet~1`\n**Reason**: gone.\n"
      index, found = run({MAIN_PATH: spec("Greet", 1), DELTA_PATH: removed})
      assert ("req", "greet") not in index.defined
      assert found == []


  def test_a_removed_block_with_no_main_copy_left_defines_nothing():
      removed = "## REMOVED Requirements\n\n### Requirement: Greet\n`req~greet~1`\n**Reason**: gone.\n"
      index, found = run({DELTA_PATH: removed})  # `openspec sync` already dropped the main copy
      assert ("req", "greet") not in index.defined
      assert found == []
  ```

  a fourth, `test_a_tag_on_a_requirement_a_change_removes_is_orphaned_and_names_the_heading` (answer 9): the first test's tree, with the message of the `orphaned` finding at `CODE` naming `` `req~greet~1` `` and the removal's file and line; and a fifth, `test_a_removed_heading_drops_only_the_requirement_of_the_root_main_spec_it_names` (the root-only rule): `MAIN_PATH` holds `Greet` as `req~greet~1`; two more main files hold a `Greet` heading under other ids, `packages/x/tests/fixtures/openspec/specs/greeting/spec.md` (`req~nested-greet~1`) and `docs/greeting/spec.md` (`req~doc-greet~1`); `DELTA_PATH` removes `Greet`. Assert that `("req", "greet")` is not in `index.defined` and that the other two are. It fails if `heads` is keyed by the spec's folder name alone, because the last file of that folder name then takes the heading and the wrong id goes; and a sixth, `test_a_removed_heading_under_a_hidden_directory_below_changes_removes_nothing` (a `REMOVED` heading in `openspec/changes/.hidden/specs/greeting/spec.md`, which is no change, so `change_of` and `_spec_key` give none: `Greet` stays defined).

- [ ] **Step 2:** Run `rtk proxy uv run pytest tests/unit/test_openspec_layers.py -q; echo $?`. Expected: the six fail, non-zero.
- [ ] **Step 3:** Implement. In `index.py` (`PurePosixPath` is imported since Task 4): the two patterns, `Removal` (a requirement heading under `## REMOVED Requirements`, which may carry no id line), and the two fields of `Item` that say where its id line sits (`heading`, the `### Requirement:` heading above it, and `section`, the first word of the second-level heading above it: `ADDED`, `MODIFIED`, `REMOVED` or `RENAMED`):

  ```python
  _REQ_HEADING = re.compile(r"###[ \t]*Requirement:[ \t]*(.+?)(?:[ \t]+#+)?", re.IGNORECASE)
  _SECTION = re.compile(r"##[ \t]+(\S+).*")


  @dataclass(frozen=True)
  class Removal:
      """A requirement heading under `## REMOVED Requirements` in a change's delta, which may carry no id line."""

      name: str
      path: str
      line: int


  # Item gains, after `layer`:
  heading: str | None = field(default=None, compare=False)  # the `### Requirement:` heading above the id line
  section: str | None = field(default=None, compare=False)  # the first word of the `## ` heading above it
  ```

  `Index` gains `removals: tuple[Removal, ...] = ()` after `regions`, and `removed`, which maps the type and name of each requirement of a root main spec that an in-flight change removes to its removal. A requirement is found by the path of its spec below the root `openspec/specs/` and by its heading, and a removal by its path below `openspec/changes/<id>/specs/` and its name, so a same-named heading in a nested fixture's `openspec/specs/` or in another document is never dropped (the root-only rule):

  ```python
      @cached_property
      def removed(self) -> dict[tuple[str, str], Removal]:
          """Map the id key of each root main-spec requirement that a change lists as REMOVED to its removal."""
          heads = {
              (key, item.heading): item
              for item in self.items
              if item.layer == MAIN and (key := _spec_key(item.path)) is not None
          }
          return {
              heads[at].id.key: removal
              for removal in self.removals
              if (key := _spec_key(removal.path)) is not None and (at := (key, removal.name)) in heads
          }


  _SPECS = ("openspec", "specs")  # the root only, beside `_CHANGES`


  def _spec_key(path: str) -> PurePosixPath | None:
      """Return a spec file's path below the root `openspec/specs/` or a change's `specs/`, else None."""
      parts = PurePosixPath(path).parts
      if parts[: len(_SPECS)] == _SPECS:
          return PurePosixPath(*parts[len(_SPECS) :])
      if (change := change_of(path)) is not None:
          below = PurePosixPath(path).relative_to(change).parts
          if below[:1] == ("specs",):
              return PurePosixPath(*below[1:])
      return None
  ```

  In `Index.defined`, add the two lines that Task 6 left out: `if item.section == "REMOVED": continue` at the top of the loop (a tombstone that kept its id line defines nothing), and `return {key: item for key, item in found.items() if key not in self.removed}`. The parser tracks the heading and the section; `_Parsed` and `_spans` return the removals too, and `build_index` keeps those of delta sources:

  ```python
  _Span = tuple[Id, int, list[Line], str | None, str | None]  # an id, its line, its body, its heading and its section
  _Parsed = tuple[list[Item], list[Link], list[NearMiss], list[Removal]]

  # build_index: `removals: list[Removal] = []` beside `misses`, and in the loop over the sources
          found_items, found_links, found_misses, found_removals = parse(source)
          if source.layer == DELTA:
              removals.extend(found_removals)
  # ... and the return
      ordered = tuple(sorted(regions, key=_region_order))
      return Index(tuple(items), tuple(links), tuple(misses), ordered, tuple(removals))

  # _markdown: `spans, misses, removals = _spans(source)`, `for item_id, number, lines, heading, section in spans:`, and,
  #   with `hashed = _body_hash(lines, source.fenced, item_id.type == "task")` from Task 7,
          items.append(Item(item_id, source.path, number, needs, hashed, body, overrides, source.layer, heading, section))
  #   ... `return items, links, misses, removals`; `_tags` returns `[], links, misses, []`.

  # _spans: `-> tuple[list[_Span], list[NearMiss], list[Removal]]`, `removals: list[Removal] = []`,
  #   `section: str | None = None` and `heading: str | None = None` beside `body`, and
                  spans.append((_to_id(strict), line.number, body, heading, section))
          elif _HEADING.match(text):
              body = None
              heading, section = _retitle(text.strip(), section, source.path, line.number, removals)
  #   ... `return spans, misses, removals`


  def _retitle(
      text: str, section: str | None, path: str, number: int, removals: list[Removal]
  ) -> tuple[str | None, str | None]:
      """Return the requirement heading and the section that hold after an ATX heading, noting a heading REMOVED lists."""
      if (named := _REQ_HEADING.fullmatch(text)) is not None:
          if section == "REMOVED":
              removals.append(Removal(named.group(1), path, number))
          return named.group(1), section
      opened = _SECTION.fullmatch(text)
      return None, opened.group(1).upper() if opened else section
  ```

  In `structural.py`, `_duplicates` skips a REMOVED item and a tombstone: at the top of its second loop (the one over `index.items`), add `if item.section == "REMOVED" or item.id.key in index.removed: continue`. Task 6's function has no `first` at that point, so do not write a guard on `first`. `_links` yields `orphaned` for a link whose target is in `index.removed`, with the message `<id> is removed at <path>:<line>: remove this tag with the code it marks` (the placeholders are the item's id and its removal's file and line), straight after `item = resolution.item`:

  ```python
          if item is None and (gone := index.removed.get(link.target.key)) is not None:
              message = f"`{subject}` is removed at {gone.path}:{gone.line}: remove this tag with the code it marks"
              yield Finding(link.path, link.line, "earnest/orphaned", subject, message)
              continue
  ```

- [ ] **Step 4:** Run Step 2's command: expect `0`. Then `mypy --strict`, ruff, vulture and the regression run: expect `0`, at the recorded count plus 6.
- [ ] **Step 5:** Commit `feat: a requirement that a change removes defines nothing, and a tag on it is orphaned`.

**Done when** (#23, rest): a requirement removed in a change in flight is out of the definitions, and a tag on it is `orphaned` and names the heading. RENAMED needs nothing while ids are stable (answer 9).
