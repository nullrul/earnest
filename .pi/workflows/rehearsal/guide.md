# Milestone harness rehearsal guide

Workflow path: `/Users/rc/.herdr/worktrees/earnest/herdsman-work-7c4a24ca/.pi/workflows/milestone.workflow.ts` (harness commit `a89bcc1`, frozen).

Fixtures: `.pi/workflows/rehearsal/inputs.json`. Everything in it is synthetic and every `expected`/`exp` is a planned expectation, not an observed result. Fill `observed` from the real smoke.

## Warnings

- Never call `stop_lead`, `resume_project` or `inspect_staff` on synthetic ids (`synthetic-session-*`). Submit synthetic dispatch receipts with no real staff call, and delegate no Lead.
- Rehearsal can never yield `verified_candidate` or goal completion. The best outcome is status `rehearsal`, and `goalCompletion` is always false.
- D's human consent tests only the harness rehearsal gate. It approves nothing: not M2b and not any future material plan.
- These are planned expectations, not observed smoke results. Pause, resume, cancel, late answer and the human gate need the real server and are not offline-validated.

## How to use a fixture

- Start the workflow with `validStartInput`. Replace `<RUN_ID>` in every report or receipt with the real `runId`.
- Submit each receipt right after its dispatch step, then answer the `awaitReport` checkpoint with the next report.
- Derived fixtures use `from` plus `set`; see `_meta.legend` in the JSON.
- Offline check: a throwaway replay of the workflow's own `input`, `dispatch.validate`, `assess` and `finalize` accepted every fixture below (6 scenario runs, 45 checks, 51 strict-JSON round-trip assertions on every node output, exit 0).
- Observed in live rehearsal: A, adopted, B, C1 and C2 passed on `e7c41ba`. D failed before the H-R2 fix (undefined properties in the `needs_approval` output). On `a89bcc1` (Manager-reported live PASS):
  - D.outside run `20261013T204958876Z-milestone-2b107fda` completed `needs_approval` with outsidePaths `[synthetic/outside/Makefile]`.
  - D.material run `20261013T205134041Z-milestone-b85ced58` completed `needs_approval` with materialChange kind `scope`.
  - `plan-approval` run `20261013T205235713Z-plan-approval-7ef60441` (mode `required`): the model answer was refused with "Protected human decisions cannot be answered by the workflow tool"; the human answered `continue` at 2026-10-13T20:58:51Z with provenance `human`.
  - That human consent approves only the rehearsal, NOT any milestone plan.

## Order

1. Invalid start: submit `invalidStartInput`.
   - Expected: it is rejected with `Invalid milestone input: limits.maxRepairs must be an integer 0..3`.
   - OBSERVED (H-R1, live rehearsal, runs 79f78ba6 and acb6f503): the runner exits 1 with exactly that diagnostic and no dispatch happens, but the workflow tool only reports a generic no-progress message and parks the run. The Manager reads the exact reason from the runner diagnostic blob (`run_runners.diagnostic_hash` joined to `blobs`) in `~/.pi/agent/workflows/state.sqlite` with a READ-ONLY query, then cancels the run: `sqlite3 -readonly ~/.pi/agent/workflows/state.sqlite "SELECT CAST(b.content AS TEXT) FROM run_runners r JOIN blobs b ON b.blob_hash=r.diagnostic_hash WHERE r.run_id='<runId>' ORDER BY r.started_at DESC LIMIT 1"`. Do not redesign validation for this.
2. A (`scenarios.A`): fail, repair, blocking review, repair, fixed review, `rehearsal`. Expect repairs 2, invalidReports 1, finalSha W3, `synthetic-f1` fixed.
   - Step 3 is a stale answer (`staleCycle`) and must rewait.
   - Steps 4-6 are pause, answer-while-paused and resume. Pause the workflow only, never the staff. Expect no automatic re-dispatch.
3. Adopted case (`scenarios.adoptedCase`): `recRep2NotAdopted` and `recRep2AdoptedMissing` must be rejected with "must adopt the existing bound assignment". `recRep2` is then accepted. Cancel this throwaway run afterwards.
4. B: cancel while waiting on `awaitReport`, then answer `goodWrite1`. The late answer must be rejected and `finalize` must not run.
5. C1: repair cap, ending `exhausted`. C2: three invalid answers, ending `blocked` (invalid-report cap).
6. D: `D.outside` (and `variantMaterial`, a new run with `D.material`) ends `needs_approval`.
   - Then start a SEPARATE `plan-approval` run with `scenarios.D.planApproval.input` (mode `required`).
   - Do not forge an answer. A model or Manager `answer` must be rejected; the human answers with `/workflow answer` in the Pi channel.
