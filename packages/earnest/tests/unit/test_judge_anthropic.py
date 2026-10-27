"""Unit tests for the `anthropic:` judge model, with a fake client: no test reaches the API or needs a key."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import anthropic
import pytest

from earnest import judge
from tests.unit.test_judge import LEVELS, index, write_code


MODEL = "anthropic:claude-opus-5-5"


@dataclass
class Messages:
    """A fake `client.messages`: records each request and returns a canned reply, or raises."""

    reply: object = None
    error: Exception | None = None
    requests: list = field(default_factory=list)

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.reply


def reply(text, stop_reason="end_turn"):
    blocks = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(stop_reason=stop_reason, content=blocks)


VERDICT = {"result": "not-satisfied", "reasoning": "no greeting", "location": {"file": "src/a.py", "line": 3}}


def model(root, messages):
    return judge.Claude(MODEL, root, SimpleNamespace(messages=messages))


def question(root, kind="implemented"):
    write_code(root)
    (asked,) = [each for each in judge.questions(index(), LEVELS) if each.kind == kind and "greet" in each.subject]
    return asked


EXPECTED = (
    "\n"
    "Question: implemented\n"
    "Requirement: When a member logs in, the system shall greet them.\n"
    "Clauses:\n"
    "when: a member logs in\n"
    "response: greet them\n"
    "Code regions:\n"
    "src/a.py:1-5\n"
    "line 1\nline 2\nline 3\nline 4\nline 5\n"
    "Test regions:\n"
    "tests/a.py:1-4\n"
    "line 1\nline 2\nline 3\nline 4\n"
)


def test_the_question_text_is_the_prompt_then_the_fields_in_a_fixed_layout(tmp_path):
    prompt = (Path(judge.__file__).parent / "prompt.txt").read_text(encoding="utf-8")
    assert judge.question_text(tmp_path, question(tmp_path)) == prompt + EXPECTED


def test_a_tested_question_shows_the_same_code_and_tests(tmp_path):
    text = judge.question_text(tmp_path, question(tmp_path, "tested"))
    assert "Question: tested\n" in text
    assert text.endswith(EXPECTED.split("Question: implemented\n")[1])


def test_the_request_sends_the_question_at_effort_high_with_a_verdict_schema_and_no_sampling(tmp_path):
    messages = Messages(reply(json.dumps(VERDICT)))
    asked = question(tmp_path)
    model(tmp_path, messages).ask(asked)
    (request,) = messages.requests
    assert request["model"] == "claude-opus-5-5"
    assert request["messages"] == [{"role": "user", "content": judge.question_text(tmp_path, asked)}]
    content = request["messages"][0]["content"]
    assert content.startswith("You judge one requirement")
    assert "When a member logs in, the system shall greet them." in content
    assert "src/a.py:1-5\nline 1" in content
    assert "tests/a.py:1-4\nline 1" in content
    config = request["output_config"]
    assert config["effort"] == "high"
    schema = config["format"]["schema"]
    assert config["format"]["type"] == "json_schema"
    assert schema["properties"]["result"]["enum"] == ["satisfied", "not-satisfied"]
    assert set(schema["required"]) == {"result", "reasoning", "location"}
    assert not {"temperature", "top_p", "top_k", "thinking", "fallbacks"} & set(request)


def test_a_structured_reply_becomes_a_verdict(tmp_path):
    verdict = model(tmp_path, Messages(reply(json.dumps(VERDICT)))).ask(question(tmp_path))
    assert verdict == judge.Verdict("not-satisfied", "no greeting", "src/a.py", 3)


def test_an_api_error_cannot_run(tmp_path):
    messages = Messages(error=anthropic.APIConnectionError(request=None))
    with pytest.raises(judge.JudgeError, match="cannot answer `req~greet~1` implemented"):
        model(tmp_path, messages).ask(question(tmp_path))


def test_a_refusal_cannot_run(tmp_path):
    with pytest.raises(judge.JudgeError, match="refusal"):
        model(tmp_path, Messages(reply("", "refusal"))).ask(question(tmp_path))


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        '{"result": "maybe", "reasoning": "x", "location": {"file": "a", "line": 1}}',
        '{"result": "satisfied", "reasoning": "x"}',
        '{"result": "satisfied", "reasoning": "x", "location": {"file": "a", "line": 0}}',
    ],
)
def test_a_malformed_reply_cannot_run(tmp_path, text):
    with pytest.raises(judge.JudgeError, match="malformed"):
        model(tmp_path, Messages(reply(text))).ask(question(tmp_path))


def test_an_anthropic_value_loads_a_model_whose_id_is_the_value(tmp_path, monkeypatch):
    messages = Messages(reply(json.dumps(VERDICT)))
    monkeypatch.setattr(anthropic, "Anthropic", lambda: SimpleNamespace(messages=messages))
    loaded = judge.load_model(MODEL, tmp_path)
    assert loaded.id == MODEL
    assert loaded.ask(question(tmp_path)).result == "not-satisfied"
    assert messages.requests[0]["model"] == "claude-opus-5-5"


def test_a_client_that_cannot_start_cannot_run(tmp_path, monkeypatch):
    error = anthropic.AnthropicError("no credentials")

    def broken():
        raise error

    monkeypatch.setattr(anthropic, "Anthropic", broken)
    with pytest.raises(judge.JudgeError, match="no credentials"):
        judge.load_model(MODEL, tmp_path)


def test_an_anthropic_value_without_a_model_name_cannot_run(tmp_path):
    with pytest.raises(judge.JudgeError, match="names no model"):
        judge.load_model("anthropic:", tmp_path)


def test_an_sdk_type_error_on_a_request_cannot_run(tmp_path):
    messages = Messages(error=TypeError("Could not resolve authentication method"))
    with pytest.raises(judge.JudgeError, match="cannot answer `req~greet~1` implemented"):
        model(tmp_path, messages).ask(question(tmp_path))


def test_the_real_client_with_no_credentials_cannot_run(tmp_path, monkeypatch):
    for name in [name for name in os.environ if name.startswith("ANTHROPIC_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("HOME", str(tmp_path))  # no profile or config file supplies credentials
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:9")
    loaded = judge.load_model("anthropic:claude-x", tmp_path)
    with pytest.raises(judge.JudgeError, match="cannot answer"):
        loaded.ask(question(tmp_path))
