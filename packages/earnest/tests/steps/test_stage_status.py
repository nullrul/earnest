"""Steps for tests/features/stage_status.feature: `earnest plan` and `earnest check --stage` over seeded-change."""

import json
import re

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.sarif import (
    PLAN_FILE,
    RECORD,
    REQUIREMENTS,
    SHARD,
    append_block,
    approval_text,
    git_output,
    header,
    intent_plan,
    located,
    printed_hash,
    read,
    record,
    results,
    run_earnest,
    sarif_run,
    write,
)


scenarios("stage_status.feature")

STATE = f"{RECORD}/aidlc-state.md"
ROW = re.compile(r"^- \[.\] (\S+) — (EXECUTE|SKIP)")
SKIPPED_EXECUTE_ROW = re.compile(r"^- \[S\] (\S+) — EXECUTE", re.MULTILINE)


def with_mark(row, mark):
    """Return a Stage Progress row with its checkbox mark replaced."""
    return f"- [{mark}]{row[5:]}"


def messages(run, rule):
    return [result["message"]["text"] for result in results(run) if result["ruleId"] == rule]


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


@given("the repo maintainer's change is committed on a task branch")
def change_committed(repo, commit_overlay):
    commit_overlay(repo, "seeded-change", "task/add-limiter-window")


@given(parsers.parse('the coding agent has an uncommitted edit to "{path}"'))
def uncommitted_edit(repo, path):
    write(repo, path, read(repo, path) + "LOCKOUT_WINDOW = 15\n")


@given(parsers.parse('the coding agent has an uncommitted edit to the body of "{item}"'))
def uncommitted_body_edit(repo, item):
    for path in (REQUIREMENTS, PLAN_FILE):
        lines = read(repo, path).split("\n")
        if f"`{item}`" in lines:
            lines[lines.index(f"`{item}`") + 2] += " (edited)"  # the id line, a blank line, then the first body line
            write(repo, path, "\n".join(lines))
            return
    pytest.fail(f"no id line for {item}")


@given(parsers.parse('the repo maintainer makes "{first}" wait on "{second}", which already waits on it'))
def task_cycle(repo, first, second):
    lines = read(repo, PLAN_FILE).split("\n")
    assert (lines[2], lines[7]) == (f"`{first}`", "")
    lines[7] = f"Depends: {second}"
    write(repo, PLAN_FILE, "\n".join(lines))


@given(parsers.parse('the repo maintainer restores the approved text of "{item}"'))
def restore_text(repo, item):
    assert item == "req~lockout-notice~1", item
    text = read(repo, REQUIREMENTS)
    assert "how long the lockout lasts." in text
    write(repo, REQUIREMENTS, text.replace("how long the lockout lasts.", "when they may try again."))


@given(parsers.parse('the repo maintainer approves "{stage}" at the gate'))
def approve_at_gate(repo, stage):
    held = header(repo, stage)
    fields = [
        ("Stage", stage.split("/")[1]),
        ("User Input", "Approve"),
        ("Assessment Hash", held["hash"]),
        ("Items", ", ".join(held["items"])),
        ("Approved By", "human"),
    ]
    append_block(repo, "GATE_APPROVED", "2026-09-26T12:00:00Z", fields)


@given(parsers.parse('the audit log gains a GATE_REJECTED row for "{slug}" after its approval'))
def audit_rejection(repo, slug):
    append_block(repo, "GATE_REJECTED", "2026-09-26T11:00:00Z", [("Stage", slug), ("Feedback", "Rework the limits.")])


@given("the audit log gains a WORKFLOW_STARTED row after the approval")
def audit_restart(repo):
    append_block(repo, "WORKFLOW_STARTED", "2026-09-26T11:00:00Z", [("Scope", "bugfix"), ("Request", "Start again.")])


@given("the audit log gains a fresh STAGE_SKIPPED row after the restart for each stage the state file marks skipped")
def audit_fresh_skips(repo):
    for number, slug in enumerate(SKIPPED_EXECUTE_ROW.findall(read(repo, STATE))):
        fields = [("Stage", slug), ("Reason", "skipped again"), ("Skip Kind", "conditional-runtime")]
        append_block(repo, "STAGE_SKIPPED", f"2026-09-26T11:10:{number:02d}Z", fields)


@given(
    parsers.parse(
        'the requirements approval sits in a second shard "{name}", which sorts before the first shard,'
        " written later than the first shard's WORKFLOW_STARTED row"
    )
)
def approval_in_second_shard(repo, name):
    shard = read(repo, SHARD)
    start = shard.index("## Gate Approved")
    write(repo, SHARD, shard[:start])
    write(repo, f"{RECORD}/audit/{name}", shard[start:])
    assert name < SHARD.rsplit("/", 1)[1]


@given("the approval row names no Assessment Hash, Items or Approved By")
def approval_without_fork_fields(repo):
    dropped = ("**Assessment Hash**", "**Items**", "**Approved By**")
    write(repo, SHARD, "\n".join(line for line in read(repo, SHARD).split("\n") if not line.startswith(dropped)))


@given(parsers.parse('the state file marks "{slug}" as skipped and the audit log holds no skip row for it'))
def unaudited_skip(repo, slug):
    assert f"- [S] {slug} — EXECUTE" in read(repo, STATE)
    blocks = read(repo, SHARD).split("---\n")
    kept = [text for text in blocks if not ("**Event**: STAGE_SKIPPED" in text and f"**Stage**: {slug}\n" in text)]
    assert len(kept) == len(blocks) - 1
    write(repo, SHARD, "---\n".join(kept))


@given(
    parsers.parse(
        'the audit log gains a STAGE_JUMPED row with direction {direction} and target "{target}" after the approval'
    )
)
def audit_jump(repo, memory, direction, target):
    memory["target"] = target
    fields = [("Direction", direction), ("Source", "code-generation"), ("Target", target), ("Scope", "bugfix")]
    append_block(repo, "STAGE_JUMPED", "2026-09-26T11:00:00Z", fields)


@given("the state file resets the marks of every later stage marked EXECUTE to pending")
def reset_later_marks(repo, memory):
    after = False
    lines = []
    for line in read(repo, STATE).split("\n"):
        row = ROW.match(line)
        if row and after and row.group(2) == "EXECUTE":
            lines.append(with_mark(line, " "))
        elif row and row.group(1) == memory["target"]:
            after = True
            lines.append(with_mark(line, "-"))  # the target is in progress again, as upstream's jump leaves it
        else:
            lines.append(line)
    write(repo, STATE, "\n".join(lines))


@given(
    parsers.parse(
        'the audit log gains a STAGE_SKIPPED row of kind jump for "{slug}", which the state file marks skipped'
    )
)
def audit_jump_skip(repo, slug):
    fields = [("Stage", slug), ("Reason", "Skipped by jump to build-and-test (forward)"), ("Skip Kind", "jump")]
    append_block(repo, "STAGE_SKIPPED", "2026-09-26T11:00:01Z", fields)
    state = read(repo, STATE)
    assert f"- [x] {slug} — EXECUTE" in state
    write(repo, STATE, state.replace(f"- [x] {slug} — EXECUTE", f"- [S] {slug} — EXECUTE"))


# The commands.


@when("the coding agent runs earnest plan twice", target_fixture="runs")
def agent_runs_plan_twice(repo):
    return [run_earnest(repo, "plan"), run_earnest(repo, "plan")]


@when(parsers.parse('the coding agent runs earnest check --stage "{stage}" twice'), target_fixture="runs")
def agent_runs_stage_check_twice(repo, memory, stage):
    memory["stage"] = stage
    return [run_earnest(repo, "check", "--stage", stage), run_earnest(repo, "check", "--stage", stage)]


# What the plan prints.


@then("the plan lists neither the initialization stages nor the stages skipped by scope or by an audited skip")
def plan_omits_stages(run):
    skipped = {"inception/reverse-engineering", "inception/units-generation"}
    skipped |= {"operation/deployment-pipeline", "operation/deployment-execution"}
    stages = [stage["stage"] for stage in intent_plan(run)["stages"]]
    assert [stage for stage in stages if stage.startswith("initialization/") or stage in skipped] == []


@then(parsers.parse('the plan does not list "{stage}"'))
def plan_does_not_list(run, stage):
    assert stage not in [entry["stage"] for entry in intent_plan(run)["stages"]]


@then("the summary names each stage with its status and approval, and the frontier")
def summary_names_stages(run):
    plan = intent_plan(run)
    lines = {line.strip() for line in run.stderr.splitlines()}
    for stage in plan["stages"]:
        assert f"{stage['stage']}: {stage['status']}, approval {approval_text(stage)}" in lines
    assert f"frontier: {plan['frontier']}" in lines


@then(parsers.parse('"{stage}" is "{status}" although the state file marks it complete'))
def typed_status_is_not_read(repo, run, stage, status):
    assert f"- [x] {stage.split('/')[1]} — EXECUTE" in read(repo, STATE)
    assert {entry["stage"]: entry["status"] for entry in intent_plan(run)["stages"]}[stage] == status


@then("the repository is unchanged")
def repository_unchanged(repo, run):
    assert json.loads(run.stdout)["version"] == "2.1.0"  # the plan ran and printed its log
    assert git_output(repo, "status", "--porcelain", "--untracked-files=all") == ""


# What a check prints and records.


@then(parsers.parse('the finding names "{item}" and says that no task delivers it'))
def unplanned_finding_names_item(run, item):
    assert any(f"`{item}`" in text and "delivered by no task" in text for text in messages(run, "earnest/unplanned"))


@then(parsers.parse('the cycle finding lists "{cycle}"'))
def cycle_finding_lists_cycle(run, cycle):
    assert any(cycle in text for text in messages(run, "earnest/cycle"))


@then("both runs print the same assessment hash")
def same_hash(runs):
    first, second = runs
    assert printed_hash(first) == printed_hash(second)


@then("the assessment hash differs from the first run's")
def hash_differs(run, memory):
    assert printed_hash(run) != memory["hash"]


@then("the assessment hash equals the first run's")
def hash_equals(run, memory):
    assert printed_hash(run) == memory["hash"]


@then("the run header records the same commit as dirty")
def header_dirty(repo, memory):
    held = header(repo, memory["stage"])
    assert held["commit"] == git_output(repo, "rev-parse", "HEAD").strip()
    assert held["dirty"] is True


@then("the run header records the repository as not dirty")
def header_not_dirty(repo, memory):
    assert header(repo, memory["stage"])["dirty"] is False


@then(
    parsers.parse(
        'the finding at requirements.md line 3 names the approval of "{stage}" and the current revision {revision:d}'
    )
)
def outdated_finding_names_approval(run, stage, revision):
    texts = [result["message"]["text"] for result in results(run) if located(result) == (REQUIREMENTS, 3)]
    assert any(stage in text and "approval" in text and f"revision {revision}" in text for text in texts), texts


@then('the SARIF log gives the stage status "not done" with its approval "outdated"')
def sarif_gives_outdated_status(run):
    assessment = sarif_run(run.stdout)["properties"]["assessment"]
    assert assessment["status"] == "not done"
    assert assessment["reasons"]["approval"] == "outdated"


@then("the SARIF log holds no earnest/unbumped-change finding")
def no_unbumped_change(run):
    assert "earnest/unbumped-change" not in [result["ruleId"] for result in results(run)]


@then(parsers.parse('the record holds a different body hash for "{item}" than the first run held'))
def body_hash_differs(repo, memory, item):
    assert record(repo)["bodies"][item] != memory["bodies"][item]


@then("the summary states that the record is absent and the body-hash baseline is unavailable")
def summary_states_record_absent(run):
    assert "record: absent, body-hash baseline unavailable" in run.stderr.splitlines()


@then(
    parsers.parse(
        'the SARIF log holds exactly one earnest/route-mismatch finding, at the "{slug}" row of the state file,'
        " naming the audit row that is missing"
    )
)
def route_mismatch_finding(repo, run, slug):
    found = [result for result in results(run) if result["ruleId"] == "earnest/route-mismatch"]
    assert len(found) == 1
    row = next(n for n, text in enumerate(read(repo, STATE).split("\n"), 1) if text.startswith(f"- [S] {slug} "))
    assert located(found[0]) == (STATE, row)
    text = found[0]["message"]["text"]
    assert slug in text
    assert "STAGE_SKIPPED" in text
