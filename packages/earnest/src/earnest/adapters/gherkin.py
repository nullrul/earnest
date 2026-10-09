"""Gherkin host adapter: the `@` tag lines outside doc strings, each without its comment."""

import re

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
    tags: list[Line] = []
    doc_string = ""
    after_step = False
    for line in split_lines(text):
        stripped = line.text.strip()
        if doc_string:
            doc_string = "" if stripped.startswith(doc_string) else doc_string
        elif after_step and stripped.startswith(_DOC_STRINGS):
            doc_string = stripped[:3]
        elif stripped.startswith("@"):
            tags.append(Line(line.number, re.split(r"\s#", line.text, maxsplit=1)[0]))
        if stripped and not stripped.startswith("#"):
            after_step = stripped.startswith(_STEPS)
    return tuple(tags)
