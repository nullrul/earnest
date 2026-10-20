"""Tests for earnest.impact: the coverage map that a stage check takes, and the impact it selects."""

import json
import sys

import pytest

from earnest import git, impact
from tests.sarif import git_output


PROJECT = {
    "pytest.ini": "[pytest]\npythonpath = src\n",
    "src/pkg/__init__.py": "",
    "src/pkg/core.py": "def one():\n    return 1\n\n\ndef two():\n    return 2\n",
    "tests/test_core.py": (
        "from pkg.core import one, two\n\n\ndef test_one():\n    assert one() == 1\n\n\ndef test_two():\n"
        "    assert two() == 2\n\n\ndef test_both():\n    assert one() + two() == 3\n"
    ),
}


def taken(repo):
    commit = git.head_commit(repo)
    (repo / ".earnest").mkdir()
    (repo / ".earnest" / ".gitignore").write_text("*\n", encoding="utf-8")
    impact.take_map(repo, commit)
    return commit


def test_take_map_keeps_the_data_file_under_the_commit_and_writes_nothing_else(files_repo):
    repo = files_repo(PROJECT)
    commit = taken(repo)
    assert impact.map_file(repo, commit).is_file()
    ignored = git_output(repo, "status", "--porcelain", "--untracked-files=all", "--ignored").splitlines()
    assert all(line.startswith("!! .earnest/") for line in ignored), ignored
    assert not list(repo.rglob("__pycache__"))
    assert sorted(path.name for path in (repo / ".earnest" / "coverage").iterdir()) == [commit, f"{commit}.json"]


def test_read_map_gives_each_line_the_sorted_node_ids_that_ran_it(files_repo):
    repo = files_repo(PROJECT)
    found = impact.read_map(repo, taken(repo))
    assert found[("src/pkg/core.py", 2)] == ("tests/test_core.py::test_both", "tests/test_core.py::test_one")
    assert found[("src/pkg/core.py", 6)] == ("tests/test_core.py::test_both", "tests/test_core.py::test_two")
    assert ("src/pkg/core.py", 1) not in found  # run at import, under the empty context of collection
    assert found[("tests/test_core.py", 5)] == ("tests/test_core.py::test_one",)


def test_a_failing_test_still_gives_a_map(files_repo):
    repo = files_repo(
        {**PROJECT, "tests/test_fail.py": "from pkg.core import one\n\n\ndef test_fails():\n    assert one() == 2\n"}
    )
    found = impact.read_map(repo, taken(repo))
    assert found[("src/pkg/core.py", 2)] == (
        "tests/test_core.py::test_both",
        "tests/test_core.py::test_one",
        "tests/test_fail.py::test_fails",
    )


def test_a_repository_without_tests_gives_an_empty_map(files_repo):
    repo = files_repo({"a.md": "a\n"})
    assert impact.read_map(repo, taken(repo)) == {}
    assert git_output(repo, "status", "--porcelain", "--untracked-files=all") == ""


def test_an_interpreter_without_pytest_gives_an_empty_map(files_repo, tmp_path):
    repo = files_repo(PROJECT)
    commit = git.head_commit(repo)
    fake = tmp_path / "python"
    fake.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    fake.chmod(0o755)
    impact.take_map(repo, commit, python=str(fake))
    assert impact.read_map(repo, commit) == {}


def test_read_map_drops_the_phase_suffix_and_the_empty_context_and_relativizes_paths(tmp_path):
    commit = "a" * 40
    (tmp_path / impact.COVERAGE).mkdir(parents=True)
    contexts = {"3": ["", "t.py::test_a|run", "t.py::test_a|setup"], "4": [""], "5": ["t.py::C::test_b|teardown"]}
    files = {"src/a.py": {"contexts": contexts}, str(tmp_path / "src" / "b.py"): {"contexts": {"1": ["t.py::x|run"]}}}
    (tmp_path / impact.COVERAGE / f"{commit}.json").write_text(json.dumps({"files": files}), encoding="utf-8")
    assert impact.read_map(tmp_path, commit) == {
        ("src/a.py", 3): ("t.py::test_a",),
        ("src/a.py", 5): ("t.py::C::test_b",),
        ("src/b.py", 1): ("t.py::x",),
    }


@pytest.mark.parametrize("text", ["{", '{"files": 3}', "[]"])
def test_a_map_that_cannot_be_read_is_no_map(tmp_path, text):
    commit = "b" * 40
    (tmp_path / impact.COVERAGE).mkdir(parents=True)
    (tmp_path / impact.COVERAGE / f"{commit}.json").write_text(text, encoding="utf-8")
    assert impact.read_map(tmp_path, commit) is None


def test_no_map_and_a_name_that_is_no_commit_read_as_no_map(tmp_path):
    assert impact.read_map(tmp_path, "c" * 40) is None
    assert impact.read_map(tmp_path, "../../etc/passwd") is None
    assert impact.read_map(tmp_path, None) is None
    with pytest.raises(ValueError, match="not a commit"):
        impact.take_map(tmp_path, "../x")


def test_the_map_run_uses_the_interpreter_that_runs_earnest():
    assert impact.take_map.__defaults__ == (sys.executable,)
