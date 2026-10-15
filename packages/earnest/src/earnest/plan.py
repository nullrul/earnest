"""Plan and stage engine: the state file's Stage Progress and the audit shards, read from the work tree."""

import heapq
import posixpath
import re
from collections import deque
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from earnest import adapters, structural
from earnest.index import ID_ENTRY, Index, Item, Line, Source, split_lines
from earnest.index import digest as digest_of
from earnest.reporter import Finding, Position, Run, RunHeader, canonical, run_key, uri


AUDIT = "audit"
_SCOPE = re.compile(r"^- \*\*Scope\*\*:[ \t]*(.*)$", re.MULTILINE)  # no lazy group before `[ \t]*$`: that is quadratic
_ROW = re.compile(r"- \[([ \-?RxS])\] (\S+) \u2014 (EXECUTE|SKIP)(?:[:\s][ \t]*(.*))?")
_FIELD = re.compile(r"\*\*([^*:]+)\*\*:[ \t]*(.*)")
_UNITS = "units-generation"
UNIT_TABLE = "unit-of-work.md"
_NAME = re.compile(r"[a-z0-9-]+")  # a name of the grammar, and a unit directory's one path segment
_DELIMITER = re.compile(r":?-+:?")
_GENERATION = re.compile(r"[0-9]{1,9}")  # a whole number of at most nine digits
_COUNTING_SCOPES = (None, "per-stage", "unit-end")  # a missing `Gate Scope` reads as per-stage


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
    table: str | None = None  # the unit table's text, read only when Units Generation is an EXECUTE row


@dataclass(frozen=True)
class UnitRow:
    """One row of the unit table that joins a unit's name to its directory, and its line."""

    name: str
    directory: str
    line: int


@dataclass(frozen=True)
class UnitTable:
    """The unit table of `unit-of-work.md`: the rows that join, and the line and reason of each row that cannot."""

    rows: tuple[UnitRow, ...]
    bad: tuple[tuple[int, str], ...] = ()


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


def parse_units(text: str, slugs: Collection[str]) -> UnitTable | None:
    """Read the first table outside a code fence whose header holds `Unit ID` and `Directory`, or None.

    A row's name is its `Unit ID` by the id rule, lower-case with dots turned into hyphens, and must be a name of the
    grammar; its directory is one segment of lower-case letters, digits and hyphens that names none of the slugs. A row
    that cannot be read, or repeats an earlier row's name or directory, is kept apart with its line.
    """
    lines, fenced = adapters.markdown.scan(text.replace("\r\n", "\n"))
    unfenced = [line for line in lines if line.number not in fenced]
    for at, line in enumerate(unfenced):
        header = _cells(line.text)
        if header is None or "Unit ID" not in header or "Directory" not in header:
            continue
        below = unfenced[at + 1 : at + 2]
        delimiter = _cells(below[0].text) if below and below[0].number == line.number + 1 else None
        if delimiter and all(_DELIMITER.fullmatch(cell) for cell in delimiter):
            columns = (header.index("Unit ID"), header.index("Directory"))
            return _unit_rows(unfenced[at + 2 :], line.number + 2, columns, frozenset(slugs))
    return None


def _cells(text: str) -> list[str] | None:
    """Return the cells of a table line, or None when the line is no table line."""
    stripped = text.strip()
    if not stripped.startswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:].removesuffix("|").split("|")]


def _unit_rows(lines: Sequence[Line], first: int, columns: tuple[int, int], slugs: frozenset[str]) -> UnitTable:
    rows: list[UnitRow] = []
    bad: list[tuple[int, str]] = []
    for expected, line in enumerate(lines, first):
        cells = _cells(line.text)
        if cells is None or line.number != expected:  # the table ends at its first line that is no table line
            break
        name, directory = (cells[column] if column < len(cells) else "" for column in columns)
        name = name.lower().replace(".", "-")
        if not _NAME.fullmatch(name) or not _NAME.fullmatch(directory) or directory in slugs:
            reason = (
                "cannot be read as a unit: write its `Unit ID` and a `Directory` of one segment of lower-case"
                " letters, digits and hyphens that names no stage"
            )
            bad.append((line.number, reason))
        elif any(row.name == name or row.directory == directory for row in rows):
            bad.append((line.number, f"repeats the unit `{name}` or the directory `{directory}` of an earlier row"))
        else:
            rows.append(UnitRow(name, directory, line.number))
    return UnitTable(tuple(rows), tuple(bad))


def load(root: Path, files: Sequence[str]) -> list[Record]:
    """Read every intent among the listed files: one record per `aidlc-state.md`, sorted by its directory.

    Raises:
        OSError: a listed file that exists cannot be read.
    """
    listed = frozenset(files)
    records: list[Record] = []
    for path in files:
        text = _read(root, path) if posixpath.basename(path) == adapters.STATE else None
        if text is not None:
            directory = posixpath.dirname(path)
            state = parse_state(text)
            events = [event for shard in _shards(files, directory) for event in _events(root, shard)]
            records.append(
                Record(directory, path, state, tuple(sorted(events)), _table(root, listed, directory, state))
            )
    return sorted(records, key=lambda record: record.directory)


def _table(root: Path, listed: frozenset[str], directory: str, state: State) -> str | None:
    """Return the unit table's text when Units Generation is an EXECUTE row: None when it is not listed or a symlink."""
    row = next((row for row in state.rows if row.slug == _UNITS and row.action == "EXECUTE"), None)
    path = None if row is None else posixpath.join(directory, row.stage, UNIT_TABLE)
    return _read(root, path) if path in listed else None


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
# Upstream's `for_each: unit-of-work` stages: on a route that holds Units Generation each stands once per unit.
FOR_EACH = frozenset(
    {"functional-design", "nfr-requirements", "nfr-design", "infrastructure-design", "code-generation"}
)


def _slug(stage: str) -> str:
    """Return a stage id's slug, its last segment, for `<phase>/<slug>` and `<phase>/<unit directory>/<slug>` alike."""
    return stage.rpartition("/")[2]


@dataclass(frozen=True)
class Approval:
    """A stage's approval: the ids and revisions its row names (None without an `Items` field), who gave it, its hash.

    `scope` names the stages whose items together make the approval current, for a unit-end row; empty is its stage.
    """

    stage: str
    items: tuple[str, ...] | None
    by: str | None
    digest: str | None
    scope: tuple[str, ...] = ()


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
    executed: tuple[str, ...] = ()  # the route before the per-unit expansion, which the route rule reads
    events: tuple[Event, ...] = ()  # the counting audit events
    table: UnitTable | None = None  # the unit table, on a route that holds Units Generation

    @property
    def units_route(self) -> bool:
        """Return whether the route holds Units Generation, so per-unit stages and a unit table."""
        return any(_slug(stage) == _UNITS for stage in self.executed)


@dataclass(frozen=True)
class StageState:
    """One stage of a plan: its approval, whether that approval is current, and the items its artifacts hold."""

    stage: str
    approval: Approval | None
    state: Literal["current", "outdated", "none"]
    items: tuple[Item, ...]


@dataclass(frozen=True)
class Unit:
    """A `unit` item of an intent, in unit order.

    It holds whether the order takes it, the names it depends on, the items it delivers by type and name, its
    directory from the unit table (None without a row) and its lane's frontier (None when every stage is approved).
    """

    item: Item
    resolved: bool
    depends: frozenset[str] = frozenset()
    delivers: frozenset[tuple[str, str]] = frozenset()
    directory: str | None = None
    frontier: str | None = None

    @property
    def name(self) -> str:
        """Return the unit's name, which a gate row's `Unit` and a unit table row carry."""
        return self.item.id.name


@dataclass(frozen=True)
class Plan:
    """An intent's stages in route order, and the frontier: the first stage without a current approval.

    On a route that holds Units Generation it also holds the units in unit order, the unit each per-unit stage belongs
    to, and the findings of the join of the unit table and the `unit` items.
    """

    intent: Intent
    stages: tuple[StageState, ...]
    frontier: str | None
    units: tuple[Unit, ...] = ()
    owners: Mapping[str, str] = field(default_factory=dict)  # each per-unit stage and the name of its unit
    join: tuple[Finding, ...] = ()


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
    skipped = {  # a skip row that carries a team field skips nothing
        event.fields.get("Stage")
        for event in events
        if event.name == "STAGE_SKIPPED" and not any(name in event.fields for name in _TEAM_FIELDS)
    }
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
    units_route = any(_slug(stage) == _UNITS for stage in route)
    table = parse_units(record.table, {row.slug for row in rows}) if units_route and record.table else None
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
        route,
        tuple(events),
        table,
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
    """Build the plan of an intent over an index: each stage's items and approval, and the frontier.

    On a route that holds Units Generation it first joins the unit table to the `unit` items and expands each per-unit
    stage once per joined unit, in unit order; each unit's frontier is the first stage of its lane without a current
    approval.
    """
    units: tuple[Unit, ...] = ()
    join: list[Finding] = []
    if intent.units_route:
        units, join = _join(intent, index)
        intent = _expand(intent, units)
    owners = {
        f"{_phase_of(stage)}/{unit.directory}/{_slug(stage)}": unit.name
        for unit in units
        if unit.directory
        for stage in intent.executed
        if _slug(stage) in FOR_EACH
    }
    held = {
        stage: tuple(
            item
            for item in index.defined.values()
            if item.path.startswith(posixpath.join(intent.directory, stage) + "/")
        )
        for stage in intent.route
    }
    stages: list[StageState] = []
    for stage in intent.route:
        approval = intent.approvals.get(stage)
        current = {
            str(item.id)
            for each in (approval.scope if approval and approval.scope else (stage,))
            for item in held[each]
        }
        if approval is None:
            state: Literal["current", "outdated", "none"] = "none"
        elif approval.items is None or set(approval.items) == current:
            state = "current"
        else:
            state = "outdated"
        stages.append(StageState(stage, approval, state, held[stage]))
    frontier = next((state.stage for state in stages if state.state != "current"), None)
    states = {state.stage: state.state for state in stages}
    units = tuple(
        replace(
            unit, frontier=next((s for s in _lane(intent.route, owners, unit.name) if states[s] != "current"), None)
        )
        for unit in units
    )
    return Plan(intent, tuple(stages), frontier, units, owners, tuple(join))


def _phase_of(stage: str) -> str:
    return stage.partition("/")[0]


def _lane(route: Sequence[str], owners: Mapping[str, str], name: str) -> list[str]:
    """Return a unit's lane: the route less the other units' per-unit stages."""
    return [stage for stage in route if owners.get(stage, name) == name]


def _join(intent: Intent, index: Index) -> tuple[tuple[Unit, ...], list[Finding]]:
    """Join the unit table to the intent's `unit` items: each unit with its directory, and the join's findings.

    A missing table, a row that cannot be read or names no `unit` item, and a `unit` item that no row names each
    raise `earnest/route-mismatch` in the Units Generation stage; a row that raises one stands for no unit.
    """
    stage = next(each for each in intent.executed if _slug(each) == _UNITS)
    table_path = posixpath.join(intent.directory, stage, UNIT_TABLE)
    ordered = unit_order(intent.directory, index)
    names = {unit.name for unit in ordered}
    rows = intent.table.rows if intent.table is not None else ()
    joined = {row.name: row for row in rows if row.name in names}

    def mismatch(path: str, line: int, subject: str, message: str) -> Finding:
        return Finding(path, line, "earnest/route-mismatch", subject, message, stage=stage, intent=intent.directory)

    found: list[Finding] = []
    if intent.table is None:
        line = next(row.line for row in intent.rows if row.slug == _UNITS and row.action == "EXECUTE")
        message = (
            f"Earnest cannot read the unit table of `{table_path}`: it is missing, a symlink, or holds no table whose"
            " header has `Unit ID` and `Directory`; restore it, with one row per unit, so each unit's stages are found"
        )
        found.append(mismatch(intent.state_path, line, _UNITS, message))
    else:
        found += [
            mismatch(table_path, line, "unit table", f"line {line} of the unit table {why}")
            for line, why in intent.table.bad
        ]
    for row in rows:
        if row.name not in names:
            message = (
                f"the unit table row for `{row.name}` names no `unit` item: add `unit~{row.name}~1`, or remove the row"
            )
            found.append(mismatch(table_path, row.line, row.name, message))
    for unit in ordered:
        if unit.name not in joined:
            message = (
                f"`{unit.item.id}` has no row in the unit table of `{table_path}`, so it has no directory: add a row"
                f" with its `Unit ID` and its `Directory`"
            )
            found.append(mismatch(unit.item.path, unit.item.line, str(unit.item.id), message))
    units = tuple(
        replace(unit, directory=joined[unit.name].directory) if unit.name in joined else unit for unit in ordered
    )
    return units, found


def unit_order(directory: str, index: Index) -> list[Unit]:
    """Return the `unit` items of the record directory in unit order, each with what it depends on and delivers.

    A `Depends:` entry counts when it names, by type and name, a `unit` item there; any other is unknown. Earnest
    repeatedly takes, among the units with no unknown entry whose dependencies are all taken, the lowest name by code
    point. The units it never takes, on a cycle, with an unknown entry or depending on such a unit, follow in name
    order and are unresolved.
    """
    items = {
        item.id.name: item
        for item in index.defined.values()
        if item.id.type == "unit" and _within(directory, item.path)
    }
    depends: dict[str, set[str]] = {name: set() for name in items}
    delivers: dict[str, set[tuple[str, str]]] = {name: set() for name in items}
    unknown: set[str] = set()
    for link in index.links:
        owner = link.owner
        if owner is None or owner.type != "unit" or owner.name not in items or not _within(directory, link.path):
            continue
        if link.key == "Delivers":
            delivers[owner.name].add(link.target.key)
        elif link.key == "Depends" and link.target.type == "unit" and link.target.name in items:
            depends[owner.name].add(link.target.name)
        elif link.key == "Depends":
            unknown.add(owner.name)
    waiting = {name: len(names) for name, names in depends.items()}
    ready = [name for name, count in waiting.items() if count == 0 and name not in unknown]
    heapq.heapify(ready)
    taken: list[str] = []
    while ready:
        name = heapq.heappop(ready)
        taken.append(name)
        # ponytail: a scan of every unit per unit taken, quadratic in the units of one intent, which number in the tens;
        # keep a follower map if an intent ever holds thousands
        for follower in sorted(other for other, names in depends.items() if name in names):
            waiting[follower] -= 1
            if waiting[follower] == 0 and follower not in unknown:
                heapq.heappush(ready, follower)
    rest = sorted(set(items) - set(taken))
    return [
        Unit(items[name], name in taken, frozenset(depends[name]), frozenset(delivers[name]))
        for name in [*taken, *rest]
    ]


def _expand(intent: Intent, units: Sequence[Unit]) -> Intent:
    """Return the intent with each per-unit stage once per joined unit, in unit order, as `<phase>/<directory>/<slug>`.

    Its approvals add those of the per-unit stages, which only unit-scoped gate rows give, and its named items add the
    items those rows froze.
    """
    joined = [unit for unit in units if unit.directory]
    per_unit = [stage for stage in intent.executed if _slug(stage) in FOR_EACH]
    route = tuple(
        expanded
        for stage in intent.executed
        for expanded in (
            [f"{_phase_of(stage)}/{unit.directory}/{_slug(stage)}" for unit in joined] if stage in per_unit else [stage]
        )
    )
    stage_ids = {
        (unit.name, _slug(stage)): f"{_phase_of(stage)}/{unit.directory}/{_slug(stage)}"
        for unit in joined
        for stage in per_unit
    }
    lanes = {unit.name: frozenset(_slug(stage) for stage in per_unit) for unit in joined}
    gates = [event for event in intent.events if event.name in {"GATE_APPROVED", "GATE_REJECTED"}]
    floors = {name: _generation(gates, name) for name in lanes}
    approvals = {stage: approval for stage, approval in intent.approvals.items() if stage in route}
    for key, stage in stage_ids.items():
        found = _unit_approval(key, gates, lanes, floors, stage_ids)
        if found is not None:
            approvals[stage] = found
    slugs = {_slug(stage) for stage in per_unit}
    plain = [event for event in gates if not _team(event) and event.fields.get("Stage") not in slugs]
    return replace(
        intent, route=route, approvals=approvals, named_items=_named(plain) | _unit_named(gates, lanes, floors)
    )


def _team(event: Event) -> bool:
    return any(name in event.fields for name in _TEAM_FIELDS)


def _split(text: str) -> tuple[str, ...]:
    """Split a list field, `Items` or `Gate Stages`, at commas and blanks."""
    return tuple(token for token in re.split(r"[\s,]+", text) if token)


def _gate_keys(event: Event, lanes: Mapping[str, frozenset[str]]) -> frozenset[tuple[str, str]]:
    """Return the unit names and slugs a gate row speaks for: none unless its `Unit` is the name of a joined unit.

    With no `Gate Scope`, or `per-stage`, and a `Gate Stages` absent or equal to its `Stage`, it speaks for that unit's
    stage of its `Stage`. A `unit-end` row whose `Gate Stages` lists its `Stage` and only per-unit stages on the unit's
    lane speaks for each of them. Any other row, `unit-merge` included, speaks for none.
    """
    name, slug = event.fields.get("Unit"), event.fields.get("Stage", "")
    if name is None or name not in lanes:
        return frozenset()
    scope, listed = event.fields.get("Gate Scope"), event.fields.get("Gate Stages")
    if scope in {None, "per-stage"} and slug in lanes[name] and (listed is None or _split(listed) == (slug,)):
        return frozenset({(name, slug)})
    stages = _split(listed or "")
    if scope == "unit-end" and slug in stages and all(each in lanes[name] for each in stages):
        return frozenset((name, each) for each in stages)
    return frozenset()


def _generation(gates: Sequence[Event], name: str) -> int:
    """Return a unit's generation: the highest whole `Attempt Generation` on its counting gate rows, 0 when absent.

    A per-stage or unit-end row counts, whatever stage it names; a value that is no whole number raises nothing.
    """
    values = [
        int(value)
        for event in gates
        if event.fields.get("Unit") == name and event.fields.get("Gate Scope") in _COUNTING_SCOPES
        for value in (event.fields.get("Attempt Generation", "0"),)
        if _GENERATION.fullmatch(value)
    ]
    return max(values, default=0)


def _at_generation(event: Event, floor: int) -> bool:
    value = event.fields.get("Attempt Generation", "0")
    return _GENERATION.fullmatch(value) is not None and int(value) >= floor


def _voids(rejection: Event, key: tuple[str, str], lanes: Mapping[str, frozenset[str]]) -> bool:
    """Return whether a rejection voids a unit's stage.

    It voids what it would approve, else its `Stage` for its unit, or for every unit when its `Unit` names none. No
    generation discounts it.
    """
    spoken = _gate_keys(rejection, lanes)
    if spoken:
        return key in spoken
    name = rejection.fields.get("Unit")
    return rejection.fields.get("Stage") == key[1] and (name == key[0] or name not in lanes)


def _unit_approval(
    key: tuple[str, str],
    gates: Sequence[Event],
    lanes: Mapping[str, frozenset[str]],
    floors: Mapping[str, int],
    stage_ids: Mapping[tuple[str, str], str],
) -> Approval | None:
    """Return a unit's stage's approval: its latest unit-scoped row at the unit's generation, unless a rejection voids it.

    A unit-end row is current on the items of every stage it lists, which `scope` names.
    """
    approved = [
        (event, items)
        for event in gates
        if event.name == "GATE_APPROVED" and key in _gate_keys(event, lanes) and _at_generation(event, floors[key[0]])
        for ok, items in (_items(event),)
        if ok
    ]
    if not approved:
        return None
    event, items = max(approved, key=lambda pair: pair[0].key)
    if any(other.name == "GATE_REJECTED" and other.key > event.key and _voids(other, key, lanes) for other in gates):
        return None
    by = event.fields.get("Approved By")
    scope = tuple(sorted(stage_ids[each] for each in _gate_keys(event, lanes)))
    return Approval(
        stage_ids[key], items, by if by in {"human", "automatic"} else None, event.fields.get("Assessment Hash"), scope
    )


def _unit_named(
    gates: Sequence[Event],
    lanes: Mapping[str, frozenset[str]],
    floors: Mapping[str, int],
) -> frozenset[str]:
    """Return the ids that counting unit-scoped approvals froze.

    While any covered key survives rejection, all listed revisions stay frozen, even items in rejected stages.
    This fails closed without trusting current item locations; only voiding every key releases the row's items.
    It grants no approval or currentness.
    """
    named: set[str] = set()
    for event in gates:
        spoken = _gate_keys(event, lanes)
        ok, items = _items(event)
        if event.name != "GATE_APPROVED" or not spoken or not ok or not items:
            continue
        if not _at_generation(event, floors[next(iter(spoken))[0]]):
            continue
        later = [other for other in gates if other.name == "GATE_REJECTED" and other.key > event.key]
        surviving = {key for key in spoken if not any(_voids(other, key, lanes) for other in later)}
        if surviving:
            named.update(items)
    return frozenset(named)


def _items(event: Event) -> tuple[bool, tuple[str, ...] | None]:
    """Return whether the event's `Items` field parses, and the ids it names: None when the field is absent."""
    text = event.fields.get("Items")
    if text is None:
        return True, None
    tokens = _split(text)
    return all(ID_ENTRY.fullmatch(token) for token in tokens), tokens


def _approval(stage: str, gates: Sequence[Event]) -> Approval | None:
    mine = [event for event in gates if event.fields.get("Stage") == _slug(stage)]
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
    """Return the item types that some stage of an intent's route produces, or None when none does.

    It reads each route before the per-unit expansion, so a unit table that cannot be read drops no need. None is the
    route rule's off switch: `structural.check` then keeps every need and link, as it does with no plan.
    """
    types = frozenset().union(
        *(PRODUCES.get(_slug(stage), frozenset()) for current in intents for stage in current.executed)
    )
    return types or None  # no intent, or a route that produces nothing: keep every need and link


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
    return not holders or any(
        stage_of(current, path) is not None or _per_unit_file(current, path) for current in holders
    )


def _per_unit_file(intent: Intent, path: str) -> bool:
    """Return whether path lies under `<phase>/<directory>/<slug>/` of a per-unit stage, whatever the directory.

    It holds without a unit table too, so a table that cannot be read drops no file from the evaluated tree.
    """
    if not intent.units_route:
        return False
    parts = (path[len(intent.directory) + 1 :] if intent.directory else path).split("/")
    stage = f"{parts[0]}/{parts[2]}" if len(parts) > 3 else ""  # noqa: PLR2004 - phase, directory, slug, then a file
    return _slug(stage) in FOR_EACH and stage in intent.executed


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


def unit_done(plan: Plan, index: Index, levels: Mapping[str, str]) -> dict[str, bool]:
    """Return whether each unit is done.

    A unit is done when it has a row, unit order resolves it, every unit it depends on is done, and its Code Generation
    stage holds a task and every task there is done.
    """
    done: dict[str, bool] = {}
    for unit in plan.units:  # in unit order, so a resolved unit's dependencies are decided before it
        tasks = [
            item
            for state in plan.stages
            if plan.owners.get(state.stage) == unit.name and _slug(state.stage) == _CODE_GENERATION
            for item in state.items
            if item.id.type == "task"
        ]
        done[unit.name] = (
            unit.directory is not None
            and unit.resolved
            and all(done.get(name, False) for name in unit.depends)
            and bool(tasks)
            and all(task_done(task, index, levels) for task in tasks)
        )
    return done


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
        if _slug(state.stage) == _BUILD_AND_TEST:
            open_tasks += stest  # an `stest` passes only at evidence, which M2 has none of
        done = errors == 0 and open_tasks == 0 and state.state == "current"
        result[state.stage] = StageStatus("done" if done else "not done", errors, open_tasks, state.state)
    return result


def plan_findings(plan: Plan, index: Index) -> list[Finding]:
    """Return the findings the plan itself raises: `unplanned`, `cycle` and `route-mismatch`."""
    return [*_unplanned(plan, index), *_cycle_findings(plan, index), *route_findings(plan.intent), *plan.join]


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
    """Return `properties.plan`: one entry per plan, in directory order, with its stages, frontier and tasks."""
    entries: list[dict[str, object]] = []
    for current in sorted(plans, key=lambda each: each.intent.directory):
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
        done = unit_done(current, index, levels)
        units = [
            {
                "id": str(unit.item.id),
                "status": "done" if done[unit.name] else "not done",
                "directory": unit.directory,
                "frontier": unit.frontier,
            }
            for unit in current.units
        ]
        entries.append(
            {
                "intent": current.intent.directory,
                "stages": stages,
                "frontier": current.frontier,
                "tasks": tasks,
                "units": units,
            }
        )
    return {"intents": entries}


def inside(intent: Intent, path: str) -> bool:
    """Return whether the file at path lies in the intent's record directory."""
    return _within(intent.directory, path)


def _within(directory: str, path: str) -> bool:
    return directory == "" or path.startswith(directory + "/")


def _unplanned(plan: Plan, index: Index) -> list[Finding]:
    """Raise `unplanned` for each `req` no task delivers, against the first Code Generation stage on the route.

    On a route that holds Units Generation it counts against the Code Generation of the lowest-named unit with a valid
    row that delivers the requirement, else of the lowest-named unit with a valid row, else against Units Generation.
    """
    first = next((each for each in plan.intent.executed if _slug(each) == _CODE_GENERATION), None)
    if first is None:
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
            stage=_unit_target(plan, first, item.id.key) if plan.intent.units_route else first,
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
    """Place a gap at the first route stage that produces the missing child's type.

    When that stage is per-unit it is the stage of the unit whose stage holds the item, else the fallback unit's.
    """
    if finding.rule != "earnest/gap" or owner is None:
        return None
    wanted = (stage for stage in owner.intent.executed if finding.child in PRODUCES.get(_slug(stage), ()))
    stage = next(wanted, None)
    if stage is None:
        return None
    if not owner.intent.units_route or _slug(stage) not in FOR_EACH:
        return owner, stage
    holder = owner.owners.get(stage_of(owner.intent, finding.path) or "")
    if holder is not None:
        directory = next(unit.directory for unit in owner.units if unit.name == holder)
        return owner, f"{_phase_of(stage)}/{directory}/{_slug(stage)}"
    named = _SUBJECT.fullmatch(finding.subject)
    return owner, _unit_target(owner, stage, (named[1], named[2]) if named else None)


def _unit_target(plan: Plan, stage: str, delivered: tuple[str, str] | None) -> str:
    """Return a per-unit stage of the fallback unit, or Units Generation when no unit has a valid row.

    The fallback is the lowest-named unit with a valid row that delivers the item, else the lowest-named unit with a
    valid row; names compare by code point, so the unit order, which follows `Depends:`, changes nothing here.
    """
    valid = sorted((unit for unit in plan.units if unit.directory), key=lambda unit: unit.name)
    chosen = next((unit for unit in valid if delivered in unit.delivers), valid[0] if valid else None)
    if chosen is None:
        return next(each for each in plan.intent.executed if _slug(each) == _UNITS)
    return f"{_phase_of(stage)}/{chosen.directory}/{_slug(stage)}"


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
    """Return a stage's position: a per-unit stage's by its unit's frontier on its lane, any other's by the route's."""
    name = plan.owners.get(stage)
    if name is None:
        order, frontier = [state.stage for state in plan.stages], plan.frontier
    else:
        order = _lane(plan.intent.route, plan.owners, name)
        frontier = next(unit.frontier for unit in plan.units if unit.name == name)
    if frontier is None:
        return "behind"
    here, front = order.index(stage), order.index(frontier)
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


class PlanError(Exception):
    """The command cannot pick what it was asked for: an intent or a stage."""


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


def select_stage(plan: Plan, text: str) -> str:
    """Return the stage that `--stage` names: its id, per-unit ones included, or its slug when one route stage has it.

    Raises:
        PlanError: the text is not a stage on the route, or its slug names several.
    """
    route = plan.intent.route
    if text in route:
        return text
    named = [stage for stage in route if _slug(stage) == text]
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
