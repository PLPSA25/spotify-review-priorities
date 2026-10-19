"""Two-scope replay, overwrite refusal and CSV-independent mismatch detection."""
import csv
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import replay_phase7_rankings as replay


@pytest.mark.skipif(
    not (replay.ROOT / "data/spotify_reviews_18months.csv").is_file(),
    reason="Raw review CSV is supplied separately",
)
def test_cli_reproduces_both_rankings(tmp_path: Path):
    out = tmp_path / "rankings"
    result = subprocess.run(
        [sys.executable, "-B", str(replay.ROOT / "scripts/replay_phase7_rankings.py"),
         "--out", str(out)],
        cwd=replay.ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS: baseline 35/35; random-prefix 35/35" in result.stdout
    for name in replay.RANKINGS:
        assert replay.read_ranking(out / name) == replay.read_ranking(replay.ROOT / "docs/phase7" / name)


def test_existing_directory_is_refused_before_loading(tmp_path: Path, monkeypatch):
    def unexpected_load(*args):
        pytest.fail("Existing output must be refused before reading inputs")

    monkeypatch.setattr(replay, "load_inputs", unexpected_load)
    with pytest.raises(ValueError, match="already exists"):
        replay.replay(tmp_path)


@pytest.mark.parametrize("changed", replay.RANKINGS)
def test_mismatch_exits_nonzero_without_raw_csv(tmp_path: Path, monkeypatch, capsys, changed):
    root = tmp_path / "repo"
    expected_dir = root / "docs/phase7"
    expected_dir.mkdir(parents=True)
    rows = [dict(zip(replay.FIELDS, values)) for values in (
        ("1", "issue-a", "3", "6", "2.000000", "6"),
        ("2", "issue-b", "1", "1", "1.000000", "1"),
    )]

    def write(path, contents):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, replay.FIELDS)
            writer.writeheader()
            writer.writerows(contents)

    for name in replay.RANKINGS:
        write(expected_dir / name, rows)

    def fake_business(_records, _sources, _prefix, output):
        for name in replay.RANKINGS:
            write(output / name, list(reversed(rows)) if name == changed else rows)

    monkeypatch.setattr(replay, "ROOT", root)
    monkeypatch.setattr(replay, "load_inputs", lambda version: ({}, {}, {}, {}, set()))
    monkeypatch.setattr(replay, "write_business", fake_business)
    monkeypatch.setattr(sys, "argv", ["replay_phase7_rankings.py", "--out", str(tmp_path / "out")])
    assert replay.main() == 1
    captured = capsys.readouterr()
    assert f"FAIL: {changed}: ranking fields or order mismatch" in captured.err
    assert "PASS" not in captured.out
