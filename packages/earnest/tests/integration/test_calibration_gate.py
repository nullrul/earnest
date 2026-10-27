"""Integration: `earnest calibrate` writes the record's `calibration` slot in the working directory's repository."""

import json

from tests.conftest import verdicts_file
from tests.sarif import record, run_earnest


def stub(monkeypatch, file):
    monkeypatch.setenv("EARNEST_JUDGE", f"stub:{verdicts_file('calibration-dev', file)}")


def test_the_slot_is_written_on_a_pass_and_replaced_by_a_fail_and_other_slots_stay(fixture_repo, monkeypatch):
    repo = fixture_repo("calibration-dev")
    stub(monkeypatch, "stub-pass.json")
    assert run_earnest(repo, "calibrate", ".").returncode == 0
    first = record(repo)["calibration"]
    assert (first["matches"], first["pass"]) == (8, True)
    data = record(repo)
    held = {"judge": {"cache": {"k": {"item": "req~x~1", "question": "tested"}}}, "evidence": {"req~x~1": {"a": 1}}}
    (repo / ".earnest" / "assessment.json").write_text(json.dumps({**data, **held}), encoding="utf-8")
    stub(monkeypatch, "stub-fail.json")
    done = run_earnest(repo, "calibrate", ".")
    assert done.returncode == 1, done.stderr
    after = record(repo)
    assert (after["calibration"]["matches"], after["calibration"]["pass"]) == (7, False)
    assert after["judge"] == held["judge"]
    assert after["evidence"] == held["evidence"]


def test_calibrate_indexes_the_fixture_and_records_in_the_working_directorys_repository(
    fixture_repo, files_repo, monkeypatch
):
    fixture = fixture_repo("calibration-dev")
    other = files_repo({"other.md": "# Other\n\n`req~other~1`\n\nThe other shall do it.\n"})
    stub(monkeypatch, "stub-pass.json")
    done = run_earnest(other, "calibrate", str(fixture))
    assert done.returncode == 0, done.stderr
    ids = [line.split()[0] for line in done.stdout.splitlines() if line.startswith("req~")]
    assert len(ids) == 10
    assert "req~other~1" not in done.stdout
    assert record(other)["calibration"]["matches"] == 8
    assert not (fixture / ".earnest").exists()
