"""Offline replay of real saved usage. No keys, providers or network calls."""

import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from pipeline.labeler import atomic_csv
from pipeline.prepare import atomic_json


def billed_items(event: dict[str, Any]) -> dict[str, int] | None:
    if type(event.get("input_tokens")) is not int or type(event.get("output_tokens")) is not int:
        return None
    total, output = event["input_tokens"], event["output_tokens"]
    if event["provider"] == "typesafe":
        return {"input": total, "output": output}
    detail = event.get("response", {}).get("usage", {}).get("input_tokens_details", {})
    cached, write = detail.get("cached_tokens", 0), detail.get("cache_write_tokens", 0)
    if any(type(value) is not int or value < 0 for value in (total, output, cached, write)) or cached + write > total:
        raise ValueError("Invalid or overlapping billing units")
    return {"input": total - cached - write, "cached_input": cached, "cache_write": write, "output": output}


def replay(cost_dir: Path, rates_path: Path | None = None) -> dict[str, Any]:
    rates_path = rates_path or cost_dir / "rates.csv"
    with rates_path.open(encoding="utf-8", newline="") as stream:
        rates = {(row["provider"], row["tier"], row["item"]): Decimal(row["price_per_million"]) / 1000000
                 for row in csv.DictReader(stream)}
    calls_path = cost_dir / "pilot_calls.jsonl"
    if not calls_path.exists():
        result = {"status": "awaiting_real_cold_warm_pilot", "api_spend_usd": None,
                  "measured_time_seconds": None, "local_compute_cost_usd": None,
                  "note": "No pilot measurements invented; preflight evidence is separate."}
        atomic_json(cost_dir / "replay.json", result)
        return result
    events = [json.loads(line) for line in calls_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(event.get("simulated") for event in events):
        raise ValueError("Simulated calls cannot be presented as measured pilot usage")
    amounts = defaultdict(Decimal)
    usage_rows, unresolved = [], []
    for event in events:
        items = billed_items(event)
        if items is None:
            unresolved.append(event["request_id"])
            continue
        for item, units in items.items():
            key = (event["provider"], event["service_tier"], item)
            if key not in rates:
                raise ValueError("Missing dated rate for actual billed tier/item: " + str(key))
            amount = Decimal(units) * rates[key]
            amounts[event["role"]] += amount
            usage_rows.append({"request_id": event["request_id"], "run_id": event["run_id"],
                               "provider": event["provider"], "model": event["model"], "tier": event["service_tier"],
                               "role": event["role"], "stage": event["stage"], "item": item,
                               "units": str(units), "unit": "tokens", "cost_usd": str(amount)})
    measurements = json.loads((cost_dir / "measurements.json").read_text(encoding="utf-8"))
    cold = measurements.get("cold", {})
    jev = [event for event in events if event["provider"] == "typesafe"]
    known_jev = [event for event in jev if type(event.get("input_tokens")) is int]
    mean = sum(event["input_tokens"] for event in known_jev) / len(known_jev) if known_jev else None
    distinct = cold.get("distinct_texts", 0)
    scope = json.loads((cost_dir / "scope.json").read_text()) if (cost_dir / "scope.json").exists() else {}
    jev_per_text = sum(event["input_tokens"] for event in known_jev) / distinct if distinct else None
    jev_rate = rates[("typesafe", "standard", "input")]
    scope_cost = Decimal(str(jev_per_text)) * scope["selected_distinct_texts"] * jev_rate if jev_per_text and scope else None
    completed = cold.get("status", "completed") == "completed" or measurements.get("memo_continuation", {}).get("status") == "completed"
    result = {"status": ("ready" if completed else "pilot_incomplete") if not unresolved else "usage_unresolved", "api_spend_usd": str(sum(amounts.values(), Decimal(0))),
              "by_role_usd": {key: str(value) for key, value in amounts.items()}, "unresolved_usage": unresolved,
              "measured_time_seconds": {kind: value.get("end_to_end_seconds") for kind, value in measurements.items() if isinstance(value, dict)},
              "local_compute_cost_usd": measurements.get("local_compute_cost_usd"),
              "jev_input_tokens_per_call": [{"request_id": event["request_id"], "input_tokens": event.get("input_tokens"),
                                              "outcome": event["outcome"]} for event in jev],
              "jev_mean_input_tokens_per_call": mean, "jev_billed_input_tokens_per_distinct_text": jev_per_text,
              "jev_100k_scope_projection_usd": str(scope_cost) if scope_cost is not None else None,
              "jev_trim_proposal_required": bool(scope_cost is not None and scope_cost > Decimal(4)),
              "scope": scope, "measurements": measurements,
              "accounting": "Calculated from reported usage and editable dated rates; receipts not reconciled."}
    cold_ids = {event["run_id"] for event in events if event.get("phase") == "initial"}
    cold_events = [event for event in events if event["run_id"] in cold_ids]
    role_costs = defaultdict(Decimal)
    for event in cold_events:
        items = billed_items(event)
        if items is not None:
            role_costs[event["role"]] += sum((Decimal(units) * rates[(event["provider"], event["service_tier"], item)]
                                              for item, units in items.items()), Decimal(0))
    fixed = role_costs["group"] + role_costs["memo"]
    variable = role_costs["enrich"] / distinct if distinct else None
    verified = cold.get("verified_reviews", 0)
    if not verified and (cost_dir / "verifier.json").exists():
        verified = len(json.loads((cost_dir / "verifier.json").read_text(encoding="utf-8")).get("predictions", {}))
    verify_each = role_costs["verify"] / verified if verified else None
    scenarios = []
    if variable is not None and verify_each is not None and scope:
        populations = [("100k sample with exact reuse", scope["selected_distinct_texts"]),
                       ("100k sample without exact reuse", scope["selected_review_ids"]),
                       ("full corpus with exact reuse", 484189), ("full corpus without exact reuse", 660609)]
        for name, work in populations:
            for conservative, factor in ((False, Decimal(1)), (True, Decimal("1.5"))):
                estimate = variable * work * factor + verify_each * 500 * factor + fixed
                model_seconds = (cold.get("enrichment_seconds", 0) * work / distinct
                                 + cold.get("verification_seconds", 0) * 500 / verified
                                 + cold.get("business_seconds", 0)) * (1.5 if conservative else 1)
                if any(key not in cold for key in ("enrichment_seconds", "verification_seconds", "business_seconds")):
                    model_seconds = None
                scenarios.append({"scope": name, "case": "conservative" if conservative else "base",
                                  "distinct_or_no_reuse_work": work, "api_spend_usd": str(estimate),
                                  "fixed_overhead_usd_counted_once": str(fixed), "verification_reviews": 500,
                                  "estimated_model_stage_seconds": model_seconds, "full_preparation_seconds": None,
                                  "exceeds_10_usd": estimate > 10,
                                  "assumptions": "Observed pilot mix; conservative variable retries/fallback/output uplift 50%; one worker. Full-corpus scenarios are comparison only."})
    result["scenarios"] = scenarios
    result["cost_per_1000_input_rows_usd"] = str(sum(amounts.values(), Decimal(0)) * 1000 / cold.get("input_rows", 100))
    result["cost_per_completed_record_usd"] = str(sum(amounts.values(), Decimal(0)) / cold["counts"]["completed"]) if cold.get("counts", {}).get("completed") else None
    result["throughput_input_rows_per_second"] = cold.get("input_rows", 100) / cold["end_to_end_seconds"] if cold.get("end_to_end_seconds") else None
    result["calls"] = {"total_attempts": len(events), "succeeded": sum(event["outcome"] == "succeeded" for event in events),
                       "failed": sum(event["outcome"] == "failed" for event in events),
                       "fallback_attempts": sum(event["stage"] == "fallback" for event in events),
                       "retry_attempts": sum(event.get("attempt", 1) > 1 for event in events),
                       "actual_models": sorted({event["model"] for event in events}),
                       "actual_tiers": sorted({str(event["service_tier"]) for event in events})}
    result["cold_exact_text_cache_hits"] = cold.get("counts", {}).get("completed", 0) - distinct
    result["warm_saved_completed_reuses"] = measurements.get("warm", {}).get("counts", {}).get("completed")
    preflight_path = Path("artifacts/preflight/calls.jsonl")
    preflight_cost = Decimal(0)
    if preflight_path.exists():
        for event in [json.loads(line) for line in preflight_path.read_text().splitlines()]:
            items = billed_items(event)
            if items is not None:
                preflight_cost += sum((Decimal(units) * rates[(event["provider"], event["service_tier"], item)]
                                       for item, units in items.items()), Decimal(0))
    result["preflight_api_spend_usd_separate"] = str(preflight_cost)
    measurement_cost = Decimal(0)
    measurement_path = Path("artifacts/jev-v2-test/calls.jsonl")
    if measurement_path.exists():
        for event in [json.loads(line) for line in measurement_path.read_text(encoding="utf-8").splitlines()]:
            items = billed_items(event)
            if items is not None:
                measurement_cost += sum((Decimal(units) * rates[(event["provider"], event["service_tier"], item)]
                                          for item, units in items.items()), Decimal(0))
    result["jev_prompt_measurement_usd_separate"] = str(measurement_cost)
    result["project_api_spend_accounted_usd"] = str(preflight_cost + measurement_cost + sum(amounts.values(), Decimal(0)))
    fields = ["request_id", "run_id", "provider", "model", "tier", "role", "stage", "item", "units", "unit", "cost_usd"]
    atomic_csv(cost_dir / "usage.csv", fields, usage_rows)
    atomic_json(cost_dir / "replay.json", result)
    write_report(cost_dir, result)
    return result


def write_report(cost_dir: Path, result: dict[str, Any]) -> None:
    from pipeline.enrich import write_jsonl

    # Keep a readable report and machine-readable counterpart; offline replay never calls a model.
    lines = ["# Measured 100-review cost/runtime report", "",
             "Source: saved pilot calls, usage, measurements and dated editable rates. Provider receipts are not reconciled.",
             "", f"Status: {result['status']}", f"Pilot API spend: ${result['api_spend_usd']}",
             f"Measured cold/warm wall seconds: {result['measured_time_seconds']}",
             f"Local compute cost: {result['local_compute_cost_usd']} (unknown is not zero).", "",
             f"Attempts, failures, retries, fallbacks, models and tiers: {result['calls']}",
             f"Cold exact-text cache hits: {result['cold_exact_text_cache_hits']}; warm completed-result reuse: {result['warm_saved_completed_reuses']}",
             f"Provider preflight spend (separate): ${result['preflight_api_spend_usd_separate']}; accounted project subtotal: ${result['project_api_spend_accounted_usd']}", "",
             f"Measured Jev mean billed input tokens per call: {result['jev_mean_input_tokens_per_call']}",
             f"Measured Jev billed input tokens per distinct text, including attempts: {result['jev_billed_input_tokens_per_distinct_text']}",
             f"Projected Jev cost for saved 100k scope: ${result['jev_100k_scope_projection_usd']}",
             f"Trimmed Jev prompt proposal required above $4: {result['jev_trim_proposal_required']}", "",
             f"Per 1,000 input rows: ${result['cost_per_1000_input_rows_usd']}",
             f"Per completed record: ${result['cost_per_completed_record_usd']}",
             f"Measured input throughput: {result['throughput_input_rows_per_second']} rows/s", "",
             "Every Jev call's measured input token count is in jev_usage.jsonl. Charged categories map to request IDs in usage.csv.",
             "Doubling API rates doubles replayed API spend; measured time/local compute remain unchanged.", "",
             "## Scope and projections", "", "These are estimates, not full-run measurements. Fixed grouping/memo overhead is counted once."]
    for scenario in result["scenarios"]:
        lines.append(f"- {scenario['scope']} / {scenario['case']}: ${scenario['api_spend_usd']}; estimated model-stage seconds {scenario['estimated_model_stage_seconds']}; exceeds $10: {scenario['exceeds_10_usd']}.")
    lines.extend(["", "Full-corpus scenarios are comparison only. Approved target remains the saved 100k prefix plus forced golden IDs.",
                  "Projection sensitivity: conservative variable work is 50% higher; it is not an extra measured experiment.",
                  "No unmeasured prompt-cache discount, concurrency speedup or Batch/Flex discount is assumed.",
                  "Missing usage request IDs: " + str(result["unresolved_usage"]), "",
                  "Inspect measurements.json for statuses, unique texts, workers, batches and stage timing; verifier.json for blinded disagreements; business.json and claims.csv for grounded memo evidence."])
    path = cost_dir / "report.md"
    import os
    import tempfile

    descriptor, temporary = tempfile.mkstemp(dir=cost_dir, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines) + "\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    write_jsonl(cost_dir / "jev_usage.jsonl", result["jev_input_tokens_per_call"])
