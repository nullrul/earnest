"""Integration: `earnest check` over a committed repository, from the scan to the exit code."""

import os

import pytest

from earnest import cli
from tests.sarif import located, sarif_run


CHAIN = {
    "docs/intent.md": "# Intent\n\n`tenet~t~1`\n\n`goal~g~1`\n\nCovers: tenet~t~1\n",
    "docs/scope.md": "# Scope\n\n`feat~f~1`\n\nCovers: goal~g~1\n",
    "docs/requirements.md": "# Requirements\n\n`req~r~1`\n\nThe service shall answer.\n\nCovers: feat~f~1\n",
    "src/app.py": "# [impl->req~r~1]\ndef answer() -> int:\n    return 42\n",
    "tests/test_app.py": "# [utest->req~r~1]\ndef test_answer() -> None:\n    assert True\n",
    "tests/app.feature": "Feature: App\n\n  @stest:feat~f~1\n  Scenario: It answers\n    Then it answers\n",
}


def check(cwd, monkeypatch, capsys):
    monkeypatch.chdir(cwd)
    code = cli.main(["check"])
    out, err = capsys.readouterr()
    return code, sarif_run(out), err


def test_a_complete_chain_passes_with_every_requirement_traced(files_repo, monkeypatch, capsys):
    code, run, err = check(files_repo(CHAIN), monkeypatch, capsys)
    assert (code, run["results"]) == (0, [])
    assert run["properties"]["traceLevels"] == {"req~r~1": "traced"}
    assert err.startswith("traced 100%, judged 0%, evidenced 0%; requirements: 1\n")


def test_a_check_from_a_subdirectory_reads_the_whole_work_tree_untracked_files_included(
    files_repo, monkeypatch, capsys
):
    repo = files_repo(CHAIN)
    (repo / "docs" / "more notes.md").write_text("# More\n\n`req~x~1`\n\nCovers: feat~f~1\n", encoding="utf-8")
    code, run, _ = check(repo / "src", monkeypatch, capsys)
    assert code == 1
    assert {(result["ruleId"], located(result)) for result in run["results"]} == {
        ("earnest/gap", ("docs/more%20notes.md", 3)),
    }


@pytest.mark.parametrize(
    "data",
    [b"# Caf\xe9\n\n`req~a~1`\n", b"# A\r x\n\n`req~a~1`\n"],
    ids=["not-utf-8", "lone-carriage-return"],
)
def test_bytes_that_are_not_utf_8_or_a_lone_carriage_return_move_no_line(data, files_repo, monkeypatch, capsys):
    repo = files_repo({"docs/a.md": "# A\n"})
    (repo / "docs" / "a.md").write_bytes(data)
    code, run, _ = check(repo, monkeypatch, capsys)
    assert code == 1
    assert {located(result) for result in run["results"]} == {("docs/a.md", 3)}


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads any file")
def test_a_tracked_file_that_cannot_be_read_exits_2_with_one_line_on_stderr(files_repo, monkeypatch, capsys):
    repo = files_repo({"docs/a.md": "# A\n"})
    unreadable = repo / "docs" / "a.md"
    unreadable.chmod(0o000)
    try:
        monkeypatch.chdir(repo)
        code = cli.main(["check"])
    finally:
        unreadable.chmod(0o644)
    out, err = capsys.readouterr()
    assert (code, out) == (2, "")
    assert err.startswith("earnest: ")
    assert len(err.splitlines()) == 1
