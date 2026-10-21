"""Judge: the questions each traced EARS requirement asks, the model that answers them, and its observations (D14)."""

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from earnest import ears
from earnest.index import Index, Item, Region, digest
from earnest.reporter import RECORD, Finding, location


QUESTIONS = ("implemented", "tested")
# The artifact types whose regions each question asks about.
KINDS = {"implemented": frozenset({"impl"}), "tested": frozenset({"utest", "itest", "stest"})}
PROMPT_HASH = digest(files(__package__).joinpath("prompt.txt").read_bytes())
_RESULTS = ("satisfied", "not-satisfied")


class JudgeError(Exception):
    """The judge cannot run: no model is named, its file cannot be read or is malformed, or an answer is missing."""


@dataclass(frozen=True)
class Verdict:
    """The judge's answer to one question: its result, its reasoning and the file and line it rests on."""

    result: str
    reasoning: str
    path: str
    line: int


@dataclass(frozen=True)
class Question:
    """One question about one requirement: `implemented` or `tested`, its sentence, and the regions it asks about."""

    item: Item
    kind: str
    sentence: ears.Sentence
    regions: tuple[Region, ...]

    @property
    def subject(self) -> str:
        """Return the requirement's id with its revision."""
        return str(self.item.id)


@dataclass(frozen=True)
class Stub:
    """The stub model: canned verdicts keyed by requirement id and revision, then by question; it reads no prompt."""

    id: str
    answers: Mapping[str, Mapping[str, Verdict]]

    def ask(self, question: Question) -> Verdict:
        """Return the canned verdict of a question.

        Raises:
            JudgeError: the file holds no answer to it.
        """
        verdict = self.answers.get(question.subject, {}).get(question.kind)
        if verdict is None:
            msg = f"the stub model's file holds no answer to `{question.subject}` {question.kind}"
            raise JudgeError(msg)
        return verdict


@dataclass(frozen=True)
class Judgement:
    """What the judge layer adds: its findings, the observations of record and each requirement's trace level."""

    findings: list[Finding]
    observations: list[dict[str, object]]
    levels: dict[str, str]


def load_model(value: str | None) -> Stub:
    """Return the model `EARNEST_JUDGE` names: `stub:<path>`, its path absolute or relative to the working directory.

    Raises:
        JudgeError: the value is unset or names no known model, or the file cannot be read or is not the object of
            canned verdicts.
    """
    if not value:
        msg = "--judge needs a model: set EARNEST_JUDGE to stub:<path of a canned-verdict file>"
        raise JudgeError(msg)
    kind, _, path = value.partition(":")
    if kind != "stub" or not path:
        msg = f"EARNEST_JUDGE names no model Earnest knows: {value!r}; use stub:<path>"
        raise JudgeError(msg)
    try:
        data = Path(path).read_bytes()
        answers = _answers(json.loads(data))
    except OSError as error:
        msg = f"the stub model's file cannot be read: {error}"
        raise JudgeError(msg) from error
    except (ValueError, TypeError, KeyError) as error:  # UnicodeDecodeError is a ValueError
        msg = f"the stub model's file {path} is not an object of canned verdicts: {error}"
        raise JudgeError(msg) from error
    return Stub("stub:" + digest(data), answers)


def _answers(data: object) -> dict[str, dict[str, Verdict]]:
    if not isinstance(data, dict):
        msg = "the file is not a JSON object"
        raise TypeError(msg)
    return {str(subject): _asked(asked) for subject, asked in data.items()}


def _asked(asked: object) -> dict[str, Verdict]:
    if not isinstance(asked, dict) or not set(asked) <= set(QUESTIONS):
        msg = f"each requirement maps {' or '.join(QUESTIONS)} to an answer, not {asked!r}"
        raise TypeError(msg)
    return {kind: _verdict(answer) for kind, answer in asked.items()}


def _verdict(answer: object) -> Verdict:
    if not isinstance(answer, dict):
        msg = f"an answer is an object, not {answer!r}"
        raise TypeError(msg)
    result, reasoning, where = answer["result"], answer["reasoning"], answer["location"]
    if result not in _RESULTS or not isinstance(reasoning, str) or not isinstance(where, dict):
        msg = f"an answer has a result of {' or '.join(_RESULTS)}, a reasoning and a location: {answer!r}"
        raise TypeError(msg)
    path, line = where["file"], where["line"]
    if not isinstance(path, str) or not isinstance(line, int) or isinstance(line, bool) or line < 1:
        msg = f"a location is a file and a line from 1: {where!r}"
        raise TypeError(msg)
    return Verdict(result, reasoning, path, line)


def environment_model() -> Stub:
    """Return the model `EARNEST_JUDGE` names in the environment."""
    return load_model(os.environ.get("EARNEST_JUDGE"))


def questions(index: Index, levels: Mapping[str, str]) -> list[Question]:
    """Return the two questions of each traced requirement whose body is one EARS sentence, in index order."""
    asked: list[Question] = []
    for item in index.defined.values():
        sentence = ears.parse(item.body) if levels.get(str(item.id)) == "traced" else None
        if sentence is not None:
            asked.extend(Question(item, kind, sentence, regions(index, item, KINDS[kind])) for kind in QUESTIONS)
    return asked


def regions(index: Index, item: Item, kinds: frozenset[str]) -> tuple[Region, ...]:
    """Return the item's tag regions at its current revision whose tags are of one of kinds, in region order."""
    tags = [link for link in index.links if link.owner is None and link.target == item.id and link.type in kinds]
    return tuple(
        dict.fromkeys(
            region for tag in tags for region in index.regions_at(tag.path, tag.line) if region.target == item.id
        )
    )


def observation(question: Question, author: str, verdict: Verdict) -> dict[str, object]:
    """Return an observation of record: an inspection of one question, by the judge or the maintainer."""
    return {
        "method": "inspection",
        "subject": question.subject,
        "question": question.kind,
        "author": author,
        "result": verdict.result,
        "reasoning": verdict.reasoning,
        "location": location(verdict.path, verdict.line),
    }


def judge(index: Index, levels: Mapping[str, str], model: Stub) -> Judgement:
    """Ask each question, and return the findings, the observations of record and the levels the answers give.

    Raises:
        JudgeError: the model cannot answer a question.
    """
    found: list[Finding] = [uncalibrated(model)]
    observations: list[dict[str, object]] = []
    for question in questions(index, levels):
        verdict = model.ask(question)
        observed = observation(question, "judge", verdict)
        observations.append(observed)
        if verdict.result != "satisfied":
            found.append(not_satisfied(question, verdict, observed))
    return Judgement(found, _sorted(observations), dict(levels))


def not_satisfied(question: Question, verdict: Verdict, observed: Mapping[str, object]) -> Finding:
    """Return `judge-not-satisfied` at the verdict's location when a region asked about holds it, else at the id line."""
    inside = any(_holds(region, verdict.path, verdict.line) for region in question.regions)
    path, line = (verdict.path, verdict.line) if inside else (question.item.path, question.item.line)
    message = f"the judge answered `{question.subject}` {question.kind} with not-satisfied: {verdict.reasoning}"
    return Finding(path, line, "earnest/judge-not-satisfied", question.subject, message, observations=(observed,))


def _holds(region: Region, path: str, line: int) -> bool:
    return region.path == path and region.first <= line <= region.last


def uncalibrated(model: Stub) -> Finding:
    """Return the run's `judge-uncalibrated` finding, at line 1 of the record; it reaches no stage."""
    # shortcut: the record holds no calibration until M6 writes one, so every judge run is uncalibrated; read the
    # `calibration` slot for a passing result of this model id and prompt hash when `earnest calibrate` exists
    message = (
        f"no passing calibration exists for the model {model.id} and the prompt {PROMPT_HASH}:"
        " run earnest calibrate before relying on the judge's verdicts"
    )
    return Finding(RECORD, 1, "earnest/judge-uncalibrated", model.id, message)


def _sorted(observations: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(observations, key=lambda each: (str(each["subject"]), str(each["question"])))
