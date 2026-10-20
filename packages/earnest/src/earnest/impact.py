"""Impact: the coverage map that `check --stage` takes, and the requirements, features and tests a change impacts."""

import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path


COVERAGE = ".earnest/coverage"
# The variables of a test run that is already going, which would steer the map run into that run's data and options.
_INHERITED = ("PYTEST_", "COV_CORE_", "COVERAGE_")

_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")  # a commit, so a record that names anything else names no path
CoverageMap = dict[tuple[str, int], tuple[str, ...]]


def map_file(root: Path, commit: str) -> Path:
    """Return the coverage data file of the map taken at commit."""
    return root / COVERAGE / commit


def _report(root: Path, commit: str) -> Path:
    return root / COVERAGE / f"{commit}.json"


def is_commit(text: object) -> bool:
    """Return whether text is a full commit sha, the only name a coverage map is kept under."""
    return isinstance(text, str) and _SHA.fullmatch(text) is not None


def take_map(root: Path, commit: str, python: str = sys.executable) -> None:
    """Take the coverage map at commit: run the repository's tests under pytest-cov with per-test contexts.

    The run uses the interpreter that runs Earnest. Its data file is `.earnest/coverage/<commit>` and its JSON report,
    with the contexts, `.earnest/coverage/<commit>.json`; it writes nothing else, so no cache, bytecode or `.coverage`
    file reaches the work tree, and the repository's own `addopts` and coverage configuration are left out. A failing
    test still gives a map; a run that gives no data, as with no pytest or no test, leaves an empty map.

    Raises:
        OSError: `.earnest/coverage/` cannot be written.
        ValueError: commit is not a full commit sha.
    """
    if not is_commit(commit):
        msg = f"{commit!r} is not a commit"
        raise ValueError(msg)
    directory = root / COVERAGE
    directory.mkdir(parents=True, exist_ok=True)
    report = _report(root, commit)
    report.unlink(missing_ok=True)
    env = {name: value for name, value in os.environ.items() if not name.startswith(_INHERITED)}
    env |= {"COVERAGE_FILE": str(map_file(root, commit)), "PYTHONDONTWRITEBYTECODE": "1"}
    tests = ["--cov=.", "--cov-context=test", "--cov-report=", f"--cov-config={os.devnull}"]
    options = ["-p", "no:cacheprovider", "-o", "addopts=", "-q"]
    _run([python, "-m", "pytest", *tests, *options], root, env)
    _run([python, "-m", "coverage", "json", "--show-contexts", f"--rcfile={os.devnull}", "-o", str(report)], root, env)
    if not report.is_file():
        report.write_text(json.dumps({"files": {}}) + "\n", encoding="utf-8")


def _run(command: list[str], root: Path, env: Mapping[str, str]) -> None:
    # the repository's own tests, run as `check --stage` promises; their exit code is no part of the map
    subprocess.run(command, cwd=root, env=env, capture_output=True, check=False)  # noqa: S603


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
