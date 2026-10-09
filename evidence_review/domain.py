"""Input contracts, source authority, and structural evidence checks."""

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Passage(Contract):
    id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=32000)


class Document(Contract):
    id: str = Field(min_length=1, max_length=128)
    version: StrictInt = Field(ge=1)
    date: date
    status: Literal["current", "superseded"]
    supersedes: str | None
    passages: list[Passage] = Field(min_length=1)


class Question(Contract):
    id: str = Field(min_length=1, max_length=128)
    topic: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=2000)


class Dataset(Contract):
    documents: list[Document] = Field(min_length=1, max_length=128)
    questions: list[Question] = Field(min_length=1, max_length=500)
    owners: dict[str, str]

    @model_validator(mode="after")
    def references(self):
        documents = {d.id: d for d in self.documents}
        passage_ids = [p.id for d in self.documents for p in d.passages]
        if len(documents) != len(self.documents):
            raise ValueError("Duplicate document IDs")
        if len(set(passage_ids)) != len(passage_ids):
            raise ValueError("Duplicate passage IDs")
        if len({q.id for q in self.questions}) != len(self.questions):
            raise ValueError("Duplicate question IDs")
        if any(
            q.topic not in self.owners or not self.owners[q.topic].strip() for q in self.questions
        ):
            raise ValueError("Every question topic needs a supplied reviewer")
        for document in self.documents:
            visited = set()
            pointer = document.id
            while pointer is not None:
                if pointer not in documents:
                    raise ValueError("Missing supersedes target")
                if pointer in visited:
                    raise ValueError("Supersession cycle")
                visited.add(pointer)
                pointer = documents[pointer].supersedes
        return self

    def document_map(self):
        return {d.id: d for d in self.documents}

    def passage_map(self):
        return {p.id: (d, p) for d in self.documents for p in d.passages}

    def question(self, question_id):
        return next(q for q in self.questions if q.id == question_id)

    def source_signature(self):
        return digest(
            [
                {
                    "id": d.id,
                    "status": d.status,
                    "supersedes": d.supersedes,
                    "passages": sorted([p.model_dump() for p in d.passages], key=lambda p: p["id"]),
                }
                for d in sorted(self.documents, key=lambda d: d.id)
            ]
        )


def load_dataset(raw: bytes | str):
    if len(raw.encode() if isinstance(raw, str) else raw) > 65536:
        raise ValueError("Dataset exceeds the 64 KiB application limit")
    return Dataset.model_validate_json(raw)


def question_key(question: Question):
    return digest(["local-workspace", question.topic, question.text])


class Authority:
    def __init__(self, data: Dataset):
        self.documents = data.document_map()
        self.children = {document_id: [] for document_id in self.documents}
        for document in data.documents:
            if document.supersedes:
                self.children[document.supersedes].append(document.id)

    def family(self, document_ids):
        result = set(document_ids)
        pending = list(result)
        while pending:
            document_id = pending.pop()
            older = self.documents[document_id].supersedes
            adjacent = self.children[document_id] + ([older] if older else [])
            for other in adjacent:
                if other not in result:
                    result.add(other)
                    pending.append(other)
        return result

    def problem(self, document_id):
        for member in sorted(self.family([document_id])):
            successors = self.children[member]
            if len(successors) > 1:
                return f"Ambiguous replacement branches for {member}"
            if not successors and self.documents[member].status != "current":
                return f"{member} is superseded but has no explicit replacement"
            if successors and self.documents[member].status != "superseded":
                return f"{member} has an explicit replacement but inconsistent status"
        return None

    def current(self, document_id):
        if self.problem(document_id):
            return None
        while self.children[document_id]:
            document_id = self.children[document_id][0]
        return document_id

    def issues(self):
        return sorted({problem for d in self.documents if (problem := self.problem(d))})


class Citation(Contract):
    passage_id: str = Field(min_length=1, max_length=128)
    quote: str = Field(min_length=1, max_length=2000)


class Conflict(Contract):
    passage_ids: list[str] = Field(min_length=2, max_length=20)
    reason: str = Field(min_length=1, max_length=2000)


class Answer(Contract):
    answer: str = Field(min_length=1, max_length=4000)
    answerability: Literal["supported", "unknown", "conflicted"]
    conflict_resolution: Literal["none", "resolved_by_supersession", "unresolved"]
    citations: list[Citation] = Field(max_length=20)
    conflicts: list[Conflict] = Field(max_length=20)
    note: str = Field(max_length=2000)


def validate_evidence(answer: Answer, data: Dataset):
    """These checks establish structure and authority, NEVER semantic entailment."""
    problems = []
    passages = data.passage_map()
    authority = Authority(data)
    if answer.answerability == "supported" and not answer.citations:
        problems.append("Supported answer requires supporting citations")
    if answer.answerability == "supported" and answer.conflict_resolution == "unresolved":
        problems.append("An unresolved conflict cannot support approval")
    if answer.answerability == "conflicted" and answer.conflict_resolution != "unresolved":
        problems.append("Conflicted answer must remain unresolved")
    for citation in answer.citations:
        if citation.passage_id not in passages:
            problems.append(f"Missing passage: {citation.passage_id}")
            continue
        document, passage = passages[citation.passage_id]
        if citation.quote not in passage.text:
            problems.append(f"Quotation mismatch: {citation.passage_id}")
        if answer.answerability == "supported":
            if problem := authority.problem(document.id):
                problems.append(problem)
            elif authority.current(document.id) != document.id:
                problems.append(f"Historical source cannot establish current policy: {document.id}")
    for conflict in answer.conflicts:
        for passage_id in conflict.passage_ids:
            if passage_id not in passages:
                problems.append(f"Missing conflict passage: {passage_id}")
    if answer.conflict_resolution == "resolved_by_supersession":
        if not answer.conflicts:
            problems.append("Resolved disagreement requires visible historical references")
        for conflict in answer.conflicts:
            docs = {passages[p][0].id for p in conflict.passage_ids if p in passages}
            if len(docs) < 2 or len({authority.current(d) for d in docs}) != 1:
                problems.append("Conflict is not resolved by explicit replacement metadata")
    return sorted(set(problems))


def source_changes(old: Dataset, new: Dataset):
    before, after = old.document_map(), new.document_map()
    changes = []
    for document_id in sorted(before.keys() | after.keys()):
        a, b = before.get(document_id), after.get(document_id)
        kinds = []
        if a is None:
            kinds = ["added"]
        elif b is None:
            kinds = ["removed"]
        else:
            pa = sorted([p.model_dump() for p in a.passages], key=lambda p: p["id"])
            pb = sorted([p.model_dump() for p in b.passages], key=lambda p: p["id"])
            if pa != pb:
                kinds.append("text")
            if (a.status, a.supersedes) != (b.status, b.supersedes):
                kinds.append("authority")
            if a.version != b.version:
                kinds.append("version")
            if a.date != b.date:
                kinds.append("date")
        for kind in kinds:
            changes.append(
                {
                    "kind": kind,
                    "document_id": document_id,
                    "before": a.model_dump(mode="json") if a else None,
                    "after": b.model_dump(mode="json") if b else None,
                }
            )
    return changes
