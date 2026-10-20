"""Command surface: `earnest check` and `earnest plan`, which wire the scanner, the index, the checks and the plan."""

import argparse
import os
import posixpath
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from earnest import adapters, git, impact, plan, reporter, structural
from earnest.index import Index, Source, build_index
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
    or newer, an intent or stage cannot be chosen, or the reader of the log or the summary goes away.
    """
    parser = argparse.ArgumentParser(prog="earnest", description="Requirements traceability for LLM-written code.")
    # main never dispatches on the bare command, so a bare `earnest` must stop here rather than run the check
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="trace the repository; SARIF 2.1.0 on stdout, a summary on stderr")
    check.add_argument("--stage", help="check one stage: its id, or its slug when that is unambiguous")
    check.add_argument("--intent", help="the record directory of the intent, when there are several")
    check.add_argument(
        "--task", help="the current task, such as task~add-limiter~1; else a task/<name>-… branch names it"
    )
    commands.add_parser("plan", help="print the route, each stage's status and approval, and the frontier")
    args = parser.parse_args(argv)
    try:
        world = _read()
        result = _plan(world) if args.command == "plan" else _check(world, args)
    except (git.GitError, OSError, reporter.RecordError, plan.PlanError) as error:
        sys.stderr.write(f"earnest: {error}\n")
        return 2
    try:
        sys.stdout.write(result.log)
        sys.stdout.flush()
        sys.stderr.write(result.notes + result.summary)
        sys.stderr.flush()
    except BrokenPipeError:  # a reader went away, as `head` does: send what is left to devnull, so exit stays quiet
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.dup2(devnull, sys.stderr.fileno())
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


def _analyse(world: _World) -> _Analysis:
    index = build_index(world.sources)
    produces = plan.produces(world.intents)
    levels = structural.traced(index, produces)
    plans = [plan.build(current, index) for current in world.intents]
    built = [each.intent for each in plans]  # each with its per-unit stages and the approvals that count for them
    frozen = plan.frozen_bodies(world.record.bodies, built)
    own = [found for each in plans for found in (*plan.plan_findings(each, index), *plan.approval_findings(each))]
    derived = plan.place(plans, index, own)
    findings = [*plan.place(plans, index, structural.check(index, produces=produces, frozen=frozen)), *derived]
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
    )
    return _Analysis(index, levels, plans, findings, derived, statuses, run)


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

    Both read the diff since the task's base commit, and run only with `--task` or on a `task/…` branch; anywhere
    else, or with no changed line in the evaluated tree, the analysis returns as it was.
    """
    branch = git.current_branch(world.root)
    if option is None and not plan.on_task_branch(branch):
        return analysis
    task = plan.current_task(plan.plan_tasks(analysis.index, world.intents), option, branch)
    base = git.merge_base(world.root, git.default_branch(world.root))
    tree = {each.path for each in plan.evaluated_tree(world.sources, world.intents)}
    changed = git.changed_lines(world.root, base, tree, keep_deletions=True)  # a deletion has no region of its own
    if not changed:
        return analysis
    found = [] if task is None else plan.out_of_task(analysis.plans, analysis.index, task, changed, analysis.findings)
    selection = _impact(world, analysis.index, impact.Change(changed, base, changed), tree)
    found += plan.degraded_findings(analysis.plans, analysis.index, selection.degraded, selection.deleted)
    return replace(analysis, findings=[*analysis.findings, *found], run=replace(analysis.run, impact=selection.impact))


def _impact(world: _World, index: Index, change: impact.Change, tree: set[str]) -> impact.Selection:
    """Select the impact of a change against the coverage map the record names, remapped since its commit."""
    commit = world.record.coverage.get("commit")
    if not impact.is_commit(commit) or not git.has_commit(world.root, str(commit)):
        return impact.select(world.root, index, change, None)
    taken = str(commit)
    coverage = impact.read_map(world.root, taken)
    if coverage is not None and taken != change.base:
        since_map = git.changed_lines(world.root, taken, tree, keep_deletions=True)
        change = replace(change, since_map=since_map, map_at_base=False)
    return impact.select(world.root, index, change, coverage)


def _check(world: _World, args: argparse.Namespace) -> _Result:
    if args.stage is None:
        if args.intent is not None:
            plan.find_intent(world.intents, _option(world, args.intent))
        analysis = _task_change(world, _analyse(world), args.task)
        findings, run = analysis.findings, analysis.run
        return _Result(
            reporter.sarif(findings, analysis.levels, run),
            reporter.summary(findings, analysis.levels, run),
            _code(findings),
        )
    chosen = plan.find_intent(world.intents, _option(world, args.intent))
    return _stage(world, _task_change(world, _analyse(world), args.task), chosen, args.stage)


def _stage(world: _World, analysis: _Analysis, chosen: plan.Intent, text: str) -> _Result:
    current = next(each for each in analysis.plans if each.intent.directory == chosen.directory)
    stage = plan.select_stage(current, text)
    found = plan.scoped(analysis.findings, current, stage)
    state = analysis.statuses[chosen.directory][stage]
    tree = plan.evaluated_tree(world.sources, world.intents)
    digest = plan.assessment_hash(plan.assessment_document(current, stage, tree, found))
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
    reporter.write_record(world.root, world.record)  # first, so `.earnest/` exists with its `.gitignore`
    # the map is taken at commit A, so a tree that is not A's bytes gives none; an earlier map stays as it was
    reason = "the work tree is dirty" if run.dirty else impact.take_map(world.root, world.commit)
    if reason is None:
        world.record.coverage = {"commit": world.commit}
        reporter.write_record(world.root, world.record)
    else:
        run = replace(run, notes=(*run.notes, f"coverage map: not taken, {reason}"))
    return _Result(
        reporter.sarif(found, analysis.levels, run), reporter.summary(found, analysis.levels, run), _code(found)
    )
