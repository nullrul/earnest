"""Reporter: the SARIF 2.1.0 log, with each requirement's trace level, and the summary that leads with three percentages."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, cast
from urllib.parse import quote


RuleId = Literal[
    "earnest/cycle",
    "earnest/duplicate",
    "earnest/gap",
    "earnest/near-miss",
    "earnest/orphaned",
    "earnest/outdated",
    "earnest/predated",
    "earnest/route-mismatch",
    "earnest/unbumped-change",
    "earnest/unplanned",
    "earnest/unwanted",
]
Position = Literal["behind", "current", "ahead"]
RULES: dict[RuleId, str] = {
    "earnest/cycle": "error",
    "earnest/duplicate": "error",
    "earnest/gap": "error",
    "earnest/near-miss": "error",
    "earnest/orphaned": "error",
    "earnest/outdated": "error",
    "earnest/predated": "error",
    "earnest/route-mismatch": "error",
    "earnest/unbumped-change": "error",
    "earnest/unplanned": "warning",
    "earnest/unwanted": "warning",
}
LEVELS = ("untraced", "traced", "judged", "evidenced")
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
    body = {
        "tool": {"driver": {"name": "earnest"}},
        "invocations": [
            {
                "executionSuccessful": True,
                "properties": {"commit": run.commit, "dirty": run.dirty, "layers": ["trace"]},
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
    return lines


def _intent_lines(entry: Mapping[str, Any]) -> list[str]:
    lines = [f"intent {entry['intent']}"]
    for stage in entry["stages"]:
        by = stage["approvedBy"] if stage["approval"] == "current" else None
        approval = f"{stage['approval']}, {by}" if by else stage["approval"]
        lines.append(f"  {stage['stage']}: {stage['status']}, approval {approval}")
    lines.append(f"  frontier: {entry['frontier'] or 'none'}")
    lines.extend(f"  task {task['id']}: {task['status']}" for task in entry["tasks"])
    lines.extend(f"  unit {unit['id']}: {unit['status']}" for unit in entry["units"])
    return lines


def _result(finding: Finding) -> dict[str, object]:
    location = {"artifactLocation": {"uri": uri(finding.path)}, "region": {"startLine": finding.line}}
    observation = {
        "method": "trace",
        "subject": finding.subject,
        "result": finding.rule.removeprefix("earnest/"),
        "reasoning": finding.message,
        "location": location,
    }
    properties: dict[str, object] = {"position": finding.position, "observations": [observation]}
    if finding.stage is not None:
        properties["stage"] = finding.stage
    return {
        "ruleId": finding.rule,
        "level": finding.level,
        "message": {"text": finding.text},
        "locations": [{"physicalLocation": location}],
        "properties": properties,
    }
