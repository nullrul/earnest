"""EARS parser: each `req` body as its clauses with their text spans, or a `req-not-ears` finding (D2)."""

import re
from collections.abc import Iterator
from dataclasses import dataclass

from earnest.index import Index
from earnest.reporter import Finding


CLAUSES = ("where", "while", "when", "if", "response")
# The five templates of D2, in its order.
TEMPLATES = (
    "The system shall response.",
    "When trigger, the system shall response.",
    "While state, the system shall response.",
    "If condition, then the system shall response.",
    "Where feature, the system shall response.",
)
# The grammar's fixed keyword order; a clause holds no comma, so the comma after it ends it.
# shortcut: a precondition with a comma inside it does not parse; read nested commas if a real spec needs them
_EARS = re.compile(
    r"(?:Where (?P<where>[^,]+), )?"
    r"(?:(?<![^ ])[Ww]hile (?P<while>[^,]+), )?"
    r"(?:(?<![^ ])[Ww]hen (?P<when>[^,]+), |(?<![^ ])[Ii]f (?P<if>[^,]+), then )?"
    r"(?<![^ ])[Tt]he (?P<system>(?:(?! shall )[^.!?]|[.!?](?! ))+) shall (?P<response>[^.!?]*(?:[.!?](?! )[^.!?]*)*)\."
)


@dataclass(frozen=True)
class Clause:
    """One clause of an EARS sentence: its kind and its text, from `start` to `end` in the sentence."""

    kind: str
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Sentence:
    """A parsed `req` body: the sentence, its line breaks read as spaces, and its clauses in the grammar's order."""

    text: str
    clauses: tuple[Clause, ...]


def parse(body: str) -> Sentence | None:
    """Parse a `req` body as one EARS sentence, or return None when it is not one.

    Line breaks and blank lines read as spaces, and runs of whitespace as one space. A sentence that holds a second
    sentence, a `shall` with no system before it, or no final full stop is not one.
    """
    text = " ".join(body.split())
    match = _EARS.fullmatch(text)
    if match is None:
        return None
    clauses = tuple(
        Clause(kind, match.group(kind), match.start(kind), match.end(kind))
        for kind in CLAUSES
        if match.group(kind) is not None
    )
    return Sentence(text, clauses)


def findings(index: Index) -> Iterator[Finding]:
    """Yield `req-not-ears` at the id line of each defined `req` whose body is not one EARS sentence."""
    templates = "; ".join(f'"{template}"' for template in TEMPLATES)
    for item in index.defined.values():
        if item.id.type == "req" and parse(item.body) is None:
            message = f"`{item.id}` is not one EARS sentence: rewrite its body as one of the five templates {templates}"
            yield Finding(item.path, item.line, "earnest/req-not-ears", str(item.id), message)
