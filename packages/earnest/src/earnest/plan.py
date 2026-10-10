"""Plan and stage engine: the state file's Stage Progress and the audit shards, read from the work tree."""

import posixpath
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from earnest.index import split_lines


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
