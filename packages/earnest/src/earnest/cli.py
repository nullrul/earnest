"""Command surface: `earnest check`, `earnest plan` and `earnest calibrate`, which wire the scanner, the index, the checks and the plan."""

import argparse
import contextlib
import os
import posixpath
import signal
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from earnest import adapters, ears, git, impact, judge, plan, reporter, structural
from earnest.index import Index, Item, Source, build_index
from earnest.reporter import Finding, Run


@dataclass(frozen=True)
class _World:
    """Everything one run reads before it decides anything."""

    root: Path
    commit: str
    sources: list[Source]
    changes: list[str]
    record: reporter.Record
    record_exists: bool
    intents: list[plan.Intent]


@dataclass(frozen=True)
class _Analysis:
    """What the run works out: the plans, every placed finding, the plan's own, and what each stage's status is."""

    index: Index
    levels: dict[str, str]
    plans: list[plan.Plan]
    findings: list[Finding]
    derived: list[Finding]
    statuses: dict[str, dict[str, plan.StageStatus]]
    run: Run
    cache: dict[str, object] | None = None  # the record's `judge` slot as a judge run leaves it, for `--judge` to write
    evidence: impact.Evidence | None = None  # what the evidence layer found, under `--evidence`
    entries: dict[str, dict[str, object]] = field(default_factory=dict)  # the `evidence` slot the run leaves


@dataclass(frozen=True)
class _Result:
    """What a run prints and returns; `notes` are stderr lines that come before the summary."""

    log: str
    summary: str
    code: int
    notes: str = ""


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return its exit code.

    The exit code is 0 when no error-level finding sits at position behind or current, 1 when one does, and 2 when
    the command cannot run: Git cannot answer, a file or the record cannot be read or written, the record is corrupt
    or newer, an intent or stage cannot be chosen, the judge's model or mutmut cannot run, or the reader of the log or the summary goes away.
    `earnest calibrate <fixture>` exits 0 when the judge passes calibration, 1 when it fails and 2 when it cannot run.
    An interrupt (Ctrl-C, SIGTERM or SIGHUP) also exits 2, after the run's cleanup.
    """
    if sys.stdout is None or sys.stderr is None:  # Python leaves a closed fd 1 or 2 as None, with nowhere to write
        return 2
    # a SIGTERM or SIGHUP ends Python without unwinding, leaving a run's process group and temp copy behind
    # only a default handler changes: an ignored SIGHUP, as nohup sets, or a caller's own handler stays
    numbers = [getattr(signal, name) for name in ("SIGTERM", "SIGHUP") if hasattr(signal, name)]
    changed = [number for number in numbers if signal.getsignal(number) is signal.SIG_DFL]
    for number in changed:
        signal.signal(number, signal.default_int_handler)
    try:
        return _main(argv)
    except KeyboardInterrupt:  # raised after the run's processes and temp copy are cleaned up on the way out
        _say("interrupted")
        return 2
    finally:  # the caller, such as a test run calling main in-process, gets its own handlers back
        for number in changed:
            signal.signal(number, signal.SIG_DFL)
        # a gone reader or dead terminal: devnull, so the shutdown flush cannot replace the exit code with 120
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except OSError:
            _quiet()


def _say(line: str) -> None:
    try:
        sys.stderr.write(f"earnest: {line}\n")
        sys.stderr.flush()
        sys.stdout.flush()  # unflushed stdout bytes would otherwise hit a gone reader at shutdown
    except OSError:  # a hung-up terminal or closed pipe: devnull stops the shutdown flush turning exit 2 into 120
        _quiet()


def _quiet() -> None:
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stdout.fileno())
    os.dup2(devnull, sys.stderr.fileno())


def _main(argv: Sequence[str] | None) -> int:
    parser = argparse.ArgumentParser(prog="earnest", description="Requirements traceability for LLM-written code.")
    # main never dispatches on the bare command, so a bare `earnest` must stop here rather than run the check
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="trace the repository; SARIF 2.1.0 on stdout, a summary on stderr")
    check.add_argument("--stage", help="check one stage: its id, or its slug when that is unambiguous")
    check.add_argument("--intent", help="the record directory of the intent, when there are several")
    check.add_argument(
        "--task",
        help="the current task, such as task~add-limiter~1; else the Current Task line of the state file names it",
    )
    check.add_argument("--judge", action="store_true", help="ask the model EARNEST_JUDGE names each judge question")
    check.add_argument(
        "--evidence", action="store_true", help="run the tests and mutmut on the tagged code; implies --judge"
    )
    commands.add_parser("plan", help="print the route, each stage's status and approval, and the frontier")
    calibrate = commands.add_parser("calibrate", help="compare the judge's verdicts on a fixture with the maintainer's")
    calibrate.add_argument(
        "fixture", type=Path, help="a directory in a Git work tree: ten requirements and verdicts.json"
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "calibrate":  # before _read(): the fixture, not the working directory, is what it indexes
            result = _calibrate(args.fixture)
        else:
            world = _read()
            result = _plan(world) if args.command == "plan" else _check(world, args)
    except (
        git.GitError,
        OSError,
        reporter.RecordError,
        plan.PlanError,
        judge.JudgeError,
        impact.EvidenceError,
    ) as error:
        _say(str(error))
        return 2
    try:
        sys.stdout.write(result.log)
        sys.stdout.flush()
        sys.stderr.write(result.notes + result.summary)
        sys.stderr.flush()
    except BrokenPipeError:  # a reader went away, as `head` does: stay silent and send what is left to devnull
        _quiet()
        return 2
    except OSError as error:  # a write failed (disk full, I/O error): say why; _say goes quiet if stderr is dead too
        _say(f"cannot write the result: {error}")
        return 2
    return result.code


def _read() -> _World:
    root = git.repo_root(Path.cwd())
    commit = git.head_commit(root)
    files = git.work_tree_files(root)
    sources = adapters.scan(root, files)
    intents = [plan.intent(record) for record in plan.load(root, files)]
    record = reporter.read_record(root)
    return _World(root, commit, sources, git.changes(root), record, (root / reporter.RECORD).exists(), intents)


def _analyse(world: _World, model: judge.Model | None = None, *, evidence: bool = False) -> _Analysis:
    index = build_index(world.sources)
    produces = plan.produces(world.intents)
    levels = structural.traced(index, produces)
    asked: list[Finding] = []
    cache: dict[str, object] | None = None
    observations: tuple[Mapping[str, object], ...] | None = None
    if model is not None:
        judged = judge.judge(index, levels, model, world.root, world.record)
        levels, asked, cache, observations = judged.levels, judged.findings, judged.cache, tuple(judged.observations)
    proof = impact.evidence(world.root, index, levels) if evidence else None  # after the judge, before placement
    failed = impact.evidence_failed(world.root, index, proof) if proof is not None else []
    entries = _entries(world, index, levels, proof, failed)
    current = impact.keys(world.root, index, entries)  # a held key counts only when the tree still gives it
    levels = impact.evidenced(levels, entries, current, judged=model is not None)
    plans = [plan.build(current, index) for current in world.intents]
    built = [each.intent for each in plans]  # each with its per-unit stages and the approvals that count for them
    frozen = plan.frozen_bodies(world.record.bodies, built)
    own = [found for each in plans for found in (*plan.plan_findings(each, index), *plan.approval_findings(each))]
    derived = plan.place(plans, index, own)
    checked = [*structural.check(index, produces=produces, frozen=frozen), *ears.findings(index)]
    checked += asked
    checked += failed
    findings = [*plan.place(plans, index, checked), *derived]
    statuses = {each.intent.directory: plan.statuses(each, index, findings, levels) for each in plans}
    props = plan.properties(plans, statuses, index, levels) if world.intents else None
    held = world.record.bodies
    unheld = sum(1 for item in index.defined.values() if _in_any(built, item.path) and str(item.id) not in held)
    run = Run(
        world.commit,
        plan.dirty(world.changes, world.intents),
        plan=props,
        record_absent=not world.record_exists and bool(index.defined),
        unheld=unheld if world.record_exists else 0,
        model=None if model is None else model.id,
        prompt=None if model is None else judge.PROMPT_HASH,
        observations=observations,
        evidence=evidence,
    )
    return _Analysis(index, levels, plans, findings, derived, statuses, run, cache, proof, entries)


def _entries(
    world: _World, index: Index, levels: Mapping[str, str], proof: impact.Evidence | None, failed: list[Finding]
) -> dict[str, dict[str, object]]:
    """Return the record's `evidence` slot as this run leaves it: as the record holds it, without the evidence layer."""
    if proof is None:
        return world.record.evidence
    stamp = {"commit": world.commit, "dirty": plan.dirty(world.changes, world.intents)}  # those of the run header
    fresh = {req: {**entry, **stamp} for req, entry in impact.entries(world.root, index, levels, proof, failed).items()}
    return impact.merged(world.record.evidence, fresh, index, levels)


def _in_any(intents: Sequence[plan.Intent], path: str) -> bool:
    return any(plan.inside(current, path) for current in intents)


def _code(findings: Sequence[Finding]) -> int:
    return 1 if any(found.level == "error" for found in findings) else 0


def _option(world: _World, text: str | None) -> str | None:
    """Return the record directory that `--intent` names: root-relative first, else relative to the working directory."""
    if text is None:
        return None
    named = posixpath.normpath(text)
    directories = {current.directory for current in world.intents}
    if named in directories:
        return named
    try:
        relative = (Path.cwd() / text).resolve().relative_to(world.root.resolve()).as_posix()
    except (ValueError, RuntimeError):  # RuntimeError: a symlink loop, on Python before 3.13
        return named
    return relative if relative in directories else named


def _plan(world: _World) -> _Result:
    analysis = _analyse(world)
    results, run = analysis.derived, analysis.run
    return _Result(
        reporter.sarif(results, analysis.levels, run),
        reporter.summary(results, analysis.levels, run),
        _code(results),
        "" if world.intents else "no plan\n",
    )


def _task_change(world: _World, analysis: _Analysis, option: str | None) -> _Analysis:
    """Add the task change: out-of-task findings when a current task is known, and the impact of the diff.

    Both read the diff since the change baseline, the commit of the current task's intent's last approved stage
    check, and run only with a current task and a baseline; without either the summary says so once, and with no
    changed line in the evaluated tree the analysis returns as it was. No Git branch is read.
    """
    if not world.intents:  # no plan, so no task to speak of: M1's output stays as it was
        return analysis
    task, reason = plan.current_task(plan.plan_tasks(analysis.index, world.intents), world.intents, option)
    if task is None:
        return _without_task_change(analysis, f"no current task, as {reason}")
    base, missing = _baseline(world, analysis, task)
    if base is None:
        return _without_task_change(analysis, missing)
    tree = {each.path for each in plan.evaluated_tree(world.sources, world.intents)}
    # a file deleted since the baseline is read whole as deleted lines, when the scanner would read its path
    gone = {path for path in git.deleted_files(world.root, base) if plan.scanned(world.intents, path)}
    changed = git.changed_lines(world.root, base, tree | gone, keep_deletions=True)  # a deletion has no region
    if not changed:
        return analysis
    found = plan.out_of_task(analysis.plans, analysis.index, task, changed, analysis.findings)
    change = impact.Change(changed, base)
    selection = impact.select(world.root, analysis.index, change, impact.read_map(world.root, base))
    found += plan.degraded_findings(analysis.plans, analysis.index, selection.degraded, selection.deleted)
    return replace(analysis, findings=[*analysis.findings, *found], run=replace(analysis.run, impact=selection.impact))


def _baseline(world: _World, analysis: _Analysis, task: Item) -> tuple[str | None, str]:
    """Return the change baseline of the task's intent, or None and why there is none."""
    holder = next((each.intent for each in analysis.plans if plan.inside(each.intent, task.path)), None)
    if holder is None:  # the baseline is per intent, and an existing task id is no usage error
        return None, f"the current task {task.id} lies in no intent, so no approved stage check gives a baseline"
    base = plan.change_baseline(holder, world.record.runs)  # the built intent holds the per-unit approvals
    if base is None:
        return None, "no approved stage check is recorded"
    full = git.full_commit(world.root, base)  # the object, never a branch named as a short sha
    if full is None:
        return None, f"the approved stage check's commit {base} is not in the repository"
    return full, ""


def _without_task_change(analysis: _Analysis, reason: str) -> _Analysis:
    note = f"task change: {reason}; no out-of-task check and no impact"
    return replace(analysis, run=replace(analysis.run, notes=(*analysis.run.notes, note)))


def _calibrate(fixture: Path) -> _Result:
    """Run the judge over the fixture's ten requirements, print them beside the maintainer's, and record the result."""
    root = git.repo_root(Path.cwd())  # the record is read before any paid question, so a bad one costs nothing
    record = reporter.read_record(root)
    model = judge.load_model(os.environ.get("EARNEST_JUDGE"), fixture)  # its regions name fixture paths
    maintainer = judge.load_verdicts(fixture / "verdicts.json")
    index = build_index(adapters.scan(fixture, git.work_tree_files(fixture)))
    held = record.judge.get("calibrate")
    cache = judge.Cache(fixture, model, held if isinstance(held, dict) else {})
    try:
        calibration = judge.calibrate(index, structural.traced(index), cache, maintainer)
    except BaseException:  # a failed question, or ^C, still keeps the answers already paid for
        if cache.used:
            # the failure in flight is what the user must see, so a record that cannot be kept now stays as it was
            with contextlib.suppress(reporter.RecordError, OSError):
                _keep_calibration(root, cache.used, None)
        raise
    _keep_calibration(root, cache.used, calibration)
    return _Result(_comparison(calibration), "", 0 if calibration.passed else 1)


def _keep_calibration(root: Path, used: dict[str, object], calibration: judge.Calibration | None) -> None:
    """Keep calibrate's judge answers in the record, reread in case a check run wrote it meanwhile, and set its slot.

    They sit apart from check's `cache`, which a judge run prunes to its own answers; a pass replaces them, so stale
    ones go, and a failed or broken-off run merges, so a rerun reuses what the earlier runs paid for.
    """
    record = reporter.read_record(root)
    held = record.judge.get("calibrate")
    kept = held if (calibration is None or not calibration.passed) and isinstance(held, dict) else {}
    record.judge = {**record.judge, "calibrate": {**kept, **used}}
    if calibration is not None:
        record.calibration = judge.slot(calibration)
    reporter.write_record(root, record)


def _comparison(calibration: judge.Calibration) -> str:
    """Return calibrate's stdout: a header, a line per requirement with both answers under a differing one, the verdict."""
    width = max(len(row.subject) for row in calibration.rows)
    lines = [f"calibration of {calibration.model} with the prompt {judge.PROMPT_HASH}"]
    for row in calibration.rows:
        results = [
            f"{who} {'/'.join(verdicts[kind].result for kind in judge.QUESTIONS)}" for who, verdicts in _sides(row)
        ]
        lines.append(f"{row.subject:<{width}}  {'  '.join(results)}  {'match' if row.matched else 'differs'}")
        for kind in judge.QUESTIONS:
            if row.judge[kind].result != row.maintainer[kind].result:
                for who, verdicts in _sides(row):
                    v = verdicts[kind]
                    lines.append(
                        f"    {kind} {who}: {v.result} at {judge.escaped(v.path)}:{v.line}: {judge.escaped(v.reasoning)}"
                    )
    lines += [f"matches: {calibration.matches}/{judge.TOTAL}", "pass" if calibration.passed else "fail"]
    return "\n".join(lines) + "\n"


def _sides(row: judge.Row) -> tuple[tuple[str, Mapping[str, judge.Verdict]], ...]:
    return (("judge", row.judge), ("maintainer", row.maintainer))


def _check(world: _World, args: argparse.Namespace) -> _Result:
    model = judge.load_model(os.environ.get("EARNEST_JUDGE"), world.root) if args.judge or args.evidence else None
    if args.stage is None:
        if args.intent is not None:
            plan.find_intent(world.intents, _option(world, args.intent))
        analysis = _task_change(world, _analyse(world, model, evidence=args.evidence), args.task)
        findings, run = analysis.findings, analysis.run
        if analysis.cache is not None:
            world.record.judge, world.record.evidence = analysis.cache, analysis.entries
            _write_check(world)
        return _Result(
            reporter.sarif(findings, analysis.levels, run),
            reporter.summary(findings, analysis.levels, run),
            _code(findings),
        )
    chosen = plan.find_intent(world.intents, _option(world, args.intent))
    return _stage(
        world, _task_change(world, _analyse(world, model, evidence=args.evidence), args.task), chosen, args.stage
    )


def _write_check(world: _World) -> None:
    """Write check's record with calibrate's slot and answers as the record now holds them.

    Calibrate owns those two, so a calibrate run that finished while this check ran keeps what it paid for.
    """
    fresh = reporter.read_record(world.root)
    world.record.calibration = fresh.calibration
    judged = {key: value for key, value in world.record.judge.items() if key != "calibrate"}
    held = fresh.judge.get("calibrate")
    world.record.judge = judged if held is None else {**judged, "calibrate": held}
    reporter.write_record(world.root, world.record)


def _stage(world: _World, analysis: _Analysis, chosen: plan.Intent, text: str) -> _Result:
    current = next(each for each in analysis.plans if each.intent.directory == chosen.directory)
    stage = plan.select_stage(current, text)
    found = plan.scoped(analysis.findings, current, stage)
    state = analysis.statuses[chosen.directory][stage]
    tree = plan.evaluated_tree(world.sources, world.intents)
    digest = plan.assessment_hash(plan.assessment_document(current, stage, tree, found, analysis.run))
    items = next(each for each in current.stages if each.stage == stage).items
    key = reporter.run_key(chosen.directory, stage)
    reasons = {"errors": state.errors, "openTasks": state.open_tasks, "approval": state.approval}
    run = replace(
        analysis.run,
        timestamp=reporter.utc_timestamp(),
        assessment={"stage": key, "hash": digest, "status": state.status, "reasons": reasons},
        record_absent=False,
        unheld=sum(1 for item in items if str(item.id) not in world.record.bodies),
    )
    # ponytail: the record is read and rewritten whole, so two stage checks of different stages racing are
    # last-writer-wins (the same stage twice is safe); take an flock on `.earnest/lock` if sensor fires run in parallel
    world.record.bodies = plan.next_bodies(world.record.bodies, current, stage)
    world.record.runs[key] = plan.header(current, stage, state, run, digest)
    if analysis.cache is not None:
        world.record.judge, world.record.evidence = analysis.cache, analysis.entries
    _write_check(world)  # first, so `.earnest/` exists with its `.gitignore`
    # the map is taken at commit A, so a tree that is not A's bytes gives none; an earlier map stays as it was
    reason = "the work tree is dirty" if run.dirty else impact.take_map(world.root, world.commit)
    if reason is None:
        world.record.coverage = {"commit": world.commit}
        _write_check(world)
    else:
        run = replace(run, notes=(*run.notes, f"coverage map: not taken, {reason}"))
    return _Result(
        reporter.sarif(found, analysis.levels, run), reporter.summary(found, analysis.levels, run), _code(found)
    )
