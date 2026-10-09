"""Tests for earnest.structural: the link rules and each requirement's trace level."""

import pytest

from earnest import structural
from earnest.index import Id, Index, Item, Link, NearMiss


FEAT = Id("feat", "f", 1)
REQ = Id("req", "r", 2)
ITEMS = (Item(FEAT, "docs/f.md", 1, ("req",)), Item(REQ, "docs/r.md", 5))
PARENT = Link("Covers", "req", FEAT, "docs/r.md", 7, owner=REQ)
IMPL = Link("Covers", "impl", REQ, "src/a.py", 3)
UTEST = Link("Covers", "utest", REQ, "tests/test_a.py", 3)


def index(*links, items=ITEMS, misses=(), parent=True):
    return Index(items, (PARENT, *links) if parent else links, misses)


def check(*links, items=ITEMS, misses=(), parent=True):
    """Check a requirement under a feat; the feat names no goal, and its own finding is not under test here."""
    found = structural.check(index(*links, items=items, misses=misses, parent=parent))
    return [finding for finding in found if finding.path != "docs/f.md"]


def located(rule, found):
    return [(finding.path, finding.line) for finding in found if finding.rule == rule]


def message(rule, found):
    (text,) = [finding.message for finding in found if finding.rule == rule]
    return text


def test_a_requirement_whose_needs_resolve_at_its_revision_is_traced():
    assert check(IMPL, UTEST) == []
    assert structural.traced(index(IMPL, UTEST)) == {"req~r~2": "traced"}


def test_a_need_with_no_cover_at_any_revision_is_a_gap_at_the_item():
    found = check(IMPL)
    assert located("earnest/gap", found) == [("docs/r.md", 5)]
    assert "`[utest->req~r~2]`" in message("earnest/gap", found)
    assert structural.traced(index(IMPL)) == {"req~r~2": "untraced"}


def test_a_cover_of_an_older_revision_is_outdated_not_a_gap():
    old = Link("Covers", "utest", Id("req", "r", 1), "tests/test_a.py", 9)
    found = check(IMPL, old)
    assert [finding.rule for finding in found] == ["earnest/outdated"]
    assert "write `req~r~2`" in message("earnest/outdated", found)
    assert structural.traced(index(IMPL, old)) == {"req~r~2": "untraced"}


def test_a_link_to_a_revision_above_the_items_is_predated():
    ahead = Link("Covers", "utest", Id("req", "r", 3), "tests/test_a.py", 9)
    assert located("earnest/predated", check(IMPL, ahead)) == [("tests/test_a.py", 9)]


def test_a_link_to_no_item_is_orphaned_and_names_the_closest_id_of_its_type():
    typo = Link("Covers", "utest", Id("req", "rr", 2), "tests/test_a.py", 9)
    other_type = Link("Covers", "impl", Id("dsn", "r", 2), "src/b.py", 4)
    found = check(IMPL, UTEST, typo, other_type)
    assert located("earnest/orphaned", found) == [("tests/test_a.py", 9), ("src/b.py", 4)]
    assert [finding.message for finding in found] == [
        "`req~rr~2` names no item: did you mean `req~r~2`?",
        "`dsn~r~2` names no item: define the item, or name one that exists",
    ]


def test_an_item_that_names_no_parent_is_orphaned():
    found = check(IMPL, UTEST, parent=False)
    assert located("earnest/orphaned", found) == [("docs/r.md", 5)]
    assert "add a `Covers:` line naming the `feat` it derives from" in message("earnest/orphaned", found)


@pytest.mark.parametrize("target", [Id("goal", "g", 1), REQ])
def test_a_covers_line_naming_no_item_of_the_parent_type_names_no_parent(target):
    items = (*ITEMS, Item(Id("goal", "g", 1), "docs/g.md", 1))
    wrong = Link("Covers", "req", target, "docs/r.md", 7, owner=REQ)
    found = check(IMPL, UTEST, wrong, items=items, parent=False)
    assert [(f.line, f.rule) for f in found if f.path == "docs/r.md"] == [
        (7, "earnest/unwanted"),
        (5, "earnest/orphaned"),
    ]


def test_a_cover_by_a_type_the_item_never_needs_is_unwanted_at_warning_level():
    itest = Link("Covers", "itest", REQ, "tests/test_b.py", 4)
    found = check(IMPL, UTEST, itest)
    assert located("earnest/unwanted", found) == [("tests/test_b.py", 4)]
    assert [finding.level for finding in found] == ["warning"]


def test_an_unwanted_cover_names_the_id_it_wrote():
    old = Link("Covers", "itest", Id("req", "r", 1), "tests/test_b.py", 4)
    assert message("earnest/unwanted", check(IMPL, UTEST, old)).startswith("`itest` covers `req~r~1` ")


def test_an_explicit_needs_line_replaces_the_default():
    items = (ITEMS[0], Item(REQ, "docs/r.md", 5, ("impl", "itest")))
    itest = Link("Covers", "itest", REQ, "tests/test_b.py", 4)
    assert located("earnest/unwanted", check(IMPL, UTEST, itest, items=items)) == [("tests/test_a.py", 3)]
    assert structural.traced(index(IMPL, itest, items=items)) == {"req~r~2": "traced"}


def test_a_second_item_with_the_same_id_is_a_duplicate():
    found = check(IMPL, UTEST, items=(*ITEMS, Item(REQ, "docs/other.md", 9)))
    assert located("earnest/duplicate", found) == [("docs/other.md", 9)]
    assert "already defined at docs/r.md:5" in message("earnest/duplicate", found)


def test_a_near_miss_is_a_finding_with_its_canned_fix():
    miss = NearMiss("src/a.py", 8, "[impl-req~r~2]", "write `->` between the artifact type and the id")
    (finding,) = check(IMPL, UTEST, misses=(miss,))
    assert (finding.rule, finding.subject) == ("earnest/near-miss", "[impl-req~r~2]")
    assert finding.message == "`[impl-req~r~2]` does not parse: " + miss.fix


def test_a_decision_names_its_drivers_and_they_count_toward_no_need():
    dsn = Id("dsn", "d", 1)
    items = (*ITEMS, Item(dsn, "docs/d.md", 1))
    drivers = Link("Drivers", "dsn", REQ, "docs/d.md", 3, owner=dsn)
    impl = Link("Covers", "impl", dsn, "src/b.py", 1)
    assert check(IMPL, UTEST, drivers, impl, items=items) == []
    assert located("earnest/orphaned", check(IMPL, UTEST, impl, items=items)) == [("docs/d.md", 1)]
