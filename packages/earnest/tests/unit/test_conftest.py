"""Tests for the conftest helpers that build fixture repositories."""

from pathlib import Path

import pytest

import tests.conftest
from tests.conftest import _is_bytecode, _leave_out
from tests.sarif import git_output


def test_fixture_copy_leaves_out_overlays_and_bytecode_but_keeps_ordinary_files(tmp_path: Path):
    ignore = _leave_out(tmp_path, "change")
    names = ["change", "__pycache__", "mod.cpython-312.pyc", "README.md"]
    assert sorted(ignore(str(tmp_path), names)) == ["__pycache__", "change", "mod.cpython-312.pyc"]


def _plant_bytecode(directory: Path) -> None:
    (directory / "__pycache__").mkdir(parents=True)
    (directory / "__pycache__" / "a.cpython-312.pyc").write_bytes(b"\0")


def _overlay_with_bytecode(root: Path) -> None:
    overlay = root / "fx" / "change" / "src"
    overlay.mkdir(parents=True)
    (overlay / "a.py").write_text("x = 1\n")
    _plant_bytecode(overlay)


def test_write_overlays_copies_no_bytecode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _overlay_with_bytecode(tmp_path)
    monkeypatch.setattr(tests.conftest, "FIXTURES", tmp_path)
    repo = tmp_path / "repo"
    assert tests.conftest.write_overlays(repo, "fx", "change") == ["src/a.py"]
    assert not (repo / "src" / "__pycache__").exists()


def test_leave_out_matches_a_nested_path(tmp_path: Path):
    ignore = _leave_out(tmp_path, "units/aidlc")
    assert ignore(str(tmp_path / "units"), ["aidlc", "other"]) == ["aidlc"]


def _tracked(repo: Path) -> list[str]:
    return git_output(repo, "ls-files").splitlines()


def test_commit_overlay_tracks_no_bytecode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, files_repo, commit_overlay):
    _overlay_with_bytecode(tmp_path)
    monkeypatch.setattr(tests.conftest, "FIXTURES", tmp_path)
    repo = commit_overlay(files_repo({"base.txt": "base\n"}), "fx", "branch")
    tracked = _tracked(repo)
    assert "src/a.py" in tracked
    assert not [path for path in tracked if _is_bytecode(Path(path))]
    assert not (repo / "src" / "__pycache__").exists()


def test_units_repo_tracks_no_bytecode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, units_repo):
    fixtures = tmp_path / "fixtures"
    aidlc = fixtures / "seeded-change" / "units" / "aidlc"
    aidlc.mkdir(parents=True)
    (aidlc / "state.md").write_text("state\n")
    _plant_bytecode(aidlc)
    (fixtures / "seeded-change" / "base.txt").write_text("base\n")
    monkeypatch.setattr(tests.conftest, "FIXTURES", fixtures)
    repo = units_repo()
    tracked = _tracked(repo)
    assert "aidlc/state.md" in tracked
    assert not [path for path in tracked if _is_bytecode(Path(path))]
    assert not (repo / "aidlc" / "__pycache__").exists()
