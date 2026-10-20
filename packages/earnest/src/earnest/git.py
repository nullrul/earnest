"""Repository reader: the work tree's root, the files Git lists for it, its commit and branch, and what changed."""

import re
import shutil
import subprocess
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path


_RECORD_DIRECTORY = ".earnest"
_DEFAULT = "main"
_HUNK = re.compile(r"@@ -([0-9]+)(?:,([0-9]+))? \+([0-9]+)(?:,([0-9]+))? @@")
_SHA = re.compile(r"[0-9a-f]{4,64}")


@dataclass(frozen=True)
class Hunk:
    """One hunk of a `-U0` diff: the old lines it replaces and the new lines it writes, each from its first line.

    A side with no lines starts at the line before the change, as Git writes it.
    """

    old_start: int
    old_count: int
    new_start: int
    new_count: int

    @property
    def new_lines(self) -> range:
        """Return the numbers of the lines the hunk writes."""
        return range(self.new_start, self.new_start + self.new_count)

    def paired(self, line: int) -> int | None:
        """Return the old line that the hunk pairs a new line with, in order, or None past the old side's end."""
        offset = line - self.new_start
        return self.old_start + offset if 0 <= offset < self.old_count else None

    @property
    def deleted_lines(self) -> range:
        """Return the numbers of the old lines the hunk deletes: those past the pairing with its new lines."""
        return range(self.old_start + self.new_count, self.old_start + self.old_count)

    def before(self, line: int) -> bool:
        """Return whether the hunk lies wholly before a new line, so it shifts that line's old number."""
        return self.new_start < line if self.new_count == 0 else self.new_start + self.new_count <= line


class GitError(Exception):
    """Git could not answer: no work tree, no commit, or no `git` on the PATH; the message is Git's first line."""


def repo_root(cwd: Path) -> Path:
    """Return the top of the work tree that holds cwd, so a check run in a subdirectory reads the whole repository."""
    return Path(_git(cwd, "rev-parse", "--show-toplevel").removesuffix("\n"))


def work_tree_files(root: Path) -> list[str]:
    """Return the files Git lists for the work tree: tracked files plus untracked files that are not ignored.

    Each path is relative to root, with forward slashes, sorted, and listed once, even a file in a merge conflict,
    which the index holds three times. Nothing under `.earnest/`, the assessment record's directory, is listed,
    whether Git ignores it or a repository tracks it.
    """
    listed = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return sorted({path for path in listed.split("\0") if path and not _in_record_directory(path)})


def changes(root: Path) -> list[str]:
    """Return the paths that differ from the commit: untracked, changed in the work tree or the index, or missing.

    One `git status` gives them, sorted and listed once, with a rename as the two paths it touches and nothing under
    `.earnest/`. `--no-optional-locks` keeps Git from refreshing `.git/index`, so a read-only command stays read-only.
    """
    listed = _git(
        root, "--no-optional-locks", "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames"
    )
    paths = {entry[3:] for entry in listed.split("\0") if entry}  # each entry is two status letters, a space, a path
    return sorted(path for path in paths if not _in_record_directory(path))


def head_commit(root: Path) -> str:
    """Return the full sha of the commit HEAD names."""
    return _git(root, "rev-parse", "HEAD").strip()


def current_branch(root: Path) -> str | None:
    """Return the short name of the branch HEAD names, or None on a detached HEAD."""
    name = _maybe(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    return name.strip() if name else None


def default_branch(root: Path) -> str:
    """Return the branch `refs/remotes/origin/HEAD` names, as a full ref, or `main` when it is not set."""
    name = _maybe(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    return name.strip() if name else _DEFAULT


def merge_base(root: Path, branch: str) -> str:
    """Return the full sha of the merge-base of HEAD with branch."""
    return _git(root, "merge-base", "HEAD", branch).strip()


def has_commit(root: Path, sha: str) -> bool:
    """Return whether sha, a hex string, names a commit the repository holds."""
    return _SHA.fullmatch(sha) is not None and _maybe(root, "cat-file", "-e", f"{sha}^{{commit}}") is not None


def changed_lines(
    root: Path, base: str, paths: Collection[str], *, keep_deletions: bool = False
) -> dict[str, tuple[Hunk, ...]]:
    """Return the hunks that changed each of paths from the commit base to the work tree, untracked files included.

    A path that has no new line is left out, unless `keep_deletions` keeps a path whose hunks only delete, and so is
    every path under `.earnest/`. An untracked file is one hunk that adds all its lines; an untracked symlink is
    skipped, so its target is never read. `--no-optional-locks` leaves `.git/index` alone.
    """
    wanted = {path for path in paths if not _in_record_directory(path)}
    # diff-index, the plumbing: `git diff` refreshes `.git/index` even under --no-optional-locks. A file touched but
    # not changed is listed by its stat alone, and its patch holds no hunk.
    listed = _git(root, "--no-optional-locks", "diff-index", "--name-only", "-z", "--no-renames", base, "--")
    untracked = _git(root, "--no-optional-locks", "ls-files", "-z", "--others", "--exclude-standard")
    found: dict[str, tuple[Hunk, ...]] = {}
    for path in sorted({name for name in listed.split("\0") if name} & wanted):
        hunks = _hunks(_git(root, "--no-optional-locks", *_DIFF, base, "--", path))
        if any(hunk.new_count or (keep_deletions and hunk.old_count) for hunk in hunks):
            found[path] = hunks
    for path in sorted({name for name in untracked.split("\0") if name} & wanted):
        file = root / path
        count = _line_count(file.read_bytes()) if file.is_file() and not file.is_symlink() else 0
        if count:
            found[path] = (Hunk(0, 0, 1, count),)
    return dict(sorted(found.items()))


def deleted_files(root: Path, base: str) -> list[str]:
    """Return the paths of the commit base that the work tree no longer holds, sorted, with none under `.earnest/`."""
    listed = _git(
        root, "--no-optional-locks", "diff-index", "--name-only", "-z", "--no-renames", "--diff-filter=D", base, "--"
    )
    return sorted({path for path in listed.split("\0") if path and not _in_record_directory(path)})


def old_line(hunks: Sequence[Hunk], line: int) -> int | None:
    """Return the line of the old side that a new line was, or None for a line the hunks add past their pairing."""
    for hunk in hunks:
        if line in hunk.new_lines:
            return hunk.paired(line)
    return line + sum(hunk.old_count - hunk.new_count for hunk in hunks if hunk.before(line))


_DIFF = (
    "diff-index",
    "-p",
    "--no-ext-diff",
    "--no-textconv",
    "--no-color",
    "--no-renames",
    "--diff-algorithm=myers",
    "-U0",
)


def _hunks(patch: str) -> tuple[Hunk, ...]:
    found = []
    for line in patch.split("\n"):
        if (match := _HUNK.match(line)) is not None:
            old, old_count, new, new_count = match.groups()
            found.append(Hunk(int(old), int(old_count or 1), int(new), int(new_count or 1)))
    return tuple(found)


def _line_count(data: bytes) -> int:
    """Return the lines Git counts in data: one per newline, and one more for a last line without one."""
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def _maybe(cwd: Path, *args: str) -> str | None:
    """Return what a Git call prints, or None when it fails, for a question whose failure is an answer."""
    try:
        return _git(cwd, *args)
    except GitError:
        return None


def _in_record_directory(path: str) -> bool:
    return path == _RECORD_DIRECTORY or path.startswith(_RECORD_DIRECTORY + "/")


def _git(cwd: Path, *args: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        msg = "git is not on the PATH"
        raise GitError(msg)
    # --literal-pathspecs: a path given to any call is a name, never a pattern, whatever `*`, `[` or `:` it holds
    done = subprocess.run([executable, "--literal-pathspecs", *args], cwd=cwd, capture_output=True, check=False)  # noqa: S603
    if done.returncode != 0:
        lines = map(str.strip, done.stderr.decode(errors="replace").splitlines())
        msg = next((line for line in lines if line), f"git {next(a for a in args if not a.startswith('-'))} failed")
        raise GitError(msg)
    # decoded from bytes, so no newline is translated, and a name that is not UTF-8 reaches the file system intact
    return done.stdout.decode("utf-8", "surrogateescape")
