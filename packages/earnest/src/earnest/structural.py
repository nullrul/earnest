"""Structural checks: the link findings the index decides without a model, and each requirement's trace level."""

from collections.abc import Iterator

from earnest.index import Index, Item, Resolution
from earnest.reporter import Finding


DEFAULT_NEEDS: dict[str, tuple[str, ...]] = {
    "tenet": ("goal",),
    "goal": ("feat",),
    "feat": ("req", "stest"),
    "req": ("impl", "utest"),
    "dsn": ("impl",),
}
# The parent edge of each item type, from the Edges of the logic design: its key, the parent types, and the fix.
_PARENTS = {
    "goal": ("Covers", ("tenet",), "add a `Covers:` line naming the `tenet` it serves"),
    "feat": ("Covers", ("goal",), "add a `Covers:` line naming the `goal` it refines"),
    "req": ("Covers", ("feat",), "add a `Covers:` line naming the `feat` it derives from"),
    "dsn": ("Drivers", ("req", "goal"), "add a `Drivers:` line naming the `req` or `goal` that drives it"),
}
_COVER_HINTS = {
    "impl": "tag the code that implements it with `[impl->{id}]`",
    "utest": "tag a unit test that verifies it with `[utest->{id}]`",
    "itest": "tag an integration test that verifies it with `[itest->{id}]`",
    "stest": "tag a scenario that verifies it with `@stest:{id}`",
}


def needs(item: Item) -> tuple[str, ...]:
    """Return the types on the item's `Needs:` line, or its type's default."""
    return item.needs if item.needs is not None else DEFAULT_NEEDS.get(item.id.type, ())


def check(index: Index) -> list[Finding]:
    """Return the link findings, in the order of the index; the reporter sorts them.

    Near-misses, duplicate ids, links that resolve to no item or to another revision, covers that count toward
    nothing, items that name no parent of their type, and needs that no cover meets.
    """
    return [*_near_misses(index), *_duplicates(index), *_links(index), *_parentless(index), *_gaps(index)]


def traced(index: Index) -> dict[str, str]:
    """Give each requirement its trace level, keyed by its id: traced when a cover of every type it needs resolves."""
    resolved = {(kind, resolution.item) for kind, resolution in _covers(index) if resolution.status == "resolved"}
    return {
        str(item.id): "traced" if all((kind, item) in resolved for kind in needs(item)) else "untraced"
        for item in index.defined.values()
        if item.id.type == "req"
    }


def _near_misses(index: Index) -> Iterator[Finding]:
    for miss in index.near_misses:
        yield Finding(miss.path, miss.line, "earnest/near-miss", miss.text, f"`{miss.text}` does not parse: {miss.fix}")


def _duplicates(index: Index) -> Iterator[Finding]:
    for item in index.items:
        first = index.defined[item.id.key]
        if item != first:
            message = f"`{item.id}` is already defined at {first.path}:{first.line}: give one of them another name"
            yield Finding(item.path, item.line, "earnest/duplicate", str(item.id), message)


def _links(index: Index) -> Iterator[Finding]:
    """Turn each link's resolution into its findings: orphaned, outdated or predated, and unwanted."""
    for link in index.links:
        resolution = index.resolutions[link.target]
        subject = str(link.target)
        item = resolution.item
        if item is None:
            close = (
                f"did you mean `{resolution.closest}`?"
                if resolution.closest
                else "define the item, or name one that exists"
            )
            yield Finding(link.path, link.line, "earnest/orphaned", subject, f"`{subject}` names no item: {close}")
            continue
        if resolution.status == "outdated":
            message = (
                f"`{subject}` names revision {link.target.revision}, and the item is at revision {item.id.revision}:"
                f" check the change, then write `{item.id}`"
            )
            yield Finding(link.path, link.line, "earnest/outdated", subject, message)
        elif resolution.status == "predated":
            message = (
                f"`{subject}` names revision {link.target.revision}, above the item's revision {item.id.revision}:"
                f" write `{item.id}`, or bump the item if its meaning changed"
            )
            yield Finding(link.path, link.line, "earnest/predated", subject, message)
        if link.key == "Covers" and link.type not in needs(item):
            wanted = ", ".join(f"`{kind}`" for kind in needs(item)) or "no cover"
            message = (
                f"`{link.type}` covers `{subject}` and counts toward nothing, because the item needs {wanted}:"
                f" use a type it needs, or add `{link.type}` to its `Needs:` line"
            )
            yield Finding(link.path, link.line, "earnest/unwanted", subject, message)


def _parentless(index: Index) -> Iterator[Finding]:
    """An item whose parent key names no id of a parent type, itself included, covers no parent."""
    named = {(link.owner, link.key, link.target.type) for link in index.links if link.owner is not None}
    for item in index.defined.values():
        if item.id.type not in _PARENTS:
            continue
        key, parents, fix = _PARENTS[item.id.type]
        if not any((item.id, key, parent) in named for parent in parents):
            yield Finding(
                item.path, item.line, "earnest/orphaned", str(item.id), f"`{item.id}` covers no parent: {fix}"
            )


def _gaps(index: Index) -> Iterator[Finding]:
    """A need no cover meets at any revision is a gap; a cover at another revision is outdated or predated instead."""
    covered = {(kind, resolution.item) for kind, resolution in _covers(index)}
    for item in index.defined.values():
        for kind in needs(item):
            if (kind, item) not in covered:
                hint = _COVER_HINTS.get(kind, "add a `{kind}` item with `Covers: {id}`").format(kind=kind, id=item.id)
                message = f"`{item.id}` needs a `{kind}` cover and has none: {hint}"
                yield Finding(item.path, item.line, "earnest/gap", str(item.id), message)


def _covers(index: Index) -> set[tuple[str, Resolution]]:
    """Return each cover as its artifact type and the resolution of the id it names."""
    return {(link.type, index.resolutions[link.target]) for link in index.links if link.key == "Covers"}
