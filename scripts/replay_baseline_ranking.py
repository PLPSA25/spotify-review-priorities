"""Replay the submitted baseline offline: python -B scripts/replay_baseline_ranking.py --out DIR.

Reads saved grading records and membership, uses pipeline.rank.aggregate, and
compares every ranking field and row order with grading/ranking.csv. No model
calls, private database or sampling permutation. Refuses an existing output dir.
"""
import argparse
import csv
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.rank import aggregate  # noqa: E402

FIELDS = ["rank", "issue_id", "complaint_count", "severity_sum", "mean_severity", "priority_score"]


def replay(out: Path) -> tuple[int, int]:
    if out.exists():
        raise ValueError("Output directory already exists")
    with gzip.open(ROOT / "grading/records.jsonl.gz", "rt", encoding="utf-8") as stream:
        records = [record for line in stream
                   if (record := json.loads(line))["status"] == "completed"]
    with (ROOT / "grading/membership.csv").open(newline="", encoding="utf-8") as stream:
        members = list(csv.DictReader(stream))
    lookup = {row["review_id"]: row["issue_id"] for row in members}
    eligible = {row["review_id"] for row in records if row["intent"] in {"complaint", "cancellation"}}
    if len(lookup) != len(members) or set(lookup) != eligible:
        raise ValueError("Membership IDs do not match eligible records")
    _, ranking, _ = aggregate(records, lambda row: lookup[row["review_id"]])
    with (ROOT / "grading/ranking.csv").open(newline="", encoding="utf-8") as stream:
        expected = list(csv.DictReader(stream))
    if ranking != expected:
        raise ValueError("Baseline ranking fields or order mismatch")
    out.mkdir(parents=True, exist_ok=False)
    with (out / "ranking.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ranking)
    return len(ranking), len(members)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        issues, members = replay(args.out)
    except (ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {issues}/{issues} issue rows match all six fields and order; "
          f"membership {members}/{members}; tracked records/membership only; zero model calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
