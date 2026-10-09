"""Tests for the Markdown host adapter."""

import pytest

from earnest.adapters import markdown
from earnest.index import MARKDOWN, Source, build_index


EXAMPLES = """# Examples

`req~real~1`

```markdown
`req~quoted~2`
Covers: FR1.2
```

Needs: impl
"""


def test_fenced_lines_are_marked_fence_lines_included():
    lines, fenced = markdown.scan(EXAMPLES)
    assert len(lines) == 10
    assert fenced == {5, 6, 7, 8}


def test_id_shaped_text_in_a_fence_is_neither_an_item_nor_a_near_miss():
    lines, fenced = markdown.scan(EXAMPLES)
    index = build_index([Source("docs/a.md", MARKDOWN, lines, fenced)])
    assert [str(item.id) for item in index.items] == ["req~real~1"]
    assert index.items[0].needs == ("impl",)
    assert index.near_misses == ()


@pytest.mark.parametrize(
    ("opening", "inside"),
    [("~~~", "```"), ("~~~~", "~~~"), ("```", "``` more"), ("```", "    ```")],
)
def test_a_fence_closes_only_on_its_own_marker_at_least_as_long_alone_on_its_line(opening, inside):
    _, fenced = markdown.scan(f"{opening}\n{inside}\n`req~a~1`\n")
    assert fenced == {1, 2, 3}


def test_a_fence_may_sit_three_spaces_in_and_close_on_a_longer_marker():
    _, fenced = markdown.scan("   ~~~ text\n`req~a~1`\n  ~~~~  \nafter\n")
    assert fenced == {1, 2, 3}


def test_backticks_in_the_info_string_make_inline_code_not_a_fence():
    _, fenced = markdown.scan("```x``` is inline code\n`req~a~1`\n")
    assert fenced == set()


def test_an_unclosed_fence_runs_to_the_end_of_the_file():
    _, fenced = markdown.scan("text\n~~~\n`req~a~1`\n")
    assert fenced == {2, 3}
