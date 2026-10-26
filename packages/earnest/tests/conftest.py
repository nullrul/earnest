"""Shared fixtures: every test's Git shut off from the user's, and fixture repositories committed in tmp_path."""

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, then, when

from tests.sarif import (
    RECORD,
    append_block,
    approval_text,
    git_output,
    header,
    intent_plan,
    located,
    printed_hash,
    record,
    rows,
    run_earnest,
    sarif_run,
    write,
)


collect_ignore = ["fixtures"]  # fixture repositories are data, and their tests are not this package's

FIXTURES = Path(__file__).parent / "fixtures"
# Pinned names and dates give a fixture commit the same sha on every run, and M4's overrides name that sha.
_IDENTITY = {
    "GIT_AUTHOR_NAME": "Earnest Fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.com",
    "GIT_AUTHOR_DATE": "2026-09-26T12:00:00+00:00",
    "GIT_COMMITTER_NAME": "Earnest Fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.com",
    "GIT_COMMITTER_DATE": "2026-09-26T12:00:00+00:00",
}


@pytest.fixture(autouse=True)
def _isolated_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shut every Git a test runs, earnest's own included, off from the user's configuration and GIT_ variables."""
    # a Git hook that runs the tests sets GIT_DIR and GIT_INDEX_FILE; GIT_EXEC_PATH only says where Git's helpers live
    for name in list(os.environ):
        if name.startswith("GIT_") and name != "GIT_EXEC_PATH":
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("XDG_CONFIG_HOME", os.devnull)  # keeps the default core.excludesFile and core.attributesFile out
    monkeypatch.setenv("GIT_ATTR_NOSYSTEM", "1")


def _git(repo: Path, *args: str) -> None:
    """Run git in repo as the fixture's pinned author and committer."""
    subprocess.run(["git", *args], cwd=repo, env=os.environ | _IDENTITY, capture_output=True, check=True)


def _commit(repo: Path) -> Path:
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "fixture")
    return repo


# the fixture paths that no base commit holds; the verdict files stay in the package, outside the repository
_OVERLAYS = (
    "change",
    "task",
    "units",
    "override",
    "override-change",
    "evidence",
    "evidence-units",
    "judge-verdicts.json",
    "evidence-verdicts.json",
)


def _leave_out(root: Path, *paths: str) -> Callable[[str, list[str]], list[str]]:
    """Return a copytree ignore that leaves out the given paths, relative to root, of the fixture at root, and any bytecode."""
    bytecode = shutil.ignore_patterns("__pycache__", "*.pyc")

    def ignore(directory: str, names: list[str]) -> list[str]:
        here = Path(directory).relative_to(root)
        return [name for name in names if (here / name).as_posix() in paths] + list(bytecode(directory, names))

    return ignore


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Callable[[str], Path]:
    """Return a builder that copies tests/fixtures/<name>, less its overlays and canned verdicts, and commits it."""

    def build(name: str) -> Path:
        repo = tmp_path / name
        shutil.copytree(FIXTURES / name, repo, ignore=_leave_out(FIXTURES / name, *_OVERLAYS))
        return _commit(repo)

    return build


@pytest.fixture
def units_repo(tmp_path: Path) -> Callable[[], Path]:
    """Return a builder of seeded-change's units variant: the base files with the record taken from `units/aidlc/`."""

    def build() -> Path:
        source = FIXTURES / "seeded-change"
        repo = tmp_path / "seeded-change"
        shutil.copytree(source, repo, ignore=_leave_out(source, *_OVERLAYS, RECORD))
        shutil.copytree(source / "units" / "aidlc", repo / "aidlc", dirs_exist_ok=True)
        return _commit(repo)

    return build


@pytest.fixture
def files_repo(tmp_path: Path) -> Callable[[dict[str, str]], Path]:
    """Return a builder that writes the given files into tmp_path / "repo" and commits them on main."""

    def build(files: dict[str, str]) -> Path:
        repo = tmp_path / "repo"
        for path, text in files.items():
            write(repo, path, text)
        return _commit(repo)

    return build


@pytest.fixture
def commit_overlay() -> Callable[[Path, str, str], Path]:
    """Return a builder that commits a fixture's `change/` overlay, and only its files, on a new branch of repo."""

    def commit(repo: Path, name: str, branch: str) -> Path:
        overlay = FIXTURES / name / "change"
        files = sorted(str(path.relative_to(overlay)) for path in overlay.rglob("*") if path.is_file())
        _git(repo, "checkout", "-q", "-b", branch)
        shutil.copytree(overlay, repo, dirs_exist_ok=True)
        _git(repo, "add", "--", *files)
        _git(repo, "commit", "-q", "--no-verify", "-m", "change")
        return repo

    return commit


def _overlay_files(name: str, overlay: str) -> list[str]:
    root = FIXTURES / name / overlay
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


def write_overlays(repo: Path, name: str, *overlays: str) -> list[str]:
    """Copy a fixture's overlays into repo's work tree, in order, and return the paths they write."""
    written: list[str] = []
    for overlay in overlays:
        shutil.copytree(FIXTURES / name / overlay, repo, dirs_exist_ok=True)
        written.extend(_overlay_files(name, overlay))
    return written


def commit_on_main(repo: Path, name: str, overlay: str) -> Path:
    """Commit a fixture's overlay, and only its files, on main, on top of HEAD; no branch is made."""
    files = write_overlays(repo, name, overlay)
    _git(repo, "add", "--", *files)
    _git(repo, "commit", "-q", "--no-verify", "-m", overlay)
    return repo


@pytest.fixture
def commit_task_change(commit_overlay) -> Callable[[Path, str], Path]:
    """Return a builder that commits seeded-change's `change/` overlay, then its `task/` overlay, on a new branch."""

    def commit(repo: Path, branch: str) -> Path:
        commit_overlay(repo, "seeded-change", branch)
        files = write_overlays(repo, "seeded-change", "task")
        _git(repo, "add", "--", *files)
        _git(repo, "commit", "-q", "--no-verify", "-m", "task")
        return repo

    return commit


# What each column of a findings table reads from a SARIF result.
_COLUMNS = {
    "rule": lambda result: result["ruleId"],
    "file": lambda result: located(result)[0],
    "line": lambda result: located(result)[1],
    "level": lambda result: result["level"],
    "position": lambda result: result["properties"]["position"],
    "stage": lambda result: result["properties"].get("stage"),
}


def location_cell(location):
    """Return a SARIF physical location as a `location` cell reads it: `<file>:<line>`."""
    return f"{location['artifactLocation']['uri']}:{location['region']['startLine']}"


# The same, with the file relative to the intent's record; a result outside the record keeps its full path.
_RECORD_COLUMNS = _COLUMNS | {"file": lambda result: located(result)[0].removeprefix(f"{RECORD}/")}


def _cell(column, text):
    """Return a table cell as the column reads it: a line as a number, and `-` in `stage` as no stage."""
    if column == "line":
        return int(text)
    return None if column == "stage" and text == "-" else text


def _exact(run, datatable, read_column):
    table = rows(datatable)
    columns = list(table[0])
    expected = [tuple(_cell(c, row[c]) for c in columns) for row in table]
    actual = [tuple(read_column[c](result) for c in columns) for result in sarif_run(run.stdout)["results"]]
    assert sorted(actual, key=repr) == sorted(expected, key=repr)


@then("the SARIF log holds exactly these findings:")
def exact_findings(run, datatable):
    _exact(run, datatable, _COLUMNS)


@then("the SARIF log holds exactly these findings in the intent's record:")
def exact_findings_in_record(run, datatable):
    _exact(run, datatable, _RECORD_COLUMNS)


@then("both runs write the same SARIF log")
def same_log(runs):
    first, second = runs
    assert json.loads(first.stdout)["version"] == "2.1.0"
    assert first.stdout == second.stdout


@then("the check exits zero")
def exits_zero(run):
    assert run.returncode == 0, run.stderr


@then("the check exits non-zero")
def exits_non_zero(run):
    assert run.returncode == 1, run.stderr
    assert sarif_run(run.stdout)["results"]


# The steps the stage_status and unit_status features share.


@pytest.fixture
def memory():
    """What a scenario remembers between steps: the stage, hash and bodies of its first stage check, a jump's target."""
    return {}


@given(parsers.parse('the coding agent has run earnest check --stage "{stage}"'))
def agent_has_run_stage_check(repo, memory, stage):
    run = run_earnest(repo, "check", "--stage", stage)
    assert run.returncode != 2, run.stderr  # the run happened: a missing command or a refusal exits 2
    header(repo, stage)  # and the record holds that stage's run header
    memory["stage"] = stage
    memory.setdefault("hash", printed_hash(run))
    memory.setdefault("bodies", record(repo)["bodies"])


@given(parsers.parse('the repo maintainer approves "{stage}" at the gate'))
def approve_at_gate(repo, stage):
    held = header(repo, stage)
    fields = [
        ("Stage", stage.split("/")[1]),
        ("User Input", "Approve"),
        ("Assessment Hash", held["hash"]),
        ("Items", ", ".join(held["items"])),
        ("Approved By", "human"),
    ]
    append_block(repo, "GATE_APPROVED", "2026-09-26T12:00:00Z", fields)


@when("the coding agent runs earnest plan", target_fixture="run")
def agent_runs_plan(repo):
    return run_earnest(repo, "plan")


@when("the coding agent runs earnest check", target_fixture="run")
def agent_runs_check(repo):
    return run_earnest(repo, "check")


@when(parsers.parse('the coding agent runs earnest check --stage "{stage}"'), target_fixture="run")
def agent_runs_stage_check(repo, memory, stage):
    memory["stage"] = stage
    return run_earnest(repo, "check", "--stage", stage)


@then("the plan lists these stages in route order:")
def plan_lists_stages(run, datatable):
    actual = [(stage["stage"], stage["status"], approval_text(stage)) for stage in intent_plan(run)["stages"]]
    assert actual == [(row["stage"], row["status"], row["approval"]) for row in rows(datatable)]


@then(parsers.parse('the frontier is "{stage}"'))
def frontier_is(run, stage):
    assert intent_plan(run)["frontier"] == stage


@then("the plan lists these tasks:")
def plan_lists_tasks(run, datatable):
    actual = [(task["id"], task["status"]) for task in intent_plan(run)["tasks"]]
    assert actual == [(row["task"], row["status"]) for row in rows(datatable)]


@then(parsers.re(r'the plan lists "(?P<first>[^"]+)"(?: and "(?P<second>[^"]+)")? among the stages'))
def plan_lists_stage(run, first, second):
    stages = [stage["stage"] for stage in intent_plan(run)["stages"]]
    assert first in stages
    assert second is None or second in stages


@then(parsers.parse('"{stage}" has the approval "{approval}"'))
def stage_has_approval(run, stage, approval):
    assert {entry["stage"]: approval_text(entry) for entry in intent_plan(run)["stages"]}[stage] == approval


@then("no assessment record exists")
def no_record(repo):
    assert not (repo / ".earnest").exists()


@then("the summary prints the assessment hash")
def summary_prints_hash(run):
    printed_hash(run)


@then('the SARIF log gives the same hash and the stage status "not done"')
def sarif_gives_hash_and_status(run):
    assessment = sarif_run(run.stdout)["properties"]["assessment"]
    assert assessment["hash"] == printed_hash(run)
    assert assessment["status"] == "not done"


@then(parsers.parse('the run header for "{stage}" in the assessment record holds:'))
def run_header_holds(repo, run, stage, datatable):
    held = header(repo, stage)
    for row in rows(datatable):
        field, value = row["field"], row["value"]
        actual = held[field]
        if field == "commit":
            value = git_output(repo, "rev-parse", "HEAD").strip()
        elif field == "hash":
            value = printed_hash(run)
        elif field == "dirty":
            value = value == "true"
        elif field in {"layers", "items"}:
            actual = ", ".join(actual)
        assert actual == value, field


@then("Git lists no new file")
def git_lists_no_new_file(repo):
    assert git_output(repo, "ls-files", "--others", "--exclude-standard") == ""


@then(parsers.parse("the {command} exits with code 2, with empty stdout"))
def exits_with_code_two(run, command):
    assert command in {"plan", "check"}
    assert (run.returncode, run.stdout) == (2, "")
