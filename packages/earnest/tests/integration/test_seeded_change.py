"""Integration: the seeded-change fixture holds the seeds, the overlay and the units variant that the scenarios read."""

from pathlib import Path

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


def test_base_commit_holds_the_m3_seeds(fixture_repo):
    repo = fixture_repo("seeded-change")
    assert lines_of(repo, "pytest.ini")[:2] == ["[pytest]", "pythonpath = src"]
    tests = lines_of(repo, "tests/test_auth.py")
    assert [tests[n - 1].strip() for n in (2, 6, 11, 16)] == [
        "from checkout.auth import audit_lockout, count_failed_logins, lockout_message",
        "assert count_failed_logins(3) == 3",
        'assert lockout_message().startswith("Try again")',
        'assert audit_lockout(str(count_failed_logins(1))) == "1"',
    ]


def test_task_overlay_changes_three_lines_of_the_code(fixture_repo, commit_task_change):
    repo = commit_task_change(fixture_repo("seeded-change"), "task/add-limiter-window")
    assert git_output(repo, "rev-list", "--count", "main..HEAD").strip() == "2"
    diff = git_output(repo, "diff", "--unified=0", "HEAD~1", "HEAD")
    assert [line for line in diff.splitlines() if line.startswith("diff --git")] == [
        "diff --git a/src/checkout/auth.py b/src/checkout/auth.py",
    ]
    hunks = [line.split(" @@")[0] + " @@" for line in diff.splitlines() if line.startswith("@@")]
    assert hunks == ["@@ -2 +2 @@", "@@ -6 +6 @@", "@@ -11 +11 @@"]
    code = lines_of(repo, "src/checkout/auth.py")
    assert [code[n - 1].strip() for n in (2, 6, 11)] == [
        "LIMIT = 5",
        "return min(window, LIMIT)",
        'return "Try again in fifteen minutes."',
    ]
    assert [code[n - 1] for n in (4, 9, 14)] == [
        "# [impl->req~rate-limit~1]",
        "# [impl->req~lockout-notice~1]",
        "# [impl->req~audit-log~1]",
    ]
    assert not (repo / "task").exists()


def test_base_copy_leaves_the_change_directory_out(fixture_repo):
    repo = fixture_repo("seeded-change")
    assert not (repo / "change").exists()
    assert not (repo / "task").exists()
    assert not any(path.startswith(("change/", "task/")) for path in git_output(repo, "ls-files").split())


def test_state_and_audit_files_hold_no_item_id_tag_or_near_miss(fixture_repo):
    repo = fixture_repo("seeded-change")
    sources = [
        Source(path, MARKDOWN, split_lines((repo / path).read_text(encoding="utf-8"))) for path in (STATE, SHARD)
    ]
    index = build_index(sources)
    assert (index.items, index.links, index.near_misses) == ((), (), ())


# The units variant: the base files with the intent's record directory taken from the `units/` overlay.

UNITS = f"{RECORD}/inception/units-generation/unit-of-work.md"


def test_base_copy_leaves_the_units_directory_out(fixture_repo):
    repo = fixture_repo("seeded-change")
    assert not (repo / "units").exists()
    assert "units/" not in git_output(repo, "ls-files")


def test_units_variant_replaces_only_the_record_directory(units_repo):
    repo = units_repo()
    files = git_output(repo, "ls-files").split()
    assert not (repo / RECORD / "construction" / "code-generation").exists()
    assert [path for path in files if path.endswith("aidlc-state.md")] == [STATE]
    assert [path for path in files if not path.startswith(RECORD)] == [
        "pytest.ini",
        "src/checkout/auth.py",
        "tests/test_auth.py",
    ]
    assert not any("FUTURE-FORMAT" in path or path.startswith(("units/", "change/", "task/")) for path in files)


def test_units_requirements_are_a_byte_copy_of_the_base():
    fixture = Path(__file__).parents[1] / "fixtures" / "seeded-change"
    assert (fixture / "units" / REQUIREMENTS).read_bytes() == (fixture / REQUIREMENTS).read_bytes()


def test_units_bookkeeping_and_table_hold_no_item_tag_or_near_miss(units_repo):
    repo = units_repo()
    table = "\n".join(lines_of(repo, UNITS)[:7])
    texts = [
        (STATE, (repo / STATE).read_text(encoding="utf-8")),
        (SHARD, (repo / SHARD).read_text(encoding="utf-8")),
    ]
    sources = [Source(path, MARKDOWN, split_lines(text)) for path, text in [*texts, (UNITS, table)]]
    index = build_index(sources)
    assert (index.items, index.links, index.near_misses) == ((), (), ())


def test_units_fixture_lines_sit_where_the_scenarios_read_them(units_repo):
    repo = units_repo()
    state = lines_of(repo, STATE)
    assert state[19] == "- [x] units-generation — EXECUTE: two units"
    assert "- [x] code-generation — EXECUTE: always" in state
    assert "| u1 | - | [x] | [x] | [x] |" in state
    units = lines_of(repo, UNITS)
    assert [units[n - 1] for n in (3, 5, 6, 10, 14, 16, 20, 21)] == [
        "| Unit ID | Directory | Responsibility |",
        "| U1 | u1-limiter | Count failed logins and lock the member out |",
        "| U2 | u2-notice | Tell a locked-out member when to try again |",
        "`unit~u1~1`",
        "Delivers: req~rate-limit~1",
        "`unit~u2~1`",
        "Delivers: req~lockout-notice~1",
        "Depends: unit~u1~1",
    ]
    assert units[6] == ""  # the table ends at line 6, so a row added after it lands at line 7
    for directory, item in (("u1-limiter", "`dsn~window-counter~1`"), ("u2-notice", "`dsn~notice-text~1`")):
        assert lines_of(repo, f"{RECORD}/construction/{directory}/functional-design/functional-spec.md")[2] == item
    assert lines_of(repo, REQUIREMENTS)[12] == "`req~audit-log~1`"
    shard = (repo / SHARD).read_text(encoding="utf-8")
    assert shard.count("**Event**: GATE_APPROVED") == 3
    assert (
        "**Unit**: u1\n**Gate Scope**: per-stage\n**Gate Stages**: functional-design\n**Attempt Generation**: 1\n"
        in shard
    )
