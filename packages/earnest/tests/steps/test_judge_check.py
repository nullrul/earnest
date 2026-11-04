"""Steps for tests/features/judge_check.feature: the EARS parse, the stub judge, overrides and the judge cache."""

from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import commit_on_main, location_cell, model_id, prompt_hash
from tests.sarif import SHARD, read, record, results, rows, run_earnest, sarif_run


scenarios("judge_check.feature")


def finding(run, rule):
    (found,) = [result for result in results(run) if result["ruleId"] == rule]
    return found


def observations(run):
    return sarif_run(run.stdout)["properties"]["observations"]


def cell(observation, column):
    return location_cell(observation["location"]) if column == "location" else observation[column]


def same_rows(found, datatable):
    """Assert the observations are the table's rows, in order, compared on the table's columns."""
    table = rows(datatable)
    columns = list(table[0])
    actual = [tuple(cell(observation, column) for column in columns) for observation in found]
    assert actual == [tuple(row[column] for column in columns) for row in table]


# Background and the steps that change the repository.


@given(
    parsers.parse(
        'the repo maintainer\'s "{name}" repository at its base commit, with the requirements stage approved'
    ),
    target_fixture="repo",
)
def maintainer_repository(fixture_repo, name):
    repo = fixture_repo(name)
    assert "**Event**: GATE_APPROVED" in read(repo, SHARD)
    return repo


@given("the repo maintainer's overrides are committed")
def overrides_committed(repo):
    commit_on_main(repo, "seeded-change", "override")


@given("the repo maintainer's change under the overrides is committed")
def change_under_overrides_committed(repo):
    commit_on_main(repo, "seeded-change", "override-change")


@when("the coding agent runs earnest check --judge", target_fixture="run")
def agent_runs_judge_check(repo):
    return run_earnest(repo, "check", "--judge")


@when("the coding agent runs earnest check --judge twice", target_fixture="runs")
def agent_runs_judge_check_twice(repo):
    return [run_earnest(repo, "check", "--judge"), run_earnest(repo, "check", "--judge")]


# What the log and the record hold.


@then(parsers.parse('the earnest/req-not-ears finding names "{req}" and lists these templates:'))
def not_ears_lists_templates(run, req, datatable):
    text = finding(run, "earnest/req-not-ears")["message"]["text"]
    assert req in text
    places = [text.find(row["template"]) for row in rows(datatable)]
    assert -1 not in places, text
    assert places == sorted(places), text


@then(parsers.parse('the SARIF log holds no observation of record for "{req}"'))
def no_observation_for(run, req):
    assert req not in {observation["subject"] for observation in observations(run)}


@then("the earnest/judge-not-satisfied finding carries this observation:")
def not_satisfied_carries(run, datatable):
    expected = {row["field"]: row["value"] for row in rows(datatable)}
    (observation,) = finding(run, "earnest/judge-not-satisfied")["properties"]["observations"]
    assert {column: cell(observation, column) for column in expected} == expected


@then("the summary lists the finding with its reasoning")
def summary_lists_reasoning(run):
    (observation,) = finding(run, "earnest/judge-not-satisfied")["properties"]["observations"]
    lines = [line for line in run.stderr.splitlines() if "earnest/judge-not-satisfied" in line]
    assert len(lines) == 1, run.stderr
    assert observation["reasoning"] in lines[0]


@then("the earnest/judge-uncalibrated finding names the stub model's id and the prompt hash")
def uncalibrated_names_model(run):
    text = finding(run, "earnest/judge-uncalibrated")["message"]["text"]
    assert model_id("seeded-change") in text
    assert prompt_hash() in text


@then("the SARIF log gives the stub model's id and the prompt hash in the run's invocation")
def invocation_names_model(run):
    (invocation,) = sarif_run(run.stdout)["invocations"]
    assert invocation["properties"]["model"] == model_id("seeded-change")
    assert invocation["properties"]["prompt"] == prompt_hash()


@then("the SARIF log gives each requirement one trace level:")
def trace_levels(run, datatable):
    expected = {row["requirement"]: row["level"] for row in rows(datatable)}
    assert sarif_run(run.stdout)["properties"]["traceLevels"] == expected


@then(parsers.parse("the SARIF log gives the judged percentage as {percent:d}"))
def judged_percentage(run, percent):
    assert sarif_run(run.stdout)["properties"]["percentages"]["judged"] == percent


@then(parsers.parse('the summary leads with "{text}"'))
def summary_leads(run, text):
    assert run.stderr.splitlines()[0] == text


@then("the SARIF log holds exactly these observations of record:")
def exact_observations(run, datatable):
    same_rows(observations(run), datatable)


@then(parsers.parse('the observation of record for "{req}" "{question}" gives the reasoning "{reasoning}"'))
def observation_reasoning(run, req, question, reasoning):
    (observation,) = [each for each in observations(run) if (each["subject"], each["question"]) == (req, question)]
    assert observation["reasoning"] == reasoning


@then("the judge cache holds exactly these questions:")
def cache_holds(repo, datatable):
    entries = record(repo)["judge"]["cache"].values()
    actual = sorted((entry["item"], entry["question"]) for entry in entries)
    assert actual == sorted((row["subject"], row["question"]) for row in rows(datatable))


@then(
    parsers.re(
        r'the (?P<rule>earnest/override-(?:expired|drift)) finding names "(?P<first>[^"]+)"'
        r' and the (?:current revision|commit) "(?P<second>[^"]+)"'
    )
)
def override_finding_names(run, rule, first, second):
    text = finding(run, rule)["message"]["text"]
    assert first in text
    assert second in text


@then("the earnest/override-drift finding carries these observations:")
def drift_carries(run, datatable):
    same_rows(finding(run, "earnest/override-drift")["properties"]["observations"], datatable)
