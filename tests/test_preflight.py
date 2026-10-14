"""Two-call plans are offline; execution requires explicit approved-plan confirmation."""

from pathlib import Path

import pytest

from pipeline.preflight import preflight_plan, run_preflight


def test_preflight_plan_never_dispatches(tmp_path: Path) -> None:
    plan = preflight_plan(Path("config.toml"), tmp_path, check_keys=False)
    assert plan["maximum_calls"] == 2
    assert plan["automatic_retries"] == 0
    assert plan["worst_case_nanodollars"] < 2_000_000  # less than $0.002, estimated only
    assert plan["calls"][1]["output_token_cap"] == 256
    assert not (tmp_path / "state.sqlite3").exists()


def test_preflight_cannot_execute_without_confirmation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="explicit yes"):
        run_preflight(Path("config.toml"), tmp_path, False, tmp_path / "plan.json")
