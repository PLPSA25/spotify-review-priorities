"""Offline human-label validation. Golden labels never become model inputs."""

import csv
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from pipeline.prepare import atomic_json, course_helper

LABEL_FIELDS = ("topic", "intent", "sentiment", "severity", "entities", "evidence_quote",
                "needs_review")


def create_template(source: Path, destination: Path) -> None:
    """Copy supplied bytes once, refusing to overwrite any human work."""
    helper = course_helper(Path(__file__).resolve().parents[1] / "data/check_submission.py")
    rows = list(helper.csv_rows(source))
    if len(rows) != 50 or any(row.get(field) != "" for row in rows for field in LABEL_FIELDS):
        raise ValueError("Expected 50 reviews with all seven human-label fields blank")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=destination.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(source.read_bytes())
            stream.flush()
            os.fsync(stream.fileno())
        # Windows rename refuses an existing target; POSIX link gives the same guarantee.
        if os.name == "nt":
            os.rename(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_golden(labels_path: Path, source: Path, report_path: Path) -> dict[str, Any]:
    """Check schema, exact source identity and quote membership without inference."""
    if report_path.resolve() in {source.resolve(), labels_path.resolve()}:
        raise ValueError("Validation report must not overwrite golden source or human labels")
    protected = Path(__file__).resolve().parents[1] / "data"
    if report_path.resolve().is_relative_to(protected.resolve()):
        raise ValueError("Never write validation reports into the preserved course data directory")
    helper = course_helper(Path(__file__).resolve().parents[1] / "data/check_submission.py")
    reference_rows = list(helper.csv_rows(source))
    expected = {row["review_id"]: row for row in reference_rows}
    if len(reference_rows) != 50 or len(expected) != 50:
        raise ValueError("Golden reference must contain 50 unique IDs")
    errors: list[dict[str, str]] = []
    seen: set[str] = set()
    valid = blank = 0

    def error(rid: str, field: str, message: str) -> None:
        errors.append({"review_id": rid, "field": field, "message": message})

    try:
        rows = list(helper.csv_rows(labels_path))
    except (ValueError, OSError, csv.Error, UnicodeError) as exc:
        rows = []
        error("", "file", str(exc))
    for row in rows:
        rid = row.get("review_id", "")
        before = len(errors)
        if rid not in expected:
            error(rid, "review_id", "Unknown original ID")
            continue
        if rid in seen:
            error(rid, "review_id", "Duplicate original ID")
            continue
        seen.add(rid)
        if any(row.get(field) != expected[rid][field] for field in helper.FIELDS):
            error(rid, "source", "Original field strings changed; restore from supplied source")
        if any(field not in row for field in LABEL_FIELDS):
            error(rid, "schema", "Missing required human-label columns")
            continue
        if all(row[field] == "" for field in LABEL_FIELDS):
            blank += 1
            error(rid, "labels", "Unlabeled; complete all seven fields yourself")
            continue
        if row["topic"] not in helper.TOPICS:
            error(rid, "topic", "Must be one of the eight exact contract labels")
        if row["intent"] not in helper.INTENTS:
            error(rid, "intent", "Must be cancellation, complaint, request, praise or unclear")
        if row["severity"] not in {"1", "2", "3", "4", "5"}:
            error(rid, "severity", "Must be an integer 1 through 5")
        try:
            sentiment = float(row["sentiment"])
            if not math.isfinite(sentiment) or not -1 <= sentiment <= 1:
                raise ValueError
        except ValueError:
            error(rid, "sentiment", "Must be a finite number from -1 through 1")
        try:
            entities = helper.loads(row["entities"])
            if not isinstance(entities, list) or any(
                not isinstance(entity, str) or not entity.strip() for entity in entities
            ):
                raise ValueError
        except ValueError:
            error(rid, "entities", 'Must be a JSON array of nonempty strings; use [] for none')
        quote = row["evidence_quote"]
        if not quote.strip() or quote not in expected[rid]["review_text"]:
            error(rid, "evidence_quote", "Must be a nonempty exact substring of original text")
        if row["needs_review"] not in {"true", "false"}:
            error(rid, "needs_review", "Use lowercase true or false")
        if len(errors) == before:
            valid += 1
    for rid in sorted(set(expected) - seen):
        error(rid, "review_id", "Missing original golden review")
    report = {"status": "valid" if not errors else "needs_human_labels_or_correction",
              "expected_records": len(expected), "received_records": len(rows),
              "valid_records": valid, "blank_records": blank, "errors": errors,
              "model_calls": 0,
              "limitation": "Schema and substring checks do not establish semantic correctness."}
    atomic_json(report_path, report)
    return report
