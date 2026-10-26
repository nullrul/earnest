"""Steps for tests/features/evidence_check.feature: `earnest check --evidence` over seeded-change's M5 overlays."""

from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import FIXTURES, commit_on_main
from tests.sarif import located, read, record, results, run_earnest, write
from tests.steps.test_judge_check import maintainer_repository, summary_leads, trace_levels
from tests.steps.test_stage_status import repository_unchanged
from tests.steps.test_unit_status import maintainer_units_repository, plan_lists_units


scenarios("evidence_check.feature")

TESTS = "tests/test_auth.py"

# Steps of other step modules, bound here too, since only conftest.py's steps are shared.
given(
    parsers.parse(
        'the repo maintainer\'s "{name}" repository at its base commit, with the requirements stage approved'
    ),
    target_fixture="repo",
)(maintainer_repository)
given(
    parsers.parse(
        'the repo maintainer\'s "{name}" repository in its future-format units variant, with the requirements,'
        " the units and the first unit's functional design approved"
    ),
    target_fixture="repo",
)(maintainer_units_repository)
then("the repository is unchanged")(repository_unchanged)
then("the plan lists these units:")(plan_lists_units)
then("the SARIF log gives each requirement one trace level:")(trace_levels)
then(parsers.parse('the summary leads with "{text}"'))(summary_leads)


# The steps that change the repository or set the model.


@given("the repo maintainer's evidence overlay is committed")
def evidence_overlay_committed(repo):
    commit_on_main(repo, "seeded-change", "evidence")


@given("the repo maintainer's units evidence overlay is committed")
def units_evidence_overlay_committed(repo):
    commit_on_main(repo, "seeded-change", "evidence-units")


@given(parsers.parse('the judge is the stub model with the canned evidence verdicts of "{name}"'))
def stub_judge_evidence(monkeypatch, name):
    monkeypatch.setenv("EARNEST_JUDGE", f"stub:{FIXTURES / name / 'evidence-verdicts.json'}")


@given(parsers.parse('the coding agent has an uncommitted edit to the test of "{req}"'))
def uncommitted_test_edit(repo, req):
    lines = read(repo, TESTS).split("\n")
    tag = lines.index(f"# [utest->{req}]")
    assert lines[tag + 2].startswith("    assert "), lines[tag + 2]  # the tag, the def, then the first assert
    lines[tag + 2] += "  # edited"
    write(repo, TESTS, "\n".join(lines))


@given("the coding agent has run earnest check --evidence")
def agent_has_run_evidence_check(repo):
    run = run_earnest(repo, "check", "--evidence")
    assert run.returncode != 2, run.stderr  # the run happened: a missing flag or a tool that cannot run exits 2
    assert record(repo).get("evidence"), "the run wrote no evidence slot"


# The commands.


@when("the coding agent runs earnest check --evidence", target_fixture="run")
def agent_runs_evidence_check(repo):
    return run_earnest(repo, "check", "--evidence")


@when("the repo maintainer runs earnest plan", target_fixture="run")
def maintainer_runs_plan(repo):
    return run_earnest(repo, "plan")


# What the log holds.


@then(parsers.parse('the SARIF log holds no finding at "{path}" line {line:d}'))
def no_finding_at(run, path, line):
    assert (path, line) not in [located(result) for result in results(run)]


@then(parsers.re(r'the SARIF log holds an (?P<rule>earnest/\S+) finding at "(?P<path>[^"]+)" line (?P<line>\d+)'))
def finding_at(run, rule, path, line):
    assert (rule, path, int(line)) in [(result["ruleId"], *located(result)) for result in results(run)]


@then(parsers.re(r"the SARIF log holds no (?P<rule>earnest/\S+) finding"))
def no_rule_finding(run, rule):
    assert rule not in [result["ruleId"] for result in results(run)]
