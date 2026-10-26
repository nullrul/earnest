"""Tests for the conftest helpers that build fixture repositories."""

from pathlib import Path

import pytest

import tests.conftest
from tests.conftest import _leave_out


def test_fixture_copy_leaves_out_overlays_and_bytecode_but_keeps_ordinary_files(tmp_path: Path):
    ignore = _leave_out(tmp_path, "change")
    names = ["change", "__pycache__", "mod.cpython-312.pyc", "README.md"]
    assert sorted(ignore(str(tmp_path), names)) == ["__pycache__", "change", "mod.cpython-312.pyc"]


def _overlay_with_bytecode(root: Path) -> Path:
    overlay = root / "fx" / "change" / "src"
    (overlay / "__pycache__").mkdir(parents=True)
    (overlay / "a.py").write_text("x = 1\n")
    (overlay / "__pycache__" / "a.cpython-312.pyc").write_bytes(b"\0")
    return overlay


def test_overlay_files_leaves_out_nested_bytecode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _overlay_with_bytecode(tmp_path)
    monkeypatch.setattr(tests.conftest, "FIXTURES", tmp_path)
    assert tests.conftest._overlay_files("fx", "change") == ["src/a.py"]


def test_write_overlays_copies_no_bytecode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _overlay_with_bytecode(tmp_path)
    monkeypatch.setattr(tests.conftest, "FIXTURES", tmp_path)
    repo = tmp_path / "repo"
    assert tests.conftest.write_overlays(repo, "fx", "change") == ["src/a.py"]
    assert not (repo / "src" / "__pycache__").exists()


def test_leave_out_matches_a_nested_path(tmp_path: Path):
    ignore = _leave_out(tmp_path, "units/aidlc")
    assert ignore(str(tmp_path / "units"), ["aidlc", "other"]) == ["aidlc"]
