"""Tests for earnest.cli: the required command, and the exit code when the check cannot run or loses its reader."""

import subprocess
import sys

import pytest

from earnest import cli


CHECK = [sys.executable, "-c", "import sys; from earnest.cli import main; sys.exit(main(['check']))"]


def test_a_command_is_required(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])
    assert exit_info.value.code == 2
    assert "check" in capsys.readouterr().err


def test_a_check_outside_a_work_tree_exits_2_with_one_line_on_stderr(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["check"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("earnest: fatal: not a git repository")
    assert len(err.splitlines()) == 1


def test_a_reader_that_goes_away_early_gets_exit_code_2_and_no_traceback(files_repo):
    repo = files_repo({"docs/a.md": "# A\n"})
    with subprocess.Popen(CHECK, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as check:
        check.stdout.close()
        err = check.stderr.read()
    assert check.returncode == 2
    assert b"Traceback" not in err


def test_a_reader_of_the_summary_that_goes_away_early_gets_exit_code_2(files_repo):
    repo = files_repo({"docs/a.md": "# A\n"})
    with subprocess.Popen(CHECK, cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as check:
        check.stderr.close()
    assert check.returncode == 2
