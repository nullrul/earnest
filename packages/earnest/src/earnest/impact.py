"""Impact: the coverage map that `check --stage` takes, and the requirements, features and tests a change impacts."""

import json
import os
import re
import subprocess
import sys
from collections import deque
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from earnest import git
from earnest.git import Hunk
from earnest.index import Index
from earnest.reporter import Impact


COVERAGE = ".earnest/coverage"
# The variables of a test run that is already going, which would steer the map run into that run's data and options.
_INHERITED = ("PYTEST_", "COV_CORE_", "COVERAGE_")

MAP_TIMEOUT = 900  # seconds the map run may take, generous for a slow suite, so a hanging test cannot hang the gate
_NO_MAP = {2: "interrupted", 3: "internal error", 4: "usage error", 5: "no tests collected"}  # pytest's exit codes
_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")  # a commit, so a record that names anything else names no path
CoverageMap = dict[tuple[str, int], tuple[str, ...]]
_TEST_TYPES = frozenset({"utest", "itest", "stest"})
_DEF = re.compile(r"([ \t]*)(?:async[ \t]+)?def[ \t]+(test\w*)[ \t]*\(")
_CLASS = re.compile(r"class[ \t]+(Test\w*)\b")


def map_file(root: Path, commit: str) -> Path:
    """Return the coverage data file of the map taken at commit."""
    return root / COVERAGE / commit


def _report(root: Path, commit: str) -> Path:
    return root / COVERAGE / f"{commit}.json"


def is_commit(text: object) -> bool:
    """Return whether text is a full commit sha, the only name a coverage map is kept under."""
    return isinstance(text, str) and _SHA.fullmatch(text) is not None


def take_map(root: Path, commit: str, python: str = sys.executable) -> str | None:
    """Take the coverage map at commit: run the repository's tests under pytest-cov with per-test contexts.

    The run uses the interpreter that runs Earnest, reads no stdin and stops after `MAP_TIMEOUT` seconds. Its data
    file is `.earnest/coverage/<commit>` and its JSON report, with the contexts, `.earnest/coverage/<commit>.json`.
    Earnest's own options write nothing outside `.earnest/`: no cache, bytecode, log file or `.coverage`, with the
    repository's `addopts` and coverage configuration left out; the repository's tests themselves run under the
    test-suite trust model. A failing test still gives a map. A run that times out, that pytest ends with exit code 2
    to 5, or that gives no coverage data gives none, and leaves an earlier map at the commit as it was.

    Returns:
        None when the map was taken, else the reason it was not, for the summary.

    Raises:
        OSError: `.earnest/coverage/` cannot be written.
        ValueError: commit is not a full commit sha.
    """
    if not is_commit(commit):
        msg = f"{commit!r} is not a commit"
        raise ValueError(msg)
    directory = root / COVERAGE
    directory.mkdir(parents=True, exist_ok=True)
    data, report = directory / f"{commit}.tmp", directory / f"{commit}.json.tmp"  # moved into place once whole
    try:
        reason = _map_run(root, python, data, report)
        if reason is None:
            report.replace(_report(root, commit))
            data.replace(map_file(root, commit))
    finally:
        data.unlink(missing_ok=True)
        report.unlink(missing_ok=True)
    return reason


def _map_run(root: Path, python: str, data: Path, report: Path) -> str | None:
    env = {name: value for name, value in os.environ.items() if not name.startswith(_INHERITED)}
    env |= {"COVERAGE_FILE": str(data), "PYTHONDONTWRITEBYTECODE": "1"}
    tests = ["--cov=.", "--cov-context=test", "--cov-report=", f"--cov-config={os.devnull}"]
    # ponytail: `cache_dir` is the cache provider's own option, so with the provider off `-o cache_dir=` is an unknown
    # option that fails a repository with `filterwarnings = error`; turning the provider off already writes no cache
    options = ["-p", "no:cacheprovider", "-o", "addopts=", "-o", "log_file=", "-q"]
    code = _run([python, "-m", "pytest", *tests, *options], root, env)
    if code is None:
        return f"the test run timed out after {MAP_TIMEOUT} s"
    if code in _NO_MAP:
        return f"pytest exited {code} ({_NO_MAP[code]})"
    if not data.is_file() or data.stat().st_size == 0:
        return "the test run gave no coverage data"
    reported = _run(
        [python, "-m", "coverage", "json", "--show-contexts", f"--rcfile={os.devnull}", "-o", str(report)], root, env
    )
    if reported is None:
        return f"the coverage report timed out after {MAP_TIMEOUT} s"
    if reported != 0 or not report.is_file():
        return "coverage could not report the test contexts"
    return None


def _run(command: list[str], root: Path, env: Mapping[str, str]) -> int | None:
    """Run the repository's own tests or report, as `check --stage` promises; None when it timed out."""
    try:
        done = subprocess.run(  # noqa: S603
            command, cwd=root, env=env, stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=MAP_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return None
    return done.returncode


def read_map(root: Path, commit: str) -> CoverageMap | None:
    """Return the coverage map taken at commit: each file and line, with the sorted node ids of the tests that ran it.

    A context is a pytest node id with its phase suffix, such as `|run`, dropped; the empty context of collection is
    no test. None means no map exists for the commit, or it cannot be read.
    """
    if not is_commit(commit):
        return None
    try:
        data = json.loads(_report(root, commit).read_text(encoding="utf-8"))
        files = data["files"]
        found: dict[tuple[str, int], set[str]] = {}
        for name, entry in files.items():
            path = _relative(root, name)
            for line, contexts in entry.get("contexts", {}).items():
                tests = {context.rpartition("|")[0] or context for context in contexts if context}
                if tests:
                    found.setdefault((path, int(line)), set()).update(tests)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    return {place: tuple(sorted(tests)) for place, tests in sorted(found.items())}


def _relative(root: Path, name: str) -> str:
    path = Path(name)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()
    return path.as_posix()


@dataclass(frozen=True)
class Selection:
    """What impact selects for a change: the impact section, and each changed line that selected the full suite."""

    impact: Impact
    degraded: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class Change:
    """A change since the task's base commit: its hunks, the base, and the hunks since the coverage map's commit."""

    hunks: Mapping[str, Sequence[Hunk]]
    base: str
    since_map: Mapping[str, Sequence[Hunk]]


def select(root: Path, index: Index, change: Change, coverage: CoverageMap | None) -> Selection:
    """Select the tests a change impacts, by the Impact rule.

    A changed line is seen through the line it was at the map's commit, by `change.since_map`, the hunks from that
    commit to the work tree, and selects the tests whose contexts covered it. A line the map never saw selects every
    test whose tag names, on type and name, what a tag region holding the line names. A line in no tag region selects
    the full suite, every test the map holds, and is degraded. The requirements are those the changed tag regions
    name, and what they cover up to the requirements, at their current revision; the features are the `feat` items
    above them.
    """
    tests: set[str] = set()
    named: set[tuple[str, str]] = set()
    degraded: list[tuple[str, int]] = []
    for path, hunks in sorted(change.hunks.items()):
        for line in sorted({line for hunk in hunks for line in hunk.new_lines}):
            keys = {region.target.key for region in index.regions_at(path, line)}
            named |= keys
            seen = _seen(coverage, change.since_map.get(path, ()), path, line)
            if seen:
                tests.update(seen)
            elif keys:
                tests.update(tagged_tests(root, index, keys))
            else:
                degraded.append((path, line))
    if degraded and coverage:
        tests.update(test for found in coverage.values() for test in found)
    above = _covered(index, named)
    selected = Impact(
        requirements=_current(index, above, "req"),
        features=_current(index, above, "feat"),
        tests=tuple(sorted(tests)),
        degraded=bool(degraded),
        base=change.base,
        mapped=coverage is not None,
    )
    return Selection(selected, tuple(degraded))


def _seen(coverage: CoverageMap | None, hunks: Sequence[Hunk], path: str, line: int) -> tuple[str, ...]:
    if coverage is None:
        return ()
    old = git.old_line(hunks, line)
    return () if old is None else coverage.get((path, old), ())


def tagged_tests(root: Path, index: Index, keys: Collection[tuple[str, str]]) -> list[str]:
    """Return the pytest node ids of the test functions in the regions of the test tags that name one of keys.

    Only Python test files give node ids: a `def test…` at the top of the file, or in a `class Test…`.
    """
    found: set[str] = set()
    for link in index.links:
        if link.owner is not None or link.type not in _TEST_TYPES or link.target.key not in keys:
            continue
        if not link.path.endswith(".py"):
            continue
        for region in index.regions_at(link.path, link.line):
            if region.target == link.target:
                found.update(_node_ids(root, link.path, region.first, region.last))
    return sorted(found)


def _node_ids(root: Path, path: str, first: int, last: int) -> list[str]:
    try:
        lines = (root / path).read_text(encoding="utf-8", errors="replace").split("\n")
    except OSError:
        return []
    found: list[str] = []
    owner: str | None = None
    body: str | None = None  # the indentation of the class body, from its first line
    for number, text in enumerate(lines, 1):
        indent = text[: len(text) - len(text.lstrip(" \t"))]
        if text.strip() and not indent:
            match = _CLASS.match(text)
            owner, body = (match[1] if match else None), None
        elif text.strip() and owner is not None and body is None:
            body = indent
        defined = _DEF.match(text)
        if defined is None or not first <= number <= last:
            continue
        if not defined[1]:
            found.append(f"{path}::{defined[2]}")
        elif owner is not None and defined[1] == body:  # a method of the class, not a def nested in one
            found.append(f"{path}::{owner}::{defined[2]}")
    return found


def _covered(index: Index, start: Iterable[tuple[str, str]]) -> set[tuple[str, str]]:
    """Return start and everything its items cover, through `Covers:` lines, transitively."""
    edges: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for link in index.links:
        if link.key == "Covers" and link.owner is not None:
            edges.setdefault(link.owner.key, set()).add(link.target.key)
    seen = set(start)
    queue = deque(seen)
    while queue:
        for target in edges.get(queue.popleft(), ()):
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return seen


def _current(index: Index, keys: Iterable[tuple[str, str]], kind: str) -> tuple[str, ...]:
    return tuple(sorted(str(index.defined[key].id) for key in keys if key[0] == kind and key in index.defined))
