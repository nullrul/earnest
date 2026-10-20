"""Helpers the tests share: SARIF runs, the earnest command, Git, data tables, the seeded paths, audit rows and the record."""

import json
import re
import subprocess
import sys
from pathlib import Path


EARNEST = Path(sys.executable).with_name("earnest")
RECORD = "aidlc/spaces/default/intents/260926-checkout"  # the intent directory of the seeded-change fixture
SHARD = f"{RECORD}/audit/fixture-a1b2c3d4.md"
REQUIREMENTS = f"{RECORD}/inception/requirements-analysis/requirements.md"
PLAN_FILE = f"{RECORD}/construction/code-generation/code-generation-plan.md"
HASH_LINE = re.compile(r"^assessment (\S+): (sha256:[0-9a-f]{64}) \((?:done|not done)\)$", re.MULTILINE)


def sarif_run(text):
    """Return the one run of the SARIF log in text."""
    (run,) = json.loads(text)["runs"]
    return run


def located(result):
    """Return a result's file, as its percent-encoded uri, and its line."""
    location = result["locations"][0]["physicalLocation"]
    return location["artifactLocation"]["uri"], location["region"]["startLine"]


def rows(datatable):
    """Return a data table's rows as dicts keyed by its header."""
    header, *body = datatable
    return [dict(zip(header, row, strict=True)) for row in body]


def run_earnest(repo, *args):
    """Run `earnest` with args in repo, as the coding agent does, and return the finished process."""
    return subprocess.run([str(EARNEST), *args], cwd=repo, capture_output=True, text=True, check=False)


def write(repo, path, text):
    """Write text to path under repo, making its directories."""
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text, encoding="utf-8")


def git_output(repo, *args):
    """Return what `git args` prints in repo; a failing Git raises."""
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


def read(repo, path):
    return (repo / path).read_text(encoding="utf-8")


def block(event, timestamp, fields=()):
    """Return one audit block as AI-DLC writes it: a heading, Timestamp, Event, the fields, then the rule line."""
    heading = event.replace("_", " ").title()
    lines = [f"## {heading}", f"**Timestamp**: {timestamp}", f"**Event**: {event}"]
    lines += [f"**{name}**: {value}" for name, value in fields]
    return "\n".join([*lines, "---"]) + "\n"


def append_block(repo, event, timestamp, fields=()):
    write(repo, SHARD, read(repo, SHARD) + block(event, timestamp, fields))


def intent_plan(run):
    """Return the one intent's plan from the SARIF log of a `plan` run."""
    return sarif_run(run.stdout)["properties"]["plan"]["intents"][0]


def approval_text(stage):
    """Return a stage's approval as the tables write it: `current, human` for a current approval, else the bare word."""
    by = stage["approvedBy"]
    return f"current, {by}" if stage["approval"] == "current" and by else stage["approval"]


def printed_hash(run):
    match = HASH_LINE.search(run.stderr)
    assert match, run.stderr
    return match.group(2)


def record(repo):
    return json.loads(read(repo, ".earnest/assessment.json"))


def header(repo, stage):
    return record(repo)["runs"][f"{RECORD}/{stage}"]


def results(run):
    return sarif_run(run.stdout)["results"]


def record_baseline(repo, stage="inception/requirements-analysis"):
    """Record a change baseline: a stage check of stage, then its approval at the gate carrying that header's hash."""
    done = run_earnest(repo, "check", "--stage", stage)
    assert done.returncode != 2, done.stderr
    held = header(repo, stage)
    fields = [("Stage", stage.split("/")[-1]), ("Assessment Hash", held["hash"]), ("Approved By", "human")]
    append_block(repo, "GATE_APPROVED", "2026-09-27T12:00:00Z", fields)
    return held["commit"]
