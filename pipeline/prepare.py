"""Verify exact bytes and preserve every original row in an offline SQLite store."""

import importlib.util
import json
import os
import sqlite3
import tempfile
import tomllib
from contextlib import closing
from pathlib import Path
from types import ModuleType
from typing import Any


def course_helper(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("course_audit", path)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load supplied checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare(source: Path, manifest_path: Path, output: Path, config_path: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    chunk_size = config["ingestion"]["chunk_size"]
    if type(chunk_size) is not int or chunk_size < 1:
        raise ValueError("chunk_size must be a positive integer")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (output / "state.sqlite3").exists():
        raise ValueError("State store already exists; choose a new output directory")
    helper = course_helper(manifest_path.parent / "check_submission.py")
    source_hash = helper.sha(source)
    declared = manifest["files"].get(source.name)
    if declared and source_hash != declared["sha256"]:
        raise ValueError("Input checksum differs from course manifest")
    profile = helper.profile(source)
    if profile["file_sha256"] != source_hash:
        raise ValueError("Input changed during profiling")
    is_full = source.name == manifest["assignment_scope"]["final_input"]
    if is_full and profile["counts"] != manifest["profile"]:
        raise ValueError("Full-file profile differs from course manifest")
    output.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=output, suffix=".sqlite3.tmp")
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(temporary)) as database:
            # This unpublished scratch database is disposable after interruption.
            # Avoid costly disk journals; publish only after all validation succeeds.
            database.execute("PRAGMA journal_mode=MEMORY")
            database.execute("PRAGMA cache_size=-65536")
            database.execute("CREATE TABLE reviews (review_id TEXT PRIMARY KEY, review_text TEXT "
                             "NOT NULL, review_rating TEXT NOT NULL, review_likes TEXT NOT NULL, "
                             "app_version TEXT NOT NULL, review_timestamp TEXT NOT NULL, "
                             "source_sha256 TEXT NOT NULL, status TEXT NOT NULL "
                             "CHECK(status IN ('pending','completed','quarantined')), "
                             "attempt_count INTEGER NOT NULL DEFAULT 0, reason TEXT)")
            database.execute("CREATE TABLE exact_texts (review_text TEXT PRIMARY KEY)")
            batch: list[tuple[Any, ...]] = []
            for row in helper.csv_rows(source):
                empty = not row["review_text"].strip()
                batch.append(tuple(row[key] for key in helper.FIELDS) + (
                    helper.row_sha(row), "quarantined" if empty else "pending",
                    "empty_review_text" if empty else None,
                ))
                if not empty:
                    database.execute("INSERT OR IGNORE INTO exact_texts VALUES (?)",
                                     (row["review_text"],))
                if len(batch) >= chunk_size:
                    database.executemany("INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,0,?)", batch)
                    database.commit()
                    batch.clear()
            database.executemany("INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,0,?)", batch)
            database.commit()
            distinct = database.execute("SELECT COUNT(*) FROM exact_texts").fetchone()[0]
            counts = dict(database.execute("SELECT status, COUNT(*) FROM reviews GROUP BY status"))
            if sum(counts.values()) != profile["counts"]["records"]:
                raise ValueError("Database row accounting mismatch")
            if is_full and distinct != 484189:
                raise ValueError("Distinct nonempty text count differs from required 484189")
        if helper.sha(source) != source_hash:
            raise ValueError("Input changed during ingestion")
        os.replace(temporary, output / "state.sqlite3")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    report = {**profile, "distinct_nonempty_texts": distinct, "internal_status_counts": counts,
              "model_calls": 0, "scope": config["scope"],
              "classification_started": False}
    identity = {"source_file": source.name, "source_sha256": source_hash,
                "source_bytes": source.stat().st_size, "source": manifest["source"],
                "course_manifest_sha256": helper.sha(manifest_path),
                "checker_sha256": helper.sha(manifest_path.parent / "check_submission.py"),
                "fields": list(helper.FIELDS), "checksum_matches_course_manifest": bool(declared)}
    atomic_json(output / "ingestion.json", profile)
    atomic_json(output / "ingestion_report.json", report)
    atomic_json(output / "data_manifest.json", identity)
    return profile["counts"]
