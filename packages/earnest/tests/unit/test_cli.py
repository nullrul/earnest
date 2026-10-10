"""Tests for earnest.cli: the required command, and the exit code when the check cannot run or loses its reader."""

import json
import subprocess
import sys

import pytest

from earnest import cli
from tests.sarif import located, sarif_run


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


DASH = "\u2014"
RECORD = "aidlc/spaces/default/intents/260926-checkout"
PLAN_FILE = f"{RECORD}/construction/code-generation/code-generation-plan.md"
UNSUPPORTED = "earnest: unsupported route: units-generation is on the route, so per-unit stages\n"
STATE = f"""## Stage Progress
### INCEPTION PHASE
- [S] units-generation {DASH} SKIP: not in scope
- [x] requirements-analysis {DASH} EXECUTE: always
### CONSTRUCTION PHASE
- [x] code-generation {DASH} EXECUTE: always
"""
UNITS = STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")


def run(repo, monkeypatch, capsys, *args):
    monkeypatch.chdir(repo)
    code = cli.main(list(args))
    out, err = capsys.readouterr()
    return code, out, err


def put(repo, path, text):
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text, encoding="utf-8")


def test_stage_with_no_record_directory_exits_two(files_repo, monkeypatch, capsys):
    code, out, err = run(files_repo({"docs/a.md": "# A\n"}), monkeypatch, capsys, "check", "--stage", "code-generation")
    assert (code, out) == (2, "")
    assert err.startswith("earnest: ")
    assert len(err.splitlines()) == 1


def test_unknown_stage_exits_two_with_one_line(fixture_repo, monkeypatch, capsys):
    code, out, err = run(fixture_repo("seeded-change"), monkeypatch, capsys, "check", "--stage", "no-such-stage")
    assert (code, out) == (2, "")
    assert len(err.splitlines()) == 1
    assert "no-such-stage" in err


def test_ambiguous_bare_slug_exits_two_and_lists_the_stages(files_repo, monkeypatch, capsys):
    state = STATE.replace("code-generation", "requirements-analysis")
    repo = files_repo({"i/aidlc-state.md": state})
    code, out, err = run(repo, monkeypatch, capsys, "check", "--stage", "requirements-analysis")
    assert (code, out) == (2, "")
    assert "inception/requirements-analysis" in err
    assert "construction/requirements-analysis" in err


def test_several_records_without_intent_exits_two_and_lists_them(files_repo, monkeypatch, capsys):
    repo = files_repo({"a/aidlc-state.md": STATE, "b/aidlc-state.md": STATE})
    code, out, err = run(repo, monkeypatch, capsys, "check", "--stage", "requirements-analysis")
    assert (code, out) == (2, "")
    assert "--intent" in err
    assert "a, b" in err


def test_intent_option_names_a_missing_record_exits_two(fixture_repo, monkeypatch, capsys):
    code, out, err = run(fixture_repo("seeded-change"), monkeypatch, capsys, "check", "--intent", "no/such/dir")
    assert (code, out) == (2, "")
    assert "no/such/dir" in err
    assert len(err.splitlines()) == 1


def test_corrupt_record_exits_two_with_empty_stdout(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    put(repo, ".earnest/assessment.json", "{not json")
    for command in (["plan"], ["check"], ["check", "--stage", "construction/code-generation"]):
        code, out, err = run(repo, monkeypatch, capsys, *command)
        assert (code, out) == (2, "")
        assert ".earnest/assessment.json" in err


def test_stage_status_sets_no_exit_code(fixture_repo, monkeypatch, capsys):
    code, out, _ = run(
        fixture_repo("seeded-change"), monkeypatch, capsys, "check", "--stage", "construction/code-generation"
    )
    assert code == 0
    assert sarif_run(out)["properties"]["assessment"]["status"] == "not done"


def test_stage_exit_code_follows_the_scoped_findings(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    lines = (repo / PLAN_FILE).read_text(encoding="utf-8").split("\n")
    lines[7] = "Depends: task~notify-lockout~1"  # a cycle, in the code generation stage
    put(repo, PLAN_FILE, "\n".join(lines))
    assert run(repo, monkeypatch, capsys, "check", "--stage", "inception/requirements-analysis")[0] == 0
    assert run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation")[0] == 1


def test_plan_without_a_record_directory_says_no_plan_and_exits_zero(files_repo, monkeypatch, capsys):
    code, out, err = run(files_repo({"docs/a.md": "# A\n"}), monkeypatch, capsys, "plan")
    assert code == 0
    assert "no plan" in err.splitlines()
    assert "plan" not in sarif_run(out)["properties"]


def test_plan_of_an_only_unsupported_intent_exits_two_with_empty_stdout(files_repo, monkeypatch, capsys):
    code, out, err = run(files_repo({"i/aidlc-state.md": UNITS}), monkeypatch, capsys, "plan")
    assert (code, out, err) == (2, "", UNSUPPORTED)


def test_check_stage_of_an_unsupported_intent_exits_two_and_writes_nothing(files_repo, monkeypatch, capsys):
    repo = files_repo({"i/aidlc-state.md": UNITS})
    code, out, err = run(repo, monkeypatch, capsys, "check", "--stage", "inception/requirements-analysis")
    assert (code, out, err) == (2, "", UNSUPPORTED)
    assert not (repo / ".earnest").exists()


def test_plain_check_places_an_unsupported_intents_findings_without_a_plan(files_repo, monkeypatch, capsys):
    repo = files_repo({"i/aidlc-state.md": UNITS, "i/inception/requirements-analysis/r.md": "`req~a~1`\n\nBody.\n"})
    code, out, _ = run(repo, monkeypatch, capsys, "check")
    assert code == 1
    results = sarif_run(out)["results"]
    assert results
    for result in results:
        assert result["properties"]["position"] == "current"
        assert "stage" not in result["properties"]
        assert result["message"]["text"].startswith("in scope: ")


def test_plan_lists_the_supported_intents_when_another_is_unsupported(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    other = "aidlc/spaces/default/intents/260927-other"
    put(repo, f"{other}/aidlc-state.md", UNITS)
    code, out, err = run(repo, monkeypatch, capsys, "plan")
    assert code == 0
    assert [entry["intent"] for entry in sarif_run(out)["properties"]["plan"]["intents"]] == [RECORD]
    assert f"earnest: skipped {other}: unsupported route" in err.splitlines()


def test_intent_option_without_stage_is_validated_and_changes_nothing_else(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    plain = run(repo, monkeypatch, capsys, "check")
    named = run(repo, monkeypatch, capsys, "check", "--intent", RECORD)
    assert named == plain
    assert not (repo / ".earnest").exists()


def test_intent_option_root_relative_wins_over_the_working_directory_form(files_repo, monkeypatch, capsys):
    repo = files_repo({"a/aidlc-state.md": STATE, "sub/a/aidlc-state.md": STATE, "sub/b/aidlc-state.md": STATE})
    stage = "inception/requirements-analysis"
    monkeypatch.chdir(repo / "sub")
    for name in ("a", "b"):
        assert cli.main(["check", "--stage", stage, "--intent", name]) == 0
        capsys.readouterr()
    runs = json.loads((repo / ".earnest" / "assessment.json").read_text(encoding="utf-8"))["runs"]
    assert sorted(runs) == [f"a/{stage}", f"sub/b/{stage}"]  # `a` exists at the root, `b` only below `sub`


def test_plan_of_several_intents_all_unsupported_exits_zero_with_skip_lines(files_repo, monkeypatch, capsys):
    repo = files_repo({"a/aidlc-state.md": UNITS, "b/aidlc-state.md": UNITS})
    code, out, err = run(repo, monkeypatch, capsys, "plan")
    assert code == 0
    assert sarif_run(out)["properties"]["plan"] == {"intents": []}
    assert [line for line in err.splitlines() if line.startswith("earnest:")] == [
        "earnest: skipped a: unsupported route",
        "earnest: skipped b: unsupported route",
    ]


def test_an_unreadable_stage_progress_row_fails_every_command(files_repo, monkeypatch, capsys):
    state = STATE.replace(f"- [x] code-generation {DASH} EXECUTE", "- [x] code-generation -- EXECUTE")
    repo = files_repo({"i/aidlc-state.md": state})
    for command in (["plan"], ["check"], ["check", "--stage", "inception/requirements-analysis"]):
        code, out, _ = run(repo, monkeypatch, capsys, *command)
        assert code == 1, command
        (found,) = [r for r in sarif_run(out)["results"] if r["ruleId"] == "earnest/route-mismatch"]
        assert (found["level"], "stage" in found["properties"]) == ("error", False)
        assert "Earnest cannot read line 6 of the state file" in found["message"]["text"]
    code, out, err = run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation")
    assert (code, out) == (2, "")  # the row that cannot be read dropped the stage from the route
    assert "not a stage on the route" in err


def test_a_renamed_stage_progress_heading_is_a_finding_not_a_silent_pass(files_repo, monkeypatch, capsys):
    state = STATE.replace("## Stage Progress", "## Stage  Progress")
    repo = files_repo({"i/aidlc-state.md": state, "docs/a.md": "`req~a~1`\n\nBody.\n"})
    code, out, err = run(repo, monkeypatch, capsys, "check")
    assert code == 1
    results = sarif_run(out)["results"]
    assert {result["ruleId"] for result in results} == {"earnest/route-mismatch", "earnest/orphaned", "earnest/gap"}
    assert err.splitlines()[0].startswith("traced 0%")  # the needs survive an emptied route, so no silent 100%
    (found,) = [result for result in results if result["ruleId"] == "earnest/route-mismatch"]
    assert located(found) == ("i/aidlc-state.md", 1)
    assert run(repo, monkeypatch, capsys, "plan")[0] == 1


def test_plain_check_of_an_unsupported_only_repository_keeps_the_m1_findings(files_repo, monkeypatch, capsys):
    repo = files_repo({"i/aidlc-state.md": UNITS, "docs/a.md": "`req~a~1`\n\nBody.\n"})
    code, out, _ = run(repo, monkeypatch, capsys, "check")
    assert code == 1
    log = sarif_run(out)
    assert {result["ruleId"] for result in log["results"]} == {"earnest/orphaned", "earnest/gap"}
    assert log["properties"]["plan"] == {"intents": []}
