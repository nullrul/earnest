"""TypeScript host adapter: `//` and block comments outside string, template and regular expression literals."""

import re

from earnest.index import Line


# ponytail: a template literal is one string up to its next backtick, so a template nested inside `${...}` ends the
# outer one early and a comment inside `${...}` reads as text; JSX text reads as code, so `//` there opens a comment.
# A TypeScript parser lifts both limits, at the cost of a dependency.
_TOKEN = re.compile(
    r"(?P<comment>//[^\n]*|/\*[\s\S]*?(?:\*/|\Z))"
    r"|(?P<literal>'(?:\\(?:\r\n|[\s\S])|[^'\\\n])*'?|\"(?:\\(?:\r\n|[\s\S])|[^\"\\\n])*\"?|`(?:\\[\s\S]|[^`\\])*`?)"
    r"|(?P<word>[\w$]+)|(?P<space>\s+)|(?P<step>\+\+|--)|(?P<other>[\s\S])",
)
# Possessive: each alternative opens on a character of its own, so a literal that never closes costs one pass.
# ponytail: that pass may run to the end of the line from each `/` that could open a regular expression, so a line of
# unclosed ones such as `(/a[/a[/a[` scans in time quadratic in its length; the TypeScript parser above lifts it too.
_REGEX = re.compile(r"/(?:\\.|\[(?:\\.|[^\]\\\n])*+\]|[^/\\\n\[])++/[A-Za-z]*+")
_BEFORE_REGEX = frozenset(
    {"return", "typeof", "instanceof", "case", "in", "of", "new", "delete", "void", "throw", "yield", "await"}
)
_CLOSERS = frozenset({")", "]", "}"})


def scan(text: str) -> tuple[Line, ...]:
    """Return the comment lines outside string, template and regular expression literals, one per physical line.

    A `/` starts a regular expression unless the token before it ends an operand or is `<`, as in the JSX closing tag
    `</p>`. A name, a number, a literal, `)`, `]`, `}`, `++` and `--` end an operand; a keyword such as `return` does
    not, unless it follows `.` or `?.` as a property name; and a postfix `!` leaves the state as it was.
    """
    comments: list[Line] = []
    operand = False  # whether the last token that is no comment or space ends an operand, so a `/` after it divides
    previous = ""  # the last token that is no comment or space
    number = 1  # the line the next token starts on
    position = 0
    while token := _TOKEN.match(text, position):
        kind, value = token.lastgroup, token.group()
        if value == "/" and not operand and previous != "<" and (regex := _REGEX.match(text, position)):
            token, kind, value = regex, "literal", regex.group()
        if kind == "comment":
            comments.extend(Line(number + offset, part) for offset, part in enumerate(value.split("\n")))
        elif kind != "space":
            if value != "!" or text.startswith("=", token.end()):  # a postfix `!` leaves the state as it was
                operand = _ends_operand(kind, value, previous)
            previous = value
        number += value.count("\n")
        position = token.end()
    return tuple(comments)


def _ends_operand(kind: str | None, value: str, previous: str) -> bool:
    if kind == "word":
        return previous == "." or value not in _BEFORE_REGEX  # after `.` or `?.`, even a keyword is a property name
    return kind in {"literal", "step"} or value in _CLOSERS
