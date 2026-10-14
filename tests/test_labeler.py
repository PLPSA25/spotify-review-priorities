"""Exercise interactive save/resume with synthetic reviews only."""

from pathlib import Path

import pytest

from pipeline.labeler import label_golden
from pipeline.prepare import course_helper
from tests.test_labels import fixtures


def scripted(values: list[str]):
    answers = iter(values)

    def ask(prompt: str) -> str:
        return next(answers)

    return ask


def test_save_default_quote_resume_and_stop(tmp_path: Path) -> None:
    source, _ = fixtures(tmp_path)
    destination, report = tmp_path / "human.csv", tmp_path / "report.json"
    shown: list[str] = []
    answers = ["8", "5", "1", "0", "café, text", "", "y", "q"]
    assert label_golden(source, destination, report, scripted(answers), shown.append) == 1
    helper = course_helper(Path("data/check_submission.py"))
    rows = list(helper.csv_rows(destination))
    assert rows[0]["evidence_quote"] == "café\n synthetic text"
    assert rows[0]["entities"] == '["café", "text"]'
    assert rows[1]["topic"] == ""
    assert source.read_bytes() != destination.read_bytes()
    assert not destination.with_suffix(".csv.lock").exists()
    shown.clear()
    answers = ["bad", "8", "5", "1", "7", "-0.5", "", "not a quote", "café", "bad", "n", "q"]
    assert label_golden(source, destination, report, scripted(answers), shown.append) == 1
    rows = list(helper.csv_rows(destination))
    assert rows[1]["evidence_quote"] == "café"
    assert rows[1]["needs_review"] == "false"
    assert not any("Review 1/50" in message for message in shown)
    assert any("exact substring" in message for message in shown)


def test_interrupt_does_not_save_partial_review(tmp_path: Path) -> None:
    source, _ = fixtures(tmp_path)
    destination = tmp_path / "human.csv"

    def interrupted(prompt: str) -> str:
        raise KeyboardInterrupt

    assert label_golden(source, destination, tmp_path / "report.json", interrupted, lambda x: None) == 0
    assert source.read_bytes() == destination.read_bytes()
    with pytest.raises(ValueError, match="Never edit"):
        label_golden(source, source, tmp_path / "report.json")
