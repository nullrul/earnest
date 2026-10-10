"""Tests for earnest.plan: the state file's Stage Progress, the audit shards, and loading both from a work tree."""

from earnest import plan
from earnest.plan import Event, Record, Row


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
