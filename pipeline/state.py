"""Transactional distinct-text queue, direct cache provenance and saved call evidence."""

import json
import sqlite3
import time
import uuid
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any

from pipeline.prepare import atomic_json, course_helper
from pipeline.schema import LABEL_FIELDS, cache_key, canonical, validate_record


class ConfigMismatch(ValueError):
    """A store cannot silently mix label configurations."""


class State:
    def __init__(self, path: Path, label_config: str) -> None:
        self.path, self.label_config = path, label_config
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            columns = {row[1] for row in db.execute("PRAGMA table_info(reviews)")}
            if columns and "source" not in columns:
                raise ValueError("Existing database is an ingestion store; choose a new enrichment output")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reviews(
                    review_id TEXT PRIMARY KEY, source TEXT NOT NULL, text TEXT NOT NULL,
                    status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, reason TEXT,
                    result TEXT, work_key TEXT);
                CREATE TABLE IF NOT EXISTS work(
                    key TEXT PRIMARY KEY,text TEXT NOT NULL,origin_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending', lease TEXT, lease_until REAL,
                    result TEXT, reason TEXT);
                CREATE TABLE IF NOT EXISTS calls(
                    request_id TEXT PRIMARY KEY,event TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS enrich_evidence(review_id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS call_reviews(
                    request_id TEXT NOT NULL,review_id TEXT NOT NULL,stage TEXT NOT NULL,
                    PRIMARY KEY(request_id,review_id));
                CREATE INDEX IF NOT EXISTS call_review_lookup ON call_reviews(review_id,stage);
                CREATE TABLE IF NOT EXISTS stage_results(
                    work_key TEXT NOT NULL, stage TEXT NOT NULL, result TEXT NOT NULL,
                    PRIMARY KEY(work_key,stage));
                CREATE TABLE IF NOT EXISTS artifacts(key TEXT PRIMARY KEY,result TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS reviews_work ON reviews(work_key);
                CREATE INDEX IF NOT EXISTS work_pending ON work(status,key);
            """)
            existing = db.execute("SELECT value FROM metadata WHERE key='label_config'").fetchone()
            if existing and existing[0] != label_config:
                raise ConfigMismatch(f"label_config mismatch: stored {existing[0]}, requested {label_config}")
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('label_config',?)", (label_config,))

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path, timeout=30)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            with db:
                yield db

    def ingest(self, source: Path, manifest: Path) -> None:
        helper = course_helper(manifest.parent / "check_submission.py")
        known = json.loads(manifest.read_text(encoding="utf-8"))["files"].get(source.name)
        checksum = helper.sha(source)
        if known and checksum != known["sha256"]:
            raise ValueError("Input checksum mismatch")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            seen: set[str] = set()
            for row in helper.csv_rows(source):
                row = {field: row[field] for field in helper.FIELDS}
                if row["review_id"] in seen:
                    raise ValueError("Duplicate input review ID")
                seen.add(row["review_id"])
                row["source_sha256"] = helper.row_sha(row)
                existing = db.execute("SELECT source FROM reviews WHERE review_id=?",
                                      (row["review_id"],)).fetchone()
                if existing:
                    if json.loads(existing[0]) != row:
                        raise ValueError("Existing ID has changed original source fields")
                    continue
                text = row["review_text"]
                key = cache_key(text, self.label_config)
                empty = not text.strip()
                db.execute("INSERT INTO reviews(review_id,source,text,status,reason,work_key) "
                           "VALUES (?,?,?,?,?,?)", (row["review_id"], canonical(row), text,
                           "quarantined" if empty else "pending",
                           "empty_review_text" if empty else None, None if empty else key))
                if not empty:
                    db.execute("INSERT OR IGNORE INTO work(key,text,origin_id) VALUES (?,?,?)",
                               (key, text, row["review_id"]))
                    work = db.execute("SELECT * FROM work WHERE key=?", (key,)).fetchone()
                    if work["text"] != text:
                        raise ValueError("Exact-text cache hash collision")
                    if work["status"] == "completed":
                        self._propagate(db, work)
                    elif work["status"] == "quarantined":
                        db.execute("UPDATE reviews SET status='quarantined',reason=? WHERE review_id=?",
                                   (work["reason"], row["review_id"]))
            if helper.sha(source) != checksum:
                raise ValueError("Input changed during ingestion")
            db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)",
                       ("input_sha256:" + str(source.resolve()), checksum))

    def claim(self, lease_seconds: float) -> dict[str, Any] | None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM work WHERE status='pending' AND lease IS NULL "
                             "ORDER BY key LIMIT 1").fetchone()
            if not row:
                return None
            token = str(uuid.uuid4())
            db.execute("UPDATE work SET lease=?,lease_until=? WHERE key=?",
                       (token, time.time() + lease_seconds, row["key"]))
            source = json.loads(db.execute("SELECT source FROM reviews WHERE review_id=?",
                                           (row["origin_id"],)).fetchone()[0])
            return {"key": row["key"], "lease": token, "source": source}

    def release(self, item: dict[str, Any]) -> None:
        with self.connect() as db:
            db.execute("UPDATE work SET lease=NULL,lease_until=NULL WHERE key=? AND lease=?",
                       (item["key"], item["lease"]))

    def events_for(self, rid: str, stage: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT c.event FROM calls c JOIN call_reviews r "
                              "ON c.request_id=r.request_id WHERE r.review_id=? "
                              "AND (? IS NULL OR r.stage=?) ORDER BY c.rowid", (rid, stage, stage))
            return [json.loads(row[0]) for row in rows]

    def expired_items(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            items = []
            for row in db.execute("SELECT * FROM work WHERE lease IS NOT NULL AND lease_until<? "
                                  "AND status='pending'", (time.time(),)):
                source = json.loads(db.execute("SELECT source FROM reviews WHERE review_id=?",
                                               (row["origin_id"],)).fetchone()[0])
                items.append({"key": row["key"], "lease": row["lease"], "source": source})
        return items

    def recover_expired(self) -> int:
        # Calls with uncertain outcome are never silently retried on lease expiry.
        with self.connect() as db:
            cursor = db.execute("UPDATE work SET reason='expired_lease_requires_reconciliation' "
                                "WHERE lease IS NOT NULL AND lease_until<?", (time.time(),))
            return cursor.rowcount

    def save_call(self, event: dict[str, Any]) -> None:
        with self.connect() as db:
            inserted = db.execute("INSERT OR IGNORE INTO calls VALUES (?,?)",
                                  (event["request_id"], canonical(event))).rowcount
            db.execute("UPDATE calls SET event=? WHERE request_id=?",
                       (canonical(event), event["request_id"]))
            for rid in event["review_ids"]:
                db.execute("INSERT OR IGNORE INTO call_reviews VALUES (?,?,?)",
                           (event["request_id"], rid, event["stage"]))
                if inserted and event["role"] == "enrich":
                    db.execute("UPDATE reviews SET attempts=attempts+1 WHERE review_id=?", (rid,))
                if event["outcome"] == "succeeded" and event["role"] == "enrich":
                    if event["label_config"] != self.label_config:
                        raise ConfigMismatch("Call label_config differs from store")
                    db.execute("INSERT OR IGNORE INTO enrich_evidence VALUES (?)", (rid,))

    def stage_result(self, key: str, stage: str, result: dict[str, Any] | None = None):
        with self.connect() as db:
            if result is not None:
                db.execute("INSERT OR REPLACE INTO stage_results VALUES (?,?,?)",
                           (key, stage, canonical(result)))
                return result
            row = db.execute("SELECT result FROM stage_results WHERE work_key=? AND stage=?",
                             (key, stage)).fetchone()
            return json.loads(row[0]) if row else None

    def artifact(self, key: str, result: dict[str, Any] | None = None) -> dict[str, Any] | None:
        with self.connect() as db:
            if result is not None:
                db.execute("INSERT OR REPLACE INTO artifacts VALUES (?,?)", (key, canonical(result)))
                return result
            row = db.execute("SELECT result FROM artifacts WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else None

    def observed_model(self, provider: str, model: str) -> None:
        with self.connect() as db:
            key = provider + "_returned_model"
            old = db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
            if old and old[0] != model:
                raise ConfigMismatch(f"Returned {provider} model changed: {old[0]} -> {model}")
            db.execute("INSERT OR IGNORE INTO metadata VALUES (?,?)", (key, model))

    def _propagate(self, db: sqlite3.Connection, work: sqlite3.Row) -> None:
        original = json.loads(work["result"])
        if original.get("cache_source_id"):
            raise ValueError("Cache origin cannot itself be a cache alias")
        if not db.execute("SELECT 1 FROM enrich_evidence WHERE review_id=?",
                          (original["review_id"],)).fetchone():
            raise ValueError("Cache origin lacks succeeded enrichment evidence")
        for row in db.execute("SELECT * FROM reviews WHERE work_key=? AND status='pending'",
                              (work["key"],)).fetchall():
            source = json.loads(row["source"])
            result = {field: original[field] for field in LABEL_FIELDS}
            result.update(review_id=row["review_id"], source_sha256=source["source_sha256"],
                          status="completed")
            if row["review_id"] != original["review_id"]:
                result["cache_source_id"] = original["review_id"]
            validate_record(result, source, self.label_config)
            db.execute("UPDATE reviews SET status='completed',result=?,reason=NULL WHERE review_id=?",
                       (canonical(result), row["review_id"]))

    def complete(self, item: dict[str, Any], result: dict[str, Any]) -> None:
        validate_record(result, item["source"], self.label_config)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute("UPDATE work SET status='completed',result=?,reason=NULL,lease=NULL,"
                                "lease_until=NULL WHERE key=? AND lease=? AND status='pending'",
                                (canonical(result), item["key"], item["lease"]))
            if cursor.rowcount != 1:
                raise ValueError("Stale/duplicate queue completion")
            self._propagate(db, db.execute("SELECT * FROM work WHERE key=?", (item["key"],)).fetchone())

    def quarantine(self, item: dict[str, Any], reason: str) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute("UPDATE work SET status='quarantined',reason=?,lease=NULL "
                                "WHERE key=? AND lease=?", (reason, item["key"], item["lease"]))
            if cursor.rowcount != 1:
                raise ValueError("Stale queue quarantine")
            db.execute("UPDATE reviews SET status='quarantined',reason=? WHERE work_key=? "
                       "AND status='pending'", (reason, item["key"]))

    def checkpoint(self, path: Path) -> None:
        with self.connect() as db:
            ids = [row[0] for row in db.execute("SELECT review_id FROM reviews "
                                              "WHERE status='completed' ORDER BY review_id")]
        atomic_json(path, {"completed_ids": ids, "label_config": self.label_config})

    def counts(self) -> dict[str, int]:
        with self.connect() as db:
            return dict(db.execute("SELECT status,COUNT(*) FROM reviews GROUP BY status"))

    def leased_count(self) -> int:
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM work WHERE lease IS NOT NULL "
                              "AND status='pending'").fetchone()[0]
