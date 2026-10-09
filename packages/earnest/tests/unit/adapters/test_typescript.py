"""Tests for the TypeScript host adapter."""

import pytest

from earnest.adapters import typescript
from earnest.index import Line


def test_line_and_block_comments_are_read_line_by_line():
    lines = typescript.scan("// [impl->req~a~1]\nconst x = 1; /* one\n[impl->req~b~1] */\n")
    assert lines == (Line(1, "// [impl->req~a~1]"), Line(2, "/* one"), Line(3, "[impl->req~b~1] */"))


def test_tag_shaped_text_inside_strings_and_template_literals_is_text():
    text = (
        'const url = "https://example.com/[impl->req~a~1]";\n'
        "const note = 'a // b';\n"
        "const t = `line // [impl->req~b~1]\n${f(x)} // still text`;\n"
        "// [impl->req~c~1]\n"
    )
    assert typescript.scan(text) == (Line(5, "// [impl->req~c~1]"),)


@pytest.mark.parametrize(
    "code",
    [
        's = s.replace(/`/g, "");',
        "const trail = /\\/*$/;",
        "return /\\/*/.test(s);",
        "const quote = /[/`]/;",
    ],
)
def test_a_regular_expression_literal_opens_no_template_or_comment(code):
    text = f'{code}\nconst s = "[impl->req~x~1]";\n// [impl->req~a~1]\n'
    assert typescript.scan(text) == (Line(3, "// [impl->req~a~1]"),)


@pytest.mark.parametrize(
    "code",
    [
        "const half = total / 2;",
        "const ratio = (a + b) / c;",
        "i++ / 2;",
        "x! / 2;",
        "obj.return / 2;",
        "return <p>Loading</p>;",
    ],
)
def test_a_slash_that_divides_or_closes_a_jsx_tag_opens_no_regular_expression(code):
    assert typescript.scan(f"{code} // [impl->req~a~1]\n") == (Line(1, "// [impl->req~a~1]"),)


@pytest.mark.parametrize("quote", ["'", '"', "`"])
def test_a_string_continued_by_a_backslash_under_crlf_ends_on_its_next_line(quote):
    lf = f"const s = {quote}a\\\nb{quote}; // [impl->req~a~1]\n// [impl->req~b~1]\n"
    assert typescript.scan(lf) == (Line(2, "// [impl->req~a~1]"), Line(3, "// [impl->req~b~1]"))
    crlf = typescript.scan(lf.replace("\n", "\r\n"))
    assert tuple(Line(line.number, line.text.rstrip()) for line in crlf) == typescript.scan(lf)
