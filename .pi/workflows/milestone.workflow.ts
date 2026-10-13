/**
 * earnest milestone harness (approved: questionnaire m00481, goal mv53vcue-djtcyq).
 *
 * A bounded, finite workflow that drives ONE already human-approved milestone
 * through write -> (repair)* -> review using Herdsman Leads. The Manager owns
 * dispatch and relaying; this workflow only decides, from reported evidence,
 * what happens next. No repository work happens in the Manager.
 *
 * Graph: dispatch (agent) -> awaitReport (checkpoint, no timeout) -> assess (compute)
 *        -> dispatch | awaitReport | finalize (compute). No shell, action, notify,
 *        humanDecision, or include nodes. All logic lives in THIS file because a
 *        resume only hashes this file.
 *
 * TRUST BOUNDARY (read this): the schemas below validate shape and cross-field
 * consistency. They cannot prove that a human approved the plan, that a command
 * really ran, or that a resultRef exists. The Manager is trusted to (a) check the
 * approval receipt before starting the run, and (b) check every resultRef/artifact
 * before relaying a report. Both are recorded as attestations in the input and in
 * every report and are echoed in the result so the reviewer and auditor can
 * challenge them. A rehearsal run uses synthetic fixtures and can never produce
 * `verified_candidate` or goal completion.
 *
 * `goalCompletion` is ALWAYS false: a verified_candidate is a candidate for review
 * and merge approval, never completion of the goal.
 *
 * Cancel: the engine ends a cancelled run WITHOUT running `finalize` (it throws
 * CancelledError before routing), so the halting guidance lives in the step
 * prompts and checkpoint content, which stay readable in the run state.
 */
import { isAbsolute } from "node:path";
import { agent, checkpoint, compute, defineWorkflow } from "@osolmaz/pi-workflows";

type Json = Record<string, unknown>;
type Identity = { lead: string; session: string; branch: string };
type Gate = { id: string; argv: string[]; cwd: string };
type Check = Gate & { kind: "regression" | "lint" | "build" };
type Input = {
  schema: string;
  milestoneId: string;
  approvedPlan: {
    ref: string;
    digest: string;
    approval: { provenance: "human"; decisionRef: string; approvedAt: string };
  };
  managerAttestation: {
    validatedBy: string;
    approvalReceiptChecked: true;
    resultRefsChecked: true;
  };
  scope: { writer: { branch: string; worktree: string }; paths: string[] };
  baseSha: string;
  gates: { bdd: Gate[]; checks: Check[] };
  limits: { maxRepairs: number; maxInvalidReports: number };
  rehearsal: boolean;
};
type Phase = "write" | "review";
type Mode = "write" | "repair" | "review";
type Next = {
  action: "dispatch" | "rewait" | "finalize";
  phase?: Phase;
  cycle?: number;
  mode?: Mode;
  repairContext?: unknown;
  status?: string;
  blocker?: string;
  materialChange?: unknown;
  outsidePaths?: string[];
};
type Ledger = {
  writeCycle: number;
  reviewCycle: number;
  repairs: number;
  invalidReports: number;
  acceptedRefs: string[];
  lastTestedSha: string | null;
  writer: Identity | null;
  reviewer: Identity | null;
  /** Reconciled CURRENT disposition per finding id. Only an independent reviewer report can move a blocker to fixed. */
  findings: Json[];
  /** Append-only audit trail of every finding as reported (writer claims included), never edited. */
  findingTrail: Json[];
  repairContexts: unknown[];
  changedPaths: string[];
  untrackedDisclosed: string[];
  evidence: { red: Json[]; commands: Json[]; gates: Json[]; ci: Json[] } | null;
  attestations: Json[];
  history: string[];
  rejections: string[];
};

const SCHEMAS = {
  run: "earnest.milestone-run.v1",
  report: "earnest.milestone-report.v1",
  result: "earnest.milestone-result.v1",
  receipt: "earnest.milestone-dispatch.v1",
  assess: "earnest.milestone-assess.v1",
  await: "earnest.milestone-await.v1",
} as const;

const STAFF_TOOLS = ["staff_list", "staff_inspect", "staff_message", "staff_delegate", "staff_resume"];
const SHA = /^[0-9a-f]{40}$/;
const ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
const CAPS = { maxRepairs: [2, 3], maxInvalidReports: [2, 3] } as const;
const DISPOSITIONS = ["open", "fixed", "accepted", "deferred"];

const isObj = (v: unknown): v is Json => v !== null && typeof v === "object" && !Array.isArray(v);
const nonEmpty = (v: unknown): v is string => typeof v === "string" && v.trim().length > 0;
const isArgv = (v: unknown): v is string[] => Array.isArray(v) && v.length > 0 && v.every(nonEmpty);
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every((s) => typeof s === "string");
const json = (v: unknown) => JSON.stringify(v);
const clone = <T>(v: unknown): T => JSON.parse(JSON.stringify(v));
// SAFETY: the engine passes a WorkflowNodeContext, a plain object; callbacks read it defensively as Json.
const asCtx = (c: unknown): Json => c as Json;
const msg = (e: unknown) => (e instanceof Error ? e.message : String(e));
const validDate = (v: unknown) => nonEmpty(v) && !Number.isNaN(Date.parse(v));
const relPath = (v: unknown): v is string =>
  nonEmpty(v) && !isAbsolute(v) && !v.includes("\\") && !v.split("/").some((s) => s === ".." || s === "");

/** Rules every prompt and checkpoint repeats so the Manager and Leads cannot miss them. */
const SAFEGUARDS = [
  "CLEAN means TRACKED content is unchanged versus testedSha: report trackedClean:true and trackedChanges:[]. Untracked user/evidence notes are PRESERVED and listed in untrackedDisclosed; report untrackedPreserved:true. NEVER delete, clean, stash or reset untracked files to become clean.",
  "WRITER evidence needs (1) RED: red[] entries each with an actual NONZERO integer exitCode, failureKind:\"behavior\" (startup/import/collection/syntax failures are NOT red evidence), expectedFailure (why the intended behavior failed), logRef, a 40-hex redSha of an EARLIER commit that differs from the final testedSha, and a chronology sentence naming that redSha (7+ chars) and its relation to testedSha; at least one entry must match a BDD gate by exact id, argv and cwd. The harness cannot prove ancestry: the reviewer must run git merge-base --is-ancestor <redSha> <testedSha>; and (2) GREEN: every BDD gate and check run LOCALLY on the final testedSha with exact argv/cwd, exitCode 0, logRef. CI-only evidence never satisfies a gate.",
  "REVIEWER must be a different identity (lead, session and branch) than the writer, is read-only (changedPaths:[] - a review claiming edits is rejected), and must pin the writer's final testedSha. Every finding carries reviewSha (= that testedSha). The reviewer MUST explicitly disposition EVERY prior blocking finding id (open|fixed) with rationale; a missing prior id is rejected, never silently cleared. Only a fresh independent reviewer report can clear a blocker; writer claims never do. Every non-blocking finding needs a disposition (fixed|accepted|deferred) and rationale.",
  "PAUSE: does not stop the Lead. The Manager MUST halt run-owned active execution with staff_stop on the EXACT assignee.session from the dispatch receipt (not optional), keep the assignment, worktree and evidence, and never stop unrelated sessions. RESUME: never re-dispatches automatically and never repeats side effects; staff_list/staff_inspect the receipt's assignee first, then, if that Lead was stopped, staff_resume the EXACT owned assignee.branch (staff_resume takes a branch; staff_stop takes the session). Never staff_delegate a new Lead for a correlation that already has an assignment: adopt it (staff_list, receipt adopted:true). CANCEL: no automatic resume; the Manager staff_stops the exact session, then staff_list/staff_inspect any uncertain target before any retry, and preserves the worktree and reports.",
  "TRUST: schemas cannot prove anything. The Manager attests (managerAttestation) that the approval receipt and every resultRef/artifact were actually checked before relaying; the harness only records and echoes that claim.",
  "A material plan/scope/BDD change, or changedPaths outside scope.paths, ends the run needs_approval; approval is a SEPARATE required plan-approval run, then a NEW harness run. This harness never approves anything and goalCompletion is always false.",
];

const REPORT_SHAPE = `{
  "schema": "${SCHEMAS.report}",
  "correlation": { "runId", "milestoneId", "phase", "cycle" },
  "resultRef": "unique per report",
  "reporter": { "branch", "role": "writer" | "reviewer" | "manager" },
  "status": "done" | "blocked",
  "managerAttestation": { "validatedBy", "resultRefsChecked": true },
  "synthetic": true            // required in rehearsal, forbidden otherwise
  "testedSha": "40-hex", "trackedClean": true, "trackedChanges": [], "untrackedPreserved": true,
  "untrackedDisclosed": [], "changedPaths": [],
  "red": [ { "id": BDD gate id, "argv", "cwd", "exitCode": nonzero int, "failureKind": "behavior", "expectedFailure", "logRef", "redSha": "40-hex earlier commit != testedSha", "chronology": "names redSha and its relation to testedSha" } ],  // writer, done
  "commands": [ { "id", "argv", "cwd", "exitCode": int|null, "where": "local"|"ci", "logRef", "testedSha" } ],  // writer, done
  "gates": [ { "id", "exitCode", "result": "pass"|"fail" } ],                                   // writer, done: one per BDD gate
  "findings": [ { "id": stable, "severity": "blocking"|"non-blocking", "category", "location", "disposition": "open"|"fixed"|"accepted"|"deferred", "rationale", "reviewSha": "reviewer only = testedSha" } ],   // reviewer: one entry per prior blocking id
  "limitations": [], "materialChange": { "kind": "plan"|"scope"|"bdd", "description" }?, "blocker": "required when blocked"
}`;

// ---------------------------------------------------------------- input

function parseInput(value: unknown): Input {
  const errs: string[] = [];
  const v: Json = isObj(value) ? value : {};
  if (!isObj(value)) errs.push("input must be an object");
  if (v.schema !== SCHEMAS.run) errs.push(`schema must be ${SCHEMAS.run}`);
  if (typeof v.milestoneId !== "string" || !ID.test(v.milestoneId)) errs.push("milestoneId must match " + ID);
  if (v.rehearsal !== undefined && typeof v.rehearsal !== "boolean") errs.push("rehearsal must be boolean");
  const rehearsal = v.rehearsal === true;

  const plan = isObj(v.approvedPlan) ? v.approvedPlan : {};
  const approval = isObj(plan.approval) ? plan.approval : {};
  if (!nonEmpty(plan.ref)) errs.push("approvedPlan.ref required");
  if (!nonEmpty(plan.digest)) errs.push("approvedPlan.digest required");
  if (approval.provenance !== "human") errs.push('approvedPlan.approval.provenance must be "human"');
  if (!nonEmpty(approval.decisionRef)) errs.push("approvedPlan.approval.decisionRef required");
  if (!validDate(approval.approvedAt)) errs.push("approvedPlan.approval.approvedAt must be an ISO date");
  if (!rehearsal && [plan.ref, approval.decisionRef].some((r) => typeof r === "string" && /^synthetic:/i.test(r.trim()))) {
    errs.push("synthetic approval references are only allowed with rehearsal:true");
  }

  const att = isObj(v.managerAttestation) ? v.managerAttestation : {};
  if (!nonEmpty(att.validatedBy)) errs.push("managerAttestation.validatedBy required");
  if (att.approvalReceiptChecked !== true) errs.push("managerAttestation.approvalReceiptChecked must be true");
  if (att.resultRefsChecked !== true) errs.push("managerAttestation.resultRefsChecked must be true");

  const scope = isObj(v.scope) ? v.scope : {};
  const writer = isObj(scope.writer) ? scope.writer : {};
  if (!nonEmpty(writer.branch)) errs.push("scope.writer.branch required");
  if (!nonEmpty(writer.worktree) || !isAbsolute(writer.worktree)) errs.push("scope.writer.worktree must be absolute");
  const paths = Array.isArray(scope.paths) ? scope.paths.map((p) => (typeof p === "string" ? p.replace(/^\.\//, "").replace(/\/+$/, "") : p)) : [];
  if (paths.length === 0 || !paths.every(relPath)) errs.push("scope.paths must be a non-empty list of relative paths without '..'");
  if (typeof v.baseSha !== "string" || !SHA.test(v.baseSha)) errs.push("baseSha must be a 40-hex sha");

  const gates = isObj(v.gates) ? v.gates : {};
  const bdd = Array.isArray(gates.bdd) ? gates.bdd : [];
  const checks = Array.isArray(gates.checks) ? gates.checks : [];
  if (bdd.length === 0) errs.push("gates.bdd needs at least one gate");
  if (checks.length === 0) errs.push("gates.checks needs at least one check");
  const ids = new Set<string>();
  const entry = (g: unknown, label: string, kinds: boolean) => {
    const o = isObj(g) ? g : {};
    if (typeof o.id !== "string" || !ID.test(o.id)) errs.push(`${label}.id invalid`);
    else if (ids.has(o.id)) errs.push(`duplicate gate/check id ${o.id}`);
    else ids.add(o.id);
    if (!isArgv(o.argv)) errs.push(`${label}.argv must be a non-empty string array`);
    if (!nonEmpty(o.cwd) || !isAbsolute(o.cwd)) errs.push(`${label}.cwd must be absolute`);
    if (kinds && !["regression", "lint", "build"].includes(String(o.kind))) errs.push(`${label}.kind must be regression|lint|build`);
  };
  bdd.forEach((g, i) => entry(g, `gates.bdd[${i}]`, false));
  checks.forEach((g, i) => entry(g, `gates.checks[${i}]`, true));

  const lim = isObj(v.limits) ? v.limits : {};
  const limits = { maxRepairs: CAPS.maxRepairs[0] as number, maxInvalidReports: CAPS.maxInvalidReports[0] as number };
  for (const key of ["maxRepairs", "maxInvalidReports"] as const) {
    const x = lim[key];
    if (x === undefined) continue;
    if (typeof x !== "number" || !Number.isInteger(x) || x < 0 || x > CAPS[key][1]) errs.push(`limits.${key} must be an integer 0..${CAPS[key][1]}`);
    else limits[key] = x;
  }
  if (v.limits !== undefined && !isObj(v.limits)) errs.push("limits must be an object");

  if (errs.length) throw new Error(`Invalid milestone input: ${errs.join("; ")}`);
  return clone<Input>({
    schema: SCHEMAS.run,
    milestoneId: v.milestoneId,
    approvedPlan: { ref: plan.ref, digest: plan.digest, approval: { provenance: "human", decisionRef: approval.decisionRef, approvedAt: approval.approvedAt } },
    managerAttestation: { validatedBy: att.validatedBy, approvalReceiptChecked: true, resultRefsChecked: true },
    scope: { writer: { branch: writer.branch, worktree: writer.worktree }, paths },
    baseSha: v.baseSha,
    gates: { bdd, checks },
    limits,
    rehearsal,
  });
}

// ---------------------------------------------------------------- state

const initialLedger = (): Ledger => ({
  writeCycle: 1,
  reviewCycle: 0,
  repairs: 0,
  invalidReports: 0,
  acceptedRefs: [],
  lastTestedSha: null,
  writer: null,
  reviewer: null,
  findings: [],
  findingTrail: [],
  repairContexts: [],
  changedPaths: [],
  untrackedDisclosed: [],
  evidence: null,
  attestations: [],
  history: [],
  rejections: [],
});
const initialNext = (): Next => ({ action: "dispatch", phase: "write", cycle: 1, mode: "write" });

function stateOf(ctx: Json): { ledger: Ledger; next: Next } {
  const outputs = (ctx.outputs ?? {}) as Json;
  const a = outputs.assess;
  if (isObj(a) && isObj(a.ledger) && isObj(a.next)) return { ledger: clone<Ledger>(a.ledger), next: clone<Next>(a.next) };
  return { ledger: initialLedger(), next: initialNext() };
}
const runIdOf = (ctx: Json) => String((ctx.state as Json | undefined)?.runId ?? "");
const inputOf = (ctx: Json) => ctx.input as Input;
const correlation = (ctx: Json, next: Next) => ({
  runId: runIdOf(ctx),
  milestoneId: inputOf(ctx).milestoneId,
  phase: next.phase,
  cycle: next.cycle,
});
const receiptOf = (ctx: Json): { assignee?: Identity } | null => {
  const r = ((ctx.outputs ?? {}) as Json).dispatch;
  return isObj(r) ? (r as { assignee?: Identity }) : null;
};
const openBlockers = (ledger: Ledger) => ledger.findings.filter((f) => f.severity === "blocking" && f.disposition !== "fixed");
const sameIdentity = (a: Identity, b: Identity) => a.lead === b.lead && a.session === b.session && a.branch === b.branch;

function haltGuidance(ledger: Ledger, receipt?: { assignee?: Identity } | null, uncertainTarget?: Json) {
  // A failed/timed-out dispatch has no receipt: never guess the writer; the Manager finds the real Lead by correlation.
  const target = uncertainTarget ? undefined : (receipt?.assignee ?? ledger.reviewer ?? ledger.writer);
  return {
    mustHaltOnPauseOrCancel: true,
    ...(uncertainTarget ? { uncertainTarget } : {}),
    staffStopTarget: target ?? null,
    staffResumeTarget: target ? { branch: target.branch } : null,
    instructions: SAFEGUARDS[3],
  };
}

// ---------------------------------------------------------------- dispatch

function dispatchPrompt(ctx: Json): string {
  const input = inputOf(ctx);
  const { ledger, next } = stateOf(ctx);
  const corr = correlation(ctx, next);
  const review = next.mode === "review";
  const bound = review ? ledger.reviewer : next.mode === "repair" ? ledger.writer : null;
  const target = bound
    ? `the ALREADY-BOUND ${review ? "REVIEW" : "WRITER"} Lead ${json(bound)} (branch ${bound.branch}, session ${bound.session})${review ? ` pinned to testedSha ${ledger.lastTestedSha}` : ` in worktree ${input.scope.writer.worktree}`}. REUSE it: send the task text with staff_message; staff_resume its EXACT branch ${bound.branch} ONLY if it was stopped (staff_resume takes a branch only, no task, no session); submit the receipt with adopted:true. NEVER staff_delegate for an already-bound ${review ? "reviewer" : "writer"}`
    : review
      ? `a SEPARATE read-only REVIEW Lead (first review: staff_delegate a NEW independent Lead whose lead, session and branch all differ from the writer${ledger.writer ? ` ${json(ledger.writer)}` : ""}) pinned to testedSha ${ledger.lastTestedSha}`
      : `the WRITER Lead on branch ${input.scope.writer.branch} (worktree ${input.scope.writer.worktree}; first write: staff_delegate)`;
  const lines = [
    `You are the Manager dispatching earnest milestone ${input.milestoneId} (${input.rehearsal ? "REHEARSAL" : "real run"}), mode "${next.mode}".`,
    `Correlation for this dispatch (every report must echo it exactly): ${json(corr)}`,
    "",
    `Dispatch to ${target}.`,
    input.rehearsal
      ? `REHEARSAL: do NOT delegate or start any Lead. Submit a clearly SYNTHETIC receipt (lead/session like "synthetic-${review ? "reviewer" : "writer"}"), review identity differing from the writer's. Every report must be marked synthetic:true with synthetic refs.`
      : `1. Call staff_list FIRST. If an assignment for this exact correlation already exists (for example after a resume), ADOPT it with staff_inspect/staff_message; never create a duplicate. Otherwise, ONLY for a first dispatch of this role, staff_delegate with the task below; an already-bound Lead is reused via staff_message (staff_resume takes a branch only and carries no task).\n2. Do NOT wait for the Lead and do NOT poll. Do no repository work yourself.`,
    "",
    "Submit exactly this receipt as soon as the assignment exists:",
    `{ "schema": "${SCHEMAS.receipt}", "correlation": ${json(corr)}, "mode": "${next.mode}", "assignee": { "lead": "<lead name>", "session": "<exact session id>", "branch": "<exact branch>" }, "adopted": <true|false> }`,
    "The receipt is rejected if its correlation names another run/phase/cycle, if the writer identity changes, or if the reviewer equals the writer.",
    "",
    "Task text to give the Lead (include these rules verbatim):",
    ...SAFEGUARDS.map((s) => `- ${s}`),
    `- Approved plan: ${json(input.approvedPlan)}; baseSha ${input.baseSha}; allowed paths ${json(input.scope.paths)}.`,
    `- BDD gates: ${json(input.gates.bdd)}`,
    `- Checks: ${json(input.gates.checks)}`,
    next.repairContext ? `- REPAIR context (fix these, do not redo accepted work): ${json(next.repairContext)}` : "",
    ...(review ? reviewContextLines(input, ledger, next) : [`- Report with phase "write", cycle ${next.cycle}.`]),
    "",
    "The Lead's report must follow this shape (you relay it only after verifying its resultRefs and artifacts):",
    REPORT_SHAPE,
  ];
  return lines.filter((l) => l !== "").join("\n");
}

/** Everything the reviewer needs; a blind review is how a prior blocker would silently vanish. */
function reviewContextLines(input: Input, ledger: Ledger, next: Next): string[] {
  const prior = openBlockers(ledger).map((f) => String(f.id));
  return [
    `- Review ONLY the writer's final testedSha ${ledger.lastTestedSha}; report with phase "review", cycle ${next.cycle}, reporter.role "reviewer", changedPaths [] and reviewSha ${ledger.lastTestedSha} on every finding.`,
    `- Writer evidence to inspect (open every logRef; do not trust the summary): ${json(ledger.evidence)}`,
    `- Writer-reported changedPaths: ${json(ledger.changedPaths)}; allowed scope ${json(input.scope.paths)}. VERIFY the actual scope yourself: git diff --name-only ${input.baseSha}..${ledger.lastTestedSha} and git diff ${input.baseSha}..${ledger.lastTestedSha} must match changedPaths and stay inside scope; also git merge-base --is-ancestor <each red.redSha> ${ledger.lastTestedSha}.`,
    `- Repair contexts so far (what earlier cycles had to fix): ${json(ledger.repairContexts)}`,
    `- Current findings by id (reconciled): ${json(ledger.findings)}`,
    `- Full finding audit trail: ${json(ledger.findingTrail)}`,
    prior.length
      ? `- You MUST explicitly disposition EVERY prior blocking finding id ${json(prior)} as "open" (still broken) or "fixed" with rationale and reviewSha. A missing id is REJECTED and never counts as cleared; writer claims never clear a blocker; only your independent verification does.`
      : "- There are no prior blocking findings; report any new findings with stable ids.",
  ];
}

function validateReceipt(output: unknown, ctx: Json): Json {
  const { ledger, next } = stateOf(ctx);
  const input = inputOf(ctx);
  const errs: string[] = [];
  const o = isObj(output) ? output : {};
  if (!isObj(output)) errs.push("receipt must be an object");
  if (o.schema !== SCHEMAS.receipt) errs.push(`schema must be ${SCHEMAS.receipt}`);
  const want = correlation(ctx, next);
  const got = isObj(o.correlation) ? o.correlation : {};
  if (!sameCorrelation(got, want)) errs.push(`receipt is for another run/phase/cycle: expected ${json(want)}, got ${json(o.correlation)}`);
  if (o.mode !== next.mode) errs.push(`mode must be "${next.mode}"`);
  const a = isObj(o.assignee) ? o.assignee : {};
  if (!nonEmpty(a.lead) || !nonEmpty(a.session) || !nonEmpty(a.branch)) errs.push("assignee needs non-empty lead, session and branch");
  else {
    const id: Identity = { lead: a.lead, session: a.session, branch: a.branch };
    if (next.mode === "review") {
      const w = ledger.writer;
      if (w && (id.lead === w.lead || id.session === w.session || id.branch === w.branch)) errs.push("reviewer must differ from the writer in lead, session and branch");
      if (id.branch === input.scope.writer.branch) errs.push("reviewer must not use the writer branch");
      if (ledger.reviewer && !sameIdentity(id, ledger.reviewer)) errs.push(`reviewer identity changed; run is bound to ${json(ledger.reviewer)}`);
    } else {
      if (id.branch !== input.scope.writer.branch) errs.push(`writer branch must be ${input.scope.writer.branch}`);
      if (ledger.writer && !sameIdentity(id, ledger.writer)) errs.push(`writer identity changed; run is bound to ${json(ledger.writer)}`);
    }
  }
  if (o.adopted !== undefined && typeof o.adopted !== "boolean") errs.push("adopted must be boolean");
  // The Lead for a repair/second review is already bound: reusing it is adoption (staff_list + staff_message; staff_resume by branch only if stopped), never a new delegation.
  if ((next.mode === "repair" ? ledger.writer : next.mode === "review" ? ledger.reviewer : null) && o.adopted !== true) {
    errs.push("this mode must adopt the existing bound assignment (adopted:true via staff_list + staff_message; staff_resume by exact branch only if stopped), not delegate a duplicate");
  }
  if (errs.length) throw new Error(`Dispatch receipt rejected: ${errs.join("; ")}`);
  return clone({ schema: SCHEMAS.receipt, correlation: want, mode: next.mode, assignee: { lead: a.lead, session: a.session, branch: a.branch }, adopted: o.adopted === true });
}

function sameCorrelation(a: Json, b: Json) {
  return a.runId === b.runId && a.milestoneId === b.milestoneId && a.phase === b.phase && a.cycle === b.cycle;
}

// ---------------------------------------------------------------- await

function awaitContent(ctx: Json) {
  const { ledger, next } = stateOf(ctx);
  const receipt = receiptOf(ctx);
  return {
    schema: SCHEMAS.await,
    expectedCorrelation: correlation(ctx, next),
    expectedReporter: next.phase === "review" ? { role: "reviewer", identity: receipt?.assignee ?? null } : { role: "writer", identity: receipt?.assignee ?? null },
    assignee: receipt?.assignee ?? null,
    rehearsal: inputOf(ctx).rehearsal,
    lastRejection: next.action === "rewait" ? ledger.rejections.slice(-5) : [],
    rejectionsRemaining: Math.max(0, inputOf(ctx).limits.maxInvalidReports - ledger.invalidReports),
    priorBlockingFindingIds: next.phase === "review" ? openBlockers(ledger).map((f) => f.id) : [],
    reviewContext: next.phase === "review" ? { testedSha: ledger.lastTestedSha, writerChangedPaths: ledger.changedPaths, writerEvidence: ledger.evidence, repairContexts: ledger.repairContexts, findings: ledger.findings } : null,
    howToAnswer: 'Call workflow {action:"answer", requestId:<this request>, input:<report object>} only AFTER verifying every resultRef/artifact. A Lead death or timeout is reported with a Manager-authored role:"manager", status:"blocked" report plus a Herdsman evidence ref.',
    halt: haltGuidance(ledger, receipt),
    safeguards: SAFEGUARDS,
    reportShape: REPORT_SHAPE,
  };
}

// ---------------------------------------------------------------- assess

type Evaluation =
  | { kind: "invalid"; reasons: string[] }
  | { kind: "blocked"; reason: string; accept: Accept }
  | { kind: "material"; materialChange?: unknown; outsidePaths?: string[]; accept: Accept }
  | { kind: "repair"; context: unknown; accept: Accept }
  | { kind: "review"; accept: Accept }
  | { kind: "pass"; accept: Accept };
type Accept = {
  ref: string;
  attestation: Json;
  testedSha?: string;
  changedPaths?: string[];
  untracked?: string[];
  findings?: Json[];
  evidence?: Ledger["evidence"];
  role?: string;
  phase?: Phase;
  cycle?: number;
  findingSha?: string;
};

const invalid = (...reasons: string[]): Evaluation => ({ kind: "invalid", reasons });

function parseAnswer(raw: unknown): { value?: Json; error?: string } {
  let v = raw;
  if (typeof v === "string") {
    try {
      v = JSON.parse(v);
    } catch {
      return { error: "report answer is not valid JSON" };
    }
  }
  return isObj(v) ? { value: v } : { error: "report answer must be a JSON object" };
}

function parseFindings(raw: unknown, errs: string[]): Json[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    errs.push("findings must be an array");
    return [];
  }
  const seen = new Set<string>();
  raw.forEach((f, i) => {
    const o = isObj(f) ? f : {};
    const at = `findings[${i}]`;
    if (!nonEmpty(o.id)) errs.push(`${at}.id required`);
    else if (seen.has(o.id)) errs.push(`${at}.id duplicate`);
    else seen.add(o.id);
    if (o.severity !== "blocking" && o.severity !== "non-blocking") errs.push(`${at}.severity must be blocking|non-blocking`);
    if (!nonEmpty(o.category) || !nonEmpty(o.location)) errs.push(`${at} needs category and location`);
    if (!nonEmpty(o.rationale)) errs.push(`${at}.rationale required`);
    if (!DISPOSITIONS.includes(String(o.disposition))) errs.push(`${at}.disposition required (${DISPOSITIONS.join("|")})`);
    else if (o.severity === "non-blocking" && o.disposition === "open") errs.push(`${at}: a non-blocking finding must be fixed, accepted or deferred, not open`);
  });
  return errs.length ? [] : clone<Json[]>(raw);
}

/** A review must re-disposition every prior open blocker at the reviewed sha; omission can never clear one. */
function reviewFindingErrors(findings: Json[], sha: string, ledger: Ledger): string[] {
  const errs: string[] = [];
  findings.forEach((f, i) => {
    if (f.reviewSha !== sha) errs.push(`findings[${i}].reviewSha must equal the reviewed testedSha ${sha}`);
  });
  const byId = new Map(findings.map((f) => [String(f.id), f]));
  for (const prior of openBlockers(ledger)) {
    const now = byId.get(String(prior.id));
    if (!now) errs.push(`prior blocking finding ${String(prior.id)} is not dispositioned: every prior blocking id needs an explicit open|fixed with rationale and reviewSha (omission never clears it)`);
    else if (now.severity !== "blocking") errs.push(`finding ${String(prior.id)} was blocking; its severity cannot be downgraded`);
    else if (now.disposition !== "open" && now.disposition !== "fixed") errs.push(`prior blocking finding ${String(prior.id)} must be dispositioned open or fixed, not ${String(now.disposition)}`);
  }
  return errs;
}

const insideScope = (p: string, scope: string[]) => scope.some((s) => p === s || p.startsWith(`${s}/`));

function writerEvidence(r: Json, input: Input, errs: string[]): { failures: Json[]; evidence: NonNullable<Ledger["evidence"]> } {
  const failures: Json[] = [];
  // RED: a nonzero behavior-test run proving the test failed before the change.
  const red = Array.isArray(r.red) ? r.red : [];
  if (red.length === 0) errs.push("writer evidence needs red[]: a behavior-test run that failed before the change");
  red.forEach((e, i) => {
    const o = isObj(e) ? e : {};
    if (!isArgv(o.argv) || !nonEmpty(o.cwd)) errs.push(`red[${i}] needs argv and cwd`);
    if (typeof o.exitCode !== "number" || !Number.isInteger(o.exitCode) || o.exitCode === 0) errs.push(`red[${i}].exitCode must be an actual NONZERO integer (zero/null is not red evidence)`);
    if (!nonEmpty(o.expectedFailure) || o.expectedFailure.trim().length < 10) errs.push(`red[${i}].expectedFailure must explain why it failed (>=10 chars)`);
    if (!nonEmpty(o.logRef)) errs.push(`red[${i}].logRef required`);
    if (o.failureKind !== "behavior") errs.push(`red[${i}].failureKind must be "behavior"; startup/import/collection/syntax failures are not behavior-test evidence (got ${json(o.failureKind)})`);
    if (typeof o.redSha !== "string" || !SHA.test(o.redSha)) errs.push(`red[${i}].redSha must be a 40-hex sha of an EARLIER commit`);
    else {
      if (o.redSha === r.testedSha) errs.push(`red[${i}].redSha must differ from the final testedSha (red and green on one commit shows no chronology)`);
      if (!nonEmpty(o.chronology) || o.chronology.trim().length < 20 || !o.chronology.includes(o.redSha.slice(0, 7))) {
        errs.push(`red[${i}].chronology must (>=20 chars) name redSha ${o.redSha.slice(0, 7)} and its earlier-commit relation to testedSha`);
      }
    }
  });
  const matchesGate = (e: unknown) => isObj(e) && input.gates.bdd.some((g) => e.id === g.id && json(g.argv) === json(e.argv) && e.cwd === g.cwd);
  if (red.length > 0 && !red.some(matchesGate)) {
    errs.push("red[] must include at least one run matching a BDD gate by exact id, argv and cwd (the behavior test that went red)");
  }
  // GREEN: exact gates and checks, local, on the final testedSha.
  const cmds = Array.isArray(r.commands) ? r.commands : [];
  const seen = new Set<string>();
  cmds.forEach((c, i) => {
    const o = isObj(c) ? c : {};
    const at = `commands[${i}]`;
    if (!nonEmpty(o.id) || !isArgv(o.argv) || !nonEmpty(o.cwd)) errs.push(`${at} needs id, argv and cwd`);
    if (o.exitCode !== null && !(typeof o.exitCode === "number" && Number.isInteger(o.exitCode))) errs.push(`${at}.exitCode must be an integer or null`);
    if (o.where !== "local" && o.where !== "ci") errs.push(`${at}.where must be local|ci`);
    if (!nonEmpty(o.logRef)) errs.push(`${at}.logRef required`);
    if (typeof o.testedSha !== "string" || !SHA.test(o.testedSha)) errs.push(`${at}.testedSha must be a 40-hex sha`);
    const key = `${o.id}/${o.where}`;
    if (seen.has(key)) errs.push(`${at} duplicates ${key}`);
    seen.add(key);
  });
  const commands: Json[] = [];
  const gatesReport = Array.isArray(r.gates) ? r.gates : [];
  const required = [...input.gates.bdd.map((g) => ({ ...g, bdd: true })), ...input.gates.checks.map((g) => ({ ...g, bdd: false }))];
  for (const req of required) {
    const mine = cmds.filter((c) => isObj(c) && c.id === req.id) as Json[];
    if (mine.length === 0) {
      errs.push(`required ${req.bdd ? "gate" : "check"} ${req.id} has no command evidence`);
      continue;
    }
    const local = mine.find((c) => c.where === "local");
    if (!local) {
      errs.push(`required ${req.id} has CI-only evidence; it must also run locally`);
      continue;
    }
    if (json(local.argv) !== json(req.argv) || local.cwd !== req.cwd) errs.push(`required ${req.id} argv/cwd differs from the approved input`);
    if (local.testedSha !== r.testedSha) errs.push(`required ${req.id} was not run on the final testedSha`);
    commands.push(local);
    if (local.exitCode !== 0) failures.push({ id: req.id, exitCode: local.exitCode ?? null, logRef: local.logRef });
    if (req.bdd) {
      const g = gatesReport.find((x) => isObj(x) && x.id === req.id) as Json | undefined;
      if (!g) errs.push(`gates[] has no entry for BDD gate ${req.id}`);
      else if (g.exitCode !== local.exitCode || g.result !== (local.exitCode === 0 ? "pass" : "fail")) errs.push(`gates[] entry for ${req.id} disagrees with its command`);
    }
  }
  // CI-reported runs are retained for the audit trail only; they never satisfy a gate above.
  const ci = cmds.filter((c) => isObj(c) && c.where === "ci");
  return { failures, evidence: { red: clone<Json[]>(red), commands: clone<Json[]>(commands), gates: clone<Json[]>(gatesReport), ci: clone<Json[]>(ci) } };
}

function evaluate(raw: unknown, ctx: Json, ledger: Ledger, next: Next): Evaluation {
  const input = inputOf(ctx);
  const parsed = parseAnswer(raw);
  if (!parsed.value) return invalid(parsed.error ?? "unreadable report");
  const r = parsed.value;
  if (r.schema !== SCHEMAS.report) return invalid(`schema must be ${SCHEMAS.report}`);
  const want = correlation(ctx, next);
  const got = isObj(r.correlation) ? r.correlation : {};
  if (!sameCorrelation(got, want)) {
    return invalid(`stale/wrong-run/wrong-attempt report: expected correlation ${json(want)}, got ${json(r.correlation)}`);
  }
  const errs: string[] = [];
  const ref = nonEmpty(r.resultRef) ? r.resultRef : "";
  if (!ref) errs.push("resultRef required");
  else if (ledger.acceptedRefs.includes(ref)) errs.push(`duplicate resultRef ${ref}`);
  if (!input.rehearsal && /^synthetic:/i.test(ref.trim())) errs.push("synthetic resultRef is not allowed outside rehearsal");
  if (input.rehearsal && r.synthetic !== true) errs.push("rehearsal reports must be marked synthetic:true");
  if (!input.rehearsal && r.synthetic !== undefined && r.synthetic !== false) errs.push("synthetic reports are only allowed in rehearsal");
  const att = isObj(r.managerAttestation) ? r.managerAttestation : {};
  if (!nonEmpty(att.validatedBy) || att.resultRefsChecked !== true) errs.push("managerAttestation {validatedBy, resultRefsChecked:true} is required: the Manager must verify resultRefs/artifacts before relaying");
  const rep = isObj(r.reporter) ? r.reporter : {};
  const role = rep.role;
  if (r.status !== "done" && r.status !== "blocked") errs.push('status must be "done" or "blocked"');
  if (!["writer", "reviewer", "manager"].includes(String(role))) errs.push("reporter.role must be writer|reviewer|manager");
  if (!nonEmpty(rep.branch)) errs.push("reporter.branch required");
  if (role === "manager") {
    if (r.status !== "blocked") errs.push("a Manager-authored report can only be status blocked");
  } else if (role !== undefined) {
    const phaseRole = next.phase === "review" ? "reviewer" : "writer";
    const assignee = receiptOf(ctx)?.assignee;
    if (role !== phaseRole) errs.push(`this phase expects a ${phaseRole} report`);
    else if (!assignee || rep.branch !== assignee.branch) errs.push(`reporter.branch must be the dispatched assignee branch ${assignee?.branch}`);
    if (role === "reviewer" && ledger.writer && rep.branch === ledger.writer.branch) errs.push("a review from the writer's own branch is not independent");
  }
  // A reviewer is read-only: reject any claimed edit BEFORE material/scope handling so a bad review never blames the writer.
  if (role === "reviewer" && (!Array.isArray(r.changedPaths) || r.changedPaths.length > 0)) {
    errs.push("a reviewer is read-only: changedPaths must be [] (claimed edits are rejected, not treated as a scope change)");
  }
  const material = r.materialChange;
  if (material !== undefined && !(isObj(material) && ["plan", "scope", "bdd"].includes(String(material.kind)) && nonEmpty(material.description))) {
    errs.push("materialChange must be {kind: plan|scope|bdd, description}");
  }
  if (errs.length) return { kind: "invalid", reasons: errs };

  const accept: Accept = { ref, attestation: { role, resultRef: ref, validatedBy: att.validatedBy } };
  if (material !== undefined) return { kind: "material", materialChange: clone(material), accept };
  if (r.status === "blocked") {
    return nonEmpty(r.blocker) ? { kind: "blocked", reason: r.blocker, accept } : invalid("a blocked report needs a blocker description");
  }

  // status done: tracked cleanliness, scope, then role-specific evidence.
  if (typeof r.testedSha !== "string" || !SHA.test(r.testedSha)) errs.push("testedSha must be a 40-hex sha");
  if (r.trackedClean !== true || !strings(r.trackedChanges) || r.trackedChanges.length > 0 || r.clean === false) {
    errs.push("tracked content must be unchanged vs testedSha (trackedClean:true, trackedChanges:[]); a clean claim with tracked changes is rejected");
  }
  if (r.untrackedPreserved !== true) errs.push("untrackedPreserved:true required: untracked files must never be erased to become clean");
  if (!strings(r.untrackedDisclosed)) errs.push("untrackedDisclosed must be an array of paths");
  const changed = strings(r.changedPaths) && r.changedPaths.every(relPath) ? (r.changedPaths as string[]) : null;
  if (!changed) errs.push("changedPaths must be an array of relative paths");
  if (errs.length) return { kind: "invalid", reasons: errs };
  if (next.phase === "write" && r.testedSha === input.baseSha) return invalid("testedSha equals baseSha: the writer produced no commit");
  const outside = (changed as string[]).filter((p) => !insideScope(p, input.scope.paths));
  accept.testedSha = r.testedSha as string;
  accept.changedPaths = changed as string[];
  accept.untracked = clone<string[]>(r.untrackedDisclosed);
  if (outside.length) return { kind: "material", outsidePaths: outside, accept };

  const findings = parseFindings(r.findings, errs);
  if (errs.length) return { kind: "invalid", reasons: errs };
  accept.findings = findings;
  accept.role = String(role);
  accept.phase = next.phase;
  accept.cycle = next.cycle;
  accept.findingSha = r.testedSha as string;
  // Writer findings are claims: a prior id never changes through them, so only NEW writer blockers count.
  const known = new Set(ledger.findings.map((f) => f.id));
  const openBlocking = findings.filter((f) => f.severity === "blocking" && f.disposition !== "fixed" && (role === "reviewer" || !known.has(f.id)));

  if (next.phase === "review") {
    if (r.testedSha !== ledger.lastTestedSha) return invalid(`review must pin the writer's final testedSha ${ledger.lastTestedSha}, got ${r.testedSha}`);
    const bad = reviewFindingErrors(findings, r.testedSha as string, ledger);
    if (bad.length) return { kind: "invalid", reasons: bad };
    return openBlocking.length ? { kind: "repair", context: { reviewFindings: openBlocking }, accept } : { kind: "pass", accept };
  }
  const { failures, evidence } = writerEvidence(r, input, errs);
  if (errs.length) return { kind: "invalid", reasons: errs };
  accept.evidence = evidence;
  if (failures.length || openBlocking.length) return { kind: "repair", context: { failingCommands: failures, openBlockingFindings: openBlocking }, accept };
  return { kind: "review", accept };
}

function out(route: "dispatch" | "rewait" | "finalize", next: Next, ledger: Ledger, reasons: string[]) {
  return { schema: SCHEMAS.assess, route, reasons, ledger, next };
}
// Engine outputs must survive a JSON round-trip, which rejects `undefined` properties (H-R2): keep only defined extras.
// Only undefined is dropped; any other non-JSON value is left for the engine to reject loudly.
const finalizeNext = (status: string, extra: Partial<Next> = {}): Next => ({
  action: "finalize",
  status,
  ...Object.fromEntries(Object.entries(extra).filter(([, v]) => v !== undefined)),
});

function assessRun(ctx: Json) {
  const { ledger, next } = stateOf(ctx);
  try {
    return assessInner(ctx, ledger, next);
  } catch (e) {
    return out("finalize", finalizeNext("blocked", { blocker: `assessInternalError: ${msg(e)}` }), ledger, [`assess failed closed: ${msg(e)}`]);
  }
}

/** Trail is append-only. Current dispositions change only through a reviewer; a writer can only ADD a new id. */
function reconcileFindings(ledger: Ledger, a: Accept) {
  for (const f of a.findings ?? []) {
    ledger.findingTrail.push({ ...f, by: a.role, resultRef: a.ref, phase: a.phase, cycle: a.cycle, testedSha: a.findingSha });
    const at = ledger.findings.findIndex((p) => p.id === f.id);
    if (a.role === "reviewer") {
      if (at >= 0) ledger.findings[at] = f;
      else ledger.findings.push(f);
    } else if (at < 0) ledger.findings.push(f);
  }
}

function assessInner(ctx: Json, ledger: Ledger, prev: Next) {
  const input = inputOf(ctx);
  const raw = ((ctx.outputs ?? {}) as Json).awaitReport;
  const ev = evaluate(raw, ctx, ledger, prev);
  const note = (s: string) => ledger.history.push(`${prev.phase}#${prev.cycle}: ${s}`);
  if (ev.kind === "invalid") {
    ledger.invalidReports += 1;
    ledger.rejections.push(...ev.reasons.map((x) => `${prev.phase}#${prev.cycle}: ${x}`));
    note(`rejected (${ev.reasons.length} reasons)`);
    if (ledger.invalidReports > input.limits.maxInvalidReports) {
      return out("finalize", finalizeNext("blocked", { blocker: `invalid-report cap exceeded (${input.limits.maxInvalidReports}); last reasons: ${ev.reasons.join("; ")}` }), ledger, ev.reasons);
    }
    return out("rewait", { ...prev, action: "rewait" }, ledger, ev.reasons);
  }
  const a = ev.accept;
  const receipt = receiptOf(ctx);
  ledger.acceptedRefs.push(a.ref);
  ledger.attestations.push(a.attestation);
  if (a.changedPaths) ledger.changedPaths = [...new Set([...ledger.changedPaths, ...a.changedPaths])];
  if (a.untracked) ledger.untrackedDisclosed = [...new Set([...ledger.untrackedDisclosed, ...a.untracked])];
  if (a.findings) reconcileFindings(ledger, a);
  if (a.evidence) ledger.evidence = a.evidence;
  const role = (a.attestation as Json).role;
  if (receipt?.assignee && role !== "manager") {
    if (prev.phase === "review") ledger.reviewer = receipt.assignee;
    else ledger.writer = receipt.assignee;
  }
  if (a.testedSha && prev.phase === "write") ledger.lastTestedSha = a.testedSha;

  switch (ev.kind) {
    case "blocked":
      note("blocked");
      return out("finalize", finalizeNext("blocked", { blocker: ev.reason }), ledger, [ev.reason]);
    case "material":
      note("needs approval");
      return out("finalize", finalizeNext("needs_approval", { materialChange: ev.materialChange, outsidePaths: ev.outsidePaths }), ledger, [ev.outsidePaths ? `changed paths outside scope: ${ev.outsidePaths.join(", ")}` : "material change reported"]);
    case "review": {
      ledger.reviewCycle += 1;
      note("writer evidence accepted");
      return out("dispatch", { action: "dispatch", phase: "review", cycle: ledger.reviewCycle, mode: "review" }, ledger, []);
    }
    case "repair": {
      note("needs repair");
      if (ledger.repairs + 1 > input.limits.maxRepairs) {
        return out("finalize", finalizeNext("exhausted", { blocker: `repair cap (${input.limits.maxRepairs}) exhausted`, repairContext: ev.context }), ledger, ["repair cap exhausted"]);
      }
      ledger.repairs += 1;
      ledger.writeCycle += 1;
      ledger.repairContexts.push(ev.context);
      return out("dispatch", { action: "dispatch", phase: "write", cycle: ledger.writeCycle, mode: "repair", repairContext: ev.context }, ledger, ["repair required"]);
    }
    case "pass":
      note("review clean");
      return out("finalize", finalizeNext(input.rehearsal ? "rehearsal" : "verified_candidate"), ledger, []);
  }
}

// ---------------------------------------------------------------- finalize

function finalizeRun(ctx: Json) {
  const input = inputOf(ctx);
  const { ledger, next } = stateOf(ctx);
  const outputs = (ctx.outputs ?? {}) as Json;
  const results = (ctx.results ?? {}) as Record<string, Json>;
  const dispatchResult = results.dispatch;
  const viaAssess = isObj(outputs.assess) && outputs.assess.route === "finalize";
  let status = next.status ?? "blocked";
  let blocker = next.blocker;
  let dispatchUncertain = false;
  if (!viaAssess) {
    dispatchUncertain = true;
    status = "blocked";
    blocker = `dispatchUncertain: dispatch step ${dispatchResult?.outcome ?? "did not complete"}${dispatchResult?.error ? ` (${String(dispatchResult.error)})` : ""}. A Lead may already exist: staff_list/staff_inspect before ANY retry; never duplicate an assignment.`;
  }
  if (input.rehearsal && status === "verified_candidate") status = "rehearsal";
  const lastReceipt = receiptOf(ctx);
  const ev = ledger.evidence;
  return {
    schema: SCHEMAS.result,
    status,
    milestoneId: input.milestoneId,
    runId: runIdOf(ctx),
    rehearsal: input.rehearsal,
    goalCompletion: false,
    blocker: blocker ?? null,
    dispatchUncertain,
    materialChange: next.materialChange ?? null,
    outsidePaths: next.outsidePaths ?? [],
    baseSha: input.baseSha,
    finalSha: ledger.lastTestedSha,
    changedPaths: ledger.changedPaths,
    untrackedDisclosed: ledger.untrackedDisclosed,
    gates: ev?.gates ?? [],
    findings: ledger.findings,
    findingTrail: ledger.findingTrail,
    repairContexts: ledger.repairContexts,
    evidence: { local: { red: ev?.red ?? [], commands: ev?.commands ?? [] }, ci: ev?.ci ?? [] },
    evidenceRefs: ledger.acceptedRefs,
    assignees: { writer: ledger.writer, reviewer: ledger.reviewer, lastDispatched: lastReceipt?.assignee ?? null },
    attestations: { input: input.managerAttestation, approval: input.approvedPlan.approval, reports: ledger.attestations },
    counters: { repairs: ledger.repairs, invalidReports: ledger.invalidReports, writeCycle: ledger.writeCycle, reviewCycle: ledger.reviewCycle },
    history: ledger.history,
    rejections: ledger.rejections,
    repairContext: next.repairContext ?? null,
    halt: haltGuidance(ledger, lastReceipt, dispatchUncertain ? { phase: next.phase ?? null, cycle: next.cycle ?? null, correlation: correlation(ctx, next) } : undefined),
    managerActions: [
      dispatchUncertain ? "UNCERTAIN DISPATCH: do NOT blind-stop and do not assume the writer. staff_list then staff_inspect by halt.uncertainTarget.correlation FIRST to find the actual Lead created for this phase/cycle (if any), staff_stop only that exact session, then keep its assignment, worktree and evidence. Never staff_delegate a duplicate." : "",
      "If any Lead for this run may still be active, staff_inspect it, then staff_stop that EXACT session from the assignees above (not optional); keep its assignment, worktree and evidence; never stop unrelated sessions. Never auto-resume after cancel; a deliberate resume uses staff_resume on the exact owned branch (branch only; task text goes via staff_message), never a new staff_delegate.",
      status === "needs_approval" ? "Run the built-in plan-approval workflow with {mode:\"required\"} as a SEPARATE run; after human approval start a NEW harness run with the amended input." : "",
      status === "verified_candidate" ? "Hand the candidate to independent review/auditing and merge approval; this is not goal completion." : "",
      status === "rehearsal" ? "Synthetic rehearsal only: no candidate exists and nothing may be merged or reported as complete." : "",
    ].filter(Boolean),
    limitations: [
      "Schemas cannot prove approvals, command runs or resultRefs; the Manager attestations are the only link to real evidence.",
      "RED-before-GREEN ordering and redSha ancestry cannot be proven from reported evidence; the reviewer and auditor must inspect the logRefs and run git merge-base --is-ancestor.",
      "CI-reported evidence is retained under evidence.ci and never counts as a local gate pass.",
      "Cancellation ends the run without running finalize; use the dispatch receipt in run state to halt the Lead.",
      ...(input.rehearsal ? ["REHEARSAL: all evidence is synthetic."] : []),
    ],
  };
}

// ---------------------------------------------------------------- definition

const workflow = defineWorkflow({
  name: "milestone",
  contractId: SCHEMAS.run,
  title: ({ input }) => `earnest milestone ${(input as Partial<Input>)?.milestoneId ?? ""}${(input as Partial<Input>)?.rehearsal ? " (rehearsal)" : ""}`,
  input: (value: unknown) => parseInput(value),
  startAt: "dispatch",
  maxSteps: 50,
  nodes: {
    dispatch: agent({
      allowedTools: STAFF_TOOLS,
      timeoutMs: 15 * 60_000,
      statusDetail: "dispatching Lead (no waiting)",
      prompt: (ctx) => dispatchPrompt(asCtx(ctx)),
      expectedOutput: `{ "schema": "${SCHEMAS.receipt}", "correlation": {runId, milestoneId, phase, cycle}, "mode": "write"|"repair"|"review", "assignee": {"lead", "session", "branch"}, "adopted": boolean }`,
      validate: (output, ctx) => validateReceipt(output, asCtx(ctx)),
    }),
    awaitReport: checkpoint({
      summary: "await the Lead's milestone report (no timeout)",
      timeoutMs: null,
      run: (ctx) => awaitContent(asCtx(ctx)),
    }),
    assess: compute({ timeoutMs: 30_000, run: (ctx) => assessRun(asCtx(ctx)) }),
    finalize: compute({ timeoutMs: 30_000, run: (ctx) => finalizeRun(asCtx(ctx)) }),
  },
  edges: [
    { from: "dispatch", switch: { on: "$result.outcome", cases: { ok: "awaitReport", failed: "finalize", timed_out: "finalize" } } },
    { from: "awaitReport", to: "assess" },
    { from: "assess", switch: { on: "$.route", cases: { rewait: "awaitReport", dispatch: "dispatch", finalize: "finalize" } } },
  ],
});

export default workflow;
