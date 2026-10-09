"""Tests for earnest.git: the work tree's root, the files Git lists for it, and its commit."""

import re

import pytest

from earnest import git


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
