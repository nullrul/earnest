"""Tests for earnest."""

from earnest import __version__


def test_version() -> None:
    """Version is set."""
    assert __version__ == "0.1.0"
