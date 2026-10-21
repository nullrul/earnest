"""Unit tests for the judge: the stub model, its questions and its observations (D14)."""

import hashlib
import json

import pytest

from earnest import judge
from earnest.index import COMMENT, MARKDOWN, Line, Source, build_index, split_lines


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


def ask(found, model, root, slot=None):
    for path, lines in (("src/a.py", 5), ("tests/a.py", 4), ("src/b.py", 3)):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text("".join(f"line {number}\n" for number in range(1, lines + 1)))
    return judge.judge(found, LEVELS, model, root, slot or {"cache": {}})


def stub(tmp_path, data):
    path = tmp_path / "verdicts.json"
    path.write_text(json.dumps(data))
    return judge.load_model(f"stub:{path}")


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
        judge.load_model(value)


def test_a_missing_file_cannot_run(tmp_path):
    with pytest.raises(judge.JudgeError, match="cannot be read"):
        judge.load_model(f"stub:{tmp_path / 'none.json'}")


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
        judge.load_model(f"stub:{path}")


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
    (found,) = [each for each in result.findings if each.rule == "earnest/judge-not-satisfied"]
    assert (found.path, found.line, found.subject) == ("src/a.py", 3, "req~greet~1")
    assert "it does" in found.message
    assert found.observations[0]["author"] == "judge"


def test_a_not_satisfied_verdict_outside_the_asked_regions_sits_at_the_id_line(tmp_path):
    outside = answer("not-satisfied", file="src/a.py", line=9)
    model = stub(tmp_path, {"req~greet~1": {"implemented": answer(), "tested": outside}})
    result = ask(index(), model, tmp_path)
    (found,) = [each for each in result.findings if each.rule == "earnest/judge-not-satisfied"]
    assert (found.path, found.line) == (SPEC, 3)


def test_one_uncalibrated_finding_per_run_at_line_one_of_the_record(tmp_path):
    model = stub(tmp_path, {"req~greet~1": {"implemented": answer(), "tested": answer()}})
    result = ask(index(), model, tmp_path)
    (found,) = [each for each in result.findings if each.rule == "earnest/judge-uncalibrated"]
    assert (found.path, found.line) == (".earnest/assessment.json", 1)
    assert model.id in found.message
    assert judge.PROMPT_HASH in found.message


def test_observations_are_sorted_by_subject_and_question(tmp_path):
    model = stub(tmp_path, {"req~greet~1": {"tested": answer(file="tests/a.py"), "implemented": answer()}})
    result = ask(index(), model, tmp_path)
    assert [(each["subject"], each["question"], each["method"]) for each in result.observations] == [
        ("req~greet~1", "implemented", "inspection"),
        ("req~greet~1", "tested", "inspection"),
    ]


def overridden(*lines):
    text = REQS.replace(
        "When a member logs in, the system shall greet them.\n",
        "When a member logs in, the system shall greet them.\n" + "".join(f"{line}\n" for line in lines),
    )
    tags = (code("src/a.py", "impl->req~greet~1", 5), code("tests/a.py", "utest->req~greet~1", 4))
    return build_index([Source(SPEC, MARKDOWN, split_lines(text)), *tags])


def test_a_standing_override_replaces_its_question_which_is_not_asked(tmp_path):
    model = stub(tmp_path, {"req~greet~1": {"tested": answer(file="tests/a.py")}})
    index = overridden("Override: req~greet~1 implemented at 89f3937,  the gateway greets  ")
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
    index = overridden(
        "Override: req~greet~1 implemented at 89f3937, one", "Override: req~greet~1 implemented at 89f3937, two"
    )
    result = ask(index, model, tmp_path)
    (found,) = [each for each in result.findings if each.rule == "earnest/duplicate"]
    assert (found.path, found.line) == (SPEC, 7)
    assert result.observations[0]["reasoning"] == "one"


@pytest.mark.parametrize(("tested", "level"), [("satisfied", "judged"), ("not-satisfied", "traced")])
def test_judged_means_traced_with_every_question_satisfied_or_overridden(tmp_path, tested, level):
    model = stub(tmp_path, {"req~greet~1": {"tested": answer(tested, file="tests/a.py")}})
    index = overridden("Override: req~greet~1 implemented at 89f3937, why")
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
