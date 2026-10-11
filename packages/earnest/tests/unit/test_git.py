"""Tests for earnest.git: the work tree's root, the files Git lists for it, and its commit."""

import os
import re

import pytest

from earnest import git
from tests.sarif import git_output


def test_work_tree_files_are_relative_to_the_root_even_with_spaces_and_accents(files_repo):
    repo = files_repo({"docs/a b.md": "a\n", "src/né.py": "x = 1\n", "top.ts": "let y = 2;\n"})
    assert git.work_tree_files(repo) == ["docs/a b.md", "src/né.py", "top.ts"]


def test_untracked_files_count_and_ignored_ones_do_not(files_repo):
    repo = files_repo({".gitignore": "build/\n", "a.md": "a\n"})
    (repo / "b.md").write_text("b\n", encoding="utf-8")
    (repo / "build").mkdir()
    (repo / "build" / "c.md").write_text("c\n", encoding="utf-8")
    assert git.work_tree_files(repo) == [".gitignore", "a.md", "b.md"]


def test_the_root_of_a_subdirectory_is_the_top_of_the_work_tree(files_repo):
    repo = files_repo({"packages/app/a.py": "x = 1\n"})
    assert git.repo_root(repo / "packages" / "app") == repo.resolve()


def test_the_head_commit_is_a_full_sha(files_repo):
    repo = files_repo({"a.md": "a\n"})
    assert re.fullmatch(r"[0-9a-f]{40}", git.head_commit(repo))


def test_a_directory_outside_any_work_tree_raises_git_errors_first_line(tmp_path, monkeypatch):
    monkeypatch.setenv("LC_ALL", "C")
    with pytest.raises(git.GitError) as error:
        git.repo_root(tmp_path)
    assert str(error.value).startswith("fatal: not a git repository")
    assert "\n" not in str(error.value)


def test_a_missing_git_raises_git_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(git.GitError, match="git is not on the PATH"):
        git.repo_root(tmp_path)


def test_work_tree_files_drops_the_record_directory(files_repo):
    repo = files_repo({"a.md": "a\n"})
    (repo / ".earnest").mkdir()
    (repo / ".earnest" / "assessment.json").write_text("{}\n", encoding="utf-8")
    assert git.work_tree_files(repo) == ["a.md"]


def test_work_tree_files_drops_a_tracked_record(files_repo):
    repo = files_repo({"a.md": "a\n", ".earnest/assessment.json": "{}\n", ".earnestry/b.md": "b\n"})
    assert git.work_tree_files(repo) == [".earnestry/b.md", "a.md"]


def test_changes_is_empty_for_a_clean_tree(files_repo):
    assert git.changes(files_repo({"a.md": "a\n", "b.md": "b\n"})) == []


def test_changes_lists_a_modified_file(files_repo):
    repo = files_repo({"a.md": "a\n", "b.md": "b\n"})
    (repo / "a.md").write_text("changed\n", encoding="utf-8")
    assert git.changes(repo) == ["a.md"]


def test_changes_lists_an_untracked_file(files_repo):
    repo = files_repo({"a.md": "a\n"})
    (repo / "docs").mkdir()
    (repo / "docs" / "new.md").write_text("new\n", encoding="utf-8")
    assert git.changes(repo) == ["docs/new.md"]


def test_changes_lists_a_staged_only_change(files_repo):
    repo = files_repo({"a.md": "a\n"})
    (repo / "a.md").write_text("changed\n", encoding="utf-8")
    git_output(repo, "add", "a.md")
    assert git.changes(repo) == ["a.md"]


def test_changes_lists_a_deleted_file_and_a_staged_deletion(files_repo):
    repo = files_repo({"a.md": "a\n", "b.md": "b\n", "c.md": "c\n"})
    (repo / "a.md").unlink()
    git_output(repo, "rm", "-q", "b.md")
    assert git.changes(repo) == ["a.md", "b.md"]


def test_changes_lists_both_paths_of_a_rename_as_separate_changes(files_repo):
    repo = files_repo({"a.md": "a\n", "b.md": "b\n"})
    git_output(repo, "mv", "a.md", "c.md")
    assert git.changes(repo) == ["a.md", "c.md"]


def test_changes_drops_the_record_directory(files_repo):
    repo = files_repo({"a.md": "a\n", ".earnest/assessment.json": "{}\n"})
    (repo / "a.md").write_text("changed\n", encoding="utf-8")
    (repo / ".earnest" / "assessment.json").write_text('{"version": 1}\n', encoding="utf-8")
    (repo / ".earnest" / "temp").write_text("x\n", encoding="utf-8")
    assert git.changes(repo) == ["a.md"]


def test_changes_reads_names_with_spaces_accents_and_glob_characters_literally(files_repo):
    names = ["docs/a b.md", "src/né.py", "x[1].md", "*.md", "dir/:(top).md"]
    repo = files_repo(dict.fromkeys(names, "a\n"))
    for name in names:
        (repo / name).write_text("changed\n", encoding="utf-8")
    assert git.changes(repo) == sorted(names)


def test_git_calls_treat_pathspec_magic_literally(files_repo):
    repo = files_repo({"a.md": "a\n", "*.md": "star\n"})
    assert git._git(repo, "ls-files", "--", "*.md") == "*.md\n"


def test_changes_leaves_the_index_alone(files_repo):
    repo = files_repo({"a.md": "a\n"})
    stamp = (repo / "a.md").stat().st_mtime_ns + 5_000_000_000  # touched, not changed: Git would refresh its entry
    os.utime(repo / "a.md", ns=(stamp, stamp))
    index = repo / ".git" / "index"
    before = (index.read_bytes(), index.stat().st_mtime_ns)
    assert git.changes(repo) == []
    assert (index.read_bytes(), index.stat().st_mtime_ns) == before
    assert not (repo / ".git" / "index.lock").exists()
