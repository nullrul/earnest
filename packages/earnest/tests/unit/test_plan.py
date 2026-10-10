"""Tests for earnest.plan: the state file's Stage Progress, the audit shards, and loading both from a work tree."""

from earnest import plan
from earnest.index import Id, Index, Item
from earnest.plan import Approval, Event, Record, Row


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
