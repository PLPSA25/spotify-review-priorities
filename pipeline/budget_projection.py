"""Offline pre-pilot budget estimates anchored to saved Jev billing evidence."""

import csv
import json
import math
import sqlite3
import tomllib
from contextlib import closing
from pathlib import Path

from pipeline.prepare import atomic_json
from pipeline.schema import configuration
from pipeline.spend import Ledger


def project(config_path: Path = Path("config.toml"), output: Path = Path("cost/project_budget.json")) -> dict:
    config = tomllib.loads(config_path.read_text())
    measured = json.loads(Path("artifacts/jev-v2-test/result.json").read_text())
    plan = json.loads(Path("artifacts/jev-v2-test/plan.json").read_text())
    if plan["configuration"] != configuration(config):
        raise ValueError("Measured prompt configuration differs from current configuration")
    def texts(path: Path) -> set[str]:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return {row["review_text"] for row in csv.DictReader(handle) if row["review_text"].strip()}

    with Path("artifacts/sampling/permutation.csv").open(newline="", encoding="utf-8") as handle:
        import itertools

        selected = {row["review_id"] for row in itertools.islice(csv.DictReader(handle), config["scope"]["sample_size"])}
    with Path("data/golden_50_to_label.csv").open(newline="", encoding="utf-8-sig") as handle:
        selected.update(row["review_id"] for row in csv.DictReader(handle))
    with closing(sqlite3.connect("file:artifacts/ingestion/state.sqlite3?mode=ro", uri=True)) as db:
        scope = {text for rid, text in db.execute("SELECT review_id,review_text FROM reviews") if rid in selected}
    stages = []
    union: set[str] = set()
    for name, current in [("pilot_100", texts(Path("data/cost_100.csv"))),
                          ("checkpoint_500", texts(Path("data/checkpoint_500.csv"))),
                          ("analysis_10000", texts(Path("data/analysis_10000.csv"))), ("scope_100k", scope)]:
        new = current - union
        stages.append({"stage": name, "distinct_texts": len(current), "new_distinct_texts": len(new)})
        union.update(current)
    base_tokens = measured["billed_input_tokens"]
    reference_bytes = len(plan["synthetic_text"].encode())
    rates = config["planning_rates"]
    scenarios = []
    for name, bytes_per_token, retry_fraction in [("base_estimate", 4, 0.10), ("conservative_estimate", 1, 0.50)]:
        # Length extrapolation is an assumption, not tokenizer measurement.
        jev_tokens = sum(base_tokens + math.ceil(max(0, len(text.encode()) - reference_bytes) / bytes_per_token) for text in union)
        scope_tokens = sum(base_tokens + math.ceil(max(0, len(text.encode()) - reference_bytes) / bytes_per_token) for text in scope)
        long = {text for text in union if len(text) > config["enrichment"]["short_review_chars"]}
        fallback = math.ceil(len(union) * config["controls"]["fallback_fraction"])
        luna_reviews = min(len(union), len(long) + fallback)
        # Assume every allowed fallback, disjoint from long extraction; no caching savings.
        text_tokens = sum(math.ceil(len(text.encode()) / bytes_per_token) for text in long)
        short_lengths = sorted((len(text.encode()) for text in union - long), reverse=True)
        text_tokens += sum(math.ceil(length / bytes_per_token) for length in short_lengths[:fallback])
        batches = math.ceil(luna_reviews / config["enrichment"]["batch_size"])
        luna_inputs = text_tokens + luna_reviews * 80 + batches * 1500
        luna_outputs = luna_reviews * config["enrichment"]["luna_output_tokens_per_review"]
        jev_usd = jev_tokens * rates["jev_input_per_million"] / 1e6
        luna_usd = (luna_inputs * rates["luna_cache_write_per_million"] + luna_outputs * rates["luna_output_per_million"]) / 1e6
        # Pilot ten, up to 500 at each of three subsequent runs; excludes golden.
        verification_reviews = 10 + 3 * config["verification"]["sample_size"]
        verify_usd = (verification_reviews * 1500 * rates["luna_cache_write_per_million"] + verification_reviews * 200 * rates["luna_output_per_million"]) / 1e6
        fixed_usd = 4 * ((20000 + 24000) * rates["luna_cache_write_per_million"] + (512 + 1200) * rates["luna_output_per_million"]) / 1e6
        initial = jev_usd + luna_usd + verify_usd + fixed_usd
        spent = Ledger(Path(config["controls"]["ledger_path"]), config["controls"]["project_api_cap_usd"]).totals()
        total = initial * (1 + retry_fraction) + spent["spent_nanodollars"] / 1e9
        scenarios.append({"scenario": name, "assumed_bytes_per_extra_token": bytes_per_token,
                          "assumed_retry_cost_fraction": retry_fraction, "jev_scope_usd_before_retries": scope_tokens * rates["jev_input_per_million"] / 1e6,
                          "jev_all_development_and_scope_usd": jev_usd, "luna_enrichment_usd": luna_usd,
                          "luna_enrichment_reviews_upper_assumed": luna_reviews, "verification_reviews": verification_reviews,
                          "verification_usd": verify_usd, "group_and_memo_four_runs_usd": fixed_usd,
                          "retry_allowance_usd": initial * retry_fraction, "already_spent_usd": spent["spent_nanodollars"] / 1e9,
                          "total_project_usd": total, "under_project_cap": total <= config["controls"]["project_api_cap_usd"]})
    result = {"status": "estimated_not_a_full_run_worst_case", "configuration": configuration(config),
              "measured_jev_synthetic_input_tokens": base_tokens, "target_met": measured["target_met"],
              "stages": stages, "distinct_text_union": len(union), "scenarios": scenarios,
              "limitations": ["Review token lengths and Luna envelope are estimates; only synthetic Jev billing is measured.",
                              "Development caches must be imported under unchanged label_config for union reuse savings.",
                              "Repeated transient failures or singleton repairs can exceed these estimates; the $10 ledger stops admission.",
                              "Confidence thresholds remain provisional; golden is never calibration data."]}
    replay_path = Path("cost/replay.json")
    if replay_path.exists():
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        if replay.get("status") == "ready" and replay.get("by_role_usd"):
            # Future development work excludes the 100 texts already paid for.
            variable = float(replay["by_role_usd"]["enrich"]) / 100 * (len(union) - 100)
            verification = float(replay["by_role_usd"]["verify"]) / 10 * (3 * config["verification"]["sample_size"])
            events = [json.loads(line) for line in Path("cost/pilot_calls.jsonl").read_text(encoding="utf-8").splitlines()]
            fixed = sum(event.get("cost_nanodollars", 0) for event in events
                        if event["role"] in {"group", "memo"} and event["outcome"] == "succeeded") / 1e9 * 3
            spent = Ledger(Path(config["controls"]["ledger_path"]), config["controls"]["project_api_cap_usd"]).totals()["spent_nanodollars"] / 1e9
            result["observed_pilot_mix_project_estimates"] = [
                {"case": case, "variable_cost_multiplier": factor,
                 "total_project_usd": spent + (variable + verification) * factor + fixed,
                 "assumptions": "Pilot enrichment and verifier usage per review extrapolated; three future group/memo runs; unchanged-config cache reuse. Not a guarantee."}
                for case, factor in [("base", 1), ("conservative", 1.5)]]
    atomic_json(output, result)
    return result


if __name__ == "__main__":
    print(json.dumps(project(), indent=2))
