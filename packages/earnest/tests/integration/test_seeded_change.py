"""Integration: the seeded-change fixture holds the seeds and the overlay that the stage_status scenarios read."""

from earnest.index import MARKDOWN, Source, build_index, split_lines
from tests.sarif import PLAN_FILE, RECORD, REQUIREMENTS, SHARD, git_output


STATE = f"{RECORD}/aidlc-state.md"


def lines_of(repo, path):
    return (repo / path).read_text(encoding="utf-8").split("\n")


def test_base_commit_holds_the_seeded_lines(fixture_repo):
    repo = fixture_repo("seeded-change")
    state = lines_of(repo, STATE)
    assert state[5] == "- **Scope**: bugfix"
    assert [state[n - 1] for n in (11, 16, 21, 25)] == [
        "### INITIALIZATION PHASE",
        "### INCEPTION PHASE",
        "### CONSTRUCTION PHASE",
        "### OPERATION PHASE",
    ]
    rows = {state[n - 1].split(" ")[2]: state[n - 1].split(" ")[1] for n in (12, 13, 14, 17, 18, 19, 22, 23, 26, 27)}
    assert rows == {
        "workspace-scaffold": "[x]",
        "workspace-detection": "[x]",
        "state-init": "[x]",
        "reverse-engineering": "[S]",
        "requirements-analysis": "[x]",
        "units-generation": "[S]",
        "code-generation": "[x]",
        "build-and-test": "[x]",
        "deployment-pipeline": "[S]",
        "deployment-execution": "[S]",
    }
    requirements = lines_of(repo, REQUIREMENTS)
    assert [requirements[n - 1] for n in (3, 8, 13)] == [
        "`req~rate-limit~1`",
        "`req~lockout-notice~1`",
        "`req~audit-log~1`",
    ]
    assert requirements[10] == "when they may try again."
    plan = lines_of(repo, PLAN_FILE)
    assert [plan[n - 1] for n in (3, 9)] == ["`task~add-limiter~1`", "`task~notify-lockout~1`"]
    assert [plan[n - 1] for n in (7, 13, 14)] == [
        "Delivers: req~rate-limit~1",
        "Delivers: req~lockout-notice~1",
        "Depends: task~add-limiter~1",
    ]
    for path, kind in (("src/checkout/auth.py", "impl"), ("tests/test_auth.py", "utest")):
        code = lines_of(repo, path)
        assert [code[n - 1] for n in (4, 9, 14)] == [
            f"# [{kind}->req~rate-limit~1]",
            f"# [{kind}->req~lockout-notice~1]",
            f"# [{kind}->req~audit-log~1]",
        ]


def test_audit_shard_blocks_sit_at_the_seeded_lines(fixture_repo):
    shard = lines_of(fixture_repo("seeded-change"), SHARD)
    assert [n for n, text in enumerate(shard, 1) if text.startswith("## ")] == [1, 7, 14, 21, 28]
    assert [n for n, text in enumerate(shard, 1) if text == "---"] == [6, 13, 20, 27, 36]
    assert [shard[n - 1] for n in (3, 9, 16, 23, 30)] == [
        "**Event**: WORKFLOW_STARTED",
        "**Event**: STAGE_SKIPPED",
        "**Event**: STAGE_SKIPPED",
        "**Event**: STAGE_SKIPPED",
        "**Event**: GATE_APPROVED",
    ]
    assert shard[33] == "**Items**: req~audit-log~1, req~lockout-notice~1, req~rate-limit~1"
    assert shard[34] == "**Approved By**: human"


def test_overlay_is_committed_on_the_task_branch(fixture_repo, commit_overlay):
    repo = commit_overlay(fixture_repo("seeded-change"), "seeded-change", "task/add-limiter-window")
    assert git_output(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() == "task/add-limiter-window"
    assert git_output(repo, "rev-list", "--count", "main..HEAD").strip() == "1"


def test_overlay_changes_two_places_of_the_requirements(fixture_repo, commit_overlay):
    repo = commit_overlay(fixture_repo("seeded-change"), "seeded-change", "task/add-limiter-window")
    diff = git_output(repo, "diff", "--unified=0", "main", "HEAD")
    assert [line for line in diff.splitlines() if line.startswith("diff --git")] == [
        f"diff --git a/{REQUIREMENTS} b/{REQUIREMENTS}",
    ]
    hunks = [line.split(" @@")[0] + " @@" for line in diff.splitlines() if line.startswith("@@")]
    assert hunks == ["@@ -3 +3 @@", "@@ -5 +5 @@", "@@ -11 +11 @@"]
    requirements = lines_of(repo, REQUIREMENTS)
    assert requirements[2] == "`req~rate-limit~2`"
    assert requirements[4].endswith("for thirty minutes")
    assert requirements[10] == "how long the lockout lasts."


def test_base_copy_leaves_the_change_directory_out(fixture_repo):
    repo = fixture_repo("seeded-change")
    assert not (repo / "change").exists()
    assert "change/" not in git_output(repo, "ls-files")


def test_state_and_audit_files_hold_no_item_id_tag_or_near_miss(fixture_repo):
    repo = fixture_repo("seeded-change")
    sources = [
        Source(path, MARKDOWN, split_lines((repo / path).read_text(encoding="utf-8"))) for path in (STATE, SHARD)
    ]
    index = build_index(sources)
    assert (index.items, index.links, index.near_misses) == ((), (), ())
