"""Helpers the tests share: the one run in a SARIF log, the earnest command, Git, a data table as rows, and the seeded paths."""

import json
import subprocess
import sys
from pathlib import Path


EARNEST = Path(sys.executable).with_name("earnest")
RECORD = "aidlc/spaces/default/intents/260926-checkout"  # the intent directory of the seeded-change fixture
SHARD = f"{RECORD}/audit/fixture-a1b2c3d4.md"
REQUIREMENTS = f"{RECORD}/inception/requirements-analysis/requirements.md"
PLAN_FILE = f"{RECORD}/construction/code-generation/code-generation-plan.md"


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
