"""Tests for the conftest helpers that build fixture repositories."""

from pathlib import Path

from tests.conftest import _leave_out


def test_fixture_copy_leaves_out_overlays_and_bytecode_but_keeps_ordinary_files(tmp_path: Path):
    ignore = _leave_out(tmp_path, "change")
    names = ["change", "__pycache__", "mod.cpython-312.pyc", "README.md"]
    assert sorted(ignore(str(tmp_path), names)) == ["__pycache__", "change", "mod.cpython-312.pyc"]
