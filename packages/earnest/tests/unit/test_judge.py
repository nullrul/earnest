"""Unit tests for the judge: the stub model, its questions and its observations (D14)."""

import hashlib
import json
from pathlib import Path

import pytest

from earnest import judge
from earnest.index import COMMENT, MARKDOWN, Line, Source, build_index, split_lines
from earnest.reporter import Record
from tests.conftest import _git as commit_as_fixture
from tests.sarif import git_output


SPEC = "docs/req.md"
REQS = """# Requirements

`req~greet~1`

When a member logs in, the system shall greet them.

`req~prose~1`

Members get greeted.
"""


def code(path, tag, lines):
    return Source(path, COMMENT, (Line(1, f"# [{tag}]"),), code_lines=frozenset(range(2, lines + 1)), line_count=lines)


def index(*extra):
    tags = (
        code("src/a.py", "impl->req~greet~1", 5),
        code("tests/a.py", "utest->req~greet~1", 4),
        code("src/b.py", "impl->req~prose~1", 3),
    )
    return build_index([Source(SPEC, MARKDOWN, split_lines(REQS)), *tags, *extra])


LEVELS = {"req~greet~1": "traced", "req~prose~1": "traced"}


def answer(result="satisfied", file="src/a.py", line=3, reasoning="it does"):
    return {"result": result, "reasoning": reasoning, "location": {"file": file, "line": line}}


def write_code(root):
    for path, lines in (("src/a.py", 5), ("tests/a.py", 4), ("src/b.py", 3)):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text("".join(f"line {number}\n" for number in range(1, lines + 1)))


def commit_code(root):
    """Commit the tagged files in a new repository at root, and return the commit's sha."""
    write_code(root)
    for args in (("init", "-q"), ("add", "src", "tests"), ("commit", "-q", "--no-verify", "-m", "code")):
        commit_as_fixture(root, *args)
    return git_output(root, "rev-parse", "HEAD").strip()


def one(result, rule):
    """Return the one finding of a rule in a judge run."""
    (found,) = [each for each in result.findings if each.rule == rule]
    return found


def ask(found, model, root, slot=None):
    if not (root / "src").exists():
        write_code(root)
    return judge.judge(found, LEVELS, model, root, Record(judge=slot or {"cache": {}}))


def stub(tmp_path, data):
    path = tmp_path / "verdicts.json"
    path.write_text(json.dumps(data))
    return judge.load_model(f"stub:{path}", tmp_path)


def test_the_model_id_is_the_stub_and_the_files_sha256(tmp_path):
    model = stub(tmp_path, {})
    data = (tmp_path / "verdicts.json").read_bytes()
    assert model.id == "stub:sha256:" + hashlib.sha256(data).hexdigest()


def test_the_prompt_hash_is_the_prompts_sha256():
    assert judge.PROMPT_HASH.startswith("sha256:")
    assert len(judge.PROMPT_HASH) == len("sha256:") + 64


@pytest.mark.parametrize("value", [None, "", "foo:x", "stub:", "stub"])
def test_an_unset_or_unknown_model_cannot_run(value):
    with pytest.raises(judge.JudgeError):
        judge.load_model(value, Path())


def test_a_missing_file_cannot_run(tmp_path):
    with pytest.raises(judge.JudgeError, match="cannot be read"):
        judge.load_model(f"stub:{tmp_path / 'none.json'}", tmp_path)


@pytest.mark.parametrize(
    "data",
    [
        "[]",
        "not json",
        '{"req~greet~1": []}',
        '{"req~greet~1": {"ok": {}}}',
        '{"req~greet~1": {"tested": {"result": "maybe", "reasoning": "x", "location": {"file": "a", "line": 1}}}}',
        '{"req~greet~1": {"tested": {"result": "satisfied", "reasoning": "x", "location": {"file": "a", "line": 0}}}}',
        '{"req~greet~1": {"tested": {"result": "satisfied", "reasoning": "x"}}}',
    ],
)
def test_a_file_that_is_not_the_object_of_canned_verdicts_cannot_run(tmp_path, data):
    path = tmp_path / "verdicts.json"
    path.write_text(data)
    with pytest.raises(judge.JudgeError, match="not an object of canned verdicts"):
        judge.load_model(f"stub:{path}", tmp_path)


def test_a_question_the_file_does_not_answer_cannot_run(tmp_path):
    model = stub(tmp_path, {"req~greet~1": {"implemented": answer()}})
    with pytest.raises(judge.JudgeError, match="req~greet~1` tested"):
        ask(index(), model, tmp_path)


def test_each_traced_ears_requirement_asks_two_questions_and_others_none():
    asked = judge.questions(index(), {**LEVELS, "req~greet~1": "traced"})
    assert [(question.subject, question.kind) for question in asked] == [
        ("req~greet~1", "implemented"),
        ("req~greet~1", "tested"),
    ]
    implemented, tested = asked
    assert [region.path for region in implemented.regions] == ["src/a.py"]
    assert [region.path for region in tested.regions] == ["tests/a.py"]
    assert judge.questions(index(), {"req~greet~1": "untraced", "req~prose~1": "traced"}) == []


def test_a_not_satisfied_verdict_sits_at_its_location_inside_an_asked_region(tmp_path):
    model = stub(tmp_path, {"req~greet~1": {"implemented": answer("not-satisfied"), "tested": answer()}})
    result = ask(index(), model, tmp_path)
    found = one(result, "earnest/judge-not-satisfied")
    assert (found.path, found.line, found.subject) == ("src/a.py", 3, "req~greet~1")
    assert "it does" in found.message
    assert found.observations[0]["author"] == "judge"


def test_a_not_satisfied_verdict_outside_the_asked_regions_sits_at_the_id_line(tmp_path):
    outside = answer("not-satisfied", file="src/a.py", line=9)
    model = stub(tmp_path, {"req~greet~1": {"implemented": answer(), "tested": outside}})
    result = ask(index(), model, tmp_path)
    found = one(result, "earnest/judge-not-satisfied")
    assert (found.path, found.line) == (SPEC, 3)


def test_one_uncalibrated_finding_per_run_at_line_one_of_the_record(tmp_path):
    model = stub(tmp_path, {"req~greet~1": {"implemented": answer(), "tested": answer()}})
    result = ask(index(), model, tmp_path)
    found = one(result, "earnest/judge-uncalibrated")
    assert (found.path, found.line) == (".earnest/assessment.json", 1)
    assert model.id in found.message
    assert judge.PROMPT_HASH in found.message


def passing(base, **over):
    return {"model": base.id, "prompt": judge.PROMPT_HASH, "matches": 8, "total": 10, "pass": True, **over}


def test_calibrated_needs_pass(tmp_path):
    model = stub(tmp_path, {})
    assert judge.calibrated(passing(model), model) is True
    assert judge.calibrated(passing(model, **{"pass": False}), model) is False


def test_calibrated_needs_same_model_and_prompt(tmp_path):
    model = stub(tmp_path, {})
    assert judge.calibrated(passing(model, model="stub:other"), model) is False
    assert judge.calibrated(passing(model, prompt="0" * 64), model) is False


def test_calibrated_none(tmp_path):
    assert judge.calibrated(None, stub(tmp_path, {})) is False


def test_calibrated_malformed_slot(tmp_path):
    model = stub(tmp_path, {})
    assert judge.calibrated(passing(model, **{"pass": "false"}), model) is False
    assert judge.calibrated({"model": model.id, "prompt": judge.PROMPT_HASH}, model) is False
    assert judge.calibrated(passing(model, matches="8"), model) is False


def test_calibrated_needs_today_s_bar(tmp_path):
    model = stub(tmp_path, {})
    assert judge.calibrated(passing(model, matches=judge.PASS_MATCHES - 1), model) is False
    assert judge.calibrated(passing(model, total=judge.TOTAL + 1), model) is False


def test_a_record_calibrated_for_this_model_raises_no_uncalibrated_finding(tmp_path):
    model = stub(tmp_path, {"req~greet~1": {"implemented": answer(), "tested": answer()}})
    write_code(tmp_path)
    record = Record(calibration=passing(model))
    result = judge.judge(index(), LEVELS, model, tmp_path, record)
    assert [each for each in result.findings if each.rule == "earnest/judge-uncalibrated"] == []


def test_observations_are_sorted_by_subject_and_question(tmp_path):
    model = stub(tmp_path, {"req~greet~1": {"tested": answer(file="tests/a.py"), "implemented": answer()}})
    result = ask(index(), model, tmp_path)
    assert [(each["subject"], each["question"], each["method"]) for each in result.observations] == [
        ("req~greet~1", "implemented", "inspection"),
        ("req~greet~1", "tested", "inspection"),
    ]


def overridden(*lines, code_lines=5):
    text = REQS.replace(
        "When a member logs in, the system shall greet them.\n",
        "When a member logs in, the system shall greet them.\n" + "".join(f"{line}\n" for line in lines),
    )
    tags = (code("src/a.py", "impl->req~greet~1", code_lines), code("tests/a.py", "utest->req~greet~1", 4))
    return build_index([Source(SPEC, MARKDOWN, split_lines(text)), *tags])


def test_a_standing_override_replaces_its_question_which_is_not_asked(tmp_path):
    model = stub(tmp_path, {"req~greet~1": {"tested": answer(file="tests/a.py")}})
    index = overridden(f"Override: req~greet~1 implemented at {commit_code(tmp_path)},  the gateway greets  ")
    result = ask(index, model, tmp_path)
    implemented, tested = result.observations
    assert implemented == {
        "method": "inspection",
        "subject": "req~greet~1",
        "question": "implemented",
        "author": "maintainer",
        "result": "satisfied",
        "reasoning": "the gateway greets",
        "location": {"artifactLocation": {"uri": SPEC}, "region": {"startLine": 6}},
    }
    assert tested["author"] == "judge"


def test_two_overrides_of_one_id_and_kind_are_a_duplicate(tmp_path):
    model = stub(tmp_path, {"req~greet~1": {"tested": answer(file="tests/a.py")}})
    at = commit_code(tmp_path)
    index = overridden(
        f"Override: req~greet~1 implemented at {at}, one", f"Override: req~greet~1 implemented at {at}, two"
    )
    result = ask(index, model, tmp_path)
    found = one(result, "earnest/duplicate")
    assert (found.path, found.line) == (SPEC, 7)
    assert result.observations[0]["reasoning"] == "one"


@pytest.mark.parametrize(("tested", "level"), [("satisfied", "judged"), ("not-satisfied", "traced")])
def test_judged_means_traced_with_every_question_satisfied_or_overridden(tmp_path, tested, level):
    model = stub(tmp_path, {"req~greet~1": {"tested": answer(tested, file="tests/a.py")}})
    index = overridden(f"Override: req~greet~1 implemented at {commit_code(tmp_path)}, why")
    assert ask(index, model, tmp_path).levels == {"req~greet~1": level, "req~prose~1": "traced"}


class Counting:
    """A model that counts the questions put to it."""

    def __init__(self, model):
        """Wrap model, keeping its id."""
        self.id, self.model, self.asked = model.id, model, []

    def ask(self, question):
        self.asked.append((question.subject, question.kind))
        return self.model.ask(question)


GREET = {"implemented": answer(), "tested": answer(file="tests/a.py")}


def test_an_unchanged_key_reuses_the_cached_verdict(tmp_path):
    model = Counting(stub(tmp_path, {"req~greet~1": GREET}))
    first = ask(index(), model, tmp_path)
    second = ask(index(), model, tmp_path, first.cache)
    assert model.asked == [("req~greet~1", "implemented"), ("req~greet~1", "tested")]
    assert second.cache == first.cache
    assert second.observations == first.observations
    entries = sorted(first.cache["cache"].values(), key=lambda entry: entry["question"])
    assert [(entry["item"], entry["question"], entry["result"]) for entry in entries] == [
        ("req~greet~1", "implemented", "satisfied"),
        ("req~greet~1", "tested", "satisfied"),
    ]


KEY = ("item", "question", "regions", "tests", "model", "prompt")


def test_the_cache_key_is_the_digest_of_its_six_parts_so_each_reruns_the_question(tmp_path):
    first = ask(index(), stub(tmp_path, {"req~greet~1": GREET}), tmp_path)
    for key, entry in first.cache["cache"].items():
        parts = {part: entry[part] for part in KEY}
        assert key == judge.digest(judge.canonical(parts).encode())
        assert (parts["model"], parts["prompt"]) == (first_model_id(tmp_path), judge.PROMPT_HASH)


def first_model_id(tmp_path):
    return "stub:" + judge.digest((tmp_path / "verdicts.json").read_bytes())


def test_a_changed_region_reruns_both_questions(tmp_path):
    model = Counting(stub(tmp_path, {"req~greet~1": GREET}))
    first = ask(index(), model, tmp_path)
    model.asked.clear()
    moved = (code("src/a.py", "impl->req~greet~1", 6), code("tests/a.py", "utest->req~greet~1", 4))
    found = build_index([Source(SPEC, MARKDOWN, split_lines(REQS)), *moved])
    ask(found, model, tmp_path, first.cache)
    assert len(model.asked) == 2


def test_a_stub_file_edit_changes_the_model_id_and_reruns(tmp_path):
    first = ask(index(), stub(tmp_path, {"req~greet~1": GREET}), tmp_path)
    model = Counting(stub(tmp_path, {"req~greet~1": GREET, "req~other~1": {}}))
    ask(index(), model, tmp_path, first.cache)
    assert len(model.asked) == 2


def rules(result):
    return [each.rule for each in result.findings]


def test_an_override_at_another_revision_expires_and_its_question_is_asked(tmp_path):
    model = Counting(stub(tmp_path, {"req~greet~1": GREET}))
    result = ask(overridden(f"Override: req~greet~2 implemented at {commit_code(tmp_path)}, why"), model, tmp_path)
    found = one(result, "earnest/override-expired")
    assert (found.path, found.line, found.subject) == (SPEC, 6, "req~greet~2")
    assert "req~greet~1" in found.message
    assert model.asked == [("req~greet~1", "implemented"), ("req~greet~1", "tested")]
    assert "earnest/override-drift" not in rules(result)


def test_an_override_whose_region_changed_drifts_and_carries_both_observations(tmp_path):
    at = commit_code(tmp_path)
    (tmp_path / "src/a.py").write_text("line 1\nline 2\nchanged\nline 4\nline 5\n")
    verdicts = {"implemented": answer("not-satisfied", reasoning="it moved"), "tested": GREET["tested"]}
    result = ask(
        overridden(f"Override: req~greet~1 implemented at {at}, why"),
        stub(tmp_path, {"req~greet~1": verdicts}),
        tmp_path,
    )
    found = one(result, "earnest/override-drift")
    assert (found.path, found.line) == (SPEC, 6)
    assert [(each["author"], each["result"]) for each in found.observations] == [
        ("maintainer", "satisfied"),
        ("judge", "not-satisfied"),
    ]
    assert "earnest/judge-not-satisfied" not in rules(result)
    assert result.observations[0]["author"] == "maintainer"
    assert result.levels["req~greet~1"] == "judged"


def test_an_override_whose_region_held_still_does_not_drift(tmp_path):
    at = commit_code(tmp_path)
    (tmp_path / "src/b.py").write_text("other\n")
    model = Counting(stub(tmp_path, {"req~greet~1": {"tested": GREET["tested"]}}))
    result = ask(overridden(f"Override: req~greet~1 implemented at {at}, why"), model, tmp_path)
    assert "earnest/override-drift" not in rules(result)
    assert model.asked == [("req~greet~1", "tested")]


def test_an_override_at_a_commit_git_does_not_hold_drifts(tmp_path):
    commit_code(tmp_path)
    model = stub(tmp_path, {"req~greet~1": GREET})
    result = ask(overridden("Override: req~greet~1 implemented at deadbeef, why"), model, tmp_path)
    found = one(result, "earnest/override-drift")
    assert "Git holds no single commit deadbeef" in found.message


def test_a_relative_stub_path_reads_against_the_working_directory(tmp_path, monkeypatch):
    stub(tmp_path, {"req~greet~1": GREET})
    monkeypatch.chdir(tmp_path)
    model = judge.load_model("stub:verdicts.json", tmp_path / "elsewhere")
    assert isinstance(model, judge.Stub)
    assert model.id == first_model_id(tmp_path)
    assert model.answers["req~greet~1"]["tested"].path == "tests/a.py"


def test_a_file_nested_past_the_parser_s_depth_cannot_run(tmp_path):
    path = tmp_path / "deep.json"
    path.write_text("[" * 100_000 + "]" * 100_000)
    with pytest.raises(judge.JudgeError, match="not an object of canned verdicts"):
        judge.load_model(f"stub:{path}", tmp_path)


def drifts_after(tmp_path, lines):
    """Commit the code, rewrite src/a.py as lines, and return the rules of a judge run under an `implemented` override.

    The index reads src/a.py at the work tree, as a check does, so its region ends at the rewritten file's last line.
    """
    at = commit_code(tmp_path)
    (tmp_path / "src/a.py").write_text("".join(f"{line}\n" for line in lines))
    model = stub(tmp_path, {"req~greet~1": GREET})
    index = overridden(f"Override: req~greet~1 implemented at {at}, why", code_lines=len(lines))
    return rules(ask(index, model, tmp_path))


@pytest.mark.parametrize(
    "lines",
    [["line 1", "line 2", "line 3", "line 4"], ["line 1"]],
    ids=["the region's last line", "all the code under the tag"],
)
def test_deleting_lines_at_the_end_of_an_overridden_region_drifts(tmp_path, lines):
    assert "earnest/override-drift" in drifts_after(tmp_path, lines)


def test_a_deletion_before_the_region_does_not_drift(tmp_path):
    # the tag moves to line 2 of src/a.py, so the deleted line 1 lies before its region, which holds still
    commit_code(tmp_path)
    (tmp_path / "src/a.py").write_text("# head\nline 1\nline 2\nline 3\nline 4\nline 5\n")
    commit_as_fixture(tmp_path, "commit", "-qam", "head")
    at = git_output(tmp_path, "rev-parse", "HEAD").strip()
    (tmp_path / "src/a.py").write_text("line 1\nline 2\nline 3\nline 4\nline 5\n")
    model = stub(tmp_path, {"req~greet~1": {"tested": GREET["tested"]}})
    index = overridden(f"Override: req~greet~1 implemented at {at}, why")
    assert "earnest/override-drift" not in rules(ask(index, model, tmp_path))


def test_an_override_at_a_prefix_a_branch_also_names_reads_the_commit_not_the_branch(tmp_path):
    at = commit_code(tmp_path)
    (tmp_path / "src/a.py").write_text("line 1\nline 2\nchanged\nline 4\nline 5\n")
    commit_as_fixture(tmp_path, "commit", "-qam", "change")
    git_output(tmp_path, "branch", at[:7])  # fixture mechanics: the branch points at the change, which matches the tree
    model = stub(tmp_path, {"req~greet~1": GREET})
    result = ask(overridden(f"Override: req~greet~1 implemented at {at[:7]}, why"), model, tmp_path)
    found = one(result, "earnest/override-drift")
    assert "its code changed" in found.message


def under_tested_override(tmp_path, path, text):
    """Commit the code, rewrite path as text, and return a judge run under a `tested` override."""
    at = commit_code(tmp_path)
    (tmp_path / path).write_text(text)
    model = Counting(stub(tmp_path, {"req~greet~1": GREET}))
    return model, ask(overridden(f"Override: req~greet~1 tested at {at}, why"), model, tmp_path)


def test_a_tested_override_stands_for_tested_and_drifts_when_its_test_changes(tmp_path):
    model, result = under_tested_override(tmp_path, "tests/a.py", "line 1\nchanged\nline 3\nline 4\n")
    found = one(result, "earnest/override-drift")
    assert found.subject == "req~greet~1"
    assert model.asked == [("req~greet~1", "implemented"), ("req~greet~1", "tested")]
    tested = [each for each in result.observations if each["question"] == "tested"]
    assert [each["author"] for each in tested] == ["maintainer"]


def test_a_tested_override_holds_when_only_the_code_changes(tmp_path):
    model, result = under_tested_override(tmp_path, "src/a.py", "line 1\nline 2\nchanged\nline 4\nline 5\n")
    assert "earnest/override-drift" not in rules(result)
    assert model.asked == [("req~greet~1", "implemented")]


def two_tags(tmp_path, tail):
    """Commit src/a.py with one tag, append tail at the work tree, and return the rules under an override of A.

    The Region rule ends a region at the line before the next tag, so a tag line appended after A starts B's region.
    """
    at = commit_code(tmp_path)
    lines = [f"line {number}" for number in range(1, 6)] + tail
    (tmp_path / "src/a.py").write_text("".join(f"{line}\n" for line in lines))
    tags = [Line(1, "# [impl->req~greet~1]")] + [Line(6, line) for line in tail if line.startswith("# [")]
    a = Source(
        "src/a.py", COMMENT, tuple(tags), code_lines=frozenset(range(2, len(lines) + 1)) - {6}, line_count=len(lines)
    )
    text = REQS.replace("them.\n", f"them.\nOverride: req~greet~1 implemented at {at}, why\n", 1)
    found = build_index([Source(SPEC, MARKDOWN, split_lines(text)), a, code("tests/a.py", "utest->req~greet~1", 4)])
    return rules(ask(found, stub(tmp_path, {"req~greet~1": GREET, "req~prose~1": GREET}), tmp_path))


@pytest.mark.parametrize(
    ("tail", "drifts"),
    [(["line 6"], True), (["# [impl->req~prose~1]", "line 7"], False)],
    ids=["a code line extends the region", "a tag line starts another region"],
)
def test_a_line_inserted_right_after_the_region(tmp_path, tail, drifts):
    assert ("earnest/override-drift" in two_tags(tmp_path, tail)) is drifts


def test_an_expired_duplicate_is_still_a_duplicate(tmp_path):
    at = commit_code(tmp_path)
    index = overridden(
        f"Override: req~greet~2 implemented at {at}, one", f"Override: req~greet~2 implemented at {at}, two"
    )
    result = ask(index, stub(tmp_path, {"req~greet~1": GREET}), tmp_path)
    assert rules(result).count("earnest/duplicate") == 1


def test_an_override_whose_tag_was_removed_from_another_file_drifts(tmp_path):
    write_code(tmp_path)
    (tmp_path / "src/c.py").write_text("# [impl->req~greet~1]\nx = 1\n")
    at = commit_code(tmp_path)
    (tmp_path / "src/c.py").unlink()  # file B loses its tag and region; src/a.py, file A, holds still
    model = stub(tmp_path, {"req~greet~1": GREET})
    result = ask(overridden(f"Override: req~greet~1 implemented at {at}, why"), model, tmp_path)
    found = one(result, "earnest/override-drift")
    assert "src/c.py" in found.message


def test_a_removed_tag_of_the_other_kind_does_not_drift_the_override(tmp_path):
    write_code(tmp_path)
    (tmp_path / "src/c.py").write_text("# [utest->req~greet~1]\nx = 1\n")
    at = commit_code(tmp_path)
    (tmp_path / "src/c.py").unlink()
    model = stub(tmp_path, {"req~greet~1": GREET})
    result = ask(overridden(f"Override: req~greet~1 implemented at {at}, why"), model, tmp_path)
    assert "earnest/override-drift" not in rules(result)


def test_an_items_region_hashes_are_taken_once_for_both_its_questions(tmp_path, monkeypatch):
    hashed = []
    original = judge.region_hash
    monkeypatch.setattr(judge, "region_hash", lambda root, found: hashed.append(found) or original(root, found))
    ask(index(), stub(tmp_path, {"req~greet~1": GREET}), tmp_path)
    assert len(hashed) == 2


def test_control_characters_in_the_judge_s_reasoning_are_escaped_in_the_finding_message(tmp_path):
    shouting = answer("not-satisfied", reasoning="bad\n\x1b[31mred\r")
    result = ask(
        index(), stub(tmp_path, {"req~greet~1": {"implemented": shouting, "tested": GREET["tested"]}}), tmp_path
    )
    found = one(result, "earnest/judge-not-satisfied")
    assert "bad\\n\\x1b[31mred\\r" in found.message
    assert not any(character in found.message for character in "\n\r\x1b")


@pytest.mark.parametrize(
    "file", ["/etc/passwd", "../outside.py", "src/../src/a.py", "src/missing.py", ".git/config", "src/.git/HEAD"]
)
def test_a_verdict_location_outside_the_work_tree_falls_back_to_the_id_line(tmp_path, file):
    commit_code(tmp_path)  # a real `.git/`, so its files exist and must still be refused
    stray = answer("not-satisfied", file=file, line=3)
    result = ask(index(), stub(tmp_path, {"req~greet~1": {"implemented": stray, "tested": GREET["tested"]}}), tmp_path)
    found = one(result, "earnest/judge-not-satisfied")
    assert (found.path, found.line) == (SPEC, 3)
    implemented = result.observations[0]
    assert implemented["location"] == {"artifactLocation": {"uri": SPEC}, "region": {"startLine": 3}}


def test_a_verdict_location_with_a_dot_component_normalises_to_its_work_tree_file(tmp_path):
    commit_code(tmp_path)  # a `.git/` to reject beside the work tree's files
    dotted = answer("not-satisfied", file="./src//a.py", line=3)
    result = ask(index(), stub(tmp_path, {"req~greet~1": {"implemented": dotted, "tested": GREET["tested"]}}), tmp_path)
    found = one(result, "earnest/judge-not-satisfied")
    assert (found.path, found.line) == ("src/a.py", 3)
    assert result.observations[0]["location"] == {"artifactLocation": {"uri": "src/a.py"}, "region": {"startLine": 3}}


def test_an_override_under_a_duplicate_of_its_item_counts_for_nothing(tmp_path):
    at = commit_code(tmp_path)
    again = f"`req~greet~1`\n\nWhen a member logs in, the system shall greet them.\nOverride: req~greet~1 implemented at {at}, why\n"
    found = index(Source("docs/other.md", MARKDOWN, split_lines(again)))
    model = Counting(stub(tmp_path, {"req~greet~1": GREET}))
    result = ask(found, model, tmp_path)
    assert ("req~greet~1", "implemented") in model.asked
    assert all(each["author"] == "judge" for each in result.observations if each["subject"] == "req~greet~1")


def loose_object(root, sha):
    return root / ".git" / "objects" / sha[:2] / sha[2:]


def test_a_changed_file_whose_blob_git_cannot_read_drifts_the_override(tmp_path):
    write_code(tmp_path)
    (tmp_path / "src/c.py").write_text("# [impl->req~greet~1]\nx = 1\n")
    at = commit_code(tmp_path)
    blob = git_output(tmp_path, "rev-parse", f"{at}:src/c.py").strip()
    loose_object(tmp_path, blob).unlink()  # the commit lists src/c.py, but its object is gone
    (tmp_path / "src/c.py").write_text("# [impl->req~greet~1]\nx = 2\n")
    model = stub(tmp_path, {"req~greet~1": GREET})
    result = ask(overridden(f"Override: req~greet~1 implemented at {at}, why"), model, tmp_path)
    found = one(result, "earnest/override-drift")
    assert "src/c.py" in found.message
    assert "cannot read" in found.message


def test_a_file_added_since_the_commit_is_absent_there_and_does_not_drift(tmp_path):
    at = commit_code(tmp_path)
    (tmp_path / "src/new.py").write_text("x = 1\n")
    commit_as_fixture(tmp_path, "add", "src/new.py")
    model = stub(tmp_path, {"req~greet~1": GREET})
    result = ask(overridden(f"Override: req~greet~1 implemented at {at}, why"), model, tmp_path)
    assert "earnest/override-drift" not in rules(result)


def test_the_old_tags_of_a_commit_and_path_are_read_once_a_run(tmp_path, monkeypatch):
    write_code(tmp_path)
    (tmp_path / "src/c.py").write_text("x = 0\n")
    at = commit_code(tmp_path)
    (tmp_path / "src/c.py").write_text("x = 1\n")
    read = []
    original = judge.git.blob
    monkeypatch.setattr(judge.git, "blob", lambda *args: read.append(args[1:]) or original(*args))
    lines = (f"Override: req~greet~1 implemented at {at}, why", f"Override: req~greet~1 tested at {at}, why")
    ask(overridden(*lines), stub(tmp_path, {}), tmp_path)
    assert read == [(at, "src/c.py")]


def test_the_region_hash_is_the_one_the_cache_key_holds(tmp_path):
    found = index()
    (entry, *_) = ask(found, stub(tmp_path, {"req~greet~1": GREET}), tmp_path).cache["cache"].values()
    item = next(each for each in found.defined.values() if str(each.id) == "req~greet~1")
    assert entry["regions"] == judge.region_hash(tmp_path, judge.regions(found, item, judge.KINDS["implemented"]))
    assert entry["tests"] == judge.region_hash(tmp_path, judge.regions(found, item, judge.KINDS["tested"]))
    assert entry["regions"] != entry["tests"]


# Calibration (M6): ten traced EARS requirements, judged against the maintainer's verdicts.
TEN = tuple(f"req~r{number}~1" for number in range(1, 11))


def ten_index(count=10, plain=(), untraced=(), extra=""):
    """Return the index of `count` requirements, each tagged by an impl and a utest unless untraced."""
    body = "# Requirements\n\n" + "".join(
        f"`req~r{n}~1`\n\n"
        + ("Members get greeted.\n\n" if n in plain else f"When {n} happens, the system shall act.\n\n")
        for n in range(1, count + 1)
    )
    tags = [
        code(f"{kind}/r{n}.py", f"{tag}->req~r{n}~1", 3)
        for n in range(1, count + 1)
        if n not in untraced
        for kind, tag in (("src", "impl"), ("tests", "utest"))
    ]
    return build_index(
        [
            Source(
                SPEC,
                MARKDOWN,
                split_lines(
                    body.replace(
                        "When 1 happens, the system shall act.\n", "When 1 happens, the system shall act.\n" + extra, 1
                    )
                ),
            ),
            *tags,
        ]
    )


def ten_levels(count=10, untraced=()):
    return {f"req~r{n}~1": "untraced" if n in untraced else "traced" for n in range(1, count + 1)}


def verdict(result="satisfied"):
    return judge.Verdict(result, "because", "src/r1.py", 2)


def maintainer(no=()):
    """Return the maintainer's verdicts: satisfied except for both questions of each requirement number in no."""
    return {
        subject: dict.fromkeys(judge.QUESTIONS, verdict("not-satisfied" if int(subject[5:-2]) in no else "satisfied"))
        for subject in TEN
    }


def model(wrong=(), one=()):
    """Return a stub that agrees with maintainer() except on both questions of `wrong` and `implemented` of `one`."""
    answers = {
        subject: {
            kind: verdict(
                "not-satisfied"
                if int(subject[5:-2]) in wrong or (kind == "implemented" and int(subject[5:-2]) in one)
                else "satisfied"
            )
            for kind in judge.QUESTIONS
        }
        for subject in TEN
    }
    return judge.Stub("stub:t", answers)


def calibrate(stub_model=None, verdicts=None, found=None):
    return judge.calibrate(found or ten_index(), ten_levels(), stub_model or model(), verdicts or maintainer())


def test_eight_matches_pass():
    result = calibrate(model(wrong=(9, 10)))
    assert (result.matches, result.passed) == (8, True)
    assert [row.subject for row in result.rows] == sorted(TEN)
    assert result.model == "stub:t"


def test_seven_matches_fail():
    result = calibrate(model(wrong=(8, 9, 10)))
    assert (result.matches, result.passed) == (7, False)


def test_match_needs_both_questions():
    result = calibrate(model(one=(1,)))
    assert result.matches == 9
    assert [row.subject for row in result.rows if not row.matched] == ["req~r1~1"]


def test_constant_judge_fails():
    result = calibrate(model(), maintainer(no=(1, 2, 3)))
    assert (result.matches, result.passed) == (7, False)


def test_overrides_ignored():
    override = f"Override: req~r1~1 implemented at {'a' * 40}, the gateway greets\n"
    found = ten_index(extra=override)
    assert any(item.overrides for item in found.defined.values())
    assert calibrate(found=found).matches == 10


@pytest.mark.parametrize(
    "found",
    [ten_index(9), ten_index(11, untraced=(11,)), ten_index(plain=(4,))],
    ids=["nine", "eleven-one-untraced", "one-not-ears"],
)
def test_not_ten_judgeable_exits(found):
    levels = {str(item.id): "untraced" if "r11" in str(item.id) else "traced" for item in found.defined.values()}
    with pytest.raises(judge.JudgeError, match="exactly ten"):
        judge.calibrate(found, levels, model(), maintainer())


def test_a_requirement_defined_twice_exits():
    found = ten_index(extra="\n`req~r3~1`\n\nWhen 3 happens, the system shall do nothing.\n")
    assert len(found.items) > len(found.defined)
    with pytest.raises(judge.JudgeError, match=r"exactly ten.*defined more than once: req~r3~1"):
        calibrate(found=found)


def test_a_second_revision_of_a_requirement_exits():
    found = ten_index(extra="\n`req~r1~2`\n\nWhen 1 happens, the system shall do nothing.\n")
    assert len(found.items) > len(found.defined)
    with pytest.raises(judge.JudgeError, match=r"defined more than once: req~r1"):
        calibrate(found=found)


@pytest.mark.parametrize(
    ("found", "levels"),
    [
        (ten_index(untraced=(4,)), {"req~r4~1": "untraced"}),
        (ten_index(plain=(4,)), {}),
        (ten_index(extra="\n`req~r3~1`\n\nWhen 3 happens, the system shall do nothing.\n"), {}),
    ],
    ids=["untraced", "not-ears", "duplicate"],
)
def test_ten_requirements_with_a_fault_are_not_called_the_wrong_number(found, levels):
    traced = {str(item.id): "traced" for item in found.defined.values()} | levels
    with pytest.raises(judge.JudgeError, match="exactly ten traced EARS requirements") as raised:
        judge.calibrate(found, traced, model(), maintainer())
    assert ", not 10" not in str(raised.value)


def test_only_requirements_are_asked():
    found = ten_index(extra="\n`dsn~d1~1`\n\nWhen 1 happens, the design shall hold.\n")
    assert "dsn~d1~1" in {str(item.id) for item in found.defined.values()}
    levels = ten_levels() | {"dsn~d1~1": "traced"}
    assert any(question.subject == "dsn~d1~1" for question in judge.questions(found, levels))
    asked = []
    stub = model()

    class Recording:
        id = stub.id

        def ask(self, question):
            asked.append(question.subject)
            return stub.ask(question)

    result = judge.calibrate(found, levels, Recording(), maintainer())
    assert sorted(asked) == sorted(TEN * 2)
    assert [row.subject for row in result.rows] == sorted(TEN)


def test_missing_maintainer_answer_raises():
    verdicts = maintainer()
    del verdicts["req~r3~1"]["tested"]
    with pytest.raises(
        judge.JudgeError,
        match=r"the maintainer's verdicts.*req~r3~1.*tested|req~r3~1.*tested.*the maintainer's verdicts",
    ):
        calibrate(verdicts=verdicts)


def test_slot_shape():
    assert judge.slot(calibrate()) == {
        "model": "stub:t",
        "prompt": judge.PROMPT_HASH,
        "matches": 10,
        "total": 10,
        "pass": True,
    }


def test_load_verdicts_missing_file_names_it(tmp_path):
    with pytest.raises(judge.JudgeError, match=r"the maintainer's verdicts cannot be read.*verdicts\.json"):
        judge.load_verdicts(tmp_path / "verdicts.json")


def test_load_verdicts_malformed_raises(tmp_path):
    path = tmp_path / "verdicts.json"
    path.write_text("[]")
    with pytest.raises(
        judge.JudgeError, match=r"the maintainer's verdicts .*verdicts\.json is not an object of canned"
    ):
        judge.load_verdicts(path)


def test_load_verdicts_reads_the_answers(tmp_path):
    path = tmp_path / "verdicts.json"
    path.write_text(json.dumps({"req~r1~1": {"tested": answer()}}))
    assert judge.load_verdicts(path) == {"req~r1~1": {"tested": judge.Verdict("satisfied", "it does", "src/a.py", 3)}}


def test_a_requirement_named_twice_in_a_verdicts_file_cannot_run(tmp_path):
    entry = '{"implemented": {"result": "satisfied", "reasoning": "r", "location": {"file": "a", "line": 1}}}'
    path = tmp_path / "verdicts.json"
    path.write_text(f'{{"req~a~1": {entry}, "req~a~1": {entry}}}', encoding="utf-8")
    with pytest.raises(judge.JudgeError, match=r"req~a~1"):
        judge.load_verdicts(path)
    with pytest.raises(judge.JudgeError, match=r"req~a~1"):
        judge.load_model(f"stub:{path}", tmp_path)


def test_a_key_named_twice_reaches_the_message_escaped(tmp_path):
    path = tmp_path / "verdicts.json"
    path.write_text('{"\\u001b[31mX": {}, "\\u001b[31mX": {}}', encoding="utf-8")
    with pytest.raises(judge.JudgeError) as caught:
        judge.load_verdicts(path)
    assert "\x1b" not in str(caught.value)
    assert "\\x1b[31mX more than once" in str(caught.value)
