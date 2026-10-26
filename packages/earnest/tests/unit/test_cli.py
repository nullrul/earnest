"""Tests for earnest.cli: the required command, and the exit code when the check cannot run or loses its reader."""

import configparser
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from earnest import cli, impact, judge
from tests.sarif import PLAN_FILE, RECORD, located, record_baseline, sarif_run, write


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
STATE = f"""## Stage Progress
### INCEPTION PHASE
- [S] units-generation {DASH} SKIP: not in scope
- [x] requirements-analysis {DASH} EXECUTE: always
### CONSTRUCTION PHASE
- [x] code-generation {DASH} EXECUTE: always
"""
UNITS = STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")
UNIT_TABLE = "i/inception/units-generation/unit-of-work.md"


def run(repo, monkeypatch, capsys, *args):
    monkeypatch.chdir(repo)
    code = cli.main(list(args))
    out, err = capsys.readouterr()
    return code, out, err


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


def test_intent_option_naming_a_looping_symlink_exits_two_with_one_line_and_no_traceback(
    fixture_repo, monkeypatch, capsys
):
    repo = fixture_repo("seeded-change")
    (repo / "loop").symlink_to("loop")
    code, out, err = run(repo, monkeypatch, capsys, "check", "--intent", "loop")
    assert (code, out) == (2, "")
    assert len(err.splitlines()) == 1
    assert "Traceback" not in err


def test_a_symlinked_earnest_directory_exits_two_and_writes_nothing_outside_the_repo(
    fixture_repo, tmp_path, monkeypatch, capsys
):
    repo = fixture_repo("seeded-change")
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / ".earnest").symlink_to(outside)
    for command in (["plan"], ["check", "--stage", "construction/code-generation"]):
        code, out, err = run(repo, monkeypatch, capsys, *command)
        assert (code, out) == (2, "")
        assert ".earnest" in err
        assert len(err.splitlines()) == 1
    assert list(outside.iterdir()) == []


def test_a_symlinked_record_exits_two_and_leaves_the_symlink_and_its_target_alone(
    fixture_repo, tmp_path, monkeypatch, capsys
):
    repo = fixture_repo("seeded-change")
    target = tmp_path / "outside.bin"
    target.write_bytes(b"\xff\xfe secret bytes")
    (repo / ".earnest").mkdir()
    (repo / ".earnest" / "assessment.json").symlink_to(target)
    for command in (["plan"], ["check"], ["check", "--stage", "construction/code-generation"]):
        code, out, err = run(repo, monkeypatch, capsys, *command)
        assert (code, out) == (2, "")
        assert ".earnest/assessment.json is a symlink" in err
        assert len(err.splitlines()) == 1
        assert "secret" not in err
    assert (repo / ".earnest" / "assessment.json").readlink() == target
    assert target.read_bytes() == b"\xff\xfe secret bytes"


def test_corrupt_record_exits_two_with_empty_stdout(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    write(repo, ".earnest/assessment.json", "{not json")
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
    write(repo, PLAN_FILE, "\n".join(lines))
    assert run(repo, monkeypatch, capsys, "check", "--stage", "inception/requirements-analysis")[0] == 0
    assert run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation")[0] == 1


def test_plan_without_a_record_directory_says_no_plan_and_exits_zero(files_repo, monkeypatch, capsys):
    code, out, err = run(files_repo({"docs/a.md": "# A\n"}), monkeypatch, capsys, "plan")
    assert code == 0
    assert "no plan" in err.splitlines()
    assert "plan" not in sarif_run(out)["properties"]


def test_plan_of_a_units_intent_without_a_table_at_its_frontier_exits_nonzero(files_repo, monkeypatch, capsys):
    code, out, err = run(files_repo({"i/aidlc-state.md": UNITS}), monkeypatch, capsys, "plan")
    assert code == 1  # Units Generation is first on the route, so the missing table is a current error
    (found,) = sarif_run(out)["results"]
    assert (found["ruleId"], found["level"], found["properties"]["stage"]) == (
        "earnest/route-mismatch",
        "error",
        "inception/units-generation",
    )
    assert "unsupported route" not in err


def test_check_stage_of_a_per_unit_stage_writes_its_run_header(files_repo, monkeypatch, capsys):
    table = "| Unit ID | Directory |\n| --- | --- |\n| A | a-dir |\n\n`unit~a~1`\n\nThe unit.\n"
    repo = files_repo({"i/aidlc-state.md": UNITS, UNIT_TABLE: table})
    stage = "construction/a-dir/code-generation"
    code, out, _ = run(repo, monkeypatch, capsys, "check", "--stage", stage)
    assert code == 0
    assert sarif_run(out)["properties"]["assessment"]["stage"] == f"i/{stage}"
    runs = json.loads((repo / ".earnest" / "assessment.json").read_text(encoding="utf-8"))["runs"]
    assert list(runs) == [f"i/{stage}"]


def test_plain_check_of_a_units_intent_without_a_table_places_its_needs_at_units_generation(
    files_repo, monkeypatch, capsys
):
    repo = files_repo(
        {"i/aidlc-state.md": UNITS, "i/inception/requirements-analysis/r.md": "`req~a~1`\n\nThe system shall work.\n"}
    )
    code, out, _ = run(repo, monkeypatch, capsys, "check")
    assert code == 1
    results = sarif_run(out)["results"]
    assert sorted((result["ruleId"], result["level"]) for result in results) == [
        ("earnest/gap", "error"),
        ("earnest/gap", "error"),
        ("earnest/route-mismatch", "error"),
        ("earnest/unplanned", "warning"),
    ]
    for result in results:
        assert (result["properties"]["position"], result["properties"]["stage"]) == (
            "current",
            "inception/units-generation",
        )


def test_plan_lists_every_intent_including_a_units_intent(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    other = "aidlc/spaces/default/intents/260927-other"
    write(repo, f"{other}/aidlc-state.md", UNITS)
    code, out, err = run(repo, monkeypatch, capsys, "plan")
    assert code == 1  # the units intent has no unit table
    assert [entry["intent"] for entry in sarif_run(out)["properties"]["plan"]["intents"]] == [RECORD, other]
    assert not [line for line in err.splitlines() if line.startswith("earnest:")]


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
    repo = files_repo({"i/aidlc-state.md": state, "docs/a.md": "`req~a~1`\n\nThe system shall work.\n"})
    code, out, err = run(repo, monkeypatch, capsys, "check")
    assert code == 1
    results = sarif_run(out)["results"]
    assert {result["ruleId"] for result in results} == {"earnest/route-mismatch", "earnest/orphaned", "earnest/gap"}
    assert err.splitlines()[0].startswith("traced 0%")  # the needs survive an emptied route, so no silent 100%
    (found,) = [result for result in results if result["ruleId"] == "earnest/route-mismatch"]
    assert located(found) == ("i/aidlc-state.md", 1)
    assert run(repo, monkeypatch, capsys, "plan")[0] == 1


def test_plain_check_of_a_units_intent_without_a_table_is_no_silent_pass(files_repo, monkeypatch, capsys):
    repo = files_repo({"i/aidlc-state.md": UNITS, "docs/a.md": "`req~a~1`\n\nThe system shall work.\n"})
    code, out, err = run(repo, monkeypatch, capsys, "check")
    assert code == 1
    log = sarif_run(out)
    assert {result["ruleId"] for result in log["results"]} == {"earnest/route-mismatch", "earnest/gap"}
    assert sorted(
        result["message"]["text"].split("`")[3] for result in log["results"] if result["ruleId"] == "earnest/gap"
    ) == [
        "impl",
        "utest",
    ]
    assert err.splitlines()[0].startswith("traced 0%")


# The task change (M3).


def test_a_task_option_that_names_no_task_exits_two_with_one_line(fixture_repo, monkeypatch, capsys):
    code, out, err = run(fixture_repo("seeded-change"), monkeypatch, capsys, "check", "--task", "task~nope~1")
    assert (code, out) == (2, "")
    assert len(err.splitlines()) == 1
    assert "task~nope~1" in err


def mark(repo, task):
    """Write the state file's Current Task line, uncommitted, as the coding agent would."""
    state = repo / RECORD / "aidlc-state.md"
    text = state.read_text(encoding="utf-8").replace(
        "## Project Information\n", f"## Project Information\n- **Current Task**: {task}\n", 1
    )
    state.write_text(text, encoding="utf-8")


def test_a_current_task_line_naming_no_task_gives_no_task_change_and_one_line(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    mark(repo, "task~unknown~1")
    write(repo, "src/checkout/auth.py", (repo / "src/checkout/auth.py").read_text(encoding="utf-8") + "\nX = 1\n")
    code, out, err = run(repo, monkeypatch, capsys, "check")
    assert code == 0
    log = sarif_run(out)
    assert not {"earnest/out-of-task", "earnest/impact-degraded"} & {result["ruleId"] for result in log["results"]}
    assert "impact" not in log["properties"]
    assert [line for line in err.splitlines() if "no current task" in line] == [
        "task change: no current task, as `task~unknown~1` names no task of its intent; no out-of-task check and no impact"
    ]


def test_a_current_task_in_no_intent_gives_no_task_change_and_one_line(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    write(repo, "docs/loose.md", "# Loose\n\n`task~stray~1`\n")  # a task outside every intent's record directory
    code, out, err = run(repo, monkeypatch, capsys, "check", "--task", "task~stray~1")
    assert code == 0
    log = sarif_run(out)
    assert not {"earnest/out-of-task", "earnest/impact-degraded"} & {result["ruleId"] for result in log["results"]}
    assert "impact" not in log["properties"]
    assert [line for line in err.splitlines() if line.startswith("task change:")] == [
        (
            "task change: the current task task~stray~1 lies in no intent, so no approved stage check gives a baseline;"
            " no out-of-task check and no impact"
        )
    ]


def test_a_stage_check_of_another_stage_leaves_out_of_task_out(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    record_baseline(repo)
    mark(repo, "task~add-limiter~1")
    write(repo, "src/checkout/auth.py", (repo / "src/checkout/auth.py").read_text(encoding="utf-8") + "\nX = 1\n")
    _, out, _ = run(repo, monkeypatch, capsys, "check")
    assert "earnest/out-of-task" in [result["ruleId"] for result in sarif_run(out)["results"]]
    _, out, _ = run(repo, monkeypatch, capsys, "check", "--stage", "inception/requirements-analysis")
    assert "earnest/out-of-task" not in [result["ruleId"] for result in sarif_run(out)["results"]]


def test_without_a_current_task_line_only_the_task_option_names_the_task(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    record_baseline(repo)
    write(repo, "src/checkout/auth.py", (repo / "src/checkout/auth.py").read_text(encoding="utf-8") + "\nX = 1\n")
    _, out, _ = run(repo, monkeypatch, capsys, "check")
    assert "earnest/out-of-task" not in [result["ruleId"] for result in sarif_run(out)["results"]]
    _, out, _ = run(repo, monkeypatch, capsys, "check", "--task", "task~add-limiter~1")
    assert "earnest/out-of-task" in [result["ruleId"] for result in sarif_run(out)["results"]]


def test_a_repository_without_a_plan_prints_no_task_change_line(files_repo, monkeypatch, capsys):
    repo = files_repo({"docs/a.md": "`req~a~1`\n\nThe system shall work.\n"})
    _, _, err = run(repo, monkeypatch, capsys, "check")
    assert "task change" not in err


def test_a_changed_audit_shard_or_state_file_raises_no_out_of_task(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    record_baseline(repo)
    for path in (f"{RECORD}/audit/fixture-a1b2c3d4.md", f"{RECORD}/aidlc-state.md", f"{RECORD}/audit/new.md"):
        target = repo / path
        write(repo, path, (target.read_text(encoding="utf-8") if target.exists() else "") + "\nmore\n")
    _, out, _ = run(repo, monkeypatch, capsys, "check", "--task", "task~add-limiter~1")
    assert "earnest/out-of-task" not in [result["ruleId"] for result in sarif_run(out)["results"]]


def test_a_current_task_with_no_changed_line_prints_no_impact(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    record_baseline(repo)
    _, out, err = run(repo, monkeypatch, capsys, "check", "--task", "task~add-limiter~1")
    assert "impact" not in sarif_run(out)["properties"]
    assert "impact:" not in err.splitlines()


def test_impact_reads_the_baseline_s_map_alone_not_the_map_the_record_names_last(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    base = record_baseline(repo)
    for taken in (repo / ".earnest/coverage").glob(f"{base}*"):  # the baseline's map, which this test's check took
        taken.unlink()
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "later", "--no-verify"], cwd=repo, check=True, env=_identity()
    )
    run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation")  # a map at a later commit
    assert record_of(repo)["coverage"]["commit"] not in {None, base}
    write(repo, "src/checkout/auth.py", (repo / "src/checkout/auth.py").read_text(encoding="utf-8") + "\nX = 1\n")
    _, _, err = run(repo, monkeypatch, capsys, "check", "--task", "task~add-limiter~1")
    assert f"  coverage map: none for the baseline commit {base}" in err.splitlines(), err


# The map a stage check takes, or the reason it takes none.


def record_of(repo):
    return json.loads((repo / ".earnest/assessment.json").read_text(encoding="utf-8"))


def test_a_stage_check_of_a_dirty_tree_takes_no_map_and_keeps_the_record_s_coverage(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation")
    first = record_of(repo)["coverage"]
    maps = sorted(path.name for path in (repo / ".earnest/coverage").iterdir())
    write(repo, "src/checkout/auth.py", (repo / "src/checkout/auth.py").read_text(encoding="utf-8") + "\nX = 1\n")
    subprocess.run(["git", "commit", "-qam", "next", "--no-verify"], cwd=repo, check=True, env=_identity())
    write(repo, "src/checkout/auth.py", (repo / "src/checkout/auth.py").read_text(encoding="utf-8") + "\nY = 1\n")
    code, _, err = run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation")
    assert code == 0
    assert record_of(repo)["coverage"] == first
    assert sorted(path.name for path in (repo / ".earnest/coverage").iterdir()) == maps
    assert "coverage map: not taken, the work tree is dirty" in err.splitlines()


def test_a_first_stage_check_of_a_dirty_tree_leaves_the_coverage_null(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    write(repo, "src/checkout/auth.py", (repo / "src/checkout/auth.py").read_text(encoding="utf-8") + "\nY = 1\n")
    run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation")
    assert record_of(repo)["coverage"] == {"commit": None}
    assert not (repo / ".earnest/coverage").exists()


def test_a_map_run_that_fails_keeps_the_record_s_coverage_and_says_why(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    monkeypatch.setattr(cli.impact, "take_map", lambda *_: "pytest exited 4 (usage error)")
    code, _, err = run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation")
    assert code == 0
    assert record_of(repo)["coverage"] == {"commit": None}
    assert "coverage map: not taken, pytest exited 4 (usage error)" in err.splitlines()


def _identity():
    return os.environ | {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }


NO_BASELINE = "task change: no approved stage check is recorded; no out-of-task check and no impact"


def test_no_approved_stage_check_drops_the_task_change_with_one_note(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    run(repo, monkeypatch, capsys, "check", "--stage", "inception/requirements-analysis")  # checked, never approved
    write(repo, "src/checkout/auth.py", (repo / "src/checkout/auth.py").read_text(encoding="utf-8") + "\nX = 1\n")
    code, out, err = run(repo, monkeypatch, capsys, "check", "--task", "task~add-limiter~1")
    assert code == 0
    rules = [result["ruleId"] for result in sarif_run(out)["results"]]
    assert not {"earnest/out-of-task", "earnest/impact-degraded"} & set(rules)
    assert "impact" not in sarif_run(out)["properties"]
    assert err.splitlines().count(NO_BASELINE) == 1


def test_a_baseline_commit_git_no_longer_holds_drops_the_task_change_with_one_note(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    record_baseline(repo)
    held = record_of(repo)
    gone = "f" * 40
    for header in held["runs"].values():
        header["commit"] = gone
    (repo / ".earnest/assessment.json").write_text(json.dumps(held), encoding="utf-8")
    write(repo, "src/checkout/auth.py", (repo / "src/checkout/auth.py").read_text(encoding="utf-8") + "\nX = 1\n")
    code, out, err = run(repo, monkeypatch, capsys, "check", "--task", "task~add-limiter~1")
    assert code == 0
    assert "impact" not in sarif_run(out)["properties"]
    note = f"task change: the approved stage check's commit {gone} is not in the repository; no out-of-task check and no impact"
    assert err.splitlines().count(note) == 1


def test_the_baseline_is_read_whatever_the_branch(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")
    record_baseline(repo)
    subprocess.run(["git", "checkout", "-q", "--detach"], cwd=repo, check=True)
    write(repo, "src/checkout/auth.py", (repo / "src/checkout/auth.py").read_text(encoding="utf-8") + "\nX = 1\n")
    _, out, _ = run(repo, monkeypatch, capsys, "check", "--task", "task~add-limiter~1")
    assert "earnest/out-of-task" in [result["ruleId"] for result in sarif_run(out)["results"]]


@pytest.mark.parametrize("value", [None, "foo:x", "stub:no-such-file.json", "stub:{list}"])
def test_judge_without_a_model_that_can_run_exits_two_with_one_line(fixture_repo, monkeypatch, capsys, tmp_path, value):
    if value == "stub:{list}":
        (tmp_path / "list.json").write_text("[]")
        value = f"stub:{tmp_path / 'list.json'}"
    if value is None:
        monkeypatch.delenv("EARNEST_JUDGE", raising=False)
    else:
        monkeypatch.setenv("EARNEST_JUDGE", value)
    code, out, err = run(fixture_repo("seeded-change"), monkeypatch, capsys, "check", "--judge")
    assert (code, out) == (2, "")
    assert len(err.splitlines()) == 1
    assert err.startswith("earnest: ")


VERDICT = {"result": "satisfied", "reasoning": "ok", "location": {"file": "src/checkout/auth.py", "line": 5}}
CANNED = {
    f"req~{name}~1": dict.fromkeys(judge.QUESTIONS, VERDICT) for name in ("rate-limit", "lockout-notice", "audit-log")
}


def canned_model(monkeypatch, tmp_path):
    path = tmp_path / "verdicts.json"
    path.write_text(json.dumps(CANNED))
    monkeypatch.setenv("EARNEST_JUDGE", f"stub:{path}")


def test_judge_names_its_model_and_prompt_in_the_invocation(fixture_repo, monkeypatch, capsys, tmp_path):
    canned_model(monkeypatch, tmp_path)
    code, out, _ = run(fixture_repo("seeded-change"), monkeypatch, capsys, "check", "--judge")
    (invocation,) = sarif_run(out)["invocations"]
    assert invocation["properties"]["layers"] == ["trace", "judge"]
    assert invocation["properties"]["model"].startswith("stub:sha256:")
    assert invocation["properties"]["prompt"].startswith("sha256:")
    assert len(sarif_run(out)["properties"]["observations"]) == 6
    assert code == 0


def test_a_judged_stage_check_names_the_judge_layer_model_and_prompt_in_its_run_header(
    fixture_repo, monkeypatch, capsys, tmp_path
):
    canned_model(monkeypatch, tmp_path)
    repo = fixture_repo("seeded-change")
    _, out, _ = run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation", "--judge")
    properties = sarif_run(out)["invocations"][0]["properties"]
    (held,) = json.loads((repo / ".earnest/assessment.json").read_text(encoding="utf-8"))["runs"].values()
    assert (held["layers"], held["model"], held["prompt"]) == (
        ["trace", "judge"],
        properties["model"],
        properties["prompt"],
    )


def test_evidence_implies_judge_so_without_a_model_it_exits_two(fixture_repo, monkeypatch, capsys):
    monkeypatch.delenv("EARNEST_JUDGE", raising=False)
    code, out, err = run(fixture_repo("seeded-change"), monkeypatch, capsys, "check", "--evidence")
    assert (code, out) == (2, "")
    assert err.startswith("earnest: ")


def recording(monkeypatch):
    """Replace `impact._run`: the suite run writes a passing JUnit report, and mutmut an empty result per file."""
    calls = []

    def fake(command, root, env):
        calls.append(command)
        for part in command:
            if part.startswith("--junitxml="):
                Path(part.partition("=")[2]).write_text("<testsuites/>", encoding="utf-8")
        if command[1:4] == ["-m", "mutmut", "run"]:
            config = configparser.ConfigParser(interpolation=None)
            config.read(root / "setup.cfg")
            for path in config["mutmut"]["source_paths"].split():
                (root / "mutants" / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(root / path, root / "mutants" / path)
                (root / "mutants" / f"{path}.meta").write_text('{"exit_code_by_key": {}}', encoding="utf-8")
        return 0

    monkeypatch.setattr(impact, "_run", fake)
    return calls


def test_check_with_evidence_runs_the_suite_and_mutmut_and_without_it_runs_neither(
    fixture_repo, monkeypatch, capsys, tmp_path
):
    canned_model(monkeypatch, tmp_path)
    repo = fixture_repo("seeded-change")
    calls = recording(monkeypatch)
    code, _, err = run(repo, monkeypatch, capsys, "check", "--evidence")
    assert code == 0, err
    suite, mutmut = calls
    assert any(part.startswith("--junitxml=") for part in suite)
    assert mutmut[1:] == ["-m", "mutmut", "run"]
    calls.clear()
    run(repo, monkeypatch, capsys, "check")
    run(repo, monkeypatch, capsys, "check", "--judge")
    assert calls == []
    run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation")
    assert [command for command in calls if "--junitxml" in " ".join(command) or "mutmut" in command] == []
    assert any("--cov-context=test" in command for command in calls)  # the coverage map's run, unchanged


def test_check_with_evidence_raises_each_judged_requirement_with_no_surviving_mutant_to_evidenced(
    fixture_repo, monkeypatch, capsys, tmp_path
):
    canned_model(monkeypatch, tmp_path)
    repo = fixture_repo("seeded-change")
    recording(monkeypatch)  # every mutated file gives no mutant, so nothing survives
    _, judged, _ = run(repo, monkeypatch, capsys, "check", "--judge")
    levels = sarif_run(judged)["properties"]["traceLevels"]
    assert set(levels.values()) == {"judged"}
    code, out, err = run(repo, monkeypatch, capsys, "check", "--evidence")
    assert code == 0, err
    shown = sarif_run(out)
    assert shown["properties"]["traceLevels"] == dict.fromkeys(levels, "evidenced")
    assert shown["properties"]["percentages"] == {"traced": 100, "judged": 100, "evidenced": 100}
    assert shown["invocations"][0]["properties"]["layers"] == ["trace", "judge", "evidence"]
    run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation", "--evidence")
    (held,) = json.loads((repo / ".earnest/assessment.json").read_text(encoding="utf-8"))["runs"].values()
    assert held["layers"] == ["trace", "judge", "evidence"]


def test_a_mutmut_that_cannot_run_exits_two_with_one_line(fixture_repo, monkeypatch, capsys, tmp_path):
    canned_model(monkeypatch, tmp_path)
    monkeypatch.setattr(impact, "_run", lambda *_: None)  # timed out
    code, out, err = run(fixture_repo("seeded-change"), monkeypatch, capsys, "check", "--evidence")
    assert (code, out) == (2, "")
    assert err.startswith("earnest: ")
    assert "timed out" in err
    assert len(err.splitlines()) == 1


ASSESSMENT = ".earnest/assessment.json"


def seed_evidence(repo, slot):
    """Write a record that M4 could have written, plus an `evidence` slot, ignored by Git as `.earnest/` is."""
    (repo / ".earnest").mkdir()
    (repo / ".earnest" / ".gitignore").write_text("*\n", encoding="utf-8")
    data = {"version": 1, "runs": {}, "bodies": {}, "coverage": {"commit": None}, "judge": {"cache": {}}}
    (repo / ASSESSMENT).write_text(json.dumps({**data, "calibration": None, "evidence": slot}), encoding="utf-8")


def held_evidence(repo):
    return json.loads((repo / ASSESSMENT).read_text(encoding="utf-8"))["evidence"]


STALE = {"key": {"regions": "old", "tests": "old", "tool": "mutmut 0"}, "result": "passed", "commit": "0" * 40}


def test_check_with_evidence_writes_each_entry_and_a_rerun_on_the_same_tree_writes_the_same_record(
    fixture_repo, monkeypatch, capsys, tmp_path
):
    canned_model(monkeypatch, tmp_path)
    repo = fixture_repo("seeded-change")
    recording(monkeypatch)  # nothing survives, so each judged requirement passes
    code, _, err = run(repo, monkeypatch, capsys, "check", "--evidence")
    assert code == 0, err
    first = (repo / ASSESSMENT).read_bytes()
    slot = held_evidence(repo)
    assert sorted(slot) == sorted(CANNED)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True)
    for entry in slot.values():
        assert (entry["result"], entry["commit"], entry["dirty"]) == ("passed", head.stdout.strip(), False)
        assert sorted(entry["key"]) == ["regions", "tests", "tool"]
        assert entry["key"]["tool"].startswith("mutmut ")
    run(repo, monkeypatch, capsys, "check", "--evidence")
    assert (repo / ASSESSMENT).read_bytes() == first
    (repo / ASSESSMENT).unlink()
    run(repo, monkeypatch, capsys, "check", "--stage", "construction/code-generation", "--evidence")
    assert held_evidence(repo) == slot  # the stage check writes the same slot


def test_a_failing_tagged_test_fails_its_requirement_drops_the_unreached_and_keeps_the_rest(
    fixture_repo, monkeypatch, capsys, tmp_path
):
    canned_model(monkeypatch, tmp_path)
    repo = fixture_repo("seeded-change")
    elsewhere = {**STALE, "result": "failed"}
    held = {f"req~{name}~1": STALE for name in ("rate-limit", "audit-log")}
    seed_evidence(repo, {**held, "req~elsewhere~1": elsewhere})
    calls = []
    failing = '<testsuites><testcase file="tests/test_auth.py" name="test_count_failed_logins"><failure/></testcase>'

    def fake(command, root, env):
        calls.append(command)
        for part in command:
            if part.startswith("--junitxml="):
                Path(part.partition("=")[2]).write_text(failing + "</testsuites>", encoding="utf-8")
        return 0

    monkeypatch.setattr(impact, "_run", fake)
    code, _, err = run(repo, monkeypatch, capsys, "check", "--evidence")
    assert code != 2, err
    assert not any("mutmut" in command for command in calls)  # with a failing test mutmut never runs
    slot = held_evidence(repo)
    assert sorted(slot) == ["req~elsewhere~1", "req~rate-limit~1"]  # lockout-notice and audit-log: no verdict
    assert slot["req~rate-limit~1"]["result"] == "failed"
    assert slot["req~rate-limit~1"]["key"] != STALE["key"]
    assert slot["req~elsewhere~1"] == elsewhere  # a requirement outside the run keeps its entry


def test_a_check_without_evidence_reads_the_slot_and_leaves_it_as_it_was(fixture_repo, monkeypatch, capsys, tmp_path):
    canned_model(monkeypatch, tmp_path)
    repo = fixture_repo("seeded-change")
    seed_evidence(repo, {"req~rate-limit~1": STALE})  # the key is not compared until stale keys are
    _, out, _ = run(repo, monkeypatch, capsys, "check")
    assert sarif_run(out)["properties"]["traceLevels"]["req~rate-limit~1"] == "evidenced"
    _, out, _ = run(repo, monkeypatch, capsys, "check", "--judge")
    levels = sarif_run(out)["properties"]["traceLevels"]
    assert (levels["req~rate-limit~1"], levels["req~audit-log~1"]) == ("evidenced", "judged")
    assert held_evidence(repo) == {"req~rate-limit~1": STALE}
