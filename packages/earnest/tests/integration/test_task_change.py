"""Integration: the coverage map a stage check takes over seeded-change, and the task change read against it."""

import json

from earnest import impact
from tests.sarif import append_block, git_output, header, located, printed_hash, record, record_baseline, run_earnest


CODE_STAGE = "construction/code-generation"
TASK = ("--task", "task~add-limiter~1")


def test_the_stage_check_maps_each_test_to_the_lines_it_runs_and_leaves_git_status_empty(fixture_repo):
    repo = fixture_repo("seeded-change")
    done = run_earnest(repo, "check", "--stage", CODE_STAGE)
    assert done.returncode == 0, done.stderr
    commit = git_output(repo, "rev-parse", "HEAD").strip()
    assert record(repo)["coverage"] == {"commit": commit}
    found = impact.read_map(repo, commit)
    assert found[("src/checkout/auth.py", 6)] == (
        "tests/test_auth.py::test_audit_lockout",
        "tests/test_auth.py::test_count_failed_logins",
    )
    assert found[("src/checkout/auth.py", 11)] == ("tests/test_auth.py::test_lockout_message",)
    assert git_output(repo, "status", "--porcelain", "--untracked-files=all") == ""
    assert not list(repo.rglob("__pycache__"))
    assert not (repo / ".pytest_cache").exists()
    assert not (repo / ".coverage").exists()


AUTH = "src/checkout/auth.py"


def commit_all(repo, message):
    git_output(repo, "add", "-A")
    git_output(
        repo, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--no-verify", "-m", message
    )


def lines_of(repo, path):
    return (repo / path).read_text(encoding="utf-8").split("\n")


def write_lines(repo, path, lines):
    (repo / path).write_text("\n".join(lines), encoding="utf-8")


SHARD = "aidlc/spaces/default/intents/260926-checkout/audit/other.md"


def test_a_line_deleted_since_the_baseline_selects_the_tests_the_baseline_s_map_saw_run_it(fixture_repo):
    repo = fixture_repo("seeded-change")
    record_baseline(repo)
    lines = lines_of(repo, AUTH)
    del lines[10]  # `return "Try again later."`, which test_lockout_message runs
    write_lines(repo, AUTH, lines)
    done = run_earnest(repo, "check", *TASK)
    found = json.loads(done.stdout)["runs"][0]
    assert found["properties"]["impact"]["tests"] == ["tests/test_auth.py::test_lockout_message"]
    assert found["properties"]["impact"]["degraded"] is False
    assert "earnest/out-of-task" not in [result["ruleId"] for result in found["results"]]  # a deletion raises none


def degraded_lines(done):
    return [
        result["locations"][0]["physicalLocation"]["region"]["startLine"]
        for result in json.loads(done.stdout)["runs"][0]["results"]
        if result["ruleId"] == "earnest/impact-degraded"
        and result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == AUTH
    ]


def test_two_stage_checks_give_the_same_hash_though_only_the_first_reads_a_coverage_map(fixture_repo):
    repo = fixture_repo("seeded-change")
    base = record_baseline(repo)
    code = lines_of(repo, AUTH)
    del code[10]  # `return "Try again later."`: the map saw test_lockout_message run it, so only its absence degrades
    write_lines(repo, AUTH, code)
    commit_all(repo, "delete")
    first = run_earnest(repo, "check", "--stage", CODE_STAGE, *TASK)
    for taken in (repo / ".earnest/coverage").glob(f"{base}*"):  # the baseline's map, which this test's check took
        taken.unlink()
    second = run_earnest(repo, "check", "--stage", CODE_STAGE, *TASK)
    assert (degraded_lines(first), degraded_lines(second)) == ([], [10])
    assert printed_hash(first) == printed_hash(second)


def test_a_file_deleted_since_the_baseline_is_read_by_impact_and_a_deleted_audit_shard_is_not(fixture_repo):
    repo = fixture_repo("seeded-change")
    (repo / SHARD).write_text("# Other\n", encoding="utf-8")
    commit_all(repo, "a second shard")
    record_baseline(repo)
    git_output(repo, "rm", "-q", AUTH, SHARD)
    found = json.loads(run_earnest(repo, "check", *TASK).stdout)["runs"][0]
    task_change = [
        (located(result), result["properties"].get("stage"), result["level"])
        for result in found["results"]
        if result["ruleId"] in {"earnest/impact-degraded", "earnest/out-of-task"}
    ]
    # every base line of auth.py but 6, 11 and 16, which tests ran, at line 1 of the deleted path, reaching no stage
    assert task_change == [((AUTH, 1), None, "note")] * 13
    assert found["properties"]["impact"]["tests"] == [
        "tests/test_auth.py::test_audit_lockout",
        "tests/test_auth.py::test_count_failed_logins",
        "tests/test_auth.py::test_lockout_message",
    ]
    assert found["properties"]["impact"]["degraded"] is True


UNIT_STAGE = "construction/u1-limiter/functional-design"


def test_on_a_units_route_a_per_unit_stage_check_approved_at_its_unit_s_gate_is_the_baseline(units_repo):
    repo = units_repo()
    done = run_earnest(repo, "check", "--stage", UNIT_STAGE)
    assert done.returncode != 2, done.stderr
    held = header(repo, UNIT_STAGE)
    unit_gate = [
        ("Stage", "functional-design"),
        ("Unit", "u1"),
        ("Gate Scope", "per-stage"),
        ("Gate Stages", "functional-design"),
        ("Attempt Generation", "1"),
        ("Assessment Hash", held["hash"]),
        ("Approved By", "human"),
    ]
    append_block(repo, "GATE_APPROVED", "2026-09-27T12:00:00Z", unit_gate)
    commit_all(repo, "the unit's gate")
    code = lines_of(repo, AUTH)
    code[10] = code[10].replace("later", "soon")  # a line test_lockout_message runs, in the task's own region
    write_lines(repo, AUTH, code)
    commit_all(repo, "a change since the baseline")
    done = run_earnest(repo, "check", *TASK)
    assert "no approved stage check" not in done.stderr
    # the diff runs from the header's commit, so the change committed since it is in the impact
    assert json.loads(done.stdout)["runs"][0]["properties"]["impact"]["tests"] == [
        "tests/test_auth.py::test_lockout_message"
    ]
    assert held["commit"] != git_output(repo, "rev-parse", "HEAD").strip()
