"""Plan and stage engine: the state file's Stage Progress and the audit shards, read from the work tree."""

import posixpath
import re
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from earnest import adapters, structural
from earnest.index import ID_ENTRY, Index, Item, Source, split_lines
from earnest.index import digest as digest_of
from earnest.reporter import Finding, Position, Run, RunHeader, canonical, run_key, uri


AUDIT = "audit"
_SCOPE = re.compile(r"^- \*\*Scope\*\*:[ \t]*(.*)$", re.MULTILINE)  # no lazy group before `[ \t]*$`: that is quadratic
_ROW = re.compile(r"- \[([ \-?RxS])\] (\S+) \u2014 (EXECUTE|SKIP)(?:[:\s][ \t]*(.*))?")
_FIELD = re.compile(r"\*\*([^*:]+)\*\*:[ \t]*(.*)")


@dataclass(frozen=True)
class Row:
    """One Stage Progress row: its phase and slug, the checkbox mark as written, EXECUTE or SKIP, and its line."""

    phase: str
    slug: str
    mark: str
    action: str
    reason: str
    line: int

    @property
    def stage(self) -> str:
        """Return the stage's id: its phase and slug."""
        return f"{self.phase}/{self.slug}"


@dataclass(frozen=True)
class State:
    """What Earnest reads of an intent's `aidlc-state.md`: its scope, for display, and its Stage Progress rows.

    The lines it cannot read as rows are kept, so a route that shrinks because of them is never silent.
    """

    scope: str
    rows: tuple[Row, ...]
    unread: tuple[int, ...] = ()  # lines under Stage Progress that start `- [` and are no row Earnest can read
    heading: int = 0  # the line of the `## Stage Progress` heading, 0 when the file has none


@dataclass(frozen=True, order=True)
class Event:
    """One audit block. Events order by `key`: timestamp, then shard file name, then position in the shard."""

    # ponytail: timestamps compare as strings, which is right for upstream's fixed-width `YYYY-MM-DDTHH:MM:SSZ`; parse
    # them if a fractional second or an offset ever appears
    key: tuple[str, str, int]
    name: str = field(compare=False)
    fields: dict[str, str] = field(compare=False)


@dataclass(frozen=True)
class Record:
    """An intent's record directory: its state file's path and content, and every audit event, in order."""

    directory: str
    state_path: str
    state: State
    events: tuple[Event, ...]


def _phase(heading: str) -> str:
    """Return the phase a `###` heading names: lower case, without a trailing ` PHASE`."""
    name = heading.strip()
    head = name[:-5]  # not a regex: `\s+PHASE$` backtracks quadratically over a long run of spaces
    if name[-5:].upper() == "PHASE" and head[-1:].isspace():
        name = head.rstrip()
    return name.lower()


def parse_state(text: str) -> State:
    """Read the scope and the Stage Progress rows of a state file; the marks are returned as written, never trusted."""
    normalized = text.replace("\r\n", "\n")
    scope = _SCOPE.search(normalized)
    rows: list[Row] = []
    unread: list[int] = []
    heading = 0
    in_progress = False
    phase = ""
    for line in split_lines(normalized):
        stripped = line.text.rstrip()
        if stripped.startswith("## "):
            in_progress = stripped[3:].strip() == "Stage Progress"
            heading = heading or (line.number if in_progress else 0)
            phase = ""
        elif in_progress and stripped.startswith("### "):
            phase = _phase(stripped[4:])
        elif in_progress and stripped.startswith("- ["):
            if phase and (row := _ROW.fullmatch(stripped)):
                rows.append(Row(phase, row[2], row[1], row[3], row[4] or "", line.number))
            else:
                unread.append(line.number)
    return State(scope.group(1).rstrip(" \t") if scope else "", tuple(rows), tuple(unread), heading)


def parse_audit(text: str, shard: str) -> list[Event]:
    """Read the events of one audit shard: blocks that end at a line `---`, with a Timestamp and an Event field."""
    events: list[Event] = []
    block: list[str] = []
    position = 0
    for line in [*text.replace("\r\n", "\n").split("\n"), "---"]:  # the last block counts, closed or not
        if line != "---":
            block.append(line)
            continue
        fields = _fields(block)
        if "Timestamp" in fields and "Event" in fields:
            events.append(Event((fields["Timestamp"], shard, position), fields["Event"], fields))
        block = []
        position += 1
    return events


def load(root: Path, files: Sequence[str]) -> list[Record]:
    """Read every intent among the listed files: one record per `aidlc-state.md`, sorted by its directory.

    Raises:
        OSError: a listed file that exists cannot be read.
    """
    records: list[Record] = []
    for path in files:
        state = _read(root, path) if posixpath.basename(path) == adapters.STATE else None
        if state is not None:
            directory = posixpath.dirname(path)
            events = [event for shard in _shards(files, directory) for event in _events(root, shard)]
            records.append(Record(directory, path, parse_state(state), tuple(sorted(events))))
    return sorted(records, key=lambda record: record.directory)


def _fields(lines: Sequence[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in lines:
        if match := _FIELD.fullmatch(line.rstrip()):
            found.setdefault(match[1], match[2].strip())  # the first of each name wins
    return found


def _shards(files: Sequence[str], directory: str) -> list[str]:
    audit = posixpath.join(directory, AUDIT)
    return [path for path in files if posixpath.dirname(path) == audit and path.endswith(".md")]


def _events(root: Path, shard: str) -> list[Event]:
    text = _read(root, shard)
    return [] if text is None else parse_audit(text, posixpath.basename(shard))


def _read(root: Path, path: str) -> str | None:
    """Return a listed file's text, or None when it is gone from the work tree or is a symlink, as the scanner skips."""
    file = root / path
    if file.is_symlink() or not file.is_file():
        return None
    return file.read_bytes().decode("utf-8-sig", errors="replace")


_INITIALIZATION = "initialization"
_TEAM_FIELDS = ("Unit", "Gate Scope", "Gate Stages")
_NO_BOUNDARY = ("", "", -1)  # sorts before every key
_UNSUPPORTED = "units-generation"


@dataclass(frozen=True)
class Approval:
    """A stage's approval: the ids and revisions its row names (None without an `Items` field), who gave it, its hash."""

    stage: str
    items: tuple[str, ...] | None
    by: str | None
    digest: str | None


@dataclass(frozen=True)
class Intent:
    """An intent as its record says: its route, the approvals that count, and the ids that approvals froze."""

    directory: str
    state_path: str
    rows: tuple[Row, ...]
    route: tuple[str, ...]
    approvals: Mapping[str, Approval]
    named_items: frozenset[str]
    mismatches: tuple[Row, ...]
    unread: tuple[int, ...] = ()
    heading: int = 0

    @property
    def unsupported(self) -> bool:
        """Return whether the route holds `units-generation`, so per-unit stages, which M2 does not report."""
        return any(stage.partition("/")[2] == _UNSUPPORTED for stage in self.route)


@dataclass(frozen=True)
class StageState:
    """One stage of a plan: its approval, whether that approval is current, and the items its artifacts hold."""

    stage: str
    approval: Approval | None
    state: Literal["current", "outdated", "none"]
    items: tuple[Item, ...]


@dataclass(frozen=True)
class Plan:
    """An intent's stages in route order, and the frontier: the first stage without a current approval."""

    intent: Intent
    stages: tuple[StageState, ...]
    frontier: str | None


def jump_span(jump: Event, rows: Sequence[Row]) -> frozenset[str]:
    """Return the slugs whose earlier audit rows a jump voids.

    A BACKWARD jump resets its target and every later row marked EXECUTE, skipped marks included; a REDO jump resets
    its target; a FORWARD jump, or a target that names no row, resets nothing. Upstream voids no row: this is the rule
    by which Earnest reads an approval or a skip as part of the attempt it follows.
    """
    slugs = [row.slug for row in rows]
    target = jump.fields.get("Target", "")
    direction = jump.fields.get("Direction", "").upper()
    if target not in slugs or direction not in {"BACKWARD", "REDO"}:
        return frozenset()
    later = rows[slugs.index(target) + 1 :] if direction == "BACKWARD" else []
    return frozenset({target, *(row.slug for row in later if row.action == "EXECUTE")})


def counting(events: Sequence[Event], rows: Sequence[Row]) -> list[Event]:
    """Return the events that count: those after the latest `WORKFLOW_STARTED` and outside every jump's reset span."""
    boundary = max((event.key for event in events if event.name == "WORKFLOW_STARTED"), default=_NO_BOUNDARY)
    jumps = [(event.key, jump_span(event, rows)) for event in events if event.name == "STAGE_JUMPED"]
    return [
        event
        for event in events
        if event.key > boundary
        and not any(event.key <= key and event.fields.get("Stage") in span for key, span in jumps)
    ]


def intent(record: Record) -> Intent:
    """Build an intent from its record: the route, the approvals that count, and the ids they froze."""
    rows = record.state.rows
    events = counting(record.events, rows)
    skipped = {event.fields.get("Stage") for event in events if event.name == "STAGE_SKIPPED"}
    route = tuple(
        row.stage
        for row in rows
        if row.action == "EXECUTE" and row.phase != _INITIALIZATION and row.slug not in skipped
    )
    mismatches = tuple(row for row in rows if row.action == "EXECUTE" and row.mark == "S" and row.slug not in skipped)
    gates = [
        event
        for event in events
        if event.name in {"GATE_APPROVED", "GATE_REJECTED"} and not any(name in event.fields for name in _TEAM_FIELDS)
    ]
    approvals = {stage: found for stage in route if (found := _approval(stage, gates)) is not None}
    state = record.state
    return Intent(
        record.directory,
        record.state_path,
        rows,
        route,
        approvals,
        _named(gates),
        mismatches,
        state.unread,
        state.heading,
    )


def route_findings(intent: Intent) -> list[Finding]:
    """Return the route-mismatch findings: unrecorded skips, and Stage Progress that Earnest cannot read.

    A stage marked skipped that the audit log does not record as skipped is one. So is any Stage Progress row, or the
    section itself, that Earnest cannot read, which would shrink the route silently.
    """
    path = intent.state_path
    found = [
        Finding(
            path,
            row.line,
            "earnest/route-mismatch",
            row.slug,
            f"`{row.slug}` is marked skipped and EXECUTE, and the audit log holds no counting `STAGE_SKIPPED` row for"
            " it: record the skip in the audit log, or restore the stage's mark",
        )
        for row in intent.mismatches
    ]
    for line in intent.unread:
        message = (
            f"Earnest cannot read line {line} of the state file as a Stage Progress row: write it as"
            " `- [x] slug \u2014 EXECUTE: reason` under a `### NAME PHASE` heading"
        )
        found.append(Finding(path, line, "earnest/route-mismatch", "Stage Progress", message))
    if not intent.rows and not intent.unread:
        line = intent.heading or 1
        message = (
            f"Earnest cannot read a Stage Progress section at line {line} of the state file, so the route would be"
            " empty: restore its `## Stage Progress` section, with `### NAME PHASE` headings and one row per stage"
        )
        found.append(Finding(path, line, "earnest/route-mismatch", "Stage Progress", message))
    return found


def build(intent: Intent, index: Index) -> Plan:
    """Build the plan of an intent over an index: each stage's items and approval, and the frontier."""
    stages: list[StageState] = []
    for stage in intent.route:
        prefix = posixpath.join(intent.directory, stage) + "/"
        items = tuple(item for item in index.defined.values() if item.path.startswith(prefix))
        approval = intent.approvals.get(stage)
        current = {str(item.id) for item in items}
        if approval is None:
            state: Literal["current", "outdated", "none"] = "none"
        elif approval.items is None or set(approval.items) == current:
            state = "current"
        else:
            state = "outdated"
        stages.append(StageState(stage, approval, state, items))
    frontier = next((state.stage for state in stages if state.state != "current"), None)
    return Plan(intent, tuple(stages), frontier)


def _items(event: Event) -> tuple[bool, tuple[str, ...] | None]:
    """Return whether the event's `Items` field parses, and the ids it names: None when the field is absent."""
    text = event.fields.get("Items")
    if text is None:
        return True, None
    tokens = tuple(token for token in re.split(r"[\s,]+", text) if token)
    return all(ID_ENTRY.fullmatch(token) for token in tokens), tokens


def _approval(stage: str, gates: Sequence[Event]) -> Approval | None:
    mine = [event for event in gates if event.fields.get("Stage") == stage.partition("/")[2]]
    approved = [
        (event, items) for event in mine if event.name == "GATE_APPROVED" for ok, items in (_items(event),) if ok
    ]
    if not approved:
        return None
    event, items = max(approved, key=lambda pair: pair[0].key)
    if any(other.name == "GATE_REJECTED" and other.key > event.key for other in mine):
        return None
    by = event.fields.get("Approved By")
    return Approval(stage, items, by if by in {"human", "automatic"} else None, event.fields.get("Assessment Hash"))


def _named(gates: Sequence[Event]) -> frozenset[str]:
    """Return the ids that counting approvals froze: those of every row that no later rejection of its stage voids."""
    named: set[str] = set()
    for event in gates:
        ok, items = _items(event)
        voided = any(
            other.name == "GATE_REJECTED"
            and other.key > event.key
            and other.fields.get("Stage") == event.fields.get("Stage")
            for other in gates
        )
        if event.name == "GATE_APPROVED" and ok and items and not voided:
            named.update(items)
    return frozenset(named)


# What the artifacts of each stage slug hold, from the mapping table of Adopting AI-DLC. Code Generation holds the
# code and test tags too, so a route that runs it keeps the default needs of `req`.
PRODUCES: dict[str, frozenset[str]] = {
    "intent-capture": frozenset({"tenet", "goal"}),
    "scope-definition": frozenset({"feat"}),
    "approval-and-handoff": frozenset({"dsn"}),
    "requirements-analysis": frozenset({"req"}),
    "domain-design": frozenset({"dsn"}),
    "units-generation": frozenset({"unit"}),
    "functional-design": frozenset({"dsn"}),
    "nfr-requirements": frozenset({"req"}),
    "nfr-design": frozenset({"dsn"}),
    "code-generation": frozenset({"task", "impl", "utest", "itest", "stest"}),
}
_CODE_GENERATION = "code-generation"
_BUILD_AND_TEST = "build-and-test"
_SUBJECT = re.compile(r"([a-z]+)~([a-z0-9-]+)~[0-9]+")
_Located = tuple[Plan, str]


@dataclass(frozen=True)
class StageStatus:
    """A stage's computed status and the reasons for it: the errors against it, its open tasks, its approval."""

    status: Literal["done", "not done"]
    errors: int
    open_tasks: int
    approval: str


def produces(intents: Sequence[Intent]) -> frozenset[str] | None:
    """Return the item types that some route stage of a supported intent produces, or None when none is supported.

    None is the route rule's off switch: `structural.check` then keeps every need and link, as it does with no plan.
    """
    supported = [current for current in intents if not current.unsupported]
    types = frozenset().union(
        *(PRODUCES.get(stage.partition("/")[2], frozenset()) for current in supported for stage in current.route)
    )
    return types or None  # no supported route, or one that produces nothing: keep every need and link


def stage_of(intent: Intent, path: str) -> str | None:
    """Return the route stage whose path holds the file at path, or None."""
    return next(
        (stage for stage in intent.route if path.startswith(posixpath.join(intent.directory, stage) + "/")), None
    )


def in_tree(intents: Sequence[Intent], path: str) -> bool:
    """Return whether the file at path is in the evaluated tree: outside every record directory, or in a route stage.

    The state file, the audit shards, `.aidlc-engine/` and the files of a stage off the route lie in a record
    directory and in no route stage, so they are out.
    """
    holders = [current for current in intents if inside(current, path)]
    return not holders or any(stage_of(current, path) is not None for current in holders)


def task_done(task: Item, index: Index, levels: Mapping[str, str]) -> bool:
    """Return whether a task is done: each thing it delivers resolves, a `req` is evidenced and a `dsn` has an `impl`."""
    covers = structural.resolved_covers(index)
    for link in index.links:
        if link.key != "Delivers" or link.owner != task.id:
            continue
        resolution = index.resolutions[link.target]
        delivered = resolution.item
        if resolution.status != "resolved" or delivered is None:
            return False
        if delivered.id.type == "req" and levels.get(str(delivered.id)) != "evidenced":
            return False
        if delivered.id.type == "dsn" and ("impl", delivered) not in covers:
            return False
    return True


def statuses(
    plan: Plan, index: Index, findings: Sequence[Finding], levels: Mapping[str, str]
) -> dict[str, StageStatus]:
    """Return each stage's computed status from the graph: no error against it, its tasks done, a current approval."""
    stest = len({str(link.target) for link in index.links if link.type == "stest"})
    result: dict[str, StageStatus] = {}
    for state in plan.stages:
        # ponytail: an error placed ahead of the frontier is a note and not counted, so an approved stage after the
        # frontier can read done despite one; count `ahead` errors here if a gate ever depends on that stage.
        errors = sum(
            1
            for found in findings
            if found.intent == plan.intent.directory and found.stage == state.stage and found.level == "error"
        )
        open_tasks = sum(1 for item in state.items if item.id.type == "task" and not task_done(item, index, levels))
        if state.stage.partition("/")[2] == _BUILD_AND_TEST:
            open_tasks += stest  # an `stest` passes only at evidence, which M2 has none of
        done = errors == 0 and open_tasks == 0 and state.state == "current"
        result[state.stage] = StageStatus("done" if done else "not done", errors, open_tasks, state.state)
    return result


def plan_findings(plan: Plan, index: Index) -> list[Finding]:
    """Return the findings the plan itself raises: `unplanned`, `cycle` and `route-mismatch`."""
    return [*_unplanned(plan, index), *_cycle_findings(plan, index), *route_findings(plan.intent)]


def approval_findings(plan: Plan) -> list[Finding]:
    """Return a note for each item that a stale approval names at an older revision, located at the item's id line.

    They stay apart from `plan_findings` so that the assessment document can leave them out: a fresh approval removes
    them, and recording an approval must not change the hash.
    """
    found: list[Finding] = []
    for state in plan.stages:
        if state.state != "outdated" or state.approval is None or state.approval.items is None:
            continue
        named = {tuple(entry.split("~")[:2]): entry for entry in state.approval.items}
        for item in state.items:
            old = named.get(item.id.key)
            if old is not None and old != str(item.id):
                message = (
                    f"the approval of `{state.stage}` names `{old}`, and the item is at revision {item.id.revision}:"
                    f" check the change, then approve `{state.stage}` again"
                )
                found.append(
                    Finding(
                        item.path,
                        item.line,
                        "earnest/outdated",
                        str(item.id),
                        message,
                        stage=state.stage,
                        intent=plan.intent.directory,
                        note=True,
                    )
                )
    return found


def place(plans: Sequence[Plan], index: Index, findings: Sequence[Finding]) -> list[Finding]:
    """Give each finding the stage it counts against, its intent and its position by that intent's frontier.

    With no plan the findings return unchanged. A finding that reaches no stage keeps position current.
    """
    if not plans:
        return list(findings)
    delivering = _delivering(plans, index)
    stest_lines = {(link.path, link.line) for link in index.links if link.type == "stest"}
    placed: list[Finding] = []
    for finding in findings:
        found = _locate(finding, plans, delivering, stest_lines)
        if found is None:
            placed.append(finding)
            continue
        current, stage = found
        placed.append(
            replace(finding, stage=stage, intent=current.intent.directory, position=_position(current, stage))
        )
    return placed


def properties(
    plans: Sequence[Plan],
    statuses_by_intent: Mapping[str, Mapping[str, StageStatus]],
    index: Index,
    levels: Mapping[str, str],
) -> dict[str, object]:
    """Return `properties.plan`: one entry per supported plan, in directory order, with its stages, frontier and tasks."""
    entries: list[dict[str, object]] = []
    for current in sorted(plans, key=lambda each: each.intent.directory):
        if current.intent.unsupported:
            continue
        status = statuses_by_intent[current.intent.directory]
        tasks = sorted(
            (
                {"id": str(item.id), "status": "done" if task_done(item, index, levels) else "not done"}
                for state in current.stages
                for item in state.items
                if item.id.type == "task"
            ),
            key=lambda task: (task["id"], task["status"]),
        )
        stages = [
            {
                "stage": state.stage,
                "status": status[state.stage].status,
                "approval": state.state,
                "approvedBy": state.approval.by if state.state == "current" and state.approval else None,
            }
            for state in current.stages
        ]
        entries.append(
            {
                "intent": current.intent.directory,
                "stages": stages,
                "frontier": current.frontier,
                "tasks": tasks,
                "units": [],
            }
        )
    return {"intents": entries}


def inside(intent: Intent, path: str) -> bool:
    """Return whether the file at path lies in the intent's record directory."""
    return intent.directory == "" or path.startswith(intent.directory + "/")


def _unplanned(plan: Plan, index: Index) -> list[Finding]:
    stage = next((each for each in plan.intent.route if each.partition("/")[2] == _CODE_GENERATION), None)
    if stage is None:
        return []
    delivered = {
        link.target.key
        for link in index.links
        if link.key == "Delivers" and link.owner is not None and link.owner.type == "task"
    }
    return [
        Finding(
            item.path,
            item.line,
            "earnest/unplanned",
            str(item.id),
            f"`{item.id}` is delivered by no task: add a `task` that delivers it, with a `Delivers:` line",
            stage=stage,
            intent=plan.intent.directory,
        )
        for item in index.defined.values()
        if item.id.type == "req" and inside(plan.intent, item.path) and item.id.key not in delivered
    ]


def _depends(plan: Plan, index: Index) -> dict[str, list[str]]:
    edges: dict[str, list[str]] = {}
    for link in index.links:
        owner = index.defined.get(link.owner.key) if link.owner is not None else None
        target = index.defined.get(link.target.key)
        if link.key == "Depends" and owner is not None and target is not None and inside(plan.intent, owner.path):
            edges.setdefault(str(owner.id), []).append(str(target.id))
    return edges


def _cycle_through(edges: Mapping[str, Sequence[str]], start: str) -> list[str] | None:
    """Return the shortest path from start back to itself, taking the lowest id first, or None.

    ponytail: one cycle per start, the shortest, so a cycle that is never the shortest through any of its tasks is not
    listed; it shows once the shorter ones are fixed. Enumerate elementary cycles if that ever matters.
    """
    queue = deque([[start]])
    visited = {start}
    while queue:
        path = queue.popleft()
        for follower in sorted(edges.get(path[-1], ())):
            if follower == start:
                return [*path, start]
            if follower not in visited:
                visited.add(follower)
                queue.append([*path, follower])
    return None


def _cycle_findings(plan: Plan, index: Index) -> list[Finding]:
    edges = _depends(plan, index)
    by_id = {str(item.id): item for item in index.defined.values()}
    found: list[Finding] = []
    seen: set[tuple[str, ...]] = set()
    for start in sorted(edges):
        path = _cycle_through(edges, start)
        if path is None:
            continue
        nodes = path[:-1]
        turn = nodes.index(min(nodes))  # a cycle starts at its first id in id order, however it was found
        cycle = tuple(nodes[turn:] + nodes[:turn])
        if cycle in seen:
            continue
        seen.add(cycle)
        item = by_id[cycle[0]]
        stage = stage_of(plan.intent, item.path)
        loop = " -> ".join([*cycle, cycle[0]])
        message = f"the plan's dependencies form a cycle, {loop}: remove a `Depends:` line from it"
        directory = plan.intent.directory if stage else None
        found.append(Finding(item.path, item.line, "earnest/cycle", cycle[0], message, stage=stage, intent=directory))
    return found


def _owner(plans: Sequence[Plan], path: str) -> Plan | None:
    holders = [current for current in plans if inside(current.intent, path)]
    return max(holders, key=lambda current: len(current.intent.directory), default=None)


def _delivering(plans: Sequence[Plan], index: Index) -> dict[tuple[str, str], _Located]:
    """Map each delivered item's type and name to the plan and stage of the task that delivers it."""
    found: dict[tuple[str, str], _Located] = {}
    for link in index.links:
        if link.key != "Delivers" or link.owner is None or link.owner.type != "task":
            continue
        owner = _owner(plans, link.path)
        stage = stage_of(owner.intent, link.path) if owner is not None else None
        if owner is not None and stage is not None:
            found.setdefault(link.target.key, (owner, stage))
    return found


def _locate(
    finding: Finding,
    plans: Sequence[Plan],
    delivering: Mapping[tuple[str, str], _Located],
    stest_lines: set[tuple[str, int]],
) -> _Located | None:
    if finding.stage is not None:
        preset = next((current for current in plans if current.intent.directory == finding.intent), None)
        return None if preset is None else (preset, finding.stage)
    owner = _owner(plans, finding.path)
    return (
        _gap_stage(finding, owner)
        or (_stest_stage(plans) if (finding.path, finding.line) in stest_lines else None)
        or _file_stage(finding, owner)
        or _delivered_stage(finding, delivering)
    )


def _gap_stage(finding: Finding, owner: Plan | None) -> _Located | None:
    if finding.rule != "earnest/gap" or owner is None:
        return None
    wanted = (stage for stage in owner.intent.route if finding.child in PRODUCES.get(stage.partition("/")[2], ()))
    stage = next(wanted, None)
    return None if stage is None else (owner, stage)


def _stest_stage(plans: Sequence[Plan]) -> _Located | None:
    return next(
        (
            (current, stage)
            for current in plans
            for stage in current.intent.route
            if stage.endswith("/" + _BUILD_AND_TEST)
        ),
        None,
    )


def _file_stage(finding: Finding, owner: Plan | None) -> _Located | None:
    stage = None if owner is None else stage_of(owner.intent, finding.path)
    return None if owner is None or stage is None else (owner, stage)


def _delivered_stage(finding: Finding, delivering: Mapping[tuple[str, str], _Located]) -> _Located | None:
    named = _SUBJECT.fullmatch(finding.subject)
    return delivering.get((named[1], named[2])) if named else None


def _position(plan: Plan, stage: str) -> Position:
    if plan.frontier is None:
        return "behind"
    order = [state.stage for state in plan.stages]
    here, front = order.index(stage), order.index(plan.frontier)
    return "behind" if here < front else "current" if here == front else "ahead"


def evaluated_tree(sources: Sequence[Source], intents: Sequence[Intent]) -> list[Source]:
    """Return the sources in the evaluated tree: outside every record directory, or in a route stage."""
    return [each for each in sources if in_tree(intents, each.path)]


def tree_digest(tree: Sequence[Source]) -> str:
    """Return the digest of the tree: the canonical JSON of each file's uri and digest, sorted by uri."""
    return digest_of(canonical(sorted([uri(each.path), each.digest] for each in tree)).encode("ascii"))


def scoped(findings: Sequence[Finding], plan: Plan, stage: str) -> list[Finding]:
    """Return what a `--stage` run reports: the stage's findings, and the findings that reach no stage."""
    return [
        found
        for found in findings
        if found.stage is None or (found.intent == plan.intent.directory and found.stage == stage)
    ]


def assessment_document(
    plan: Plan, stage: str, tree: Sequence[Source], findings: Sequence[Finding]
) -> dict[str, object]:
    """Return the assessment document that the assessment hash covers, version 1.

    It holds the stage's items with their body hashes, the findings of the run that lie in the evaluated tree, as
    their rule, uri, line, subject and message, and the tree's digest. It holds no position, commit, timestamp, route
    or approval, and no approval note, which a fresh approval removes.
    """
    state = next(each for each in plan.stages if each.stage == stage)
    inside = {each.path for each in tree}
    counted = [found for found in scoped(findings, plan, stage) if not found.note and found.path in inside]
    return {
        "v": 1,
        "stage": run_key(plan.intent.directory, stage),
        "layers": ["trace"],
        "model": None,
        "prompt": None,
        "items": sorted([str(item.id), item.body_hash] for item in state.items),
        "findings": sorted(
            [found.rule, uri(found.path), found.line, found.subject, found.message] for found in counted
        ),
        "tree": tree_digest(tree),
    }


def assessment_hash(document: Mapping[str, object]) -> str:
    """Return the assessment hash: the digest of the document's compact canonical JSON."""
    return digest_of(canonical(document).encode("ascii"))


def next_bodies(held: Mapping[str, str], plan: Plan, stage: str) -> dict[str, str]:
    """Return the body hashes the record holds after a stage check.

    An item's hash is recorded when none is held, and replaced on each run until a counting approval row names the
    item's id with its revision; from then on it stays, and any later difference raises `unbumped-change`.
    """
    # ponytail: an entry for a revision that no longer exists is never pruned; prune by the index if the record grows
    bodies = dict(held)
    for item in next(each for each in plan.stages if each.stage == stage).items:
        key = str(item.id)
        if key not in bodies or key not in plan.intent.named_items:
            bodies[key] = item.body_hash
    return bodies


def frozen_bodies(held: Mapping[str, str], intents: Sequence[Intent]) -> dict[str, str]:
    """Return the held hashes that a counting approval row froze, for `structural.check` to compare with."""
    return {key: value for key, value in held.items() if any(key in current.named_items for current in intents)}


def dirty(changes: Sequence[str], intents: Sequence[Intent]) -> bool:
    """Return whether a changed path lies in the evaluated tree: a scanned suffix, outside AI-DLC's bookkeeping."""
    directories = {current.directory for current in intents}
    return any(
        adapters.reads(path) and not adapters.skipped(path, directories) and in_tree(intents, path) for path in changes
    )


def header(plan: Plan, stage: str, status: StageStatus, run: Run, digest: str) -> RunHeader:
    """Return the run header of a stage check: the run's commit, `dirty` and time, the status, its reasons and the hash."""
    state = next(each for each in plan.stages if each.stage == stage)
    return RunHeader(
        intent=plan.intent.directory,
        stage=stage,
        commit=run.commit,
        dirty=run.dirty,
        timestamp=run.timestamp,
        layers=("trace",),
        model=None,
        prompt=None,
        items=tuple(sorted(str(item.id) for item in state.items)),
        status=status.status,
        reasons={"errors": status.errors, "openTasks": status.open_tasks, "approval": status.approval},
        digest=digest,
    )


UNSUPPORTED_ROUTE = "unsupported route: units-generation is on the route, so per-unit stages"


class PlanError(Exception):
    """The command cannot pick what it was asked for: an intent, a stage, or a route that M2 does not report."""


def find_intent(intents: Sequence[Intent], option: str | None) -> Intent:
    """Return the intent named by `--intent`, or the only one.

    Raises:
        PlanError: the option names no record directory, or none is named and there is not exactly one.
    """
    known = ", ".join(current.directory for current in intents)
    if option is not None:
        found = next((current for current in intents if current.directory == option), None)
        if found is None:
            msg = f"no record directory {option}: the record directories are {known or 'none'}"
            raise PlanError(msg)
        return found
    if not intents:
        msg = "no record directory holds an aidlc-state.md"
        raise PlanError(msg)
    if len(intents) > 1:
        msg = f"several record directories hold an aidlc-state.md, so name one with --intent: {known}"
        raise PlanError(msg)
    return intents[0]


def select_intent(intents: Sequence[Intent], option: str | None) -> Intent:
    """Return the intent a stage check runs on: `find_intent`, refusing a route with per-unit stages.

    Raises:
        PlanError: see `find_intent`, or the intent's route holds `units-generation`.
    """
    found = find_intent(intents, option)
    if found.unsupported:
        raise PlanError(UNSUPPORTED_ROUTE)
    return found


def select_stage(plan: Plan, text: str) -> str:
    """Return the stage that `--stage` names: its id, or its slug when exactly one route stage has it.

    Raises:
        PlanError: the text is not a stage on the route, or its slug names several.
    """
    route = plan.intent.route
    if text in route:
        return text
    named = [stage for stage in route if stage.partition("/")[2] == text]
    if len(named) == 1:
        return named[0]
    if named:
        msg = f"{text} names several stages, so name one of {', '.join(named)}"
        raise PlanError(msg)
    msg = f"{text} is not a stage on the route: {', '.join(route) or _unreadable(plan.intent)}"
    raise PlanError(msg)


def _unreadable(intent: Intent) -> str:
    """Say where the state file's Stage Progress cannot be read, when that is why the route is empty."""
    found = [each for each in route_findings(intent) if each.subject == "Stage Progress"]
    if not found:
        return "none"
    return f"the state file's Stage Progress cannot be read ({found[0].path}:{found[0].line})"
