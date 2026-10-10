"""Tests for earnest.plan: the state file's Stage Progress, the audit shards, and loading both from a work tree."""

from earnest import plan
from earnest.index import Id, Index, Item, Link
from earnest.plan import Approval, Event, Record, Row
from earnest.reporter import Finding


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
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")


def test_scope_is_read_from_the_state_file():
    assert plan.parse_state(STATE_TEXT).scope == "bugfix"
    assert plan.parse_state("# nothing\n").scope == ""


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


def intent_of(*blocks, state=FULL_STATE, directory="r"):
    events = tuple(sorted(events_of(*blocks)))
    return plan.intent(Record(directory, f"{directory}/aidlc-state.md", plan.parse_state(state), events))


def item(text, stage=REQUIREMENTS, line=1):
    kind, name, revision = text.split("~")
    return Item(Id(kind, name, int(revision)), f"r/{stage}/doc.md", line)


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


def test_units_generation_on_the_route_is_unsupported():
    state = FULL_STATE.replace(
        f"- [S] units-generation {DASH} SKIP: not in bugfix scope", f"- [ ] units-generation {DASH} EXECUTE: needed"
    )
    current = intent_of(BASE, state=state)
    assert "inception/units-generation" in current.route
    assert current.unsupported


def test_units_generation_off_the_route_is_supported():
    assert not intent_of(BASE).unsupported
    assert not intent_of(START).unsupported


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


def ident(text):
    kind, name, revision = text.split("~")
    return Id(kind, name, int(revision))


def delivers(task_text, req_text, line=7):
    return Link("Delivers", "task", ident(req_text), PLAN_PATH, line, owner=ident(task_text))


def depends(task_text, other_text, line=8):
    return Link("Depends", "task", ident(other_text), PLAN_PATH, line, owner=ident(task_text))


def task(text, line=3):
    return item(text, stage=CODE_GENERATION, line=line)


def planned(*blocks, items=(), links=(), state=FULL_STATE):
    """Return the plan and the index of an intent that the audit blocks describe, over the given items and links."""
    index = Index(tuple(items), tuple(links), ())
    return plan.build(intent_of(*blocks, state=state), index), index


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


def test_produces_is_none_when_the_route_produces_nothing():
    assert plan.produces([intent_of(BASE, state="## Stage Progress\n")]) is None  # an emptied route is no route rule
    assert plan.produces([intent_of(BASE, state="")]) is None


def test_produces_is_none_when_no_intent_is_supported():
    state = FULL_STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")
    assert plan.produces([]) is None
    assert plan.produces([intent_of(BASE, state=state)]) is None
    assert plan.produces([intent_of(BASE, state=state), intent_of(BASE)]) == plan.produces([intent_of(BASE)])


def test_in_tree_is_false_for_an_unsupported_intents_state_and_audit_files():
    state = FULL_STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")
    unsupported = intent_of(BASE, state=state, directory="u")
    assert unsupported.unsupported
    assert not plan.in_tree([unsupported], "u/aidlc-state.md")
    assert not plan.in_tree([unsupported], "u/audit/a.md")
    assert plan.in_tree([unsupported], "u/inception/requirements-analysis/requirements.md")


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


def test_properties_leave_out_an_unsupported_intent():
    state = FULL_STATE.replace(f"- [S] units-generation {DASH} SKIP", f"- [ ] units-generation {DASH} EXECUTE")
    built, index = planned(BASE)
    unsupported = plan.build(intent_of(BASE, state=state, directory="u"), index)
    statuses = {p.intent.directory: plan.statuses(p, index, [], {}) for p in (built, unsupported)}
    props = plan.properties([unsupported, built], statuses, index, {})
    assert [entry["intent"] for entry in props["intents"]] == ["r"]
    assert plan.properties([unsupported], statuses, index, {}) == {"intents": []}
