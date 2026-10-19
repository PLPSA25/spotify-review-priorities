"""Submission-level baseline replay, overwrite refusal and mismatch detection."""
import csv
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import replay_baseline_ranking as replay


def test_cli_reproduces_submitted_ranking(tmp_path: Path):
    out = tmp_path / "ranking"
    result = subprocess.run(
        [sys.executable, "-B", str(replay.ROOT / "scripts/replay_baseline_ranking.py"), "--out", str(out)],
        cwd=replay.ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS: 35/35 issue rows" in result.stdout
    with (out / "ranking.csv").open(newline="", encoding="utf-8") as actual:
        with (replay.ROOT / "grading/ranking.csv").open(newline="", encoding="utf-8") as expected:
            assert list(csv.DictReader(actual)) == list(csv.DictReader(expected))


def test_existing_directory_is_refused(tmp_path: Path):
    with pytest.raises(ValueError, match="already exists"):
        replay.replay(tmp_path)


def test_changed_order_fails_without_creating_output(tmp_path: Path, monkeypatch):
    aggregate = replay.aggregate

    def wrong_order(*args):
        members, ranking, claims = aggregate(*args)
        return members, list(reversed(ranking)), claims

    monkeypatch.setattr(replay, "aggregate", wrong_order)
    out = tmp_path / "mismatch"
    with pytest.raises(ValueError, match="mismatch"):
        replay.replay(out)
    assert not out.exists()
