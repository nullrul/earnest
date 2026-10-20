"""Integration: the coverage map a stage check takes over seeded-change, and the task change read against it."""

from earnest import impact
from tests.sarif import git_output, record, run_earnest


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
