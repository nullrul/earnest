"""Tests for earnest.adapters: the adapter picked by suffix for each listed file, and how its bytes are read."""

import hashlib

from earnest import adapters
from earnest.index import COMMENT, GHERKIN, MARKDOWN, Line


RECORD = "aidlc/spaces/default/intents/260926-checkout"


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


def scanned(tmp_path, paths):
    """Write each path as a file holding one tag line, scan them all, and return the paths that were read."""
    for path in paths:
        file = tmp_path / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("# [impl->req~a~1]\n", encoding="utf-8")
    return [source.path for source in adapters.scan(tmp_path, paths)]


def test_source_digest_is_of_the_raw_bytes_even_with_bad_utf8(tmp_path):
    data = b"# Caf\xe9\n\n`req~a~1`\n"
    (tmp_path / "a.md").write_bytes(data)
    (source,) = adapters.scan(tmp_path, ["a.md"])
    assert source.digest == "sha256:" + hashlib.sha256(data).hexdigest()


def test_source_carries_line_count_as_git_counts_it(tmp_path):
    files = {"a.md": b"one\ntwo\n", "b.md": b"one\ntwo", "c.md": b"a\rb\n", "d.md": b""}
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    counts = {source.path: source.line_count for source in adapters.scan(tmp_path, list(files))}
    assert counts == {"a.md": 2, "b.md": 2, "c.md": 1, "d.md": 0}


def test_source_code_lines_are_set_for_comment_surfaces_only(tmp_path):
    files = {
        "a.py": "# [impl->req~a~1]\nx = 1\n",
        "a.ts": "// [impl->req~a~1]\nlet x = 1;\n",
        "a.feature": "@stest:feat~f~1\nScenario: S\n",
        "a.md": "`req~a~1`\n",
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    found = {source.path: source.code_lines for source in adapters.scan(tmp_path, list(files))}
    assert found == {"a.py": {2}, "a.ts": {2}, "a.feature": {2}, "a.md": frozenset()}


def test_reads_is_true_for_scanned_suffixes_only():
    assert all(adapters.reads(path) for path in ("a/b.py", "c.tsx", "d.mts", "e.cts", "f.feature", "g.md", "h.ts"))
    assert not any(adapters.reads(path) for path in ("a.txt", "b.json", "c.toml", "Makefile", "d/e.yml"))


def test_scan_skips_the_state_file_and_the_audit_shards_of_a_record_directory(tmp_path):
    paths = [f"{RECORD}/aidlc-state.md", f"{RECORD}/audit/a.md", f"{RECORD}/audit/b.md", f"{RECORD}/notes.md"]
    assert scanned(tmp_path, paths) == [f"{RECORD}/notes.md"]


def test_scan_skips_engine_files_and_the_legacy_aidlc_siblings(tmp_path):
    paths = [
        f"{RECORD}/aidlc-state.md",
        f"{RECORD}/.aidlc-engine/sensors/earnest/detail.md",
        f"{RECORD}/.aidlc-sensors/detail.md",
        f"{RECORD}/.aidlc-reviews/review.md",
        f"{RECORD}/inception/requirements-analysis/requirements.md",
    ]
    assert scanned(tmp_path, paths) == [f"{RECORD}/inception/requirements-analysis/requirements.md"]


def test_scan_skips_memory_md_under_a_stage_directory_and_reads_other_markdown(tmp_path):
    paths = [
        f"{RECORD}/aidlc-state.md",
        f"{RECORD}/inception/requirements-analysis/memory.md",
        f"{RECORD}/inception/requirements-analysis/requirements.md",
        f"{RECORD}/memory.md",
        f"{RECORD}/inception/memory.md",
    ]
    assert scanned(tmp_path, paths) == [
        f"{RECORD}/inception/requirements-analysis/requirements.md",
        f"{RECORD}/memory.md",
        f"{RECORD}/inception/memory.md",
    ]


def test_scan_reads_the_artifacts_of_a_record_directory(tmp_path):
    paths = [
        f"{RECORD}/aidlc-state.md",
        f"{RECORD}/inception/requirements-analysis/requirements.md",
        f"{RECORD}/construction/code-generation/code-generation-plan.md",
        "src/checkout/auth.py",
    ]
    assert scanned(tmp_path, paths) == paths[1:]


def test_scan_without_a_state_file_skips_nothing(tmp_path):
    paths = ["audit/a.md", ".aidlc-engine/x.md", "x/inception/y/memory.md", "aidlc/spaces/default/intents/z/audit/b.md"]
    assert scanned(tmp_path, paths) == paths


def test_scan_applies_the_skips_to_each_record_directory_alone(tmp_path):
    paths = ["one/aidlc-state.md", "one/audit/a.md", "one-b/audit/a.md", "two/audit/a.md", "two/notes.md"]
    assert scanned(tmp_path, paths) == ["one-b/audit/a.md", "two/audit/a.md", "two/notes.md"]


def test_skipped_is_the_one_predicate_scan_uses():
    directories = {RECORD}
    below = ("aidlc-state.md", "audit/a.md", ".aidlc-engine/x.md", ".aidlc-sensors/y.md", "inception/stage/memory.md")
    assert all(adapters.skipped(f"{RECORD}/{path}", directories) for path in below)
    other = (
        f"{RECORD}/notes.md",
        f"{RECORD}/inception/stage/requirements.md",
        "docs/audit/a.md",
        "other/aidlc-state.md",
        f"{RECORD}-b/aidlc-state.md",
    )
    assert not any(adapters.skipped(path, directories) for path in other)
    assert adapters.skipped("audit/a.md", {""})
    paths = [f"{RECORD}/aidlc-state.md", "aidlc-state.md", "docs/a.md"]
    assert adapters.record_directories(paths) == {RECORD, ""}
