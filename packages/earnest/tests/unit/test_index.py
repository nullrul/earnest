"""Tests for earnest.index: the grammar, the Near-miss table and Reference resolution."""

import hashlib

import pytest

from earnest import adapters
from earnest.index import (
    COMMENT,
    GHERKIN,
    MARKDOWN,
    Id,
    Item,
    Line,
    Link,
    Region,
    Source,
    build_index,
    digest,
    split_lines,
)


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


def comments(*lines):
    return Source("src/a.py", COMMENT, tuple(Line(number, text) for number, text in lines))


def gherkin(*lines):
    return Source("tests/a.feature", GHERKIN, tuple(Line(number, text) for number, text in lines))


def test_a_comment_tag_covers_its_target_from_its_artifact_type_with_or_without_spaces():
    index = build_index([comments((3, "# see [impl->req~a~2] and [ utest -> req~b~1 ]"))])
    assert index.links == (
        Link("Covers", "impl", Id("req", "a", 2), "src/a.py", 3),
        Link("Covers", "utest", Id("req", "b", 1), "src/a.py", 3),
    )
    assert index.near_misses == ()


@pytest.mark.parametrize(
    ("source", "fix"),
    [
        (comments((1, "# [impl-req~x~1]")), "write `->`"),
        (comments((1, "# [ impl-req~x~1 ]")), "write `->`"),
        (comments((1, "# [impl->req~x]")), "append `~`"),
        (comments((1, "# [impl->req~x_y~1]")), "rewrite it as `[type->type~name~revision]`"),
        (comments((1, "# [impel->req~x~1]")), "use a known item type, such as `impl`"),
        (gherkin((1, "@stest:feat~Login~1")), "lower-case the name"),
        (gherkin((1, "@stest feat~login~1")), "put `:`"),
        (gherkin((1, "@stest:fet~login~1")), "use a known item type, such as `feat`"),
        (gherkin((1, "@stest:feat~login~1,")), "rewrite it as `@type:type~name~revision`"),
    ],
)
def test_a_tag_that_fails_its_surface_is_a_near_miss(source, fix):
    (miss,) = build_index([source]).near_misses
    assert miss.fix.startswith(fix)


def test_a_line_of_bracket_and_arrow_runs_parses_at_once():
    line = "# [" + "->~" * 2000 + " [impl->req~a~1]"
    assert build_index([comments((1, line))]).links == (Link("Covers", "impl", Id("req", "a", 1), "src/a.py", 1),)


def test_at_forms_are_tags_only_on_the_gherkin_surface():
    index = build_index(
        [
            gherkin((1, "@smoke @stest:feat~a~1")),
            comments((1, "/** @see req~x~1 */"), (2, "// @stest feat~y~1, and user@host:~/notes")),
        ]
    )
    assert [str(link.target) for link in index.links] == ["feat~a~1"]
    assert index.near_misses == ()


def test_each_written_id_resolves_once_by_type_and_name_then_by_revision():
    items = markdown("`feat~login~2`\n`req~login~1`\n")
    tags = comments(
        (1, "# [impl->feat~login~2] [impl->feat~login~1] [impl->feat~login~3]"),
        (2, "# [impl->feat~logn~2] [impl->feat~logn~2] [impl->dsn~login~1]"),
    )
    index = build_index([items, tags])
    feat = index.defined[Id("feat", "login", 2).key]
    assert {
        str(target): (resolution.item, resolution.status, resolution.closest)
        for target, resolution in index.resolutions.items()
    } == {
        "feat~login~2": (feat, "resolved", None),
        "feat~login~1": (feat, "outdated", None),
        "feat~login~3": (feat, "predated", None),
        "feat~logn~2": (None, "orphaned", Id("feat", "login", 2)),
        "dsn~login~1": (None, "orphaned", None),
    }


def body_hash(text, fenced=frozenset()):
    return build_index([markdown(text, fenced)]).items[0].body_hash


def sha(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_body_hash_ignores_blank_lines_and_trailing_whitespace():
    plain = "`req~a~1`\n\nWhen x, the s shall y.\n\n"
    noisy = "`req~a~1`\nWhen x, the s shall y.   \n\n\n\t\n"
    assert body_hash(plain) == body_hash(noisy)


def test_body_hash_ignores_key_lines_and_where_they_sit():
    above = "`req~a~1`\n\nCovers: feat~f~1\nNeeds: impl\n\nWhen x, the s shall y.\n"
    below = "`req~a~1`\n\nWhen x, the s shall y.\n\nNeeds: impl\n\nCovers: feat~f~1, feat~g~1\n"
    assert body_hash(above) == body_hash(below) == sha("When x, the s shall y.")


def test_body_hash_counts_fenced_lines():
    text = "`req~a~1`\n\nBody.\n\n```text\ncode\n```\n"
    assert body_hash(text, frozenset({5, 6, 7})) == sha("Body.\n```text\ncode\n```")
    assert body_hash(text, frozenset({5, 6, 7})) != body_hash("`req~a~1`\n\nBody.\n")


def test_fenced_key_like_line_stays_body_and_keys_nothing():
    text = "`req~a~1`\n\nBody.\n\n```\nCovers: feat~z~9\n```\n"
    index = build_index([markdown(text, frozenset({5, 6, 7}))])
    assert index.links == ()
    assert index.items[0].body_hash == sha("Body.\n```\nCovers: feat~z~9\n```")


def test_body_hash_changes_with_one_word():
    assert body_hash("`req~a~1`\n\nThe s shall y.\n") != body_hash("`req~a~1`\n\nThe s shall z.\n")


def test_item_without_body_hashes_the_empty_body():
    assert body_hash("`req~a~1`\n") == digest(b"") == sha("")


def test_each_item_hashes_its_own_span():
    index = build_index([markdown("`req~a~1`\n\nOne.\n\n`req~b~1`\n\nTwo.\n")])
    assert [item.body_hash for item in index.items] == [sha("One."), sha("Two.")]


def test_crlf_and_lf_bodies_hash_alike():
    lf = "`req~a~1`\n\nOne.\nTwo.\n"
    assert body_hash(lf.replace("\n", "\r\n")) == body_hash(lf)


def test_body_hash_is_the_sha256_of_utf8_lines_joined_by_lf_with_no_final_lf():
    text = "`req~a~1`\n\nalpha caf\u00e9\n\n  beta\n"
    expected = "sha256:" + hashlib.sha256("alpha caf\u00e9\n  beta".encode()).hexdigest()
    assert body_hash(text) == expected


def test_body_hash_removes_only_trailing_spaces_and_tabs():
    base = body_hash("`req~a~1`\n\nx y\n")
    assert body_hash("`req~a~1`\n\nx y \t \n") == base
    assert body_hash("`req~a~1`\n\n  x y\n") != base
    assert body_hash("`req~a~1`\n\nx  y\n") != base


def test_a_line_of_other_unicode_whitespace_is_not_blank():
    assert body_hash("`req~a~1`\n\na\n\u00a0\nb\n") == sha("a\n\u00a0\nb")
    assert body_hash("`req~a~1`\n\na\n\u00a0\nb\n") != body_hash("`req~a~1`\n\na\nb\n")


def test_body_hash_of_bad_bytes_uses_the_replacement_character(tmp_path):
    (tmp_path / "a.md").write_bytes(b"`req~a~1`\n\nCaf\xe9\n")
    index = build_index(adapters.scan(tmp_path, ["a.md"]))
    assert index.items[0].body_hash == sha("Caf\ufffd")


def tagged(tags, code, count, path="src/a.py", surface=COMMENT):
    """Return a source with a tag comment at each (line, id), code on the given lines, and count lines in all."""
    lines = tuple(Line(number, f"# [impl->{item}]") for number, item in tags)
    return Source(path, surface, lines, code_lines=frozenset(code), line_count=count)


A, B = Id("req", "a", 1), Id("req", "b", 1)


def test_region_runs_from_a_tag_to_the_next_tag():
    source = tagged([(1, "req~a~1"), (5, "req~b~1")], {2, 3, 4, 6, 7}, 8)
    assert build_index([source]).regions == (Region(A, "src/a.py", 1, 4), Region(B, "src/a.py", 5, 8))


def test_region_of_the_last_tag_ends_at_the_end_of_the_file():
    assert build_index([tagged([(3, "req~a~1")], {4, 5}, 6)]).regions == (Region(A, "src/a.py", 3, 6),)
    assert build_index([tagged([(3, "req~a~1")], {4, 5}, 0)]).regions == (Region(A, "src/a.py", 3, 3),)


def test_stacked_tags_share_the_region_that_follows():
    stacked = tagged([(1, "req~a~1"), (2, "req~b~1")], {3, 4}, 5)
    assert build_index([stacked]).regions == (Region(A, "src/a.py", 1, 5), Region(B, "src/a.py", 1, 5))
    on_code = tagged([(1, "req~a~1"), (2, "req~b~1")], {1, 3, 4}, 5)  # a code line on the tag's own line is code
    assert build_index([on_code]).regions == (Region(A, "src/a.py", 1, 1), Region(B, "src/a.py", 2, 5))


def test_repeated_tags_for_one_id_union_their_regions():
    joined = tagged([(1, "req~a~1"), (4, "req~a~1"), (7, "req~b~1")], {2, 3, 5, 6, 8, 9}, 9)
    assert build_index([joined]).regions == (Region(A, "src/a.py", 1, 6), Region(B, "src/a.py", 7, 9))
    apart = tagged([(1, "req~a~1"), (4, "req~b~1"), (7, "req~a~1")], {2, 3, 5, 6, 8, 9}, 9)
    assert build_index([apart]).regions == (
        Region(A, "src/a.py", 1, 3),
        Region(B, "src/a.py", 4, 6),
        Region(A, "src/a.py", 7, 9),
    )


def test_tags_in_different_files_never_share_a_region():
    one = tagged([(1, "req~a~1")], {2}, 3, path="src/a.py")
    two = tagged([(1, "req~a~1")], {2, 3}, 4, path="src/b.py")
    assert build_index([two, one]).regions == (Region(A, "src/a.py", 1, 3), Region(A, "src/b.py", 1, 4))


def test_gherkin_tags_have_regions():
    lines = (Line(1, "@stest:feat~f~1"),)
    source = Source("tests/a.feature", GHERKIN, lines, code_lines=frozenset({2, 3}), line_count=4)
    assert build_index([source]).regions == (Region(Id("feat", "f", 1), "tests/a.feature", 1, 4),)
