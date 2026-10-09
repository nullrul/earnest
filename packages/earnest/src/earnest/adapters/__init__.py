"""Host adapters: each listed file's adapter, picked by suffix, hands its lines to the grammar."""

from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath

from earnest.adapters import gherkin, markdown, python, typescript
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Line, Source


_Scan = Callable[[str], tuple[tuple[Line, ...], frozenset[int]]]


def _unfenced(scan: Callable[[str], tuple[Line, ...]]) -> _Scan:
    return lambda text: (scan(text), frozenset())


# Each suffix an adapter reads: its surface, and the scan that gives its lines and the lines inside its code fences.
_SCANS: dict[str, tuple[str, _Scan]] = {
    ".md": (MARKDOWN, markdown.scan),
    ".feature": (GHERKIN, _unfenced(gherkin.scan)),
    ".py": (COMMENT, _unfenced(python.scan)),
    ".ts": (COMMENT, _unfenced(typescript.scan)),
    ".tsx": (COMMENT, _unfenced(typescript.scan)),
    ".mts": (COMMENT, _unfenced(typescript.scan)),
    ".cts": (COMMENT, _unfenced(typescript.scan)),
}


def scan(root: Path, paths: Iterable[str]) -> list[Source]:
    """Scan each listed file whose suffix an adapter reads, in the order given, which `git.work_tree_files` sorts.

    Other files are skipped, and so are files gone from the work tree, symlinks, whose target Git does not hold, binary
    files, which hold a NUL byte in their first 8000 bytes as Git judges, and code files with no `~`, since every tag
    holds one. Text decodes as UTF-8, with a byte order mark dropped and each byte that is not UTF-8 replaced.

    Raises:
        OSError: a file cannot be read.
    """
    sources: list[Source] = []
    for path in paths:
        adapter = _SCANS.get(PurePosixPath(path).suffix)
        file = root / path
        if adapter is None or file.is_symlink() or not file.is_file():
            continue
        surface, read = adapter
        data = file.read_bytes()
        if b"\0" not in data[:8000] and (surface != COMMENT or b"~" in data):
            sources.append(Source(path, surface, *read(data.decode("utf-8-sig", errors="replace"))))
    return sources
