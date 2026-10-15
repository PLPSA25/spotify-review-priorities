"""Four-question parsing and the separately gated one-call measurement."""

import tomllib
from pathlib import Path

import pytest

from pipeline.classify import jev_payload, parse_jev
from pipeline.jev_measure import measurement_plan, run_measurement
from pipeline.providers import MockTransport


def test_choice_margin_routes_even_high_reported_confidence() -> None:
    config = tomllib.loads(Path("config.toml").read_text())
    response = MockTransport().request("typesafe", jev_payload("Music will not play.", config))
    topic = response["answers"]["topic"]
    topic["confidence"] = 0.99
    topic["probabilities"] = {key: 0.0 for key in topic["probabilities"]}
    topic["probabilities"][topic["choice"]] = 0.52
    rival = next(key for key in topic["probabilities"] if key != topic["choice"])
    topic["probabilities"][rival] = 0.48
    assert parse_jev(response, 0.75, 0.15)["needs_review"]
    assert parse_jev(response, 0.75, 0.15)["low_confidence"]


def test_measurement_is_offline_and_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pipeline.jev_measure.keys_from_env", lambda _: {})
    plan = measurement_plan(Path("config.toml"), tmp_path)
    assert plan["maximum_calls"] == 1 and plan["automatic_retries"] == 0
    assert plan["worst_case_nanodollars"] < 250000  # active v3 restores language/context judgments
    assert plan["synthetic_text"] == "Music will not play."
    with pytest.raises(ValueError, match="confirm-spend"):
        run_measurement(Path("config.toml"), tmp_path, tmp_path / "plan.json", False)
