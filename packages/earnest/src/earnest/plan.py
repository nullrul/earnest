"""Plan and stage engine: the state file's Stage Progress and the audit shards, read from the work tree."""

import posixpath
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from earnest.index import TYPES, Index, Item, split_lines
from earnest.reporter import Finding


STATE = "aidlc-state.md"
AUDIT = "audit"
_SCOPE = re.compile(r"^- \*\*Scope\*\*:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
_ROW = re.compile(r"- \[([ \-?RxS])\] (\S+) \u2014 (EXECUTE|SKIP)(?:[:\s][ \t]*(.*))?")
_FIELD = re.compile(r"\*\*([^*:]+)\*\*:[ \t]*(.*)")
_PHASE_WORD = re.compile(r"\s+PHASE$", re.IGNORECASE)


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
            phase = _PHASE_WORD.sub("", stripped[4:].strip()).lower()
        elif in_progress and stripped.startswith("- ["):
            if phase and (row := _ROW.fullmatch(stripped)):
                rows.append(Row(phase, row[2], row[1], row[3], row[4] or "", line.number))
            else:
                unread.append(line.number)
    return State(scope.group(1) if scope else "", tuple(rows), tuple(unread), heading)


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
        state = _read(root, path) if posixpath.basename(path) == STATE else None
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
_ITEM_ID = re.compile(rf"(?:{'|'.join(TYPES)})~[a-z0-9-]+~[1-9][0-9]{{0,8}}")
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
    scope: str
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
        state.scope,
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
    return all(_ITEM_ID.fullmatch(token) for token in tokens), tokens


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
