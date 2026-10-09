"""Markdown host adapter: the lines of a stage artifact, with its code fences marked."""

import re

from earnest.index import Line, split_lines


_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")


def scan(text: str) -> tuple[tuple[Line, ...], frozenset[int]]:
    """Return every line, and the lines inside code fences, fence lines included; an unclosed fence runs to the end.

    A fence opens on three or more backticks or tildes after up to three spaces, and a backtick fence's info string
    holds no backtick. It closes on the same character, at least as many, with nothing after them.
    """
    lines = split_lines(text)
    fenced: set[int] = set()
    fence = ""
    for line in lines:
        marker = _FENCE.fullmatch(line.text)
        if fence:
            fenced.add(line.number)
            if marker and marker.group(1).startswith(fence) and not marker.group(2).strip():
                fence = ""
        elif marker and not (marker.group(1).startswith("`") and "`" in marker.group(2)):
            fenced.add(line.number)
            fence = marker.group(1)
    return lines, frozenset(fenced)
