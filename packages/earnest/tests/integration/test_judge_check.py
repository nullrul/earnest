"""Integration: `check --judge` writes the judge cache to the record's `judge` slot and answers a rerun from it."""

import json
from pathlib import Path

from tests.conftest import commit_on_main
from tests.sarif import record, run_earnest


VERDICTS = Path(__file__).parent.parent / "fixtures" / "seeded-change" / "judge-verdicts.json"


def judged_repo(fixture_repo, monkeypatch):
    repo = commit_on_main(fixture_repo("seeded-change"), "seeded-change", "override")
    monkeypatch.setenv("EARNEST_JUDGE", f"stub:{VERDICTS}")
    return repo


def test_the_judge_slot_round_trips_and_a_rerun_with_an_unchanged_key_reuses_it(fixture_repo, monkeypatch):
    repo = judged_repo(fixture_repo, monkeypatch)
    first = run_earnest(repo, "check", "--judge")
    assert first.returncode == 1, first.stderr
    slot = record(repo)["judge"]
    assert sorted((entry["item"], entry["question"]) for entry in slot["cache"].values()) == [
        ("req~lockout-notice~1", "tested"),
        ("req~rate-limit~1", "tested"),
    ]
    second = run_earnest(repo, "check", "--judge")
    assert second.stdout == first.stdout
    assert record(repo)["judge"] == slot


def test_a_plain_check_writes_no_record_and_reports_no_judge(fixture_repo, monkeypatch):
    repo = judged_repo(fixture_repo, monkeypatch)
    done = run_earnest(repo, "check")
    assert not (repo / ".earnest").exists()
    run = json.loads(done.stdout)["runs"][0]
    assert "observations" not in run["properties"]
    assert run["invocations"][0]["properties"]["layers"] == ["trace"]
