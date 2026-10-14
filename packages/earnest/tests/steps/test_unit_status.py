"""Steps for tests/features/unit_status.feature: per-unit stages, units and unit gates over seeded-change's units variant."""

from pytest_bdd import given, parsers, scenarios, then, when

from tests.sarif import (
    RECORD,
    REQUIREMENTS,
    SHARD,
    append_block,
    header,
    intent_plan,
    read,
    results,
    rows,
    run_earnest,
    write,
)


scenarios("unit_status.feature")

STATE = f"{RECORD}/aidlc-state.md"
UNITS = f"{RECORD}/inception/units-generation/unit-of-work.md"
APPROVED_AT = "2026-09-26T12:00:00Z"


def optional(*fields):
    """Return the (name, value) fields whose value is not `-`, the outline's mark for an omitted field."""
    return [(name, value) for name, value in fields if value != "-"]


def units(run):
    return intent_plan(run)["units"]


# Background and the steps that change the repository; every edit is uncommitted.


@given(
    parsers.parse(
        'the repo maintainer\'s "{name}" repository in its future-format units variant, with the requirements,'
        " the units and the first unit's functional design approved"
    ),
    target_fixture="repo",
)
def maintainer_units_repository(units_repo, name):
    assert name == "seeded-change", name
    repo = units_repo()
    assert "**Unit**: u1" in read(repo, SHARD)
    return repo


@given(parsers.parse('the coding agent defines "{item}" a second time at the end of the requirements'))
def define_twice(repo, item):
    write(repo, REQUIREMENTS, read(repo, REQUIREMENTS) + f"\n`{item}`\n\nDefined twice by mistake.\n")


@given(parsers.parse("the coding agent leaves the unit table {state}, uncommitted"))
def unusable_table(repo, tmp_path, state):
    table = repo / UNITS
    if state == "deleted":
        table.unlink()
        return
    assert state == "a symlink to a copy outside the repository", state
    copy = tmp_path / "unit-of-work.md"
    copy.write_text(table.read_text(encoding="utf-8"), encoding="utf-8")
    table.unlink()
    table.symlink_to(copy)


@given(parsers.parse('the repo maintainer adds the row "{row}" after the unit table\'s last row'))
def add_table_row(repo, row):
    lines = read(repo, UNITS).split("\n")
    assert lines[5].startswith("| U2 |"), lines[5]
    lines.insert(6, row)
    write(repo, UNITS, "\n".join(lines))


@given(
    parsers.parse(
        'the repo maintainer moves the second unit to the directory "{directory}", in the unit table and on disk'
    )
)
def move_second_unit(repo, directory):
    text = read(repo, UNITS)
    assert "| U2 | u2-notice |" in text
    write(repo, UNITS, text.replace("| U2 | u2-notice |", f"| U2 | {directory} |"))
    construction = repo / RECORD / "construction"
    (construction / "u2-notice").rename(construction / directory)


@given(
    parsers.parse(
        'the repo maintainer makes unit "{first}" depend on "{second}" and drops the dependency of "{second}" on "{first}"'
    )
)
def reverse_dependency(repo, first, second):
    assert (first, second) == ("u1", "u2"), (first, second)
    lines = read(repo, UNITS).split("\n")
    lines.remove("Depends: unit~u1~1")
    lines.insert(lines.index("Delivers: req~rate-limit~1") + 1, "Depends: unit~u2~1")
    write(repo, UNITS, "\n".join(lines))


@given(parsers.parse('the repo maintainer approves "{stage}" at the per-stage gate of unit "{unit}"'))
def approve_per_stage(repo, stage, unit):
    held = header(repo, stage)
    slug = stage.rsplit("/", 1)[1]
    fields = [
        ("Stage", slug),
        ("Unit", unit),
        ("Gate Scope", "per-stage"),
        ("Gate Stages", slug),
        ("Attempt Generation", "1"),
        ("Assessment Hash", held["hash"]),
        ("Items", ", ".join(held["items"])),
        ("Approved By", "human"),
    ]
    append_block(repo, "GATE_APPROVED", APPROVED_AT, fields)


@given(parsers.parse('the repo maintainer approves unit "{unit}" at its unit-end gate, reported against "{slug}"'))
def approve_unit_end(repo, unit, slug):
    assert (unit, slug) == ("u2", "code-generation"), (unit, slug)
    stages = ("construction/u2-notice/functional-design", "construction/u2-notice/code-generation")
    items = sorted({item for stage in stages for item in header(repo, stage)["items"]})
    fields = [
        ("Stage", slug),
        ("Unit", unit),
        ("Gate Scope", "unit-end"),
        ("Gate Stages", "functional-design,code-generation"),
        ("Attempt Generation", "1"),
        ("Items", ", ".join(items)),
        ("Approved By", "human"),
    ]
    append_block(repo, "GATE_APPROVED", APPROVED_AT, fields)


@given(
    parsers.parse(
        'the audit log gains a GATE_APPROVED row for "{slug}" with Unit "{unit}", Gate Scope "{scope}"'
        ' and Gate Stages "{stages}"'
    )
)
def audit_unit_approval(repo, slug, unit, scope, stages):
    fields = [("Stage", slug), *optional(("Unit", unit), ("Gate Scope", scope), ("Gate Stages", stages))]
    fields += [("Items", "dsn~notice-text~1"), ("Approved By", "human")]
    append_block(repo, "GATE_APPROVED", APPROVED_AT, fields)


@given(
    parsers.parse(
        'the audit log gains a per-stage GATE_APPROVED row for "{slug}" of unit "{unit}"'
        ' at Attempt Generation "{generation}"'
    )
)
def audit_generation_approval(repo, slug, unit, generation):
    fields = [
        ("Stage", slug),
        ("Unit", unit),
        ("Gate Scope", "per-stage"),
        ("Gate Stages", slug),
        ("Attempt Generation", generation),
        ("Items", "task~add-limiter~1"),
        ("Approved By", "human"),
    ]
    append_block(repo, "GATE_APPROVED", APPROVED_AT, fields)


@given(parsers.parse('the audit log gains a GATE_REJECTED row for "{slug}" of unit "{unit}" after the approval'))
def audit_unit_rejection(repo, slug, unit):
    scoped = [("Unit", unit), ("Gate Scope", "per-stage")] if unit != "-" else []
    fields = [("Stage", slug), *scoped, ("Feedback", "Rework the design.")]
    append_block(repo, "GATE_REJECTED", "2026-09-26T11:30:00Z", fields)


# The commands.


@when(
    "the coding agent runs earnest plan before and after an uncommitted edit drops the state file's Unit Progress",
    target_fixture="runs",
)
def plan_before_and_after_dropping_unit_progress(repo):
    before = run_earnest(repo, "plan")
    text = read(repo, STATE)
    assert "\n## Unit Progress\n" in text
    write(repo, STATE, text[: text.index("## Unit Progress")])
    return [before, run_earnest(repo, "plan")]


# What the plan prints.


@then("the plan lists these units:")
def plan_lists_units(run, datatable):
    actual = [(unit["id"], unit["status"], unit["directory"], unit["frontier"]) for unit in units(run)]
    assert actual == [(row["unit"], row["status"], row["directory"], row["frontier"]) for row in rows(datatable)]


@then(parsers.parse('the frontier of unit "{unit}" is "{stage}"'))
def unit_frontier_is(run, unit, stage):
    assert {entry["id"]: entry["frontier"] for entry in units(run)}[unit] == stage


@then("the summary names each unit with its status, directory and frontier")
def summary_names_units(run):
    lines = {line.strip() for line in run.stderr.splitlines()}
    for unit in units(run):
        directory, frontier = unit["directory"] or "none", unit["frontier"] or "none"
        assert f"unit {unit['id']}: {unit['status']}, directory {directory}, frontier {frontier}" in lines


@then("the plan exits zero and names no unsupported route")
def plan_exits_zero(run):
    assert run.returncode == 0, run.stderr
    assert "unsupported route" not in run.stderr


@then(parsers.parse('"{stage}" is "{status}" although the state file marks it complete for its unit'))
def typed_unit_status_is_not_read(repo, run, stage, status):
    state = read(repo, STATE)
    assert "- [x] code-generation — EXECUTE" in state
    assert "| u1 | - | [x] | [x] | [x] |" in state
    assert {entry["stage"]: entry["status"] for entry in intent_plan(run)["stages"]}[stage] == status


# What a check prints.


@then("the SARIF log holds no findings")
def no_findings(run):
    assert results(run) == []


@then(parsers.parse('stderr is one line that names "{named}"'))
def stderr_names(run, named):
    lines = run.stderr.splitlines()
    assert len(lines) == 1, lines
    assert named in lines[0], lines
