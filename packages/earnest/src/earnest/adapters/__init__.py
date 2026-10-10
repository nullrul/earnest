"""Host adapters: each listed file's adapter, picked by suffix, hands its lines to the grammar."""

from collections.abc import Callable, Collection, Iterable
from pathlib import Path, PurePosixPath

from earnest.adapters import gherkin, markdown, python, typescript
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Line, Source, digest, split_lines


STATE = "aidlc-state.md"
_STAGE_DEPTH = 3  # `<phase>/<slug>/memory.md` below a record directory

_Scan = Callable[[str], tuple[tuple[Line, ...], frozenset[int]]]
_Code = Callable[[str], frozenset[int]]


def _unfenced(scan: Callable[[str], tuple[Line, ...]]) -> _Scan:
    return lambda text: (scan(text), frozenset())


# Each suffix an adapter reads: its surface, the scan that gives its lines and the lines inside its code fences, and
# the scan that gives the lines that hold code (None for Markdown, which holds no code lines).
_SCANS: dict[str, tuple[str, _Scan, _Code | None]] = {
    ".md": (MARKDOWN, markdown.scan, None),
    ".feature": (GHERKIN, _unfenced(gherkin.scan), gherkin.code_lines),
    ".py": (COMMENT, _unfenced(python.scan), python.code_lines),
    ".ts": (COMMENT, _unfenced(typescript.scan), typescript.code_lines),
    ".tsx": (COMMENT, _unfenced(typescript.scan), typescript.code_lines),
    ".mts": (COMMENT, _unfenced(typescript.scan), typescript.code_lines),
    ".cts": (COMMENT, _unfenced(typescript.scan), typescript.code_lines),
}


def reads(path: str) -> bool:
    """Return whether an adapter reads files with the suffix of path."""
    return PurePosixPath(path).suffix in _SCANS


def record_directories(paths: Iterable[str]) -> frozenset[str]:
    """Return the record directories among the listed paths: the parent of each `aidlc-state.md`, `""` at the root."""
    parents = (PurePosixPath(path).parent for path in paths if PurePosixPath(path).name == STATE)
    return frozenset("" if parent == PurePosixPath(".") else parent.as_posix() for parent in parents)


def skipped(path: str, directories: Collection[str]) -> bool:
    """Return whether path is bookkeeping that AI-DLC writes inside one of the record directories, which no scan reads.

    Below a record directory these are its `aidlc-state.md`, everything under `audit/`, every entry whose name begins
    `.aidlc-` (`.aidlc-engine/` and the legacy siblings), and a `memory.md` in a stage directory, three or more
    components down. Directories compare by whole components, so `one` never holds `one-b`.
    """
    parts = PurePosixPath(path).parts
    bases = (PurePosixPath(directory).parts for directory in directories)
    return any(parts[: len(base)] == base and _is_bookkeeping(parts[len(base) :]) for base in bases)


def _is_bookkeeping(below: tuple[str, ...]) -> bool:
    return (
        below == (STATE,)
        or (len(below) > 1 and below[0] == "audit")
        or (bool(below) and below[0].startswith(".aidlc-"))
        or (len(below) >= _STAGE_DEPTH and below[-1] == "memory.md")
    )


def scan(root: Path, paths: Iterable[str]) -> list[Source]:
    """Scan each listed file whose suffix an adapter reads, in the order given, which `git.work_tree_files` sorts.

    Other files are skipped, and so are the bookkeeping files of a record directory (see `skipped`), files gone from
    the work tree, symlinks, whose target Git does not hold, binary files, which hold a NUL byte in their first 8000
    bytes as Git judges, and code files with no `~`, since every tag holds one. Text decodes as UTF-8, with a byte
    order mark dropped and each byte that is not UTF-8 replaced. Each source carries the digest of the raw bytes.

    Raises:
        OSError: a file cannot be read.
    """
    listed = list(paths)
    directories = record_directories(listed)
    sources: list[Source] = []
    for path in listed:
        adapter = _SCANS.get(PurePosixPath(path).suffix)
        file = root / path
        if adapter is None or skipped(path, directories) or file.is_symlink() or not file.is_file():
            continue
        surface, read, code = adapter
        data = file.read_bytes()
        if b"\0" in data[:8000] or (surface == COMMENT and b"~" not in data):
            continue
        text = data.decode("utf-8-sig", errors="replace")
        lines, fenced = read(text)
        sources.append(
            Source(
                path=path,
                surface=surface,
                lines=lines,
                fenced=fenced,
                code_lines=code(text) if code else frozenset(),
                digest=digest(data),
                line_count=len(split_lines(text)),
            )
        )
    return sources
