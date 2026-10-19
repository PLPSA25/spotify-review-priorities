"""Offline two-scope replay: python -B scripts/replay_phase7_rankings.py --out DIR.

Uses tracked Phase 7 inputs plus data/spotify_reviews_18months.csv. Writes the
six write_business artifacts into a new directory and checks all six ranking
fields and row order against docs/phase7. No model calls or private database.
"""
import argparse
from contextlib import chdir
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.phase7_work import load_inputs, write_business  # noqa: E402

FIELDS = ["rank", "issue_id", "complaint_count", "severity_sum", "mean_severity", "priority_score"]
RANKINGS = ("ranking.csv", "sample_ranking.csv")


def read_ranking(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"{path.name}: ranking columns mismatch")
        return list(reader)


def replay(out: Path) -> tuple[int, int]:
    out = out.resolve()
    if out.exists():
        raise ValueError("Output directory already exists")
    with chdir(ROOT):
        records, sources, _proposal, _taxonomy, prefix = load_inputs("v3")
        out.mkdir(parents=True, exist_ok=False)
        write_business(records, sources, prefix, output=out)
        counts = []
        for name in RANKINGS:
            actual = read_ranking(out / name)
            expected = read_ranking(ROOT / "docs/phase7" / name)
            if actual != expected:
                raise ValueError(f"{name}: ranking fields or order mismatch")
            counts.append(len(actual))
    return counts[0], counts[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        baseline, secondary = replay(args.out)
    except (ValueError, OSError, csv.Error) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: baseline {baseline}/{baseline}; random-prefix {secondary}/{secondary}; "
          "all six fields and row order match; zero model calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
