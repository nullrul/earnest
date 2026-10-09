"""Shared fixtures: every test's Git shut off from the user's, and fixture repositories committed in tmp_path."""

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest


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


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Callable[[str], Path]:
    """Return a builder that copies tests/fixtures/<name> into tmp_path and commits it on main."""

    def build(name: str) -> Path:
        repo = tmp_path / name
        shutil.copytree(FIXTURES / name, repo)
        return _commit(repo)

    return build
