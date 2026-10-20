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


# The task's base and the lines changed since it (M3).


def _commit_all(repo, message="next"):
    git_output(repo, "add", "-A")
    git_output(repo, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", message)


def test_current_branch_names_the_checked_out_branch(files_repo):
    repo = files_repo({"a.md": "a\n"})
    git_output(repo, "checkout", "-q", "-b", "task/add-limiter-window")
    assert git.current_branch(repo) == "task/add-limiter-window"


def test_current_branch_is_none_on_a_detached_head(files_repo):
    repo = files_repo({"a.md": "a\n"})
    git_output(repo, "checkout", "-q", "--detach")
    assert git.current_branch(repo) is None


def test_default_branch_is_main_without_an_origin_head(files_repo):
    assert git.default_branch(files_repo({"a.md": "a\n"})) == "main"


def test_default_branch_follows_origin_head(files_repo):
    repo = files_repo({"a.md": "a\n"})
    head = git.head_commit(repo)
    git_output(repo, "update-ref", "refs/remotes/origin/trunk", head)
    git_output(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
    assert git.default_branch(repo) == "refs/remotes/origin/trunk"


def test_merge_base_is_the_fork_point_of_a_branch(files_repo):
    repo = files_repo({"a.md": "a\n"})
    base = git.head_commit(repo)
    git_output(repo, "checkout", "-q", "-b", "task/x-y")
    (repo / "a.md").write_text("b\n", encoding="utf-8")
    _commit_all(repo)
    assert git.merge_base(repo, "main") == base


def test_has_commit_tells_a_commit_from_an_unknown_sha(files_repo):
    repo = files_repo({"a.md": "a\n"})
    assert git.has_commit(repo, git.head_commit(repo))
    assert not git.has_commit(repo, "0" * 40)
    assert not git.has_commit(repo, "--all")


def test_changed_lines_reads_modified_added_and_deleted_lines_as_hunks(files_repo):
    repo = files_repo({"a.py": "1\n2\n3\n4\n5\n6\n7\n8\n"})
    base = git.head_commit(repo)
    (repo / "a.py").write_text("1\nTWO\n3\n5\n6\nSIX-A\nSIX-B\n\n7\n8\n", encoding="utf-8")
    hunks = git.changed_lines(repo, base, {"a.py"})["a.py"]
    assert [(h.old_start, h.old_count, h.new_start, h.new_count) for h in hunks] == [
        (2, 1, 2, 1),
        (4, 1, 3, 0),
        (6, 0, 6, 3),
    ]
    assert [line for hunk in hunks for line in hunk.new_lines] == [2, 6, 7, 8]  # the blank added line counts
    assert hunks[0].paired(2) == 2
    assert hunks[2].paired(6) is None


def test_a_hunk_pairs_its_new_lines_with_its_old_ones_up_to_the_shorter_side():
    hunk = git.Hunk(old_start=5, old_count=2, new_start=7, new_count=3)
    assert [hunk.paired(line) for line in hunk.new_lines] == [5, 6, None]


def test_old_line_remaps_an_unchanged_line_across_the_hunks_before_it():
    hunks = (git.Hunk(2, 1, 2, 1), git.Hunk(4, 1, 3, 0), git.Hunk(6, 0, 6, 3))
    assert [git.old_line(hunks, line) for line in (1, 2, 3, 4, 5, 6, 9, 10)] == [1, 2, 3, 5, 6, None, 7, 8]


def test_changed_lines_reads_an_untracked_file_as_added_whole(files_repo):
    repo = files_repo({"a.md": "a\n"})
    (repo / "new file.md").write_text("x\n\ny", encoding="utf-8")
    hunks = git.changed_lines(repo, git.head_commit(repo), {"new file.md", "a.md"})
    assert list(hunks) == ["new file.md"]
    assert [list(hunk.new_lines) for hunk in hunks["new file.md"]] == [[1, 2, 3]]
    assert hunks["new file.md"][0].paired(1) is None


def test_changed_lines_keeps_only_the_paths_asked_for_and_never_the_record(files_repo):
    repo = files_repo({"a.md": "a\n", "b.md": "b\n"})
    base = git.head_commit(repo)
    for name in ("a.md", "b.md"):
        (repo / name).write_text("changed\n", encoding="utf-8")
    (repo / ".earnest").mkdir()
    (repo / ".earnest" / "x.md").write_text("x\n", encoding="utf-8")
    assert list(git.changed_lines(repo, base, {"a.md", ".earnest/x.md"})) == ["a.md"]


def test_changed_lines_reads_several_hunks_of_names_with_glob_characters_and_crlf(files_repo):
    names = ["x[1].md", "*.md", "a b.md"]
    repo = files_repo(dict.fromkeys(names, "1\r\n2\r\n3\r\n4\r\n5\r\n"))
    base = git.head_commit(repo)
    for name in names:
        (repo / name).write_text("ONE\r\n2\r\n3\r\n4\r\nFIVE\r\n", encoding="utf-8", newline="")
    found = git.changed_lines(repo, base, set(names))
    assert sorted(found) == sorted(names)
    assert all([list(hunk.new_lines) for hunk in hunks] == [[1], [5]] for hunks in found.values())


def test_changed_lines_spans_commits_and_the_work_tree_and_skips_a_deleted_file(files_repo):
    repo = files_repo({"a.md": "a\n", "b.md": "b\n"})
    base = git.head_commit(repo)
    (repo / "a.md").write_text("a\ncommitted\n", encoding="utf-8")
    _commit_all(repo)
    (repo / "a.md").write_text("a\ncommitted\nuncommitted\n", encoding="utf-8")
    (repo / "b.md").unlink()
    found = git.changed_lines(repo, base, {"a.md", "b.md"})
    assert [list(hunk.new_lines) for hunk in found["a.md"]] == [[2, 3]]
    assert "b.md" not in found


def test_changed_lines_leaves_the_index_alone(files_repo):
    repo = files_repo({"a.md": "a\n"})
    base = git.head_commit(repo)
    stamp = (repo / "a.md").stat().st_mtime_ns + 5_000_000_000
    os.utime(repo / "a.md", ns=(stamp, stamp))
    index = repo / ".git" / "index"
    before = (index.read_bytes(), index.stat().st_mtime_ns)
    assert git.changed_lines(repo, base, {"a.md"}) == {}
    assert (index.read_bytes(), index.stat().st_mtime_ns) == before


def test_changed_lines_keeps_a_deletion_only_file_when_asked(files_repo):
    repo = files_repo({"a.py": "1\n2\n3\n4\n"})
    base = git.head_commit(repo)
    (repo / "a.py").write_text("1\n4\n", encoding="utf-8")
    assert git.changed_lines(repo, base, {"a.py"}) == {}
    assert git.changed_lines(repo, base, {"a.py"}, keep_deletions=True) == {"a.py": (git.Hunk(2, 2, 1, 0),)}


def test_a_hunk_lists_the_old_lines_it_deletes_past_its_pairing():
    assert list(git.Hunk(2, 2, 1, 0).deleted_lines) == [2, 3]
    assert list(git.Hunk(5, 3, 5, 1).deleted_lines) == [6, 7]
    assert list(git.Hunk(5, 1, 5, 2).deleted_lines) == []


def test_changed_lines_skips_an_untracked_symlink_and_never_reads_its_target(files_repo, tmp_path):
    repo = files_repo({"a.md": "a\n"})
    outside = tmp_path / "outside.md"
    outside.write_text("1\n2\n3\n", encoding="utf-8")
    (repo / "link.md").symlink_to(outside)
    assert git.changed_lines(repo, git.head_commit(repo), {"link.md"}) == {}


def test_deleted_files_lists_the_paths_of_the_base_missing_from_the_work_tree(files_repo):
    repo = files_repo({"a.py": "1\n2\n", "b.py": "b\n", "c.py": "c\n", "d b[1].py": "d\n"})
    base = git.head_commit(repo)
    git_output(repo, "rm", "-q", "a.py")
    _commit_all(repo)
    (repo / "b.py").unlink()
    (repo / "d b[1].py").unlink()
    (repo / "c.py").write_text("changed\n", encoding="utf-8")
    assert git.deleted_files(repo, base) == ["a.py", "b.py", "d b[1].py"]
    assert git.changed_lines(repo, base, {"a.py"}, keep_deletions=True) == {"a.py": (git.Hunk(1, 2, 0, 0),)}
