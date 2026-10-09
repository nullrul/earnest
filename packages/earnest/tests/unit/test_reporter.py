"""Tests for earnest.reporter: SARIF 2.1.0, percentages and the summary."""

import json

from earnest import reporter
from earnest.reporter import Finding
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
    }


def test_percentages_round_down_so_100_means_every_requirement():
    assert reporter.percentages(LEVELS) == {"traced": 66, "judged": 0, "evidenced": 0}
    almost = {f"req~r{number}~1": "traced" for number in range(199)} | {"req~last~1": "untraced"}
    assert reporter.percentages(almost)["traced"] == 99
    assert reporter.percentages({}) == {"traced": 0, "judged": 0, "evidenced": 0}


def test_the_log_is_one_sarif_2_1_0_run_with_located_results_in_order():
    text = reporter.sarif(FINDINGS, LEVELS, "abc123")
    assert json.loads(text)["version"] == "2.1.0"
    run = sarif_run(text)
    assert run["tool"] == {"driver": {"name": "earnest"}}
    assert [(result["ruleId"], result["level"]) for result in run["results"]] == [
        ("earnest/gap", "error"),
        ("earnest/unwanted", "warning"),
    ]
    assert run["properties"] == {"traceLevels": LEVELS, "percentages": {"traced": 66, "judged": 0, "evidenced": 0}}
    assert run["invocations"] == [
        {"executionSuccessful": True, "properties": {"commit": "abc123", "layers": ["trace"]}},
    ]


def test_each_result_sits_at_its_percent_encoded_file_in_scope_over_its_observation():
    first = sarif_run(reporter.sarif(FINDINGS, LEVELS, "abc123"))["results"][0]
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
    assert reporter.sarif(FINDINGS, LEVELS, "abc") == reporter.sarif(FINDINGS[::-1], shuffled, "abc")


def test_the_summary_leads_with_the_three_percentages():
    lines = reporter.summary(FINDINGS, LEVELS).splitlines()
    assert lines[0] == "traced 66%, judged 0%, evidenced 0%; requirements: 3"
    assert lines[1:4] == ["  req~a~1: traced", "  req~b~1: untraced", "  req~c~1: traced"]
    assert lines[4] == "docs/a b.md:9: error earnest/gap: in scope: a"
    assert lines[-1] == "findings: 2, errors: 1"
