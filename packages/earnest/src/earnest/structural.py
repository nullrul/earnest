"""Structural checks: the link findings the index decides without a model, and each requirement's trace level."""

from collections.abc import Iterable, Iterator, Mapping

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


def needs(item: Item, produces: frozenset[str] | None = None) -> tuple[str, ...]:
    """Return the types on the item's `Needs:` line, or its type's default, less those the route does not produce."""
    wanted = item.needs if item.needs is not None else DEFAULT_NEEDS.get(item.id.type, ())
    return _produced(wanted, produces)


def check(
    index: Index, *, produces: frozenset[str] | None = None, frozen: Mapping[str, str] | None = None
) -> list[Finding]:
    """Return the link findings, in the order of the index; the reporter sorts them.

    Near-misses, duplicate ids, links that resolve to no item or to another revision, covers that count toward
    nothing, items that name no parent of their type, needs that no cover meets, and bodies that changed after an
    approval froze their hash. `produces` is the set of item types some stage on the route produces: needs, parents
    and links that name any other type are dropped, as the route rule of Stages says. `None` is no route. `frozen`
    maps `type~name~revision` to the body hash that an approval froze.
    """
    return [
        *_near_misses(index),
        *_duplicates(index),
        *_links(index, produces),
        *_parentless(index, produces),
        *_gaps(index, produces),
        *_unbumped(index, frozen or {}),
    ]


def resolved_covers(index: Index) -> set[tuple[str, Item]]:
    """Return each cover that resolves at its item's current revision, as its artifact type and the item."""
    return {
        (kind, resolution.item)
        for kind, resolution in _covers(index)
        if resolution.status == "resolved" and resolution.item is not None
    }


def traced(index: Index, produces: frozenset[str] | None = None) -> dict[str, str]:
    """Give each requirement its trace level, keyed by its id: traced when a cover of every type it needs resolves."""
    resolved = resolved_covers(index)
    return {
        str(item.id): "traced" if all((kind, item) in resolved for kind in needs(item, produces)) else "untraced"
        for item in index.defined.values()
        if item.id.type == "req"
    }


def _produced(types: Iterable[str], produces: frozenset[str] | None) -> tuple[str, ...]:
    return tuple(types) if produces is None else tuple(kind for kind in types if kind in produces)


def _near_misses(index: Index) -> Iterator[Finding]:
    for miss in index.near_misses:
        yield Finding(miss.path, miss.line, "earnest/near-miss", miss.text, f"`{miss.text}` does not parse: {miss.fix}")


def _duplicates(index: Index) -> Iterator[Finding]:
    for item in index.items:
        first = index.defined[item.id.key]
        if item != first:
            message = f"`{item.id}` is already defined at {first.path}:{first.line}: give one of them another name"
            yield Finding(item.path, item.line, "earnest/duplicate", str(item.id), message)


def _links(index: Index, produces: frozenset[str] | None) -> Iterator[Finding]:
    """Turn each link's resolution into its findings: orphaned, outdated or predated, and unwanted."""
    for link in [link for link in index.links if produces is None or link.target.type in produces]:
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
        if link.key == "Covers" and link.type not in needs(item, produces):
            wanted = ", ".join(f"`{kind}`" for kind in needs(item, produces)) or "no cover"
            message = (
                f"`{link.type}` covers `{subject}` and counts toward nothing, because the item needs {wanted}:"
                f" use a type it needs, or add `{link.type}` to its `Needs:` line"
            )
            yield Finding(link.path, link.line, "earnest/unwanted", subject, message)


def _parentless(index: Index, produces: frozenset[str] | None) -> Iterator[Finding]:
    """An item whose parent key names no id of a parent type, itself included, covers no parent.

    On a route that produces none of an item's parent types the item is the chain root, and covers no parent.
    """
    named = {(link.owner, link.key, link.target.type) for link in index.links if link.owner is not None}
    for item in index.defined.values():
        if item.id.type not in _PARENTS:
            continue
        key, all_parents, fix = _PARENTS[item.id.type]
        parents = _produced(all_parents, produces)
        if parents and not any((item.id, key, parent) in named for parent in parents):
            yield Finding(
                item.path, item.line, "earnest/orphaned", str(item.id), f"`{item.id}` covers no parent: {fix}"
            )


def _gaps(index: Index, produces: frozenset[str] | None) -> Iterator[Finding]:
    """A need no cover meets at any revision is a gap; a cover at another revision is outdated or predated instead."""
    covered = {(kind, resolution.item) for kind, resolution in _covers(index)}
    for item in index.defined.values():
        for kind in needs(item, produces):
            if (kind, item) not in covered:
                hint = _COVER_HINTS.get(kind, "add a `{kind}` item with `Covers: {id}`").format(kind=kind, id=item.id)
                message = f"`{item.id}` needs a `{kind}` cover and has none: {hint}"
                yield Finding(item.path, item.line, "earnest/gap", str(item.id), message, child=kind)


def _unbumped(index: Index, frozen: Mapping[str, str]) -> Iterator[Finding]:
    """A body whose hash differs from the one an approval froze for its id and revision changed without a bump."""
    for item in index.defined.values():
        held = frozen.get(str(item.id))
        if held is not None and held != item.body_hash:
            message = (
                f"`{item.id}` changed its body after its approval and is still at revision {item.id.revision}:"
                f" bump the revision to {item.id.revision + 1}, or restore the text"
            )
            yield Finding(item.path, item.line, "earnest/unbumped-change", str(item.id), message)


def _covers(index: Index) -> set[tuple[str, Resolution]]:
    """Return each cover as its artifact type and the resolution of the id it names."""
    return {(link.type, index.resolutions[link.target]) for link in index.links if link.key == "Covers"}
