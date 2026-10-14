"""Interactive human-only labeling; no provider imports or network access."""

import csv
import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from pipeline.labels import LABEL_FIELDS, create_template, validate_golden
from pipeline.prepare import course_helper


class StopLabeling(Exception):
    """The user requested a safe stop."""


def atomic_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def label_golden(source: Path, destination: Path, report: Path,
                 ask: Callable[[str], str] = input,
                 show: Callable[[str], None] = print) -> int:
    """Save each complete review atomically and resume past validated human work."""
    if source.resolve() == destination.resolve():
        raise ValueError("Never edit the supplied golden template")
    if not destination.exists():
        create_template(source, destination)
    helper = course_helper(Path(__file__).resolve().parents[1] / "data/check_submission.py")
    lock = destination.with_suffix(destination.suffix + ".lock")
    # Exclusive session lock prevents two interactive labelers overwriting each other.
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    saved = 0
    try:
        result = validate_golden(destination, source, report)
        if any(error["field"] in {"file", "source", "schema", "review_id"}
               for error in result["errors"]):
            raise ValueError("Golden source/IDs changed; inspect the validation report first")
        invalid = {error["review_id"] for error in result["errors"]}
        rows = list(helper.csv_rows(destination))
        fields = list(rows[0])

        def answer(prompt: str) -> str:
            value = ask(prompt)
            if value.strip().lower() == "q":
                raise StopLabeling
            return value

        def menu(name: str, choices: tuple[str, ...]) -> str:
            show(name + ": " + "; ".join(f"{i}: {choice}" for i, choice in enumerate(choices, 1)))
            while True:
                value = answer(f"{name} number (q to stop): ").strip()
                if value.isdigit() and 1 <= int(value) <= len(choices):
                    return choices[int(value) - 1]
                show("Choose one of the listed numbers.")

        for index, row in enumerate(rows, 1):
            if row["review_id"] not in invalid:
                continue
            show(f"\nReview {index}/50 | {row['review_id']}\n{row['review_text']}")
            values = {"topic": menu("topic", helper.TOPICS),
                      "intent": menu("intent", ("cancellation", "complaint", "request",
                                               "praise", "unclear")),
                      "severity": menu("severity", ("1", "2", "3", "4", "5"))}
            while True:
                value = answer("sentiment [-1, -0.5, 0, 0.5, 1]: ").strip()
                if value in {"-1", "-0.5", "0", "0.5", "1"}:
                    values["sentiment"] = value
                    break
                show("Choose one of the five sentiment values.")
            entities = answer("entities, comma-separated (Enter for none): ")
            values["entities"] = json.dumps([term.strip() for term in entities.split(",")
                                            if term.strip()], ensure_ascii=False)
            while True:
                quote = answer("quote: Enter for full text, or type an exact substring: ")
                quote = row["review_text"] if quote == "" else quote
                if quote.strip() and quote in row["review_text"]:
                    values["evidence_quote"] = quote
                    break
                show("Quote must be a nonempty exact substring; spelling and spaces must match.")
            while True:
                value = answer("needs_review [y/n]: ").strip().lower()
                if value in {"y", "n"}:
                    values["needs_review"] = "true" if value == "y" else "false"
                    break
                show("Enter y or n.")
            assert set(values) == set(LABEL_FIELDS)
            row.update(values)
            atomic_csv(destination, fields, rows)
            saved += 1
            show("Saved this review.")
    except (StopLabeling, EOFError, KeyboardInterrupt):
        show("Stopped safely; completed reviews are saved, current unfinished review is unchanged.")
    finally:
        lock.unlink()
        validate_golden(destination, source, report)
    show(f"Saved {saved} reviews this session. Resume with the same command.")
    return saved
