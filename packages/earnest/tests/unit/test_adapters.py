"""Tests for earnest.adapters: the adapter picked by suffix for each listed file, and how its bytes are read."""

from earnest import adapters
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Line


def test_each_suffix_gets_its_adapter_and_other_files_are_skipped(tmp_path):
    files = {
        "a.md": "`req~a~1`\n",
        "b.py": "# [impl->req~a~1]\nx = 1\n",
        "c.ts": "// [impl->req~a~1]\n",
        "d.mts": "// [impl->req~a~1]\n",
        "e.cts": "// [impl->req~a~1]\n",
        "f.tsx": "// [impl->req~a~1]\n",
        "g.feature": "@stest:feat~f~1\nScenario: S\n",
        "h.txt": "[impl->req~a~1]\n",
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    sources = adapters.scan(tmp_path, [*files, "gone.py"])
    assert [(source.path, source.surface, len(source.lines)) for source in sources] == [
        ("a.md", MARKDOWN, 1),
        ("b.py", COMMENT, 1),
        ("c.ts", COMMENT, 1),
        ("d.mts", COMMENT, 1),
        ("e.cts", COMMENT, 1),
        ("f.tsx", COMMENT, 1),
        ("g.feature", GHERKIN, 1),
    ]


def test_a_byte_order_mark_is_dropped(tmp_path):
    (tmp_path / "a.md").write_bytes(b"\xef\xbb\xbf`req~a~1`\n")
    (source,) = adapters.scan(tmp_path, ["a.md"])
    assert source.lines == (Line(1, "`req~a~1`"),)


def test_a_binary_file_is_skipped(tmp_path):
    (tmp_path / "a.ts").write_bytes(b"// [impl->req~a~1]\n\0\n")
    assert adapters.scan(tmp_path, ["a.ts"]) == []


def test_text_that_is_not_utf_8_keeps_its_lines_with_replacement_characters(tmp_path):
    (tmp_path / "a.md").write_bytes(b"# Caf\xe9\n\n`req~a~1`\n")
    (source,) = adapters.scan(tmp_path, ["a.md"])
    assert source.lines == (Line(1, "# Caf\ufffd"), Line(2, ""), Line(3, "`req~a~1`"))


def test_a_tracked_symlink_is_not_scanned(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("`req~a~1`\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").symlink_to("CLAUDE.md")
    assert [source.path for source in adapters.scan(tmp_path, ["AGENTS.md", "CLAUDE.md"])] == ["CLAUDE.md"]
