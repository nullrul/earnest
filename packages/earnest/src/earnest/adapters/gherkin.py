"""Gherkin host adapter: the `@` tag lines outside doc strings, each without its comment."""

import re
from collections.abc import Iterator

from earnest.index import Line, split_lines


_DOC_STRINGS = ('"""', "```")
_STEPS = ("Given ", "When ", "Then ", "And ", "But ", "* ")


def scan(text: str) -> tuple[Line, ...]:
    """Return the `@` tag lines, each cut at its first `#` after whitespace, where a comment opens, as Gherkin cuts it.

    A doc string opens on a line whose stripped text starts with its delimiter, three double quotes or three backticks,
    right after a step, blank lines and comments aside, and closes on the next line that starts with the same delimiter.
    Its lines are text, never tags, and a delimiter line anywhere else, such as in a description, is text too.
    """
    # ponytail: step keywords are English only, so a feature written in another `# language:` opens no doc strings; the
    # official Gherkin parser knows every language's keywords, at the cost of a dependency.
    return tuple(
        Line(line.number, re.split(r"\s#", line.text, maxsplit=1)[0])
        for line, kind in _classified(text)
        if kind == "tag"
    )


def code_lines(text: str) -> frozenset[int]:
    """Return the numbers of the lines that hold code: every line that is no tag line, comment or blank.

    The lines of a doc string, its delimiters included, are code, and a `#` or `@` line inside one is text.
    """
    return frozenset(line.number for line, kind in _classified(text) if _holds_code(line, kind))


def _holds_code(line: Line, kind: str) -> bool:
    stripped = line.text.strip()
    return bool(stripped) and kind != "tag" and (kind == "doc" or not stripped.startswith("#"))


def _classified(text: str) -> Iterator[tuple[Line, str]]:
    """Yield each line with its kind: `tag` for a tag line, `doc` for a doc-string line, else `plain`."""
    doc_string = ""
    after_step = False
    for line in split_lines(text):
        stripped = line.text.strip()
        kind = "plain"
        if doc_string:
            kind = "doc"
            doc_string = "" if stripped.startswith(doc_string) else doc_string
        elif after_step and stripped.startswith(_DOC_STRINGS):
            kind = "doc"
            doc_string = stripped[:3]
        elif stripped.startswith("@"):
            kind = "tag"
        yield line, kind
        if stripped and not stripped.startswith("#"):
            after_step = stripped.startswith(_STEPS)
