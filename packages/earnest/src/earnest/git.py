"""Repository reader: the work tree's root, the files Git lists for it, and its commit, read through Git."""

import shutil
import subprocess
from pathlib import Path


_RECORD_DIRECTORY = ".earnest"


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
