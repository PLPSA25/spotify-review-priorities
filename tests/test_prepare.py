"""Check source preservation, accounting and ingestion failure behavior."""

import csv
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from pipeline.prepare import course_helper, prepare


def fixture_input(tmp_path: Path) -> tuple[Path, Path, list[dict[str, str]]]:
    helper = course_helper(Path("data/check_submission.py"))
    rows = []
    for rid, text in (("a", "café\n original "), ("b", "café\n original "), ("c", " ")):
        rows.append(dict(zip(helper.FIELDS, (rid, text, "2", "0", "", "2023-01-01"))))
    source = tmp_path / "test.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=helper.FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    manifest = json.loads(Path("data/manifest.json").read_text())
    manifest["files"][source.name] = {"sha256": helper.sha(source)}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    (tmp_path / "check_submission.py").write_bytes(Path("data/check_submission.py").read_bytes())
    return source, manifest_path, rows


def test_preserves_exact_source_and_accounts_for_empty(tmp_path: Path) -> None:
    source, manifest, rows = fixture_input(tmp_path)
    output = tmp_path / "output"
    prepare(source, manifest, output, Path("config.toml"))
    helper = course_helper(Path("data/check_submission.py"))
    with closing(sqlite3.connect(output / "state.sqlite3")) as database:
        saved = database.execute("SELECT review_text, source_sha256, status, reason "
                                 "FROM reviews ORDER BY review_id").fetchall()
    assert saved[0][:2] == (rows[0]["review_text"], helper.row_sha(rows[0]))
    assert saved[1][:2] == (rows[1]["review_text"], helper.row_sha(rows[1]))
    assert saved[2][2:] == ("quarantined", "empty_review_text")
    report = json.loads((output / "ingestion_report.json").read_text())
    assert report["distinct_nonempty_texts"] == 1
    assert report["internal_status_counts"] == {"pending": 2, "quarantined": 1}
    assert json.loads((output / "ingestion.json").read_text()) == helper.profile(source)


def test_checksum_failure_creates_no_database(tmp_path: Path) -> None:
    source, manifest, _ = fixture_input(tmp_path)
    source.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="checksum"):
        prepare(source, manifest, tmp_path / "output", Path("config.toml"))
    assert not (tmp_path / "output/state.sqlite3").exists()


def test_refuses_to_overwrite_existing_state(tmp_path: Path) -> None:
    source, manifest, _ = fixture_input(tmp_path)
    output = tmp_path / "output"
    prepare(source, manifest, output, Path("config.toml"))
    original = (output / "state.sqlite3").read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        prepare(source, manifest, output, Path("config.toml"))
    assert (output / "state.sqlite3").read_bytes() == original
