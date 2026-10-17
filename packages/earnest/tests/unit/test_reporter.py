"""Tests for earnest.reporter: SARIF 2.1.0, percentages and the summary."""

import ast
import json
import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from earnest import reporter
from earnest.reporter import Finding, Record, RecordError, Run, RunHeader
from tests.sarif import sarif_run


FINDINGS = [
    Finding("src/b.py", 3, "earnest/unwanted", "req~b~1", "b"),
    Finding("docs/a b.md", 9, "earnest/gap", "req~a~1", "a"),
]
LEVELS = {"req~a~1": "traced", "req~b~1": "untraced", "req~c~1": "traced"}


def test_each_rule_has_its_sarif_level():
    assert reporter.RULES == {
        "earnest/duplicate": "error",
        "earnest/gap": "error",
        "earnest/near-miss": "error",
        "earnest/orphaned": "error",
        "earnest/outdated": "error",
        "earnest/predated": "error",
        "earnest/unwanted": "warning",
        "earnest/unbumped-change": "error",
        "earnest/unplanned": "warning",
        "earnest/cycle": "error",
        "earnest/route-mismatch": "error",
    }


def test_percentages_round_down_so_100_means_every_requirement():
    assert reporter.percentages(LEVELS) == {"traced": 66, "judged": 0, "evidenced": 0}
    almost = {f"req~r{number}~1": "traced" for number in range(199)} | {"req~last~1": "untraced"}
    assert reporter.percentages(almost)["traced"] == 99
    assert reporter.percentages({}) == {"traced": 0, "judged": 0, "evidenced": 0}


def test_the_log_is_one_sarif_2_1_0_run_with_located_results_in_order():
    text = reporter.sarif(FINDINGS, LEVELS, Run(commit="abc123"))
    assert json.loads(text)["version"] == "2.1.0"
    run = sarif_run(text)
    assert run["tool"] == {"driver": {"name": "earnest"}}
    assert [(result["ruleId"], result["level"]) for result in run["results"]] == [
        ("earnest/gap", "error"),
        ("earnest/unwanted", "warning"),
    ]
    assert run["properties"] == {"traceLevels": LEVELS, "percentages": {"traced": 66, "judged": 0, "evidenced": 0}}
    assert run["invocations"] == [
        {"executionSuccessful": True, "properties": {"commit": "abc123", "dirty": False, "layers": ["trace"]}},
    ]


def test_each_result_sits_at_its_percent_encoded_file_in_scope_over_its_observation():
    first = sarif_run(reporter.sarif(FINDINGS, LEVELS, Run(commit="abc123")))["results"][0]
    location = {"artifactLocation": {"uri": "docs/a%20b.md"}, "region": {"startLine": 9}}
    assert first["locations"] == [{"physicalLocation": location}]
    assert first["message"] == {"text": "in scope: a"}
    assert first["properties"]["position"] == "current"
    assert "stage" not in first["properties"]
    assert first["properties"]["observations"] == [
        {"method": "trace", "subject": "req~a~1", "result": "gap", "reasoning": "a", "location": location},
    ]


def test_the_same_findings_in_another_order_give_the_same_bytes():
    shuffled = dict(reversed(LEVELS.items()))
    run = Run(commit="abc")
    assert reporter.sarif(FINDINGS, LEVELS, run) == reporter.sarif(FINDINGS[::-1], shuffled, run)


def test_the_log_is_one_line_that_ends_in_a_single_newline():
    log = reporter.sarif(FINDINGS, LEVELS, Run(commit="abc"))
    assert log.endswith("}\n")
    assert log.count("\n") == 1


def test_the_summary_lists_the_levels_by_requirement_id_whatever_their_order():
    lines = reporter.summary([], dict(reversed(LEVELS.items()))).splitlines()
    assert lines[1:4] == ["  req~a~1: traced", "  req~b~1: untraced", "  req~c~1: traced"]


def test_the_summary_counts_no_error_for_a_finding_of_an_error_rule_that_reads_as_a_note():
    notes = [gap(stage=STAGE, position="ahead"), Finding("a.md", 1, "earnest/outdated", "req~a~1", "m", note=True)]
    lines = reporter.summary(notes, {}).splitlines()
    assert [line.split(" ", 2)[1] for line in lines if line.startswith(("a.md:", "r/x.md:"))] == ["note", "note"]
    assert lines[-1] == "findings: 2, errors: 0"


def test_the_summary_leads_with_the_three_percentages():
    lines = reporter.summary(FINDINGS, LEVELS).splitlines()
    assert lines[0] == "traced 66%, judged 0%, evidenced 0%; requirements: 3"
    assert lines[1:4] == ["  req~a~1: traced", "  req~b~1: untraced", "  req~c~1: traced"]
    assert lines[4] == "docs/a b.md:9: error earnest/gap: in scope: a"
    assert lines[-1] == "findings: 2, errors: 1"


RECORD = "aidlc/spaces/default/intents/260926-checkout"
STAGE = "construction/code-generation"
HASH = "sha256:" + "0" * 64
PLAN = {
    "intents": [
        {
            "intent": RECORD,
            "stages": [
                {
                    "stage": "inception/requirements-analysis",
                    "status": "done",
                    "approval": "current",
                    "approvedBy": "human",
                },
                {"stage": STAGE, "status": "not done", "approval": "none", "approvedBy": None},
            ],
            "frontier": STAGE,
            "tasks": [{"id": "task~a~1", "status": "not done"}, {"id": "task~b~1", "status": "done"}],
            "units": [],
        },
    ],
}
ASSESSMENT = {"stage": f"{RECORD}/{STAGE}", "hash": HASH, "status": "not done", "reasons": {"approval": "none"}}


def gap(**fields):
    return Finding("a.md", 1, "earnest/gap", "req~a~1", "m", **fields)


@pytest.mark.parametrize(
    ("rule", "level"),
    [
        ("earnest/unbumped-change", "error"),
        ("earnest/unplanned", "warning"),
        ("earnest/cycle", "error"),
        ("earnest/route-mismatch", "error"),
    ],
)
def test_new_rules_carry_their_levels(rule, level):
    assert reporter.RULES[rule] == level
    assert Finding("a.md", 1, rule, "x", "m").level == level


def test_ahead_position_makes_a_note():
    assert gap(stage=STAGE, position="ahead").level == "note"
    assert gap(stage=STAGE, position="behind").level == "error"
    assert gap(stage=STAGE, position="current").level == "error"
    assert gap(stage=STAGE, intent=RECORD, position="ahead", note=True, child="impl") == gap()  # no part in equality


def test_note_flag_makes_a_note_at_every_position():
    for position in ("behind", "current", "ahead"):
        assert gap(stage=STAGE, position=position, note=True).level == "note"
    assert Finding("a.md", 1, "earnest/outdated", "req~a~1", "m", note=True).level == "note"
    assert Finding("a.md", 1, "earnest/outdated", "req~a~1", "m").level == "error"


@pytest.mark.parametrize(
    ("stage", "position", "text"),
    [
        (None, "current", "in scope: m"),
        (STAGE, "current", f"in scope at {STAGE}: m"),
        (STAGE, "behind", f"regression in approved stage {STAGE}: m"),
        (STAGE, "ahead", f"expected at {STAGE}: m"),
    ],
)
def test_text_opens_with_the_position(stage, position, text):
    assert gap(stage=stage, position=position).text == text


def test_result_carries_position_and_stage():
    (result,) = sarif_run(reporter.sarif([gap(stage=STAGE, position="ahead")], {}, Run(commit="abc")))["results"]
    assert result["properties"]["position"] == "ahead"
    assert result["properties"]["stage"] == STAGE
    assert result["level"] == "note"
    assert result["message"] == {"text": f"expected at {STAGE}: m"}


def test_result_omits_stage_when_none():
    (result,) = sarif_run(reporter.sarif([gap()], {}, Run(commit="abc")))["results"]
    assert result["properties"]["position"] == "current"
    assert "stage" not in result["properties"]


def test_invocation_carries_dirty():
    run = sarif_run(reporter.sarif([], {}, Run(commit="abc", dirty=True)))
    assert run["invocations"][0]["properties"] == {"commit": "abc", "dirty": True, "layers": ["trace"]}


def test_run_carries_plan_with_an_intents_list_and_assessment_properties():
    run = sarif_run(reporter.sarif([], {}, Run(commit="abc", plan=PLAN, assessment=ASSESSMENT)))
    assert run["properties"]["plan"] == PLAN
    assert run["properties"]["assessment"] == ASSESSMENT
    assert run["properties"]["plan"]["intents"][0]["intent"] == RECORD
    bare = sarif_run(reporter.sarif([], {}, Run(commit="abc")))
    assert set(bare["properties"]) == {"traceLevels", "percentages"}


def test_summary_lists_stages_frontier_and_hash():
    lines = reporter.summary([], {}, Run(commit="abc", plan=PLAN, assessment=ASSESSMENT)).splitlines()
    assert lines[:5] == [
        "traced 0%, judged 0%, evidenced 0%; requirements: 0",
        f"intent {RECORD}",
        "  inception/requirements-analysis: done, approval current, human",
        f"  {STAGE}: not done, approval none",
        f"  frontier: {STAGE}",
    ]
    assert f"assessment {RECORD}/{STAGE}: {HASH} (not done)" in lines
    assert lines[-1] == "findings: 0, errors: 0"


def test_summary_lists_tasks_and_units_with_their_status():
    unit = {"id": "unit~a~1", "status": "not done", "directory": None, "frontier": None}
    entry = {**PLAN["intents"][0], "frontier": None, "units": [unit]}
    lines = reporter.summary([], {}, Run(commit="abc", plan={"intents": [entry]})).splitlines()
    assert lines[4:8] == [
        "  frontier: none",
        "  task task~a~1: not done",
        "  task task~b~1: done",
        "  unit unit~a~1: not done, directory none, frontier none",
    ]
    placed = {**unit, "directory": "a-dir", "frontier": "construction/a-dir/code-generation"}
    lines = reporter.summary([], {}, Run(commit="abc", plan={"intents": [{**entry, "units": [placed]}]})).splitlines()
    assert lines[7] == "  unit unit~a~1: not done, directory a-dir, frontier construction/a-dir/code-generation"


def test_summary_states_a_missing_record():
    lines = reporter.summary([], {}, Run(commit="abc", record_absent=True)).splitlines()
    assert "record: absent, body-hash baseline unavailable" in lines
    assert not [line for line in lines if line.startswith("body-hash baseline")]
    assert (
        "record: absent, body-hash baseline unavailable" not in reporter.summary([], {}, Run(commit="abc")).splitlines()
    )


def test_summary_counts_items_without_a_held_hash():
    lines = reporter.summary([], {}, Run(commit="abc", unheld=2)).splitlines()
    assert "body-hash baseline: 2 items without a held hash" in lines
    assert not [
        line for line in reporter.summary([], {}, Run(commit="abc", unheld=0)).splitlines() if "baseline" in line
    ]
    assert reporter.summary(FINDINGS, LEVELS) == reporter.summary(FINDINGS, LEVELS, Run(commit="abc"))


INTENT = "aidlc/spaces/default/intents/260926-checkout"


def header(intent=INTENT, stage="construction/code-generation"):
    return RunHeader(
        intent=intent,
        stage=stage,
        commit="a" * 40,
        dirty=False,
        timestamp="2026-09-26T12:00:00Z",
        layers=("trace",),
        model=None,
        prompt=None,
        items=("task~a~1", "task~b~1"),
        status="not done",
        reasons={"errors": 0, "openTasks": 2, "approval": "none"},
        digest="sha256:" + "1" * 64,
    )


def stored(root):
    return json.loads((root / ".earnest" / "assessment.json").read_text(encoding="utf-8"))


def test_canonical_compact_bytes_have_no_trailing_newline():
    assert reporter.canonical({"b": [1, 2], "a": "caf\u00e9", "c": None}) == '{"a":"caf\\u00e9","b":[1,2],"c":null}'
    assert reporter.canonical({"t": (1, 2), "f": False}) == '{"f":false,"t":[1,2]}'


def test_canonical_pretty_bytes_end_with_one_newline():
    pretty = reporter.canonical({"b": 1, "a": {"c": 2}, "e": "\u00e9"}, pretty=True)
    assert pretty == '{\n  "a": {\n    "c": 2\n  },\n  "b": 1,\n  "e": "\\u00e9"\n}\n'


def test_canonical_rejects_floats_and_nan():
    for value in (1.5, float("nan"), float("inf"), [1, (2, 0.5)], {"a": {"b": 2.0}}):
        with pytest.raises(TypeError, match="integers only"):
            reporter.canonical({"value": value})


def test_run_key_joins_intent_and_stage():
    assert reporter.run_key(INTENT, "inception/requirements-analysis") == f"{INTENT}/inception/requirements-analysis"


def test_utc_timestamp_shape():
    assert reporter.utc_timestamp(datetime(2026, 9, 26, 12, 0, 0, tzinfo=UTC)) == "2026-09-26T12:00:00Z"
    plus_two = timezone(timedelta(hours=2))
    assert reporter.utc_timestamp(datetime(2026, 9, 26, 12, 0, 0, 999, tzinfo=plus_two)) == "2026-09-26T10:00:00Z"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", reporter.utc_timestamp())


def test_record_round_trips(tmp_path):
    held = header()
    record = Record(runs={reporter.run_key(INTENT, held.stage): held}, bodies={"req~a~1": "sha256:" + "2" * 64})
    reporter.write_record(tmp_path, record)
    assert reporter.read_record(tmp_path) == record
    data = stored(tmp_path)
    assert data["runs"][f"{INTENT}/{held.stage}"]["hash"] == held.digest  # the digest travels as the key `hash`
    assert "digest" not in data["runs"][f"{INTENT}/{held.stage}"]
    text = (tmp_path / ".earnest" / "assessment.json").read_text(encoding="utf-8")
    assert text == reporter.canonical(data, pretty=True)


def test_missing_record_is_empty_with_the_slot_defaults(tmp_path):
    record = reporter.read_record(tmp_path)
    assert record == Record()
    assert (record.version, record.runs, record.bodies) == (1, {}, {})
    assert (record.coverage, record.judge, record.calibration) == ({"commit": None}, {"cache": {}}, None)
    assert not (tmp_path / ".earnest").exists()  # reading writes nothing


def test_a_symlinked_earnest_directory_is_neither_read_nor_written(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".earnest").symlink_to(outside)
    with pytest.raises(OSError, match=r"\.earnest"):
        reporter.read_record(repo)
    with pytest.raises(OSError, match=r"\.earnest"):
        reporter.write_record(repo, Record())
    assert list(outside.iterdir()) == []


def test_a_symlinked_record_is_neither_read_nor_written_and_its_target_stays_unread(tmp_path):
    target = tmp_path / "outside.bin"
    target.write_bytes(b"\xff\xfe secret bytes")
    repo = tmp_path / "repo"
    (repo / ".earnest").mkdir(parents=True)
    (repo / ".earnest" / "assessment.json").symlink_to(target)
    for action in (lambda: reporter.read_record(repo), lambda: reporter.write_record(repo, Record())):
        with pytest.raises(OSError, match=r"\.earnest/assessment\.json is a symlink") as error:
            action()
        assert "secret" not in str(error.value)
    assert target.read_bytes() == b"\xff\xfe secret bytes"
    assert (repo / ".earnest" / "assessment.json").is_symlink()


def test_a_record_that_is_not_utf8_keeps_its_bytes_out_of_the_error(tmp_path):
    (tmp_path / ".earnest").mkdir()
    (tmp_path / ".earnest" / "assessment.json").write_bytes(b"\xff\xfe secret bytes")
    with pytest.raises(RecordError, match=r"UnicodeDecodeError") as error:
        reporter.read_record(tmp_path)
    assert "secret" not in str(error.value)


def test_corrupt_record_raises_and_names_the_file(tmp_path):
    (tmp_path / ".earnest").mkdir()
    slots = '"runs": {}, "bodies": {}, "coverage": {}, "judge": {}, "calibration": null'  # a whole record's slots
    for text in (
        "{not json",
        "[]",
        '{"version": 1}',
        '{"version": 0}',
        '{"version": "1"}',
        '{"version": 1, "runs": []}',
        f'{{"version": 1, {slots}, "x": 1.5}}',  # a float or NaN would crash the next write
        f'{{"version": 1, {slots}, "x": NaN}}',
        "[" * 100_000,  # RecursionError
        "\xff",
    ):
        (tmp_path / ".earnest" / "assessment.json").write_text(text, encoding="utf-8")
        with pytest.raises(RecordError, match=r"\.earnest/assessment\.json"):
            reporter.read_record(tmp_path)
    (tmp_path / ".earnest" / "assessment.json").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(RecordError, match=r"\.earnest/assessment\.json"):
        reporter.read_record(tmp_path)


def test_newer_version_raises(tmp_path):
    (tmp_path / ".earnest").mkdir()
    (tmp_path / ".earnest" / "assessment.json").write_text('{"version": 2}', encoding="utf-8")
    with pytest.raises(RecordError, match="version 2"):
        reporter.read_record(tmp_path)


def test_unknown_top_level_keys_survive_a_write_at_the_same_version(tmp_path):
    reporter.write_record(tmp_path, Record(extra={"future": {"a": [1, 2]}}))
    record = reporter.read_record(tmp_path)
    assert record.extra == {"future": {"a": [1, 2]}}
    record.bodies["req~a~1"] = "sha256:" + "3" * 64
    reporter.write_record(tmp_path, record)
    data = stored(tmp_path)
    assert data["future"] == {"a": [1, 2]}
    assert data["bodies"] == {"req~a~1": "sha256:" + "3" * 64}
    assert data["version"] == 1


def test_write_creates_the_marker_once_and_never_rewrites_an_existing_directory(tmp_path):
    reporter.write_record(tmp_path, Record())
    marker = tmp_path / ".earnest" / ".gitignore"
    assert marker.read_text(encoding="utf-8") == "*\n"
    marker.write_text("custom\n", encoding="utf-8")  # a repository's own choice
    reporter.write_record(tmp_path, Record())
    assert marker.read_text(encoding="utf-8") == "custom\n"
    other = tmp_path / "other"
    (other / ".earnest").mkdir(parents=True)
    reporter.write_record(other, Record())
    assert not (other / ".earnest" / ".gitignore").exists()


def test_write_is_atomic_when_replace_fails(tmp_path, monkeypatch):
    reporter.write_record(tmp_path, Record(bodies={"req~a~1": "sha256:" + "4" * 64}))
    before = (tmp_path / ".earnest" / "assessment.json").read_bytes()

    def refuse(self, target):
        raise PermissionError(target)

    monkeypatch.setattr(Path, "replace", refuse)
    with pytest.raises(PermissionError):
        reporter.write_record(tmp_path, Record(bodies={"req~a~1": "sha256:" + "5" * 64}))
    assert (tmp_path / ".earnest" / "assessment.json").read_bytes() == before
    assert sorted(path.name for path in (tmp_path / ".earnest").iterdir()) == [".gitignore", "assessment.json"]


def test_runs_are_keyed_by_intent_and_stage_so_two_intents_never_collide(tmp_path):
    one, two = header("intents/one"), header("intents/two")
    record = Record(runs={reporter.run_key(h.intent, h.stage): h for h in (one, two)})
    reporter.write_record(tmp_path, record)
    assert sorted(stored(tmp_path)["runs"]) == [
        "intents/one/construction/code-generation",
        "intents/two/construction/code-generation",
    ]
    assert reporter.read_record(tmp_path) == record


def test_reporter_imports_neither_structural_nor_plan():
    tree = ast.parse(Path(reporter.__file__).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert not {name for name in names if name.startswith(("earnest.structural", "earnest.plan"))}
