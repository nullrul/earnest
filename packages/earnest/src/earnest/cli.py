"""Command surface: `earnest check`, which wires the scanner, the index, the checks and the reporter."""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from earnest import adapters, git, reporter, structural
from earnest.index import build_index


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return its exit code.

    The exit code is 0 when no error-level finding sits at position behind or current, 1 when one does, and 2 when
    the check cannot run: Git cannot answer, a file cannot be read, or the reader of the log or the summary goes away.
    """
    parser = argparse.ArgumentParser(prog="earnest", description="Requirements traceability for LLM-written code.")
    # main never dispatches on the command, so a bare `earnest` must stop here rather than run the check
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="trace the repository; SARIF 2.1.0 on stdout, a summary on stderr")
    parser.parse_args(argv)
    try:
        root = git.repo_root(Path.cwd())
        commit = git.head_commit(root)
        sources = adapters.scan(root, git.work_tree_files(root))
    except (git.GitError, OSError) as error:
        sys.stderr.write(f"earnest: {error}\n")
        return 2
    index = build_index(sources)
    findings = structural.check(index)
    levels = structural.traced(index)
    try:
        sys.stdout.write(reporter.sarif(findings, levels, commit))
        sys.stdout.flush()
        sys.stderr.write(reporter.summary(findings, levels))
        sys.stderr.flush()
    except BrokenPipeError:  # a reader went away, as `head` does: send what is left to devnull, so exit stays quiet
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.dup2(devnull, sys.stderr.fileno())
        return 2
    # ponytail: every finding sits at position current until stages exist, so any error-level one fails the check
    return 1 if any(finding.level == "error" for finding in findings) else 0
