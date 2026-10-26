"""Integration: `check --evidence` runs mutmut for real on seeded-change's evidence overlay."""

from earnest import adapters, git, impact, plan, structural
from earnest.index import build_index
from tests.conftest import commit_on_main


def test_pin_the_run_kills_the_five_mutants_of_req_rate_limit(fixture_repo):
    """A pin, green from the start: `req~rate-limit~1` is evidenced by five killed mutants, not by a skipped run."""
    repo = commit_on_main(fixture_repo("seeded-change"), "seeded-change", "evidence")
    files = git.work_tree_files(repo)
    index = build_index(adapters.scan(repo, files))
    levels = structural.traced(index, plan.produces([plan.intent(each) for each in plan.load(repo, files)]))
    found = impact.evidence(repo, index, levels)
    region = [mutant for mutant in found.mutants if mutant.key.rpartition(".")[2].startswith("x_count_failed_logins_")]
    assert sorted(mutant.key.rpartition(".")[2] for mutant in region) == [
        f"x_count_failed_logins__mutmut_{n}" for n in range(1, 6)
    ]
    assert {(mutant.path, mutant.line) for mutant in region} == {("src/checkout/auth.py", 10)}
    assert all(mutant.code in impact._KILLED for mutant in region)
