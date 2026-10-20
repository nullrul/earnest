"""Steps for tests/features/task_change.feature: out-of-task findings and impact on seeded-change's task branch."""

from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import FIXTURES, _git, write_overlays
from tests.sarif import (
    PLAN_FILE,
    REQUIREMENTS,
    SHARD,
    git_output,
    header,
    intent_plan,
    read,
    record,
    results,
    rows,
    run_earnest,
    sarif_run,
    write,
)


scenarios("task_change.feature")

TASK_BRANCH = "task/add-limiter-window"
BASE = FIXTURES / "seeded-change"
# The body line of each task a step adds to the plan; "the same six-line shape" leaves the text to the step.
TASK_BODIES = {"task~tell-wait~1": "Tell the member how long to wait.", "task~add~1": "Record each lockout."}
FIELDS = ("requirements", "features", "tests", "degraded")


def messages(run, rule):
    return [result["message"]["text"] for result in results(run) if result["ruleId"] == rule]


def exits(text):
    """Return the exits an out-of-task message offers: the `; `-separated list after `exits: `."""
    _, found, listed = text.partition("exits: ")
    assert found, text
    return listed.split("; ")


def impact_section(run):
    """Return the summary's impact section as field and value, from the lines after `impact:`."""
    lines = run.stderr.splitlines()
    assert "impact:" in lines, run.stderr
    start = lines.index("impact:") + 1
    section = {}
    for line in lines[start:]:
        if not line.startswith("  "):
            break
        field, _, value = line.strip().partition(": ")
        section[field] = value
    return section


def task_lines(task, req):
    """Return the six plan lines that add a task: a blank line, its id line, a blank line, its body, a blank line, its edge."""
    return f"\n`{task}`\n\n{TASK_BODIES[task]}\n\nDelivers: {req}\n"


# Background and the steps that change the repository.


@given(
    parsers.parse(
        'the repo maintainer\'s "{name}" repository at its base commit, with the requirements stage approved'
    ),
    target_fixture="repo",
)
def maintainer_repository(fixture_repo, name):
    repo = fixture_repo(name)
    assert "**Event**: GATE_APPROVED" in read(repo, SHARD)
    return repo


@given("the coding agent's task change is committed on the task branch")
def task_change_on_task_branch(repo, memory, commit_task_change):
    commit_task_change(repo, TASK_BRANCH)
    memory["head"] = git_output(repo, "rev-parse", "HEAD").strip()


@given("the coding agent's task change is left uncommitted on main")
def task_change_uncommitted(repo):
    write_overlays(repo, "seeded-change", "change", "task")
    assert git_output(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() == "main"


@given(parsers.parse('the coding agent\'s task change is committed on the branch "{branch}"'))
def task_change_on_branch(repo, commit_task_change, branch):
    commit_task_change(repo, branch)


@given(parsers.parse('the coding agent tags line {line:d} of "{path}" under "{req}", uncommitted'))
def tag_line(repo, line, path, req):
    lines = read(repo, path).split("\n")
    lines[line - 1] += f"  # [impl->{req}]"  # a trailing tag, so no line moves
    write(repo, path, "\n".join(lines))


@given(
    parsers.parse(
        'the coding agent proposes the task "{task}", delivering "{req}", in the plan, uncommitted',
    ),
)
def propose_task(repo, task, req):
    write(repo, PLAN_FILE, read(repo, PLAN_FILE) + task_lines(task, req))


@given(
    parsers.parse(
        'the coding agent declares the change at line {line:d} of "{path}" blocked, in a message to the maintainer'
    ),
)
def declare_blocked(repo, line, path):
    assert read(repo, path).split("\n")[line - 1]  # the message names a line that exists, and the repository is left


@given(parsers.parse('the repo maintainer adds the task "{task}", delivering "{req}", to the plan on main'))
def add_task_on_main(repo, task, req):
    write(repo, PLAN_FILE, read(repo, PLAN_FILE) + task_lines(task, req))
    _git(repo, "add", "--", PLAN_FILE)
    _git(repo, "commit", "-q", "--no-verify", "-m", "plan")


@given(
    parsers.parse(
        'the coding agent restores the requirements, and lines {first:d} and {second:d} of "{path}",'
        " to their base text, uncommitted"
    ),
)
def restore_base_text(repo, first, second, path):
    write(repo, REQUIREMENTS, (BASE / REQUIREMENTS).read_text(encoding="utf-8"))
    base = (BASE / path).read_text(encoding="utf-8").split("\n")
    lines = read(repo, path).split("\n")
    for line in (first, second):
        lines[line - 1] = base[line - 1]
    write(repo, path, "\n".join(lines))


@when(parsers.parse('the coding agent runs earnest check --task "{task}"'), target_fixture="run")
def agent_runs_check_with_task(repo, task):
    return run_earnest(repo, "check", "--task", task)


# What the stage check keeps.


@then("the assessment record gives the repository's HEAD commit as the coverage map's commit")
def record_names_map_commit(repo):
    assert record(repo)["coverage"] == {"commit": git_output(repo, "rev-parse", "HEAD").strip()}


@then(parsers.parse('the coverage map for that commit is kept under "{directory}"'))
def map_is_kept(repo, directory):
    assert (repo / directory / git_output(repo, "rev-parse", "HEAD").strip()).is_file()


@then(parsers.parse('the run header for "{stage}" gives the layers "{layers}"'))
def header_layers(repo, stage, layers):
    assert ", ".join(header(repo, stage)["layers"]) == layers


# What the check reports of the task change.


@then(
    parsers.re(r'each earnest/out-of-task finding names "(?P<task>[^"]+)" and offers exactly these exits:'),
)
def out_of_task_exits(run, task, datatable):
    found = messages(run, "earnest/out-of-task")
    assert found
    wanted = [row["exit"] for row in rows(datatable)]
    for text in found:
        assert f"`{task}`" in text, text
        assert exits(text) == wanted, text


@then(parsers.re(r'each earnest/out-of-task finding names "(?P<task>[^"]+)"'))
def out_of_task_names(run, task):
    found = messages(run, "earnest/out-of-task")
    assert found
    assert all(f"`{task}`" in text for text in found), found


@then("the summary lists every out-of-task finding with its exits")
def summary_lists_out_of_task(run):
    lines = run.stderr.splitlines()
    for result in results(run):
        if result["ruleId"] == "earnest/out-of-task":
            location = result["locations"][0]["physicalLocation"]
            place = f"{location['artifactLocation']['uri']}:{location['region']['startLine']}:"
            assert any(line.startswith(place) and result["message"]["text"] in line for line in lines), place


@then(parsers.parse('the SARIF log\'s plan lists "{task}" as "{status}"'))
def plan_lists_task(run, task, status):
    assert {entry["id"]: entry["status"] for entry in intent_plan(run)["tasks"]}[task] == status


@then("the repository is unchanged since the task change")
def unchanged_since_task_change(repo, memory):
    assert git_output(repo, "rev-parse", "HEAD").strip() == memory["head"]
    assert git_output(repo, "status", "--porcelain", "--untracked-files=all") == ""


# The impact section.


@then("the summary prints no impact section")
def no_impact_section(run):
    assert "impact:" not in run.stderr.splitlines()


@then("the SARIF log carries no impact")
def no_impact_property(run):
    assert "impact" not in sarif_run(run.stdout)["properties"]


@then("the summary's impact section reads:")
def impact_section_reads(run, datatable):
    section = impact_section(run)
    assert {field: section.get(field) for field in FIELDS} == {row["field"]: row["value"] for row in rows(datatable)}


@then("the SARIF log carries the same impact")
def sarif_carries_impact(run):
    section = impact_section(run)
    impact = sarif_run(run.stdout)["properties"]["impact"]
    assert sorted(impact) == sorted(FIELDS)
    assert impact["degraded"] is (section["degraded"] == "yes")
    for field in ("requirements", "features", "tests"):
        assert impact[field] == sorted(impact[field])
        empty = "the full suite" if field == "tests" and impact["degraded"] else "none"
        assert (", ".join(impact[field]) or empty) == section[field], field


@then("each earnest/impact-degraded finding says impact selected the full suite")
def degraded_says_full_suite(run):
    found = messages(run, "earnest/impact-degraded")
    assert found
    assert all("impact selected the full suite" in text for text in found), found


@then("the summary states that no coverage map exists for the base commit")
def summary_states_no_map(repo, run):
    base = git_output(repo, "merge-base", "HEAD", "main").strip()
    assert f"  coverage map: none for the base commit {base}" in run.stderr.splitlines(), run.stderr
