"""Grammar and index: items, links and near-misses from the lines the host adapters hand over."""

import difflib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property


MARKDOWN = "markdown"
COMMENT = "comment"
GHERKIN = "gherkin"
TYPES = ("tenet", "goal", "feat", "req", "dsn", "unit", "task", "impl", "utest", "itest", "stest")
KEYS = ("Needs", "Covers", "Drivers", "Delivers", "Depends", "Override")

_TYPE = f"({'|'.join(TYPES)})"
_ID = rf"{_TYPE}~([a-z0-9-]+)~([1-9][0-9]{{0,8}})"  # nine digits at most, far under int()'s 4300-digit limit
_ID_ENTRY = re.compile(_ID)
_TYPE_ENTRY = re.compile(_TYPE)
_ATX = r"#{1,6}(?:[ \t]+|$)"  # the marks that open an ATX heading, after up to three spaces
_HEADING = re.compile(rf" {{0,3}}{_ATX}")
# An id-line candidate: a backticked token that opens with a word of letters and a `~`, alone on its line or after
# heading marks, with text after it or none, where a heading's closing run of `#` is no text. Any other backticked
# token, such as `~/.config`, is body text.
_ID_LINE = re.compile(rf" {{0,3}}({_ATX})?`([A-Za-z]+~[^`]*)`(?(1)(?:[ \t]+#+$)?)(.*)")
_KEY_NAME = f"({'|'.join(KEYS)})"
# A key line as written, or decorated: indentation, list and quote markers and emphasis may come before its key. Its
# letters fold case in ASCII alone, so a letter such as the long s, which Unicode folds to `s`, stands in for none.
_KEY = re.compile(rf"[ \t]*(?:(?:[-*+]|[0-9]+\.)[ \t]+|>[ \t]*)*[*_]*{_KEY_NAME}[*_]*[ \t]*:", re.IGNORECASE | re.ASCII)
_KEY_LINE = re.compile(rf"{_KEY_NAME}:(?: (\S.*))?")
_OVERRIDE = re.compile(rf"{_ID} (?:implemented|tested) at [0-9a-f]+,.+")
_SEPARATORS = re.compile(r"[\s,]+")
_TYPE_SLOT = re.compile(r"(?:^|[\[@:>]\s*)([a-z]+)(?=\s*(?:->|[:~]|$))")

# The Near-miss table of the logic design, in order, for text that fails the grammar of its place: the first row that
# applies at that place (None for every place) and whose pattern fits gives the canned fix. `_keys` checks the key and
# empty-value rows on a whole key line before its entries reach this table, and `_fix` the unknown-type row after it.
_FIXES: tuple[tuple[str | None, re.Pattern[str], str], ...] = (
    (None, re.compile(r"\[\s*[a-z]+\s*-[^>]"), "write `->` between the artifact type and the id"),
    (None, re.compile(r"(?:^|->|:)\s*[A-Za-z]+~[^~\s\]]+\s*\]?$"), "append `~` and the item's current revision"),
    (None, re.compile(r"(?<![a-z])[a-z]+~[^~\sA-Z]*[A-Z][^~\s]*~"), "lower-case the name"),
    (GHERKIN, re.compile(r"^@[a-z]+[ \t]+[a-z]+~"), "put `:` between the artifact type and the id"),
    (
        None,
        re.compile(r"^[A-Z]+-?[0-9]+(?:\.[0-9]+)*$"),
        "lower-case it, turn dots into hyphens, and add the type and the revision, so `FR1.2` becomes `req~fr1-2~1`",
    ),
    ("id line", re.compile(rf"^{_ID}[ \t]"), "put the id alone on its line and move the text into the body"),
)
_KEY_FIX = "write the key exactly as `{}: `, with a capital, no formatting and one space after the colon"
_EMPTY_FIX = "name at least one id, separated by `, `, with no empty entry"
_NAME_RULE = "a name of lower-case letters, digits and hyphens, and a revision from 1"
_FORMS = {
    "id line": f"`type~name~revision` in backticks, alone on its line or after heading marks, with {_NAME_RULE}",
    "id": f"`type~name~revision`, with {_NAME_RULE}",
    "Needs": "item types separated by a comma and a space, such as `impl, utest`",
    "Override": f"`type~name~revision implemented at commit, reason`, or `tested` for tests, with {_NAME_RULE}",
}


@dataclass(frozen=True)
class Line:
    """One line a host adapter hands to the grammar, numbered from 1."""

    number: int
    text: str


@dataclass(frozen=True)
class Source:
    """One listed file as its host adapter saw it.

    For Markdown, `lines` holds every line and `fenced` the lines inside code fences. For the comment and Gherkin
    surfaces, `lines` holds the comment or tag lines.
    """

    path: str
    surface: str
    lines: tuple[Line, ...]
    fenced: frozenset[int] = frozenset()


@dataclass(frozen=True)
class Id:
    """An item id: type, name and revision."""

    type: str
    name: str
    revision: int

    @property
    def key(self) -> tuple[str, str]:
        """Return the type and name, which pick the item an id names whatever its revision."""
        return self.type, self.name

    def __str__(self) -> str:
        """Return the id as it is written, `type~name~revision`."""
        return f"{self.type}~{self.name}~{self.revision}"


@dataclass(frozen=True)
class Item:
    """A Markdown item: its id, where its id line sits, and the types on its `Needs:` line."""

    id: Id
    path: str
    line: int
    needs: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Link:
    """An id named by a key line or a tag, and where it was written.

    `type` is the naming item's type, or the tag's artifact type. `owner` is the item whose key line names the
    target, and is None for a tag.
    """

    key: str
    type: str
    target: Id
    path: str
    line: int
    owner: Id | None = None


@dataclass(frozen=True)
class NearMiss:
    """Text that nearly parses as a tag, an id line or a key line, with its canned fix."""

    path: str
    line: int
    text: str
    fix: str


@dataclass(frozen=True)
class Index:
    """The graph that the check and the judge share."""

    items: tuple[Item, ...]
    links: tuple[Link, ...]
    near_misses: tuple[NearMiss, ...]

    @cached_property
    def defined(self) -> dict[tuple[str, str], Item]:
        """Map each type and name to the first item that defines it; later items with that id are duplicates."""
        found: dict[tuple[str, str], Item] = {}
        for item in self.items:
            found.setdefault(item.id.key, item)
        return found


_Parsed = tuple[list[Item], list[Link], list[NearMiss]]


def split_lines(text: str) -> tuple[Line, ...]:
    """Number text's lines from 1, split at each newline alone, as Git counts them; a final newline adds no line."""
    return tuple(Line(number, raw) for number, raw in enumerate(text.removesuffix("\n").split("\n"), 1)) if text else ()


def build_index(sources: Iterable[Source]) -> Index:
    """Parse every source into one index, keeping the order of the sources and of their lines."""
    items: list[Item] = []
    links: list[Link] = []
    misses: list[NearMiss] = []
    for source in sources:
        if source.surface == MARKDOWN:
            found_items, found_links, found_misses = _markdown(source)
            items.extend(found_items)
            links.extend(found_links)
            misses.extend(found_misses)
    return Index(tuple(items), tuple(links), tuple(misses))


def _to_id(match: re.Match[str], first: int = 1) -> Id:
    return Id(match.group(first), match.group(first + 1), int(match.group(first + 2)))


def _fix(text: str, place: str) -> str:
    """Return the canned fix of the first Near-miss row that fits text written at place."""
    for where, pattern, fix in _FIXES:
        if where in (None, place) and pattern.search(text):
            return fix
    unknown = [word for word in _TYPE_SLOT.findall(text) if word not in TYPES]
    if unknown:
        closest = difflib.get_close_matches(unknown[0], TYPES, n=1, cutoff=0)[0]
        return f"use a known item type, such as `{closest}`"
    return f"rewrite it as {_FORMS[place]}"


def _markdown(source: Source) -> _Parsed:
    items: list[Item] = []
    links: list[Link] = []
    spans, misses = _spans(source)
    for item_id, number, lines in spans:
        needs, item_links, key_misses = _keys(source.path, item_id, lines)
        items.append(Item(item_id, source.path, number, needs))
        links.extend(item_links)
        misses.extend(key_misses)
    return items, links, misses


def _spans(source: Source) -> tuple[list[tuple[Id, int, list[Line]]], list[NearMiss]]:
    """Split a Markdown file into items: an id line owns the lines up to the next id line or ATX heading."""
    spans: list[tuple[Id, int, list[Line]]] = []
    misses: list[NearMiss] = []
    body: list[Line] | None = None
    for line in source.lines:
        if line.number in source.fenced:
            continue  # fenced code is body, and never starts, ends or keys an item
        text = line.text.rstrip()
        if loose := _ID_LINE.fullmatch(text):
            token, after = loose.group(2, 3)
            strict = None if after else _ID_ENTRY.fullmatch(token)
            if strict is None:
                misses.append(NearMiss(source.path, line.number, token + after, _fix(token + after, "id line")))
                body = None  # a malformed id line ends the item above it, as an id line would
            else:
                body = []
                spans.append((_to_id(strict), line.number, body))
        elif _HEADING.match(text):
            body = None
        elif body is not None:
            body.append(line)
    return spans, misses


def _keys(path: str, owner: Id, lines: Iterable[Line]) -> tuple[tuple[str, ...] | None, list[Link], list[NearMiss]]:
    """Read an item's key lines: its needs, its links, and every key, value or entry that fails to parse."""
    needs: tuple[str, ...] | None = None
    links: list[Link] = []
    misses: list[NearMiss] = []
    for line in lines:
        text = line.text.rstrip()
        if (key := _KEY.match(text)) is None:
            continue
        if (exact := _KEY_LINE.fullmatch(text)) is None:
            misses.append(NearMiss(path, line.number, text, _KEY_FIX.format(key.group(1).capitalize())))
            continue
        name, value = exact.group(1), exact.group(2) or ""
        if name == "Override":
            if not _OVERRIDE.fullmatch(value):
                misses.append(NearMiss(path, line.number, value or text, _fix(value, name)))
        elif name == "Needs":
            types, found = _list(path, line, value, _TYPE_ENTRY, name)
            misses.extend(found)
            if not found:
                needs = tuple(entry.group() for entry in types)
        else:
            ids, found = _list(path, line, value, _ID_ENTRY, "id")
            misses.extend(found)
            links.extend(Link(name, owner.type, _to_id(entry), path, line.number, owner=owner) for entry in ids)
    return needs, links, misses


def _list(
    path: str, line: Line, value: str, grammar: re.Pattern[str], place: str
) -> tuple[list[re.Match[str]], list[NearMiss]]:
    """Read a list value: the entries that parse, and a near-miss for each that does not.

    Entries are separated by exactly `, `. Any other separator, or an empty entry, fails the whole line once, and each
    entry is still read.
    """
    entries = [entry for entry in _SEPARATORS.split(value) if entry]
    misses: list[NearMiss] = []
    if not entries or ", ".join(entries) != value:
        misses.append(NearMiss(path, line.number, line.text.rstrip(), _EMPTY_FIX))
    parsed: list[re.Match[str]] = []
    for entry in entries:
        if match := grammar.fullmatch(entry):
            parsed.append(match)
        else:
            misses.append(NearMiss(path, line.number, entry, _fix(entry, place)))
    return parsed, misses
