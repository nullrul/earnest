"""Python host adapter: `#` comments, through `tokenize`."""

import contextlib
import io
import re
import tokenize
from collections.abc import Iterator

from earnest.index import Line


def scan(text: str) -> tuple[Line, ...]:
    """Return the file's comments, each with its line number.

    A file that stops tokenizing, such as one an agent is halfway through editing, keeps what came before the error.
    """
    return tuple(Line(token.start[0], token.string) for token in _tokens(text) if token.type == tokenize.COMMENT)


# Tokens that stand for no code: a comment, a line break that ends no statement, and the indentation bookkeeping.
_LAYOUT = frozenset(
    {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
)


def code_lines(text: str) -> frozenset[int]:
    """Return the numbers of the lines that hold code: every line of each token that is no comment or layout.

    A string that spans lines holds code on each of them, and a file that stops tokenizing keeps what came before the
    error, as `scan` does.
    """
    found: set[int] = set()
    for token in _tokens(text):
        if token.type not in _LAYOUT:
            found.update(range(token.start[0], token.end[0] + 1))
    return frozenset(found)


def _tokens(text: str) -> Iterator[tokenize.TokenInfo]:
    spaced = re.sub(r"\r(?!\n)", " ", text)  # a lone `\r` would swallow the `#` after it; Git counts no line there
    with contextlib.suppress(tokenize.TokenError, SyntaxError):
        yield from tokenize.generate_tokens(io.StringIO(spaced).readline)
