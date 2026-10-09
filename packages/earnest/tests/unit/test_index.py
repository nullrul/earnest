"""Tests for earnest.index: the grammar, the Near-miss table and Reference resolution."""

import pytest

from earnest.index import MARKDOWN, Id, Item, Line, Source, build_index, split_lines


def markdown(text, fenced=frozenset()):
    return Source("docs/a.md", MARKDOWN, split_lines(text), fenced)


def test_lines_split_at_each_newline_alone_as_git_counts_them():
    assert split_lines("a\rb\x0bc\x0cd\x1ce\x85f\ng\n") == (Line(1, "a\rb\x0bc\x0cd\x1ce\x85f"), Line(2, "g"))
    assert split_lines("a\n\nb") == (Line(1, "a"), Line(2, ""), Line(3, "b"))
    assert split_lines("") == ()


def test_an_item_runs_from_its_id_line_to_the_next_id_line_or_heading():
    text = (
        "`req~a~2`\n\nWhen x, the s shall y.\n\nNeeds: impl, itest\nCovers: feat~f~1, feat~g~1\n"
        "### `req~b~1`\n\nCovers: feat~f~1\n   ## Notes\n\nCovers: feat~h~1\n"
    )
    index = build_index([markdown(text)])
    assert index.items == (
        Item(Id("req", "a", 2), "docs/a.md", 1, ("impl", "itest")),
        Item(Id("req", "b", 1), "docs/a.md", 7),
    )
    assert [(link.owner, str(link.target), link.line) for link in index.links] == [
        (Id("req", "a", 2), "feat~f~1", 6),
        (Id("req", "a", 2), "feat~g~1", 6),
        (Id("req", "b", 1), "feat~f~1", 9),
    ]
    assert index.near_misses == ()


@pytest.mark.parametrize("line", ["`req~b~1`", "## `req~b~1`", "   ## `req~b~1`", "#\t`req~b~1`", "## `req~b~1` ##"])
def test_an_id_line_stands_alone_or_in_an_atx_heading_whose_closing_run_is_no_text(line):
    index = build_index([markdown(f"{line}\nCovers: feat~f~1\n")])
    assert [str(link.owner) for link in index.links] == ["req~b~1"]
    assert index.near_misses == ()


def test_text_after_a_backticked_token_that_is_no_id_is_body():
    index = build_index([markdown("`req~a~1`\n`~/.config/app` holds the cache\nCovers: feat~f~1\n")])
    assert [str(link.target) for link in index.links] == ["feat~f~1"]
    assert index.near_misses == ()


def test_a_lone_backticked_token_that_is_no_id_is_body():
    index = build_index([markdown("`req~a~1`\n`~/.config`\nCovers: feat~f~1\n")])
    assert [str(link.target) for link in index.links] == ["feat~f~1"]
    assert index.near_misses == ()


@pytest.mark.parametrize(
    ("line", "fix"),
    [
        ("`req~x`", "append `~` and the item's current revision"),
        ("### `req~Login~1`", "lower-case the name"),
        ("`req~login_rate~1`", "rewrite it as `type~name~revision` in backticks"),
        ("`req~b~1` Login rate limit", "put the id alone on its line and move the text into the body"),
        ("## `req~b~1` Login rate limit", "put the id alone on its line and move the text into the body"),
        ("`rq~rate-limit~1`", "use a known item type, such as `req`"),
        ("`Req~a~1`", "rewrite it as `type~name~revision` in backticks"),
        ("`rq~x~1` text", "use a known item type, such as `req`"),
    ],
)
def test_a_malformed_id_line_is_a_near_miss_that_ends_the_item_above(line, fix):
    index = build_index([markdown(f"`req~a~1`\n{line}\nCovers: feat~f~1\n")])
    assert [str(item.id) for item in index.items] == ["req~a~1"]
    (miss,) = index.near_misses
    assert miss.line == 2
    assert miss.fix.startswith(fix)
    assert index.links == ()


@pytest.mark.parametrize(
    ("line", "text", "fix"),
    [
        ("Covers: feat~f~1, FR1.2", "FR1.2", "lower-case it, turn dots into hyphens"),
        ("Covers: feat~x", "feat~x", "append `~`"),
        ("Delivers: req~Login~1", "req~Login~1", "lower-case the name"),
        ("Depends: task~set_up~1", "task~set_up~1", "rewrite it as `type~name~revision`"),
        ("Covers: fet~f~1", "fet~f~1", "use a known item type, such as `feat`"),
        ("Covers: @stest:feat~f~1", "@stest:feat~f~1", "rewrite it as `type~name~revision`"),
        ("Needs: impl, utst", "utst", "use a known item type, such as `utest`"),
        ("Needs: Impl", "Impl", "rewrite it as item types"),
        ("Override: req~a~1 implemented 3f9c2a1, why", "req~a~1 implemented 3f9c2a1, why", "rewrite it as `type~"),
        ("Covers:", "Covers:", "name at least one id, separated by `, `, with no empty entry"),
        ("Covers: feat~f~1,", "Covers: feat~f~1,", "name at least one id"),
        ("Covers: , feat~f~1", "Covers: , feat~f~1", "name at least one id"),
        ("Covers: feat~f~1,feat~g~1", "Covers: feat~f~1,feat~g~1", "name at least one id"),
        ("Needs: impl,utest", "Needs: impl,utest", "name at least one id"),
        ("Needs: impl utest", "Needs: impl utest", "name at least one id"),
    ],
)
def test_a_key_line_value_that_fails_its_grammar_is_a_near_miss(line, text, fix):
    index = build_index([markdown(f"`req~a~1`\n{line}\n")])
    (miss,) = index.near_misses
    assert (miss.line, miss.text) == (2, text)
    assert miss.fix.startswith(fix)


@pytest.mark.parametrize(
    ("line", "key"),
    [
        ("**Covers:** feat~f~1", "Covers"),
        ("covers: feat~f~1", "Covers"),
        ("Covers:feat~f~1", "Covers"),
        ("_Needs_: impl", "Needs"),
        ("Delivers :  req~a~1", "Delivers"),
        ("- Covers: feat~f~1", "Covers"),
        ("  Depends: task~t~1", "Depends"),
        ("> Needs: impl", "Needs"),
    ],
)
def test_a_key_not_written_exactly_is_a_near_miss_that_names_the_key(line, key):
    index = build_index([markdown(f"`req~a~1`\n{line}\n")])
    (miss,) = index.near_misses
    assert miss.text == line
    assert miss.fix == (
        f"write the key exactly as `{key}: `, with a capital, no formatting and one space after the colon"
    )
    assert index.links == ()


def test_a_key_that_only_unicode_case_folding_would_match_is_body():
    index = build_index([markdown("`req~a~1`\nNeed\u017f: impl\n")])  # U+017F, the long s
    assert index.items[0].needs is None
    assert index.near_misses == ()


def test_the_entries_beside_an_empty_one_still_link():
    index = build_index([markdown("`req~a~1`\nCovers: feat~f~1,\n")])
    assert [str(link.target) for link in index.links] == ["feat~f~1"]


def test_a_valid_needs_line_and_an_override_line_parse_cleanly():
    text = "`req~a~1`\nNeeds: impl, utest\nOverride: req~a~1 implemented at 3f9c2a1, lives in the gateway\n"
    index = build_index([markdown(text)])
    assert index.items[0].needs == ("impl", "utest")
    assert index.near_misses == ()


def test_fenced_lines_never_start_end_or_key_an_item():
    text = "`req~a~1`\n~~~\n# heading\n`req~b~1`\nCovers: FR1.2\n~~~\nCovers: feat~f~1\n"
    index = build_index([markdown(text, frozenset({2, 3, 4, 5, 6}))])
    assert [str(item.id) for item in index.items] == ["req~a~1"]
    assert [str(link.target) for link in index.links] == ["feat~f~1"]
    assert index.near_misses == ()


def test_defined_keeps_the_first_item_of_each_type_and_name():
    index = build_index([markdown("`req~a~1`\n`req~a~2`\n")])
    assert len(index.items) == 2
    assert index.defined[Id("req", "a", 2).key].line == 1


def test_a_revision_too_long_to_be_an_int_is_a_near_miss_not_a_crash():
    digits = "9" * 5000
    index = build_index([markdown(f"`req~a~{digits}`\n`req~b~1`\nCovers: feat~f~{digits}\n")])
    assert [str(item.id) for item in index.items] == ["req~b~1"]
    assert [miss.line for miss in index.near_misses] == [1, 3]
    assert index.links == ()


def test_crlf_line_ends_parse_like_newlines():
    text = "`req~a~1`\r\nNeeds: impl\r\nCovers: feat~f~1\r\n"
    crlf = build_index([markdown(text)])
    assert crlf == build_index([markdown(text.replace("\r\n", "\n"))])
    assert crlf.items[0].needs == ("impl",)
    assert [str(link.target) for link in crlf.links] == ["feat~f~1"]
    assert crlf.near_misses == ()
