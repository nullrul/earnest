"""Tests for earnest.plan: the state file's Stage Progress, the audit shards, and loading both from a work tree."""

import time

import pytest

from earnest import adapters, git, plan, structural
from earnest.git import Hunk
from earnest.index import MARKDOWN, Id, Index, Item, Link, Region, Source, build_index
from earnest.index import digest as digest_of
from earnest.plan import Approval, ChangedRegion, Event, Record, Row
from earnest.reporter import Finding, Run, RunHeader
from tests.sarif import PLAN_FILE, write
from tests.sarif import REQUIREMENTS as REQUIREMENTS_FILE


DASH = "\u2014"
STATE_TEXT = f"""# AI-DLC State Tracking

## Project Information
- **Project**: checkout
- **Scope**: bugfix

## Stage Progress
<!-- Checkbox states: [ ] pending, [-] in-progress, [?] awaiting approval, [R] revising, [x] completed, [S] skipped -->
### INITIALIZATION PHASE
- [x] workspace-scaffold {DASH} EXECUTE: always
- [x] state-init {DASH} EXECUTE: always

### INCEPTION PHASE
- [S] reverse-engineering {DASH} EXECUTE: greenfield project
- [S] units-generation {DASH} SKIP: not in bugfix scope

## Current Status
- [x] not-a-row {DASH} EXECUTE: after the section
"""


def block(timestamp, event, **fields):
    """Return an audit block as AI-DLC writes it."""
    lines = ["## Heading", f"**Timestamp**: {timestamp}", f"**Event**: {event}"]
    lines += [f"**{name.replace('_', ' ')}**: {value}" for name, value in fields.items()]
    return "\n".join([*lines, "---"]) + "\n"


def put(root, files):
    for path, text in files.items():
        write(root, path, text)


def test_scope_is_read_from_the_state_file():
    assert plan.parse_state(STATE_TEXT).scope == "bugfix"
    assert plan.parse_state("# nothing\n").scope == ""


def test_a_long_run_of_spaces_in_a_scope_or_a_phase_heading_parses_in_linear_time():
    spaces = " " * 50_000
    started = time.perf_counter()
    scope = plan.parse_state(f"- **Scope**: a{spaces}b\n").scope
    plan.parse_state(f"## Stage Progress\n### a{spaces}b\n- [x] s \u2014 EXECUTE\n")
    assert time.perf_counter() - started < 1  # the quadratic regexes took about 7 seconds each
    assert scope == f"a{spaces}b"


def test_scope_loses_trailing_blanks_and_phase_loses_only_a_separate_word():
    assert plan.parse_state("- **Scope**:  \t bugfix \t \n").scope == "bugfix"
    state = "## Stage Progress\n### {}\n- [x] s \u2014 EXECUTE\n"
    for heading, phase in (
        ("A  phase ", "a"),
        ("PHASE", "phase"),
        ("aPHASE", "aphase"),
        ("Two Words PHASE", "two words"),
    ):
        assert plan.parse_state(state.format(heading)).rows[0].phase == phase


def test_stage_progress_rows_are_read_in_order_with_phase_slug_mark_action_reason_and_line():
    assert plan.parse_state(STATE_TEXT).rows == (
        Row("initialization", "workspace-scaffold", "x", "EXECUTE", "always", 10),
        Row("initialization", "state-init", "x", "EXECUTE", "always", 11),
        Row("inception", "reverse-engineering", "S", "EXECUTE", "greenfield project", 14),
        Row("inception", "units-generation", "S", "SKIP", "not in bugfix scope", 15),
    )
    assert plan.parse_state(STATE_TEXT).rows[2].stage == "inception/reverse-engineering"


def test_phase_heading_loses_the_word_phase_and_is_lower_cased():
    text = f"## Stage Progress\n### CONSTRUCTION PHASE\n- [ ] a {DASH} EXECUTE\n### Operation Phase\n- [ ] b {DASH} SKIP: x\n"
    assert [(row.phase, row.reason) for row in plan.parse_state(text).rows] == [
        ("construction", ""),
        ("operation", "x"),
    ]


def test_a_second_level_heading_resets_the_phase():
    text = (
        f"## Stage Progress\n### A PHASE\n- [x] a {DASH} EXECUTE\n## Other\n## Stage Progress\n- [x] b {DASH} EXECUTE\n"
    )
    state = plan.parse_state(text)
    assert state.rows == (Row("a", "a", "x", "EXECUTE", "", 3),)  # `b` follows a heading that reset the phase
    assert (state.unread, state.heading) == ((6,), 1)


def test_checkbox_lines_outside_stage_progress_are_ignored():
    text = (
        f"- [x] early {DASH} EXECUTE: before any section\n## Stage Progress\n- [x] no-phase {DASH} EXECUTE: no heading yet\n"
        f"### INCEPTION PHASE\n- [x] a {DASH} EXECUTE: yes\nnot a row\n- [x] b - EXECUTE: wrong dash\n"
        f"## Unit Progress\n- [x] c {DASH} EXECUTE: after\n"
    )
    state = plan.parse_state(text)
    assert [row.slug for row in state.rows] == ["a"]
    assert (state.unread, state.heading) == ((3, 7), 2)  # the row before any phase, and the one with the wrong dash


def test_state_without_stage_progress_has_no_rows():
    assert plan.parse_state("# AI-DLC State Tracking\n\n## Project Information\n- **Scope**: classic\n").rows == ()
    assert plan.parse_state("").rows == ()
    for text in ("# AI-DLC State Tracking\n\n## Stage  Progress\n### INCEPTION PHASE\n- [x] a - EXECUTE\n", ""):
        state = plan.parse_state(text)
        assert (state.rows, state.unread, state.heading) == ((), (), 0)  # a renamed heading is no section at all


def test_unreadable_rows_under_stage_progress_are_collected_by_line():
    text = (
        f"## Stage Progress\n### INCEPTION PHASE\n- [x] a {DASH} EXECUTE (always)\n- [x] b {DASH} EXECUTE: ok\n"
        f"- [x] c -- EXECUTE\n- [?x] d {DASH} EXECUTE\n- [x] e {DASH} MAYBE\n- [x] f {DASH} EXECUTEX\n"
    )
    state = plan.parse_state(text)
    assert [row.slug for row in state.rows] == ["a", "b"]
    assert (state.unread, state.heading) == ((5, 6, 7, 8), 1)


def test_row_tail_may_be_a_bare_word_or_follow_a_space():
    text = (
        f"## Stage Progress\n### INCEPTION PHASE\n- [x] a {DASH} EXECUTE\n- [x] b {DASH} EXECUTE (always)\n"
        f"- [x] c {DASH} SKIP: x\n- [x] d {DASH} EXECUTE:x\n"
    )
    assert [(row.slug, row.action, row.reason) for row in plan.parse_state(text).rows] == [
        ("a", "EXECUTE", ""),
        ("b", "EXECUTE", "(always)"),
        ("c", "SKIP", "x"),
        ("d", "EXECUTE", "x"),
    ]


def test_heading_line_of_stage_progress_is_recorded():
    assert plan.parse_state(STATE_TEXT).heading == 7
    assert plan.parse_state("## Stage Progress\n## Stage Progress\n").heading == 1  # the first one


def test_row_marks_are_returned_as_written():
    marks = [" ", "-", "?", "R", "x", "S"]
    text = "## Stage Progress\n### INCEPTION PHASE\n" + "".join(
        f"- [{mark}] s{number} {DASH} EXECUTE\n" for number, mark in enumerate(marks)
    )
    assert [row.mark for row in plan.parse_state(text).rows] == marks


def test_blocks_split_at_the_rule_line_and_fields_are_read():
    text = block("2026-09-26T09:00:00Z", "WORKFLOW_STARTED", Scope="bugfix") + block(
        "2026-09-26T10:00:00Z", "GATE_APPROVED", Stage="requirements-analysis", Items="req~a~1, req~b~1"
    )
    events = plan.parse_audit(text, "a.md")
    assert [(event.key, event.name) for event in events] == [
        (("2026-09-26T09:00:00Z", "a.md", 0), "WORKFLOW_STARTED"),
        (("2026-09-26T10:00:00Z", "a.md", 1), "GATE_APPROVED"),
    ]
    assert events[1].fields["Items"] == "req~a~1, req~b~1"
    assert events[1].fields["Stage"] == "requirements-analysis"


def test_first_timestamp_of_a_block_is_used():
    text = "## H\n**Timestamp**: 2026-09-26T09:00:00Z\n**Event**: STAGE_STARTED\n**Timestamp**: 2030-01-01T00:00:00Z\n---\n"
    (event,) = plan.parse_audit(text, "a.md")
    assert event.key[0] == "2026-09-26T09:00:00Z"


def test_block_without_timestamp_or_event_is_ignored():
    text = "## H\n**Event**: STAGE_STARTED\n---\n## H\n**Timestamp**: 2026-09-26T09:00:00Z\n---\n" + block(
        "2026-09-26T10:00:00Z", "HUMAN_TURN"
    )
    events = plan.parse_audit(text, "a.md")
    assert [(event.name, event.key[2]) for event in events] == [
        ("HUMAN_TURN", 2)
    ]  # ignored blocks still take a position


def test_event_name_is_the_event_field():
    text = (
        "## Gate Approved\n**Timestamp**: 2026-09-26T10:00:00Z\n**Event**: GATE_APPROVED\n**Details**: **Event**: no\n"
    )
    (event,) = plan.parse_audit(text, "a.md")  # a last block that the file leaves unclosed still counts
    assert (event.name, event.fields["Details"]) == ("GATE_APPROVED", "**Event**: no")


def test_crlf_shard_is_read_like_lf():
    text = block("2026-09-26T10:00:00Z", "GATE_APPROVED", Stage="a")
    assert plan.parse_audit(text.replace("\n", "\r\n"), "a.md") == plan.parse_audit(text, "a.md")
    assert plan.parse_audit(text.replace("\n", "\r\n"), "a.md")[0].fields["Stage"] == "a"


def test_crlf_shard_of_two_events_reads_both_with_their_positions():
    text = block("2026-09-26T09:00:00Z", "WORKFLOW_STARTED") + block("2026-09-26T09:05:00Z", "STAGE_SKIPPED", Stage="x")
    found = plan.parse_audit(text.replace("\n", "\r\n"), "a.md")
    assert [(event.key, event.name, event.fields.get("Stage")) for event in found] == [
        (("2026-09-26T09:00:00Z", "a.md", 0), "WORKFLOW_STARTED", None),
        (("2026-09-26T09:05:00Z", "a.md", 1), "STAGE_SKIPPED", "x"),
    ]


def test_events_order_by_timestamp_then_shard_name_then_position():
    same = "2026-09-26T09:00:00Z"
    early = plan.parse_audit(block("2026-09-26T08:00:00Z", "STAGE_STARTED"), "z.md")
    first = plan.parse_audit(block(same, "STAGE_STARTED") + block(same, "STAGE_COMPLETED"), "a.md")
    second = plan.parse_audit(block(same, "HUMAN_TURN"), "b.md")
    ordered = sorted([*second, *first[::-1], *early])
    assert [(event.key[1], event.name) for event in ordered] == [
        ("z.md", "STAGE_STARTED"),
        ("a.md", "STAGE_STARTED"),
        ("a.md", "STAGE_COMPLETED"),
        ("b.md", "HUMAN_TURN"),
    ]


def test_load_merges_every_audit_shard_into_one_ordered_log(tmp_path):
    record = "aidlc/spaces/default/intents/260926-checkout"
    put(
        tmp_path,
        {
            f"{record}/aidlc-state.md": STATE_TEXT,
            f"{record}/audit/b-1.md": block("2026-09-26T10:00:00Z", "GATE_APPROVED", Stage="requirements-analysis"),
            f"{record}/audit/a-1.md": block("2026-09-26T11:00:00Z", "GATE_REJECTED", Stage="requirements-analysis"),
            f"{record}/audit/notes.txt": block("2026-09-26T08:00:00Z", "WORKFLOW_STARTED"),
            f"{record}/inception/audit/c.md": block("2026-09-26T07:00:00Z", "WORKFLOW_STARTED"),
        },
    )
    files = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file())
    (found,) = plan.load(tmp_path, files)
    assert (found.directory, found.state_path) == (record, f"{record}/aidlc-state.md")
    assert found.state.scope == "bugfix"
    assert [(event.key[1], event.name) for event in found.events] == [
        ("b-1.md", "GATE_APPROVED"),
        ("a-1.md", "GATE_REJECTED"),
    ]


def test_load_reads_a_shard_only_from_the_audit_directory_of_its_own_record(tmp_path):
    started = block("2026-09-26T09:00:00Z", "WORKFLOW_STARTED")
    files = {
        "r/aidlc-state.md": STATE_TEXT,
        "r/audit/a.md": started,
        "r/audit/nested/b.md": started,  # below the audit directory, not in it
        "r/audit-old/c.md": started,
        "r-b/aidlc-state.md": STATE_TEXT,
        "r-b/audit/d.md": started,
    }
    put(tmp_path, files)
    records = plan.load(tmp_path, sorted(files))
    assert [(record.directory, [event.key[1] for event in record.events]) for record in records] == [
        ("r", ["a.md"]),
        ("r-b", ["d.md"]),
    ]


def test_load_takes_only_a_file_named_exactly_aidlc_state_md_for_a_state_file(tmp_path):
    files = {f"x/{name}": STATE_TEXT for name in ("aidlc-state.md.bak", "old-aidlc-state.md", "AIDLC-STATE.md")}
    put(tmp_path, files)
    assert plan.load(tmp_path, sorted(files)) == []


def test_load_reads_a_shard_that_opens_with_a_byte_order_mark_on_its_first_field(tmp_path):
    put(tmp_path, {"x/aidlc-state.md": STATE_TEXT})
    (tmp_path / "x" / "audit").mkdir()
    (tmp_path / "x" / "audit" / "a.md").write_bytes(
        b"\xef\xbb\xbf**Timestamp**: 2026-09-26T09:00:00Z\n**Event**: HUMAN_TURN\n---\n"
    )
    (found,) = plan.load(tmp_path, ["x/aidlc-state.md", "x/audit/a.md"])
    assert [(event.key, event.name) for event in found.events] == [(("2026-09-26T09:00:00Z", "a.md", 0), "HUMAN_TURN")]


def test_load_lists_one_record_per_directory_holding_a_state_file(tmp_path):
    put(
        tmp_path,
        {
            "aidlc-state.md": STATE_TEXT,
            "audit/r.md": block("2026-09-26T09:00:00Z", "WORKFLOW_STARTED"),
            "one/aidlc-state.md": STATE_TEXT,
            "one/audit/o.md": block("2026-09-26T09:00:00Z", "STAGE_STARTED"),
            "two/deep/aidlc-state.md": STATE_TEXT,
            "docs/a.md": "# A\n",
        },
    )
    files = [
        "aidlc-state.md",
        "audit/r.md",
        "docs/a.md",
        "one/aidlc-state.md",
        "one/audit/o.md",
        "two/deep/aidlc-state.md",
    ]
    records = plan.load(tmp_path, files)
    assert [(record.directory, [event.name for event in record.events]) for record in records] == [
        ("", ["WORKFLOW_STARTED"]),
        ("one", ["STAGE_STARTED"]),
        ("two/deep", []),
    ]


def test_load_orders_records_by_directory_not_by_state_file_path(tmp_path):
    put(tmp_path, {"a-b/aidlc-state.md": STATE_TEXT, "a/aidlc-state.md": STATE_TEXT})
    files = ["a-b/aidlc-state.md", "a/aidlc-state.md"]  # by path, "a-b/" sorts before "a/"
    assert [record.directory for record in plan.load(tmp_path, files)] == ["a", "a-b"]


def test_load_without_a_state_file_gives_no_record(tmp_path):
    put(tmp_path, {"audit/a.md": block("2026-09-26T09:00:00Z", "WORKFLOW_STARTED"), "docs/a.md": "# A\n"})
    assert plan.load(tmp_path, ["audit/a.md", "docs/a.md"]) == []
    assert plan.load(tmp_path, []) == []


def test_load_reads_bad_utf8_with_replacement(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "aidlc-state.md").write_bytes(
        f"## Stage Progress\n### INCEPTION PHASE\n- [x] a {DASH} EXECUTE: caf".encode() + b"\xe9\n"
    )
    (tmp_path / "x" / "audit").mkdir()
    (tmp_path / "x" / "audit" / "a.md").write_bytes(
        b"\xef\xbb\xbf## H\n**Timestamp**: 2026-09-26T09:00:00Z\n**Event**: HUMAN_TURN\n**Details**: caf\xe9\n---\n"
    )
    (found,) = plan.load(tmp_path, ["x/aidlc-state.md", "x/audit/a.md"])
    assert found.state.rows[0].reason == "caf\ufffd"
    assert found.events[0].fields["Details"] == "caf\ufffd"  # and the byte order mark did not hide the first field


def test_load_skips_a_deleted_tracked_file_and_a_symlink(tmp_path):
    put(tmp_path, {"real/aidlc-state.md": STATE_TEXT, "real/audit/a.md": block("2026-09-26T09:00:00Z", "HUMAN_TURN")})
    (tmp_path / "link").mkdir()
    (tmp_path / "link" / "aidlc-state.md").symlink_to(tmp_path / "real" / "aidlc-state.md")
    (tmp_path / "real" / "audit" / "b.md").symlink_to(tmp_path / "real" / "audit" / "a.md")
    files = [
        "gone/aidlc-state.md",
        "link/aidlc-state.md",
        "real/aidlc-state.md",
        "real/audit/a.md",
        "real/audit/b.md",
        "real/audit/gone.md",
    ]
    records = plan.load(tmp_path, files)
    assert [record.directory for record in records] == ["real"]
    assert [event.key[1] for event in records[0].events] == ["a.md"]
    assert isinstance(records[0], Record)
    assert all(isinstance(event, Event) for event in records[0].events)


HASH = "sha256:" + "0" * 64
STAGES = ("inception/requirements-analysis", "construction/code-generation", "construction/build-and-test")
FULL_STATE = f"""## Project Information
- **Scope**: bugfix

## Stage Progress
### INITIALIZATION PHASE
- [x] workspace-scaffold {DASH} EXECUTE: always
- [x] workspace-detection {DASH} EXECUTE: always
- [x] state-init {DASH} EXECUTE: always
### INCEPTION PHASE
- [S] reverse-engineering {DASH} EXECUTE: greenfield project
- [x] requirements-analysis {DASH} EXECUTE: always
- [S] units-generation {DASH} SKIP: not in bugfix scope
### CONSTRUCTION PHASE
- [x] code-generation {DASH} EXECUTE: always
- [x] build-and-test {DASH} EXECUTE: always
### OPERATION PHASE
- [S] deployment-pipeline {DASH} EXECUTE: no pipeline change
- [S] deployment-execution {DASH} EXECUTE: no pipeline change
"""
ROWS = plan.parse_state(FULL_STATE).rows
UNITS_STATE = FULL_STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")
START = block("2026-09-26T09:00:00Z", "WORKFLOW_STARTED", Scope="bugfix")
SKIPS = "".join(
    block(f"2026-09-26T09:{minute}:00Z", "STAGE_SKIPPED", Stage=slug, Skip_Kind="conditional-runtime")
    for minute, slug in (("10", "reverse-engineering"), ("20", "deployment-pipeline"), ("21", "deployment-execution"))
)


def gate(timestamp, event="GATE_APPROVED", stage="requirements-analysis", **fields):
    return block(timestamp, event, Stage=stage, **fields)


def jump(timestamp, direction, target):
    fields = {"Direction": direction, "Source": "code-generation", "Target": target, "Scope": "bugfix"}
    return block(timestamp, "STAGE_JUMPED", **fields)


APPROVED = gate("2026-09-26T10:00:00Z", Items="req~a~1, req~b~1", Approved_By="human", Assessment_Hash=HASH)
BASE = START + SKIPS + APPROVED
REQUIREMENTS = STAGES[0]


def events_of(*blocks):
    return plan.parse_audit("".join(blocks), "a.md")


def intent_of(*blocks, state=FULL_STATE, directory="r", table=None):
    events = tuple(sorted(events_of(*blocks)))
    return plan.intent(Record(directory, f"{directory}/aidlc-state.md", plan.parse_state(state), events, table))


def ident(text):
    kind, name, revision = text.split("~")
    return Id(kind, name, int(revision))


def item(text, stage=REQUIREMENTS, line=1):
    return Item(ident(text), f"r/{stage}/doc.md", line)


def counted(*blocks):
    return [(event.name, event.fields.get("Stage")) for event in plan.counting(events_of(*blocks), ROWS)]


def test_row_before_the_latest_workflow_started_does_not_count():
    assert counted(APPROVED, block("2026-09-26T11:00:00Z", "WORKFLOW_STARTED")) == []


def test_row_after_the_latest_workflow_started_counts():
    assert counted(START, APPROVED) == [("GATE_APPROVED", "requirements-analysis")]
    restart = block("2026-09-26T09:30:00Z", "WORKFLOW_STARTED")
    assert counted(START, gate("2026-09-26T09:20:00Z"), restart, APPROVED) == [
        ("GATE_APPROVED", "requirements-analysis")
    ]


def test_backward_jump_voids_rows_of_its_target_and_every_later_execute_row():
    later = gate("2026-09-26T10:30:00Z", stage="code-generation")
    kept = counted(START, SKIPS, APPROVED, later, jump("2026-09-26T11:00:00Z", "BACKWARD", "requirements-analysis"))
    assert kept == [("STAGE_SKIPPED", "reverse-engineering"), ("STAGE_JUMPED", None)]
    again = gate("2026-09-26T12:00:00Z")  # an approval after the jump belongs to the new attempt
    after = jump("2026-09-26T11:00:00Z", "BACKWARD", "requirements-analysis")
    assert REQUIREMENTS in intent_of(START, SKIPS, APPROVED, after, again).approvals


def test_backward_jump_reset_span_includes_skipped_marks():
    (event,) = events_of(jump("2026-09-26T11:00:00Z", "BACKWARD", "requirements-analysis"))
    span = plan.jump_span(event, ROWS)
    assert {"deployment-pipeline", "deployment-execution"} <= span  # rows marked [S] and EXECUTE
    assert "units-generation" not in span  # a planned SKIP row is no EXECUTE row


def test_backward_jump_leaves_earlier_stages_alone():
    (event,) = events_of(jump("2026-09-26T11:00:00Z", "BACKWARD", "code-generation"))
    span = plan.jump_span(event, ROWS)
    assert span == {"code-generation", "build-and-test", "deployment-pipeline", "deployment-execution"}


def test_redo_jump_voids_its_target_only():
    (event,) = events_of(jump("2026-09-26T11:00:00Z", "REDO", "code-generation"))
    assert plan.jump_span(event, ROWS) == {"code-generation"}
    (lower,) = events_of(jump("2026-09-26T11:00:00Z", "redo", "code-generation"))  # Direction is read in any case
    assert plan.jump_span(lower, ROWS) == {"code-generation"}


def test_forward_jump_voids_nothing():
    (event,) = events_of(jump("2026-09-26T11:00:00Z", "FORWARD", "build-and-test"))
    assert plan.jump_span(event, ROWS) == frozenset()
    assert counted(START, APPROVED, jump("2026-09-26T11:00:00Z", "FORWARD", "build-and-test"))[0] == (
        "GATE_APPROVED",
        "requirements-analysis",
    )


def test_jump_to_an_unknown_target_voids_nothing():
    for direction in ("BACKWARD", "REDO"):
        (event,) = events_of(jump("2026-09-26T11:00:00Z", direction, "no-such-stage"))
        assert plan.jump_span(event, ROWS) == frozenset()


def test_route_is_execute_rows_outside_initialization_in_row_order():
    assert intent_of(BASE).route == STAGES
    assert intent_of(START).route == (
        "inception/reverse-engineering",
        *STAGES,
        "operation/deployment-pipeline",
        "operation/deployment-execution",
    )


def test_route_id_is_phase_slash_slug():
    route = intent_of(BASE).route
    assert route[0] == "inception/requirements-analysis"
    assert not [stage for stage in route if stage.startswith("initialization/")]
    assert "inception/units-generation" not in route  # a SKIP row


def test_counting_skip_row_removes_a_stage_from_the_route():
    only = block("2026-09-26T09:20:00Z", "STAGE_SKIPPED", Stage="deployment-pipeline", Skip_Kind="conditional-runtime")
    route = intent_of(START, only).route
    assert "operation/deployment-pipeline" not in route
    assert "operation/deployment-execution" in route


def test_skip_mark_without_a_row_does_not_remove_a_stage():
    assert "operation/deployment-pipeline" in intent_of(START).route  # marked [S] and EXECUTE, and no audit row


def test_skip_row_inside_a_reset_span_puts_the_stage_back_on_the_route():
    route = intent_of(BASE, jump("2026-09-26T11:00:00Z", "BACKWARD", "requirements-analysis")).route
    assert "operation/deployment-pipeline" in route
    assert "operation/deployment-execution" in route
    assert "inception/reverse-engineering" not in route  # its skip row precedes the target, so it still counts


def test_skip_row_before_the_boundary_puts_the_stage_back_on_the_route():
    route = intent_of(SKIPS, block("2026-09-26T11:00:00Z", "WORKFLOW_STARTED")).route
    assert "inception/reverse-engineering" in route
    assert "operation/deployment-pipeline" in route


def test_route_mismatch_for_a_skipped_mark_without_a_counting_row():
    current = intent_of(START)
    assert [row.slug for row in current.mismatches] == [
        "reverse-engineering",
        "deployment-pipeline",
        "deployment-execution",
    ]
    found = plan.route_findings(current)
    assert [(f.rule, f.path, f.line, f.subject, f.level) for f in found] == [
        ("earnest/route-mismatch", "r/aidlc-state.md", 10, "reverse-engineering", "error"),
        ("earnest/route-mismatch", "r/aidlc-state.md", 17, "deployment-pipeline", "error"),
        ("earnest/route-mismatch", "r/aidlc-state.md", 18, "deployment-execution", "error"),
    ]
    assert all("`STAGE_SKIPPED`" in f.message and f.subject in f.message for f in found)
    assert all(f.stage is None for f in found)  # it reaches no stage


def test_route_mismatch_for_a_skipped_initialization_row():
    state = FULL_STATE.replace(f"- [x] state-init {DASH} EXECUTE", f"- [S] state-init {DASH} EXECUTE")
    current = intent_of(BASE, state=state)
    assert [row.slug for row in current.mismatches] == ["state-init"]
    assert "initialization/state-init" not in current.route  # an Initialization row never joins the route


def test_no_route_mismatch_when_a_counting_skip_row_exists():
    assert intent_of(BASE).mismatches == ()
    assert plan.route_findings(intent_of(BASE)) == []


def test_no_route_mismatch_for_pending_marks_and_skip_rows():
    state = FULL_STATE.replace(f"- [S] reverse-engineering {DASH} EXECUTE", f"- [ ] reverse-engineering {DASH} EXECUTE")
    only = block("2026-09-26T09:20:00Z", "STAGE_SKIPPED", Stage="deployment-pipeline", Skip_Kind="conditional-runtime")
    rest = block("2026-09-26T09:21:00Z", "STAGE_SKIPPED", Stage="deployment-execution", Skip_Kind="conditional-runtime")
    assert intent_of(START, only, rest, state=state).mismatches == ()  # [S] on a SKIP row is no EXECUTE row either


def test_unreadable_row_is_a_route_mismatch_finding_at_its_line():
    state = FULL_STATE.replace(f"- [x] code-generation {DASH} EXECUTE", "- [x] code-generation -- EXECUTE")
    current = intent_of(BASE, state=state)
    assert "construction/code-generation" not in current.route  # the route shrank, and the finding says why
    (found,) = plan.route_findings(current)
    assert (found.rule, found.path, found.line, found.level, found.stage) == (
        "earnest/route-mismatch",
        "r/aidlc-state.md",
        14,
        "error",
        None,
    )
    assert "Earnest cannot read line 14" in found.message
    assert "Stage Progress row" in found.message
    only = "## Stage Progress\n### CONSTRUCTION PHASE\n- [x] code-generation -- EXECUTE\n"
    (alone,) = plan.route_findings(intent_of(BASE, state=only))  # an unreadable row is no empty section as well
    assert "Earnest cannot read line 3" in alone.message


def test_empty_stage_progress_section_is_a_route_mismatch_finding_at_the_heading():
    state = "## Project Information\n- **Scope**: bugfix\n\n## Stage Progress\n\n## Current Status\n"
    current = intent_of(BASE, state=state)
    assert current.route == ()
    (found,) = plan.route_findings(current)
    assert (found.rule, found.line, found.level) == ("earnest/route-mismatch", 4, "error")
    assert "Earnest cannot read a Stage Progress section at line 4" in found.message


def test_missing_stage_progress_section_is_a_route_mismatch_finding_at_line_one():
    renamed = FULL_STATE.replace("## Stage Progress", "## Stage  Progress")
    for state in (renamed, "", "## Project Information\n- **Scope**: bugfix\n"):
        current = intent_of(BASE, state=state)
        assert current.route == ()
        (found,) = plan.route_findings(current)
        assert (found.line, found.path) == (1, "r/aidlc-state.md")
    assert plan.route_findings(intent_of(BASE)) == []  # a state file that reads gives none


def test_units_generation_on_the_route_expands_per_unit_stages():
    state = FULL_STATE.replace(
        f"- [S] units-generation {DASH} SKIP: not in bugfix scope", f"- [ ] units-generation {DASH} EXECUTE: needed"
    )
    current = intent_of(BASE, state=state)
    assert current.units_route
    assert "construction/code-generation" in current.route  # the intent holds the route before the expansion
    table = "| Unit ID | Directory |\n| --- | --- |\n| A | a-dir |\n"
    built = plan.build(intent_of(BASE, state=state, table=table), Index((unit("a"),), (), ()))
    expanded = (REQUIREMENTS, "inception/units-generation", "construction/a-dir/code-generation", BUILD_AND_TEST)
    assert built.intent.route == expanded
    assert built.intent.executed == current.route


def test_route_without_units_generation_is_unchanged():
    for current in (intent_of(BASE), intent_of(START)):
        assert not current.units_route
        built = plan.build(current, Index((unit("a"),), (), ()))
        assert built.intent.route == current.route == current.executed
        assert (built.units, built.join) == ((), ())


def test_approval_row_is_read():
    approval = intent_of(BASE).approvals[REQUIREMENTS]
    assert approval == Approval(REQUIREMENTS, ("req~a~1", "req~b~1"), "human", HASH)


def test_approved_by_automatic_is_read():
    row = gate("2026-09-26T10:00:00Z", Items="req~a~1", Approved_By="automatic")
    assert intent_of(START, row).approvals[REQUIREMENTS].by == "automatic"
    other = gate("2026-09-26T10:00:00Z", Items="req~a~1", Approved_By="robot")
    assert intent_of(START, other).approvals[REQUIREMENTS].by is None


def test_malformed_latest_approval_lets_the_older_one_count():
    bad = gate("2026-09-26T10:30:00Z", Items="req~a~1, nonsense")
    current = intent_of(START, APPROVED, bad)
    assert current.approvals[REQUIREMENTS].items == ("req~a~1", "req~b~1")  # the later row is no approval at all
    assert current.named_items == {"req~a~1", "req~b~1"}


def test_latest_counting_row_per_stage_is_the_approval():
    second = gate("2026-09-26T10:30:00Z", Items="req~a~2, req~b~1", Approved_By="automatic")
    approval = intent_of(START, APPROVED, second).approvals[REQUIREMENTS]
    assert (approval.items, approval.by) == (("req~a~2", "req~b~1"), "automatic")
    events = tuple(reversed(events_of(START, APPROVED, second)))  # the result does not depend on the input order
    unsorted = plan.intent(Record("r", "r/aidlc-state.md", plan.parse_state(FULL_STATE), events))
    assert unsorted.approvals[REQUIREMENTS] == approval


def test_rejection_after_the_approval_leaves_none():
    rejected = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Feedback="Rework.")
    assert intent_of(START, APPROVED, rejected).approvals == {}


def test_rejection_before_the_approval_is_history():
    rejected = gate("2026-09-26T09:30:00Z", "GATE_REJECTED", Feedback="Rework.")
    assert REQUIREMENTS in intent_of(START, rejected, APPROVED).approvals


def test_approval_after_a_rejection_counts():
    rejected = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Feedback="Rework.")
    again = gate("2026-09-26T12:00:00Z", Items="req~c~1")
    assert intent_of(START, APPROVED, rejected, again).approvals[REQUIREMENTS].items == ("req~c~1",)


def test_rows_with_unit_gate_scope_or_gate_stages_are_ignored():
    for field_name in ("Unit", "Gate_Scope", "Gate_Stages"):
        team = gate("2026-09-26T10:00:00Z", Items="req~a~1", **{field_name: "u1"})
        assert intent_of(START, team).approvals == {}
    team_rejection = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Unit="u1")
    assert REQUIREMENTS in intent_of(START, APPROVED, team_rejection).approvals


def test_row_without_items_is_an_approval_with_no_items():
    approval = intent_of(START, gate("2026-09-26T10:00:00Z")).approvals[REQUIREMENTS]
    assert approval == Approval(REQUIREMENTS, None, None, None)


def test_row_with_malformed_items_is_not_an_approval():
    bad = gate("2026-09-26T10:30:00Z", Items="req~a~1, nonsense")
    assert intent_of(START, bad).approvals == {}
    assert intent_of(START, APPROVED, bad).approvals[REQUIREMENTS].items == ("req~a~1", "req~b~1")  # the earlier row


def test_row_for_a_slug_off_the_route_is_not_an_approval():
    off = gate("2026-09-26T10:00:00Z", stage="reverse-engineering", Items="req~a~1")
    unknown = gate("2026-09-26T10:00:00Z", stage="no-such-stage", Items="req~a~1")
    assert intent_of(START, SKIPS, off, unknown).approvals == {}


def test_stage_progress_marks_never_change_an_approval():
    assert intent_of(START).approvals == {}  # every route stage is marked [x], and none is approved
    state = FULL_STATE.replace(f"- [x] requirements-analysis {DASH}", f"- [ ] requirements-analysis {DASH}")
    assert REQUIREMENTS in intent_of(BASE, state=state).approvals


def test_named_items_hold_the_ids_of_every_counting_row():
    other = gate("2026-09-26T10:30:00Z", stage="reverse-engineering", Items="req~z~9")
    assert intent_of(START, APPROVED, other).named_items == {"req~a~1", "req~b~1", "req~z~9"}


def test_voided_rows_name_nothing():
    rejected = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Feedback="Rework.")
    assert intent_of(START, APPROVED, rejected).named_items == frozenset()
    assert intent_of(APPROVED, block("2026-09-26T11:00:00Z", "WORKFLOW_STARTED")).named_items == frozenset()
    later = gate("2026-09-26T12:00:00Z", Items="req~c~1")
    assert intent_of(START, APPROVED, rejected, later).named_items == {"req~c~1"}
    other = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", stage="code-generation")  # another stage's rejection
    assert intent_of(START, APPROVED, other).named_items == {"req~a~1", "req~b~1"}


def test_rows_without_items_name_nothing():
    assert intent_of(START, gate("2026-09-26T10:00:00Z")).named_items == frozenset()
    assert intent_of(START, gate("2026-09-26T10:00:00Z", Items="nonsense")).named_items == frozenset()
    rejected = gate("2026-09-26T10:00:00Z", "GATE_REJECTED", Items="req~z~9")  # only an approval names its items
    assert intent_of(START, rejected).named_items == frozenset()


def test_team_rows_name_nothing_in_named_items():
    team = gate("2026-09-26T10:00:00Z", Items="req~a~1", Unit="u1", Gate_Scope="per-stage")
    assert intent_of(START, team).named_items == frozenset()


def test_approval_is_current_when_items_and_revisions_match():
    index = Index((item("req~a~1"), item("req~b~1")), (), ())
    state = plan.build(intent_of(BASE), index).stages[0]
    assert (state.state, state.items) == ("current", index.items)
    extra = Index((*index.items, item("req~c~1", stage=f"{REQUIREMENTS}-extra")), (), ())  # a stage of a longer name
    assert plan.build(intent_of(BASE), extra).stages[0].state == "current"


def test_approval_is_outdated_when_a_revision_moved():
    index = Index((item("req~a~2"), item("req~b~1")), (), ())
    assert plan.build(intent_of(BASE), index).stages[0].state == "outdated"
    assert plan.build(intent_of(BASE), Index((item("req~a~1"),), (), ())).stages[0].state == "outdated"  # one gone
    assert plan.build(intent_of(BASE), Index((*index.items, item("req~c~1")), (), ())).stages[0].state == "outdated"
    grown = Index((item("req~a~1"), item("req~b~1"), item("req~c~1")), (), ())  # an item added after the approval
    assert plan.build(intent_of(BASE), grown).stages[0].state == "outdated"


def test_approval_without_items_is_current_and_never_outdated():
    current = intent_of(START, SKIPS, gate("2026-09-26T10:00:00Z"))
    index = Index((item("req~a~7"), item("req~new~1")), (), ())
    assert plan.build(current, index).stages[0].state == "current"


def test_stage_without_a_row_has_no_approval():
    built = plan.build(intent_of(BASE), Index((), (), ()))
    assert [(state.stage, state.approval, state.state) for state in built.stages[1:]] == [
        (STAGES[1], None, "none"),
        (STAGES[2], None, "none"),
    ]


def test_frontier_is_the_first_stage_without_a_current_approval():
    index = Index((item("req~a~1"), item("req~b~1")), (), ())
    assert plan.build(intent_of(BASE), index).frontier == "construction/code-generation"
    assert plan.build(intent_of(START, SKIPS), index).frontier == REQUIREMENTS
    assert plan.build(intent_of(BASE), Index((item("req~a~2"),), (), ())).frontier == REQUIREMENTS


def test_frontier_is_none_when_every_stage_is_approved():
    rows = [gate("2026-09-26T10:00:00Z", stage=slug, Items="") for slug in ("requirements-analysis", "code-generation")]
    rows.append(gate("2026-09-26T10:30:00Z", stage="build-and-test"))
    built = plan.build(intent_of(START, SKIPS, *rows), Index((), (), ()))
    assert [state.state for state in built.stages] == ["current", "current", "current"]
    assert built.frontier is None


def test_rejected_stage_is_the_frontier_with_approval_none():
    rejected = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Feedback="Rework.")
    built = plan.build(intent_of(BASE, rejected), Index((item("req~a~1"), item("req~b~1")), (), ()))
    assert (built.stages[0].approval, built.stages[0].state, built.frontier) == (None, "none", REQUIREMENTS)


CODE_GENERATION = STAGES[1]
BUILD_AND_TEST = STAGES[2]
PLAN_PATH = f"r/{CODE_GENERATION}/plan.md"


def delivers(task_text, req_text, line=7):
    return Link("Delivers", "task", ident(req_text), PLAN_PATH, line, owner=ident(task_text))


def depends(task_text, other_text, line=8):
    return Link("Depends", "task", ident(other_text), PLAN_PATH, line, owner=ident(task_text))


def task(text, line=3):
    return item(text, stage=CODE_GENERATION, line=line)


def planned(*blocks, items=(), links=(), state=FULL_STATE, table=None):
    """Return the plan and the index of an intent that the audit blocks describe, over the given items and links."""
    index = Index(tuple(items), tuple(links), ())
    return plan.build(intent_of(*blocks, state=state, table=table), index), index


def found_in(stage, **fields):
    return Finding("r/x.md", 1, "earnest/gap", "req~a~1", "m", stage=stage, intent="r", **fields)


def test_stage_of_a_path_under_a_route_stage():
    current = intent_of(BASE)
    assert plan.stage_of(current, "r/inception/requirements-analysis/requirements.md") == REQUIREMENTS
    assert plan.stage_of(current, f"r/{CODE_GENERATION}/deep/plan.md") == CODE_GENERATION


def test_stage_of_a_path_outside_every_stage():
    current = intent_of(BASE)
    for path in ("r/aidlc-state.md", "src/a.py", "r/inception/reverse-engineering/a.md", "rr/inception/x.md"):
        assert plan.stage_of(current, path) is None


def test_in_tree_for_paths_outside_every_intent():
    assert plan.in_tree([intent_of(BASE)], "src/a.py")
    assert plan.in_tree([intent_of(BASE)], "docs/readme.md")
    assert plan.in_tree([], "r/aidlc-state.md")


def test_in_tree_for_a_route_stage_artifact():
    assert plan.in_tree([intent_of(BASE)], "r/inception/requirements-analysis/requirements.md")
    assert plan.in_tree([intent_of(BASE)], f"r/{CODE_GENERATION}/plan.md")


def test_in_tree_is_false_for_state_audit_engine_and_off_route_stage_files():
    current = intent_of(BASE)
    for path in (
        "r/aidlc-state.md",
        "r/audit/a.md",
        "r/.aidlc-engine/sensors/earnest/detail.md",
        "r/inception/reverse-engineering/notes.md",
        "r/loose.md",
    ):
        assert not plan.in_tree([current], path)


def test_produces_is_the_union_of_the_route_stages_types():
    assert plan.produces([intent_of(BASE)]) == {"req", "task", "impl", "utest", "itest", "stest"}


def test_produces_pins_the_tag_types_of_code_generation():
    assert {"impl", "utest", "itest", "stest", "task"} <= plan.PRODUCES["code-generation"]
    assert plan.PRODUCES["requirements-analysis"] == {"req"}
    assert plan.PRODUCES.get("build-and-test", frozenset()) == frozenset()


def test_unknown_slug_produces_nothing():
    state = FULL_STATE.replace("### OPERATION PHASE", f"### OPERATION PHASE\n- [x] mystery-stage {DASH} EXECUTE: x")
    assert plan.produces([intent_of(BASE, state=state)]) == {"req", "task", "impl", "utest", "itest", "stest"}


def test_nfr_requirements_produces_req():
    state = f"## Stage Progress\n### CONSTRUCTION PHASE\n- [x] nfr-requirements {DASH} EXECUTE: x\n"
    assert plan.produces([intent_of(BASE, state=state)]) == {"req"}


def test_produces_is_none_when_the_route_produces_nothing():
    assert plan.produces([intent_of(BASE, state="## Stage Progress\n")]) is None  # an emptied route is no route rule
    assert plan.produces([intent_of(BASE, state="")]) is None


def test_produces_is_none_without_an_intent_and_keeps_a_units_routes_needs():
    assert plan.produces([]) is None
    wanted = {"req", "unit", "task", "impl", "utest", "itest", "stest"}
    assert plan.produces([intent_of(BASE, state=UNITS_STATE)]) == wanted
    assert plan.produces([intent_of(BASE, state=UNITS_STATE), intent_of(BASE)]) == wanted


def test_in_tree_of_a_units_intent_drops_bookkeeping_and_keeps_per_unit_files():
    units = intent_of(BASE, state=UNITS_STATE, directory="u")
    assert not plan.in_tree([units], "u/aidlc-state.md")
    assert not plan.in_tree([units], "u/audit/a.md")
    assert plan.in_tree([units], "u/inception/requirements-analysis/requirements.md")
    assert plan.in_tree([units], "u/construction/any-dir/code-generation/code-generation-plan.md")


def test_stage_is_not_done_without_an_approval():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    assert plan.statuses(built, index, [], {})[BUILD_AND_TEST] == plan.StageStatus("not done", 0, 0, "none")


def test_stage_is_done_with_an_approval_and_no_error():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    assert plan.statuses(built, index, [], {})[REQUIREMENTS] == plan.StageStatus("done", 0, 0, "current")


def test_stage_is_not_done_with_an_error_counted_against_it():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    counted_ = [
        found_in(REQUIREMENTS),  # an error, and the only one that counts
        found_in(REQUIREMENTS, position="ahead"),  # a note
        found_in(REQUIREMENTS, note=True),
        found_in(CODE_GENERATION),  # another stage
        Finding("r/x.md", 1, "earnest/unplanned", "req~a~1", "m", stage=REQUIREMENTS, intent="r"),  # a warning
        Finding("r/x.md", 1, "earnest/gap", "req~a~1", "m", stage=REQUIREMENTS, intent="other"),
    ]
    assert plan.statuses(built, index, counted_, {})[REQUIREMENTS] == plan.StageStatus("not done", 1, 0, "current")


def test_stage_is_not_done_with_an_open_task():
    approved = gate("2026-09-26T10:30:00Z", stage="code-generation", Items="task~a~1, task~b~1")
    items = [item("req~a~1"), item("req~b~1"), task("task~a~1"), task("task~b~1", 9)]
    links = [delivers("task~a~1", "req~a~1"), delivers("task~b~1", "req~b~1", 13)]
    built, index = planned(BASE, approved, items=items, links=links)
    status = plan.statuses(built, index, [], {"req~a~1": "traced", "req~b~1": "traced"})[CODE_GENERATION]
    assert status == plan.StageStatus("not done", 0, 2, "current")


def test_task_delivering_a_req_is_never_done_before_evidence():
    mine = task("task~a~1")
    index = Index((item("req~a~1"), mine), (delivers("task~a~1", "req~a~1"),), ())
    assert not plan.task_done(mine, index, {"req~a~1": "traced"})
    assert not plan.task_done(mine, index, {})
    assert plan.task_done(mine, index, {"req~a~1": "evidenced"})  # the rule, which no M2 requirement can meet
    stale = Index((item("req~a~2"), mine), (delivers("task~a~1", "req~a~1"),), ())
    assert not plan.task_done(mine, stale, {"req~a~2": "evidenced"})  # it delivers an older revision
    gone = Index((mine,), (delivers("task~a~1", "req~zzz~1"),), ())
    assert not plan.task_done(mine, gone, {})
    decision = Index((item("dsn~d~1"), mine), (delivers("task~a~1", "dsn~d~1"),), ())
    assert not plan.task_done(mine, decision, {})
    cover = Link("Covers", "impl", ident("dsn~d~1"), "src/a.py", 3)
    assert plan.task_done(mine, Index(decision.items, (*decision.links, cover), ()), {})


def test_reasons_count_errors_open_tasks_and_approval():
    stale, index = planned(BASE, items=[item("req~a~2"), item("req~b~1")])
    errors = [found_in(REQUIREMENTS), found_in(REQUIREMENTS)]
    assert plan.statuses(stale, index, errors, {})[REQUIREMENTS] == plan.StageStatus("not done", 2, 0, "outdated")
    stest = Link("Covers", "stest", ident("feat~f~1"), "tests/a.feature", 3)
    built, index = planned(BASE, gate("2026-09-26T10:30:00Z", stage="build-and-test"), links=[stest, stest])
    assert plan.statuses(built, index, [], {})[BUILD_AND_TEST] == plan.StageStatus("not done", 0, 1, "current")


def test_unplanned_counts_against_the_first_code_generation_stage():
    items = [item("req~a~1", line=3), item("req~b~1", line=8)]
    built, index = planned(BASE, items=items, links=[delivers("task~t~1", "req~a~1")])
    (found,) = plan.plan_findings(built, index)
    assert (found.rule, found.path, found.line, found.subject, found.level) == (
        "earnest/unplanned",
        "r/inception/requirements-analysis/doc.md",
        8,
        "req~b~1",
        "warning",
    )
    assert (found.stage, found.intent) == (CODE_GENERATION, "r")
    assert "`req~b~1` is delivered by no task" in found.message


def test_unplanned_ignores_the_delivered_revision():
    built, index = planned(BASE, items=[item("req~a~2")], links=[delivers("task~t~1", "req~a~1")])
    assert plan.plan_findings(built, index) == []


def test_unplanned_leaves_out_a_requirement_outside_the_intent_directory():
    outside = [Item(Id("req", "z", 1), "docs/z.md", 1), Item(Id("req", "y", 1), "rr/inception/y.md", 1)]
    built, index = planned(BASE, items=[item("req~a~1"), *outside], links=[delivers("task~t~1", "req~a~1")])
    assert plan.plan_findings(built, index) == []


def test_route_without_code_generation_raises_no_unplanned():
    state = FULL_STATE.replace(f"- [x] code-generation {DASH} EXECUTE", f"- [x] code-generation {DASH} SKIP")
    built, index = planned(BASE, items=[item("req~a~1")], state=state)
    assert CODE_GENERATION not in built.intent.route
    assert plan.plan_findings(built, index) == []


def test_cycle_is_located_at_the_first_item_in_id_order():
    items = [task("task~b~1", 9), task("task~a~1", 3)]
    built, index = planned(
        BASE, items=items, links=[depends("task~b~1", "task~a~1"), depends("task~a~1", "task~b~1", 4)]
    )
    (found,) = plan.plan_findings(built, index)
    assert (found.rule, found.path, found.line, found.subject, found.level) == (
        "earnest/cycle",
        f"r/{CODE_GENERATION}/doc.md",
        3,
        "task~a~1",
        "error",
    )
    assert (found.stage, found.intent) == (CODE_GENERATION, "r")


def test_cycle_message_lists_the_loop():
    items = [task("task~a~1", 3), task("task~b~1", 9)]
    built, index = planned(BASE, items=items, links=[depends("task~a~1", "task~b~1"), depends("task~b~1", "task~a~1")])
    (found,) = plan.plan_findings(built, index)
    assert "task~a~1 -> task~b~1 -> task~a~1" in found.message
    alone, own = planned(BASE, items=[task("task~a~1")], links=[depends("task~a~1", "task~a~1")])
    assert "task~a~1 -> task~a~1" in plan.plan_findings(alone, own)[0].message


def test_overlapping_cycles_are_each_located_at_their_first_item_in_id_order():
    items = [task("task~aa~1", 3), task("task~bb~1", 9), task("task~cc~1", 15)]
    links = [
        depends("task~aa~1", "task~bb~1"),
        depends("task~bb~1", "task~aa~1"),
        depends("task~aa~1", "task~cc~1"),
        depends("task~cc~1", "task~aa~1"),
    ]
    built, index = planned(BASE, items=items, links=links)
    found = plan.plan_findings(built, index)
    assert [(f.line, f.subject) for f in found] == [(3, "task~aa~1"), (3, "task~aa~1")]
    loops = ["task~aa~1 -> task~bb~1 -> task~aa~1", "task~aa~1 -> task~cc~1 -> task~aa~1"]
    assert [any(loop in f.message for f in found) for loop in loops] == [True, True]
    assert all(f.message.startswith("the plan's dependencies form a cycle, task~aa~1 -> ") for f in found)


def test_cycles_are_found_through_the_lowest_id_neighbour_first():
    items = [task("task~a~1", 3), task("task~b~1", 9), task("task~c~1", 15)]
    links = [
        depends("task~a~1", "task~c~1"),
        depends("task~a~1", "task~b~1"),
        depends("task~b~1", "task~a~1"),
        depends("task~c~1", "task~a~1"),
    ]
    built, index = planned(BASE, items=items, links=links)
    found = plan.plan_findings(built, index)
    assert [f.message.split("cycle, ")[1].split(":")[0] for f in found] == [
        "task~a~1 -> task~b~1 -> task~a~1",
        "task~a~1 -> task~c~1 -> task~a~1",
    ]


def test_acyclic_graph_has_no_cycle():
    items = [task("task~a~1", 3), task("task~b~1", 9)]
    built, index = planned(BASE, items=items, links=[depends("task~b~1", "task~a~1")])
    assert plan.plan_findings(built, index) == []


def test_finding_in_a_stage_artifact_takes_its_stage_and_intent():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    (found,) = plan.place(
        [built], index, [Finding("r/inception/requirements-analysis/x.md", 4, "earnest/duplicate", "req~a~1", "m")]
    )
    assert (found.stage, found.intent, found.position, found.level) == (REQUIREMENTS, "r", "behind", "error")
    assert found.text.startswith(f"regression in approved stage {REQUIREMENTS}: ")


def test_place_keeps_a_preset_stage():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    preset = Finding(
        "r/inception/requirements-analysis/x.md",
        4,
        "earnest/unplanned",
        "req~a~1",
        "m",
        stage=CODE_GENERATION,
        intent="r",
    )
    (found,) = plan.place([built], index, [preset])
    assert (found.stage, found.position) == (CODE_GENERATION, "current")
    alien = Finding("x", 1, "earnest/gap", "s", "m", stage="s/x", intent="elsewhere", position="ahead")
    (foreign,) = plan.place([built], index, [alien])
    assert (foreign.stage, foreign.intent, foreign.position) == ("s/x", "elsewhere", "ahead")  # no such plan: unchanged


def test_tag_finding_reaches_the_stage_of_the_delivering_task():
    items = [item("req~a~1"), item("req~b~1"), task("task~t~1")]
    built, index = planned(BASE, items=items, links=[delivers("task~t~1", "req~a~1")])
    tag = Finding("src/a.py", 4, "earnest/outdated", "req~a~1", "m")
    (found,) = plan.place([built], index, [tag])
    assert (found.stage, found.intent, found.position) == (CODE_GENERATION, "r", "current")


def test_a_tag_finding_reaches_the_stage_of_the_first_task_that_delivers_its_item():
    in_code = delivers("task~t~1", "dsn~x~1")
    in_build = Link("Delivers", "task", ident("dsn~x~1"), f"r/{BUILD_AND_TEST}/plan.md", 2, owner=ident("task~u~1"))
    for subject in ("dsn~x~1", "dsn~x~12"):  # a revision other than the delivered one still names the item
        tag = Finding("src/a.py", 4, "earnest/orphaned", subject, "m")
        stages = []
        for links in ([in_code, in_build], [in_build, in_code]):
            built, index = planned(BASE, links=links)
            stages.append(plan.place([built], index, [tag])[0].stage)
        assert stages == [CODE_GENERATION, BUILD_AND_TEST]


def test_a_gap_counts_against_the_first_route_stage_that_produces_its_type():
    analysis = f"- [x] requirements-analysis {DASH} EXECUTE: always\n"
    state = FULL_STATE.replace(analysis, f"{analysis}- [x] domain-design {DASH} EXECUTE: x\n").replace(
        "### CONSTRUCTION PHASE\n", f"### CONSTRUCTION PHASE\n- [x] functional-design {DASH} EXECUTE: x\n"
    )
    built, index = planned(BASE, state=state)
    (found,) = plan.place([built], index, [Finding("r/x.md", 1, "earnest/gap", "req~a~1", "m", child="dsn")])
    assert found.stage == "inception/domain-design"  # functional-design, later on the route, produces dsn too


def test_place_gives_a_finding_to_the_innermost_intent_that_holds_its_path():
    outer, index = planned(BASE)
    inner = plan.build(intent_of(BASE, directory="r/sub"), index)
    finding = Finding(f"r/sub/{REQUIREMENTS}/x.md", 1, "earnest/duplicate", "req~a~1", "m")
    for plans in ([outer, inner], [inner, outer]):
        (placed,) = plan.place(plans, index, [finding])
        assert (placed.intent, placed.stage) == ("r/sub", REQUIREMENTS)


def test_inside_holds_whole_path_components_only():
    assert plan.inside(intent_of(BASE), "r/a.md")
    assert not plan.inside(intent_of(BASE), "rr/a.md")
    assert not plan.inside(intent_of(BASE), "r-b/a.md")
    assert plan.inside(intent_of(BASE, directory=""), "any/a.md")  # the root record directory holds every path


def test_a_plan_without_a_frontier_places_every_finding_behind():
    rows = [gate("2026-09-26T10:00:00Z", stage=slug, Items="") for slug in ("requirements-analysis", "code-generation")]
    rows.append(gate("2026-09-26T10:30:00Z", stage="build-and-test"))
    index = Index((), (), ())
    built = plan.build(intent_of(START, SKIPS, *rows), index)
    assert built.frontier is None
    findings = [Finding(f"r/{stage}/x.md", 1, "earnest/duplicate", "req~a~1", "m") for stage in STAGES]
    placed = plan.place([built], index, findings)
    assert [(f.stage, f.position, f.level) for f in placed] == [(stage, "behind", "error") for stage in STAGES]


def test_stest_reaches_the_build_and_test_stage():
    stest = Link("Covers", "stest", ident("feat~f~1"), "tests/a.feature", 3)
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")], links=[stest])
    (found,) = plan.place([built], index, [Finding("tests/a.feature", 3, "earnest/orphaned", "feat~f~1", "m")])
    assert (found.stage, found.position, found.level) == (BUILD_AND_TEST, "ahead", "note")
    (other,) = plan.place([built], index, [Finding("tests/a.feature", 9, "earnest/orphaned", "feat~f~1", "m")])
    assert other.stage is None


def test_gap_counts_against_the_stage_of_the_missing_childs_type():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    path = "r/inception/requirements-analysis/doc.md"
    gaps = [Finding(path, 5, "earnest/gap", "req~a~1", "m", child=kind) for kind in ("impl", "utest", "req")]
    stages = [found.stage for found in plan.place([built], index, gaps)]
    assert stages == [CODE_GENERATION, CODE_GENERATION, REQUIREMENTS]  # a req gap falls back to its own file's stage


def test_finding_reaching_no_stage_keeps_position_current():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    orphan = Finding("src/z.py", 2, "earnest/orphaned", "req~zzz~1", "m")
    near = Finding("src/z.py", 3, "earnest/near-miss", "[impl-x]", "m")
    for found in plan.place([built], index, [orphan, near]):
        assert (found.stage, found.intent, found.position, found.level) == (None, None, "current", "error")


def test_position_behind_current_and_ahead():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    paths = [f"r/{stage}/x.md" for stage in STAGES]
    found = plan.place([built], index, [Finding(path, 1, "earnest/duplicate", "req~a~1", "m") for path in paths])
    assert [(f.stage, f.position) for f in found] == list(zip(STAGES, ["behind", "current", "ahead"], strict=True))


def test_place_takes_several_plans_and_uses_each_findings_own_frontier():
    first, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    second = plan.build(intent_of(START, SKIPS, directory="s"), index)
    mine = Finding(f"r/{CODE_GENERATION}/x.md", 1, "earnest/duplicate", "req~a~1", "m")
    theirs = Finding(f"s/{CODE_GENERATION}/x.md", 1, "earnest/duplicate", "req~a~1", "m")
    placed = plan.place([first, second], index, [mine, theirs])
    assert [(f.intent, f.position) for f in placed] == [("r", "current"), ("s", "ahead")]


def test_ahead_finding_is_a_note():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    (found,) = plan.place([built], index, [Finding(f"r/{BUILD_AND_TEST}/x.md", 1, "earnest/duplicate", "req~a~1", "m")])
    assert (found.position, found.level) == ("ahead", "note")
    assert found.text == f"expected at {BUILD_AND_TEST}: m"


def test_finding_in_a_stage_off_the_route_is_stage_less_and_current():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    (found,) = plan.place(
        [built], index, [Finding("r/inception/reverse-engineering/a.md", 1, "earnest/duplicate", "req~a~1", "m")]
    )
    assert (found.stage, found.intent, found.position) == (None, None, "current")


def test_finding_under_an_intent_without_a_plan_is_left_alone():
    built, index = planned(BASE, items=[item("req~a~1"), item("req~b~1")])
    elsewhere = Finding("other/inception/requirements-analysis/x.md", 1, "earnest/duplicate", "req~a~1", "m")
    assert plan.place([], index, [elsewhere])[0] is elsewhere
    (found,) = plan.place([built], index, [elsewhere])
    assert (found.stage, found.intent, found.position) == (None, None, "current")


def stale_plan(*items_, extra=()):
    """Return the plan of an intent whose requirements approval names req~a~1 and req~b~1, over the given items."""
    return planned(BASE, *extra, items=list(items_))


def test_stale_approval_is_a_note_at_the_position_of_its_stage():
    built, index = stale_plan(item("req~a~2", line=3), item("req~b~1", line=8))
    (found,) = plan.approval_findings(built)
    assert (found.rule, found.path, found.line, found.subject, found.note) == (
        "earnest/outdated",
        "r/inception/requirements-analysis/doc.md",
        3,
        "req~a~2",
        True,
    )
    (placed,) = plan.place([built], index, [found])
    assert (placed.stage, placed.intent, placed.position, placed.level) == (REQUIREMENTS, "r", "current", "note")


def test_stale_approval_in_a_stage_after_the_frontier_reads_ahead():
    approved = gate("2026-09-26T10:30:00Z", stage="code-generation", Items="task~a~1")
    built, index = planned(START, SKIPS, approved, items=[task("task~a~2")])
    assert built.frontier == REQUIREMENTS  # nothing approves the requirements stage
    (found,) = plan.approval_findings(built)
    (placed,) = plan.place([built], index, [found])
    assert (placed.stage, placed.position, placed.level) == (CODE_GENERATION, "ahead", "note")


def test_stale_approval_is_located_at_each_moved_item():
    built, _ = stale_plan(item("req~a~2", line=3), item("req~b~3", line=8))
    assert [(f.line, f.subject) for f in plan.approval_findings(built)] == [(3, "req~a~2"), (8, "req~b~3")]


def test_stale_approval_names_the_stage_and_the_current_revision():
    built, _ = stale_plan(item("req~a~2"), item("req~b~1"))
    (found,) = plan.approval_findings(built)
    assert REQUIREMENTS in found.message
    assert "approval" in found.message
    assert "revision 2" in found.message
    assert "`req~a~1`" in found.message


def test_earlier_rows_raise_nothing_after_a_fresh_approval():
    fresh = gate("2026-09-26T10:30:00Z", Items="req~a~2, req~b~1")
    built, _ = stale_plan(item("req~a~2"), item("req~b~1"), extra=[fresh])
    assert built.stages[0].state == "current"
    assert plan.approval_findings(built) == []


def test_stale_approval_with_a_removed_or_unnamed_item_reads_outdated_without_a_located_finding():
    gone, _ = stale_plan(item("req~a~1"))
    assert gone.stages[0].state == "outdated"
    assert plan.approval_findings(gone) == []
    extra, _ = stale_plan(item("req~a~1"), item("req~b~1"), item("req~c~1"))
    assert extra.stages[0].state == "outdated"
    assert plan.approval_findings(extra) == []


def test_properties_list_stages_in_route_order_and_tasks_sorted():
    items = [item("req~a~1"), item("req~b~1"), task("task~b~1"), task("task~a~1", 9)]
    built, index = planned(BASE, items=items, links=[delivers("task~a~1", "req~a~1")])
    statuses = {"r": plan.statuses(built, index, [], {})}
    (entry,) = plan.properties([built], statuses, index, {})["intents"]
    assert (entry["intent"], entry["frontier"], entry["units"]) == ("r", CODE_GENERATION, [])
    assert entry["stages"] == [
        {"stage": REQUIREMENTS, "status": "done", "approval": "current", "approvedBy": "human"},
        {"stage": CODE_GENERATION, "status": "not done", "approval": "none", "approvedBy": None},
        {"stage": BUILD_AND_TEST, "status": "not done", "approval": "none", "approvedBy": None},
    ]
    assert entry["tasks"] == [{"id": "task~a~1", "status": "not done"}, {"id": "task~b~1", "status": "done"}]


def test_properties_hold_one_entry_per_supported_intent():
    first, index = planned(BASE, items=[item("req~a~2"), item("req~b~1")])
    second = plan.build(intent_of(START, SKIPS, directory="a"), index)
    statuses = {p.intent.directory: plan.statuses(p, index, [], {}) for p in (first, second)}
    props = plan.properties([first, second], statuses, index, {})
    assert [entry["intent"] for entry in props["intents"]] == ["a", "r"]
    stale = props["intents"][1]["stages"][0]
    assert (stale["approval"], stale["approvedBy"]) == ("outdated", None)  # `approvedBy` is for a current approval


def test_properties_list_a_units_intent():
    built, index = planned(BASE)
    units = plan.build(intent_of(BASE, state=UNITS_STATE, directory="u"), index)
    statuses = {p.intent.directory: plan.statuses(p, index, [], {}) for p in (built, units)}
    props = plan.properties([units, built], statuses, index, {})
    assert [entry["intent"] for entry in props["intents"]] == ["r", "u"]
    stages = [stage["stage"] for stage in props["intents"][1]["stages"]]
    assert stages == [REQUIREMENTS, "inception/units-generation", BUILD_AND_TEST]  # no table: no per-unit stage


def source(path, data="x"):
    return Source(path, MARKDOWN, (), digest=digest_of(data.encode()))


def hashed(text, body, stage=REQUIREMENTS, line=1):
    return Item(ident(text), f"r/{stage}/doc.md", line, None, body)


def document(built, stage, tree, findings):
    return plan.assessment_document(built, stage, tree, findings)


TREE = [source("src/a.py", "code")]


def test_evaluated_tree_is_the_sources_in_tree():
    paths = [
        "src/a.py",
        "r/aidlc-state.md",
        "r/audit/a.md",
        f"r/{REQUIREMENTS}/x.md",
        "r/inception/reverse-engineering/y.md",
    ]
    tree = plan.evaluated_tree([source(path) for path in paths], [intent_of(BASE)])
    assert [each.path for each in tree] == ["src/a.py", f"r/{REQUIREMENTS}/x.md"]


def test_tree_digest_changes_when_an_evaluated_file_changes():
    one, two = [source("a.py", "1")], [source("a.py", "2")]
    assert plan.tree_digest(one) != plan.tree_digest(two)
    assert plan.tree_digest(one) == plan.tree_digest([source("a.py", "1")])
    pair = [source("b.py", "1"), source("a.py", "1")]
    assert plan.tree_digest(pair) == plan.tree_digest(pair[::-1])  # sorted by uri
    assert plan.tree_digest([source("a b.py", "1")]) != plan.tree_digest([source("a%20b.py", "2")])


def test_tree_digest_is_the_digest_of_the_compact_json_of_uri_and_digest_pairs_sorted_by_uri():
    tree = [
        Source("src/z.py", MARKDOWN, (), digest="sha256:2"),
        Source("src/\u00e9.py", MARKDOWN, (), digest="sha256:1"),
    ]
    # the encoded name sorts before `z`, though the name itself sorts after it
    assert plan.tree_digest(tree) == digest_of(b'[["src/%C3%A9.py","sha256:1"],["src/z.py","sha256:2"]]')


def test_tree_digest_ignores_a_state_or_audit_edit():
    intents = [intent_of(BASE)]
    base = [source("src/a.py"), source("r/aidlc-state.md", "one"), source("r/audit/a.md", "one")]
    edited = [source("src/a.py"), source("r/aidlc-state.md", "two"), source("r/audit/a.md", "two")]
    assert plan.tree_digest(plan.evaluated_tree(base, intents)) == plan.tree_digest(
        plan.evaluated_tree(edited, intents)
    )


def test_document_leaves_out_the_findings_of_the_task_change():
    built, _ = planned(BASE, items=[hashed("req~a~1", "h1", line=3)])
    tree = [source(f"r/{REQUIREMENTS}/doc.md"), source("src/a.py")]
    task_change = [
        Finding(f"r/{REQUIREMENTS}/doc.md", 5, "earnest/impact-degraded", "x", "m", stage=REQUIREMENTS, intent="r"),
        Finding("src/a.py", 2, "earnest/impact-degraded", "src/a.py:2", "m"),
        Finding("src/a.py", 2, "earnest/out-of-task", "task~t~1", "m", stage=REQUIREMENTS, intent="r"),
    ]
    assert document(built, REQUIREMENTS, tree, task_change) == document(built, REQUIREMENTS, tree, [])


def test_document_holds_position_free_findings():
    built, _ = planned(BASE, items=[hashed("req~b~1", "h2", line=8), hashed("req~a~1", "h1", line=3)])
    tree = [source(f"r/{REQUIREMENTS}/doc.md"), source("src/a.py")]
    found = Finding(f"r/{REQUIREMENTS}/doc.md", 8, "earnest/duplicate", "req~b~1", "m", stage=REQUIREMENTS, intent="r")
    shifted = Finding("src/a.py", 4, "earnest/orphaned", "req~z~1", "z", position="current")
    shown = document(built, REQUIREMENTS, tree, [found, shifted])
    assert shown == {
        "v": 1,
        "stage": f"r/{REQUIREMENTS}",
        "layers": ["trace"],
        "model": None,
        "prompt": None,
        "items": [["req~a~1", "h1"], ["req~b~1", "h2"]],
        "findings": [
            ["earnest/duplicate", f"r/{REQUIREMENTS}/doc.md", 8, "req~b~1", "m"],
            ["earnest/orphaned", "src/a.py", 4, "req~z~1", "z"],
        ],
        "tree": plan.tree_digest(tree),
    }
    moved = Finding(
        found.path, 8, found.rule, found.subject, found.message, stage=REQUIREMENTS, intent="r", position="ahead"
    )
    assert document(built, REQUIREMENTS, tree, [moved, shifted]) == shown  # the position takes no part


def test_findings_outside_the_tree_are_dropped_from_the_document():
    built, _ = planned(BASE, items=[hashed("req~a~1", "h1")])
    inside = Finding("src/a.py", 1, "earnest/orphaned", "req~z~1", "m")
    outside = Finding("r/aidlc-state.md", 17, "earnest/route-mismatch", "deployment-pipeline", "m")
    elsewhere = Finding(
        f"r/{CODE_GENERATION}/x.md", 1, "earnest/duplicate", "req~a~1", "m", stage=CODE_GENERATION, intent="r"
    )
    tree = [source("src/a.py"), source(f"r/{CODE_GENERATION}/x.md")]
    assert [entry[1] for entry in document(built, REQUIREMENTS, tree, [inside, outside, elsewhere])["findings"]] == [
        "src/a.py"
    ]


def test_document_leaves_out_approval_findings():
    built, _ = planned(BASE, items=[hashed("req~a~2", "h1"), hashed("req~b~1", "h2")])
    (note,) = plan.approval_findings(built)
    path = f"r/{REQUIREMENTS}/doc.md"
    tree = [source(path)]
    assert document(built, REQUIREMENTS, tree, [note]) == document(built, REQUIREMENTS, tree, [])


def test_recording_an_approval_leaves_the_hash_as_it_was():
    items = [hashed("req~a~1", "h1"), hashed("req~b~1", "h2"), hashed("task~t~1", "h3", CODE_GENERATION)]
    before, index = planned(BASE, items=items)
    after, _ = planned(BASE, gate("2026-09-26T12:00:00Z", stage="code-generation", Items="task~t~1"), items=items)
    assert (before.frontier, after.frontier) == (CODE_GENERATION, BUILD_AND_TEST)
    tree = [source("src/a.py")]
    one = plan.assessment_hash(
        document(before, CODE_GENERATION, tree, plan.place([before], index, plan.plan_findings(before, index)))
    )
    two = plan.assessment_hash(
        document(after, CODE_GENERATION, tree, plan.place([after], index, plan.plan_findings(after, index)))
    )
    assert one == two


def test_hash_is_stable_across_two_runs():
    built, _ = planned(BASE, items=[hashed("req~a~1", "h1"), hashed("req~b~1", "h2")])
    first = plan.assessment_hash(document(built, REQUIREMENTS, TREE, []))
    assert first == plan.assessment_hash(document(built, REQUIREMENTS, TREE, []))
    assert first.startswith("sha256:")
    assert len(first) == len("sha256:") + 64
    assert first != plan.assessment_hash(document(built, REQUIREMENTS, [source("src/a.py", "other")], []))


def test_hash_excludes_commit_and_timestamp():
    built, _ = planned(BASE, items=[hashed("req~a~1", "h1")])
    assert set(document(built, REQUIREMENTS, TREE, [])) == {
        "v",
        "stage",
        "layers",
        "model",
        "prompt",
        "items",
        "findings",
        "tree",
    }


def test_baseline_records_when_none_is_held():
    built, _ = planned(START, SKIPS, items=[hashed("req~a~1", "h1"), hashed("req~b~1", "h2")])
    assert plan.next_bodies({}, built, REQUIREMENTS) == {"req~a~1": "h1", "req~b~1": "h2"}


def test_baseline_replaces_until_a_counting_row_names_the_revision():
    built, _ = planned(START, SKIPS, items=[hashed("req~a~1", "new")])
    held = {"req~a~1": "old", "req~other~1": "kept"}
    assert plan.next_bodies(held, built, REQUIREMENTS) == {"req~a~1": "new", "req~other~1": "kept"}
    assert held["req~a~1"] == "old"  # the argument is not changed


def test_baseline_freezes_after_a_counting_row_names_it():
    built, _ = planned(BASE, items=[hashed("req~a~1", "new"), hashed("req~b~1", "new")])
    assert plan.next_bodies({"req~a~1": "old", "req~b~1": "old"}, built, REQUIREMENTS) == {
        "req~a~1": "old",
        "req~b~1": "old",
    }


def test_baseline_for_a_bumped_revision_starts_free():
    built, _ = planned(BASE, items=[hashed("req~a~2", "new"), hashed("req~b~1", "new")])
    result = plan.next_bodies({"req~a~1": "old", "req~b~1": "old"}, built, REQUIREMENTS)
    assert result == {"req~a~1": "old", "req~a~2": "new", "req~b~1": "old"}
    again = plan.next_bodies({**result, "req~a~2": "newer"}, built, REQUIREMENTS)
    assert again["req~a~2"] == "new"  # no row names revision 2 yet, so each run replaces it


def test_baseline_replaces_again_after_a_rejection_voids_the_row():
    rejected = gate("2026-09-26T11:00:00Z", "GATE_REJECTED", Feedback="Rework.")
    built, _ = planned(BASE, rejected, items=[hashed("req~a~1", "new"), hashed("req~b~1", "new")])
    assert plan.next_bodies({"req~a~1": "old", "req~b~1": "old"}, built, REQUIREMENTS) == {
        "req~a~1": "new",
        "req~b~1": "new",
    }


def test_baseline_records_when_a_named_revision_has_no_held_hash():
    built, _ = planned(BASE, items=[hashed("req~a~1", "new"), hashed("req~b~1", "new")])
    assert plan.next_bodies({"req~b~1": "old"}, built, REQUIREMENTS) == {"req~a~1": "new", "req~b~1": "old"}


def test_frozen_bodies_keeps_only_hashes_a_counting_row_names():
    held = {"req~a~1": "x", "req~c~1": "y", "req~z~1": "z"}
    other = intent_of(START, SKIPS, gate("2026-09-26T10:00:00Z", Items="req~z~1"), directory="s")
    assert plan.frozen_bodies(held, [intent_of(BASE)]) == {"req~a~1": "x"}
    assert plan.frozen_bodies(held, [intent_of(BASE), other]) == {"req~a~1": "x", "req~z~1": "z"}
    assert plan.frozen_bodies(held, []) == {}


def test_header_carries_the_fields_and_the_reasons_of_the_status():
    built, _ = planned(BASE, items=[hashed("req~b~1", "h2"), hashed("req~a~1", "h1")])
    status = plan.StageStatus("not done", 2, 1, "outdated")
    run = Run(commit="a" * 40, dirty=True, timestamp="2026-09-26T12:00:00Z")
    held = plan.header(built, REQUIREMENTS, status, run, "sha256:" + "1" * 64)
    assert (held.intent, held.stage, held.commit, held.dirty, held.timestamp) == (
        "r",
        REQUIREMENTS,
        "a" * 40,
        True,
        "2026-09-26T12:00:00Z",
    )
    assert (held.layers, held.model, held.prompt) == (("trace",), None, None)
    assert held.items == ("req~a~1", "req~b~1")
    assert (held.status, held.digest) == ("not done", "sha256:" + "1" * 64)
    assert dict(held.reasons) == {"errors": 2, "openTasks": 1, "approval": "outdated"}


def test_scoped_keeps_stage_and_stageless_findings():
    built, _ = planned(BASE)
    mine = found_in(REQUIREMENTS)
    other_stage = found_in(CODE_GENERATION)
    stageless = Finding("src/a.py", 1, "earnest/orphaned", "req~z~1", "m")
    assert plan.scoped([mine, other_stage, stageless], built, REQUIREMENTS) == [mine, stageless]


def test_scoped_separates_equal_stage_ids_of_two_intents():
    built, _ = planned(BASE)
    ours = found_in(REQUIREMENTS)
    theirs = Finding("s/x.md", 1, "earnest/gap", "req~a~1", "m", stage=REQUIREMENTS, intent="s")
    assert plan.scoped([ours, theirs], built, REQUIREMENTS) == [ours]
    assert [found.intent for found in plan.scoped([ours, theirs], built, REQUIREMENTS)] == ["r"]


def test_dirty_counts_an_edited_scanned_file():
    assert plan.dirty(["src/a.py"], [intent_of(BASE)])
    assert plan.dirty(["tests/a.feature"], [intent_of(BASE)])
    assert not plan.dirty([], [intent_of(BASE)])


def test_dirty_ignores_the_audit_log_and_state_file():
    paths = ["r/aidlc-state.md", "r/audit/a.md", "r/audit/fixture-0000aaaa.md", "r/.aidlc-engine/sensors/x.md"]
    assert not plan.dirty(paths, [intent_of(BASE)])


def test_dirty_counts_a_deleted_stage_artifact():
    assert plan.dirty([f"r/{REQUIREMENTS}/requirements.md"], [intent_of(BASE)])  # a missing file is a change too


def test_dirty_ignores_an_unscanned_suffix():
    paths = ["data.json", "notes.txt", "Makefile", f"r/{REQUIREMENTS}/diagram.png"]
    assert not plan.dirty(paths, [intent_of(BASE)])


def test_dirty_counts_a_scratch_markdown_file():
    assert plan.dirty(["notes.md"], [intent_of(BASE)])
    assert plan.dirty(["r/scratch.md"], [intent_of(BASE)]) is False  # inside the record directory, in no route stage


def test_dirty_counts_a_deleted_tracked_markdown_file_outside_every_intent():
    assert plan.dirty(["docs/old.md"], [])
    assert plan.dirty(["docs/old.md"], [intent_of(BASE)])


def test_dirty_ignores_a_stage_diary_memory_md():
    memory = f"r/{REQUIREMENTS}/memory.md"
    assert not plan.dirty([memory], [intent_of(BASE)])
    assert plan.dirty([memory, f"r/{REQUIREMENTS}/requirements.md"], [intent_of(BASE)])


def test_dirty_ignores_a_units_intents_bookkeeping_and_sees_its_per_unit_files():
    units = intent_of(BASE, state=UNITS_STATE, directory="u")
    assert not plan.dirty(["u/aidlc-state.md", "u/audit/a.md", "u/.aidlc-engine/x.md"], [units])
    assert plan.dirty(["u/inception/requirements-analysis/r.md"], [units])
    assert plan.dirty(["u/construction/a-dir/code-generation/plan.md"], [units])


def test_find_intent_by_directory_option():
    one, two = intent_of(BASE, directory="a"), intent_of(BASE, directory="b")
    assert plan.find_intent([one, two], "b") is two
    assert plan.find_intent([one, two], "a") is one


def test_find_intent_single_record_without_the_option():
    only = intent_of(BASE, directory="a")
    assert plan.find_intent([only], None) is only


def test_find_intent_with_several_records_and_no_option_lists_them():
    with pytest.raises(plan.PlanError, match=r"--intent.*a.*b"):
        plan.find_intent([intent_of(BASE, directory="a"), intent_of(BASE, directory="b")], None)


def test_find_intent_with_no_record_raises():
    with pytest.raises(plan.PlanError, match=r"no record directory holds an aidlc-state\.md"):
        plan.find_intent([], None)


def test_find_intent_unknown_directory_names_the_candidates():
    with pytest.raises(plan.PlanError, match=r"zzz.*a, b"):
        plan.find_intent([intent_of(BASE, directory="a"), intent_of(BASE, directory="b")], "zzz")


def test_select_stage_by_phase_slash_slug():
    built, _ = planned(BASE)
    assert plan.select_stage(built, CODE_GENERATION) == CODE_GENERATION


def test_select_stage_by_unique_bare_slug():
    built, _ = planned(BASE)
    assert plan.select_stage(built, "code-generation") == CODE_GENERATION
    assert plan.select_stage(built, "requirements-analysis") == REQUIREMENTS


def test_select_stage_rejects_an_unknown_slug():
    built, _ = planned(BASE)
    with pytest.raises(plan.PlanError, match=r"no-such is not a stage on the route: .*requirements-analysis"):
        plan.select_stage(built, "no-such")
    with pytest.raises(plan.PlanError, match="not a stage on the route"):
        plan.select_stage(built, "inception/units-generation")  # a SKIP row is not on the route


def test_select_stage_names_the_state_file_when_an_unreadable_stage_progress_emptied_the_route():
    built, _ = planned(BASE, state=FULL_STATE.replace("## Stage Progress", "## Stage  Progress"))
    with pytest.raises(plan.PlanError) as error:
        plan.select_stage(built, "requirements-analysis")
    assert str(error.value) == (
        "requirements-analysis is not a stage on the route: the state file's Stage Progress cannot be read"
        " (r/aidlc-state.md:1)"
    )
    empty, _ = planned(START, state="## Stage Progress\n### INCEPTION PHASE\n" + f"- [x] a {DASH} SKIP\n")
    with pytest.raises(plan.PlanError, match=r"route: none$"):  # an empty route that reads fine says so plainly
        plan.select_stage(empty, "a")


def test_select_stage_rejects_an_ambiguous_bare_slug():
    state = FULL_STATE.replace(f"- [x] build-and-test {DASH}", f"- [x] requirements-analysis {DASH}")
    built, _ = planned(BASE, state=state)
    with pytest.raises(plan.PlanError, match=r"names several stages.*inception/requirements-analysis.*construction/"):
        plan.select_stage(built, "requirements-analysis")
    assert plan.select_stage(built, "inception/requirements-analysis") == "inception/requirements-analysis"


# Units routes: the unit table, per-unit stages, unit gates, lanes and unit status (M2b).

UNIT_STATE = UNITS_STATE.replace(
    "### CONSTRUCTION PHASE\n", f"### CONSTRUCTION PHASE\n- [ ] functional-design {DASH} EXECUTE: per unit\n"
)
UNITS_ROW = next(row.line for row in plan.parse_state(UNIT_STATE).rows if row.slug == "units-generation")
UNITS_GENERATION = "inception/units-generation"
TABLE_PATH = f"r/{UNITS_GENERATION}/unit-of-work.md"
TABLE = (
    "# Units\n\n| Unit ID | Directory | Responsibility |\n| --- | --- | --- |\n| A | a-dir | x |\n| B | b-dir | y |\n"
)


def unit(name, line=10, path=TABLE_PATH):
    return Item(ident(f"unit~{name}~1"), path, line)


def unit_link(key, owner, target, line=12):
    return Link(key, "unit", ident(target), TABLE_PATH, line, owner=ident(owner))


UNITS_AB = (unit("a"), unit("b", 11))


def units_plan(*blocks, items=UNITS_AB, links=(), table=TABLE, state=UNIT_STATE):
    return planned(START, SKIPS, *blocks, items=list(items), links=list(links), state=state, table=table)


def mismatches(built, index):
    return [found for found in plan.plan_findings(built, index) if found.rule == "earnest/route-mismatch"]


def test_parse_units_reads_the_first_unfenced_unit_id_and_directory_table():
    text = (
        "```\n| Unit ID | Directory |\n| --- | --- |\n| F | fenced |\n```\n\n"
        "| Name | Other |\n| --- | --- |\n| X | y |\n\n"
        "| Responsibility | Unit ID | Directory |\n|:--|--:|---|\n| r | U1.2 | u1-dir |\n| s | NFR3 | n3 |\n\nafter\n"
        "| Unit ID | Directory |\n| --- | --- |\n| Z | second-table |\n"
    )
    table = plan.parse_units(text, frozenset())
    assert table is not None
    assert [(row.name, row.directory, row.line) for row in table.rows] == [("u1-2", "u1-dir", 13), ("nfr3", "n3", 14)]
    assert table.bad == ()
    assert plan.parse_units(text.replace("\n", "\r\n"), frozenset()) == table


def test_parse_units_flags_unreadable_repeated_and_unsafe_rows():
    rows = ["| `u1` | a |", "| U 1 | b |", "| C | .. |", "| D | a/b |", "| E | code-generation |", "| F | F-dir |"]
    rows += ["| G | g |", "| g | h |", "| H | g |", "| I |"]
    text = "| Unit ID | Directory |\n| --- | --- |\n" + "\n".join(rows) + "\n"
    table = plan.parse_units(text, frozenset({"code-generation"}))
    assert table is not None
    assert [(row.name, row.directory) for row in table.rows] == [("g", "g")]
    assert [line for line, _ in table.bad] == [3, 4, 5, 6, 7, 8, 10, 11, 12]
    assert all(reason for _, reason in table.bad)


def test_parse_units_without_a_header_table_is_none():
    assert plan.parse_units("# Units\n\n| Unit | Dir |\n| --- | --- |\n| A | a |\n", frozenset()) is None
    assert plan.parse_units("| Unit ID | Directory |\n| A | a |\n", frozenset()) is None  # no delimiter row
    assert plan.parse_units("", frozenset()) is None


def test_missing_symlinked_or_headerless_table_is_a_route_mismatch_at_units_generation(tmp_path):
    put(tmp_path, {"r/aidlc-state.md": UNIT_STATE, "elsewhere.md": TABLE})
    listed = ["r/aidlc-state.md", TABLE_PATH]
    (record,) = plan.load(tmp_path, listed)
    assert record.table is None  # missing
    (tmp_path / TABLE_PATH).parent.mkdir(parents=True)
    (tmp_path / TABLE_PATH).symlink_to(tmp_path / "elsewhere.md")
    (record,) = plan.load(tmp_path, listed)
    assert record.table is None  # a symlink
    for table in (None, "# Units\n\nno table here\n"):
        built, index = units_plan(items=(), table=table)
        (found,) = mismatches(built, index)
        assert (found.path, found.line, found.stage, found.intent) == (
            "r/aidlc-state.md",
            UNITS_ROW,
            UNITS_GENERATION,
            "r",
        )
        assert "unit-of-work.md" in found.message


def test_load_reads_the_unit_table_raw(tmp_path):
    put(tmp_path, {"r/aidlc-state.md": UNIT_STATE, TABLE_PATH: "\ufeff" + TABLE})
    (record,) = plan.load(tmp_path, ["r/aidlc-state.md", TABLE_PATH])
    assert record.table == TABLE


def test_unit_item_without_row_is_flagged_with_or_without_a_table():
    for table in (TABLE, None):
        built, index = units_plan(items=(unit("a"), unit("b", 11), unit("c", 12)), table=table)
        flagged = [(found.path, found.line, found.subject) for found in mismatches(built, index)]
        assert (TABLE_PATH, 12, "unit~c~1") in flagged
        assert all(found.stage == UNITS_GENERATION for found in mismatches(built, index))
    built, index = units_plan()
    assert mismatches(built, index) == []


def test_row_without_unit_item_is_flagged_and_expands_nothing():
    built, index = units_plan(items=(unit("a"),))
    (found,) = mismatches(built, index)
    assert (found.path, found.line, found.subject, found.stage) == (TABLE_PATH, 6, "b", UNITS_GENERATION)
    assert not any("b-dir" in stage for stage in built.intent.route)
    assert "construction/a-dir/code-generation" in built.intent.route


def test_table_is_read_only_with_units_generation_on_the_route(tmp_path):
    put(tmp_path, {"r/aidlc-state.md": FULL_STATE, TABLE_PATH: TABLE})
    (record,) = plan.load(tmp_path, ["r/aidlc-state.md", TABLE_PATH])
    assert record.table is None
    built, index = planned(BASE, items=[unit("c")], table=None)  # no units route: no table needed, no unit flagged
    assert mismatches(built, index) == []


# Upstream's `for_each: unit-of-work` stages, written out so a slug dropped from `plan.FOR_EACH` fails here.
PER_UNIT_SLUGS = ("functional-design", "nfr-requirements", "nfr-design", "infrastructure-design", "code-generation")


@pytest.mark.parametrize("slug", PER_UNIT_SLUGS)
def test_each_for_each_slug_expands_once_per_unit(slug):
    row = f"- [ ] {slug} {DASH} EXECUTE: per unit\n"
    state = UNITS_STATE.replace("### CONSTRUCTION PHASE\n", f"### CONSTRUCTION PHASE\n{row}")
    if slug == "code-generation":
        state = UNITS_STATE
    built, _ = units_plan(state=state)
    per_unit = [stage for stage in built.intent.route if stage.endswith(f"/{slug}")]
    assert per_unit == [f"construction/a-dir/{slug}", f"construction/b-dir/{slug}"]
    assert [built.owners[stage] for stage in per_unit] == ["a", "b"]


def test_shared_slugs_stay_single():
    built, _ = units_plan()
    assert built.intent.route == (
        REQUIREMENTS,
        UNITS_GENERATION,
        "construction/a-dir/functional-design",
        "construction/b-dir/functional-design",
        "construction/a-dir/code-generation",
        "construction/b-dir/code-generation",
        BUILD_AND_TEST,
    )
    assert not {REQUIREMENTS, UNITS_GENERATION, BUILD_AND_TEST} & set(built.owners)


def order(items, links):
    return [(each.name, each.resolved) for each in plan.unit_order("r", Index(tuple(items), tuple(links), ()))]


def test_unit_order_is_dependency_order_with_ties_by_code_point():
    items = [unit("a"), unit("b"), unit("c")]
    assert order(items, [unit_link("Depends", "unit~a~1", "unit~c~1")]) == [("b", True), ("c", True), ("a", True)]
    assert order([unit("u2"), unit("u10")], []) == [("u10", True), ("u2", True)]


def test_unit_order_puts_a_cycle_last_by_name():
    items = [unit("a"), unit("b"), unit("x"), unit("d")]
    links = [unit_link("Depends", "unit~a~1", "unit~b~1"), unit_link("Depends", "unit~b~1", "unit~a~1")]
    links.append(unit_link("Depends", "unit~x~1", "unit~x~1"))
    assert order(items, links) == [("d", True), ("a", False), ("b", False), ("x", False)]


def test_unit_order_puts_an_unknown_dependency_last_by_name():
    other = unit("o", path="o/inception/units-generation/unit-of-work.md")
    items = [unit("a"), unit("b"), unit("c"), unit("d"), unit("e"), other, task("task~t~1")]
    links = [
        unit_link("Depends", "unit~b~1", "unit~nothing~1"),  # an id with no item
        unit_link("Depends", "unit~c~1", "task~t~1"),  # a task
        unit_link("Depends", "unit~d~1", "unit~o~1"),  # a unit of another intent
        unit_link("Depends", "unit~a~1", "unit~e~2"),  # a unit there, by type and name, whatever its revision
    ]
    assert order(items, links) == [("e", True), ("a", True), ("b", False), ("c", False), ("d", False)]


def test_unit_order_puts_units_blocked_by_an_unresolved_unit_last_by_name():
    links = [unit_link("Depends", "unit~a~1", "unit~zz~1"), unit_link("Depends", "unit~c~1", "unit~a~1")]
    assert order([unit("a"), unit("b"), unit("c")], links) == [("b", True), ("a", False), ("c", False)]


def test_expansion_follows_unit_order_and_skips_units_without_a_row():
    table = "| Unit ID | Directory |\n| --- | --- |\n| A | a-dir |\n| C | c-dir |\n"
    links = (unit_link("Depends", "unit~a~1", "unit~c~1"),)
    built, _ = units_plan(items=(unit("a"), unit("b"), unit("c")), links=links, table=table)
    assert [(each.name, each.directory) for each in built.units] == [("b", None), ("c", "c-dir"), ("a", "a-dir")]
    assert [stage for stage in built.intent.route if stage.endswith("/functional-design")] == [
        "construction/c-dir/functional-design",
        "construction/a-dir/functional-design",
    ]


def test_unitless_audited_skip_removes_a_per_unit_slug_for_every_unit():
    skip = block("2026-09-26T09:30:00Z", "STAGE_SKIPPED", Stage="functional-design", Skip_Kind="conditional-runtime")
    built, _ = units_plan(skip)
    assert not any(stage.endswith("/functional-design") for stage in built.intent.route)


def test_unit_scoped_skip_skips_nothing():
    for field_name in ("Unit", "Gate_Scope", "Gate_Stages"):
        skip = block("2026-09-26T09:30:00Z", "STAGE_SKIPPED", Stage="functional-design", **{field_name: "a"})
        built, _ = units_plan(skip)
        assert [stage for stage in built.intent.route if stage.endswith("/functional-design")] == [
            "construction/a-dir/functional-design",
            "construction/b-dir/functional-design",
        ]


def test_produces_reads_the_unexpanded_route():
    current = intent_of(START, SKIPS, state=UNIT_STATE)  # no table: the needs of every per-unit stage stay
    assert plan.produces([current]) == {"req", "unit", "dsn", "task", "impl", "utest", "itest", "stest"}


def test_in_tree_keeps_per_unit_files_without_a_table():
    current = intent_of(START, SKIPS, state=UNIT_STATE)
    assert plan.in_tree([current], "r/construction/any-dir/functional-design/spec.md")
    assert plan.in_tree([current], "r/construction/other/code-generation/code-generation-plan.md")
    assert not plan.in_tree([current], "r/construction/any-dir/build-and-test/x.md")  # a shared stage is not per unit
    assert not plan.in_tree([current], "r/construction/a/b/functional-design/x.md")  # a directory is one segment
    assert not plan.in_tree([current], "r/construction/any-dir/nfr-design/x.md")  # not on the route


def test_select_stage_takes_a_per_unit_id_and_refuses_a_unit_name():
    built, _ = units_plan()
    assert plan.select_stage(built, "construction/a-dir/code-generation") == "construction/a-dir/code-generation"
    texts = ("construction/a/code-generation", "construction/code-generation", "construction/../a-dir/code-generation")
    for text in texts:
        with pytest.raises(plan.PlanError, match="is not a stage on the route"):
            plan.select_stage(built, text)
    with pytest.raises(plan.PlanError, match=r"names several stages.*construction/a-dir/code-generation"):
        plan.select_stage(built, "code-generation")


A_FD, B_FD = "construction/a-dir/functional-design", "construction/b-dir/functional-design"
A_CG, B_CG = "construction/a-dir/code-generation", "construction/b-dir/code-generation"
LANES = {"a": frozenset({"functional-design", "code-generation"}), "b": frozenset({"functional-design"})}


def unit_item(text, stage, line=3):
    return Item(ident(text), f"r/{stage}/doc.md", line)


UNIT_ITEMS = (*UNITS_AB, unit_item("dsn~a~1", A_FD), unit_item("dsn~b~1", B_FD), unit_item("task~a~1", A_CG))


def unit_gate(minute, slug, event="GATE_APPROVED", **fields):
    return block(f"2026-09-26T10:{minute:02d}:00Z", event, Stage=slug, **fields)


def approvals_of(*blocks, items=UNIT_ITEMS):
    built, _ = units_plan(*blocks, items=items)
    return {state.stage: state.state for state in built.stages if state.stage in {A_FD, B_FD, A_CG, B_CG}}, built


def keys(stage="functional-design", **fields):
    (event,) = events_of(gate("2026-09-26T10:00:00Z", stage=stage, **fields))
    return plan._gate_keys(event, LANES)


def test_gate_keys_per_stage_unit_end_merge_and_unknown():
    assert keys(Unit="a") == {("a", "functional-design")}
    assert keys(Unit="a", Gate_Scope="per-stage", Gate_Stages="functional-design") == {("a", "functional-design")}
    assert keys(Unit="a", Gate_Scope="per-stage", Gate_Stages="code-generation") == set()
    assert keys(Unit="a", Gate_Scope="per-stage", Gate_Stages="functional-design,code-generation") == set()
    listed = keys("code-generation", Unit="a", Gate_Scope="unit-end", Gate_Stages="functional-design,code-generation")
    assert listed == {("a", "functional-design"), ("a", "code-generation")}
    assert keys(Unit="a", Gate_Scope="unit-end", Gate_Stages="code-generation") == set()  # it must list its Stage
    assert (
        keys(Unit="b", Gate_Scope="unit-end", Gate_Stages="functional-design,code-generation") == set()
    )  # off b's lane
    for scope in ("unit-merge", "team"):
        assert keys(Unit="a", Gate_Scope=scope, Gate_Stages="functional-design") == set()
    for unknown in ("z", "A", "a-dir"):
        assert keys(Unit=unknown) == set()
    assert keys() == set()
    assert keys("requirements-analysis", Unit="a") == set()  # not a per-unit stage


def test_gate_stages_split_like_items():
    for text in (
        "functional-design,code-generation",
        "functional-design code-generation",
        " ,functional-design, code-generation,",
    ):
        assert keys("code-generation", Unit="a", Gate_Scope="unit-end", Gate_Stages=text) == {
            ("a", "functional-design"),
            ("a", "code-generation"),
        }


def test_unit_end_needs_every_listed_stage_on_the_units_lane_and_is_current_on_the_union():
    fields = {"Unit": "a", "Gate_Scope": "unit-end", "Approved_By": "human"}
    union = unit_gate(
        30, "code-generation", Gate_Stages="functional-design,code-generation", Items="dsn~a~1, task~a~1", **fields
    )
    states, built = approvals_of(union)
    assert (states[A_FD], states[A_CG], states[B_FD]) == ("current", "current", "none")
    assert next(state for state in built.stages if state.stage == A_FD).approval.by == "human"
    part = unit_gate(30, "code-generation", Gate_Stages="functional-design,code-generation", Items="task~a~1", **fields)
    states, _ = approvals_of(part)
    assert (states[A_FD], states[A_CG]) == ("outdated", "outdated")
    off_lane = unit_gate(30, "code-generation", Gate_Stages="nfr-design,code-generation", Items="task~a~1", **fields)
    assert approvals_of(off_lane)[0][A_CG] == "none"


def test_partial_unit_end_rejection_keeps_surviving_stage_unbumped_change_and_baseline():
    original_fd = hashed("dsn~a~1", digest_of(b"Original functional design."), A_FD, line=3)
    original_cg = hashed("task~a~1", digest_of(b"Original code generation plan."), A_CG, line=3)
    original_items = (*UNITS_AB, original_fd, original_cg)
    unchecked, _ = units_plan(items=original_items)
    held = plan.next_bodies({}, unchecked, A_FD)
    held = plan.next_bodies(held, unchecked, A_CG)
    assert held == {"dsn~a~1": original_fd.body_hash, "task~a~1": original_cg.body_hash}
    approved = unit_gate(
        10,
        "code-generation",
        Unit="a",
        Gate_Scope="unit-end",
        Gate_Stages="functional-design,code-generation",
        Attempt_Generation="1",
        Items="dsn~a~1, task~a~1",
        Approved_By="human",
        Assessment_Hash=HASH,
    )
    rejected = unit_gate(
        20,
        "code-generation",
        "GATE_REJECTED",
        Unit="a",
        Gate_Scope="per-stage",
        Gate_Stages="code-generation",
        Attempt_Generation="1",
        Feedback="Rework only the code generation plan.",
    )
    approval_event, rejection_event = events_of(approved, rejected)
    assert approval_event.name == "GATE_APPROVED"
    assert approval_event.fields == {
        "Timestamp": "2026-09-26T10:10:00Z",
        "Event": "GATE_APPROVED",
        "Stage": "code-generation",
        "Unit": "a",
        "Gate Scope": "unit-end",
        "Gate Stages": "functional-design,code-generation",
        "Attempt Generation": "1",
        "Items": "dsn~a~1, task~a~1",
        "Approved By": "human",
        "Assessment Hash": HASH,
    }
    assert rejection_event.name == "GATE_REJECTED"
    assert rejection_event.fields == {
        "Timestamp": "2026-09-26T10:20:00Z",
        "Event": "GATE_REJECTED",
        "Stage": "code-generation",
        "Unit": "a",
        "Gate Scope": "per-stage",
        "Gate Stages": "code-generation",
        "Attempt Generation": "1",
        "Feedback": "Rework only the code generation plan.",
    }
    assert approval_event.key < rejection_event.key
    states, before_rejection = approvals_of(approved, items=original_items)
    assert (states[A_FD], states[A_CG]) == ("current", "current")
    assert plan.frozen_bodies(held, [before_rejection.intent]) == held
    changed_fd = hashed("dsn~a~1", digest_of(b"Edited functional design without a revision bump."), A_FD, line=3)
    assert changed_fd.id == original_fd.id
    assert changed_fd.body_hash != original_fd.body_hash
    built, index = units_plan(approved, rejected, items=(*UNITS_AB, changed_fd, original_cg))
    stages = {stage.stage: stage for stage in built.stages}
    assert (stages[A_FD].state, stages[A_CG].state) == ("current", "none")
    surviving = stages[A_FD].approval
    assert surviving is not None
    assert surviving.items == ("dsn~a~1", "task~a~1")
    assert surviving.scope == (A_CG, A_FD)
    frozen = plan.frozen_bodies(held, [built.intent])
    findings = structural.check(index, produces=plan.produces([built.intent]), frozen=frozen)
    assert [(f.rule, f.subject, f.path, f.line, f.level) for f in findings if f.rule == "earnest/unbumped-change"] == [
        ("earnest/unbumped-change", "dsn~a~1", f"r/{A_FD}/doc.md", 3, "error")
    ]
    assert frozen == held  # Fail closed: a surviving FD key retains even CG-only listed items.
    assert {"dsn~a~1", "task~a~1"} <= built.intent.named_items
    assert plan.next_bodies(held, built, A_FD) == held  # The surviving approval must not let a check overwrite FD.


def test_partial_unit_end_rejection_keeps_relocated_item_unbumped_change_and_baseline():
    original_fd = hashed("dsn~a~1", digest_of(b"Original functional design."), A_FD, line=3)
    original_cg = hashed("task~a~1", digest_of(b"Original code generation plan."), A_CG, line=7)
    unchecked, _ = units_plan(items=(*UNITS_AB, original_fd, original_cg))
    held = plan.next_bodies(plan.next_bodies({}, unchecked, A_FD), unchecked, A_CG)
    assert held == {"dsn~a~1": original_fd.body_hash, "task~a~1": original_cg.body_hash}
    approved = unit_gate(
        10,
        "code-generation",
        Unit="a",
        Gate_Scope="unit-end",
        Gate_Stages="functional-design,code-generation",
        Attempt_Generation="1",
        Items="dsn~a~1, task~a~1",
        Approved_By="human",
        Assessment_Hash=HASH,
    )
    rejected = unit_gate(
        20,
        "code-generation",
        "GATE_REJECTED",
        Unit="a",
        Gate_Scope="per-stage",
        Gate_Stages="code-generation",
        Attempt_Generation="1",
    )
    approval_event, rejection_event = events_of(approved, rejected)
    assert approval_event.fields["Gate Scope"] == "unit-end"
    assert approval_event.fields["Gate Stages"] == "functional-design,code-generation"
    assert approval_event.fields["Items"] == "dsn~a~1, task~a~1"
    assert rejection_event.name == "GATE_REJECTED"
    assert rejection_event.fields["Gate Scope"] == "per-stage"
    assert rejection_event.fields["Gate Stages"] == "code-generation"
    assert approval_event.fields["Attempt Generation"] == rejection_event.fields["Attempt Generation"] == "1"
    assert approval_event.key < rejection_event.key
    moved_fd = hashed("dsn~a~1", original_fd.body_hash, A_CG, line=3)
    assert moved_fd.id == original_fd.id
    assert moved_fd.path != original_fd.path
    moved, _ = units_plan(approved, rejected, items=(*UNITS_AB, moved_fd, original_cg))
    assert next(stage for stage in moved.stages if stage.stage == A_FD).state == "current"
    changed_fd = hashed("dsn~a~1", digest_of(b"Relocated and edited without a revision bump."), A_CG, line=3)
    assert changed_fd.id == moved_fd.id
    assert changed_fd.path == moved_fd.path
    assert changed_fd.body_hash != moved_fd.body_hash
    built, index = units_plan(approved, rejected, items=(*UNITS_AB, changed_fd, original_cg))
    stages = {stage.stage: stage for stage in built.stages}
    assert (stages[A_FD].state, stages[A_CG].state) == ("current", "none")
    surviving = stages[A_FD].approval
    assert surviving is not None
    assert surviving.items == ("dsn~a~1", "task~a~1")
    assert surviving.scope == (A_CG, A_FD)
    assert not stages[A_FD].items
    frozen = plan.frozen_bodies(held, [built.intent])
    findings = structural.check(index, produces=plan.produces([built.intent]), frozen=frozen)
    assert [(f.rule, f.subject, f.path, f.line, f.level) for f in findings if f.rule == "earnest/unbumped-change"] == [
        ("earnest/unbumped-change", "dsn~a~1", f"r/{A_CG}/doc.md", 3, "error")
    ]
    assert frozen == held
    assert plan.next_bodies(held, built, A_CG) == held  # Checking the new location cannot overwrite the baseline.


@pytest.mark.parametrize(
    ("rejected_slug", "scope", "unit_name", "expected"),
    [
        (None, None, None, {"dsn~a~1", "task~a~1", "dsn~b~1"}),
        ("code-generation", "per-stage", "a", {"dsn~a~1", "task~a~1", "dsn~b~1"}),
        ("functional-design", "per-stage", "a", {"dsn~a~1", "task~a~1", "dsn~b~1"}),
        ("code-generation", "unit-end", "a", {"dsn~b~1"}),
        ("code-generation", "per-stage", "b", {"dsn~a~1", "task~a~1", "dsn~b~1"}),
    ],
)
def test_unit_end_frozen_items_follow_surviving_keys_without_affecting_other_units(
    rejected_slug, scope, unit_name, expected
):
    rows = [
        unit_gate(
            10,
            "code-generation",
            Unit="a",
            Gate_Scope="unit-end",
            Gate_Stages="functional-design,code-generation",
            Items="dsn~a~1, task~a~1",
        ),
        unit_gate(11, "functional-design", Unit="b", Items="dsn~b~1"),
    ]
    if rejected_slug:
        listed = "functional-design,code-generation" if scope == "unit-end" else rejected_slug
        rows.append(unit_gate(20, rejected_slug, "GATE_REJECTED", Unit=unit_name, Gate_Scope=scope, Gate_Stages=listed))
    states, built = approvals_of(*rows)
    assert built.intent.named_items == expected
    assert states[B_FD] == "current"
    held = {text: digest_of(text.encode()) for text in ("dsn~a~1", "task~a~1", "dsn~b~1")}
    assert plan.frozen_bodies(held, [built.intent]) == {text: held[text] for text in expected}


def test_partial_unit_end_rejection_preserves_all_edited_items_while_code_generation_survives():
    original_fd = hashed("dsn~a~1", digest_of(b"Original design."), A_FD)
    original_cg = hashed("task~a~1", digest_of(b"Original plan."), A_CG)
    unchecked, _ = units_plan(items=(*UNITS_AB, original_fd, original_cg))
    held = plan.next_bodies(plan.next_bodies({}, unchecked, A_FD), unchecked, A_CG)
    changed_fd = hashed("dsn~a~1", digest_of(b"Reworked design."), A_FD)
    changed_cg = hashed("task~a~1", digest_of(b"Unbumped plan."), A_CG)
    rows = [
        unit_gate(
            10,
            "code-generation",
            Unit="a",
            Gate_Scope="unit-end",
            Gate_Stages="functional-design,code-generation",
            Items="dsn~a~1, task~a~1",
        ),
        unit_gate(20, "functional-design", "GATE_REJECTED", Unit="a"),
    ]
    built, index = units_plan(*rows, items=(*UNITS_AB, changed_fd, changed_cg))
    states = {stage.stage: stage.state for stage in built.stages}
    assert (states[A_FD], states[A_CG]) == ("none", "current")
    frozen = plan.frozen_bodies(held, [built.intent])
    assert frozen == held
    findings = structural.check(index, produces=plan.produces([built.intent]), frozen=frozen)
    assert [f.subject for f in findings if f.rule == "earnest/unbumped-change"] == ["dsn~a~1", "task~a~1"]
    assert plan.next_bodies(held, built, A_CG) == held
    assert plan.next_bodies(held, built, A_FD) == held


@pytest.mark.parametrize("reverse_definitions", [False, True])
def test_partial_unit_end_freezes_all_listed_items_regardless_of_definitions_or_references(reverse_definitions):
    shared = [unit_item("dsn~shared~1", A_CG), unit_item("dsn~shared~1", A_FD)]
    if reverse_definitions:
        shared.reverse()
    items = (*UNIT_ITEMS, *shared)
    reference = Link("Delivers", "dsn", ident("task~a~1"), f"r/{A_FD}/doc.md", 7, owner=ident("dsn~a~1"))
    approved = unit_gate(
        10,
        "code-generation",
        Unit="a",
        Gate_Scope="unit-end",
        Gate_Stages="functional-design,code-generation",
        Items="dsn~a~1, dsn~shared~1, task~a~1",
    )
    rejected = unit_gate(20, "code-generation", "GATE_REJECTED", Unit="a")
    built, _ = units_plan(approved, rejected, items=items, links=(reference,))
    assert built.intent.named_items == {"dsn~a~1", "dsn~shared~1", "task~a~1"}
    # Once every original key is voided, only a separate later approval freezes its own Items.
    all_rejected = unit_gate(
        25,
        "code-generation",
        "GATE_REJECTED",
        Unit="a",
        Gate_Scope="unit-end",
        Gate_Stages="functional-design,code-generation",
    )
    independent = unit_gate(30, "functional-design", Unit="a", Items="task~a~1")
    built, _ = units_plan(approved, rejected, all_rejected, independent, items=items, links=(reference,))
    assert built.intent.named_items == {"task~a~1"}


@pytest.mark.parametrize("scope", ["per-stage", "unit-end"])
def test_partial_unit_end_unattributable_items_are_retained_only_while_a_key_survives(scope):
    # This definition is not inside functional-design/; the missing id has no current definition at all.
    boundary = unit_item("dsn~boundary~1", A_FD + "-extra")
    approved = unit_gate(
        10,
        "code-generation",
        Unit="a",
        Gate_Scope="unit-end",
        Gate_Stages="functional-design,code-generation",
        Items="dsn~a~1, task~a~1, dsn~missing~7, dsn~boundary~1",
    )
    listed = "functional-design" if scope == "per-stage" else "functional-design,code-generation"
    rejected = unit_gate(20, "functional-design", "GATE_REJECTED", Unit="a", Gate_Scope=scope, Gate_Stages=listed)
    built, _ = units_plan(approved, items=(*UNIT_ITEMS, boundary))
    assert built.intent.named_items == {"dsn~a~1", "task~a~1", "dsn~missing~7", "dsn~boundary~1"}
    built, _ = units_plan(approved, rejected, items=(*UNIT_ITEMS, boundary))
    expected = {"dsn~a~1", "task~a~1", "dsn~missing~7", "dsn~boundary~1"} if scope == "per-stage" else set()
    assert built.intent.named_items == expected


def test_partial_unit_end_freezes_only_listed_revisions_without_freezing_new_revisions():
    changed_fd = hashed("dsn~a~2", digest_of(b"New revision design."), A_FD)
    changed_cg = hashed("task~a~2", digest_of(b"New revision plan."), A_CG)
    approved = unit_gate(
        10,
        "code-generation",
        Unit="a",
        Gate_Scope="unit-end",
        Gate_Stages="functional-design,code-generation",
        Items="dsn~a~1, task~a~1",
    )
    rejected = unit_gate(20, "code-generation", "GATE_REJECTED", Unit="a")
    built, index = units_plan(approved, rejected, items=(*UNITS_AB, changed_fd, changed_cg))
    assert built.intent.named_items == {"dsn~a~1", "task~a~1"}  # Listed revisions only, regardless of location.
    held = {"dsn~a~1": digest_of(b"Old design."), "task~a~1": digest_of(b"Old plan.")}
    frozen = plan.frozen_bodies(held, [built.intent])
    assert frozen == held
    assert not [f for f in structural.check(index, frozen=frozen) if f.rule == "earnest/unbumped-change"]
    assert plan.next_bodies(held, built, A_FD) == {**held, "dsn~a~2": changed_fd.body_hash}


@pytest.mark.parametrize("generation", ["1", "2", "x2", "1234567890"])
def test_partial_unit_end_frozen_items_preserve_generation_rules(generation):
    approved = unit_gate(
        10,
        "code-generation",
        Unit="a",
        Gate_Scope="unit-end",
        Gate_Stages="functional-design,code-generation",
        Attempt_Generation="1",
        Items="dsn~a~1, task~a~1",
    )
    rejected = unit_gate(20, "code-generation", "GATE_REJECTED", Unit="a", Attempt_Generation=generation)
    states, built = approvals_of(approved, rejected)
    assert states[A_CG] == "none"  # Invalid generations never discount a rejection.
    assert states[A_FD] == ("none" if generation == "2" else "current")
    assert built.intent.named_items == (set() if generation == "2" else {"dsn~a~1", "task~a~1"})


@pytest.mark.parametrize(
    "reset",
    [
        block("2026-09-26T11:00:00Z", "WORKFLOW_STARTED", Scope="classic"),
        jump("2026-09-26T11:00:00Z", "BACKWARD", "code-generation"),
    ],
)
def test_unit_end_frozen_items_preserve_restart_and_jump_rules(reset):
    approved = unit_gate(
        10,
        "code-generation",
        Unit="a",
        Gate_Scope="unit-end",
        Gate_Stages="functional-design,code-generation",
        Items="dsn~a~1, task~a~1",
    )
    states, built = approvals_of(approved, reset)
    assert (states[A_FD], states[A_CG]) == ("none", "none")
    assert built.intent.named_items == set()


def test_generation_is_the_highest_counting_row_per_unit_of_any_scope():
    rows = [
        unit_gate(10, "functional-design", Unit="a", Attempt_Generation="2", Items="dsn~a~1"),
        unit_gate(
            20,
            "code-generation",
            Unit="a",
            Gate_Scope="unit-end",
            Gate_Stages="code-generation",
            Attempt_Generation="3",
            Items="task~a~1",
        ),
        unit_gate(25, "functional-design", Unit="a", Gate_Scope="unit-merge", Attempt_Generation="9"),  # not counting
        unit_gate(30, "functional-design", Unit="b", Attempt_Generation="1", Items="dsn~b~1"),
    ]
    states, _ = approvals_of(*rows)
    assert (states[A_FD], states[A_CG], states[B_FD]) == ("none", "current", "current")


def test_missing_generation_is_zero_and_invalid_approves_nothing_and_raises_no_maximum():
    states, _ = approvals_of(unit_gate(10, "functional-design", Unit="a", Items="dsn~a~1"))
    assert states[A_FD] == "current"
    for invalid in ("x2", "1234567890", "-1", "1.0"):
        rows = (
            unit_gate(10, "functional-design", Unit="a", Items="dsn~a~1"),
            unit_gate(20, "code-generation", Unit="a", Attempt_Generation=invalid, Items="task~a~1"),
        )
        states, _ = approvals_of(*rows)
        assert (states[A_FD], states[A_CG]) == ("current", "none"), invalid


def test_generation_two_on_another_stage_voids_generation_one():
    rows = (
        unit_gate(10, "functional-design", Unit="a", Attempt_Generation="1", Items="dsn~a~1"),
        unit_gate(20, "code-generation", Unit="a", Attempt_Generation="2", Items="task~a~1"),
    )
    states, _ = approvals_of(*rows)
    assert (states[A_FD], states[A_CG]) == ("none", "current")


def test_rejection_voids_its_key_else_its_slug_for_its_unit_or_every_unit():
    approved = (
        unit_gate(10, "functional-design", Unit="a", Attempt_Generation="1", Items="dsn~a~1"),
        unit_gate(11, "functional-design", Unit="b", Items="dsn~b~1"),
    )
    cases = {
        (("Unit", "a"), ("Gate_Scope", "per-stage")): ("none", "current"),
        (("Unit", "a"), ("Gate_Scope", "unit-merge")): ("none", "current"),  # it would approve nothing: a's Stage
        (): ("none", "none"),  # no Unit: every unit
        (("Unit", "zz"),): ("none", "none"),  # a Unit that names no unit: every unit
    }
    for fields, expected in cases.items():
        rejected = unit_gate(30, "functional-design", "GATE_REJECTED", Feedback="Rework.", **dict(fields))
        states, _ = approvals_of(*approved, rejected)
        assert (states[A_FD], states[B_FD]) == expected, fields
    before = unit_gate(5, "functional-design", "GATE_REJECTED", Unit="a")
    assert approvals_of(before, *approved)[0][A_FD] == "current"  # a rejection before the approval is history


def test_restart_and_jump_void_per_unit_rows_for_every_unit():
    approved = (
        unit_gate(10, "functional-design", Unit="a", Items="dsn~a~1"),
        unit_gate(11, "functional-design", Unit="b", Items="dsn~b~1"),
    )
    restart = block("2026-09-26T11:00:00Z", "WORKFLOW_STARTED", Scope="classic")
    states, _ = approvals_of(*approved, restart)
    assert (states[A_FD], states[B_FD]) == ("none", "none")
    back = jump("2026-09-26T11:00:00Z", "BACKWARD", "functional-design")
    states, _ = approvals_of(*approved, back)
    assert (states[A_FD], states[B_FD]) == ("none", "none")


def test_named_items_follow_counting_per_unit_approvals():
    rows = (
        unit_gate(10, "functional-design", Unit="a", Items="dsn~a~1"),
        unit_gate(11, "functional-design", Unit="b", Items="dsn~b~1"),
        unit_gate(12, "functional-design", "GATE_REJECTED", Unit="b"),
        unit_gate(13, "code-generation", Unit="a", Attempt_Generation="x", Items="task~a~1"),  # approves nothing
        unit_gate(14, "functional-design", Items="dsn~loose~1"),  # no Unit on a per-unit stage: approves nothing
    )
    _, built = approvals_of(*rows)
    assert {"dsn~a~1"} <= built.intent.named_items
    assert not {"dsn~b~1", "task~a~1", "dsn~loose~1"} & built.intent.named_items


SHARED = (unit_gate(1, "requirements-analysis"), unit_gate(2, "units-generation"))  # no Items: current, never stale


def at(stage, rule="earnest/duplicate", subject="req~a~1", line=1, **fields):
    return Finding(f"r/{stage}/x.md", line, rule, subject, "m", **fields)


def placed(built, index, *findings):
    return [(found.stage, found.position) for found in plan.place([built], index, list(findings))]


def test_each_unit_has_its_own_frontier():
    built, _ = units_plan(*SHARED, unit_gate(10, "functional-design", Unit="a"))
    assert [(each.name, each.frontier) for each in built.units] == [("a", A_CG), ("b", B_FD)]
    assert built.frontier == B_FD
    done = [
        unit_gate(minute, slug, Unit=name)
        for minute, (slug, name) in enumerate(
            [
                ("functional-design", "a"),
                ("functional-design", "b"),
                ("code-generation", "a"),
                ("code-generation", "b"),
            ],
            10,
        )
    ]
    every, _ = units_plan(*SHARED, *done)
    assert [(each.name, each.frontier) for each in every.units] == [("a", BUILD_AND_TEST), ("b", BUILD_AND_TEST)]


def test_a_units_error_is_not_ahead_because_another_units_frontier_is_earlier():
    built, index = units_plan(*SHARED, unit_gate(10, "functional-design", Unit="a"))
    assert built.intent.route.index(B_FD) < built.intent.route.index(A_CG)  # b's frontier sits earlier on the route
    assert placed(built, index, at(A_CG), at(B_CG), at(A_FD), at(B_FD)) == [
        (A_CG, "current"),
        (B_CG, "ahead"),
        (A_FD, "behind"),
        (B_FD, "current"),
    ]


def test_shared_stage_after_units_is_ahead_until_every_unit_is_approved():
    three = [unit_gate(10, "functional-design", Unit="a"), unit_gate(11, "functional-design", Unit="b")]
    three.append(unit_gate(12, "code-generation", Unit="a"))
    built, index = units_plan(*SHARED, *three)
    assert placed(built, index, at(BUILD_AND_TEST), at(UNITS_GENERATION)) == [
        (BUILD_AND_TEST, "ahead"),
        (UNITS_GENERATION, "behind"),
    ]
    every, index = units_plan(*SHARED, *three, unit_gate(13, "code-generation", Unit="b"))
    assert placed(every, index, at(BUILD_AND_TEST)) == [(BUILD_AND_TEST, "current")]


# Units a (no row), b and c (rows), so the lowest name owns no fallback; c delivers req~x~1, and so does a.
FALLBACK_TABLE = "| Unit ID | Directory |\n| --- | --- |\n| B | b-dir |\n| C | c-dir |\n"
FALLBACK_ITEMS = (unit("a"), unit("b", 11), unit("c", 12), item("req~x~1", line=3), item("req~y~1", line=8))
FALLBACK_LINKS = (unit_link("Delivers", "unit~c~1", "req~x~1"), unit_link("Delivers", "unit~a~1", "req~x~1"))
REVERSED = (
    (unit_link("Depends", "unit~b~1", "unit~c~1"),),  # c, then b
    (unit_link("Depends", "unit~c~1", "unit~b~1"),),  # b, then c
)


def fallback_plan(depends, extra=()):
    rows = [*SHARED, unit_gate(10, "functional-design", Unit="b"), unit_gate(11, "functional-design", Unit="c")]
    items = (*FALLBACK_ITEMS, *extra)
    return units_plan(*rows, items=items, links=(*FALLBACK_LINKS, *depends), table=FALLBACK_TABLE)


def test_gap_placement_holding_then_lowest_lexical_valid_delivering_then_lowest_lexical_valid_unit():
    held = unit_item("dsn~held~1", "construction/c-dir/functional-design")
    results = []
    for depends in REVERSED:
        built, index = fallback_plan(depends, extra=(held,))
        gaps = [
            Finding(held.path, 3, "earnest/gap", "dsn~held~1", "m", child="impl"),  # held by c's stage
            Finding(f"r/{REQUIREMENTS}/doc.md", 3, "earnest/gap", "req~x~1", "m", child="impl"),  # c delivers it
            Finding(f"r/{REQUIREMENTS}/doc.md", 8, "earnest/gap", "req~y~1", "m", child="utest"),  # nobody does
            Finding(f"r/{REQUIREMENTS}/doc.md", 8, "earnest/gap", "req~y~1", "m", child="dsn"),
        ]
        results.append(placed(built, index, *gaps))
    assert (
        results[0]
        == results[1]
        == [
            ("construction/c-dir/code-generation", "current"),
            ("construction/c-dir/code-generation", "current"),
            ("construction/b-dir/code-generation", "current"),
            ("construction/b-dir/functional-design", "behind"),
        ]
    )


def test_needs_with_no_unit_count_against_units_generation():
    for table in (None, "| Unit ID | Directory |\n| --- | --- |\n| A | .. |\n"):
        built, index = units_plan(*SHARED, items=(unit("a"), item("req~x~1", line=3)), table=table)
        gap = Finding(f"r/{REQUIREMENTS}/doc.md", 3, "earnest/gap", "req~x~1", "m", child="impl")
        assert placed(built, index, gap) == [(UNITS_GENERATION, "behind")]  # its approval names no Items
        (unplanned,) = [found for found in plan.plan_findings(built, index) if found.rule == "earnest/unplanned"]
        assert unplanned.stage == UNITS_GENERATION


def test_unplanned_lowest_lexical_valid_delivering_unit_then_lowest_lexical_valid_unit_code_generation():
    results = []
    for depends in REVERSED:
        built, index = fallback_plan(depends)
        found = sorted(f for f in plan.plan_findings(built, index) if f.rule == "earnest/unplanned")
        results.append([(f.subject, f.stage) for f in found])
    assert (
        results[0]
        == results[1]
        == [
            ("req~x~1", "construction/c-dir/code-generation"),
            ("req~y~1", "construction/b-dir/code-generation"),
        ]
    )
    route = UNIT_STATE.replace(f"- [x] code-generation {DASH} EXECUTE: always\n", "")
    built, index = units_plan(items=FALLBACK_ITEMS, table=FALLBACK_TABLE, state=route)
    assert [f for f in plan.plan_findings(built, index) if f.rule == "earnest/unplanned"] == []


def done_of(items, links=(), levels=None, table=TABLE):
    built, index = units_plan(*SHARED, items=items, links=links, table=table)
    return plan.unit_done(built, index, levels or {})


@pytest.mark.parametrize("plan_present", [False, True], ids=["missing-plan", "task-empty-plan"])
def test_unit_done_ignores_doc_tasks_when_canonical_plan_has_no_tasks(tmp_path, plan_present):
    canonical = f"r/{A_CG}/code-generation-plan.md"
    files = {
        "r/aidlc-state.md": UNIT_STATE,
        TABLE_PATH: TABLE + "\n`unit~a~1`\n\nDo the work.\n",
        f"r/{A_CG}/doc.md": "# Notes\n\n`task~a~1`\n\nA completed task with no deliveries.\n",
    }
    if plan_present:
        files[canonical] = "# Code generation plan\n\nNo tasks have been planned.\n"
    put(tmp_path, files)
    assert (tmp_path / canonical).is_file() is plan_present
    sources = adapters.scan(tmp_path, sorted(files))
    assert (canonical in {source.path for source in sources}) is plan_present
    index = build_index(sources)
    (record,) = plan.load(tmp_path, sorted(files))
    built = plan.build(plan.intent(record), index)
    (task_item,) = [item for item in index.items if item.id.type == "task"]
    assert task_item.path == f"r/{A_CG}/doc.md"
    assert plan.task_done(task_item, index, {}) is True
    assert plan.unit_done(built, index, {}) == {"a": False}


def test_unit_done_needs_a_row_dependencies_a_task_and_every_task_done():
    items = (
        *UNITS_AB,
        unit("c", 12),
        Item(ident("task~a~1"), f"r/{A_CG}/code-generation-plan.md", 3),  # no deliveries, so done
    )
    assert done_of(items) == {"a": True, "b": False, "c": False}  # b has no task, c no row
    assert done_of(items, links=(unit_link("Depends", "unit~a~1", "unit~b~1"),))["a"] is False  # b is not done
    delivering = (
        Link("Delivers", "task", ident("req~r~1"), f"r/{A_CG}/code-generation-plan.md", 7, owner=ident("task~a~1")),
    )
    with_req = (*items, item("req~r~1"))
    assert done_of(with_req, links=delivering, levels={"req~r~1": "traced"})["a"] is False
    assert done_of(with_req, links=delivering, levels={"req~r~1": "evidenced"})["a"] is True


def test_unresolved_unit_is_not_done():
    table = "| Unit ID | Directory |\n| --- | --- |\n| A | a-dir |\n| B | b-dir |\n"
    items = (
        *UNITS_AB,
        Item(ident("task~a~1"), f"r/{A_CG}/code-generation-plan.md", 3),
        Item(ident("task~b~1"), f"r/{B_CG}/code-generation-plan.md", 3),
    )
    assert done_of(items, table=table) == {"a": True, "b": True}
    cycle = (unit_link("Depends", "unit~a~1", "unit~b~1"), unit_link("Depends", "unit~b~1", "unit~a~1"))
    assert done_of(items, links=cycle, table=table) == {"a": False, "b": False}
    unknown = (unit_link("Depends", "unit~a~1", "unit~zz~1"),)
    assert done_of(items, links=unknown, table=table) == {"a": False, "b": True}
    blocked = (*unknown, unit_link("Depends", "unit~b~1", "unit~a~1"))
    assert done_of(items, links=blocked, table=table) == {"a": False, "b": False}


def test_properties_list_units_in_unit_order_and_tasks_by_id():
    items = (
        *UNITS_AB,
        Item(ident("task~z~1"), f"r/{A_CG}/code-generation-plan.md", 3),
        Item(ident("task~b~1"), f"r/{B_CG}/code-generation-plan.md", 3),
    )
    links = (unit_link("Depends", "unit~a~1", "unit~b~1"),)  # b, then a
    built, index = units_plan(*SHARED, unit_gate(10, "functional-design", Unit="b"), items=items, links=links)
    statuses = {"r": plan.statuses(built, index, [], {})}
    (entry,) = plan.properties([built], statuses, index, {})["intents"]
    assert entry["units"] == [
        {"id": "unit~b~1", "status": "done", "directory": "b-dir", "frontier": B_CG},
        {"id": "unit~a~1", "status": "done", "directory": "a-dir", "frontier": A_FD},
    ]
    assert [task["id"] for task in entry["tasks"]] == ["task~b~1", "task~z~1"]
    lonely, index = units_plan(*SHARED, items=(unit("a"),), table=None)
    statuses = {"r": plan.statuses(lonely, index, [], {})}
    (entry,) = plan.properties([lonely], statuses, index, {})["intents"]
    assert entry["units"] == [{"id": "unit~a~1", "status": "not done", "directory": None, "frontier": BUILD_AND_TEST}]


# The Out-of-task rule (M3).

ADD_LIMITER = "task~add-limiter~1"


def seeded(repo):
    """Return the plans and the index of a seeded-change work tree, as `earnest check` builds them."""
    files = git.work_tree_files(repo)
    index = build_index(adapters.scan(repo, files))
    intents = [plan.intent(record) for record in plan.load(repo, files)]
    return [plan.build(current, index) for current in intents], index, intents


def task_item(name, path="plan.md"):
    return Item(Id("task", name, 1), path, 1)


def test_the_state_file_s_current_task_lines_are_read_in_project_information_only():
    text = (
        "## Project Information\n- **Scope**: feature\n- **Current Task**:  task~a~1 \n\n"
        "## Stage Progress\n- **Current Task**: task~b~1\n"
    )
    assert plan.parse_state(text).current == ("task~a~1",)
    assert plan.parse_state("- **Current Task**: task~a~1\n").current == ()


def intents_marking(*marks, directory="r"):
    """Return one intent per entry of marks, in r, r2, …, whose state file holds those Current Task lines."""
    found = []
    for number, lines in enumerate(marks):
        name = directory if number == 0 else f"{directory}{number + 1}"
        text = "## Project Information\n" + "".join(f"- **Current Task**: {line}\n" for line in lines)
        found.append(plan.intent(Record(name, f"{name}/aidlc-state.md", plan.parse_state(text), ())))
    return found


TASKS = [task_item("add-limiter", "r/plan.md"), task_item("notify-lockout", "r/plan.md"), task_item("x", "r2/plan.md")]


def test_the_one_current_task_line_names_a_task_of_its_intent_on_type_and_name():
    found, reason = plan.current_task(TASKS, intents_marking(["task~notify-lockout~7"]), None)
    assert (found.id.name, reason) == ("notify-lockout", None)


def test_task_option_wins_over_the_state_file_and_ignores_the_revision():
    found, _ = plan.current_task(TASKS, intents_marking(["task~add-limiter~1"]), "task~notify-lockout~3")
    assert found.id.name == "notify-lockout"


@pytest.mark.parametrize(
    ("marks", "reason"),
    [
        (([],), "no state file names one"),
        ((["task~add-limiter~1", "task~notify-lockout~1"],), "several Current Task lines name one"),
        ((["task~add-limiter~1"], ["task~x~1"]), "several Current Task lines name one"),
        ((["task~x~1"],), "`task~x~1` names no task of its intent"),
        ((["add-limiter"],), "`add-limiter` names no task of its intent"),
        ((["task~add-limiter~1 task~notify-lockout~1"],), "names no task of its intent"),
    ],
)
def test_no_single_current_task_line_gives_no_current_task_and_says_why(marks, reason):
    found, said = plan.current_task(TASKS, intents_marking(*marks), None)
    assert found is None
    assert reason in said


@pytest.mark.parametrize("option", ["task~nope~1", "notify-lockout", "req~notify-lockout~1"])
def test_task_option_that_names_no_task_raises(option):
    with pytest.raises(plan.PlanError, match="names no task"):
        plan.current_task([task_item("notify-lockout")], [], option)


def test_changed_regions_are_tag_regions_that_hold_a_change_then_hunks_outside_every_tag_region():
    a, b = Id("req", "a", 1), Id("req", "b", 1)
    index = Index((), (), (), (Region(a, "x.py", 4, 8), Region(b, "x.py", 4, 8), Region(a, "x.py", 9, 12)))
    changed = {"x.py": (Hunk(1, 1, 2, 1), Hunk(5, 2, 5, 2), Hunk(13, 0, 13, 2)), "y.md": (Hunk(3, 1, 3, 1),)}
    assert plan.changed_regions(index, changed) == [
        ChangedRegion("x.py", (4, 5, 6, 7, 8), (5, 6), (a, b)),
        ChangedRegion("x.py", (2,), (2,)),
        ChangedRegion("x.py", (13, 14), (13, 14)),
        ChangedRegion("y.md", (3,), (3,)),
    ]


def test_a_hunk_that_straddles_a_tag_region_gives_a_region_of_its_lines_outside_it():
    index = Index((), (), (), (Region(Id("req", "a", 1), "x.py", 4, 8),))
    assert plan.changed_regions(index, {"x.py": (Hunk(2, 4, 2, 4),)})[1] == ChangedRegion("x.py", (2, 3), (2, 3))


def out_of_task_rows(repo, changed, task=ADD_LIMITER, findings=()):
    plans, index, intents = seeded(repo)
    current, _ = plan.current_task(plan.plan_tasks(index, intents), intents, task)
    found = plan.out_of_task(plans, index, current, changed, list(findings))
    return [(each.path, each.line, each.stage, each.position, each.level) for each in found]


CODE_GENERATION = "construction/code-generation"


def test_a_region_outside_the_task_is_flagged_at_its_first_changed_line_in_scope_at_the_tasks_stage(fixture_repo):
    repo = fixture_repo("seeded-change")
    changed = {"src/checkout/auth.py": (Hunk(2, 1, 2, 1), Hunk(6, 1, 6, 1), Hunk(11, 1, 11, 2))}
    assert out_of_task_rows(repo, changed) == [
        ("src/checkout/auth.py", 11, CODE_GENERATION, "current", "warning"),  # the region of req~lockout-notice~1
        ("src/checkout/auth.py", 2, CODE_GENERATION, "current", "warning"),  # before the first tag
    ]


def test_an_outdated_finding_on_a_regions_line_suppresses_it(fixture_repo):
    repo = fixture_repo("seeded-change")
    outdated = Finding("src/checkout/auth.py", 9, "earnest/outdated", "req~lockout-notice~1", "m")
    prose = Finding(REQUIREMENTS_FILE, 3, "earnest/outdated", "req~rate-limit~2", "m", note=True)
    changed = {"src/checkout/auth.py": (Hunk(11, 1, 11, 1),), REQUIREMENTS_FILE: (Hunk(3, 1, 3, 1), Hunk(5, 1, 5, 1))}
    assert out_of_task_rows(repo, changed, findings=[outdated, prose]) == [
        (REQUIREMENTS_FILE, 5, CODE_GENERATION, "current", "warning"),
    ]


def test_the_message_names_the_task_the_tags_and_the_exits(fixture_repo):
    plans, index, intents = seeded(fixture_repo("seeded-change"))
    task, _ = plan.current_task(plan.plan_tasks(index, intents), intents, ADD_LIMITER)
    (found,) = plan.out_of_task(plans, index, task, {"src/checkout/auth.py": (Hunk(11, 1, 11, 1),)}, [])
    assert found.subject == ADD_LIMITER
    assert "`req~lockout-notice~1`" in found.message
    assert found.text.startswith(f"in scope at {CODE_GENERATION}: ")


def test_proposing_a_task_that_delivers_the_regions_tag_clears_it_and_the_proposal_raises_none(fixture_repo):
    repo = fixture_repo("seeded-change")
    plan_text = (repo / PLAN_FILE).read_text(encoding="utf-8")
    write(repo, PLAN_FILE, plan_text + "\n`task~tell-wait~1`\n\nTell.\n\nDelivers: req~lockout-notice~1\n")
    changed = {"src/checkout/auth.py": (Hunk(2, 1, 2, 1), Hunk(11, 1, 11, 1)), PLAN_FILE: (Hunk(14, 0, 15, 6),)}
    assert out_of_task_rows(repo, changed) == [("src/checkout/auth.py", 2, CODE_GENERATION, "current", "warning")]


def test_a_plan_hunk_that_adds_no_task_is_out_of_task(fixture_repo):
    repo = fixture_repo("seeded-change")
    write(repo, PLAN_FILE, (repo / PLAN_FILE).read_text(encoding="utf-8") + "\nA note.\n")
    assert out_of_task_rows(repo, {PLAN_FILE: (Hunk(14, 0, 15, 2),)}) == [
        (PLAN_FILE, 15, CODE_GENERATION, "current", "warning"),
    ]


def test_a_tag_at_another_revision_of_a_delivered_requirement_lies_inside_the_task(fixture_repo):
    repo = fixture_repo("seeded-change")
    lines = (repo / "src/checkout/auth.py").read_text(encoding="utf-8").split("\n")
    lines[1] = "LIMIT = 5  # [impl->req~rate-limit~2]"
    write(repo, "src/checkout/auth.py", "\n".join(lines))
    assert out_of_task_rows(repo, {"src/checkout/auth.py": (Hunk(2, 1, 2, 1),)}) == []


def test_impact_degraded_counts_against_the_stage_whose_artifact_holds_the_line_and_code_reaches_none(fixture_repo):
    plans, index, _ = seeded(fixture_repo("seeded-change"))
    found = plan.degraded_findings(plans, index, [(REQUIREMENTS_FILE, 5), (PLAN_FILE, 15), ("src/checkout/auth.py", 2)])
    assert [(each.path, each.stage, each.position, each.level) for each in found] == [
        (REQUIREMENTS_FILE, "inception/requirements-analysis", "behind", "note"),
        (PLAN_FILE, CODE_GENERATION, "current", "note"),
        ("src/checkout/auth.py", None, "current", "note"),
    ]
    assert all("impact selected the full suite" in each.message for each in found)


def test_a_deleted_line_that_selected_the_full_suite_is_degraded_where_it_was_and_names_its_base_line(fixture_repo):
    plans, index, _ = seeded(fixture_repo("seeded-change"))
    (found,) = plan.degraded_findings(plans, index, [], [(REQUIREMENTS_FILE, 4, 5)])
    assert (found.path, found.line, found.stage, found.level) == (
        REQUIREMENTS_FILE,
        4,
        "inception/requirements-analysis",
        "note",
    )
    assert "line 5 of the baseline commit" in found.message
    assert "impact selected the full suite" in found.message


def test_the_hunk_of_a_proposed_task_that_delivers_none_of_the_changed_regions_tags_is_out_of_task(fixture_repo):
    repo = fixture_repo("seeded-change")
    plan_text = (repo / PLAN_FILE).read_text(encoding="utf-8")
    write(repo, PLAN_FILE, plan_text + "\n`task~log-it~1`\n\nLog.\n\nDelivers: req~audit-log~1\n")
    changed = {"src/checkout/auth.py": (Hunk(11, 1, 11, 1),), PLAN_FILE: (Hunk(14, 0, 15, 6),)}
    assert out_of_task_rows(repo, changed) == [
        (PLAN_FILE, 15, CODE_GENERATION, "current", "warning"),
        ("src/checkout/auth.py", 11, CODE_GENERATION, "current", "warning"),
    ]


def test_scanned_is_a_file_of_the_evaluated_tree_by_its_path_alone(fixture_repo):
    _, _, intents = seeded(fixture_repo("seeded-change"))
    assert plan.scanned(intents, "src/checkout/auth.py")
    assert plan.scanned(intents, REQUIREMENTS_FILE)
    assert not plan.scanned(intents, "aidlc/spaces/default/intents/260926-checkout/audit/fixture-a1b2c3d4.md")
    assert not plan.scanned(intents, "aidlc/spaces/default/intents/260926-checkout/aidlc-state.md")
    assert not plan.scanned(intents, "data/blob.bin")


# The change baseline: the commit of the last approved stage check the record holds.

GATE_REQ, GATE_CG = "inception/requirements-analysis", "construction/code-generation"


def held_header(stage, digest, commit, dirty=False):
    return RunHeader("r", stage, commit, dirty, "2026-09-26T12:00:00Z", ("trace",), None, None, (), "done", {}, digest)


def baseline_intent(*rows):
    """Return an intent whose audit holds one GATE_APPROVED row per (stage, hash, timestamp).

    Its approvals are the latest row of each stage, as `plan.intent` reads them.
    """
    events = tuple(
        Event((at, "a.md", number), "GATE_APPROVED", {"Stage": stage.rpartition("/")[2], "Assessment Hash": digest})
        for number, (stage, digest, at) in enumerate(rows)
    )
    approvals = {}
    for event, (stage, digest, _) in sorted(zip(events, rows, strict=True), key=lambda pair: pair[0].key):
        approvals[stage] = Approval(stage, None, "human", digest, at=event.key)
    return plan.Intent("r", "r/aidlc-state.md", (), tuple(approvals), approvals, frozenset(), (), events=events)


def runs_of(*headers):
    return {f"r/{each.stage}": each for each in headers}


def test_the_baseline_is_the_commit_of_the_header_whose_hash_the_approval_row_carries():
    intent = baseline_intent((GATE_REQ, "h1", "2026-09-26T12:00:00Z"))
    assert plan.change_baseline(intent, runs_of(held_header(GATE_REQ, "h1", "c1"))) == "c1"


def test_the_latest_approval_row_in_audit_order_gives_the_baseline_across_stages():
    intent = baseline_intent((GATE_CG, "h2", "2026-09-27T12:00:00Z"), (GATE_REQ, "h1", "2026-09-26T12:00:00Z"))
    runs = runs_of(held_header(GATE_REQ, "h1", "c1"), held_header(GATE_CG, "h2", "c2"))
    assert plan.change_baseline(intent, runs) == "c2"


def test_a_later_stage_check_that_replaces_the_header_ends_that_stage_s_claim():
    intent = baseline_intent((GATE_REQ, "h1", "2026-09-26T12:00:00Z"), (GATE_CG, "h2", "2026-09-27T12:00:00Z"))
    runs = runs_of(held_header(GATE_REQ, "h1", "c1"), held_header(GATE_CG, "h3", "c3"))
    assert plan.change_baseline(intent, runs) == "c1"


@pytest.mark.parametrize("digest", [None, "sha256:placeholder"])
def test_a_row_without_the_header_s_hash_gives_no_baseline(digest):
    intent = baseline_intent((GATE_REQ, digest, "2026-09-26T12:00:00Z"))
    assert plan.change_baseline(intent, runs_of(held_header(GATE_REQ, "h1", "c1"))) is None


def test_a_stage_without_a_held_header_or_an_approval_gives_no_baseline():
    assert plan.change_baseline(baseline_intent((GATE_REQ, "h1", "2026-09-26T12:00:00Z")), {}) is None
    assert plan.change_baseline(baseline_intent(), runs_of(held_header(GATE_REQ, "h1", "c1"))) is None


def test_a_per_unit_stage_and_a_dirty_header_give_the_baseline_as_held():
    stage = "construction/unit-a/code-generation"
    intent = baseline_intent((stage, "h1", "2026-09-26T12:00:00Z"))
    assert plan.change_baseline(intent, runs_of(held_header(stage, "h1", "c1", dirty=True))) == "c1"


def test_the_stage_s_counting_row_gives_its_place_in_audit_order():
    # a stage approved again with the same hash is at its latest row, after the other stage
    rows = ((GATE_REQ, "h1", "2026-09-26T12:00:00Z"), (GATE_CG, "h2", "2026-09-27T12:00:00Z"))
    intent = baseline_intent(*rows, (GATE_REQ, "h1", "2026-09-28T12:00:00Z"))
    runs = runs_of(held_header(GATE_REQ, "h1", "c1"), held_header(GATE_CG, "h2", "c2"))
    assert plan.change_baseline(intent, runs) == "c1"
