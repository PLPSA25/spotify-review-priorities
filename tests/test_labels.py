"""Synthetic fixtures only; tests never label the real golden reviews."""

import csv
from pathlib import Path

import pytest

from pipeline.labels import LABEL_FIELDS, create_template, validate_golden
from pipeline.prepare import course_helper


def fixtures(tmp_path: Path) -> tuple[Path, Path]:
    helper = course_helper(Path("data/check_submission.py"))
    fields = (*helper.FIELDS, *LABEL_FIELDS)
    rows = [dict(zip(helper.FIELDS, (str(i), "café\n synthetic text", "1", "0", "", "2023")))
            for i in range(50)]
    source, labeled = tmp_path / "source.csv", tmp_path / "labels.csv"
    for path, labels in ((source, False), (labeled, True)):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                values = dict.fromkeys(LABEL_FIELDS, "")
                if labels:
                    values.update(topic="other", intent="unclear", sentiment="0", severity="1",
                                  entities="[]", evidence_quote="café\n", needs_review="true")
                writer.writerow({**row, **values})
    return source, labeled


def mutate(path: Path, field: str, value: str) -> None:
    helper = course_helper(Path("data/check_submission.py"))
    rows = list(helper.csv_rows(path))
    rows[0][field] = value
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def test_blank_copy_is_exact_and_never_overwrites(tmp_path: Path) -> None:
    source, _ = fixtures(tmp_path)
    copy = tmp_path / "copy.csv"
    create_template(source, copy)
    assert copy.read_bytes() == source.read_bytes()
    with pytest.raises(FileExistsError):
        create_template(source, copy)
    result = validate_golden(copy, source, tmp_path / "report.json")
    assert result["blank_records"] == 50
    assert result["valid_records"] == 0


def test_valid_synthetic_labels(tmp_path: Path) -> None:
    source, labeled = fixtures(tmp_path)
    assert validate_golden(labeled, source, tmp_path / "report.json")["status"] == "valid"


@pytest.mark.parametrize(("field", "value"), [
    ("topic", "payments"), ("intent", "angry"), ("severity", "3.0"),
    ("sentiment", "NaN"), ("sentiment", "1.1"), ("entities", '[""]'),
    ("entities", "{}"), ("needs_review", "TRUE"), ("evidence_quote", "cafe"),
    ("review_text", "changed"), ("review_id", "1"),
])
def test_rejects_invalid_fields(tmp_path: Path, field: str, value: str) -> None:
    source, labeled = fixtures(tmp_path)
    mutate(labeled, field, value)
    result = validate_golden(labeled, source, tmp_path / "report.json")
    assert result["status"] != "valid"
    assert result["errors"]


def test_rejects_missing_record(tmp_path: Path) -> None:
    source, labeled = fixtures(tmp_path)
    helper = course_helper(Path("data/check_submission.py"))
    rows = list(helper.csv_rows(labeled))[:-1]
    with labeled.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    result = validate_golden(labeled, source, tmp_path / "report.json")
    assert any(error["message"] == "Missing original golden review" for error in result["errors"])


def test_rejects_malformed_csv(tmp_path: Path) -> None:
    source, labeled = fixtures(tmp_path)
    labeled.write_text('review_id,review_text\n"unclosed', encoding="utf-8")
    result = validate_golden(labeled, source, tmp_path / "report.json")
    assert result["status"] != "valid"
    assert any(error["field"] == "file" for error in result["errors"])


def test_report_cannot_overwrite_human_work(tmp_path: Path) -> None:
    source, labeled = fixtures(tmp_path)
    original = labeled.read_bytes()
    with pytest.raises(ValueError, match="must not overwrite"):
        validate_golden(labeled, source, labeled)
    assert labeled.read_bytes() == original
