"""Reporter: the SARIF 2.1.0 log, with each requirement's trace level, and the summary that leads with three percentages."""

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import quote


RuleId = Literal[
    "earnest/cycle",
    "earnest/duplicate",
    "earnest/evidence-failed",
    "earnest/gap",
    "earnest/impact-degraded",
    "earnest/judge-not-satisfied",
    "earnest/judge-uncalibrated",
    "earnest/near-miss",
    "earnest/orphaned",
    "earnest/out-of-task",
    "earnest/outdated",
    "earnest/override-drift",
    "earnest/override-expired",
    "earnest/predated",
    "earnest/req-not-ears",
    "earnest/route-mismatch",
    "earnest/unbumped-change",
    "earnest/unplanned",
    "earnest/unwanted",
]
Position = Literal["behind", "current", "ahead"]
RULES: dict[RuleId, str] = {
    "earnest/cycle": "error",
    "earnest/duplicate": "error",
    "earnest/evidence-failed": "error",
    "earnest/gap": "error",
    "earnest/impact-degraded": "note",
    "earnest/judge-not-satisfied": "warning",
    "earnest/judge-uncalibrated": "warning",
    "earnest/near-miss": "error",
    "earnest/orphaned": "error",
    "earnest/out-of-task": "warning",
    "earnest/outdated": "error",
    "earnest/override-drift": "warning",
    "earnest/override-expired": "warning",
    "earnest/predated": "error",
    "earnest/req-not-ears": "error",
    "earnest/route-mismatch": "error",
    "earnest/unbumped-change": "error",
    "earnest/unplanned": "warning",
    "earnest/unwanted": "warning",
}
LEVELS = ("untraced", "traced", "judged", "evidenced")
# The three exits of an out-of-task finding, in the order of the Out-of-task rule; the first two clear it.
EXITS = ("tag it under a requirement the task delivers", "propose a task", "declare it blocked")
DEGRADED = (
    "the line lies in no tag region and no coverage data covers it, so impact selected the full suite:"
    " run every test, or tag the line under the requirement it serves"
)
_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_OPENINGS: dict[Position, str] = {
    "behind": "regression in approved stage {}",
    "current": "in scope at {}",
    "ahead": "expected at {}",
}


@dataclass(frozen=True, order=True)
class Finding:
    """A located result: file, line, rule, the id or text it is about, and a message that names the change to make.

    The stage it counts against and its position come from the plan; with no stage a finding is in scope. The extra
    fields take no part in equality or order.
    """

    path: str
    line: int
    rule: RuleId
    subject: str
    message: str
    stage: str | None = field(default=None, compare=False)
    intent: str | None = field(default=None, compare=False)  # the record directory of its stage; never serialized
    position: Position = field(default="current", compare=False)
    note: bool = field(default=False, compare=False)  # a note at every position, as a stale stage approval is
    child: str = field(default="", compare=False)  # for a gap, the item type whose absence it reports
    observations: tuple[Mapping[str, object], ...] = field(default=(), compare=False)  # else the trace observation

    @property
    def level(self) -> str:
        """Return the SARIF level: note at position ahead or when flagged, else the level of the finding's rule."""
        return "note" if self.note or self.position == "ahead" else RULES[self.rule]

    @property
    def text(self) -> str:
        """Return the message as it is reported, opening with the finding's position."""
        if self.stage is None:
            return f"in scope: {self.message}"
        return f"{_OPENINGS[self.position].format(self.stage)}: {self.message}"


def deleted_message(line: int) -> str:
    """Return the message of an `impact-degraded` note at a deleted line with no coverage data."""
    return (
        f"line {line} of the baseline commit was deleted here and no coverage data covers it, so impact selected the"
        " full suite: run every test"
    )


def evidence_message(requirement: str, path: str, line: int, cause: str) -> str:
    """Return the message of an `evidence-failed` finding: the requirement, the file and line, and what failed there."""
    return f"`{requirement}` is not evidenced at {path}:{line}: {cause}"


def out_of_task_message(task: str, tags: Sequence[str]) -> str:
    """Return the message of an out-of-task finding: the current task, the region's tags or `no tag`, the exits."""
    region = f"the region of {', '.join(f'`{tag}`' for tag in tags)}" if tags else "a hunk with no tag"
    return f"the change in {region} lies outside the current task `{task}`; exits: {'; '.join(EXITS)}"


@dataclass(frozen=True)
class Impact:
    """The impact section: the impacted requirements and features, the tests to run, and whether it is degraded.

    `base` is the change baseline and `mapped` whether a coverage map was read. With no map, a degraded impact
    selects the full suite as no test, and the summary says so.
    """

    requirements: tuple[str, ...]
    features: tuple[str, ...]
    tests: tuple[str, ...]
    degraded: bool
    base: str
    mapped: bool

    def as_property(self) -> dict[str, object]:
        """Return `properties.impact`: the ids sorted, and `degraded`."""
        return {
            "requirements": sorted(self.requirements),
            "features": sorted(self.features),
            "tests": sorted(self.tests),
            "degraded": self.degraded,
        }

    def lines(self) -> list[str]:
        """Return the summary's impact section, one line a field."""
        tests = ", ".join(sorted(self.tests)) or ("the full suite" if self.degraded else "none")
        lines = [
            "impact:",
            f"  requirements: {', '.join(sorted(self.requirements)) or 'none'}",
            f"  features: {', '.join(sorted(self.features)) or 'none'}",
            f"  tests: {tests}",
            f"  degraded: {'yes' if self.degraded else 'no'}",
        ]
        if not self.mapped:
            lines.append(f"  coverage map: none for the baseline commit {self.base}")
        return lines


@dataclass(frozen=True)
class Run:
    """What one run adds to its log and summary besides the findings: the commit and the plan's view of the work."""

    commit: str
    dirty: bool = False
    timestamp: str = ""
    plan: Mapping[str, object] | None = None
    assessment: Mapping[str, object] | None = None
    record_absent: bool = False
    unheld: int = 0
    impact: Impact | None = None
    notes: tuple[str, ...] = ()  # summary lines the run states once, such as why it took no coverage map
    model: str | None = None  # the judge's model id and prompt hash, when the judge layer ran
    prompt: str | None = None
    observations: tuple[Mapping[str, object], ...] | None = None  # the observations of record, when the judge ran
    evidence: bool = False  # whether the evidence layer ran


def percentages(levels: Mapping[str, str]) -> dict[str, int]:
    """Return the share of requirements at each level or above, in whole percent rounded down, so 100 means all."""
    ranks = [LEVELS.index(level) for level in levels.values()]
    return {
        name: 100 * sum(rank >= floor for rank in ranks) // len(ranks) if ranks else 0
        for floor, name in enumerate(LEVELS[1:], start=1)
    }


def uri(path: str) -> str:
    """Return a path as a SARIF artifact uri: percent-encoded, with names that are not UTF-8 kept apart."""
    return quote(path, errors="surrogateescape")  # Git hands over names that are not UTF-8 as surrogates


def sarif(findings: Sequence[Finding], levels: Mapping[str, str], run: Run) -> str:
    """Return one SARIF 2.1.0 log; it holds no timestamp, so an unchanged repository gives the same bytes."""
    properties: dict[str, object] = {"traceLevels": dict(levels), "percentages": percentages(levels)}
    if run.plan is not None:
        properties["plan"] = run.plan
    if run.assessment is not None:
        properties["assessment"] = run.assessment
    if run.impact is not None:
        properties["impact"] = run.impact.as_property()
    invocation: dict[str, object] = {"commit": run.commit, "dirty": run.dirty, "layers": ["trace"]}
    if run.observations is not None:
        properties["observations"] = list(run.observations)
        layers = ["trace", "judge", "evidence"] if run.evidence else ["trace", "judge"]
        invocation |= {"layers": layers, "model": run.model, "prompt": run.prompt}
    body = {
        "tool": {"driver": {"name": "earnest"}},
        "invocations": [
            {
                "executionSuccessful": True,
                "properties": invocation,
            },
        ],
        "results": [_result(finding) for finding in sorted(findings)],
        "properties": properties,
    }
    log = {"$schema": _SCHEMA, "version": "2.1.0", "runs": [body]}
    return json.dumps(log, sort_keys=True, separators=(",", ":")) + "\n"


def summary(findings: Sequence[Finding], levels: Mapping[str, str], run: Run | None = None) -> str:
    """Return the human summary: the percentages, the plan's view of the work, each level, then each finding."""
    shares = percentages(levels)
    head = (
        f"traced {shares['traced']}%, judged {shares['judged']}%, evidenced {shares['evidenced']}%;"
        f" requirements: {len(levels)}"
    )
    lines = [
        head,
        *(_run_lines(run) if run is not None else []),
        *(f"  {req}: {level}" for req, level in sorted(levels.items())),
        *(f"{f.path}:{f.line}: {f.level} {f.rule}: {f.text}" for f in sorted(findings)),
    ]
    errors = sum(1 for finding in findings if finding.level == "error")
    lines.append(f"findings: {len(findings)}, errors: {errors}")
    return "\n".join(lines) + "\n"


def _run_lines(run: Run) -> list[str]:
    lines: list[str] = []
    if run.plan is not None:
        for entry in cast("Sequence[Mapping[str, Any]]", run.plan["intents"]):
            lines.extend(_intent_lines(entry))
    if run.assessment is not None:
        lines.append(f"assessment {run.assessment['stage']}: {run.assessment['hash']} ({run.assessment['status']})")
    if run.record_absent:
        lines.append("record: absent, body-hash baseline unavailable")
    if run.unheld > 0:
        lines.append(f"body-hash baseline: {run.unheld} items without a held hash")
    if run.impact is not None:
        lines.extend(run.impact.lines())
    lines.extend(run.notes)
    return lines


def _intent_lines(entry: Mapping[str, Any]) -> list[str]:
    lines = [f"intent {entry['intent']}"]
    for stage in entry["stages"]:
        by = stage["approvedBy"] if stage["approval"] == "current" else None
        approval = f"{stage['approval']}, {by}" if by else stage["approval"]
        lines.append(f"  {stage['stage']}: {stage['status']}, approval {approval}")
    lines.append(f"  frontier: {entry['frontier'] or 'none'}")
    lines.extend(f"  task {task['id']}: {task['status']}" for task in entry["tasks"])
    lines.extend(
        f"  unit {unit['id']}: {unit['status']}, directory {unit['directory'] or 'none'},"
        f" frontier {unit['frontier'] or 'none'}"
        for unit in entry["units"]
    )
    return lines


def location(path: str, line: int) -> dict[str, object]:
    """Return a SARIF physical location: the file as its artifact uri, and the line."""
    return {"artifactLocation": {"uri": uri(path)}, "region": {"startLine": line}}


def _result(finding: Finding) -> dict[str, object]:
    where = location(finding.path, finding.line)
    observation = {
        "method": "trace",
        "subject": finding.subject,
        "result": finding.rule.removeprefix("earnest/"),
        "reasoning": finding.message,
        "location": where,
    }
    observations = list(finding.observations) or [observation]
    properties: dict[str, object] = {"position": finding.position, "observations": observations}
    if finding.stage is not None:
        properties["stage"] = finding.stage
    return {
        "ruleId": finding.rule,
        "level": finding.level,
        "message": {"text": finding.text},
        "locations": [{"physicalLocation": where}],
        "properties": properties,
    }


RECORD = ".earnest/assessment.json"
VERSION = 1
_KNOWN = frozenset({"version", "runs", "bodies", "coverage", "judge", "calibration"})


class RecordError(Exception):
    """The assessment record cannot be used: it does not parse, has the wrong shape, or is newer than this release."""


@dataclass(frozen=True)
class RunHeader:
    """The latest run of one stage of one intent, as the record keeps it; the digest is stored under the key `hash`."""

    intent: str
    stage: str
    commit: str
    dirty: bool
    timestamp: str
    layers: tuple[str, ...]
    model: str | None
    prompt: str | None
    items: tuple[str, ...]
    status: str
    reasons: Mapping[str, int | str]
    digest: str


@dataclass
class Record:
    """The assessment record: the latest run header of each stage, the body hashes, and the slots later layers fill.

    `extra` holds the top-level keys another tool added, so a write does not lose them. `Record()` is the empty record.
    """

    version: int = VERSION
    runs: dict[str, RunHeader] = field(default_factory=dict)
    bodies: dict[str, str] = field(default_factory=dict)
    # the commit the coverage map was taken at, as `{"commit": sha}`; the map lies under `.earnest/coverage/<sha>`
    coverage: dict[str, object] = field(default_factory=lambda: {"commit": None})
    judge: dict[str, object] = field(default_factory=lambda: {"cache": {}})
    calibration: dict[str, object] | None = None
    extra: dict[str, object] = field(default_factory=dict)


def canonical(obj: object, *, pretty: bool = False) -> str:
    """Return obj as canonical JSON: sorted keys, ASCII, integers only.

    The compact form has no trailing newline and is what the assessment hash and the SARIF log use; the pretty form
    indents two spaces and ends with one newline, and is what the record file holds.

    Raises:
        TypeError: obj holds a float.
    """
    _integers_only(obj)
    if pretty:
        return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def run_key(intent: str, stage: str) -> str:
    """Return the key of a stage's run header in `runs`: the intent's record directory and the stage's id."""
    # ponytail: a record directory at the repository root is "", which gives a leading slash that `--intent ""` cannot
    # name; give the root a name here if a repository ever keeps its state file there
    return f"{intent}/{stage}"


def utc_timestamp(now: datetime | None = None) -> str:
    """Return now, or the current time, in UTC to the second as `YYYY-MM-DDTHH:MM:SSZ`."""
    return (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _refuse_symlink(root: Path) -> None:
    """Raise OSError when `.earnest` or the record file is a symlink, which sends the record out of the repository."""
    for link in (root / ".earnest", root / RECORD):
        if link.is_symlink():
            msg = f"{link.relative_to(root).as_posix()} is a symlink; the record must lie in the repository"
            raise OSError(msg)


def read_record(root: Path) -> Record:
    """Return the assessment record under root; a missing file is the empty record.

    Raises:
        RecordError: the file does not parse, has the wrong shape, or has a newer `version` than this release reads.
        OSError: the file cannot be read, or `.earnest` or the record file is a symlink.
    """
    _refuse_symlink(root)
    try:
        record = _record(json.loads((root / RECORD).read_text(encoding="utf-8")))
    except FileNotFoundError:
        return Record()
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError) as error:  # UnicodeDecodeError: ValueError
        msg = f"{RECORD} is not an assessment record: {type(error).__name__}: {error}"
        raise RecordError(msg) from error
    return record


def write_record(root: Path, record: Record) -> None:
    """Replace the assessment record under root with record, whole or not at all.

    The text goes to a temporary file in `.earnest/` and replaces the record, so a crash or a second writer leaves a
    whole file. A new `.earnest/` gets a `.gitignore` holding `*`; an existing one is left as it is.

    Raises:
        OSError: the directory or the file cannot be written, or `.earnest` or the record file is a symlink; the old
            record stays and no temporary file does.
    """
    _refuse_symlink(root)
    directory = root / ".earnest"
    created = not directory.exists()
    directory.mkdir(exist_ok=True)
    if created:
        (directory / ".gitignore").write_text("*\n", encoding="utf-8")
    body = {
        **record.extra,
        "version": VERSION,
        "runs": {key: _header_json(held) for key, held in record.runs.items()},
        "bodies": record.bodies,
        "coverage": record.coverage,
        "judge": record.judge,
        "calibration": record.calibration,
    }
    # ponytail: mkstemp makes the file mode 0600 (Git tracks 100644 either way), and a write that fails after the
    # directory is new leaves its `.gitignore` behind; chmod and clean up if either ever matters
    descriptor, name = tempfile.mkstemp(dir=directory, prefix="assessment.", suffix=".tmp")
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(canonical(body, pretty=True))
        temp.replace(root / RECORD)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _integers_only(obj: object) -> None:
    if isinstance(obj, float):
        msg = f"canonical JSON holds integers only, not {obj!r}"
        raise TypeError(msg)
    if isinstance(obj, Mapping):
        for value in obj.values():
            _integers_only(value)
    elif isinstance(obj, list | tuple):
        for value in obj:
            _integers_only(value)


def _record(data: object) -> Record:
    # ponytail: shallow validation, so `version: true` or a non-string body hash passes; type-check every field when
    # something other than Earnest writes the record
    if not isinstance(data, dict) or not isinstance(data["version"], int) or data["version"] < 1:
        msg = "the file is not a JSON object with a version"
        raise TypeError(msg)
    if data["version"] > VERSION:
        msg = f"{RECORD} has version {data['version']}, and this release reads up to version {VERSION}: update earnest"
        raise RecordError(msg)
    _integers_only(data)  # a float would pass the read and crash the next write
    return Record(
        version=data["version"],
        runs={key: _header(held) for key, held in data["runs"].items()},
        bodies=dict(data["bodies"]),
        coverage=dict(data["coverage"]),
        judge=dict(data["judge"]),
        calibration=None if data["calibration"] is None else dict(data["calibration"]),
        extra={key: value for key, value in data.items() if key not in _KNOWN},
    )


def _header(held: Mapping[str, Any]) -> RunHeader:
    return RunHeader(
        intent=held["intent"],
        stage=held["stage"],
        commit=held["commit"],
        dirty=held["dirty"],
        timestamp=held["timestamp"],
        layers=tuple(held["layers"]),
        model=held["model"],
        prompt=held["prompt"],
        items=tuple(held["items"]),
        status=held["status"],
        reasons=dict(held["reasons"]),
        digest=held["hash"],
    )


def _header_json(held: RunHeader) -> dict[str, object]:
    return {
        "intent": held.intent,
        "stage": held.stage,
        "commit": held.commit,
        "dirty": held.dirty,
        "timestamp": held.timestamp,
        "layers": list(held.layers),
        "model": held.model,
        "prompt": held.prompt,
        "items": list(held.items),
        "status": held.status,
        "reasons": dict(held.reasons),
        "hash": held.digest,
    }
