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


def _tokens(text: str) -> Iterator[tokenize.TokenInfo]:
    spaced = re.sub(r"\r(?!\n)", " ", text)  # a lone `\r` would swallow the `#` after it; Git counts no line there
    with contextlib.suppress(tokenize.TokenError, SyntaxError):
        yield from tokenize.generate_tokens(io.StringIO(spaced).readline)
