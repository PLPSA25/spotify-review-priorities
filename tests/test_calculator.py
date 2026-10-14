"""Arithmetic fixtures are synthetic and temporary, never claimed as real pilot output."""

import csv
import json
from decimal import Decimal
from pathlib import Path

from pipeline.calculator import billed_items, replay
from pipeline.prepare import atomic_json


def test_doubling_rates_doubles_spend_not_time_or_local_compute(tmp_path: Path) -> None:
    (tmp_path / "rates.csv").write_bytes(Path("cost/rates.csv").read_bytes())
    event = {"request_id": "arithmetic-fixture", "run_id": "fixture", "provider": "typesafe", "model": "jev-1.13.0",
             "service_tier": "standard", "role": "enrich", "stage": "jev", "phase": "initial",
             "input_tokens": 1000000, "output_tokens": 999, "outcome": "succeeded"}
    (tmp_path / "pilot_calls.jsonl").write_text(json.dumps(event) + "\n")
    atomic_json(tmp_path / "measurements.json", {"cold": {"end_to_end_seconds": 12.5, "distinct_texts": 100,
                 "counts": {"completed": 100}, "input_rows": 100}, "warm": {"end_to_end_seconds": 1.25},
                 "local_compute_cost_usd": 0.75})
    first = replay(tmp_path)
    with (tmp_path / "rates.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row["price_per_million"] = str(Decimal(row["price_per_million"]) * 2)
    with (tmp_path / "double.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    doubled = replay(tmp_path, tmp_path / "double.csv")
    assert Decimal(doubled["api_spend_usd"]) == Decimal(first["api_spend_usd"]) * 2
    assert doubled["measured_time_seconds"] == first["measured_time_seconds"]
    assert doubled["local_compute_cost_usd"] == first["local_compute_cost_usd"]


def test_billing_items_do_not_double_count_cached_or_reasoning_tokens() -> None:
    event = {"provider": "openai", "input_tokens": 1000, "output_tokens": 100,
             "response": {"usage": {"input_tokens_details": {"cached_tokens": 300, "cache_write_tokens": 200},
                                     "output_tokens_details": {"reasoning_tokens": 40}}}}
    assert billed_items(event) == {"input": 500, "cached_input": 300, "cache_write": 200, "output": 100}


def test_default_replay_without_measurements_has_no_fabricated_usage(tmp_path: Path) -> None:
    (tmp_path / "rates.csv").write_bytes(Path("cost/rates.csv").read_bytes())
    result = replay(tmp_path)
    assert result["status"] == "awaiting_real_cold_warm_pilot"
    assert result["api_spend_usd"] is None
