# Milestone harness rehearsal evidence

Tested SHA: `a89bcc1ab5de05b415b1351fd5880ad7a50d466e`. This is rehearsal evidence only, not milestone or goal completion.

## Checkpoint chain

`ab8edb6900071e7c135fd394e8d923cb5576c901` -> `578609abf2e3a5e976d5be704e737eaebbab2165` -> `e7c41baa142e149d3103a48b49541a1ae3ab9fdd` -> `a89bcc1ab5de05b415b1351fd5880ad7a50d466e`

Harness paths (unchanged by this close-out): `.pi/workflows/milestone.workflow.ts`, `.pi/workflows/milestone.test.mjs`. This close-out adds only `.pi/workflows/rehearsal/` (`guide.md`, `inputs.json`, `observed-a89bcc1.txt`, `EVIDENCE.md`).

## Commands run at close-out

| Command | Exit | Result |
| --- | --- | --- |
| `rtk proxy node --test .pi/workflows/milestone.test.mjs` | 0 | 48 tests, 48 pass, 0 fail |
| `LINT_FILE=.pi/workflows/rehearsal/guide.md make lint-file` | 0 | markdown clean |
| `LINT_FILE=.pi/workflows/rehearsal/EVIDENCE.md make lint-file` | 0 | markdown clean |

No test touched the global workflow database.

## Review chain

| Commit | Verdict |
| --- | --- |
| `ab8edb69` | accept-with-fixes, 1 MUST |
| `578609a` | clear-with-nits (S-N1) |
| `e7c41ba` | clear, 0 MUST, 0 blocking (per Manager) |
| `a89bcc1` | clear-with-nits, 0 MUST, 0 blocking (round 3 review) |

## Dispositions

- LOW, incorrect guide column `run_runners.diagnostic`: FIXED by this commit (guide now uses `diagnostic_hash` joined to `blobs`; query not run against the global database).
- COULD, vacuous `statuses` check at `milestone.test.mjs:910-911`: DEFERRED, non-blocking; the real assertions at 912-914 remain.
- Stale `outputs.dispatch` note: UNVERIFIED, not a gate.

## Round 5 nit dispositions

Base: `4ebb5ee4d5bf562a7b2ee10cfb99e68f27857ff6`. These offline checks do not replace the historical live rehearsal or establish milestone completion.

- R5-N1, non-idempotent scope normalization: FIXED. The parser strips all repeated leading `./` segments with `/^(?:\.\/)+/`. A regression using `././docs/` asserts that parsing twice equals parsing once and that the normalized path is `docs`.
- R5-N2, stale rehearsal references: FIXED. The guide points to tracked `.pi/workflows/rehearsal/inputs.json`; the fixture warnings point to tracked `.pi/workflows/rehearsal/guide.md`. Historical frozen-harness references are unchanged.

| Validation | Exit | Result |
| --- | --- | --- |
| Test-only RED on the unchanged base production file: `rtk proxy node --test .pi/workflows/milestone.test.mjs` | 1 | 59 tests, 58 pass, 1 fail: the new idempotence assertion, `docs` versus `./docs` |
| GREEN after the parser fix: same command | 0 | 59 tests, 59 pass, 0 fail |
| Obsolete-tool-name grep over the five changed harness paths | 1 | No matches; empty output, not a grep error |
| Cached markdownlint-cli2 0.19.1, both changed Markdown files | 0 | 0 errors; no install |
| `rtk proxy node --check .pi/workflows/milestone.test.mjs` | 0 | Syntax valid |
| JSON parse and corrected-reference checks | 0 | Both target files exist and are tracked |
| `git diff --check` | 0 | No whitespace errors |

Both test commands captured the raw exit status immediately, without a pipeline. `TMPDIR` was set to the ignored implementation evidence directory's `tmp` subdirectory, keeping temporary test databases inside this worktree; no global workflow database was used. RED output, the test-only patch, unchanged-production proof, GREEN output, and further check results are retained under ignored `.pi-herdsman/r5-nits-implementation/`. No live workflow was run for these nits. A broader recursive grep exited 0 because the unchanged historical `observed-a89bcc1.txt` transcript contains two lines with old tool names; it is outside the five-path change scope and was preserved. The scoped grep command and both scan outputs are retained with the implementation evidence.

## Live rehearsal

| Scenario | Commit | Outcome |
| --- | --- | --- |
| A | `e7c41ba` | completed `rehearsal`, goalCompletion false, repairs 2, invalidReports 1 |
| adopted | `e7c41ba` | non-adopted repair receipts rejected, adopted accepted |
| B | `e7c41ba` | cancelled while parked; late answer rejected, finalize not run |
| C1 | `e7c41ba` | `exhausted` (repair cap) |
| C2 | `e7c41ba` | `blocked` (invalid-report cap) |
| D.outside | `a89bcc1` | `needs_approval`, outsidePaths `[synthetic/outside/Makefile]` |
| D.material | `a89bcc1` | `needs_approval`, materialChange kind `scope` |
| plan-approval (required) | `a89bcc1` | model answer refused; human `continue` at 2026-10-13T20:58:51Z, provenance `human` |

Source: `observed-a89bcc1.txt` (also holds the e7c41ba runs and the pre-fix D failure). All inputs are synthetic. The human receipt is authentic but approves only the rehearsal, not any milestone plan.

## Limitations

- H-R1: invalid start input surfaces only a generic no-progress message in the workflow tool; the exact reason needs the read-only diagnostic query.
- Review replay: 173 checks clean plus 1 script error; no corrected rerun was done. It is not 174/174.
- Writer replay (45 checks, 51 round-trip assertions) is the writer's own and is uncorroborated.
- Schemas cannot prove approval or result refs; the Manager attestation is trusted.
- Synthetic rehearsals verify no real product BDD.
