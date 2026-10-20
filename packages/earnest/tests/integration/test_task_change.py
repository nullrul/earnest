"""Integration: the coverage map a stage check takes over seeded-change, and the task change read against it."""

import json

from earnest import impact
from tests.sarif import git_output, located, printed_hash, record, run_earnest


CODE_STAGE = "construction/code-generation"


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


def test_a_map_taken_after_the_base_is_read_through_a_deletion_since_its_commit(fixture_repo):
    repo = fixture_repo("seeded-change")
    git_output(repo, "checkout", "-q", "-b", "task/add-limiter-window")
    lines = lines_of(repo, AUTH)
    lines[5] = "    return min(window, 5)"
    lines.insert(5, "    # the window is capped")  # line 6 at A; the return moves to line 7
    write_lines(repo, AUTH, lines)
    commit_all(repo, "a")
    assert run_earnest(repo, "check", "--stage", CODE_STAGE).returncode == 0
    commit = git_output(repo, "rev-parse", "HEAD").strip()
    assert record(repo)["coverage"] == {"commit": commit}
    del lines[5]  # since A only a deletion; since the base only line 6 is modified
    write_lines(repo, AUTH, lines)
    done = run_earnest(repo, "check")
    impact_property = json.loads(done.stdout)["runs"][0]["properties"]["impact"]
    assert impact_property == {
        "requirements": ["req~rate-limit~1"],
        "features": [],
        # from the map's line 7, not the tags' choice for the line, which leaves test_audit_lockout out
        "tests": ["tests/test_auth.py::test_audit_lockout", "tests/test_auth.py::test_count_failed_logins"],
        "degraded": False,
    }


def test_a_line_deleted_since_the_base_selects_the_tests_the_map_at_the_base_saw_run_it(fixture_repo):
    repo = fixture_repo("seeded-change")
    assert run_earnest(repo, "check", "--stage", CODE_STAGE).returncode == 0
    git_output(repo, "checkout", "-q", "-b", "task/add-limiter-window")
    lines = lines_of(repo, AUTH)
    del lines[10]  # `return "Try again later."`, which test_lockout_message runs
    write_lines(repo, AUTH, lines)
    done = run_earnest(repo, "check")
    found = json.loads(done.stdout)["runs"][0]
    assert found["properties"]["impact"]["tests"] == ["tests/test_auth.py::test_lockout_message"]
    assert found["properties"]["impact"]["degraded"] is False
    assert "earnest/out-of-task" not in [result["ruleId"] for result in found["results"]]  # a deletion raises none


def test_two_stage_checks_on_a_task_branch_give_the_same_hash_though_the_first_takes_the_map(fixture_repo):
    repo = fixture_repo("seeded-change")
    git_output(repo, "checkout", "-q", "-b", "task/add-limiter-window")
    code = lines_of(repo, AUTH)
    code[1:3] = ["def helper() -> int:", "    return 1"]  # in no tag region, and run only by a test
    write_lines(repo, AUTH, code)
    tests = lines_of(repo, "tests/test_auth.py")
    tests[1] = "from checkout.auth import audit_lockout, count_failed_logins, helper, lockout_message"
    tests[5] = "    assert count_failed_logins(3) == 3 * helper()"
    write_lines(repo, "tests/test_auth.py", tests)
    commit_all(repo, "helper")
    first = run_earnest(repo, "check", "--stage", CODE_STAGE)
    second = run_earnest(repo, "check", "--stage", CODE_STAGE)
    degraded = [
        [
            result["locations"][0]["physicalLocation"]["region"]["startLine"]
            for result in json.loads(run.stdout)["runs"][0]["results"]
            if result["ruleId"] == "earnest/impact-degraded"
            and result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == AUTH
        ]
        for run in (first, second)
    ]
    assert degraded == [[2, 3], [2]]  # the map the first run took sees line 3 run by a test
    assert printed_hash(first) == printed_hash(second)


def test_a_file_deleted_since_the_base_is_read_by_impact_and_a_deleted_audit_shard_is_not(fixture_repo):
    repo = fixture_repo("seeded-change")
    assert run_earnest(repo, "check", "--stage", CODE_STAGE).returncode == 0
    git_output(repo, "checkout", "-q", "-b", "task/add-limiter-window")
    git_output(repo, "rm", "-q", AUTH, "aidlc/spaces/default/intents/260926-checkout/audit/fixture-a1b2c3d4.md")
    found = json.loads(run_earnest(repo, "check").stdout)["runs"][0]
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
