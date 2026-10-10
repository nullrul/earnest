"""Tests for earnest.reporter: SARIF 2.1.0, percentages and the summary."""

import json

import pytest

from earnest import reporter
from earnest.reporter import Finding, Run
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
    entry = {**PLAN["intents"][0], "frontier": None, "units": [{"id": "unit~a~1", "status": "not done"}]}
    lines = reporter.summary([], {}, Run(commit="abc", plan={"intents": [entry]})).splitlines()
    assert lines[4:8] == [
        "  frontier: none",
        "  task task~a~1: not done",
        "  task task~b~1: done",
        "  unit unit~a~1: not done",
    ]


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
