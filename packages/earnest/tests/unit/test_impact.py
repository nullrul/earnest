"""Tests for earnest.impact: the coverage map that a stage check takes, and the impact it selects."""

import json
import sys

import pytest

from earnest import adapters, git, impact
from earnest.git import Hunk
from earnest.index import Source, build_index
from tests.sarif import git_output


PROJECT = {
    "pytest.ini": "[pytest]\npythonpath = src\n",
    "src/pkg/__init__.py": "",
    "src/pkg/core.py": "def one():\n    return 1\n\n\ndef two():\n    return 2\n",
    "tests/test_nested.py": (
        "class TestOuter:\n    def test_method(self):\n        def test_inner():\n            pass\n\n"
        "        test_inner()\n"
    ),
    "tests/test_core.py": (
        "from pkg.core import one, two\n\n\ndef test_one():\n    assert one() == 1\n\n\ndef test_two():\n"
        "    assert two() == 2\n\n\ndef test_both():\n    assert one() + two() == 3\n"
    ),
}


def taken(repo):
    commit = git.head_commit(repo)
    (repo / ".earnest").mkdir()
    (repo / ".earnest" / ".gitignore").write_text("*\n", encoding="utf-8")
    assert impact.take_map(repo, commit) is None
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


def untaken(repo, **options):
    commit = git.head_commit(repo)
    (repo / ".earnest").mkdir(exist_ok=True)
    (repo / ".earnest" / ".gitignore").write_text("*\n", encoding="utf-8")
    reason = impact.take_map(repo, commit, **options)
    assert impact.read_map(repo, commit) is None
    assert not impact.map_file(repo, commit).exists()
    assert sorted(path.name for path in (repo / ".earnest" / "coverage").iterdir()) == []
    return reason


def test_a_repository_without_tests_gives_no_map_and_says_why(files_repo):
    repo = files_repo({"a.md": "a\n"})
    assert untaken(repo) == "pytest exited 5 (no tests collected)"
    assert git_output(repo, "status", "--porcelain", "--untracked-files=all") == ""


def fake_python(tmp_path, script):
    fake = tmp_path / "python"
    fake.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
    fake.chmod(0o755)
    return str(fake)


def test_an_interpreter_without_pytest_gives_no_map_and_says_why(files_repo, tmp_path):
    reason = untaken(files_repo(PROJECT), python=fake_python(tmp_path, "exit 1"))
    assert reason == "the test run gave no coverage data"


@pytest.mark.parametrize(("code", "meaning"), [(2, "interrupted"), (3, "internal error"), (4, "usage error")])
def test_pytest_exit_codes_2_to_5_give_no_map(files_repo, tmp_path, code, meaning):
    reason = untaken(files_repo(PROJECT), python=fake_python(tmp_path, f"exit {code}"))
    assert reason == f"pytest exited {code} ({meaning})"


def test_a_test_run_that_times_out_gives_no_map_and_says_so(files_repo, tmp_path, monkeypatch):
    monkeypatch.setattr(impact, "MAP_TIMEOUT", 1)
    reason = untaken(files_repo(PROJECT), python=fake_python(tmp_path, "sleep 5"))
    assert reason == "the test run timed out after 1 s"


def test_a_failed_run_leaves_an_earlier_map_at_the_commit_as_it_was(files_repo, tmp_path):
    repo = files_repo(PROJECT)
    commit = taken(repo)
    before = impact.read_map(repo, commit)
    assert impact.take_map(repo, commit, python=fake_python(tmp_path, "exit 4")) is not None
    assert impact.read_map(repo, commit) == before


def test_the_map_run_reads_no_stdin_and_has_a_generous_timeout(files_repo, tmp_path):
    assert impact.MAP_TIMEOUT == 900
    repo = files_repo(
        {**PROJECT, "tests/test_stdin.py": "import sys\n\n\ndef test_stdin():\n    assert sys.stdin.read() == ''\n"}
    )
    assert impact.read_map(repo, taken(repo))[("src/pkg/core.py", 2)]


def test_the_map_run_turns_off_the_repositorys_log_file(files_repo):
    repo = files_repo({**PROJECT, "pytest.ini": "[pytest]\npythonpath = src\nlog_file = run.log\n"})
    taken(repo)
    assert not (repo / "run.log").exists()


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


# Selection by the Impact rule.

BASE = "d" * 40
CODE = (
    "X = 0\n"  # 1: before every tag
    "# [impl->req~a~1]\n"  # 2
    "def a():\n"  # 3
    "    return 1\n"  # 4
    "\n"  # 5
    "# [impl->dsn~b~1]\n"  # 6
    "def b():\n"  # 7
    "    return 2\n"  # 8
)
TESTS = (
    "# [utest->req~a~2]\n"  # 1: another revision, matched on type and name
    "def test_a():\n"
    "    pass\n"
    "# [utest->dsn~b~1]\n"  # 4
    "class TestB:\n"
    "    def test_b(self):\n"
    "        pass\n"
)
SPEC = "`feat~f~1`\n\nF.\n\n`req~a~1`\n\nA.\n\nCovers: feat~f~1\n\n`dsn~b~1`\n\nB.\n\nCovers: req~a~1\n"
FILES = {"src/m.py": CODE, "tests/test_m.py": TESTS, "docs/spec.md": SPEC}


def selected(tmp_path, hunks, coverage, since_map=None):
    for path, text in FILES.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")
    index = build_index(adapters.scan(tmp_path, sorted(FILES)))
    change = impact.Change(hunks, BASE, hunks if since_map is None else since_map)
    return impact.select(tmp_path, index, change, coverage)


MAP = {("src/m.py", 4): ("tests/test_m.py::test_a",), ("src/m.py", 8): ("tests/test_m.py::TestB::test_b",)}


def test_a_modified_line_selects_the_tests_the_map_saw_run_its_paired_base_line(tmp_path):
    found = selected(tmp_path, {"src/m.py": (Hunk(4, 1, 4, 1),)}, MAP)
    assert found.impact.tests == ("tests/test_m.py::test_a",)
    assert (found.impact.degraded, found.degraded, found.impact.mapped) == (False, (), True)
    assert found.impact.requirements == ("req~a~1",)
    assert found.impact.features == ("feat~f~1",)


def test_an_unseen_line_in_a_tag_region_selects_the_tests_tagged_on_type_and_name(tmp_path):
    found = selected(tmp_path, {"src/m.py": (Hunk(4, 0, 5, 1),)}, MAP)  # line 5 is added, beyond the pairing
    assert found.impact.tests == ("tests/test_m.py::test_a",)
    assert not found.impact.degraded


def test_a_tag_region_of_a_design_names_the_requirement_it_covers_and_selects_a_test_method(tmp_path):
    found = selected(tmp_path, {"src/m.py": (Hunk(7, 1, 7, 1),)}, None)
    assert found.impact.tests == ("tests/test_m.py::TestB::test_b",)
    assert found.impact.requirements == ("req~a~1",)
    assert found.impact.features == ("feat~f~1",)
    assert not found.impact.mapped


def test_a_line_in_no_tag_region_selects_the_full_suite_and_is_degraded_blank_lines_included(tmp_path):
    found = selected(tmp_path, {"src/m.py": (Hunk(1, 1, 1, 1),), "docs/spec.md": (Hunk(2, 1, 2, 2),)}, MAP)
    assert found.degraded == (("docs/spec.md", 2), ("docs/spec.md", 3), ("src/m.py", 1))
    assert found.impact.tests == ("tests/test_m.py::TestB::test_b", "tests/test_m.py::test_a")
    assert found.impact.degraded
    assert found.impact.requirements == ()


def test_without_a_map_the_full_suite_is_no_test_and_degraded(tmp_path):
    found = selected(tmp_path, {"src/m.py": (Hunk(1, 1, 1, 1),)}, None)
    assert (found.impact.tests, found.impact.degraded, found.impact.mapped) == ((), True, False)
    assert "  tests: the full suite" in found.impact.lines()


def test_a_line_is_remapped_through_the_hunks_since_the_maps_commit(tmp_path):
    # since the map, two lines were added at the top, so line 6 now was line 4 then
    found = selected(tmp_path, {"src/m.py": (Hunk(6, 1, 6, 1),)}, MAP, since_map={"src/m.py": (Hunk(0, 0, 1, 2),)})
    assert found.impact.tests == ("tests/test_m.py::test_a",)


def test_a_deleted_line_selects_nothing(tmp_path):
    found = selected(tmp_path, {"src/m.py": (Hunk(4, 1, 3, 0),)}, MAP)
    assert found.impact.tests == ()
    assert found.degraded == ()


def test_only_python_test_files_give_node_ids(tmp_path):
    (tmp_path / "f.feature").write_text("@stest:req~a~1\nScenario: x\n", encoding="utf-8")
    index = build_index([*adapters.scan(tmp_path, ["f.feature"]), Source("x.md", "markdown", ())])
    assert impact.tagged_tests(tmp_path, index, {("req", "a")}) == []


def test_a_def_nested_inside_a_test_method_is_no_test(tmp_path):
    (tmp_path / "tests").mkdir()
    text = "# [utest->req~a~1]\nclass TestOuter:\n    def test_method(self):\n        def test_inner():\n            pass\n"
    (tmp_path / "tests" / "test_n.py").write_text(text, encoding="utf-8")
    index = build_index(adapters.scan(tmp_path, ["tests/test_n.py"]))
    assert impact.tagged_tests(tmp_path, index, {("req", "a")}) == ["tests/test_n.py::TestOuter::test_method"]
