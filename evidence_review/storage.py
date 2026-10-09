"""Transactional local history. No globally shared SQLite connections."""

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .domain import (
    Answer,
    Dataset,
    canonical,
    digest,
    question_key,
    source_changes,
    validate_evidence,
)


def now():
    return datetime.now(UTC).isoformat()


SCHEMA = """
PRAGMA user_version = 1;
CREATE TABLE IF NOT EXISTS datasets(
 id TEXT PRIMARY KEY, payload TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS drafts(
 id TEXT PRIMARY KEY, qkey TEXT NOT NULL, question_id TEXT NOT NULL,
 payload TEXT NOT NULL, dataset_id TEXT NOT NULL REFERENCES datasets(id),
 origin TEXT NOT NULL, run_id TEXT, errors TEXT NOT NULL, created TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS drafts_question ON drafts(qkey, created);
CREATE TABLE IF NOT EXISTS approvals(
 id TEXT PRIMARY KEY, qkey TEXT NOT NULL, draft_id TEXT NOT NULL REFERENCES drafts(id),
 payload TEXT NOT NULL, dataset_id TEXT NOT NULL REFERENCES datasets(id),
 reviewer TEXT NOT NULL, stale INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS approvals_question ON approvals(qkey, created);
CREATE TABLE IF NOT EXISTS changes(
 id TEXT PRIMARY KEY, before_id TEXT NOT NULL REFERENCES datasets(id),
 after_id TEXT NOT NULL REFERENCES datasets(id), payload TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS approval_changes(
 approval_id TEXT NOT NULL REFERENCES approvals(id),
 change_id TEXT NOT NULL REFERENCES changes(id), PRIMARY KEY(approval_id, change_id));
CREATE TABLE IF NOT EXISTS events(
 id TEXT PRIMARY KEY, qkey TEXT, kind TEXT NOT NULL, payload TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs(
 id TEXT PRIMARY KEY, qkey TEXT NOT NULL, payload TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, started REAL NOT NULL);
"""


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connection() as conn:
            conn.executescript(SCHEMA)
        os.chmod(self.path, 0o600)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _dataset(conn):
        row = conn.execute(
            "SELECT d.id, d.payload FROM datasets d JOIN meta m "
            "ON m.key='active_dataset' AND m.value=d.id"
        ).fetchone()
        if not row:
            raise ValueError("No dataset imported")
        return row["id"], Dataset.model_validate_json(row["payload"])

    def snapshot(self):
        with self.connection() as conn:
            return self._dataset(conn)

    def dataset(self, dataset_id):
        with self.connection() as conn:
            row = conn.execute("SELECT payload FROM datasets WHERE id=?", (dataset_id,)).fetchone()
            return Dataset.model_validate_json(row["payload"])

    def import_dataset(self, data: Dataset):
        payload = data.model_dump(mode="json")
        dataset_id = digest(payload)
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            active = conn.execute("SELECT value FROM meta WHERE key='active_dataset'").fetchone()
            if active and active["value"] == dataset_id:
                return []
            old = self._dataset(conn)[1] if active else None
            conn.execute(
                "INSERT OR IGNORE INTO datasets VALUES(?,?,?)",
                (dataset_id, canonical(payload), now()),
            )
            changes = source_changes(old, data) if old else []
            approvals = conn.execute("SELECT * FROM approvals").fetchall()
            for change in changes:
                change_id = str(uuid4())
                conn.execute(
                    "INSERT INTO changes VALUES(?,?,?,?,?)",
                    (change_id, active["value"], dataset_id, canonical(change), now()),
                )
                for approval in approvals:
                    previous = Dataset.model_validate_json(
                        conn.execute(
                            "SELECT payload FROM datasets WHERE id=?", (approval["dataset_id"],)
                        ).fetchone()["payload"]
                    )
                    cited = Answer.model_validate_json(approval["payload"]).citations
                    dependencies = {previous.passage_map()[c.passage_id][0].id for c in cited}
                    affected = change["kind"] in {"added", "removed", "text", "authority"}
                    affected |= (
                        change["kind"] == "version" and change["document_id"] in dependencies
                    )
                    if affected:
                        conn.execute("UPDATE approvals SET stale=1 WHERE id=?", (approval["id"],))
                        conn.execute(
                            "INSERT INTO approval_changes VALUES(?,?)", (approval["id"], change_id)
                        )
            conn.execute(
                "INSERT INTO meta VALUES('active_dataset',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (dataset_id,),
            )
            self._event(
                conn, None, "dataset_import", {"dataset_id": dataset_id, "changes": len(changes)}
            )
            return changes

    @staticmethod
    def _event(conn, qkey, kind, payload):
        conn.execute(
            "INSERT INTO events VALUES(?,?,?,?,?)",
            (str(uuid4()), qkey, kind, canonical(payload), now()),
        )

    def event(self, question, kind, payload):
        with self.connection() as conn:
            self._event(conn, question_key(question) if question else None, kind, payload)

    def save_draft(self, question, answer: Answer, dataset_id, origin, run_id=None):
        answer = Answer.model_validate(answer.model_dump())
        errors = validate_evidence(answer, self.dataset(dataset_id))
        draft_id = str(uuid4())
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO drafts VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    draft_id,
                    question_key(question),
                    question.id,
                    answer.model_dump_json(),
                    dataset_id,
                    origin,
                    run_id,
                    canonical(errors),
                    now(),
                ),
            )
            self._event(conn, question_key(question), "draft_saved", {"draft_id": draft_id})
        return draft_id

    def latest_draft(self, question):
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM drafts WHERE qkey=? ORDER BY created DESC LIMIT 1",
                (question_key(question),),
            ).fetchone()
            return dict(row) if row else None

    def latest_approval(self, question):
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE qkey=? ORDER BY created DESC LIMIT 1",
                (question_key(question),),
            ).fetchone()
            return dict(row) if row else None

    def review_changes(self, approval_id):
        with self.connection() as conn:
            return [
                json.loads(row["payload"])
                for row in conn.execute(
                    "SELECT c.payload FROM changes c JOIN approval_changes ac ON c.id=ac.change_id "
                    "WHERE ac.approval_id=? ORDER BY c.created",
                    (approval_id,),
                )
            ]

    def draft_fresh(self, draft):
        old = self.dataset(draft["dataset_id"])
        _, current = self.snapshot()
        if old.source_signature() != current.source_signature():
            return False
        answer = Answer.model_validate_json(draft["payload"])
        previous = old.passage_map()
        latest = current.passage_map()
        return all(
            c.passage_id in latest
            and previous[c.passage_id][0].version == latest[c.passage_id][0].version
            for c in answer.citations
        )

    def approve(
        self,
        draft_id,
        reviewer,
        *,
        semantic_confirmed,
        changes_confirmed=False,
        expected_dataset_id=None,
    ):
        if not semantic_confirmed:
            raise ValueError("Human semantic review must confirm the complete answer")
        if not reviewer.strip() or len(reviewer) > 128:
            raise ValueError("Provide a local reviewer label")
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            draft = conn.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
            if draft is None:
                raise ValueError("Draft does not exist")
            latest = conn.execute(
                "SELECT id FROM drafts WHERE qkey=? ORDER BY created DESC LIMIT 1", (draft["qkey"],)
            ).fetchone()
            if latest["id"] != draft_id:
                raise ValueError("Draft changed: inspect the latest revision before approval")
            dataset_id, current = self._dataset(conn)
            if expected_dataset_id and expected_dataset_id != dataset_id:
                raise ValueError("Sources changed while reviewing; reload and inspect them")
            answer = Answer.model_validate_json(draft["payload"])
            problems = validate_evidence(answer, current)
            if answer.answerability != "supported" or problems:
                raise ValueError(
                    "Approval blocked: " + "; ".join(problems or ["Unresolved evidence"])
                )
            previous = conn.execute(
                "SELECT * FROM approvals WHERE qkey=? ORDER BY created DESC LIMIT 1",
                (draft["qkey"],),
            ).fetchone()
            old_source = Dataset.model_validate_json(
                conn.execute(
                    "SELECT payload FROM datasets WHERE id=?", (draft["dataset_id"],)
                ).fetchone()["payload"]
            )
            dependencies = {
                old_source.passage_map()[c.passage_id][0].id
                for c in answer.citations
                if c.passage_id in old_source.passage_map()
            }
            relevant_changes = [
                c
                for c in source_changes(old_source, current)
                if c["kind"] in {"added", "removed", "text", "authority"}
                or (c["kind"] == "version" and c["document_id"] in dependencies)
            ]
            if (relevant_changes or (previous and previous["stale"])) and not changes_confirmed:
                raise ValueError("Inspect and acknowledge the source changes before reapproval")
            approval_id = str(uuid4())
            conn.execute(
                "INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?)",
                (
                    approval_id,
                    draft["qkey"],
                    draft_id,
                    answer.model_dump_json(),
                    dataset_id,
                    reviewer.strip(),
                    0,
                    now(),
                ),
            )
            self._event(
                conn,
                draft["qkey"],
                "approved",
                {"approval_id": approval_id, "draft_id": draft_id, "semantic_review": "human"},
            )
            return approval_id

    def reusable(self, question):
        approval = self.latest_approval(question)
        if not approval or approval["stale"]:
            return None
        previous = self.dataset(approval["dataset_id"])
        _, current = self.snapshot()
        answer = Answer.model_validate_json(approval["payload"])
        if previous.source_signature() != current.source_signature():
            return None
        old_passages, new_passages = previous.passage_map(), current.passage_map()
        if any(
            c.passage_id not in new_passages
            or old_passages[c.passage_id][0].version != new_passages[c.passage_id][0].version
            for c in answer.citations
        ):
            return None
        if validate_evidence(answer, current):
            return None
        return approval

    def save_run(self, question, metadata):
        run_id = str(uuid4())
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO runs VALUES(?,?,?,?)",
                (run_id, question_key(question), canonical(metadata), now()),
            )
        return run_id

    def runs(self, question=None):
        with self.connection() as conn:
            sql = "SELECT * FROM runs"
            args = ()
            if question:
                sql += " WHERE qkey=?"
                args = (question_key(question),)
            return [
                dict(r) | {"metadata": json.loads(r["payload"])}
                for r in conn.execute(sql + " ORDER BY created DESC", args)
            ]

    def history(self, question):
        with self.connection() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM events WHERE qkey=? OR qkey IS NULL "
                    "ORDER BY created DESC LIMIT 50",
                    (question_key(question),),
                )
            ]

    def revisions(self, question):
        with self.connection() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM drafts WHERE qkey=? ORDER BY created DESC",
                    (question_key(question),),
                )
            ]

    def reserve_attempt(self, limit=50, per_minute=10):
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            total = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
            recent = conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE started>?", (time.time() - 60,)
            ).fetchone()[0]
            if total >= limit:
                raise ValueError("Persisted live-request budget exhausted")
            if recent >= per_minute:
                raise ValueError("Local rate limit: wait before another provider attempt")
            conn.execute("INSERT INTO attempts VALUES(?,?)", (str(uuid4()), time.time()))

    def require_review(self, question, reason):
        with self.connection() as conn:
            conn.execute("UPDATE approvals SET stale=1 WHERE qkey=?", (question_key(question),))
            self._event(conn, question_key(question), "human_review_required", {"reason": reason})

    def attempt_count(self):
        with self.connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
