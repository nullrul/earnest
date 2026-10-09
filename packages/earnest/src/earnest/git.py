"""Repository reader: the work tree's root, the files Git lists for it, and its commit, read through Git."""

import shutil
import subprocess
from pathlib import Path


class GitError(Exception):
    """Git could not answer: no work tree, no commit, or no `git` on the PATH; the message is Git's first line."""


def repo_root(cwd: Path) -> Path:
    """Return the top of the work tree that holds cwd, so a check run in a subdirectory reads the whole repository."""
    return Path(_git(cwd, "rev-parse", "--show-toplevel").removesuffix("\n"))


def work_tree_files(root: Path) -> list[str]:
    """Return the files Git lists for the work tree: tracked files plus untracked files that are not ignored.

    Each path is relative to root, with forward slashes, sorted, and listed once, even a file in a merge conflict,
    which the index holds three times.
    """
    listed = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return sorted({path for path in listed.split("\0") if path})


def head_commit(root: Path) -> str:
    """Return the full sha of the commit HEAD names."""
    return _git(root, "rev-parse", "HEAD").strip()


def _git(cwd: Path, *args: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        msg = "git is not on the PATH"
        raise GitError(msg)
    done = subprocess.run([executable, *args], cwd=cwd, capture_output=True, check=False)  # noqa: S603
    if done.returncode != 0:
        lines = done.stderr.decode(errors="replace").splitlines()
        msg = next((line.strip() for line in lines if line.strip()), f"git {args[0]} failed")
        raise GitError(msg)
    # decoded from bytes, so no newline is translated, and a name that is not UTF-8 reaches the file system intact
    return done.stdout.decode("utf-8", "surrogateescape")
