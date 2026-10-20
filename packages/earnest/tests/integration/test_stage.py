"""Integration: `earnest plan` and `earnest check --stage` over the seeded-change repository, through the script."""

import json
import os
import re

import pytest

from earnest import cli, reporter
from tests.sarif import PLAN_FILE, RECORD, REQUIREMENTS, SHARD, git_output, located, run_earnest, sarif_run


REQ_STAGE = "inception/requirements-analysis"
CODE_STAGE = "construction/code-generation"
HASH = re.compile(r"^assessment \S+: (sha256:[0-9a-f]{64}) \((?:done|not done)\)$", re.MULTILINE)


def record_of(repo):
    return json.loads((repo / ".earnest" / "assessment.json").read_text(encoding="utf-8"))


def edit(repo, path, old, new):
    text = (repo / path).read_text(encoding="utf-8")
    assert old in text
    (repo / path).write_text(text.replace(old, new), encoding="utf-8")


def stage_check(repo, stage):
    done = run_earnest(repo, "check", "--stage", stage)
    assert done.returncode in {0, 1}, done.stderr
    return done


def table(done):
    return sorted(
        (
            r["ruleId"],
            located(r)[0],
            located(r)[1],
            r["level"],
            r["properties"]["position"],
            r["properties"].get("stage"),
        )
        for r in sarif_run(done.stdout)["results"]
    )


def test_plan_is_read_only_and_prints_the_route(fixture_repo):
    repo = fixture_repo("seeded-change")
    done = run_earnest(repo, "plan")
    assert done.returncode == 0, done.stderr
    entry = sarif_run(done.stdout)["properties"]["plan"]["intents"][0]
    assert [(s["stage"], s["status"], s["approval"], s["approvedBy"]) for s in entry["stages"]] == [
        (REQ_STAGE, "done", "current", "human"),
        (CODE_STAGE, "not done", "none", None),
        ("construction/build-and-test", "not done", "none", None),
    ]
    assert entry["frontier"] == CODE_STAGE
    assert git_output(repo, "status", "--porcelain", "--untracked-files=all") == ""
    assert not (repo / ".earnest").exists()


def test_plan_stderr_lists_the_tasks(fixture_repo):
    lines = run_earnest(fixture_repo("seeded-change"), "plan").stderr.splitlines()
    assert f"intent {RECORD}" in lines
    assert "  task task~add-limiter~1: not done" in lines
    assert "  task task~notify-lockout~1: not done" in lines
    assert f"  frontier: {CODE_STAGE}" in lines


def test_plan_properties_are_an_intents_list(fixture_repo):
    props = sarif_run(run_earnest(fixture_repo("seeded-change"), "plan").stdout)["properties"]
    assert set(props["plan"]) == {"intents"}
    (entry,) = props["plan"]["intents"]
    assert set(entry) == {"intent", "stages", "frontier", "tasks", "units"}
    assert (entry["intent"], entry["units"]) == (RECORD, [])
    assert [task["id"] for task in entry["tasks"]] == ["task~add-limiter~1", "task~notify-lockout~1"]


def test_check_carries_properties_plan(fixture_repo):
    repo = fixture_repo("seeded-change")
    plain = sarif_run(run_earnest(repo, "check").stdout)["properties"]
    staged = sarif_run(stage_check(repo, CODE_STAGE).stdout)["properties"]
    assert plain["plan"]["intents"][0]["frontier"] == staged["plan"]["intents"][0]["frontier"] == CODE_STAGE
    assert "assessment" not in plain
    assert set(staged["assessment"]) == {"stage", "hash", "status", "reasons"}


def test_check_stage_writes_the_header_and_the_marker(fixture_repo):
    repo = fixture_repo("seeded-change")
    done = stage_check(repo, CODE_STAGE)
    assert (repo / ".earnest" / ".gitignore").read_text(encoding="utf-8") == "*\n"
    held = record_of(repo)["runs"][f"{RECORD}/{CODE_STAGE}"]
    assert held["commit"] == git_output(repo, "rev-parse", "HEAD").strip()
    assert (held["dirty"], held["layers"], held["status"]) == (False, ["trace"], "not done")
    assert held["items"] == ["task~add-limiter~1", "task~notify-lockout~1"]
    assert held["reasons"] == {"errors": 0, "openTasks": 2, "approval": "none"}
    assert held["hash"] == HASH.search(done.stderr).group(1)
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", held["timestamp"])


def test_the_hash_ignores_the_commit_of_the_run(fixture_repo):
    repo = fixture_repo("seeded-change")
    first = stage_check(repo, CODE_STAGE)
    first_held = record_of(repo)["runs"][f"{RECORD}/{CODE_STAGE}"]
    git_output(
        repo, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-q", "--allow-empty", "--no-verify", "-m", "x"
    )
    second = stage_check(repo, CODE_STAGE)
    held = record_of(repo)["runs"][f"{RECORD}/{CODE_STAGE}"]
    assert held["commit"] != first_held["commit"]
    assert (
        held["hash"] == first_held["hash"] == HASH.search(second.stderr).group(1) == HASH.search(first.stderr).group(1)
    )


def test_the_first_stage_check_counts_its_items_without_a_held_hash_and_does_not_call_the_record_absent(fixture_repo):
    repo = fixture_repo("seeded-change")
    lines = stage_check(repo, CODE_STAGE).stderr.splitlines()
    assert "body-hash baseline: 2 items without a held hash" in lines
    assert "record: absent, body-hash baseline unavailable" not in lines
    assert not [line for line in stage_check(repo, CODE_STAGE).stderr.splitlines() if "baseline" in line]


def test_plan_without_a_record_says_so_and_counts_no_baseline(fixture_repo):
    lines = run_earnest(fixture_repo("seeded-change"), "plan").stderr.splitlines()
    assert "record: absent, body-hash baseline unavailable" in lines
    assert not [line for line in lines if line.startswith("body-hash baseline")]


def test_runs_are_keyed_by_intent_directory_and_stage(fixture_repo):
    repo = fixture_repo("seeded-change")
    stage_check(repo, CODE_STAGE)
    stage_check(repo, REQ_STAGE)
    assert sorted(record_of(repo)["runs"]) == [f"{RECORD}/{CODE_STAGE}", f"{RECORD}/{REQ_STAGE}"]


def test_two_stage_checks_print_the_same_hash_and_log(fixture_repo):
    repo = fixture_repo("seeded-change")
    first, second = stage_check(repo, CODE_STAGE), stage_check(repo, CODE_STAGE)
    assert HASH.search(first.stderr).group(1) == HASH.search(second.stderr).group(1)
    assert first.stdout == second.stdout


def test_a_failed_record_write_exits_two_with_empty_stdout(fixture_repo, monkeypatch, capsys):
    repo = fixture_repo("seeded-change")

    def refuse(root, record):
        message = "disk full"
        raise OSError(message)

    monkeypatch.setattr(reporter, "write_record", refuse)
    monkeypatch.chdir(repo)
    assert cli.main(["check", "--stage", CODE_STAGE]) == 2
    assert capsys.readouterr() == ("", "earnest: disk full\n")
    assert not (repo / ".earnest").exists()


def test_check_without_stage_writes_nothing_and_says_the_record_is_absent(fixture_repo):
    repo = fixture_repo("seeded-change")
    done = run_earnest(repo, "check")
    assert not (repo / ".earnest").exists()
    assert "record: absent, body-hash baseline unavailable" in done.stderr.splitlines()
    assert git_output(repo, "status", "--porcelain", "--untracked-files=all") == ""


def test_broken_links_output_is_unchanged_except_dirty_and_the_record_absent_line(fixture_repo):
    done = run_earnest(fixture_repo("broken-links"), "check")
    assert done.returncode == 1
    log = sarif_run(done.stdout)
    assert set(log["properties"]) == {"traceLevels", "percentages"}
    assert log["invocations"][0]["properties"] == {
        "commit": log["invocations"][0]["properties"]["commit"],
        "dirty": False,
        "layers": ["trace"],
    }
    for result in log["results"]:
        assert result["properties"]["position"] == "current"
        assert "stage" not in result["properties"]
        assert result["message"]["text"].startswith("in scope: ")
    lines = done.stderr.splitlines()
    assert lines[0].startswith("traced ")
    assert lines[1] == "record: absent, body-hash baseline unavailable"
    assert lines[2].startswith("  req~")


def test_audit_row_leaves_hash_and_dirty_unchanged(fixture_repo):
    repo = fixture_repo("seeded-change")
    first = stage_check(repo, CODE_STAGE)
    shard = repo / SHARD
    block = "## Gate Approved\n**Timestamp**: 2026-09-26T12:00:00Z\n**Event**: GATE_APPROVED\n"
    shard.write_text(
        shard.read_text(encoding="utf-8") + block + "**Stage**: code-generation\n**Items**: task~add-limiter~1\n---\n",
        encoding="utf-8",
    )
    second = stage_check(repo, CODE_STAGE)
    assert HASH.search(first.stderr).group(1) == HASH.search(second.stderr).group(1)
    assert record_of(repo)["runs"][f"{RECORD}/{CODE_STAGE}"]["dirty"] is False


def test_plain_check_raises_no_unbumped_change_on_a_hash_no_row_names(fixture_repo):
    repo = fixture_repo("seeded-change")
    stage_check(repo, CODE_STAGE)
    edit(repo, PLAN_FILE, "Tell the member when the lockout starts.", "Tell the member when it starts.")
    rules = {result["ruleId"] for result in sarif_run(run_earnest(repo, "check").stdout)["results"]}
    assert "earnest/unbumped-change" not in rules


def test_stage_check_before_the_approval_replaces_the_held_hash(fixture_repo):
    repo = fixture_repo("seeded-change")
    stage_check(repo, CODE_STAGE)
    before = record_of(repo)["bodies"]["task~notify-lockout~1"]
    edit(repo, PLAN_FILE, "Tell the member when the lockout starts.", "Tell the member when it starts.")
    stage_check(repo, CODE_STAGE)
    assert record_of(repo)["bodies"]["task~notify-lockout~1"] != before


def test_overlay_findings_match_the_scenario_table(fixture_repo, commit_overlay):
    repo = fixture_repo("seeded-change")
    stage_check(repo, REQ_STAGE)
    commit_overlay(repo, "seeded-change", "task/add-limiter-window")
    done = run_earnest(repo, "check")
    assert done.returncode == 1
    assert table(done) == sorted(
        [
            ("earnest/unbumped-change", REQUIREMENTS, 8, "error", "current", REQ_STAGE),
            ("earnest/outdated", REQUIREMENTS, 3, "note", "current", REQ_STAGE),
            ("earnest/outdated", PLAN_FILE, 7, "note", "ahead", CODE_STAGE),
            ("earnest/outdated", "src/checkout/auth.py", 4, "note", "ahead", CODE_STAGE),
            ("earnest/outdated", "tests/test_auth.py", 4, "note", "ahead", CODE_STAGE),
            ("earnest/unplanned", REQUIREMENTS, 13, "note", "ahead", CODE_STAGE),
            ("earnest/out-of-task", REQUIREMENTS, 5, "warning", "current", CODE_STAGE),
            ("earnest/out-of-task", REQUIREMENTS, 11, "warning", "current", CODE_STAGE),
            ("earnest/impact-degraded", REQUIREMENTS, 3, "note", "current", REQ_STAGE),
            ("earnest/impact-degraded", REQUIREMENTS, 5, "note", "current", REQ_STAGE),
            ("earnest/impact-degraded", REQUIREMENTS, 11, "note", "current", REQ_STAGE),
        ]
    )


def test_route_mismatch_fails_the_stage_check_of_any_stage(fixture_repo):
    repo = fixture_repo("seeded-change")
    text = (repo / SHARD).read_text(encoding="utf-8")
    start = text.index("## Stage Skipped\n**Timestamp**: 2026-09-26T09:20:00Z")
    end = text.index("---\n", start) + 4
    (repo / SHARD).write_text(text[:start] + text[end:], encoding="utf-8")
    done = stage_check(repo, REQ_STAGE)
    assert done.returncode == 1
    assert [r["ruleId"] for r in sarif_run(done.stdout)["results"]] == ["earnest/route-mismatch"]


def test_plain_check_prints_the_count_of_indexed_items_without_a_held_hash(fixture_repo):
    repo = fixture_repo("seeded-change")
    stage_check(repo, CODE_STAGE)  # holds the two tasks; the record now exists
    assert "body-hash baseline: 3 items without a held hash" in run_earnest(repo, "check").stderr.splitlines()


def test_plan_exits_zero_where_check_exits_one_on_the_overlay(fixture_repo, commit_overlay):
    repo = fixture_repo("seeded-change")
    stage_check(repo, REQ_STAGE)
    commit_overlay(repo, "seeded-change", "task/add-limiter-window")
    assert run_earnest(repo, "check").returncode == 1  # the unbumped change is an error against the requirements stage
    assert run_earnest(repo, "plan").returncode == 0  # and a plan reports only what the plan itself raises


def test_the_header_records_the_errors_and_open_tasks_that_hold_a_stage_back(fixture_repo, commit_overlay):
    repo = fixture_repo("seeded-change")
    stage_check(repo, REQ_STAGE)
    commit_overlay(repo, "seeded-change", "task/add-limiter-window")
    stage_check(repo, REQ_STAGE)
    stage_check(repo, CODE_STAGE)
    runs = record_of(repo)["runs"]
    assert runs[f"{RECORD}/{REQ_STAGE}"]["reasons"] == {"errors": 1, "openTasks": 0, "approval": "outdated"}
    assert runs[f"{RECORD}/{CODE_STAGE}"]["reasons"] == {"errors": 0, "openTasks": 2, "approval": "none"}


def test_plan_results_include_the_stale_approval_note(fixture_repo, commit_overlay):
    repo = fixture_repo("seeded-change")
    commit_overlay(repo, "seeded-change", "task/add-limiter-window")
    done = run_earnest(repo, "plan")
    assert table(done) == [
        ("earnest/outdated", REQUIREMENTS, 3, "note", "current", REQ_STAGE),
        ("earnest/unplanned", REQUIREMENTS, 13, "note", "ahead", CODE_STAGE),
    ]


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads any file")
def test_an_unreadable_audit_shard_exits_two_with_one_line(fixture_repo):
    repo = fixture_repo("seeded-change")
    (repo / SHARD).chmod(0o000)
    try:
        done = run_earnest(repo, "plan")
    finally:
        (repo / SHARD).chmod(0o644)
    assert (done.returncode, done.stdout) == (2, "")
    assert done.stderr.startswith("earnest: ")
    assert len(done.stderr.splitlines()) == 1
