"""Judge: the questions each traced EARS requirement asks, the model that answers them, and its observations (D14)."""

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from importlib.resources import files
from pathlib import Path, PurePosixPath

from earnest import adapters, ears, git
from earnest.index import Index, Item, Link, Override, Region, build_index, digest
from earnest.reporter import RECORD, Finding, canonical, location


# The questions, and the artifact types whose regions each asks about.
KINDS = {"implemented": frozenset({"impl"}), "tested": frozenset({"utest", "itest", "stest"})}
QUESTIONS = tuple(KINDS)
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
    cache: dict[str, object]  # the record's `judge` slot as this run leaves it


@dataclass
class Cache:
    """The judge cache: the record's entries, and the ones this run used, which are what the slot keeps."""

    root: Path
    model: Stub
    held: Mapping[str, object]
    used: dict[str, object] = field(default_factory=dict)
    hashes: dict[str, tuple[str, str]] = field(default_factory=dict)  # each item's code and test region hashes

    def ask(self, question: Question, index: Index) -> Verdict:
        """Return the cached verdict of a question whose key is unchanged, else ask the model and cache its answer."""
        item = question.item
        if (hashes := self.hashes.get(question.subject)) is None:
            code = self._hash(regions(index, item, KINDS["implemented"]))
            hashes = self.hashes[question.subject] = (code, self._hash(regions(index, item, KINDS["tested"])))
        code, tests = hashes
        parts = {
            "item": question.subject,
            "question": question.kind,
            "regions": code,
            "tests": tests,
            "model": self.model.id,
            "prompt": PROMPT_HASH,
        }
        key = digest(canonical(parts).encode("ascii"))
        verdict = _cached(self.held.get(key)) or self.model.ask(question)
        where = {"file": verdict.path, "line": verdict.line}
        self.used[key] = {**parts, "result": verdict.result, "reasoning": verdict.reasoning, "location": where}
        return verdict

    def _hash(self, found: Sequence[Region]) -> str:
        """Return the digest of regions: each one's path, lines and text, in path and line order."""
        chunks: list[bytes] = []
        for region in sorted(found, key=lambda each: (each.path, each.first, each.last)):
            text = (self.root / region.path).read_bytes().split(b"\n")[region.first - 1 : region.last]
            chunks.append(f"{region.path}:{region.first}-{region.last}\n".encode("utf-8", "surrogateescape"))
            chunks.append(b"\n".join(text) + b"\n")
        return digest(b"".join(chunks))


def _cached(entry: object) -> Verdict | None:
    """Return a cache entry's verdict, or None when the entry is not one this release wrote."""
    try:
        return _verdict(entry)
    except (TypeError, KeyError):
        return None


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
    except (ValueError, TypeError, KeyError, RecursionError) as error:  # UnicodeDecodeError is a ValueError
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


def questions(index: Index, levels: Mapping[str, str]) -> list[Question]:
    """Return the two questions of each traced requirement whose body is one EARS sentence, in index order."""
    # shortcut: a question carries its clause spans but no question text, as the stub reads no prompt; M6's real
    # model builds the text from the spans and prompt.txt
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


def judge(index: Index, levels: Mapping[str, str], model: Stub, root: Path, slot: Mapping[str, object]) -> Judgement:
    """Ask each question no standing override answers, and return the findings, observations, levels and cache.

    The cache is the record's `judge` slot, read from root's work tree; the questions this run asked or reused stay.

    Raises:
        JudgeError: the model cannot answer a question.
        OSError: a tagged file cannot be read.
    """
    held = slot.get("cache")
    cache = Cache(root, model, held if isinstance(held, dict) else {})
    standing, found = overrides(index)
    found.insert(0, uncalibrated(model))
    observations: list[dict[str, object]] = []
    satisfied: dict[str, int] = {}
    for question in questions(index, levels):
        override = standing.get((question.subject, question.kind))
        if override is not None:
            observed = observation(
                question, "maintainer", Verdict("satisfied", override.reason, override.path, override.line)
            )
            if (why := drifted(root, index, override, question.regions)) is not None:
                rerun = observation(question, "judge", located(root, question, cache.ask(question, index)))
                found.append(drift(override, why, observed, rerun))
        else:
            verdict = located(root, question, cache.ask(question, index))
            observed = observation(question, "judge", verdict)
            if verdict.result != "satisfied":
                found.append(not_satisfied(question, verdict, observed))
        observations.append(observed)
        satisfied[question.subject] = satisfied.get(question.subject, 0) + (observed["result"] == "satisfied")
    levels = {req: "judged" if satisfied.get(req) == len(QUESTIONS) else level for req, level in levels.items()}
    observations.sort(key=lambda each: (str(each["subject"]), str(each["question"])))
    return Judgement(found, observations, levels, {"cache": cache.used})


def located(root: Path, question: Question, verdict: Verdict) -> Verdict:
    """Return the verdict, at the item's id line when its location is no relative path to a file in root's work tree."""
    parts = PurePosixPath(verdict.path).parts
    if not parts or parts[0] == "/" or ".." in parts or not (root / verdict.path).is_file():
        return replace(verdict, path=question.item.path, line=question.item.line)
    return verdict


def overrides(index: Index) -> tuple[dict[tuple[str, str], Override], list[Finding]]:
    """Return the standing overrides by id and kind, and a `duplicate` for each repeat of an id and kind.

    An override stands when it names its item's current revision. One that names no defined item stands for nothing.
    """
    standing: dict[tuple[str, str], Override] = {}
    seen: dict[tuple[str, str], Override] = {}  # the first override of each id and kind, standing or expired
    found: list[Finding] = []
    for written in (override for item in index.items for override in item.overrides):
        item = index.defined.get(written.target.key)
        if item is None:
            continue
        key = (str(written.target), written.kind)
        first = seen.setdefault(key, written)
        if first is not written:
            message = (
                f"`{written.target}` {written.kind} is already overridden at {first.path}:{first.line}:"
                " keep one of the two overrides"
            )
            found.append(Finding(written.path, written.line, "earnest/duplicate", key[0], message))
        elif item.id != written.target:
            found.append(expired(written, item))
        else:
            standing[key] = written
    return standing, found


def expired(written: Override, item: Item) -> Finding:
    """Return `override-expired` at an override that names a revision other than its item's current one."""
    message = (
        f"the override of `{written.target}` {written.kind} names revision {written.target.revision}, and the item is"
        f" at `{item.id}`: judge the new revision, or write a new override for it"
    )
    return Finding(written.path, written.line, "earnest/override-expired", str(written.target), message)


def drifted(root: Path, index: Index, written: Override, found: Sequence[Region]) -> str | None:
    """Return why an override drifted: a region changed or was removed since its commit, or Git lacks the commit.

    A commit Git does not hold shows nothing of the code since it, so the override counts as drifted. None: it holds.
    """
    commit = git.full_commit(root, written.commit)  # the object, never a branch named as the prefix
    if commit is None:
        return f"Git holds no single commit {written.commit}, so nothing shows the code held still since the override"
    hunks = git.changed_lines(root, commit, {region.path for region in found}, keep_deletions=True)
    # shortcut: a region's end replaced by a new tag line is not caught, as the hunks map no old line to the region;
    # read old_line() against the region at the override's commit if such an edit must count as drift
    if any(_touches(hunk, region) for region in found for hunk in hunks.get(region.path, ())):
        return f"its code changed since {written.commit}, the commit the override stands at"
    if (path := _lost_tag(root, index, written, commit)) is not None:
        return (
            f"{path} lost a tag of its {written.kind} regions since {written.commit}, the commit the override stands at"
        )
    return None


def _lost_tag(root: Path, index: Index, written: Override, commit: str) -> str | None:
    """Return the first changed file that held more of the override's tags at its commit than at the work tree."""

    def count(links: Iterable[Link]) -> int:
        kinds = KINDS[written.kind]
        return sum(link.owner is None and link.target == written.target and link.type in kinds for link in links)

    for path in git.changed_files(root, commit):
        old = git.blob(root, commit, path)
        before = None if old is None else adapters.source(path, old)
        if before is not None and count(build_index([before]).links) > count(
            link for link in index.links if link.path == path
        ):
            return path
    return None


def _touches(hunk: git.Hunk, region: Region) -> bool:
    """Return whether a hunk writes a line of region, or deletes lines inside or at the end of region."""
    if hunk.new_count:
        return any(region.first <= line <= region.last for line in hunk.new_lines)
    return region.first <= hunk.new_start <= region.last


def drift(written: Override, why: str, observed: Mapping[str, object], rerun: Mapping[str, object]) -> Finding:
    """Return `override-drift` at the override, carrying its observation and then the judge's rerun."""
    message = (
        f"the override of `{written.target}` {written.kind} drifted: {why}; the judge now answers {rerun['result']};"
        " review the code, then move the override to a new commit"
    )
    subject = str(written.target)
    return Finding(
        written.path, written.line, "earnest/override-drift", subject, message, observations=(observed, rerun)
    )


def not_satisfied(question: Question, verdict: Verdict, observed: Mapping[str, object]) -> Finding:
    """Return `judge-not-satisfied` at the verdict's location when a region asked about holds it, else at the id line."""
    inside = any(_holds(region, verdict.path, verdict.line) for region in question.regions)
    path, line = (verdict.path, verdict.line) if inside else (question.item.path, question.item.line)
    message = (
        f"the judge answered `{question.subject}` {question.kind} with not-satisfied: {_escaped(verdict.reasoning)}"
    )
    return Finding(path, line, "earnest/judge-not-satisfied", question.subject, message, observations=(observed,))


def _escaped(text: str) -> str:
    """Return the model's text with each control character, a newline or an ANSI escape, written as its escape."""
    return "".join(character if character.isprintable() else ascii(character)[1:-1] for character in text)


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
