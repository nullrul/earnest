// Tests for milestone.workflow.ts. Run: node --test .pi/workflows/milestone.test.mjs
// Uses only the public @osolmaz/pi-workflows entry point (PI_WORKFLOWS_DIR overrides the install path),
// a temporary SQLite database for engine cases, and clearly SYNTHETIC fixtures (never a real human receipt).
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const PKG = process.env.PI_WORKFLOWS_DIR ?? "/Users/rc/.pi/agent/npm/node_modules/@osolmaz/pi-workflows";
const lib = await import(pathToFileURL(join(PKG, "dist/workflows/index.js")).href);
const def = await lib.loadWorkflowFile(fileURLToPath(new URL("./milestone.workflow.ts", import.meta.url)));
const dbDir = mkdtempSync(join(tmpdir(), "earnest-milestone-test-"));
let dbN = 0;
const newDb = () => join(dbDir, `state-${dbN++}.sqlite`);

// ------------------------------------------------------------------ fixtures (SYNTHETIC)
const sha = (c) => c.repeat(40);
const BASE = sha("a");
const W1 = sha("b");
const W2 = sha("c");
const WT = "/synthetic/worktree";
const BDD = { id: "bdd-1", argv: ["uv", "run", "pytest", "tests/bdd"], cwd: WT };
const LINT = { id: "lint", kind: "lint", argv: ["make", "lint"], cwd: WT };
const REG = { id: "regression", kind: "regression", argv: ["make", "test"], cwd: WT };
const WRITER = { lead: "lead-w", session: "sess-w", branch: "feat/writer" };
const REVIEWER = { lead: "lead-r", session: "sess-r", branch: "review/reader" };

const rawInput = (over = {}) => ({
  schema: "earnest.milestone-run.v1",
  milestoneId: "m-test",
  approvedPlan: {
    ref: "fixture:synthetic-test-only/plan",
    digest: "sha256:fixture",
    approval: { provenance: "human", decisionRef: "fixture:synthetic-test-only/decision", approvedAt: "2026-01-01T00:00:00Z" },
  },
  managerAttestation: { validatedBy: "fixture-manager", approvalReceiptChecked: true, resultRefsChecked: true },
  scope: { writer: { branch: WRITER.branch, worktree: WT }, paths: ["packages/earnest/src", "docs/"] },
  baseSha: BASE,
  gates: { bdd: [BDD], checks: [LINT, REG] },
  ...over,
});
const rehearsalInput = (over = {}) =>
  rawInput({
    rehearsal: true,
    approvedPlan: { ...rawInput().approvedPlan, ref: "synthetic:plan", approval: { ...rawInput().approvedPlan.approval, decisionRef: "synthetic:decision" } },
    ...over,
  });

let refN = 0;
const ref = () => `fixture:synthetic-test-only/result-${refN++}`;
const att = { validatedBy: "fixture-manager", resultRefsChecked: true };

/** Drives the pure nodes the way the engine would: dispatch.validate -> awaitReport answer -> assess. */
class Sim {
  constructor(input, runId = "run-1") {
    this.runId = runId;
    this.input = def.input(input);
    this.outputs = {};
    this.results = {};
  }
  ctx() {
    return { input: this.input, outputs: this.outputs, results: this.results, state: { runId: this.runId }, signal: new AbortController().signal };
  }
  get next() {
    return this.outputs.assess?.next ?? { action: "dispatch", phase: "write", cycle: 1, mode: "write" };
  }
  get corr() {
    return { runId: this.runId, milestoneId: this.input.milestoneId, phase: this.next.phase, cycle: this.next.cycle };
  }
  /** A repair or second review reuses the bound Lead, so the receipt must say it adopted it. */
  get bound() {
    const l = this.outputs.assess?.ledger;
    return this.next.mode === "repair" ? Boolean(l?.writer) : this.next.mode === "review" ? Boolean(l?.reviewer) : false;
  }
  receipt(assignee, over = {}) {
    return { schema: "earnest.milestone-dispatch.v1", correlation: this.corr, mode: this.next.mode, assignee, adopted: this.bound, ...over };
  }
  dispatch(assignee, over = {}) {
    const v = def.nodes.dispatch.validate(this.receipt(assignee, over), this.ctx());
    this.outputs.dispatch = v;
    this.results.dispatch = { outcome: "ok" };
    return v;
  }
  answer(report) {
    this.outputs.awaitReport = report;
    const a = def.nodes.assess.run(this.ctx());
    this.outputs.assess = a;
    return a;
  }
  finalize() {
    return def.nodes.finalize.run(this.ctx());
  }
}

const baseReport = (sim, role, over = {}) => ({
  schema: "earnest.milestone-report.v1",
  correlation: sim.corr,
  resultRef: ref(),
  reporter: { branch: role === "writer" ? WRITER.branch : REVIEWER.branch, role },
  status: "done",
  managerAttestation: { ...att },
  ...(sim.input.rehearsal ? { synthetic: true } : {}),
  trackedClean: true,
  trackedChanges: [],
  untrackedPreserved: true,
  untrackedDisclosed: [".pi-herdsman/notes.md"],
  limitations: [],
  ...over,
});
const cmd = (g, over = {}) => ({ id: g.id, argv: g.argv, cwd: g.cwd, exitCode: 0, where: "local", logRef: `fixture:log/${g.id}`, testedSha: W1, ...over });
const RED_SHA = sha("d");
const redEntry = (o = {}) => ({
  id: BDD.id,
  argv: BDD.argv,
  cwd: WT,
  exitCode: 1,
  failureKind: "behavior",
  expectedFailure: "AssertionError: feature missing before the change",
  logRef: "fixture:log/red",
  redSha: RED_SHA,
  chronology: `redSha ${RED_SHA.slice(0, 7)} is the earlier test-only commit; testedSha is its descendant with the implementation`,
  ...o,
});
const writerReport = (sim, over = {}) => {
  const testedSha = over.testedSha ?? W1;
  return baseReport(sim, "writer", {
    testedSha,
    changedPaths: ["packages/earnest/src/x.py"],
    red: [redEntry()],
    commands: [BDD, LINT, REG].map((g) => cmd(g, { testedSha })),
    gates: [{ id: BDD.id, exitCode: 0, result: "pass" }],
    findings: [],
    ...over,
  });
};
/** Findings default to the reviewed sha, as a real reviewer must report them. */
const reviewReport = (sim, over = {}) => {
  const testedSha = over.testedSha ?? W1;
  const findings = (over.findings ?? []).map((f) => ({ reviewSha: testedSha, ...f }));
  return baseReport(sim, "reviewer", { testedSha, changedPaths: [], ...over, findings });
};

/** Sim already past a first good writer report and dispatched to the reviewer. */
function atReview(input = rawInput(), runId) {
  const sim = new Sim(input, runId);
  sim.dispatch(WRITER);
  const a = sim.answer(writerReport(sim));
  assert.equal(a.route, "dispatch");
  assert.equal(a.next.phase, "review");
  sim.dispatch(REVIEWER);
  return sim;
}
const atWrite = (input = rawInput()) => {
  const sim = new Sim(input);
  sim.dispatch(WRITER);
  return sim;
};
const reasonsOf = (a) => a.reasons.join(" | ");

// ------------------------------------------------------------------ input
test("input: valid input normalises with default limits and trimmed scope", () => {
  const i = def.input(rawInput());
  assert.deepEqual(i.limits, { maxRepairs: 2, maxInvalidReports: 2 });
  assert.deepEqual(i.scope.paths, ["packages/earnest/src", "docs"]);
  assert.equal(i.rehearsal, false);
  assert.deepEqual(def.input(rawInput({ limits: { maxRepairs: 3, maxInvalidReports: 0 } })).limits, { maxRepairs: 3, maxInvalidReports: 0 });
});

test("input: rejections", () => {
  const approved = rawInput().approvedPlan;
  const cases = {
    "non-human provenance": rawInput({ approvedPlan: { ...approved, approval: { ...approved.approval, provenance: "model" } } }),
    "missing approval time": rawInput({ approvedPlan: { ...approved, approval: { ...approved.approval, approvedAt: "yesterday-ish" } } }),
    "bad base sha": rawInput({ baseSha: "abc" }),
    "duplicate ids": rawInput({ gates: { bdd: [BDD], checks: [{ ...LINT, id: BDD.id }] } }),
    "over-cap repairs": rawInput({ limits: { maxRepairs: 4 } }),
    "over-cap invalid reports": rawInput({ limits: { maxInvalidReports: 4 } }),
    "non-integer limit": rawInput({ limits: { maxRepairs: 1.5 } }),
    "relative worktree": rawInput({ scope: { writer: { branch: "b", worktree: "rel/wt" }, paths: ["a"] } }),
    "empty scope": rawInput({ scope: { writer: { branch: "b", worktree: WT }, paths: [] } }),
    "escaping scope path": rawInput({ scope: { writer: { branch: "b", worktree: WT }, paths: ["../x"] } }),
    "no manager attestation": rawInput({ managerAttestation: undefined }),
    "attestation not checked": rawInput({ managerAttestation: { validatedBy: "m", approvalReceiptChecked: true, resultRefsChecked: false } }),
    "no bdd gates": rawInput({ gates: { bdd: [], checks: [LINT] } }),
    "no checks": rawInput({ gates: { bdd: [BDD], checks: [] } }),
    "bad check kind": rawInput({ gates: { bdd: [BDD], checks: [{ ...LINT, kind: "style" }] } }),
    "relative gate cwd": rawInput({ gates: { bdd: [{ ...BDD, cwd: "rel" }], checks: [LINT] } }),
    "wrong schema": rawInput({ schema: "other" }),
    "synthetic approval outside rehearsal": rawInput({ approvedPlan: { ...approved, ref: "synthetic:plan" } }),
  };
  for (const [name, value] of Object.entries(cases)) assert.throws(() => def.input(value), /Invalid milestone input/, name);
  assert.throws(() => def.input("nope"), /Invalid milestone input/);
  assert.doesNotThrow(() => def.input(rehearsalInput()));
});

// ------------------------------------------------------------------ graph
test("graph: definition validates, node kinds are restricted, bounds are explicit", () => {
  lib.validateWorkflowDefinition(def);
  assert.deepEqual(Object.fromEntries(Object.entries(def.nodes).map(([k, n]) => [k, n.nodeType])), {
    dispatch: "agent",
    awaitReport: "checkpoint",
    assess: "compute",
    finalize: "compute",
  });
  assert.equal(def.includes, undefined);
  assert.equal(def.nodes.awaitReport.timeoutMs, null);
  assert.equal(def.nodes.awaitReport.humanDecision, undefined);
  assert.deepEqual(def.nodes.dispatch.allowedTools, ["staff_list", "staff_inspect", "staff_message", "staff_delegate", "staff_resume"]);
  assert.equal(def.nodes.dispatch.timeoutMs, 15 * 60_000);
  assert.equal(def.nodes.assess.timeoutMs, 30_000);
  assert.equal(def.nodes.finalize.timeoutMs, 30_000);
  assert.equal(def.startAt, "dispatch");
  const [R, I] = [3, 3]; // caps
  const worst = 3 * (2 * R + 2) + 2 * (I + 1) + 1;
  assert.ok(def.maxSteps >= worst, `maxSteps ${def.maxSteps} < worst case ${worst}`);
  assert.equal(def.maxSteps, 50);
});

// ------------------------------------------------------------------ dispatch receipt / ownership
test("dispatch receipt: accepted and normalised; prompt carries correlation and safeguards", () => {
  const sim = new Sim(rawInput());
  const prompt = def.nodes.dispatch.prompt(sim.ctx());
  assert.ok(prompt.includes(JSON.stringify(sim.corr)));
  for (const needle of ["staff_list", "staff_stop", "NEVER delete", "NONZERO", "different identity", "managerAttestation", "needs_approval", "never repeats side effects", "Do NOT wait"]) {
    assert.ok(prompt.includes(needle), `prompt missing ${needle}`);
  }
  const v = sim.dispatch(WRITER);
  assert.deepEqual(v.assignee, WRITER);
  assert.equal(v.adopted, false);
});

test("dispatch receipt: wrong run / phase / cycle / mode / branch / shape rejected", () => {
  const sim = new Sim(rawInput());
  const bad = (over, re) => assert.throws(() => def.nodes.dispatch.validate(sim.receipt(WRITER, over), sim.ctx()), re);
  bad({ correlation: { ...sim.corr, runId: "other-run" } }, /another run\/phase\/cycle/);
  bad({ correlation: { ...sim.corr, cycle: 2 } }, /another run\/phase\/cycle/);
  bad({ correlation: { ...sim.corr, phase: "review" } }, /another run\/phase\/cycle/);
  bad({ correlation: { ...sim.corr, milestoneId: "other" } }, /another run\/phase\/cycle/);
  bad({ mode: "review" }, /mode must be/);
  bad({ schema: "x" }, /schema must be/);
  bad({ assignee: { ...WRITER, branch: "someone/else" } }, /writer branch must be/);
  bad({ assignee: { lead: "l", session: "", branch: WRITER.branch } }, /non-empty lead, session and branch/);
  bad({ adopted: "yes" }, /adopted must be boolean/);
  assert.throws(() => def.nodes.dispatch.validate("garbage", sim.ctx()), /rejected/);
});

test("dispatch receipt: writer identity and reviewer independence are enforced across cycles", () => {
  const sim = atReview();
  // reviewer equal to the writer in any one dimension is rejected
  for (const clash of [{ ...REVIEWER, lead: WRITER.lead }, { ...REVIEWER, session: WRITER.session }, { ...REVIEWER, branch: WRITER.branch }]) {
    assert.throws(() => def.nodes.dispatch.validate(sim.receipt(clash), sim.ctx()), /reviewer must differ|reviewer must not use/);
  }
  // the writer identity is bound after the first accepted writer report
  const rep = new Sim(rawInput());
  rep.dispatch(WRITER);
  rep.answer(writerReport(rep, { commands: [BDD, LINT, REG].map((g) => cmd(g, { exitCode: g === LINT ? 2 : 0 })) }));
  assert.equal(rep.next.mode, "repair");
  assert.throws(() => def.nodes.dispatch.validate(rep.receipt({ ...WRITER, session: "sess-other" }), rep.ctx()), /writer identity changed/);
  assert.doesNotThrow(() => rep.dispatch(WRITER, { adopted: true }));
});

test("dispatch receipt: a bound reviewer cannot be swapped on a later review", () => {
  const sim = atReview();
  sim.answer(reviewReport(sim, { findings: [{ id: "f1", severity: "blocking", category: "logic", location: "x.py:1", disposition: "open", rationale: "wrong" }] }));
  assert.equal(sim.next.mode, "repair");
  sim.dispatch(WRITER);
  sim.answer(writerReport(sim, { testedSha: W2 }));
  assert.equal(sim.next.mode, "review");
  assert.throws(() => def.nodes.dispatch.validate(sim.receipt({ lead: "lead-r2", session: "sess-r2", branch: "review/other" }), sim.ctx()), /reviewer identity changed/);
});

// ------------------------------------------------------------------ happy path
test("pass: green writer evidence -> review; clean review -> verified_candidate with goalCompletion false", () => {
  const sim = atWrite();
  const a = sim.answer(writerReport(sim));
  assert.equal(a.route, "dispatch");
  assert.deepEqual(a.next, { action: "dispatch", phase: "review", cycle: 1, mode: "review" });
  assert.equal(a.ledger.lastTestedSha, W1);
  assert.deepEqual(a.ledger.writer, WRITER);
  sim.dispatch(REVIEWER);
  const wait = def.nodes.awaitReport.run(sim.ctx());
  assert.deepEqual(wait.expectedCorrelation, sim.corr);
  assert.deepEqual(wait.halt.staffStopTarget, REVIEWER);
  assert.equal(wait.halt.mustHaltOnPauseOrCancel, true);
  const r = sim.answer(
    reviewReport(sim, { findings: [{ id: "n1", severity: "non-blocking", category: "style", location: "x.py:2", disposition: "deferred", rationale: "cosmetic, tracked" }] }),
  );
  assert.equal(r.route, "finalize");
  assert.equal(r.next.status, "verified_candidate");
  const out = sim.finalize();
  assert.equal(out.schema, "earnest.milestone-result.v1");
  assert.equal(out.status, "verified_candidate");
  assert.equal(out.goalCompletion, false);
  assert.equal(out.finalSha, W1);
  assert.equal(out.dispatchUncertain, false);
  assert.deepEqual(out.assignees.writer, WRITER);
  assert.deepEqual(out.assignees.reviewer, REVIEWER);
  assert.deepEqual(out.halt.staffStopTarget, REVIEWER);
  assert.equal(out.evidenceRefs.length, 2);
  assert.equal(out.attestations.approval.provenance, "human");
  assert.equal(out.attestations.input.approvalReceiptChecked, true);
  assert.equal(out.attestations.reports.length, 2);
  assert.deepEqual(out.evidence.ci, []);
  assert.deepEqual(out.untrackedDisclosed, [".pi-herdsman/notes.md"]);
  assert.ok(out.managerActions.some((m) => m.includes("staff_stop")));
  assert.ok(out.limitations.some((l) => l.includes("Cancellation")));
});

// ------------------------------------------------------------------ safeguard 1: clean / untracked
test("clean: tracked changes, missing preservation claim, or a dishonest clean claim are rejected", () => {
  const cases = {
    "trackedClean false": { trackedClean: false },
    "trackedClean true with tracked changes": { trackedChanges: ["packages/earnest/src/x.py"] },
    "clean:false indication": { clean: false },
    "trackedChanges missing": { trackedChanges: undefined },
    "untracked preservation not claimed": { untrackedPreserved: undefined },
    "untracked list missing": { untrackedDisclosed: undefined },
  };
  for (const [name, over] of Object.entries(cases)) {
    const sim = atWrite();
    const a = sim.answer(writerReport(sim, over));
    assert.equal(a.route, "rewait", name);
    assert.match(reasonsOf(a), /tracked content must be unchanged|untrackedPreserved|untrackedDisclosed/, name);
  }
  const sim = atReview();
  assert.equal(sim.answer(reviewReport(sim, { trackedClean: false })).route, "rewait");
});

test("clean: disclosed untracked files are preserved, not rejected, and reach the result", () => {
  const sim = atWrite();
  sim.answer(writerReport(sim, { untrackedDisclosed: [".pi-herdsman/a.md", "notes/b.txt"] }));
  assert.deepEqual(sim.outputs.assess.ledger.untrackedDisclosed, [".pi-herdsman/a.md", "notes/b.txt"]);
  sim.dispatch(REVIEWER);
  sim.answer(reviewReport(sim, { untrackedDisclosed: ["notes/c.txt"] }));
  assert.deepEqual(sim.finalize().untrackedDisclosed, [".pi-herdsman/a.md", "notes/b.txt", "notes/c.txt"]);
  assert.ok(def.nodes.dispatch.prompt(atWrite().ctx()).includes("NEVER delete, clean, stash or reset untracked files"));
});

// ------------------------------------------------------------------ safeguard 2: red / green
test("red evidence: missing, zero, null, non-behavior, same/malformed sha, bad chronology or wrong gate is rejected", () => {
  const cases = {
    "no red": [{ red: [] }, /red/i],
    "red absent": [{ red: undefined }, /red/i],
    "zero exit": [{ red: [redEntry({ exitCode: 0 })] }, /NONZERO/],
    "null exit": [{ red: [redEntry({ exitCode: null })] }, /NONZERO/],
    "string exit": [{ red: [redEntry({ exitCode: "1" })] }, /NONZERO/],
    "vague reason": [{ red: [redEntry({ expectedFailure: "failed" })] }, /expectedFailure/],
    "no logRef": [{ red: [redEntry({ logRef: "" })] }, /logRef/],
    "not a BDD argv": [{ red: [redEntry({ argv: ["echo", "hi"] })] }, /exact id, argv and cwd/],
    "wrong cwd": [{ red: [redEntry({ cwd: "/elsewhere" })] }, /exact id, argv and cwd/],
    "wrong gate id": [{ red: [redEntry({ id: "other-gate" })] }, /exact id, argv and cwd/],
    "malformed redSha": [{ red: [redEntry({ redSha: "abc123" })] }, /40-hex sha of an EARLIER commit/],
    "missing redSha": [{ red: [redEntry({ redSha: undefined })] }, /40-hex sha of an EARLIER commit/],
    "identical sha": [{ red: [redEntry({ redSha: W1, chronology: `redSha ${W1.slice(0, 7)} equals the tested commit here` })] }, /must differ from the final testedSha/],
    "no chronology": [{ red: [redEntry({ chronology: undefined })] }, /chronology/],
    "chronology omits the sha": [{ red: [redEntry({ chronology: "ran before the implementation was written, honest" })] }, /chronology/],
    "startup failure": [{ red: [redEntry({ failureKind: "startup" })] }, /failureKind/],
    "import failure": [{ red: [redEntry({ failureKind: "import" })] }, /failureKind/],
    "collection failure": [{ red: [redEntry({ failureKind: "collection" })] }, /failureKind/],
    "no failureKind": [{ red: [redEntry({ failureKind: undefined })] }, /failureKind/],
  };
  for (const [name, [over, re]] of Object.entries(cases)) {
    const sim = atWrite();
    const a = sim.answer(writerReport(sim, over));
    assert.equal(a.route, "rewait", name);
    assert.match(reasonsOf(a), re, name);
  }
  // one valid behavior run is enough even next to a second red entry for another file's gate-less run
  const ok = atWrite();
  assert.equal(ok.answer(writerReport(ok, { red: [redEntry(), redEntry({ id: "extra", argv: ["x"], redSha: sha("e"), chronology: `redSha ${sha("e").slice(0, 7)} also came before the final commit` })] })).route, "dispatch");
  // a red run at the base commit is a legitimate earlier commit
  const atBase = atWrite();
  assert.equal(atBase.answer(writerReport(atBase, { red: [redEntry({ redSha: BASE, chronology: `redSha ${BASE.slice(0, 7)} is baseSha, before the change` })] })).route, "dispatch");
  // a writer that produced no commit is rejected
  const noCommit = atWrite();
  const n = noCommit.answer(writerReport(noCommit, { testedSha: BASE, commands: [BDD, LINT, REG].map((g) => cmd(g, { testedSha: BASE })) }));
  assert.match(reasonsOf(n), /equals baseSha/);
});

test("green evidence: missing, CI-only, argv/cwd mismatch, other sha, bad gates[] -> rewait", () => {
  const all = (fn) => [BDD, LINT, REG].map((g, i) => fn(g, i));
  const cases = {
    "missing check": { commands: [cmd(BDD), cmd(LINT)], re: /regression has no command evidence/ },
    "CI-only": { commands: all((g) => cmd(g, { where: g === REG ? "ci" : "local" })), re: /CI-only/ },
    "argv mismatch": { commands: all((g) => cmd(g, g === LINT ? { argv: ["make", "lint-lite"] } : {})), re: /argv\/cwd differs/ },
    "cwd mismatch": { commands: all((g) => cmd(g, g === LINT ? { cwd: "/elsewhere" } : {})), re: /argv\/cwd differs/ },
    "other sha": { commands: all((g) => cmd(g, g === REG ? { testedSha: W2 } : {})), re: /final testedSha/ },
    "no logRef": { commands: all((g) => cmd(g, g === REG ? { logRef: "" } : {})), re: /logRef/ },
    "gates disagree": { gates: [{ id: BDD.id, exitCode: 0, result: "fail" }], re: /disagrees/ },
    "gates missing": { gates: [], re: /no entry for BDD gate/ },
  };
  for (const [name, { re, ...over }] of Object.entries(cases)) {
    const sim = atWrite();
    const a = sim.answer(writerReport(sim, over));
    assert.equal(a.route, "rewait", name);
    assert.match(reasonsOf(a), re, name);
  }
});

test("non-zero or null required exit -> repair (not rewait); cap -> exhausted", () => {
  for (const code of [1, null]) {
    const sim = atWrite();
    const a = sim.answer(
      writerReport(sim, { commands: [BDD, LINT, REG].map((g) => cmd(g, g === REG ? { exitCode: code } : {})), gates: [{ id: BDD.id, exitCode: 0, result: "pass" }] }),
    );
    assert.equal(a.route, "dispatch", String(code));
    assert.equal(a.next.mode, "repair");
    assert.equal(a.next.cycle, 2);
    assert.equal(a.ledger.repairs, 1);
    assert.deepEqual(a.next.repairContext.failingCommands.map((f) => f.id), ["regression"]);
  }
  const sim = atWrite(rawInput({ limits: { maxRepairs: 1 } }));
  const failing = (s) => writerReport(s, { commands: [BDD, LINT, REG].map((g) => cmd(g, { exitCode: 1 })), gates: [{ id: BDD.id, exitCode: 1, result: "fail" }] });
  assert.equal(sim.answer(failing(sim)).route, "dispatch");
  sim.dispatch(WRITER);
  const end = sim.answer(failing(sim));
  assert.equal(end.route, "finalize");
  assert.equal(end.next.status, "exhausted");
  const out = sim.finalize();
  assert.equal(out.status, "exhausted");
  assert.equal(out.goalCompletion, false);
  assert.equal(out.counters.repairs, 1);
});

// ------------------------------------------------------------------ correlation / duplicates / caps
test("stale, wrong-run, wrong-attempt, duplicate and wrong-SHA reports -> rewait; invalid cap -> blocked", () => {
  const sim = atWrite();
  const stale = [
    writerReport(sim, { correlation: { ...sim.corr, cycle: 9 } }),
    writerReport(sim, { correlation: { ...sim.corr, runId: "old-run" } }),
    writerReport(sim, { correlation: { ...sim.corr, phase: "review" } }),
    writerReport(sim, { correlation: undefined }),
  ];
  const a1 = sim.answer(stale[0]);
  assert.equal(a1.route, "rewait");
  assert.match(reasonsOf(a1), /stale\/wrong-run\/wrong-attempt/);
  assert.deepEqual(a1.next, { action: "rewait", phase: "write", cycle: 1, mode: "write" });
  assert.equal(a1.ledger.invalidReports, 1);
  const a2 = sim.answer(stale[1]);
  assert.equal(a2.route, "rewait");
  const a3 = sim.answer(stale[2]); // third invalid with default cap 2 -> blocked
  assert.equal(a3.route, "finalize");
  assert.equal(a3.next.status, "blocked");
  assert.match(a3.next.blocker, /invalid-report cap/);
  assert.equal(sim.finalize().status, "blocked");

  // after a rewait the same expected correlation is still accepted
  const ok = new Sim(rawInput());
  ok.dispatch(WRITER);
  assert.equal(ok.answer(writerReport(ok, { correlation: { ...ok.corr, runId: "x" } })).route, "rewait");
  assert.equal(ok.answer(writerReport(ok)).route, "dispatch");
});

test("duplicate resultRef and wrong-SHA review are rejected", () => {
  const sim = atWrite();
  const first = writerReport(sim);
  sim.answer(first);
  sim.dispatch(REVIEWER);
  const dup = sim.answer(reviewReport(sim, { resultRef: first.resultRef }));
  assert.equal(dup.route, "rewait");
  assert.match(reasonsOf(dup), /duplicate resultRef/);
  const wrong = sim.answer(reviewReport(sim, { testedSha: W2 }));
  assert.equal(wrong.route, "rewait");
  assert.match(reasonsOf(wrong), /pin the writer's final testedSha/);
  const good = sim.answer(reviewReport(sim));
  assert.equal(good.next.status, "verified_candidate");
});

test("assess never throws on garbage answers", () => {
  for (const junk of [undefined, null, 5, "{{", "[]", [], {}, { schema: "earnest.milestone-report.v1" }, '{"schema":"earnest.milestone-report.v1","correlation":null}']) {
    const sim = atWrite();
    const a = sim.answer(junk);
    assert.equal(a.route, "rewait", String(junk));
  }
  // a JSON string answer is parsed
  const sim = atWrite();
  assert.equal(sim.answer(JSON.stringify(writerReport(sim))).route, "dispatch");
  // internal failure fails closed instead of throwing
  const broken = def.nodes.assess.run({ input: undefined, outputs: {}, results: {}, state: { runId: "r" }, signal: new AbortController().signal });
  assert.equal(broken.route, "finalize");
  assert.equal(broken.next.status, "blocked");
});

// ------------------------------------------------------------------ findings / review
test("blocking finding -> repair; dispositions are mandatory for non-blocking findings", () => {
  const blocking = { id: "b1", severity: "blocking", category: "logic", location: "x.py:9", disposition: "open", rationale: "off by one" };
  const sim = atReview();
  const a = sim.answer(reviewReport(sim, { findings: [blocking] }));
  assert.equal(a.route, "dispatch");
  assert.equal(a.next.mode, "repair");
  assert.deepEqual(a.next.repairContext.reviewFindings.map((f) => f.id), ["b1"]);
  // repair, then a fixed blocking finding no longer blocks
  sim.dispatch(WRITER);
  sim.answer(writerReport(sim, { testedSha: W2 }));
  assert.equal(sim.next.cycle, 2);
  assert.equal(sim.next.mode, "review");
  sim.dispatch(REVIEWER);
  const done = sim.answer(reviewReport(sim, { testedSha: W2, findings: [{ ...blocking, disposition: "fixed" }] }));
  assert.equal(done.next.status, "verified_candidate");
  assert.equal(sim.finalize().finalSha, W2);

  const nb = { id: "n1", severity: "non-blocking", category: "style", location: "x.py:1", rationale: "meh" };
  for (const [name, f] of Object.entries({ "no disposition": nb, "open non-blocking": { ...nb, disposition: "open" }, "unknown disposition": { ...nb, disposition: "later" }, "no rationale": { ...nb, disposition: "deferred", rationale: "" } })) {
    const s = atReview();
    const r = s.answer(reviewReport(s, { findings: [f] }));
    assert.equal(r.route, "rewait", name);
    assert.match(reasonsOf(r), /findings\[0\]/, name);
  }
  const s = atReview();
  assert.equal(s.answer(reviewReport(s, { findings: [{ ...nb, disposition: "accepted" }] })).next.status, "verified_candidate");
});

test("repair cap counts review-driven repairs too; review rounds stay <= repairs + 1", () => {
  const sim = atReview(rawInput({ limits: { maxRepairs: 1 } }));
  const blocking = (id) => [{ id, severity: "blocking", category: "c", location: "l", disposition: "open", rationale: "r" }];
  assert.equal(sim.answer(reviewReport(sim, { findings: blocking("b1") })).next.mode, "repair");
  sim.dispatch(WRITER);
  sim.answer(writerReport(sim, { testedSha: W2 }));
  sim.dispatch(REVIEWER);
  const end = sim.answer(reviewReport(sim, { testedSha: W2, findings: [...blocking("b1"), ...blocking("b2")] }));
  assert.equal(end.next.status, "exhausted");
  const c = sim.finalize().counters;
  assert.equal(c.repairs, 1);
  assert.ok(c.reviewCycle <= c.repairs + 1);
});

// ------------------------------------------------------------------ MUST1: review context + findings reconciliation
const B1 = { id: "b1", severity: "blocking", category: "logic", location: "x.py:9", disposition: "open", rationale: "off by one" };
/** Review 1 finds blocker b1; the writer repairs on W2; the sim is now dispatched to the SAME reviewer for review 2. */
function atSecondReview() {
  const sim = atReview();
  assert.equal(sim.answer(reviewReport(sim, { findings: [B1] })).next.mode, "repair");
  sim.dispatch(WRITER);
  // the writer claims b1 fixed; that claim must not clear it
  assert.equal(sim.answer(writerReport(sim, { testedSha: W2, findings: [{ ...B1, disposition: "fixed", rationale: "writer says fixed" }] })).next.mode, "review");
  sim.dispatch(REVIEWER);
  return sim;
}

test("review context: prompt carries evidence, logRefs, changedPaths, findings, repair context and the verification commands", () => {
  const sim = atSecondReview();
  const prompt = def.nodes.dispatch.prompt(sim.ctx());
  for (const needle of [
    "fixture:log/red", "fixture:log/lint", "packages/earnest/src/x.py", '"b1"', "off by one", "reviewFindings",
    `git diff --name-only ${BASE}..${W2}`, `git diff ${BASE}..${W2}`, "git merge-base --is-ancestor",
    "MUST explicitly disposition EVERY prior blocking finding", "audit trail",
  ]) assert.ok(prompt.includes(needle), `review prompt missing ${needle}`);
  const c = def.nodes.awaitReport.run(sim.ctx());
  assert.deepEqual(c.priorBlockingFindingIds, ["b1"]);
  assert.equal(c.reviewContext.testedSha, W2);
  assert.deepEqual(c.reviewContext.writerChangedPaths, ["packages/earnest/src/x.py"]);
  assert.ok(c.reviewContext.writerEvidence.red.length > 0 && c.reviewContext.repairContexts.length === 1);
  // write-phase checkpoint carries no review context
  assert.equal(def.nodes.awaitReport.run(atWrite().ctx()).reviewContext, null);
});

test("findings: a writer 'fixed' claim never clears a blocker; the trail keeps both reports", () => {
  const sim = atSecondReview();
  const l = sim.outputs.assess.ledger;
  assert.equal(l.findings.find((f) => f.id === "b1").disposition, "open");
  assert.deepEqual(l.findingTrail.map((f) => [f.id, f.by, f.disposition]), [["b1", "reviewer", "open"], ["b1", "writer", "fixed"]]);
});

test("findings: an empty second review is rejected while a prior blocker exists", () => {
  const sim = atSecondReview();
  const a = sim.answer(reviewReport(sim, { testedSha: W2, findings: [] }));
  assert.equal(a.route, "rewait");
  assert.match(reasonsOf(a), /prior blocking finding b1 is not dispositioned/);
  assert.equal(a.ledger.findings.find((f) => f.id === "b1").disposition, "open");
});

test("findings: an unknown or wrong id does not stand in for the prior id", () => {
  const sim = atSecondReview();
  const a = sim.answer(reviewReport(sim, { testedSha: W2, findings: [{ ...B1, id: "b9", disposition: "fixed" }] }));
  assert.equal(a.route, "rewait");
  assert.match(reasonsOf(a), /prior blocking finding b1 is not dispositioned/);
  const ok = sim.answer(reviewReport(sim, { testedSha: W2, findings: [{ ...B1, id: "b9", disposition: "fixed" }, { ...B1, disposition: "fixed" }] }));
  assert.equal(ok.next.status, "verified_candidate");
});

test("findings: a downgraded, accepted, deferred, wrong-reviewSha or reviewSha-less prior blocker is rejected for exactly one reason", () => {
  for (const [name, f, re] of [
    ["downgraded", { ...B1, severity: "non-blocking", disposition: "fixed" }, /cannot be downgraded/],
    ["accepted", { ...B1, disposition: "accepted" }, /open or fixed/],
    ["deferred", { ...B1, disposition: "deferred" }, /open or fixed/],
    ["wrong reviewSha", { ...B1, disposition: "fixed", reviewSha: W1 }, /reviewSha must equal/],
    ["no reviewSha", { ...B1, disposition: "fixed", reviewSha: undefined }, /reviewSha must equal/],
  ]) {
    const sim = atSecondReview();
    // reviewReport defaults reviewSha to the reviewed sha; only the reviewSha cases override it
    const a = sim.answer(reviewReport(sim, { testedSha: W2, findings: [f] }));
    assert.equal(a.route, "rewait", name);
    assert.equal(a.reasons.length, 1, `${name}: ${reasonsOf(a)}`);
    assert.match(reasonsOf(a), re, name);
  }
});

test("findings: explicitly resolved blocker clears via a fresh review; still-open one repairs again; trail is append-only", () => {
  const sim = atSecondReview();
  const done = sim.answer(reviewReport(sim, { testedSha: W2, findings: [{ ...B1, disposition: "fixed", rationale: "verified fixed at W2 in diff" }] }));
  assert.equal(done.next.status, "verified_candidate");
  const out = sim.finalize();
  assert.equal(out.findings.find((f) => f.id === "b1").disposition, "fixed");
  assert.equal(out.findings.find((f) => f.id === "b1").reviewSha, W2);
  assert.deepEqual(out.findingTrail.map((f) => f.disposition), ["open", "fixed", "fixed"]);
  assert.deepEqual(out.findingTrail.map((f) => f.by), ["reviewer", "writer", "reviewer"]);
  assert.equal(out.repairContexts.length, 1);

  const still = atSecondReview();
  const r = still.answer(reviewReport(still, { testedSha: W2, findings: [{ ...B1, disposition: "open", rationale: "still wrong" }] }));
  assert.equal(r.next.mode, "repair");
  assert.deepEqual(r.next.repairContext.reviewFindings.map((f) => f.id), ["b1"]);
});

// ------------------------------------------------------------------ SHOULD1: reviewer edits never blame the writer
test("review: claimed edits are rejected before scope handling and leave the writer ledger untouched", () => {
  for (const changedPaths of [["Makefile"], ["packages/earnest/src/y.py"], ["Makefile", "packages/earnest/src/x.py"]]) {
    const sim = atReview();
    const before = JSON.stringify(sim.outputs.assess.ledger);
    const a = sim.answer(reviewReport(sim, { changedPaths }));
    assert.equal(a.route, "rewait", JSON.stringify(changedPaths));
    assert.notEqual(a.next.status, "needs_approval");
    assert.equal(a.next.outsidePaths, undefined);
    assert.match(reasonsOf(a), /reviewer is read-only/);
    assert.deepEqual(a.ledger.changedPaths, ["packages/earnest/src/x.py"], "writer path ledger untouched");
    assert.deepEqual(a.ledger.writer, WRITER);
    assert.equal(JSON.stringify({ ...a.ledger, invalidReports: 0, rejections: [], history: [] }), JSON.stringify({ ...JSON.parse(before), invalidReports: 0, rejections: [], history: [] }));
  }
  // even with a materialChange attached, a reviewer edit claim is not accepted as a material change
  const sim = atReview();
  assert.equal(sim.answer(reviewReport(sim, { changedPaths: ["Makefile"], materialChange: { kind: "scope", description: "also edited Makefile" } })).route, "rewait");
  // a missing changedPaths is rejected too
  const m = atReview();
  assert.equal(m.answer(reviewReport(m, { changedPaths: undefined })).route, "rewait");
});

// ------------------------------------------------------------------ SHOULD3: pause / resume / adoption
test("pause/resume: halt and prompts name staff_stop (session) and staff_resume (branch); no duplicate delegation", () => {
  const sim = atWrite();
  const c = def.nodes.awaitReport.run(sim.ctx());
  assert.deepEqual(c.halt.staffStopTarget, WRITER);
  assert.deepEqual(c.halt.staffResumeTarget, { branch: WRITER.branch });
  const text = c.safeguards.join("\n");
  for (const needle of ["staff_stop on the EXACT assignee.session", "staff_resume the EXACT owned assignee.branch", "Never staff_delegate a new Lead for a correlation that already has an assignment", "CANCEL: no automatic resume", "staff_list/staff_inspect", "preserves the worktree and reports"]) {
    assert.ok(text.includes(needle), `safeguards missing ${needle}`);
  }
  assert.ok(def.nodes.dispatch.prompt(sim.ctx()).includes("Call staff_list FIRST"));
  assert.ok(def.nodes.dispatch.prompt(sim.ctx()).includes("ADOPT it"));
  const fin = atReview();
  fin.answer(reviewReport(fin));
  const out = fin.finalize();
  assert.deepEqual(out.halt.staffResumeTarget, { branch: REVIEWER.branch });
  assert.ok(out.managerActions.some((m) => m.includes("Never auto-resume after cancel")));
});

test("adoption: a repair or second review that delegates a duplicate Lead (adopted:false) is rejected; adopt is accepted", () => {
  const rep = new Sim(rawInput());
  rep.dispatch(WRITER);
  rep.answer(writerReport(rep, { commands: [BDD, LINT, REG].map((g) => cmd(g, { exitCode: g === LINT ? 2 : 0 })) }));
  assert.equal(rep.next.mode, "repair");
  assert.throws(() => def.nodes.dispatch.validate(rep.receipt(WRITER, { adopted: false }), rep.ctx()), /must adopt the existing bound assignment/);
  assert.throws(() => def.nodes.dispatch.validate(rep.receipt(WRITER, { adopted: undefined }), rep.ctx()), /must adopt/);
  assert.equal(rep.dispatch(WRITER, { adopted: true }).adopted, true);
  // first-time dispatches may be fresh delegations
  assert.equal(new Sim(rawInput()).dispatch(WRITER, { adopted: false }).adopted, false);
  const rv = atSecondReview();
  assert.equal(rv.outputs.dispatch.adopted, true);
  const sim = atReview();
  sim.answer(reviewReport(sim, { findings: [B1] }));
  sim.dispatch(WRITER);
  sim.answer(writerReport(sim, { testedSha: W2 }));
  assert.throws(() => def.nodes.dispatch.validate(sim.receipt(REVIEWER, { adopted: false }), sim.ctx()), /must adopt the existing bound assignment/);
});

// ------------------------------------------------------------------ COULD
test("could: synthetic prefix is case-insensitive; CI evidence is retained separately and never a local pass", () => {
  const real = atWrite();
  assert.match(reasonsOf(real.answer(writerReport(real, { resultRef: "SYNTHETIC:r1" }))), /synthetic resultRef/);
  assert.match(reasonsOf(real.answer(writerReport(real, { resultRef: " Synthetic:r2" }))), /synthetic resultRef/);
  const approved = rawInput().approvedPlan;
  assert.throws(() => def.input(rawInput({ approvedPlan: { ...approved, ref: "Synthetic:plan" } })), /synthetic approval references/);

  const sim = atWrite();
  const ciRun = cmd(REG, { where: "ci", logRef: "fixture:ci/regression" });
  assert.equal(sim.answer(writerReport(sim, { commands: [BDD, LINT, REG].map((g) => cmd(g)).concat([ciRun]) })).route, "dispatch");
  assert.deepEqual(sim.outputs.assess.ledger.evidence.ci.map((c) => c.logRef), ["fixture:ci/regression"]);
  assert.ok(sim.outputs.assess.ledger.evidence.commands.every((c) => c.where === "local"));
  sim.dispatch(REVIEWER);
  sim.answer(reviewReport(sim));
  assert.deepEqual(sim.finalize().evidence.ci.map((c) => c.where), ["ci"]);
  // CI-only still cannot satisfy the gate
  const ciOnly = atWrite();
  assert.match(reasonsOf(ciOnly.answer(writerReport(ciOnly, { commands: [cmd(BDD), cmd(LINT), ciRun] }))), /CI-only/);
});

// ------------------------------------------------------------------ approval / scope / blocked
test("out-of-scope paths and materialChange end needs_approval", () => {
  const sim = atWrite();
  const a = sim.answer(writerReport(sim, { changedPaths: ["packages/earnest/src/x.py", "Makefile"] }));
  assert.equal(a.route, "finalize");
  assert.equal(a.next.status, "needs_approval");
  assert.deepEqual(a.next.outsidePaths, ["Makefile"]);
  const out = sim.finalize();
  assert.equal(out.status, "needs_approval");
  assert.ok(out.managerActions.some((m) => m.includes("plan-approval") && m.includes("required")));
  assert.equal(out.goalCompletion, false);

  for (const kind of ["plan", "scope", "bdd"]) {
    const s = atWrite();
    const r = s.answer(writerReport(s, { materialChange: { kind, description: "needs a different approach" } }));
    assert.equal(r.next.status, "needs_approval", kind);
    assert.equal(s.finalize().materialChange.kind, kind);
  }
  const s = atWrite();
  assert.equal(s.answer(writerReport(s, { materialChange: { kind: "other", description: "x" } })).route, "rewait");
  const rv = atReview();
  assert.equal(rv.answer(reviewReport(rv, { changedPaths: ["packages/earnest/src/x.py"] })).route, "rewait"); // reviewer is read-only
  const rv2 = atReview();
  assert.equal(rv2.answer(reviewReport(rv2, { materialChange: { kind: "plan", description: "plan is wrong" } })).next.status, "needs_approval");
});

test("blocked reports (Lead or Manager-authored) finalize blocked; Manager cannot claim done", () => {
  const sim = atWrite();
  const a = sim.answer(baseReport(sim, "writer", { status: "blocked", blocker: "tool crashed" }));
  assert.equal(a.next.status, "blocked");
  assert.equal(a.next.blocker, "tool crashed");
  const m = atWrite();
  const blocked = m.answer({ ...baseReport(m, "manager", { status: "blocked", blocker: "Lead died; evidence herdsman:inspect/123" }), reporter: { branch: "manager", role: "manager" } });
  assert.equal(blocked.next.status, "blocked");
  const m2 = atWrite();
  assert.equal(m2.answer({ ...writerReport(m2), reporter: { branch: "manager", role: "manager" } }).route, "rewait");
  const m3 = atWrite();
  assert.equal(m3.answer(baseReport(m3, "writer", { status: "blocked" })).route, "rewait"); // blocker text required
});

test("reporter identity: wrong role, wrong branch and self-review are rejected; attestation is required", () => {
  const w = atWrite();
  assert.equal(w.answer(baseReport(w, "reviewer", { ...writerReport(w), reporter: { branch: REVIEWER.branch, role: "reviewer" } })).route, "rewait");
  const w2 = atWrite();
  assert.equal(w2.answer(writerReport(w2, { reporter: { branch: "someone/else", role: "writer" } })).route, "rewait");
  const self = atReview();
  const a = self.answer(reviewReport(self, { reporter: { branch: WRITER.branch, role: "reviewer" } }));
  assert.equal(a.route, "rewait");
  assert.match(reasonsOf(a), /dispatched assignee branch|not independent/);
  const noAtt = atWrite();
  const r = noAtt.answer(writerReport(noAtt, { managerAttestation: undefined }));
  assert.equal(r.route, "rewait");
  assert.match(reasonsOf(r), /managerAttestation/);
  const unchecked = atWrite();
  assert.equal(unchecked.answer(writerReport(unchecked, { managerAttestation: { validatedBy: "m", resultRefsChecked: false } })).route, "rewait");
});

// ------------------------------------------------------------------ rehearsal
test("rehearsal: synthetic marking required; never verified_candidate", () => {
  const sim = new Sim(rehearsalInput());
  sim.dispatch(WRITER);
  assert.ok(def.nodes.dispatch.prompt(sim.ctx()).includes("do NOT delegate"));
  const unmarked = writerReport(sim);
  delete unmarked.synthetic;
  assert.match(reasonsOf(sim.answer(unmarked)), /synthetic:true/);
  assert.equal(sim.answer(writerReport(sim)).route, "dispatch");
  sim.dispatch(REVIEWER);
  const r = sim.answer(reviewReport(sim));
  assert.equal(r.next.status, "rehearsal");
  const out = sim.finalize();
  assert.equal(out.status, "rehearsal");
  assert.notEqual(out.status, "verified_candidate");
  assert.equal(out.rehearsal, true);
  assert.equal(out.goalCompletion, false);
  assert.ok(out.limitations.some((l) => l.includes("synthetic")));
  assert.ok(out.managerActions.some((m) => m.includes("Synthetic rehearsal")));

  // a real run refuses synthetic-marked reports and synthetic refs
  const real = atWrite();
  assert.match(reasonsOf(real.answer(writerReport(real, { synthetic: true }))), /only allowed in rehearsal/);
  assert.match(reasonsOf(real.answer(writerReport(real, { resultRef: "synthetic:r1" }))), /synthetic resultRef/);
});

// ------------------------------------------------------------------ finalize / dispatch uncertainty
test("finalize: failed or timed-out dispatch -> blocked with dispatchUncertain and the exact assignee context", () => {
  for (const outcome of ["failed", "timed_out"]) {
    const sim = new Sim(rawInput());
    sim.results.dispatch = { outcome, error: "boom" };
    const first = sim.finalize();
    assert.equal(first.status, "blocked", outcome);
    assert.equal(first.dispatchUncertain, true);
    assert.match(first.blocker, /staff_list\/staff_inspect before ANY retry/);
    assert.equal(first.halt.staffStopTarget, null);
    assert.equal(first.halt.staffResumeTarget, null);
    assert.deepEqual(first.halt.uncertainTarget, { phase: "write", cycle: 1, correlation: { runId: "run-1", milestoneId: "m-test", phase: "write", cycle: 1 } });
    // after an earlier accepted writer cycle the known identity stays visible, but is never guessed as the stop target
    const later = atWrite();
    later.answer(writerReport(later));
    later.results.dispatch = { outcome };
    delete later.outputs.dispatch;
    const out = later.finalize();
    assert.equal(out.dispatchUncertain, true);
    assert.deepEqual(out.assignees.writer, WRITER);
    assert.equal(out.halt.staffStopTarget, null, "no blind stop of the writer");
    assert.equal(out.halt.staffResumeTarget, null);
    assert.deepEqual(out.halt.uncertainTarget.correlation, { runId: "run-1", milestoneId: "m-test", phase: "review", cycle: 1 });
    assert.ok(!JSON.stringify(out.halt).includes(WRITER.session) && !JSON.stringify(out.halt).includes(WRITER.branch), "halt must not name the writer");
    const act = out.managerActions[0];
    for (const needle of ["UNCERTAIN DISPATCH", "do NOT blind-stop", "staff_list then staff_inspect", "uncertainTarget.correlation", "stop only"].map((n) => n.replace("stop only", "staff_stop only that exact session"))) {
      assert.ok(act.includes(needle), `managerActions[0] missing ${needle}`);
    }
    assert.ok(!act.includes(WRITER.session));
  }
  // a normal (certain) result keeps the exact receipt target and has no uncertainTarget
  const ok = atReview();
  ok.answer(reviewReport(ok));
  const done = ok.finalize();
  assert.deepEqual(done.halt.staffStopTarget, REVIEWER);
  assert.equal(done.halt.uncertainTarget, undefined);
});

// ------------------------------------------------------------------ S-N1 / C-3: bound-Lead reuse vs first delegation
test("prompt: the FIRST review and FIRST write may staff_delegate a new Lead", () => {
  const first = new Sim(rawInput());
  const w = def.nodes.dispatch.prompt(first.ctx());
  assert.match(w, /ONLY for a first dispatch of this role, staff_delegate/);
  assert.ok(!w.includes("ALREADY-BOUND"));
  const rv = atReview(); // writer bound, reviewer not yet dispatched: rebuild the first-review prompt
  const firstReview = new Sim(rawInput());
  firstReview.dispatch(WRITER);
  firstReview.answer(writerReport(firstReview));
  const p = def.nodes.dispatch.prompt(firstReview.ctx());
  assert.ok(p.includes("first review: staff_delegate a NEW independent Lead"));
  assert.ok(p.includes(JSON.stringify(WRITER)), "names the writer it must differ from");
  assert.ok(!p.includes("ALREADY-BOUND") && !p.includes("NEVER staff_delegate for an already-bound"));
  assert.ok(rv);
});

test("prompt: second review and repair name the bound identity, forbid staff_delegate, require adopted:true", () => {
  const second = atSecondReview();
  const rv = def.nodes.dispatch.prompt(second.ctx());
  for (const needle of [JSON.stringify(REVIEWER), REVIEWER.branch, REVIEWER.session, "ALREADY-BOUND REVIEW Lead", "staff_message", `staff_resume its EXACT branch ${REVIEWER.branch} ONLY if it was stopped`, "adopted:true", "NEVER staff_delegate for an already-bound reviewer"]) {
    assert.ok(rv.includes(needle), `second-review prompt missing ${needle}`);
  }
  assert.ok(!rv.includes("a SEPARATE read-only REVIEW Lead (first review"));
  const repair = new Sim(rawInput());
  repair.dispatch(WRITER);
  repair.answer(writerReport(repair, { commands: [BDD, LINT, REG].map((g) => cmd(g, { exitCode: g === LINT ? 2 : 0 })) }));
  assert.equal(repair.next.mode, "repair");
  const rp = def.nodes.dispatch.prompt(repair.ctx());
  for (const needle of [JSON.stringify(WRITER), "ALREADY-BOUND WRITER Lead", "staff_message", `staff_resume its EXACT branch ${WRITER.branch} ONLY if it was stopped`, "adopted:true", "NEVER staff_delegate for an already-bound writer"]) {
    assert.ok(rp.includes(needle), `repair prompt missing ${needle}`);
  }
  // the generic step is first-dispatch-only
  assert.ok(rp.includes("ONLY for a first dispatch of this role"));
});

test("guidance: staff_resume is branch-only everywhere; task text goes via staff_message", () => {
  const sim = atSecondReview();
  const texts = [def.nodes.dispatch.prompt(sim.ctx()), def.nodes.awaitReport.run(sim.ctx()).safeguards.join("\n"), def.nodes.awaitReport.run(sim.ctx()).halt.instructions, sim.finalize().managerActions.join("\n")];
  for (const t of texts) {
    assert.ok(!/staff_resume[^.;]*(with the task|session)/i.test(t.replace(/staff_resume takes a branch only, no task, no session/g, "").replace(/staff_resume takes a branch; staff_stop takes the session/g, "")), "staff_resume must not be described as taking a task or session");
    assert.ok(!t.includes("staff_delegate (or staff_resume"));
  }
  assert.ok(texts[0].includes("staff_resume takes a branch only, no task, no session"));
  assert.ok(texts[3].includes("branch only; task text goes via staff_message"));
  assert.ok(texts[1].includes("staff_resume takes a branch"));
});

test("resume ownership: awaitReport content names the exact assignee and never re-dispatches by itself", () => {
  const sim = atWrite();
  const c = def.nodes.awaitReport.run(sim.ctx());
  assert.deepEqual(c.assignee, WRITER);
  assert.deepEqual(c.expectedReporter, { role: "writer", identity: WRITER });
  assert.ok(c.safeguards.some((s) => s.includes("staff_stop") && s.includes("RESUME: never re-dispatches")));
  const rejected = sim.answer(writerReport(sim, { trackedClean: false }));
  const again = def.nodes.awaitReport.run({ ...sim.ctx(), outputs: { ...sim.outputs, assess: rejected } });
  assert.equal(again.rejectionsRemaining, 1);
  assert.ok(again.lastRejection.length > 0);
});

// ------------------------------------------------------------------ engine (scripted executor, temp database)
const parseDispatch = (prompt) => ({
  corr: JSON.parse(/Correlation for this dispatch \(every report must echo it exactly\): (\{.*\})/.exec(prompt)[1]),
  mode: /, mode "(\w+)"/.exec(prompt)[1],
});
const identityFor = (mode) => (mode === "review" ? REVIEWER : WRITER);
const receiptFor = (prompt, adopted = false) => {
  const { corr, mode } = parseDispatch(prompt);
  return { schema: "earnest.milestone-dispatch.v1", correlation: corr, mode, assignee: identityFor(mode), adopted };
};
const engineFor = (executor) => new lib.WorkflowEngine({ executor, databasePath: newDb() });
const goodExecutor = (seen = []) => ({
  enforcesToolAllowlist: true,
  async runAgentStep(request) {
    // a repair, or a second review, reuses the bound Lead: it is adopted, never re-delegated
    const mode = parseDispatch(request.prompt).mode;
    const adopted = mode === "repair" || (mode === "review" && seen.some((r) => parseDispatch(r.prompt).mode === "review"));
    seen.push(request);
    const accepted = await request.accept(receiptFor(request.prompt, adopted));
    if (!accepted.ok) throw new Error(accepted.error);
    return { output: accepted.value };
  },
});

test("engine: accepted dispatch parks the run waiting on the no-timeout checkpoint", async () => {
  const seen = [];
  const { state } = await engineFor(goodExecutor(seen)).run(def, rawInput());
  assert.equal(state.status, "waiting");
  assert.equal(state.waitingOn, "awaitReport");
  assert.equal(seen.length, 1);
  assert.deepEqual(seen[0].contract.allowedTools, ["staff_list", "staff_inspect", "staff_message", "staff_delegate", "staff_resume"]);
  assert.equal(state.outputs.dispatch.assignee.branch, WRITER.branch);
  assert.equal(state.outputs.dispatch.correlation.runId, state.runId);
});

test("engine: a bad receipt is rejected, then a good one is accepted", async () => {
  const errors = [];
  const executor = {
    enforcesToolAllowlist: true,
    async runAgentStep(request) {
      const good = receiptFor(request.prompt);
      const bad = await request.accept({ ...good, correlation: { ...good.correlation, runId: "someone-elses-run" } });
      errors.push(bad.ok ? "accepted?!" : bad.error);
      const ok = await request.accept(good);
      if (!ok.ok) throw new Error(ok.error);
      return { output: ok.value };
    },
  };
  const { state } = await engineFor(executor).run(def, rawInput());
  assert.match(errors[0], /Dispatch receipt rejected: .*another run\/phase\/cycle/);
  assert.equal(state.status, "waiting");
});

test("engine: an executor without allowlist enforcement cannot run the dispatch step", async () => {
  const { state } = await engineFor({ async runAgentStep() { throw new Error("must not run"); } })
    .run(def, rawInput())
    .catch((e) => ({ state: { status: "threw", error: String(e) } }));
  assert.notEqual(state.status, "waiting");
});

test("engine: dispatch timeout routes to finalize as blocked dispatchUncertain", async () => {
  const fast = lib.defineWorkflow({ ...def, nodes: { ...def.nodes, dispatch: { ...def.nodes.dispatch, timeoutMs: 50 } } });
  const executor = {
    enforcesToolAllowlist: true,
    runAgentStep: (_request, signal) => new Promise((_resolve, reject) => signal.addEventListener("abort", () => reject(signal.reason ?? new Error("aborted")))),
  };
  const { state } = await engineFor(executor).run(fast, rawInput());
  assert.equal(state.status, "completed");
  assert.equal(state.results.dispatch.outcome, "timed_out");
  assert.equal(state.finalOutput.status, "blocked");
  assert.equal(state.finalOutput.dispatchUncertain, true);
  assert.equal(state.finalOutput.goalCompletion, false);
  assert.match(state.finalOutput.blocker, /^dispatchUncertain: dispatch step timed_out/);
  assert.equal(state.error, undefined);
  assert.equal(state.steps.at(-1).nodeId, "finalize");
});

test("engine: cancel while dispatching ends cancelled", async () => {
  let started;
  const running = new Promise((r) => (started = r));
  const executor = {
    enforcesToolAllowlist: true,
    runAgentStep: (_request, signal) =>
      new Promise((_resolve, reject) => {
        started();
        signal.addEventListener("abort", () => reject(signal.reason ?? new Error("aborted")));
      }),
  };
  const engine = engineFor(executor);
  const run = engine.run(def, rawInput());
  await running;
  engine.cancel();
  const { state } = await run;
  assert.equal(state.status, "cancelled");
});

// Not testable in-process: engine.resumeRun refuses a run whose status is "waiting" (store.js prepareRunResume);
// resuming a parked checkpoint, pause/resume, checkpoint answers and the human approval path go through the
// workflow server. They are covered by the Manager rehearsal smoke (A-D), not here.

/** Replace only the checkpoint with scripted answers (a human/Manager answer needs the server). */
function scriptedRun(answers, input, executor = goodExecutor()) {
  const queue = [...answers];
  const scripted = lib.defineWorkflow({
    ...def,
    nodes: { ...def.nodes, awaitReport: lib.compute({ run: (ctx) => queue.shift()(ctx) }) },
  });
  return engineFor(executor).run(scripted, input);
}
const next = (ctx) => ctx.outputs.assess?.next ?? { phase: "write", cycle: 1 };
const reportFor = (ctx, role, over = {}) => {
  const n = next(ctx);
  const sim = { corr: { runId: ctx.state.runId, milestoneId: ctx.input.milestoneId, phase: n.phase, cycle: n.cycle }, input: ctx.input };
  return role === "writer" ? writerReport(sim, over) : reviewReport(sim, over);
};

test("engine: repair loop end to end -> verified_candidate within the step bound", async () => {
  const failingWrite = (ctx) => reportFor(ctx, "writer", { commands: [BDD, LINT, REG].map((g) => cmd(g, { exitCode: g === LINT ? 1 : 0 })) });
  const blocking = [{ id: "b1", severity: "blocking", category: "logic", location: "x.py:1", disposition: "open", rationale: "wrong" }];
  const answers = [
    failingWrite, // repair 1
    (ctx) => reportFor(ctx, "writer"),
    (ctx) => reportFor(ctx, "reviewer", { findings: blocking }), // repair 2
    (ctx) => reportFor(ctx, "writer", { testedSha: W2 }),
    (ctx) => reportFor(ctx, "reviewer", { testedSha: W2, findings: [{ ...blocking[0], disposition: "fixed", rationale: "verified fixed at W2" }] }),
  ];
  const seen = [];
  const { state } = await scriptedRun(answers, rawInput(), goodExecutor(seen));
  assert.equal(state.status, "completed", state.error);
  assert.equal(state.finalOutput.status, "verified_candidate");
  assert.equal(state.finalOutput.goalCompletion, false);
  assert.equal(state.finalOutput.finalSha, W2);
  assert.equal(state.finalOutput.counters.repairs, 2);
  assert.deepEqual(seen.map((r) => parseDispatch(r.prompt).mode), ["write", "repair", "review", "repair", "review"]);
  assert.ok(state.steps.length <= def.maxSteps);
});

test("engine: invalid reports rewait up to the cap, then block", async () => {
  const stale = (ctx) => ({ ...reportFor(ctx, "writer"), correlation: { ...next(ctx), runId: "old" } });
  const { state } = await scriptedRun([stale, stale, stale], rawInput());
  assert.equal(state.status, "completed");
  assert.equal(state.finalOutput.status, "blocked");
  assert.equal(state.finalOutput.counters.invalidReports, 3);
  const dispatches = state.steps.filter((s) => s.nodeId === "dispatch").length;
  assert.equal(dispatches, 1, "a rewait must not re-dispatch");
});

test("engine: rehearsal end to end ends rehearsal, never verified_candidate", async () => {
  const answers = [(ctx) => reportFor(ctx, "writer"), (ctx) => reportFor(ctx, "reviewer")];
  const { state } = await scriptedRun(answers, rehearsalInput());
  assert.equal(state.finalOutput.status, "rehearsal");
});
