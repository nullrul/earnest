"""Shared fixtures: every test's Git shut off from the user's, and fixture repositories committed in tmp_path."""

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_bdd import then

from tests.sarif import located, rows, sarif_run, write


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


def _leave_out_change(root: Path) -> Callable[[str, list[str]], list[str]]:
    """Return a copytree ignore that leaves out the `change/` overlay at the top of the fixture at root."""

    def ignore(directory: str, names: list[str]) -> list[str]:
        return ["change"] if Path(directory) == root and "change" in names else []

    return ignore


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Callable[[str], Path]:
    """Return a builder that copies tests/fixtures/<name>, less its `change/` overlay, into tmp_path and commits it."""

    def build(name: str) -> Path:
        repo = tmp_path / name
        shutil.copytree(FIXTURES / name, repo, ignore=_leave_out_change(FIXTURES / name))
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


# What each column of a findings table reads from a SARIF result.
_COLUMNS = {
    "rule": lambda result: result["ruleId"],
    "file": lambda result: located(result)[0],
    "line": lambda result: located(result)[1],
    "level": lambda result: result["level"],
    "position": lambda result: result["properties"]["position"],
    "stage": lambda result: result["properties"].get("stage"),
}


@then("the SARIF log holds exactly these findings:")
def exact_findings(run, datatable):
    table = rows(datatable)
    columns = list(table[0])
    expected = [tuple(int(row[c]) if c == "line" else row[c] for c in columns) for row in table]
    actual = [tuple(_COLUMNS[c](result) for c in columns) for result in sarif_run(run.stdout)["results"]]
    assert sorted(actual, key=repr) == sorted(expected, key=repr)


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
