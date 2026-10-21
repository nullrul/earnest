"""Unit tests for the EARS parser and `req-not-ears` (D2)."""

import pytest

from earnest import ears
from earnest.index import MARKDOWN, Source, build_index, split_lines


def kinds(body):
    sentence = ears.parse(body)
    assert sentence is not None
    return {clause.kind: clause.text for clause in sentence.clauses}


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("The system shall log in.", {"response": "log in"}),
        ("When a member logs in, the system shall greet them.", {"when": "a member logs in", "response": "greet them"}),
        (
            "While the shop is closed, the system shall refuse orders.",
            {"while": "the shop is closed", "response": "refuse orders"},
        ),
        ("If the card fails, then the system shall say so.", {"if": "the card fails", "response": "say so"}),
        ("Where coupons are on, the system shall take them.", {"where": "coupons are on", "response": "take them"}),
    ],
)
def test_each_template_parses_with_its_clauses(body, expected):
    assert kinds(body) == expected


def test_clauses_combine_in_order_where_while_when():
    body = "Where coupons are on, while the cart is open, when a code is typed, the system shall apply it."
    assert kinds(body) == {
        "where": "coupons are on",
        "while": "the cart is open",
        "when": "a code is typed",
        "response": "apply it",
    }
    assert ears.parse("While the cart is open, where coupons are on, the system shall apply it.") is None


def test_a_clause_span_points_into_the_sentence():
    sentence = ears.parse("When a member logs in, the system shall greet them.")
    assert sentence is not None
    for clause in sentence.clauses:
        assert sentence.text[clause.start : clause.end] == clause.text


def test_line_breaks_read_as_spaces():
    sentence = ears.parse("\nThe system shall lock a member out\nafter five failed logins.\n\n")
    assert sentence is not None
    assert sentence.text == "The system shall lock a member out after five failed logins."


@pytest.mark.parametrize(
    "body",
    [
        "Lockouts go into the audit log.",
        "The system shall log in. The system shall log out.",
        "The system shall log in",
        "",
        "When a member logs in the system shall greet them.",
        "The cache expires. Then the system shall reset.",
        "When a member logs in. Then, the system shall greet them.",
        "The system, when locked, shall reply.",
        "While the cache is warm. If it expires, then the system shall reset.",
    ],
)
def test_a_body_that_is_not_one_ears_sentence_does_not_parse(body):
    assert ears.parse(body) is None


def test_req_not_ears_sits_at_the_id_line_and_lists_the_five_templates_in_order():
    text = "# R\n\n`req~a~1`\n\nLockouts go.\n\n`req~b~1`\n\nThe system shall work.\n\n`feat~c~1`\n\nNot EARS.\n"
    index = build_index([Source("r.md", MARKDOWN, split_lines(text))])
    (found,) = ears.findings(index)
    assert (found.path, found.line, found.rule, found.subject) == ("r.md", 3, "earnest/req-not-ears", "req~a~1")
    places = [found.message.find(template) for template in ears.TEMPLATES]
    assert -1 not in places
    assert places == sorted(places)
