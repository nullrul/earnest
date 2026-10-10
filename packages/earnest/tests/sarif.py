"""Helpers the tests share: the one run in a SARIF log, the earnest command, Git, and a data table as rows."""

import json
import subprocess
import sys
from pathlib import Path


EARNEST = Path(sys.executable).with_name("earnest")


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


def git_output(repo, *args):
    """Return what `git args` prints in repo; a failing Git raises."""
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout
