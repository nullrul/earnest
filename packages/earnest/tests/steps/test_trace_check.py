"""Steps for tests/features/trace_check.feature: `earnest check` over the broken-links fixture."""

import json
import subprocess
import sys
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from tests.sarif import located, sarif_run


scenarios("trace_check.feature")

EARNEST = Path(sys.executable).with_name("earnest")


def run_check(repo):
    """Run `earnest check` in repo, as the coding agent does."""
    return subprocess.run([str(EARNEST), "check"], cwd=repo, capture_output=True, text=True, check=False)


def rows(datatable):
    """Return a data table's rows as dicts keyed by its header."""
    header, *body = datatable
    return [dict(zip(header, row, strict=True)) for row in body]


@given(
    parsers.parse('the repo maintainer\'s "{name}" repository, with a broken link of every kind'),
    target_fixture="repo",
)
def maintainer_repository(fixture_repo, name):
    return fixture_repo(name)


@when("the coding agent runs earnest check", target_fixture="run")
def agent_runs_check(repo):
    return run_check(repo)


@when("the coding agent runs earnest check twice", target_fixture="runs")
def agent_runs_check_twice(repo):
    return [run_check(repo), run_check(repo)]


@then("both runs write the same SARIF log")
def same_log(runs):
    first, second = runs
    assert json.loads(first.stdout)["version"] == "2.1.0"
    assert first.stdout == second.stdout


@then("the SARIF log holds exactly these findings:")
def exact_findings(run, datatable):
    expected = sorted((row["rule"], row["file"], int(row["line"])) for row in rows(datatable))
    actual = sorted((result["ruleId"], *located(result)) for result in sarif_run(run.stdout)["results"])
    assert actual == expected


@then("every finding is in scope at position current, with no stage")
def all_current(run):
    for result in sarif_run(run.stdout)["results"]:
        assert result["properties"]["position"] == "current"
        assert "stage" not in result["properties"]
        assert result["message"]["text"].startswith("in scope: ")


@then("every finding carries the trace observation behind it")
def observations(run):
    for result in sarif_run(run.stdout)["results"]:
        (observation,) = result["properties"]["observations"]
        assert observation["method"] == "trace"
        assert observation["result"] == result["ruleId"].removeprefix("earnest/")
        assert observation["location"] == result["locations"][0]["physicalLocation"]
        assert f"`{observation['subject']}`" in result["message"]["text"]


@then("each finding at these places names its fix:")
def findings_name_fix(run, datatable):
    results = sarif_run(run.stdout)["results"]
    for row in rows(datatable):
        texts = [r["message"]["text"] for r in results if located(r) == (row["file"], int(row["line"]))]
        assert any(row["fix"] in text for text in texts), (row, texts)


@then("the SARIF log gives each requirement one trace level:")
def trace_levels(run, datatable):
    expected = {row["requirement"]: row["level"] for row in rows(datatable)}
    assert sarif_run(run.stdout)["properties"]["traceLevels"] == expected


@then("each untraced requirement has a located finding that names it")
def untraced_have_reasons(run):
    run_log = sarif_run(run.stdout)
    for requirement, level in run_log["properties"]["traceLevels"].items():
        if level == "untraced":
            assert any(f"`{requirement}`" in result["message"]["text"] for result in run_log["results"]), requirement


@then(parsers.parse("the SARIF log gives the traced percentage as {percent:d}"))
def traced_percentage(run, percent):
    assert sarif_run(run.stdout)["properties"]["percentages"]["traced"] == percent


@then(parsers.parse('the summary leads with "{text}"'))
def summary_leads(run, text):
    assert run.stderr.splitlines()[0] == text


@then("the check exits non-zero, with the SARIF log on stdout")
def exits_non_zero(run):
    assert run.returncode != 0
    assert sarif_run(run.stdout)["results"]
