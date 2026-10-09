"""Reporter: the SARIF 2.1.0 log, with each requirement's trace level, and the summary that leads with three percentages."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import quote


RULES = {
    "earnest/duplicate": "error",
    "earnest/gap": "error",
    "earnest/near-miss": "error",
    "earnest/orphaned": "error",
    "earnest/outdated": "error",
    "earnest/predated": "error",
    "earnest/unwanted": "warning",
}
LEVELS = ("untraced", "traced", "judged", "evidenced")
_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"


@dataclass(frozen=True, order=True)
class Finding:
    """A located result: file, line, rule, the id or text it is about, and a message that names the change to make."""

    path: str
    line: int
    rule: str
    subject: str
    message: str

    @property
    def level(self) -> str:
        """Return the SARIF level of the finding's rule."""
        return RULES[self.rule]

    @property
    def text(self) -> str:
        """Return the message as it is reported, opening with the finding's position."""
        # ponytail: no finding reaches a stage until stages exist, so each sits at position current, `in scope`.
        return f"in scope: {self.message}"


def percentages(levels: Mapping[str, str]) -> dict[str, int]:
    """Return the share of requirements at each level or above, in whole percent rounded down, so 100 means all."""
    ranks = [LEVELS.index(level) for level in levels.values()]
    shares: dict[str, int] = {}
    for rank, name in enumerate(LEVELS[1:], start=1):
        reached = sum(1 for value in ranks if value >= rank)
        shares[name] = 100 * reached // len(ranks) if ranks else 0
    return shares


def sarif(findings: Sequence[Finding], levels: Mapping[str, str], commit: str) -> str:
    """Return one SARIF 2.1.0 log; it holds no timestamp, so an unchanged repository gives the same bytes."""
    run = {
        "tool": {"driver": {"name": "earnest"}},
        "invocations": [{"executionSuccessful": True, "properties": {"commit": commit, "layers": ["trace"]}}],
        "results": [_result(finding) for finding in sorted(findings)],
        "properties": {"traceLevels": dict(levels), "percentages": percentages(levels)},
    }
    log = {"$schema": _SCHEMA, "version": "2.1.0", "runs": [run]}
    return json.dumps(log, sort_keys=True, separators=(",", ":")) + "\n"


def summary(findings: Sequence[Finding], levels: Mapping[str, str]) -> str:
    """Return the human summary: the three percentages, each requirement's level, then each finding."""
    shares = percentages(levels)
    head = (
        f"traced {shares['traced']}%, judged {shares['judged']}%, evidenced {shares['evidenced']}%;"
        f" requirements: {len(levels)}"
    )
    lines = [
        head,
        *(f"  {req}: {level}" for req, level in sorted(levels.items())),
        *(f"{f.path}:{f.line}: {f.level} {f.rule}: {f.text}" for f in sorted(findings)),
    ]
    errors = sum(1 for finding in findings if finding.level == "error")
    lines.append(f"findings: {len(findings)}, errors: {errors}")
    return "\n".join(lines) + "\n"


def _result(finding: Finding) -> dict[str, object]:
    uri = quote(finding.path, errors="surrogateescape")  # Git hands over names that are not UTF-8 as surrogates
    location = {"artifactLocation": {"uri": uri}, "region": {"startLine": finding.line}}
    observation = {
        "method": "trace",
        "subject": finding.subject,
        "result": finding.rule.removeprefix("earnest/"),
        "reasoning": finding.message,
        "location": location,
    }
    return {
        "ruleId": finding.rule,
        "level": finding.level,
        "message": {"text": finding.text},
        "locations": [{"physicalLocation": location}],
        "properties": {"position": "current", "observations": [observation]},
    }
