"""Grammar and index: items, links and near-misses from the lines the host adapters hand over."""

import difflib
import hashlib
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import cached_property
from typing import Literal


MARKDOWN = "markdown"
COMMENT = "comment"
GHERKIN = "gherkin"
TYPES = ("tenet", "goal", "feat", "req", "dsn", "unit", "task", "impl", "utest", "itest", "stest")
KEYS = ("Needs", "Covers", "Drivers", "Delivers", "Depends", "Override")

_TYPE = f"({'|'.join(TYPES)})"
_ID = rf"{_TYPE}~([a-z0-9-]+)~([1-9][0-9]{{0,8}})"  # nine digits at most, far under int()'s 4300-digit limit
ID_ENTRY = re.compile(_ID)
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
    COMMENT: f"`[type->type~name~revision]`, with {_NAME_RULE}",
    GHERKIN: f"`@type:type~name~revision`, with {_NAME_RULE}",
    "id line": f"`type~name~revision` in backticks, alone on its line or after heading marks, with {_NAME_RULE}",
    "id": f"`type~name~revision`, with {_NAME_RULE}",
    "Needs": "item types separated by a comma and a space, such as `impl, utest`",
    "Override": f"`type~name~revision implemented at commit, reason`, or `tested` for tests, with {_NAME_RULE}",
}
# Each run ends where the next part begins, at the first `->` or `~`, so no line backtracks more than linearly.
_BRACKET = r"\[\s*(?:(?:[^\[\]\s>-]+\s*)?->\s*)?[^\[\]\s~]*~[^\[\]\s]*\s*\]"
_TAG_FORMS = {
    COMMENT: re.compile(rf"\[\s*{_TYPE}\s*->\s*{_ID}\s*\]"),
    GHERKIN: re.compile(rf"@{_TYPE}:{_ID}"),
}
# A tag candidate is the near-miss superset of a surface: a bracketed token with a `~` inside, spaced as OFT allows, and
# on the Gherkin surface alone a token that opens with `@` and holds a `~`, including `@stest feat~login~1`. A JSDoc
# `@see req~x~1` in a comment is therefore no candidate.
_TAG_CANDIDATES = {
    COMMENT: re.compile(_BRACKET),
    GHERKIN: re.compile(rf"{_BRACKET}|(?<!\S)@[a-z]+[ \t]+[a-z]+~\S*|(?<!\S)@[^\s@~]*~\S*"),
}


@dataclass(frozen=True)
class Line:
    """One line a host adapter hands to the grammar, numbered from 1."""

    number: int
    text: str


def digest(data: bytes) -> str:
    """Return `sha256:` and the lower-case hex SHA-256 of data."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Source:
    """One listed file as its host adapter saw it.

    For Markdown, `lines` holds every line and `fenced` the lines inside code fences. For the comment and Gherkin
    surfaces, `lines` holds the comment or tag lines and `code_lines` the numbers of the lines that hold code, which
    the Region rule reads. `digest` is the digest of the raw bytes read, and `line_count` the lines Git counts.
    """

    path: str
    surface: str
    lines: tuple[Line, ...]
    fenced: frozenset[int] = frozenset()
    code_lines: frozenset[int] = frozenset()
    digest: str = ""
    line_count: int = 0


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
    """A Markdown item: its id, where its id line sits, the types on its `Needs:` line, and its body hash.

    The body hash derives from the lines, so it takes no part in equality: two items with one id, place and needs are
    the same item.
    """

    id: Id
    path: str
    line: int
    needs: tuple[str, ...] | None = None
    body_hash: str = field(default="", compare=False)


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


Status = Literal["resolved", "outdated", "predated", "orphaned"]


@dataclass(frozen=True)
class Region:
    """The lines of a file that a tag governs, from `first` to `last` inclusive."""

    target: Id
    path: str
    first: int
    last: int


@dataclass(frozen=True)
class Resolution:
    """What a written id names: its item, and `resolved`, `outdated`, `predated` or `orphaned`.

    An orphaned id carries the closest id of its own type, when one is close enough to suggest.
    """

    item: Item | None
    status: Status
    closest: Id | None = None


@dataclass(frozen=True)
class Index:
    """The graph that the check and the judge share."""

    items: tuple[Item, ...]
    links: tuple[Link, ...]
    near_misses: tuple[NearMiss, ...]
    regions: tuple[Region, ...] = ()

    @cached_property
    def defined(self) -> dict[tuple[str, str], Item]:
        """Map each type and name to the first item that defines it; later items with that id are duplicates."""
        found: dict[tuple[str, str], Item] = {}
        for item in self.items:
            found.setdefault(item.id.key, item)
        return found

    @cached_property
    def resolutions(self) -> dict[Id, Resolution]:
        """Resolve each id the links name, once per id written, by type and name and then by revision."""
        return {target: self._resolve(target) for target in dict.fromkeys(link.target for link in self.links)}

    def _resolve(self, target: Id) -> Resolution:
        item = self.defined.get(target.key)
        if item is None:
            same_type = {found.id.name: found.id for found in self.defined.values() if found.id.type == target.type}
            close = difflib.get_close_matches(target.name, same_type, n=1)
            return Resolution(None, "orphaned", same_type[close[0]] if close else None)
        if target.revision < item.id.revision:
            return Resolution(item, "outdated")
        if target.revision > item.id.revision:
            return Resolution(item, "predated")
        return Resolution(item, "resolved")


_Parsed = tuple[list[Item], list[Link], list[NearMiss]]


def split_lines(text: str) -> tuple[Line, ...]:
    """Number text's lines from 1, split at each newline alone, as Git counts them; a final newline adds no line."""
    return tuple(Line(number, raw) for number, raw in enumerate(text.removesuffix("\n").split("\n"), 1)) if text else ()


def build_index(sources: Iterable[Source]) -> Index:
    """Parse every source into one index, keeping the order of the sources and of their lines."""
    items: list[Item] = []
    links: list[Link] = []
    misses: list[NearMiss] = []
    regions: list[Region] = []
    for source in sources:
        parse = _markdown if source.surface == MARKDOWN else _tags
        found_items, found_links, found_misses = parse(source)
        items.extend(found_items)
        links.extend(found_links)
        misses.extend(found_misses)
        if source.surface != MARKDOWN:
            regions.extend(_regions(source, found_links))
    return Index(tuple(items), tuple(links), tuple(misses), tuple(sorted(regions, key=_region_order)))


def _region_order(region: Region) -> tuple[str, int, str]:
    return region.path, region.first, str(region.target)


def _regions(source: Source, tags: Sequence[Link]) -> list[Region]:
    """Derive the regions of a file's tags by the Region rule.

    A tag governs the lines from itself to the next group of tags, or to the end of the file. Tags with no code line
    from one to the next are one group, and share the region that follows them, which starts at the group's first tag.
    A code line on a tag's own line counts as code. The regions of one id that overlap or touch merge into one.
    """
    groups: list[list[Link]] = []
    for tag in sorted(tags, key=lambda link: link.line):
        if groups and not any(line in source.code_lines for line in range(groups[-1][-1].line, tag.line)):
            groups[-1].append(tag)
        else:
            groups.append([tag])
    spans: dict[Id, list[tuple[int, int]]] = {}
    for group, after in zip(groups, [*groups[1:], None], strict=False):
        last = after[0].line - 1 if after else max(source.line_count, group[-1].line)
        for tag in group:
            spans.setdefault(tag.target, []).append((group[0].line, last))
    return [
        Region(target, source.path, first, last) for target, found in spans.items() for first, last in _merge(found)
    ]


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for first, last in sorted(spans):
        if merged and first <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], last))
        else:
            merged.append((first, last))
    return merged


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
        keyed = [line for line in lines if line.number not in source.fenced]
        needs, item_links, key_misses = _keys(source.path, item_id, keyed)
        items.append(Item(item_id, source.path, number, needs, _body_hash(lines, source.fenced)))
        links.extend(item_links)
        misses.extend(key_misses)
    return items, links, misses


def _spans(source: Source) -> tuple[list[tuple[Id, int, list[Line]]], list[NearMiss]]:
    """Split a Markdown file into items: an id line owns the lines up to the next id line or ATX heading.

    Fenced lines belong to the item above them, and never start, end or key an item.
    """
    spans: list[tuple[Id, int, list[Line]]] = []
    misses: list[NearMiss] = []
    body: list[Line] | None = None
    for line in source.lines:
        if line.number in source.fenced:
            if body is not None:
                body.append(line)
            continue
        text = line.text.rstrip()
        if loose := _ID_LINE.fullmatch(text):
            token, after = loose.group(2, 3)
            strict = None if after else ID_ENTRY.fullmatch(token)
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


def _body_hash(lines: Iterable[Line], fenced: frozenset[int]) -> str:
    """Return the digest of an item's body: its non-blank lines, less its key lines, joined by line feeds.

    A fenced line is body even where it looks like a key line. Each line loses one carriage return before its line
    feed, then trailing spaces and tabs, and is blank when nothing is left; other whitespace stays, so only what Git
    and an editor add at a line's end leaves the hash as it was.
    """
    stripped = [(line.number, line.text.removesuffix("\r").rstrip(" \t")) for line in lines]
    kept = [text for number, text in stripped if text and (number in fenced or _KEY.match(text) is None)]
    return digest("\n".join(kept).encode("utf-8"))


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
            ids, found = _list(path, line, value, ID_ENTRY, "id")
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


def _tags(source: Source) -> _Parsed:
    strict = _TAG_FORMS[source.surface]
    links: list[Link] = []
    misses: list[NearMiss] = []
    for line in source.lines:
        for candidate in _TAG_CANDIDATES[source.surface].finditer(line.text):
            text = candidate.group()
            if tag := strict.fullmatch(text):
                links.append(Link("Covers", tag.group(1), _to_id(tag, 2), source.path, line.number))
            else:
                misses.append(NearMiss(source.path, line.number, text, _fix(text, source.surface)))
    return [], links, misses
