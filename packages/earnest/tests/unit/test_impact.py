"""Tests for earnest.impact: the coverage map that a stage check takes, and the impact it selects."""

import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from earnest import adapters, git, impact, judge, reporter
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


def test_a_timed_out_run_kills_the_processes_its_command_started(tmp_path, monkeypatch):
    monkeypatch.setattr(impact, "MAP_TIMEOUT", 0.5)
    pid = tmp_path / "pid"
    command = ["/bin/sh", "-c", f"sleep 60 & echo $! > {pid}; wait"]
    assert impact._process(command, tmp_path, {}) is None
    grandchild = int(pid.read_text(encoding="utf-8"))
    deadline = time.monotonic() + 5
    while _alive(grandchild) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not _alive(grandchild)


def test_a_terminated_earnest_kills_the_processes_its_command_started(tmp_path):
    pid = tmp_path / "pid"
    command = ["/bin/sh", "-c", f"sleep 60 & echo $! > {pid}; wait"]
    script = (
        "from earnest import cli, impact\n"
        f"cli._read = lambda: impact._process({command!r}, None, {{}})\n"
        "raise SystemExit(cli.main(['plan']))\n"
    )
    child = subprocess.Popen([sys.executable, "-c", script], stderr=subprocess.PIPE, text=True)
    grandchild = None
    try:
        deadline = time.monotonic() + 30
        while not (pid.exists() and pid.read_text(encoding="utf-8").strip()) and time.monotonic() < deadline:
            time.sleep(0.05)
        grandchild = int(pid.read_text(encoding="utf-8"))
        child.send_signal(signal.SIGTERM)
        _, err = child.communicate(timeout=10)
        assert child.returncode == 2
        assert err == "earnest: interrupted\n"
        deadline = time.monotonic() + 5
        while _alive(grandchild) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not _alive(grandchild)
    finally:
        child.kill()
        child.wait()
        if grandchild is not None and _alive(grandchild):
            os.kill(grandchild, signal.SIGKILL)


def test_a_terminated_earnest_exits_2_when_the_reader_of_stderr_is_gone(tmp_path):
    pid = tmp_path / "pid"
    command = ["/bin/sh", "-c", f"sleep 60 & echo $! > {pid}; wait"]
    script = (
        "from earnest import cli, impact\n"
        f"cli._read = lambda: impact._process({command!r}, None, {{}})\n"
        "raise SystemExit(cli.main(['plan']))\n"
    )
    child = subprocess.Popen([sys.executable, "-c", script], stderr=subprocess.PIPE)
    grandchild = None
    try:
        deadline = time.monotonic() + 30
        while not (pid.exists() and pid.read_text(encoding="utf-8").strip()) and time.monotonic() < deadline:
            time.sleep(0.05)
        grandchild = int(pid.read_text(encoding="utf-8"))
        child.stderr.close()
        child.send_signal(signal.SIGTERM)
        assert child.wait(timeout=10) == 2
    finally:
        child.kill()
        child.wait()
        if grandchild is not None and _alive(grandchild):
            os.kill(grandchild, signal.SIGKILL)


def test_an_error_exit_is_2_when_the_reader_of_stderr_is_gone(tmp_path):
    script = "import sys\nfrom earnest import cli\nraise SystemExit(cli.main(['check']))\n"
    child = subprocess.Popen([sys.executable, "-c", script], cwd=tmp_path, stderr=subprocess.PIPE)
    try:
        child.stderr.close()  # long before the child has imported enough to write
        assert child.wait(timeout=30) == 2
    finally:
        child.kill()
        child.wait()


@pytest.mark.parametrize("gone", [("stdout",), ("stderr",), ("stdout", "stderr")], ids="-".join)
@pytest.mark.parametrize("args", [["bogus"], [], ["--help"]], ids=["bogus", "bare", "help"])
def test_an_argparse_exit_never_becomes_120(args, gone):
    script = "import sys; from earnest import cli; raise SystemExit(cli.main(sys.argv[1:]))"
    streams = {name: subprocess.PIPE if name in gone else subprocess.DEVNULL for name in ("stdout", "stderr")}
    child = subprocess.Popen([sys.executable, "-c", script, *args], **streams)
    try:
        for name in gone:
            getattr(child, name).close()  # long before the child has imported enough to write
        assert child.wait(timeout=30) in (0, 2)
    finally:
        child.kill()
        child.wait()


def _plan_with_stdout_raising(tmp_path, raising):
    script = (
        "import errno, sys\n"
        "from earnest import cli\n"
        "class Failing:\n"
        "    def write(self, text):\n"
        f"        raise {raising}\n"
        "    def flush(self):\n"
        "        pass\n"
        "    def fileno(self):\n"
        "        return 1\n"
        "cli._read = lambda: None\n"
        "cli._plan = lambda world: cli._Result(log='log', summary='summary', code=0)\n"
        "sys.stdout = Failing()\n"
        "raise SystemExit(cli.main(['plan']))\n"
    )
    return subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False
    )


def test_a_failed_write_of_the_log_exits_2_and_says_why(tmp_path):
    child = _plan_with_stdout_raising(tmp_path, "OSError(errno.ENOSPC, 'No space left on device')")
    assert child.returncode == 2
    assert b"earnest: cannot write the result: [Errno 28] No space left on device" in child.stderr
    assert b"Traceback" not in child.stderr


def test_a_gone_reader_of_the_log_exits_2_and_stays_silent(tmp_path):
    child = _plan_with_stdout_raising(tmp_path, "BrokenPipeError(errno.EPIPE, 'Broken pipe')")
    assert child.returncode == 2
    assert child.stderr == b""


@pytest.mark.parametrize("closed", ["1", "2"])
def test_a_closed_standard_stream_exits_2_not_a_traceback(closed):
    script = "from earnest import cli; raise SystemExit(cli.main(['plan']))"
    child = subprocess.run(
        ["/bin/sh", "-c", f'exec "$0" -c "$1" {closed}>&-', sys.executable, script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert child.returncode == 2
    assert b"Traceback" not in child.stderr


def test_a_terminated_earnest_exits_2_when_the_reader_of_stdout_is_gone_with_bytes_unflushed(tmp_path):
    pid = tmp_path / "pid"
    command = ["/bin/sh", "-c", f"sleep 60 & echo $! > {pid}; wait"]
    script = (
        "import sys\n"
        "from earnest import cli, impact\n"
        f"cli._read = lambda: (sys.stdout.write('unflushed'), impact._process({command!r}, None, {{}}))\n"
        "raise SystemExit(cli.main(['plan']))\n"
    )
    child = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE)
    grandchild = None
    try:
        deadline = time.monotonic() + 30
        while not (pid.exists() and pid.read_text(encoding="utf-8").strip()) and time.monotonic() < deadline:
            time.sleep(0.05)
        grandchild = int(pid.read_text(encoding="utf-8"))
        child.stdout.close()
        child.send_signal(signal.SIGTERM)
        assert child.wait(timeout=10) == 2
    finally:
        child.kill()
        child.wait()
        if grandchild is not None and _alive(grandchild):
            os.kill(grandchild, signal.SIGKILL)


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


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


def selected(tmp_path, hunks, coverage):
    for path, text in FILES.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")
    index = build_index(adapters.scan(tmp_path, sorted(FILES)))
    change = impact.Change(hunks, BASE)
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


def test_a_line_deleted_since_the_baseline_selects_the_tests_that_covered_it_in_the_baseline_s_map(tmp_path):
    found = selected(tmp_path, {"src/m.py": (Hunk(4, 1, 3, 0),)}, MAP)  # base line 4 deleted
    assert found.impact.tests == ("tests/test_m.py::test_a",)
    assert (found.degraded, found.deleted, found.impact.degraded) == ((), (), False)


def test_a_deleted_line_with_no_coverage_data_is_degraded_at_the_line_before_it(tmp_path):
    found = selected(tmp_path, {"src/m.py": (Hunk(5, 2, 4, 0), Hunk(9, 2, 8, 1))}, MAP)
    assert found.deleted == (("src/m.py", 4, 5), ("src/m.py", 4, 6), ("src/m.py", 8, 10))
    assert found.impact.degraded
    assert found.impact.tests == ("tests/test_m.py::TestB::test_b", "tests/test_m.py::test_a")  # the full suite


def test_a_deleted_line_without_a_map_is_degraded(tmp_path):
    found = selected(tmp_path, {"src/m.py": (Hunk(1, 1, 0, 0),)}, None)
    assert found.deleted == (("src/m.py", 1, 1),)  # a deletion at the top sits at line 1
    assert (found.impact.tests, found.impact.degraded) == ((), True)


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


def tagged_in(tmp_path, text):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_n.py").write_text(text, encoding="utf-8")
    index = build_index(adapters.scan(tmp_path, ["tests/test_n.py"]))
    return impact.tagged_tests(tmp_path, index, {("req", "a")})


def test_a_utf8_bom_does_not_send_a_test_file_to_the_line_scan(tmp_path):
    text = "\ufeff# [utest->req~a~1]\nclass TestC:\n    def test_one(self):\n        pass\n# a note\n    def test_two(self):\n        pass\n"
    assert tagged_in(tmp_path, text) == ["tests/test_n.py::TestC::test_one", "tests/test_n.py::TestC::test_two"]
    assert (tmp_path / "tests" / "test_n.py").read_bytes()[:3] == b"\xef\xbb\xbf"


def test_a_syntax_warning_in_a_test_file_is_not_raised(tmp_path):
    text = '# [utest->req~a~1]\nclass TestC:\n    def test_one(self):\n        x = "\\d"\n# a note\n    def test_two(self):\n        pass\n'
    assert tagged_in(tmp_path, text) == ["tests/test_n.py::TestC::test_one", "tests/test_n.py::TestC::test_two"]


def test_a_column_0_comment_in_a_test_class_keeps_the_methods_after_it(tmp_path):
    text = "# [utest->req~a~1]\nclass TestC:\n    def test_one(self):\n        pass\n# a note\n    def test_two(self):\n        pass\n"
    assert tagged_in(tmp_path, text) == ["tests/test_n.py::TestC::test_one", "tests/test_n.py::TestC::test_two"]


def test_a_multi_line_string_at_column_0_in_a_test_method_keeps_the_methods_after_it(tmp_path):
    text = '# [utest->req~a~1]\nclass TestS:\n    def test_one(self):\n        x = """\ndef test_fake():\n"""\n    def test_two(self):\n        pass\n'
    assert tagged_in(tmp_path, text) == ["tests/test_n.py::TestS::test_one", "tests/test_n.py::TestS::test_two"]


def test_an_unparsable_test_file_is_read_by_its_lines(tmp_path):
    text = "# [utest->req~a~1]\nclass TestU:\n    def test_one(self):\n        pass(\nasync def test_two():\n    pass\n"
    assert tagged_in(tmp_path, text) == ["tests/test_n.py::TestU::test_one", "tests/test_n.py::test_two"]


def test_a_test_file_too_deep_for_the_parser_is_read_by_its_lines(tmp_path):
    text = "# [utest->req~a~1]\ndef test_ok():\n    pass\n\nBIG = " + " + ".join(["1"] * 10000) + "\n"
    assert tagged_in(tmp_path, text) == ["tests/test_n.py::test_ok"]


def test_a_deleted_file_selects_the_tests_that_covered_its_lines_and_degrades_the_rest_at_its_line_1(tmp_path):
    gone = {("src/gone.py", 2): ("tests/test_m.py::test_a",)}
    found = selected(tmp_path, {"src/gone.py": (Hunk(1, 3, 0, 0),)}, gone)
    assert found.impact.tests == ("tests/test_m.py::test_a",)  # and the full suite, which this map is
    assert found.deleted == (("src/gone.py", 1, 1), ("src/gone.py", 1, 3))


# The evidence layer: the whole suite, then mutmut, on a temporary copy of the work tree.

EVIDENCE_SPEC = "`req~a~1`\n\nA.\n\n`req~u~1`\n\nU.\n\n`dsn~b~1`\n\nB.\n\nCovers: req~a~1\n"
EVIDENCE = {
    "pytest.ini": "[pytest]\npythonpath = src\n",
    "docs/spec.md": EVIDENCE_SPEC,
    "src/pkg/__init__.py": "",
    "src/pkg/core.py": (
        "# [impl->req~a~1]\n"  # 1
        "def one():\n"  # 2
        "    return 1\n"  # 3
        "\n\n"
        "class Box:\n"  # 6
        "    # a comment above the def\n"  # 7
        "    def size(self, n):\n"  # 8
        "        x = 1\n"  # 9
        "        return n + x\n"  # 10
    ),
    "src/pkg/other.py": "# [impl->req~u~1]\ndef other():\n    return 3\n",
    "src/pkg/design.py": "# [impl->dsn~b~1]\ndef design():\n    return 4\n",
    "web/a.ts": "// [impl->req~a~1]\nexport const a = 1;\n",
    "tests/test_core.py": (
        "from pkg.core import Box, one\n\n\n"
        "# [utest->req~a~1]\ndef test_one():\n    assert one() == 1\n\n\n"
        "def test_size():\n    assert Box().size(1) > 0\n"
    ),
}
LEVELS = {"req~a~1": "judged", "req~u~1": "untraced"}


def scanned(repo):
    return build_index(adapters.scan(repo, git.work_tree_files(repo)))


def test_the_files_to_mutate_are_the_python_files_of_the_impl_regions_of_traced_requirements(files_repo):
    repo = files_repo(EVIDENCE)
    assert impact.mutation_files(scanned(repo), LEVELS) == ["src/pkg/core.py"]
    assert impact.mutation_files(scanned(repo), {**LEVELS, "req~u~1": "traced"}) == [
        "src/pkg/core.py",
        "src/pkg/other.py",
    ]


def test_the_evidence_run_maps_each_mutant_to_its_line_and_leaves_the_work_tree_as_it_was(files_repo):
    repo = files_repo({**EVIDENCE, "notes.txt": "gone\n"})
    (repo / "notes.txt").unlink()  # a tracked file deleted from the work tree
    before = git_output(repo, "status", "--porcelain", "--untracked-files=all", "--ignored")
    found = impact.evidence(repo, scanned(repo), LEVELS)
    assert git_output(repo, "status", "--porcelain", "--untracked-files=all", "--ignored") == before
    assert found.tool == f"mutmut {impact.version('mutmut')}"
    assert found.failing == ()
    assert [(m.path, m.line, m.key.rpartition(".")[2], m.code) for m in found.mutants] == [
        ("src/pkg/core.py", 3, "x_one__mutmut_1", 1),
        ("src/pkg/core.py", 9, "xǁBoxǁsize__mutmut_1", 1),
        ("src/pkg/core.py", 9, "xǁBoxǁsize__mutmut_2", 0),
        ("src/pkg/core.py", 10, "xǁBoxǁsize__mutmut_3", 1),
    ]


JUNIT_PASS = '<testsuites><testsuite><testcase file="tests/test_core.py" classname="tests.test_core" name="test_one"/></testsuite></testsuites>'


def stub_run(monkeypatch, junit=JUNIT_PASS, mutmut=None):
    """Replace `impact._run`: the suite run writes junit (None: no report), the mutmut run calls mutmut(copy)."""
    calls = []

    def run(command, root, env):
        calls.append((command, root, {path.relative_to(root).as_posix() for path in root.rglob("*")}))
        report = next((part.partition("=")[2] for part in command if part.startswith("--junitxml=")), None)
        if report is not None and junit is not None:
            Path(report).write_text(junit, encoding="utf-8")
        if command[1:4] == ["-m", "mutmut", "run"] and mutmut is not None:
            return mutmut(root)
        return 0

    monkeypatch.setattr(impact, "_run", run)
    return calls


def test_the_copy_holds_the_listed_files_and_merges_mutmut_s_section_into_setup_cfg(files_repo, monkeypatch):
    setup = "[tool:pytest]\naddopts = -q %(here)s\n"
    repo = files_repo({**EVIDENCE, "setup.cfg": setup, "notes.txt": "gone\n"})
    (repo / "notes.txt").unlink()
    (repo / "untracked.txt").write_text("kept\n", encoding="utf-8")
    seen = {}

    def mutmut(copy):
        seen["setup"] = (copy / "setup.cfg").read_text(encoding="utf-8")  # and returns None: timed out

    calls = stub_run(monkeypatch, mutmut=mutmut)
    with pytest.raises(impact.EvidenceError, match="mutmut run timed out"):
        impact.evidence(repo, scanned(repo), LEVELS)
    (suite, _, listed), (run, root, _) = calls
    assert suite[1:3] == ["-m", "pytest"]
    assert suite[suite.index("junit_family=xunit1") - 1] == "-o"
    assert run == [sys.executable, "-m", "mutmut", "run"]
    assert "notes.txt" not in listed
    assert {"untracked.txt", "src/pkg/core.py"} <= listed
    assert not str(root).startswith(str(repo))
    assert "[tool:pytest]\naddopts = -q %(here)s\n" in seen["setup"]
    assert "source_paths = \n\tsrc/pkg/core.py\n" in seen["setup"]
    assert "also_copy = \n\tdocs\n\tpytest.ini\n\tsetup.cfg\n\tsrc\n\ttests\n\tuntracked.txt\n\tweb\n" in seen["setup"]


def test_the_merged_setup_cfg_keeps_the_case_of_other_sections_keys(files_repo, monkeypatch):
    repo = files_repo({**EVIDENCE, "setup.cfg": "[options.package_data]\nMyPkg = *.json\n"})
    seen = {}

    def mutmut(copy):
        seen["setup"] = (copy / "setup.cfg").read_text(encoding="utf-8")  # and returns None: timed out

    stub_run(monkeypatch, mutmut=mutmut)
    with pytest.raises(impact.EvidenceError, match="mutmut run timed out"):
        impact.evidence(repo, scanned(repo), LEVELS)
    assert "MyPkg = *.json" in seen["setup"]


def test_a_malformed_setup_cfg_exits_2_naming_it(files_repo, monkeypatch):
    repo = files_repo({**EVIDENCE, "setup.cfg": "[tool:pytest]\naddopts = -q\naddopts = -x\n"})
    stub_run(monkeypatch)
    with pytest.raises(impact.EvidenceError, match=r"setup\.cfg"):
        impact.evidence(repo, scanned(repo), LEVELS)


def test_the_copy_leaves_out_a_stale_mutants_directory(files_repo, monkeypatch):
    repo = files_repo(EVIDENCE)
    (repo / "mutants").mkdir()
    (repo / "mutants" / "x.meta").write_text("{}\n", encoding="utf-8")
    seen = {}

    def mutmut(copy):
        seen["stale"] = (copy / "mutants" / "x.meta").exists()  # and returns None: timed out

    stub_run(monkeypatch, mutmut=mutmut)
    with pytest.raises(impact.EvidenceError, match="mutmut run timed out"):
        impact.evidence(repo, scanned(repo), LEVELS)
    assert seen["stale"] is False


@pytest.mark.parametrize("name", ["pyproject.toml", "setup.cfg"])
def test_a_config_file_that_is_not_utf_8_exits_2_naming_it(files_repo, monkeypatch, name):
    repo = files_repo(EVIDENCE)
    (repo / name).write_bytes(b"\xff\xfe\x00bad\n")
    stub_run(monkeypatch)
    with pytest.raises(impact.EvidenceError, match=name.replace(".", r"\.")):
        impact.evidence(repo, scanned(repo), LEVELS)


def test_a_tool_mutmut_section_in_pyproject_exits_2(files_repo, monkeypatch):
    repo = files_repo({**EVIDENCE, "pyproject.toml": "[tool.mutmut]\nsource_paths = ['src']\n"})
    stub_run(monkeypatch)
    with pytest.raises(impact.EvidenceError, match=r"\[tool.mutmut\]"):
        impact.evidence(repo, scanned(repo), LEVELS)


def test_a_pyproject_whose_tool_is_not_a_table_exits_2_naming_it(files_repo, monkeypatch):
    repo = files_repo({**EVIDENCE, "pyproject.toml": "tool = 1\n"})
    stub_run(monkeypatch)
    with pytest.raises(impact.EvidenceError, match=r"pyproject\.toml"):
        impact.evidence(repo, scanned(repo), LEVELS)


def test_a_mutmut_section_in_setup_cfg_exits_2(files_repo, monkeypatch):
    repo = files_repo({**EVIDENCE, "setup.cfg": "[mutmut]\nsource_paths = src\n"})
    calls = stub_run(monkeypatch)
    with pytest.raises(impact.EvidenceError, match=r"setup\.cfg has its own \[mutmut\]"):
        impact.evidence(repo, scanned(repo), LEVELS)
    assert calls == []


FAILING = (
    "<testsuites><testsuite>"
    '<testcase file="tests/test_core.py" classname="tests.test_core" name="test_one"><failure message="x"/></testcase>'
    '<testcase file="tests/test_core.py" classname="tests.test_core.TestBox" name="test_box[2-3]"><error/></testcase>'
    '<testcase file="tests/test_core.py" classname="tests.test_core" name="test_skip"><skipped/></testcase>'
    "</testsuite></testsuites>"
)
TAGGED = {
    **EVIDENCE,
    "tests/test_core.py": (
        "# [utest->req~a~1]\ndef test_one():\n    pass\n\n\n"
        "# [utest->req~a~1]\nclass TestBox:\n    def test_box(self):\n        pass\n\n\n"
        "def test_skip():\n    pass\n"
    ),
}


def test_the_failing_tagged_tests_of_the_junit_report_read_as_node_ids_and_mutmut_does_not_run(files_repo, monkeypatch):
    repo = files_repo(TAGGED)
    calls = stub_run(monkeypatch, junit=FAILING)
    found = impact.evidence(repo, scanned(repo), LEVELS)
    assert found.failing == ("tests/test_core.py::TestBox::test_box", "tests/test_core.py::test_one")
    assert found.mutants == ()
    assert len(calls) == 1  # the suite run alone


def test_a_failing_untagged_test_exits_2_naming_it_and_mutmut_does_not_run(files_repo, monkeypatch):
    repo = files_repo(EVIDENCE)
    junit = FAILING.replace("test_one", "test_size")
    calls = stub_run(monkeypatch, junit=junit)
    with pytest.raises(impact.EvidenceError, match=r"tests/test_core.py::TestBox::test_box"):
        impact.evidence(repo, scanned(repo), LEVELS)
    assert len(calls) == 1


@pytest.mark.parametrize("junit", [None, "<testsuites><testsuite>"])
def test_a_missing_or_unparsable_junit_report_exits_2(files_repo, monkeypatch, junit):
    repo = files_repo(EVIDENCE)
    stub_run(monkeypatch, junit=junit)
    with pytest.raises(impact.EvidenceError, match="JUnit report"):
        impact.evidence(repo, scanned(repo), LEVELS)


def test_a_suite_run_that_times_out_exits_2(files_repo, monkeypatch):
    repo = files_repo(EVIDENCE)
    monkeypatch.setattr(impact, "_run", lambda *_: None)
    with pytest.raises(impact.EvidenceError, match="test run timed out"):
        impact.evidence(repo, scanned(repo), LEVELS)


def meta(text):
    def write(copy):
        (copy / "mutants" / "src" / "pkg").mkdir(parents=True)
        if text is not None:
            (copy / "mutants" / "src" / "pkg" / "core.py.meta").write_text(text, encoding="utf-8")
        return 0

    return write


@pytest.mark.parametrize(
    "text", [None, "{", '{"exit_code_by_key": []}', '{"exit_code_by_key": {"pkg.core.x_one__mutmut_1": 0}}']
)
def test_an_unreadable_mutmut_result_exits_2(files_repo, monkeypatch, text):
    repo = files_repo(EVIDENCE)
    stub_run(monkeypatch, mutmut=meta(text))  # the last has no mutants file to read its line from
    with pytest.raises(impact.EvidenceError, match=r"no readable result for src/pkg/core\.py"):
        impact.evidence(repo, scanned(repo), LEVELS)


def missing(name):
    raise impact.PackageNotFoundError(name)


@pytest.mark.parametrize(
    ("version", "message"), [(missing, "mutmut is not installed"), (lambda _: "4.0.0", "not mutmut 3")]
)
def test_mutmut_missing_or_of_another_major_exits_2(files_repo, monkeypatch, version, message):
    repo = files_repo(EVIDENCE)
    calls = stub_run(monkeypatch)
    monkeypatch.setattr(impact, "version", version)
    with pytest.raises(impact.EvidenceError, match=message):
        impact.evidence(repo, scanned(repo), LEVELS)
    assert calls == []


def test_a_python_that_does_not_exist_exits_2_naming_mutmut_missing_under_it(files_repo, monkeypatch, tmp_path):
    repo = files_repo(EVIDENCE)
    calls = stub_run(monkeypatch)
    python = str(tmp_path / "no-such-python")
    with pytest.raises(impact.EvidenceError, match=re.escape(f"mutmut under {python} is missing")):
        impact.evidence(repo, scanned(repo), LEVELS, python=python)
    assert calls == []


def test_a_mutmut_under_python_of_another_version_exits_2(files_repo, monkeypatch, tmp_path):
    repo = files_repo(EVIDENCE)
    calls = stub_run(monkeypatch)
    python = fake_python(tmp_path, "echo 3.0.0")
    with pytest.raises(impact.EvidenceError, match=re.escape(f"mutmut under {python} is 3.0.0")):
        impact.evidence(repo, scanned(repo), LEVELS, python=python)
    assert calls == []


# The region filter and `evidence-failed`.

REGIONS = {
    **EVIDENCE,
    "src/pkg/lines.py": (
        "def free():\n"  # 1, above every tag
        "    return 0\n"  # 2
        "\n\n"
        "# [impl->req~a~1]\n"  # 5
        "# [impl->req~u~1]\n"  # 6, stacked: one region for both
        "def both():\n"  # 7
        "    return 1\n"  # 8
    ),
}


def mutant(path, line, code, name="x_f__mutmut_1"):
    return impact.Mutant(path, line, f"pkg.mod.{name}", code)


def raised(repo, *mutants, failing=()):
    found = impact.evidence_failed(repo, scanned(repo), impact.Evidence("mutmut 3.8.0", failing, mutants))
    return [(each.path, each.line, each.rule, each.subject) for each in found]


def test_a_surviving_mutant_in_a_tagged_region_raises_evidence_failed_per_line_against_each_requirement(files_repo):
    repo = files_repo(REGIONS)
    found = raised(
        repo,
        mutant("src/pkg/lines.py", 8, 0, "x_both__mutmut_1"),
        mutant("src/pkg/lines.py", 8, 0, "x_both__mutmut_2"),
        mutant("src/pkg/lines.py", 7, 1),
    )
    assert found == [
        ("src/pkg/lines.py", 8, "earnest/evidence-failed", "req~a~1"),
        ("src/pkg/lines.py", 8, "earnest/evidence-failed", "req~u~1"),
    ]
    message = impact.evidence_failed(
        repo,
        scanned(repo),
        impact.Evidence("mutmut 3.8.0", (), (mutant("src/pkg/lines.py", 8, 0, "x_both__mutmut_2"),)),
    )[0].message
    assert "`req~a~1`" in message
    assert "src/pkg/lines.py:8" in message
    assert "x_both__mutmut_2" in message


def test_a_surviving_mutant_outside_every_region_or_in_a_design_region_raises_nothing(files_repo):
    repo = files_repo(REGIONS)
    assert raised(repo, mutant("src/pkg/lines.py", 2, 0), mutant("src/pkg/design.py", 3, 0)) == []


@pytest.mark.parametrize(
    ("code", "count"),
    [(0, 1), (5, 1), (33, 1), (1, 0), (3, 0), (36, 0), (24, 0), (-24, 0), (152, 0), (255, 0), (37, 0), (34, 0)],
)
def test_the_status_map_counts_survived_and_no_tests_as_surviving_and_the_rest_as_nothing(files_repo, code, count):
    repo = files_repo(REGIONS)
    assert len(raised(repo, mutant("src/pkg/core.py", 3, code))) == count


@pytest.mark.parametrize(
    ("code", "status"),
    [(-9, "segfault"), (-11, "segfault"), (35, "suspicious"), (2, "interrupted"), (None, "not checked"), (99, "99")],
)
def test_an_incomplete_or_unlisted_mutmut_status_exits_2(files_repo, code, status):
    repo = files_repo(REGIONS)
    with pytest.raises(impact.EvidenceError, match=status):
        raised(repo, mutant("src/pkg/lines.py", 2, code))  # outside every region, still an incomplete run


def test_a_failing_tagged_test_raises_evidence_failed_at_its_tag_line(files_repo):
    repo = files_repo(TAGGED)
    found = raised(repo, failing=("tests/test_core.py::TestBox::test_box",))
    assert found == [("tests/test_core.py", 6, "earnest/evidence-failed", "req~a~1")]


def test_the_stryker_reader_gives_the_file_and_line_of_each_surviving_mutant_no_coverage_included():
    report = Path(__file__).with_name("stryker-report.json")
    assert impact.stryker_survivors(report) == [
        ("src/limits.ts", 4),
        ("src/limits.ts", 9),
        ("src/notice.ts", 2),
        ("src/notice.ts", 5),  # NoCoverage: no test reaches it, so it survives
    ]


# The evidenced level and the evidence entries of E1.


def requirement(found, name):
    return next(item for item in found.defined.values() if str(item.id) == name)


KILLED = (mutant("src/pkg/core.py", 3, 1), mutant("src/pkg/other.py", 3, 1))  # one killed in each requirement


def entries(repo, levels, proof):
    found = scanned(repo)
    return impact.entries(repo, found, levels, proof, impact.evidence_failed(repo, found, proof))


def test_each_requirement_the_run_mutated_gets_an_entry_keyed_by_its_regions_its_tests_and_the_tool(files_repo):
    repo = files_repo(EVIDENCE)
    found = scanned(repo)
    proof = impact.Evidence("mutmut 3.8.0", (), (*KILLED, mutant("src/pkg/other.py", 3, 0)))  # survives in req~u~1
    held = entries(repo, {"req~a~1": "judged", "req~u~1": "judged"}, proof)
    item = requirement(found, "req~a~1")
    code = judge.region_hash(repo, judge.regions(found, item, judge.KINDS["implemented"]))
    tests = judge.region_hash(repo, judge.regions(found, item, judge.KINDS["tested"]))
    assert held["req~a~1"] == {"key": {"regions": code, "tests": tests, "tool": "mutmut 3.8.0"}, "result": "passed"}
    assert held["req~u~1"]["result"] == "failed"
    assert set(held) == {"req~a~1", "req~u~1"}


def test_only_a_judged_requirement_with_no_failure_passes_and_one_the_run_reached_no_verdict_on_has_no_entry(
    files_repo,
):
    repo = files_repo(EVIDENCE)
    clean = impact.Evidence("mutmut 3.8.0", (), KILLED)
    assert set(entries(repo, {"req~a~1": "traced", "req~u~1": "judged"}, clean)) == {"req~u~1"}
    failing = impact.Evidence("mutmut 3.8.0", ("tests/test_core.py::test_one",), ())  # so mutmut never ran
    held = entries(repo, {"req~a~1": "judged", "req~u~1": "judged"}, failing)
    assert {req: entry["result"] for req, entry in held.items()} == {"req~a~1": "failed"}


def test_a_judged_requirement_passes_only_with_a_killed_mutant_in_its_impl_regions(files_repo):
    repo = files_repo(EVIDENCE)
    levels = {"req~a~1": "judged", "req~u~1": "judged"}
    outside = impact.Evidence("mutmut 3.8.0", (), (mutant("src/pkg/other.py", 3, 1),))  # killed, in req~u~1 only
    assert {req: entry["result"] for req, entry in entries(repo, levels, outside).items()} == {"req~u~1": "passed"}
    assert entries(repo, levels, impact.Evidence("mutmut 3.8.0", (), ())) == {}


def test_a_skipped_mutant_is_no_kill(files_repo):
    repo = files_repo(EVIDENCE)
    skipped = impact.Evidence("mutmut 3.8.0", (), (mutant("src/pkg/core.py", 3, 34),))
    assert entries(repo, {"req~a~1": "judged", "req~u~1": "judged"}, skipped) == {}


def test_a_requirement_with_no_impl_region_of_a_mutated_file_gets_no_entry(files_repo):
    repo = files_repo(
        {**EVIDENCE, "src/pkg/other.py": "def other():\n    return 3\n", "web/u.ts": "// [impl->req~u~1]\n"}
    )
    held = entries(repo, {"req~a~1": "judged", "req~u~1": "judged"}, impact.Evidence("mutmut 3.8.0", (), KILLED))
    assert set(held) == {"req~a~1"}


PASSED = {"key": {}, "result": "passed"}
FAILED = {"key": {}, "result": "failed"}


def test_with_a_model_a_judged_requirement_with_a_passed_entry_for_its_id_and_revision_is_evidenced():
    levels = {"req~a~1": "judged", "req~b~1": "judged", "req~c~1": "traced", "req~d~1": "judged", "req~e~1": "untraced"}
    entries = {"req~a~1": PASSED, "req~b~1": FAILED, "req~c~1": PASSED, "req~d~2": PASSED, "req~e~1": PASSED}
    assert impact.evidenced(levels, entries, {req: {} for req in entries}, judged=True) == {
        "req~a~1": "evidenced",
        "req~b~1": "judged",
        "req~c~1": "traced",
        "req~d~1": "judged",  # the entry is for another revision
        "req~e~1": "untraced",
    }


def test_with_no_model_a_traced_requirement_with_a_passed_entry_is_evidenced():
    levels = {"req~a~1": "traced", "req~b~1": "traced", "req~e~1": "untraced"}
    entries = {"req~a~1": PASSED, "req~b~1": FAILED, "req~e~1": PASSED}
    assert impact.evidenced(levels, entries, {req: {} for req in entries}, judged=False) == {
        "req~a~1": "evidenced",
        "req~b~1": "traced",
        "req~e~1": "untraced",
    }


def test_each_requirement_keeps_exactly_one_level():
    levels = {"req~a~1": "judged", "req~b~1": "traced", "req~c~1": "untraced"}
    raised = impact.evidenced(levels, dict.fromkeys(levels, PASSED), {req: {} for req in levels}, judged=True)
    assert list(raised) == list(levels)
    assert all(level in reporter.LEVELS for level in raised.values())


STALE = {
    "code": ("src/pkg/core.py", "    return 1\n", "    return 1  # edited\n", "mutmut 3.8.0"),
    "test": ("tests/test_core.py", "    assert one() == 1\n", "    assert one() == 1  # edited\n", "mutmut 3.8.0"),
    "tool": ("src/pkg/core.py", "", "", "mutmut 3.9.0"),
    "no mutmut": ("src/pkg/core.py", "", "", None),
}


@pytest.mark.parametrize("judged", [True, False], ids=["model", "no model"])
@pytest.mark.parametrize("stale", list(STALE))
def test_an_entry_counts_only_under_the_key_of_the_current_work_tree_and_the_installed_mutmut(
    files_repo, monkeypatch, stale, judged
):
    repo = files_repo(EVIDENCE)
    floor = "judged" if judged else "traced"
    held = entries(repo, {"req~a~1": "judged"}, impact.Evidence("mutmut 3.8.0", (), KILLED))
    assert held["req~a~1"]["result"] == "passed"

    def level():
        found = scanned(repo)
        return impact.evidenced({"req~a~1": floor}, held, impact.keys(repo, found, held), judged=judged)["req~a~1"]

    monkeypatch.setattr(impact, "tool", lambda: "mutmut 3.8.0")
    assert level() == "evidenced"  # the key the run wrote matches the tree it ran on
    path, old, new, name = STALE[stale]
    text = (repo / path).read_text(encoding="utf-8")
    (repo / path).write_text(text.replace(old, new, 1) if old else text, encoding="utf-8")
    monkeypatch.setattr(impact, "tool", lambda: name)
    assert level() == floor
