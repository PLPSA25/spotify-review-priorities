"""Offline scope counts from a saved deterministic nonempty-ID permutation."""

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from pipeline.prepare import atomic_json, course_helper


def scope_profile(config: dict[str, Any], output: Path) -> dict[str, Any]:
    helper = course_helper(Path("data/check_submission.py"))
    seed, count = config["scope"]["seed"], config["scope"]["sample_size"]
    with closing(sqlite3.connect("file:artifacts/ingestion/state.sqlite3?mode=ro", uri=True)) as db:
        ids = [row[0] for row in db.execute("SELECT review_id FROM reviews WHERE status='pending'")]
        order = sorted(ids, key=lambda rid: (hashlib.sha256((seed + ":" + rid).encode()).digest(), rid))
        chosen = set(order[:count])
        golden = {row["review_id"] for row in helper.csv_rows(Path("data/golden_50_to_label.csv"))}
        forced = golden - chosen
        selected = chosen | golden
        texts = {text for rid, text in db.execute("SELECT review_id,review_text FROM reviews") if rid in selected}
        pilot_texts = {row["review_text"] for row in helper.csv_rows(Path("data/cost_100.csv"))}
        covered = sum(text in texts for (text,) in db.execute("SELECT review_text FROM reviews WHERE status='pending'"))
    output.mkdir(parents=True, exist_ok=True)
    from pipeline.labeler import atomic_csv

    atomic_csv(output / "permutation.csv", ["review_id"], [{"review_id": rid} for rid in order])
    report = {"seed": seed, "method": "Ascending SHA-256(seed + ':' + review_id), ID tie-break; all nonempty IDs",
              "permutation_sha256": helper.sha(output / "permutation.csv"), "permutation_count": len(order),
              "random_prefix_count": count, "forced_golden_additions": len(forced),
              "selected_review_ids": len(selected), "selected_distinct_texts": len(texts),
              "pilot_reusable_distinct_texts_if_config_unchanged": len(texts & pilot_texts),
              "potential_exact_text_completed_rows": covered, "coverage_fraction_estimated": covered / len(order),
              "classification_performed": False}
    atomic_json(output / "scope.json", report)
    return report
