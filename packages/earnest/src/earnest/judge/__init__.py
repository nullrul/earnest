"""Judge: the questions each traced EARS requirement asks, the model that answers them, and its observations (D14)."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field, replace
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Protocol

from earnest import adapters, ears, git
from earnest.index import Index, Item, Link, Override, Region, build_index, digest
from earnest.reporter import RECORD, Finding, Record, canonical, location


if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    import anthropic
    from anthropic.types import OutputConfigParam


# The questions, and the artifact types whose regions each asks about.
KINDS = {"implemented": frozenset({"impl"}), "tested": frozenset({"utest", "itest", "stest"})}
QUESTIONS = tuple(KINDS)
_PROMPT = files(__package__).joinpath("prompt.txt").read_bytes()  # the bytes PROMPT_HASH names are the text sent
PROMPT_HASH = digest(_PROMPT)
MAX_TOKENS = 16000  # room for the thinking Opus 5.5 always does, and the verdict after it
_RESULTS = ("satisfied", "not-satisfied")
PASS_MATCHES = 8  # SC4: the judge passes calibration when it matches the maintainer on eight of ten requirements
TOTAL = 10


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
    """One question about one requirement: `implemented` or `tested`, its sentence, and the regions it asks about.

    `tagged` holds the item's code and test regions by question, both of which the question text shows.
    """

    item: Item
    kind: str
    sentence: ears.Sentence
    tagged: Mapping[str, tuple[Region, ...]]

    @property
    def regions(self) -> tuple[Region, ...]:
        """Return the regions this question asks about."""
        return self.tagged[self.kind]

    @property
    def subject(self) -> str:
        """Return the requirement's id with its revision."""
        return str(self.item.id)


class Model(Protocol):
    """A model that answers questions: the stub, or a real model."""

    @property
    def id(self) -> str:
        """Return the model's id, the key of its calibration."""

    def ask(self, question: Question) -> Verdict:
        """Return the verdict of a question."""


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
    model: Model
    held: Mapping[str, object]
    used: dict[str, object] = field(default_factory=dict)
    hashes: dict[str, tuple[str, str]] = field(default_factory=dict)  # each item's code and test region hashes

    @property
    def id(self) -> str:
        """Return the cached model's id."""
        return self.model.id

    def ask(self, question: Question) -> Verdict:
        """Return the cached verdict of a question whose key is unchanged, else ask the model and cache its answer."""
        if (hashes := self.hashes.get(question.subject)) is None:
            code = region_hash(self.root, question.tagged["implemented"])
            tested = region_hash(self.root, question.tagged["tested"])
            hashes = self.hashes[question.subject] = (code, tested)
        code, tests = hashes
        parts = {
            "item": question.subject,
            "question": question.kind,
            "sentence": digest(question.sentence.text.encode()),  # the model reads it; its clauses follow from it
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


def region_hash(root: Path, found: Sequence[Region]) -> str:
    """Return the digest of regions in root's work tree: each one's path, lines and text, in path and line order."""
    chunks: list[bytes] = []
    for region in sorted(found, key=lambda each: (each.path, each.first, each.last)):
        chunks.append(f"{region.path}:{region.first}-{region.last}\n".encode("utf-8", "surrogateescape"))
        chunks.append(_region_bytes(root, region) + b"\n")
    return digest(b"".join(chunks))


def held(record: Record, key: str) -> dict[str, object]:
    """Return the record's judge slot under key, or an empty one when it is not an object."""
    slot = record.judge.get(key)
    return slot if isinstance(slot, dict) else {}


def _region_bytes(root: Path, region: Region) -> bytes:
    """Return a region's lines from root's work tree; the cache key and the question text both slice them here."""
    return b"\n".join((root / region.path).read_bytes().split(b"\n")[region.first - 1 : region.last])


def _cached(entry: object) -> Verdict | None:
    """Return a cache entry's verdict, or None when the entry is not one this release wrote."""
    try:
        return _verdict(entry)
    except (TypeError, KeyError):
        return None


def load_model(value: str | None, root: Path) -> Model:
    """Return the model `EARNEST_JUDGE` names: `stub:<path>` or `anthropic:<model>`.

    A stub's path is absolute or relative to the working directory, whatever root is. Root is the directory whose
    files the questions' regions name, which a real model reads into each question.

    Raises:
        JudgeError: the value is unset or names no known model, the file cannot be read or is not the object of
            canned verdicts, or the SDK's client cannot start.
    """
    if not value:
        msg = "earnest needs a model: set EARNEST_JUDGE to anthropic:<model> or stub:<path of a canned-verdict file>"
        raise JudgeError(msg)
    kind, _, path = value.partition(":")
    if kind == "anthropic" and path:
        return _claude(value, root)
    if kind != "stub" or not path:
        msg = f"EARNEST_JUDGE names no model Earnest knows: {value!r}; use anthropic:<model> or stub:<path>"
        raise JudgeError(msg)
    data, answers = _read_answers(Path(path), "the stub model's file")
    return Stub("stub:" + digest(data), answers)


def _claude(value: str, root: Path) -> Claude:
    """Return the `anthropic:` model; the SDK resolves its own credentials, and earnest reads no key.

    Raises:
        JudgeError: the SDK's client cannot start.
    """
    import anthropic  # noqa: PLC0415  # only an `anthropic:` value loads the SDK, so stub runs never import it

    try:
        client = anthropic.Anthropic()
    except anthropic.AnthropicError as error:
        msg = f"the model {value} cannot start: {error}"
        raise JudgeError(msg) from error
    return Claude(value, root, client)


# The verdict object the model is asked for through structured outputs: the stub's canned-verdict answer.
_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "result": {"type": "string", "enum": list(_RESULTS)},
        "reasoning": {"type": "string"},
        "location": {
            "type": "object",
            "properties": {"file": {"type": "string"}, "line": {"type": "integer"}},
            "required": ["file", "line"],
            "additionalProperties": False,
        },
    },
    "required": ["result", "reasoning", "location"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Claude:
    """A Claude model through the `anthropic` SDK; its id is the `EARNEST_JUDGE` value, verbatim."""

    id: str
    root: Path
    client: anthropic.Anthropic

    def ask(self, question: Question) -> Verdict:
        """Send the question's text and return the model's structured verdict.

        Raises:
            JudgeError: the API fails, the model refuses or stops early, or its reply is not a verdict.
        """
        import anthropic  # noqa: PLC0415  # loaded already by load_model; named here for its error class

        asked = f"`{question.subject}` {question.kind}"
        # gating answer 3: effort is pinned in code, the verdict comes through structured outputs, and no sampling
        # parameter is sent
        config: OutputConfigParam = {"effort": "high", "format": {"type": "json_schema", "schema": _SCHEMA}}
        name = self.id.partition(":")[2]
        text = question_text(self.root, question)  # built outside the try: earnest's own errors are not the model's
        try:
            reply = self.client.messages.create(
                model=name,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": text}],
                output_config=config,
            )
        except (anthropic.AnthropicError, TypeError, ValueError) as error:
            # the SDK rejects a request unsent with a TypeError (no credentials) or a ValueError (max_tokens over the
            # non-streaming limit); its wording is not a contract, so every one of them cannot run
            msg = f"the model {self.id} cannot answer {asked}: {error}"
            raise JudgeError(msg) from error
        if reply.model != name:  # an alias: bind the cache and calibration to the model that answers
            msg = f"the model {self.id} answered {asked} as {reply.model}: set EARNEST_JUDGE=anthropic:{reply.model}"
            raise JudgeError(msg)
        if reply.stop_reason != "end_turn":  # a refusal, or a reply cut off at max_tokens
            msg = f"the model {self.id} stopped on {asked} with {reply.stop_reason}"
            raise JudgeError(msg)
        text = "".join(block.text for block in reply.content if block.type == "text")
        try:
            return _verdict(_from_line_one(json.loads(text)))
        except (ValueError, TypeError, KeyError, RecursionError) as error:
            msg = f"the model {self.id} gave a malformed answer to {asked}: {error}"
            raise JudgeError(msg) from error


def _from_line_one(answer: object) -> object:
    """Return the reply with a line below 1 read as line 1: structured outputs cannot hold the model to a minimum."""
    if isinstance(answer, dict) and isinstance(where := answer.get("location"), dict):
        line = where.get("line")
        if isinstance(line, int) and not isinstance(line, bool) and line < 1:
            return {**answer, "location": {**where, "line": 1}}
    return answer


def question_text(root: Path, question: Question) -> str:
    """Return what one question sends: prompt.txt, then the question, the sentence and its clauses, the code and tests.

    Each field is labelled, and each region is its lines from root's files between a BEGIN line naming its
    `path:first-last` and an END line; both carry a tag from the lines' digest, so the lines cannot forge the END.
    """
    lines = ["", f"Question: {question.kind}", f"Requirement: {question.sentence.text}", "Clauses:"]
    lines += [f"{clause.kind}: {clause.text}" for clause in question.sentence.clauses]
    for label, kind in (("Code regions:", "implemented"), ("Test regions:", "tested")):
        lines.append(label)
        for region in question.tagged[kind]:
            data = _region_bytes(root, region)
            tag = digest(data).removeprefix("sha256:")[:16]
            lines += [
                f"BEGIN {tag} {region.path}:{region.first}-{region.last}",
                data.decode(errors="replace"),
                f"END {tag}",
            ]
    return _PROMPT.decode("utf-8") + "\n".join(lines) + "\n"


def _read_answers(path: Path, name: str) -> tuple[bytes, dict[str, dict[str, Verdict]]]:
    """Return the bytes of a file of canned verdicts and its answers; name is how the messages call the file.

    Raises:
        JudgeError: the file cannot be read or is not the object of canned verdicts.
    """
    try:
        data = path.read_bytes()
        return data, _answers(json.loads(data, object_pairs_hook=_unique))
    except OSError as error:
        msg = f"{name} cannot be read: {error}"
        raise JudgeError(msg) from error
    except (ValueError, TypeError, KeyError, RecursionError) as error:  # UnicodeDecodeError is a ValueError
        msg = f"{name} {path} is not an object of canned verdicts: {error}"
        raise JudgeError(msg) from error


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Return the object of pairs; a key named twice raises, as json.loads would keep only the last."""
    if twice := sorted(key for key, count in Counter(key for key, _ in pairs).items() if count > 1):
        msg = f"it names {', '.join(map(escaped, twice))} more than once"
        raise ValueError(msg)
    return dict(pairs)


def load_verdicts(path: Path) -> dict[str, dict[str, Verdict]]:
    """Return the maintainer's verdicts, keyed by requirement id and revision, then by question.

    Raises:
        JudgeError: the file cannot be read or is not the object of canned verdicts.
    """
    return _read_answers(path, "the maintainer's verdicts")[1]


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
    asked: list[Question] = []
    for item in index.defined.values():
        sentence = ears.parse(item.body) if levels.get(str(item.id)) == "traced" else None
        if sentence is not None:
            tagged = {kind: regions(index, item, KINDS[kind]) for kind in QUESTIONS}
            asked.extend(Question(item, kind, sentence, tagged) for kind in QUESTIONS)
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


def judge(index: Index, levels: Mapping[str, str], model: Model, root: Path, record: Record) -> Judgement:
    """Ask each question no standing override answers, and return the findings, observations, levels and cache.

    The cache is the record's `judge` slot, read from root's work tree; a judge run that the record's `calibration`
    slot does not cover for this model and prompt raises `judge-uncalibrated`; the questions this run asked or reused stay.

    Raises:
        JudgeError: the model cannot answer a question.
        OSError: a tagged file cannot be read.
    """
    cache = Cache(root, model, held(record, "cache"))
    standing, found = overrides(index)
    past = Past(root)
    if not calibrated(record.calibration, model):
        found.insert(0, uncalibrated(model))
    observations: list[dict[str, object]] = []
    satisfied: dict[str, int] = {}
    for question in questions(index, levels):
        override = standing.get((question.subject, question.kind))
        if override is not None:
            observed = observation(
                question, "maintainer", Verdict("satisfied", override.reason, override.path, override.line)
            )
            if (why := drifted(past, index, override, question.regions)) is not None:
                rerun = observation(question, "judge", located(root, question, cache.ask(question)))
                found.append(drift(override, why, observed, rerun))
        else:
            verdict = located(root, question, cache.ask(question))
            observed = observation(question, "judge", verdict)
            if verdict.result != "satisfied":
                found.append(not_satisfied(question, verdict, observed))
        observations.append(observed)
        satisfied[question.subject] = satisfied.get(question.subject, 0) + (observed["result"] == "satisfied")
    levels = {req: "judged" if satisfied.get(req) == len(QUESTIONS) else level for req, level in levels.items()}
    observations.sort(key=lambda each: (str(each["subject"]), str(each["question"])))
    return Judgement(found, observations, levels, {"cache": cache.used})  # cli's _write_check keeps calibrate's answers


def located(root: Path, question: Question, verdict: Verdict) -> Verdict:
    """Return the verdict, at the item's id line when its location is no line of a file in root's work tree."""
    path = PurePosixPath(verdict.path)  # drops `.` parts and doubled slashes, keeps `..`
    parts = path.parts
    if (
        not parts
        or path.is_absolute()
        or ".." in parts
        or ".git" in parts
        or not (root / path).is_file()
        or verdict.line > len((root / path).read_bytes().splitlines())
    ):
        return replace(verdict, path=question.item.path, line=question.item.line)
    return replace(verdict, path=path.as_posix())


def overrides(index: Index) -> tuple[dict[tuple[str, str], Override], list[Finding]]:
    """Return the standing overrides by id and kind, and a `duplicate` for each repeat of an id and kind.

    An override stands when it names its item's current revision. One that names no defined item stands for nothing.
    """
    standing: dict[tuple[str, str], Override] = {}
    seen: dict[tuple[str, str], Override] = {}  # the first override of each id and kind, standing or expired
    found: list[Finding] = []
    # an override under a duplicate of its item stands for nothing: only the defining item's overrides count
    defining = [each for each in index.items if index.defined.get(each.id.key) is each]
    for item, written in ((each, override) for each in defining for override in each.overrides):
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


@dataclass
class Past:
    """The files of the override commits a run reads, each commit's tree and each path's tags read once."""

    root: Path
    trees: dict[str, frozenset[str] | None] = field(default_factory=dict)
    tags: dict[tuple[str, str], tuple[Link, ...] | None] = field(default_factory=dict)

    def links(self, commit: str, path: str) -> tuple[Link, ...] | None:
        """Return the tag links of path at a full commit id; none when its tree holds no such file.

        Returns:
            None when Git cannot read the commit's tree or the path's object: fail closed, so the caller drifts.
        """
        if commit not in self.trees:
            try:
                self.trees[commit] = git.tree_paths(self.root, commit)
            except git.GitError:
                self.trees[commit] = None
        tree = self.trees[commit]
        if tree is not None and path not in tree:
            return ()
        if (commit, path) not in self.tags:
            self.tags[commit, path] = None if tree is None else self._read(commit, path)
        return self.tags[commit, path]

    def _read(self, commit: str, path: str) -> tuple[Link, ...] | None:
        try:
            data = git.blob(self.root, commit, path)
        except git.GitError:
            return None
        source = adapters.source(path, data)
        return () if source is None else build_index([source]).links


def drifted(past: Past, index: Index, written: Override, found: Sequence[Region]) -> str | None:
    """Return why an override drifted: a region changed or was removed since its commit, or Git lacks the commit.

    A commit Git does not hold shows nothing of the code since it, so the override counts as drifted. None: it holds.
    """
    root = past.root
    commit = git.full_commit(root, written.commit)  # the object, never a branch named as the prefix
    if commit is None:
        return f"Git holds no single commit {written.commit}, so nothing shows the code held still since the override"
    hunks = git.changed_lines(root, commit, {region.path for region in found}, keep_deletions=True)
    # shortcut: a region's end replaced by a new tag line is not caught, as the hunks map no old line to the region;
    # read old_line() against the region at the override's commit if such an edit must count as drift
    if any(_touches(hunk, region) for region in found for hunk in hunks.get(region.path, ())):
        return f"its code changed since {written.commit}, the commit the override stands at"
    return _lost_tag(past, index, written, commit)


def _lost_tag(past: Past, index: Index, written: Override, commit: str) -> str | None:
    """Return why a changed file drifts the override: it held more of its tags at the commit, or Git cannot read it."""

    def count(links: Iterable[Link]) -> int:
        kinds = KINDS[written.kind]
        return sum(link.owner is None and link.target == written.target and link.type in kinds for link in links)

    since = f"since {written.commit}, the commit the override stands at"
    for path in git.changed_files(past.root, commit):
        before = past.links(commit, path)
        if before is None:
            return f"Git cannot read {path} at {written.commit}, so nothing shows its tags held still {since}"
        if count(before) > count(link for link in index.links if link.path == path):
            return f"{path} lost a tag of its {written.kind} regions {since}"
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
        f"the judge answered `{question.subject}` {question.kind} with not-satisfied: {escaped(verdict.reasoning)}"
    )
    return Finding(path, line, "earnest/judge-not-satisfied", question.subject, message, observations=(observed,))


def escaped(text: str) -> str:
    """Return the model's text with each control character, a newline or an ANSI escape, written as its escape."""
    return "".join(character if character.isprintable() else ascii(character)[1:-1] for character in text)


def _holds(region: Region, path: str, line: int) -> bool:
    return region.path == path and region.first <= line <= region.last


def uncalibrated(model: Model) -> Finding:
    """Return the run's `judge-uncalibrated` finding, at line 1 of the record; it reaches no stage."""
    message = (
        f"no passing calibration exists for the model {model.id} and the prompt {PROMPT_HASH}:"
        " run earnest calibrate <fixture> before relying on the judge's verdicts"
    )
    return Finding(RECORD, 1, "earnest/judge-uncalibrated", model.id, message)


@dataclass(frozen=True)
class Row:
    """One requirement's calibration: the judge's and the maintainer's verdict on each question."""

    subject: str
    judge: Mapping[str, Verdict]
    maintainer: Mapping[str, Verdict]

    @property
    def matched(self) -> bool:
        """Return whether the judge and the maintainer agree on both questions."""
        return all(self.judge[kind].result == self.maintainer[kind].result for kind in QUESTIONS)


@dataclass(frozen=True)
class Calibration:
    """A model's calibration: one row per requirement of the fixture."""

    model: str
    rows: tuple[Row, ...]

    @property
    def matches(self) -> int:
        """Return the count of requirements the judge matched."""
        return sum(row.matched for row in self.rows)

    @property
    def passed(self) -> bool:
        """Return whether the judge matched enough requirements (SC4)."""
        return self.matches >= PASS_MATCHES


def calibrate(
    index: Index,
    levels: Mapping[str, str],
    model: Model,
    root: Path,
    maintainer: Mapping[str, Mapping[str, Verdict]],
) -> Calibration:
    """Ask the model both questions of the ten requirements and set its verdicts beside the maintainer's.

    Overrides are ignored: every question is asked of the model, or of a Cache that holds its earlier answer. Each
    verdict's location is held to root's work tree, as check's are.

    Raises:
        JudgeError: the index does not hold exactly ten traced EARS requirements, each defined once, or the maintainer's verdicts lack
            an answer to one of their questions.
    """
    reqs = [item for item in index.defined.values() if item.id.type == "req"]
    subjects = {str(item.id) for item in reqs}
    asked = [question for question in questions(index, levels) if question.subject in subjects]
    posed = {question.subject for question in asked}  # questions() poses only traced EARS requirements
    faulty = [str(item.id) for item in reqs if str(item.id) not in posed]
    # index.defined keeps the first item per type and name, whatever its revision, and drops any later one unseen
    twice = sorted(
        {str(item.id) for item in index.items if item.id.type == "req" and index.defined[item.id.key] is not item}
    )
    if len(reqs) != TOTAL or faulty or twice:
        parts = ["calibration needs exactly ten traced EARS requirements"]
        if len(reqs) != TOTAL:
            parts[0] += f", not {len(reqs)}"
        if faulty:
            parts.append(f"untraced or not EARS: {', '.join(faulty)}")
        if twice:
            parts.append(f"defined more than once: {', '.join(twice)}")
        raise JudgeError("; ".join(parts))
    for question in asked:
        if question.kind not in maintainer.get(question.subject, {}):
            msg = f"the maintainer's verdicts hold no answer to `{question.subject}` {question.kind}"
            raise JudgeError(msg)
    judged = {(question.subject, question.kind): located(root, question, model.ask(question)) for question in asked}
    rows = tuple(
        Row(
            subject,
            {kind: judged[subject, kind] for kind in QUESTIONS},
            {kind: maintainer[subject][kind] for kind in QUESTIONS},
        )
        for subject in sorted(subjects)
    )
    return Calibration(model.id, rows)


def slot(calibration: Calibration) -> dict[str, object]:
    """Return the record's `calibration` value."""
    return {
        "model": calibration.model,
        "prompt": PROMPT_HASH,
        "matches": calibration.matches,
        "total": TOTAL,
        "pass": calibration.passed,
    }


def calibrated(held: Mapping[str, object] | None, model: Model) -> bool:
    """Return whether the record's `calibration` slot holds a pass for this model id and the current prompt hash."""
    return (
        held is not None
        and held.get("pass") is True
        and isinstance(matches := held.get("matches"), int)
        and matches >= PASS_MATCHES  # today's bar, not the one the slot was written under
        and held.get("total") == TOTAL
        and held.get("model") == model.id
        and held.get("prompt") == PROMPT_HASH
    )
