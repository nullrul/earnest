"""Steps for tests/features/calibration_gate.feature: earnest calibrate against the synthetic calibration-dev fixture."""

from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import model_id, prompt_hash
from tests.sarif import record, results, rows, run_earnest, sarif_run
from tests.steps.test_evidence_check import no_rule_finding
from tests.steps.test_judge_check import agent_runs_judge_check


scenarios("calibration_gate.feature")

# Steps of other step modules, bound here too, since only conftest.py's steps are shared.
when("the coding agent runs earnest check --judge", target_fixture="run")(agent_runs_judge_check)
then(parsers.re(r"the SARIF log holds no (?P<rule>earnest/\S+) finding"))(no_rule_finding)


def calibration_rows(run):
    """Return the requirement lines of calibrate's stdout as (id, judge, maintainer, agreement)."""
    lines = [line.split() for line in run.stdout.splitlines() if line.startswith("req~")]
    return [(id_, judge, maintainer, agreement) for id_, _, judge, _, maintainer, agreement in lines]


# The repository and the faults.


@given(parsers.parse('the repo maintainer\'s "{name}" repository committed on main'), target_fixture="repo")
def maintainer_repository(fixture_repo, name):
    return fixture_repo(name)


@given("the repo maintainer has run earnest calibrate")
def maintainer_has_calibrated(repo):
    run = run_earnest(repo, "calibrate", ".")
    assert run.returncode == 0, run.stderr


@given("EARNEST_JUDGE is unset")
def judge_unset(monkeypatch):
    monkeypatch.delenv("EARNEST_JUDGE", raising=False)


@given("the fixture's verdicts.json is deleted")
def verdicts_deleted(repo):
    (repo / "verdicts.json").unlink()


@given("the fixture's last requirement is deleted")
def last_requirement_deleted(repo):
    text = (repo / "requirements.md").read_text(encoding="utf-8")
    cut = text.find("`req~receipt-total~1`")
    assert cut != -1
    (repo / "requirements.md").write_text(text[:cut], encoding="utf-8")


# The run.


@when("the repo maintainer runs earnest calibrate", target_fixture="run")
def maintainer_runs_calibrate(repo):
    return run_earnest(repo, "calibrate", ".")


# What calibrate prints, returns and records.


@then("the calibration lists these requirements:")
def calibration_lists(run, datatable):
    expected = [(row["requirement"], row["judge"], row["maintainer"], row["agreement"]) for row in rows(datatable)]
    assert calibration_rows(run) == expected, run.stdout


@then(parsers.re(r'the calibration lists "(?P<a>[^"]+)", "(?P<b>[^"]+)" and "(?P<c>[^"]+)" as differing'))
def calibration_differing(run, a, b, c):
    assert {row[0] for row in calibration_rows(run) if row[3] == "differs"} == {a, b, c}, run.stdout


@then(parsers.parse('the calibration ends with "{matches}" and "{verdict}"'))
def calibration_ends(run, matches, verdict):
    assert run.stdout.splitlines()[-2:] == [matches, verdict], run.stdout


@then(parsers.parse("the calibrate exits with code {code:d}"))
def calibrate_exits(run, code):
    assert run.returncode == code, run.stderr


@then(
    parsers.re(
        r'the record\'s calibration slot holds the model of "(?P<file>[^"]+)", the prompt hash,'
        r" (?P<matches>\d+) matches of 10 and (?P<verdict>a pass|no pass)"
    )
)
def record_holds_calibration(repo, file, matches, verdict):
    assert record(repo)["calibration"] == {
        "model": model_id("calibration-dev", file),
        "prompt": prompt_hash(),
        "matches": int(matches),
        "total": 10,
        "pass": verdict == "a pass",
    }


@then(parsers.parse('the calibrate exits with code 2, with empty stdout and one line on stderr naming "{cause}"'))
def calibrate_cannot_run(run, cause):
    assert run.returncode == 2, run.stderr
    assert run.stdout == ""
    assert run.stderr.startswith("earnest: ")
    assert len(run.stderr.splitlines()) == 1, run.stderr
    assert cause in run.stderr


@then("the record holds no calibration")
def record_holds_none(repo):
    assert not (repo / ".earnest" / "assessment.json").exists() or record(repo)["calibration"] is None


@then(parsers.parse('the SARIF log gives the model of "{file}" and the prompt hash in the run\'s invocation'))
def invocation_names_model(run, file):
    (invocation,) = sarif_run(run.stdout)["invocations"]
    assert invocation["properties"]["model"] == model_id("calibration-dev", file)
    assert invocation["properties"]["prompt"] == prompt_hash()


@then(parsers.parse('the earnest/judge-uncalibrated finding names the model of "{file}" and the prompt hash'))
def uncalibrated_names_model(run, file):
    (finding,) = [result for result in results(run) if result["ruleId"] == "earnest/judge-uncalibrated"]
    text = finding["message"]["text"]
    assert model_id("calibration-dev", file) in text
    assert prompt_hash() in text
