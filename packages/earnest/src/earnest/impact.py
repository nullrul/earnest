"""Impact: the coverage map that `check --stage` takes, the impact of a change, and the evidence of `--evidence`."""

import ast
import configparser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from collections import deque
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from earnest import git, judge
from earnest.git import Hunk
from earnest.index import Index, Item, Link
from earnest.reporter import Finding, Impact, evidence_message


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
MUTMUT_MAJOR = "3"  # the major whose result format the reader parses
_CLICK = "\u01c1"  # mutmut's separator of class and method in a mutant's name (U+01C1)
_VERSION = "import importlib.metadata as m; print(m.version('mutmut'))"
# mutmut 3.8's `status_by_exit_code`, read once: no test killed the mutant, or a test or the type check stopped it
_SURVIVING = frozenset({0, 5, 33})  # survived, no tests
_KILLED = frozenset({1, 3, 36, 24, -24, 152, 255, 37, 34})  # killed, timeout, caught by type check; skipped: nothing
_INCOMPLETE = {-9: "segfault", -11: "segfault", 35: "suspicious", 2: "interrupted", None: "not checked"}


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
    env = _environment() | {"COVERAGE_FILE": str(data), "PYTHONDONTWRITEBYTECODE": "1"}
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


def _environment() -> dict[str, str]:
    """Return Earnest's environment less the variables of a test run already going, for the runs Earnest starts."""
    return {name: value for name, value in os.environ.items() if not name.startswith(_INHERITED)}


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
    """What impact selects for a change: the impact section, and each line that selected the full suite.

    `degraded` holds each changed line, as its file and line; `deleted` each deleted line, as its file, the line of the
    work tree it was deleted at, and its line in the baseline commit.
    """

    impact: Impact
    degraded: tuple[tuple[str, int], ...]
    deleted: tuple[tuple[str, int, int], ...] = ()


@dataclass(frozen=True)
class Change:
    """A change since the change baseline: its hunks, deletions kept, and the baseline, whose map impact reads."""

    hunks: Mapping[str, Sequence[Hunk]]
    base: str


def select(root: Path, index: Index, change: Change, coverage: CoverageMap | None) -> Selection:
    """Select the tests a change impacts, by the Impact rule.

    The map is the baseline's, so a changed line is seen through the baseline line its hunk pairs it with, and selects
    the tests whose contexts covered it. A line the map never saw selects every
    test whose tag names, on type and name, what a tag region holding the line names. A line in no tag region selects
    the full suite, every test the map holds, and is degraded. A line deleted since the baseline selects the tests that
    covered it in the map; with no such data it selects the full suite and is degraded, at the line
    of the work tree it was deleted at. The requirements are those the changed tag regions
    name, and what they cover up to the requirements, at their current revision; the features are the `feat` items
    above them.
    """
    tests: set[str] = set()
    named: set[tuple[str, str]] = set()
    degraded: list[tuple[str, int]] = []
    deleted: list[tuple[str, int, int]] = []
    for path, hunks in sorted(change.hunks.items()):
        for hunk in hunks:
            for old in hunk.deleted_lines:
                covered = coverage.get((path, old), ()) if coverage is not None else ()
                tests.update(covered)
                if not covered:
                    deleted.append((path, max(hunk.new_start + max(hunk.new_count - 1, 0), 1), old))
        for line in sorted({line for hunk in hunks for line in hunk.new_lines}):
            keys = {region.target.key for region in index.regions_at(path, line)}
            named |= keys
            seen = _seen(coverage, hunks, path, line)
            if seen:
                tests.update(seen)
            elif keys:
                tests.update(tagged_tests(root, index, keys))
            else:
                degraded.append((path, line))
    if (degraded or deleted) and coverage:
        tests.update(test for found in coverage.values() for test in found)
    above = _covered(index, named)
    selected = Impact(
        requirements=_current(index, above, "req"),
        features=_current(index, above, "feat"),
        tests=tuple(sorted(tests)),
        degraded=bool(degraded or deleted),
        base=change.base,
        mapped=coverage is not None,
    )
    return Selection(selected, tuple(degraded), tuple(deleted))


def _seen(coverage: CoverageMap | None, hunks: Sequence[Hunk], path: str, line: int) -> tuple[str, ...]:
    if coverage is None:
        return ()
    old = git.old_line(hunks, line)
    return () if old is None else coverage.get((path, old), ())


def tagged_tests(root: Path, index: Index, keys: Collection[tuple[str, str]]) -> list[str]:
    """Return the pytest node ids of the test functions in the regions of the test tags that name one of keys.

    Only Python test files give node ids: a `def test…` at the top of the file, or in a `class Test…`.
    """
    return sorted({node for _, nodes in _test_tags(root, index, keys) for node in nodes})


def _test_tags(root: Path, index: Index, keys: Collection[tuple[str, str]]) -> Iterator[tuple[Link, list[str]]]:
    """Yield each Python test tag that names one of keys, with the node ids of the tests in its region."""
    for link in index.links:
        if link.owner is not None or link.type not in _TEST_TYPES or link.target.key not in keys:
            continue
        if not link.path.endswith(".py"):
            continue
        for region in index.regions_at(link.path, link.line):
            if region.target == link.target:
                yield link, _node_ids(root, link.path, link.line, region.last)  # from the tag: regions of one id merge


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


class EvidenceError(Exception):
    """The evidence layer cannot run: mutmut is missing or of another version, or a run gives no result."""


@dataclass(frozen=True)
class Mutant:
    """One mutant mutmut ran: the file and line it changes, its key, and mutmut's exit code for it, None if unchecked."""

    path: str
    line: int
    key: str
    code: int | None


@dataclass(frozen=True)
class Evidence:
    """What `--evidence` found: the tool that ran, the failing tagged tests, and every mutant mutmut ran.

    With a failing tagged test mutmut does not run, so `mutants` is empty.
    """

    tool: str
    failing: tuple[str, ...]
    mutants: tuple[Mutant, ...]


def tool() -> str | None:
    """Return the `tool` of an evidence key: `mutmut <version>` in Earnest's own interpreter, or None without one."""
    try:
        return f"mutmut {version('mutmut')}"
    except PackageNotFoundError:
        return None


def mutation_files(index: Index, levels: Mapping[str, str]) -> list[str]:
    """Return the files mutmut mutates: the Python files holding an `impl` region of a traced requirement."""
    paths = {
        region.path
        for item in index.defined.values()
        if item.id.type == "req" and levels.get(str(item.id), "untraced") != "untraced"
        for region in judge.regions(index, item, judge.KINDS["implemented"])
    }
    return sorted(path for path in paths if path.endswith(".py"))


def evidence(root: Path, index: Index, levels: Mapping[str, str], python: str = sys.executable) -> Evidence:
    """Run the evidence layer on a temporary copy of the work tree: the whole suite, then mutmut on `mutation_files`.

    mutmut runs as `take_map` runs pytest, under python, and only when the suite passes on the unmutated copy, since
    mutmut's own stats run aborts on any failing test. A failing tagged test gives the result without mutmut.

    Raises:
        EvidenceError: mutmut is missing, of another major, or of another version under python; the copy's
            `pyproject.toml` has its own `[tool.mutmut]`; an untagged test fails; or a run times out or gives no result.
        OSError: the copy cannot be written.
    """
    name = _tool(python)
    files = mutation_files(index, levels)
    with tempfile.TemporaryDirectory(prefix="earnest-evidence-") as temporary:
        copy = _copy(root, Path(temporary) / "tree")
        _configure(copy, files)
        failing = _suite(copy, Path(temporary) / "junit.xml", python)  # the report sits beside the copy, not in it
        untagged = sorted(
            set(failing) - set(tagged_tests(root, index, [key for key in index.defined if key[0] == "req"]))
        )
        if untagged:
            msg = f"evidence: the untagged test {', '.join(untagged)} fails on the unmutated code, so mutmut cannot run"
            raise EvidenceError(msg)
        if failing or not files:
            return Evidence(name, tuple(failing), ())
        if _run([python, "-m", "mutmut", "run"], copy, _environment()) is None:  # its exit code is no verdict
            msg = f"evidence: the mutmut run timed out after {MAP_TIMEOUT} s"
            raise EvidenceError(msg)
        return Evidence(name, (), tuple(mutant for path in files for mutant in _mutants(copy, path)))


def _tool(python: str) -> str:
    name = tool()
    if name is None:
        msg = "evidence: mutmut is not installed"
        raise EvidenceError(msg)
    own = name.removeprefix("mutmut ")
    if own.split(".")[0] != MUTMUT_MAJOR:
        msg = f"evidence: mutmut {own} is not mutmut {MUTMUT_MAJOR}, whose results Earnest reads"
        raise EvidenceError(msg)
    try:
        done = subprocess.run(  # noqa: S603
            [python, "-c", _VERSION],
            env=_environment(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAP_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        done = None
    there = done.stdout.strip() if done is not None and done.returncode == 0 else "missing"
    if there != own:
        msg = f"evidence: mutmut under {python} is {there}, not the {own} that Earnest reads"
        raise EvidenceError(msg)
    return name


def _copy(root: Path, copy: Path) -> Path:
    copy.mkdir()
    for path in git.work_tree_files(root):
        if (root / path).is_file():  # a tracked file deleted from the work tree is listed, but is not there
            (copy / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / path, copy / path)
    return copy


class _CaseConfig(configparser.ConfigParser):
    """A parser that keeps each option name's case, so a case-sensitive key such as a package name survives."""

    def optionxform(self, optionstr: str) -> str:
        return optionstr


def _configure(copy: Path, files: Sequence[str]) -> None:
    """Merge mutmut's section into the copy's `setup.cfg`, which mutmut reads only without a `[tool.mutmut]`."""
    try:
        own = "mutmut" in tomllib.loads((copy / "pyproject.toml").read_text(encoding="utf-8")).get("tool", {})
    except (OSError, tomllib.TOMLDecodeError):
        own = False
    if own:
        msg = "evidence: pyproject.toml has its own [tool.mutmut], which mutmut would read instead of Earnest's"
        raise EvidenceError(msg)
    config = _CaseConfig(interpolation=None)
    try:
        config.read(copy / "setup.cfg", encoding="utf-8")
    except configparser.Error as error:
        msg = f"evidence: setup.cfg cannot be read, so mutmut's section cannot be merged into it ({error})"
        raise EvidenceError(msg) from error
    # every top-level entry, so the tests find what they need beside `src/` and `tests/`, such as a `pytest.ini`
    entries = sorted({path.name for path in copy.iterdir()} | {"setup.cfg"})
    config["mutmut"] = {"source_paths": "\n" + "\n".join(files), "also_copy": "\n" + "\n".join(entries)}
    with (copy / "setup.cfg").open("w", encoding="utf-8") as out:
        config.write(out)


def _suite(copy: Path, report: Path, python: str) -> list[str]:
    command = [python, "-m", "pytest", f"--junitxml={report}", "-o", "junit_family=xunit1", "-p", "no:cacheprovider"]
    if _run([*command, "-q"], copy, _environment()) is None:
        msg = f"evidence: the test run timed out after {MAP_TIMEOUT} s"
        raise EvidenceError(msg)
    return failures(report)


def failures(report: Path) -> list[str]:
    """Return the node ids of the tests an xunit1 JUnit report gives as failed or in error, a case's `[...]` dropped.

    Raises:
        EvidenceError: the report is missing or cannot be parsed, so the run gave no result.
    """
    try:
        cases = list(ET.parse(report).getroot().iter("testcase"))  # noqa: S314 - Earnest's own temporary output
    except (OSError, ET.ParseError) as error:
        msg = f"evidence: the test run gave no JUnit report ({error})"
        raise EvidenceError(msg) from error
    return sorted(
        {_node_id(case) for case in cases if case.find("failure") is not None or case.find("error") is not None}
    )


def _node_id(case: ET.Element) -> str:
    path, name = case.get("file", ""), case.get("name", "").partition("[")[0]
    if not path:  # a collection error names its module alone
        return case.get("classname") or name
    owner = case.get("classname", "").removeprefix(path.removesuffix(".py").replace("/", "."))
    return "::".join([path, *(part for part in owner.split(".") if part), name])


def _mutants(copy: Path, path: str) -> list[Mutant]:
    """Read mutmut's result for path: each mutant's exit code, from `.meta`, and its line, from `mutants/<path>`."""
    try:
        codes = json.loads((copy / "mutants" / f"{path}.meta").read_text(encoding="utf-8"))["exit_code_by_key"]
        text = (copy / "mutants" / path).read_text(encoding="utf-8")
        variants, lines = _functions(text), text.split("\n")
        original = _functions((copy / path).read_text(encoding="utf-8"))
        found = [Mutant(path, _line(original, variants, lines, key), key, _code(code)) for key, code in codes.items()]
    except (OSError, ValueError, KeyError, TypeError, AttributeError, SyntaxError) as error:
        msg = f"evidence: mutmut gave no readable result for {path}"
        raise EvidenceError(msg) from error
    return sorted(found, key=lambda mutant: (mutant.line, mutant.key))


def _code(code: object) -> int | None:
    if code is not None and (not isinstance(code, int) or isinstance(code, bool)):
        raise TypeError(code)
    return code


def _functions(text: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return the functions of a module, and the methods of its classes as `Class.method`, by name."""
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            found[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for inner in node.body:
                if isinstance(inner, ast.FunctionDef | ast.AsyncFunctionDef):
                    found[f"{node.name}.{inner.name}"] = inner
    return found


def _line(
    original: Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef],
    variants: Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef],
    lines: Sequence[str],
    key: str,
) -> int:
    """Return the line a mutant changes, from the `def` line of its function in the unmutated file.

    The offset is that of the first line where its variant differs from `__mutmut_orig`, so comments above a `def`
    never shift it.
    """
    name = key.rpartition(".")[2]
    base = name.rpartition("__mutmut_")[0]
    if base.startswith(f"x{_CLICK}"):  # a method, `x<click>Class<click>method`
        owner, _, method = base[2:].partition(_CLICK)
        qualified, prefix = f"{owner}.{method}", f"{owner}."
    else:
        qualified, prefix = base.removeprefix("x_"), ""
    variant, orig = variants[prefix + name], variants[f"{prefix}{base}__mutmut_orig"]
    changed = list(lines[variant.lineno - 1 : variant.end_lineno or variant.lineno])
    unchanged = lines[orig.lineno - 1 : orig.end_lineno or orig.lineno]
    changed[0] = changed[0].replace(variant.name, orig.name, 1)
    pairs = zip(changed, unchanged, strict=False)
    offset = next((at for at, (one, other) in enumerate(pairs) if one != other), min(len(changed), len(unchanged)))
    return original[qualified].lineno + offset


def evidence_failed(root: Path, index: Index, found: Evidence) -> list[Finding]:
    """Return the `evidence-failed` findings of an evidence result, by the Region rule and mutmut's statuses.

    A surviving mutant counts only on a line of an `impl` region of a requirement, and raises one finding per line
    against each requirement whose region holds it. A failing tagged test raises one at its tag, against the
    requirement the tag names.

    Raises:
        EvidenceError: a mutant's status says the mutmut run is incomplete, or mutmut gave a code it does not list.
    """
    return [*_mutant_findings(index, _surviving(found.mutants)), *_test_findings(root, index, found.failing)]


def entries(
    root: Path, index: Index, levels: Mapping[str, str], found: Evidence, failed: Iterable[Finding]
) -> dict[str, dict[str, object]]:
    """Return the evidence entry of each requirement with an `impl` region in a mutated file, keyed as E1 gives.

    An entry's key hashes the requirement's `impl` regions and its test regions as the judge cache does, and names
    the tool. Its result is `failed` when failed, the run's `evidence_failed` findings, hold one against it, and `passed` when the run judged it
    and mutmut killed a mutant on a line of its `impl` regions; a requirement the run reached no verdict on, such as one not judged, gets no entry.

    Raises:
        OSError: a tagged file cannot be read.
    """
    files = set(mutation_files(index, levels))
    against = {each.subject for each in failed}
    kept: dict[str, dict[str, object]] = {}
    for item in index.defined.values():
        if not _mutated(index, item, files):
            continue
        req = str(item.id)
        if req in against:
            result = "failed"
        elif levels.get(req) == "judged" and _killed(index, item, found.mutants):  # none with a failing test
            result = "passed"
        else:
            continue
        kept[req] = {"key": key(root, index, item, found.tool), "result": result}
    return kept


def key(root: Path, index: Index, item: Item, name: str) -> dict[str, object]:
    """Return item's evidence key in root's work tree: its `impl` and test regions hashed as the judge cache does.

    Raises:
        OSError: a tagged file cannot be read.
    """
    code = judge.region_hash(root, judge.regions(index, item, judge.KINDS["implemented"]))
    tests = judge.region_hash(root, judge.regions(index, item, judge.KINDS["tested"]))
    return {"regions": code, "tests": tests, "tool": name}


def keys(root: Path, index: Index, held: Collection[str]) -> dict[str, dict[str, object]]:
    """Return the current key of each held requirement the index defines, under the installed mutmut; none without one.

    Raises:
        OSError: a tagged file cannot be read.
    """
    name = tool()
    if name is None:
        return {}
    return {str(item.id): key(root, index, item, name) for item in index.defined.values() if str(item.id) in held}


def merged(
    held: Mapping[str, dict[str, object]],
    fresh: Mapping[str, dict[str, object]],
    index: Index,
    levels: Mapping[str, str],
) -> dict[str, dict[str, object]]:
    """Return the evidence slot as a run leaves it: held, with the run's own requirements' entries replaced.

    The run's own are the requirements whose files it set out to mutate: each takes its fresh entry, or none when the
    run reached no verdict on it; the entries of every other requirement are kept.
    """
    files = set(mutation_files(index, levels))
    reached = {str(item.id) for item in index.defined.values() if _mutated(index, item, files)}
    return {**{req: entry for req, entry in held.items() if req not in reached}, **fresh}


def _killed(index: Index, item: Item, mutants: Iterable[Mutant]) -> bool:
    """Return whether a mutant mutmut killed sits on a line of an `impl` region of item."""
    code = judge.regions(index, item, judge.KINDS["implemented"])
    return any(
        mutant.code in _KILLED and region.path == mutant.path and region.first <= mutant.line <= region.last
        for mutant in mutants
        for region in code
    )


def _mutated(index: Index, item: Item, files: Collection[str]) -> bool:
    """Return whether item is a `req` with an `impl` region in one of the files mutmut mutates."""
    code = judge.regions(index, item, judge.KINDS["implemented"])
    return item.id.type == "req" and any(region.path in files for region in code)


def evidenced(
    levels: Mapping[str, str],
    held: Mapping[str, Mapping[str, object]],
    current: Mapping[str, Mapping[str, object]],
    *,
    judged: bool,
) -> dict[str, str]:
    """Return the levels with each requirement raised to evidenced whose entry is `passed` under its current key.

    current gives each requirement's key in the work tree, as `keys` does; an entry under any other key is stale.
    With a model a requirement must be judged; with none, traced, as only a judged requirement gets a `passed` entry.
    """
    floor = "judged" if judged else "traced"

    def counts(req: str) -> bool:
        entry = held.get(req, {})
        return entry.get("result") == "passed" and req in current and entry.get("key") == current[req]

    return {req: "evidenced" if level == floor and counts(req) else level for req, level in levels.items()}


def _surviving(mutants: Iterable[Mutant]) -> list[Mutant]:
    kept = []
    for mutant in mutants:
        if mutant.code in _SURVIVING:
            kept.append(mutant)
        elif mutant.code not in _KILLED:
            status = _INCOMPLETE.get(mutant.code, f"the exit code {mutant.code}, which mutmut does not list")
            msg = (
                f"evidence: mutmut left {mutant.key} at {mutant.path}:{mutant.line} {status}, so its run is incomplete"
            )
            raise EvidenceError(msg)
    return kept


def _mutant_findings(index: Index, mutants: Iterable[Mutant]) -> list[Finding]:
    regions = [
        (region, str(item.id))
        for item in index.defined.values()
        if item.id.type == "req"
        for region in judge.regions(index, item, judge.KINDS["implemented"])
    ]
    lines: dict[tuple[str, int], list[str]] = {}
    for mutant in mutants:
        lines.setdefault((mutant.path, mutant.line), []).append(mutant.key.rpartition(".")[2])
    return [
        _failed(path, line, req, f"the mutant {', '.join(names)} survives the tests: add a test that kills it")
        for (path, line), names in sorted(lines.items())
        for req in sorted(
            {req for region, req in regions if region.path == path and region.first <= line <= region.last}
        )
    ]


def _test_findings(root: Path, index: Index, failing: Collection[str]) -> list[Finding]:
    nearest: dict[tuple[str, tuple[str, str]], Link] = {}  # each failing test and requirement, at its closest tag
    tagged = _test_tags(root, index, [key for key in index.defined if key[0] == "req"])
    for link, nodes in sorted(tagged, key=lambda pair: (pair[0].path, pair[0].line)):
        for node in set(nodes) & set(failing):
            nearest[node, link.target.key] = link  # a later tag of one id is closer, as its nodes start at the tag
    tags: dict[Link, list[str]] = {}
    for (node, _), link in sorted(nearest.items()):
        tags.setdefault(link, []).append(node)
    return [
        _failed(
            link.path,
            link.line,
            str(index.defined[link.target.key].id),
            f"its test {', '.join(nodes)} fails on the unmutated code: fix the test or the code",
        )
        for link, nodes in tags.items()
    ]


def _failed(path: str, line: int, req: str, cause: str) -> Finding:
    return Finding(path, line, "earnest/evidence-failed", req, evidence_message(req, path, line, cause))


def stryker_survivors(report: Path) -> list[tuple[str, int]]:
    """Return the file and line of each `Survived` or `NoCoverage` mutant of a StrykerJS report, sorted, once each.

    Raises:
        EvidenceError: the report cannot be read or is not of the mutation-testing-report schema.
    """
    try:
        files = json.loads(report.read_text(encoding="utf-8"))["files"]
        return sorted(
            {
                (path, int(mutant["location"]["start"]["line"]))
                for path, entry in files.items()
                for mutant in entry["mutants"]
                if mutant["status"] in {"Survived", "NoCoverage"}  # no test kills it, as mutmut's no tests
            }
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        msg = f"evidence: the StrykerJS report {report} cannot be read"
        raise EvidenceError(msg) from error
