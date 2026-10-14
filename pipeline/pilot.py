"""Explicit cold pilot, followed by a zero-call warm replay under unchanged configuration."""

import json
import time
import tomllib
import uuid
from pathlib import Path
from typing import Any

from pipeline.batching import enrich_batch
from pipeline.calls import Calls
from pipeline.classify import jev_payload, luna_payload
from pipeline.enrich import export_state, validate_settings, write_jsonl
from pipeline.labeler import atomic_csv
from pipeline.pilot_stages import business_stages, verify_pilot
from pipeline.prepare import atomic_json, course_helper
from pipeline.providers import HTTPTransport, keys_from_env
from pipeline.schema import canonical, configuration
from pipeline.spend import Ledger, fallback_quota, token_cost
from pipeline.state import State


def pilot_plan(config_path: Path, output: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    validate_settings(config)
    helper = course_helper(Path("data/check_submission.py"))
    source = Path("data/cost_100.csv")
    manifest = json.loads(Path("data/manifest.json").read_text())
    if helper.sha(source) != manifest["files"][source.name]["sha256"]:
        raise ValueError("Pilot input checksum mismatch")
    rows = list(helper.csv_rows(source))
    unique = {row["review_text"]: row for row in rows}
    d = len(unique)
    rates = dict(config["planning_rates"])
    rates["luna_input_per_million"] = max(rates["luna_input_per_million"], rates["luna_cache_write_per_million"])
    total = 0
    for row in unique.values():
        for provider, payload in (("typesafe", jev_payload(row["review_text"], config)),
                                  ("openai", luna_payload(row, {}, config, False))):
            bound = len(canonical(payload).encode()) + config["controls"]["token_overhead_bound"]
            cost = token_cost(bound, 0 if provider == "typesafe" else config["enrichment"]["luna_output_tokens_per_review"], rates, provider)
            # Conservative: singleton initial + singleton repair, each up to 3 transient attempts.
            total += cost * (config["pilot"]["transient_attempts"] + 1 if provider == "typesafe" else 2 * config["pilot"]["transient_attempts"])
    verify_n = min(config["pilot"]["verification_sample_size"], len(rows))
    # Explicit fixed-role upper envelopes; include schema, rubric, all claim rows and bounded evidence.
    role_bounds = {"verify": (20000, verify_n * 200), "group": (20000, config["pilot"]["group_output_token_cap"]),
                   "memo": (24000, config["pilot"]["memo_output_token_cap"])}
    for inputs, outputs in role_bounds.values():
        total += token_cost(inputs, outputs, rates, "openai") * (config["pilot"]["transient_attempts"] + 1)
    verify_repairs = verify_n * config["pilot"]["transient_attempts"]
    total += verify_repairs * token_cost(10000, 200, rates, "openai")
    long = sum(len(text) > config["enrichment"]["short_review_chars"] for text in unique)
    fallback = fallback_quota(d, config["controls"]["fallback_fraction"])
    batch = config["enrichment"]["batch_size"]
    # Batches form per queue window and may split on token bounds: safe first-pass upper.
    expected_luna_max = long + min(fallback, d - long)
    maximum = d * (config["pilot"]["transient_attempts"] + 1) + d * 2 * config["pilot"]["transient_attempts"] + 3 * (config["pilot"]["transient_attempts"] + 1) + verify_repairs
    plan = {"step": "cold_cost_100_pilot", "input_sha256": helper.sha(source), "input_rows": len(rows),
            "distinct_texts": d, "configuration": configuration(config), "worker_count": 1,
            "expected_initial_calls_upper": d + expected_luna_max + 3,
            "calls": {"jev_initial": d, "luna_enrich_initial_upper": expected_luna_max,
                      "verify_initial": 1, "group_initial": 1, "memo_initial": 1,
                      "maximum_including_repairs_and_transient_retries": maximum},
            "verification_reviews": verify_n, "batch_size": batch,
            "transient_attempts": config["pilot"]["transient_attempts"],
            "worst_case_nanodollars": total, "approval_status": "awaiting_explicit_yes",
            "warm_run": "Offline reuse; stop rather than dispatch any new call."}
    atomic_json(output / "pilot_plan.json", plan)
    return plan


def run_pilot(config_path: Path, cost_dir: Path, approved_path: Path, confirmed: bool) -> None:
    if not confirmed:
        raise ValueError("Paid pilot requires explicit yes and --confirm-spend")
    approved = json.loads(approved_path.read_text(encoding="utf-8"))
    current = pilot_plan(config_path, cost_dir)
    if approved != current:
        raise ValueError("Pilot plan changed; obtain a new yes")
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config["controls"]["max_workers"] != 1:
        raise ValueError("Cold pilot must use one worker")
    cap = current["worst_case_nanodollars"] / 1e9
    if cap > config["controls"]["pilot_api_cap_usd"]:
        raise ValueError("Worst-case pilot projection exceeds configured pilot cap")
    state = State(cost_dir / "state.sqlite3", configuration(config))
    with state.connect() as db:
        if db.execute("SELECT COUNT(*) FROM calls").fetchone()[0]:
            raise ValueError("Cold pilot already attempted; review before approving resume/another experiment")
    ledger = Ledger(Path(config["controls"]["ledger_path"]), config["controls"]["project_api_cap_usd"])
    transport = HTTPTransport(keys_from_env(Path(".env")), config["controls"]["request_timeout_seconds"])
    measurements: dict[str, Any] = {"local_compute_cost_usd": None}
    run_id = str(uuid.uuid4())
    config["controls"]["run_api_cap_usd"] = cap
    config["controls"]["max_transient_attempts"] = config["pilot"]["transient_attempts"]
    calls = Calls(state, ledger, transport, config, run_id, "initial")
    calls.max_calls = current["calls"]["maximum_including_repairs_and_transient_retries"]
    started = time.perf_counter()
    status, error = "completed", None
    try:
        prepare_start = time.perf_counter()
        state.ingest(Path("data/cost_100.csv"), Path("data/manifest.json"))
        preparation_seconds = time.perf_counter() - prepare_start
        classify_start = time.perf_counter()
        quota = fallback_quota(current["distinct_texts"], config["controls"]["fallback_fraction"])
        while True:
            items = []
            for _ in range(config["enrichment"]["batch_size"]):
                item = state.claim(config["controls"]["lease_seconds"])
                if item is None:
                    break
                items.append(item)
            if not items:
                break
            enrich_batch(state, calls, items, config, quota)
            print(f"Saved pilot progress: {state.counts()}", flush=True)
        enrichment_seconds = time.perf_counter() - classify_start
        if state.counts().get("completed", 0) != 100:
            raise ValueError("Pilot enrichment incomplete; fix before scaling")
        verify_start = time.perf_counter()
        verification = verify_pilot(state, calls, config)
        verification_seconds = time.perf_counter() - verify_start
        atomic_json(cost_dir / "verifier.json", verification)
        if not verification["complete"]:
            raise ValueError("Pilot verifier incomplete; inspect before scaling")
        business_start = time.perf_counter()
        business = business_stages(state, calls, config)
        business_seconds = time.perf_counter() - business_start
        atomic_json(cost_dir / "business.json", business)
        for name, fields in (("membership", ["issue_id", "review_id"]),
                             ("ranking", ["rank", "issue_id", "complaint_count", "severity_sum", "mean_severity", "priority_score"]),
                             ("claims", ["claim_id", "issue_id", "metric", "value"])):
            atomic_csv(cost_dir / (name + ".csv"), fields, business[name])
        measurements["cold"] = {"status": "completed", "input_rows": 100, "distinct_texts": current["distinct_texts"],
                                 "input_sha256": current["input_sha256"], "counts": state.counts(),
                                 "preparation_seconds": preparation_seconds, "enrichment_seconds": enrichment_seconds,
                                 "verification_seconds": verification_seconds, "business_seconds": business_seconds,
                                 "end_to_end_seconds": time.perf_counter() - started, "run_id": run_id,
                                 "verified_reviews": len(verification["predictions"]), "workers": 1, "batch_size": current["batch_size"]}
        warm_start = time.perf_counter()

        class NoDispatch:
            def request(self, provider, payload):
                raise AssertionError("Warm pilot cannot dispatch any model request")

        warm_calls = Calls(state, ledger, NoDispatch(), config, str(uuid.uuid4()), "resume")
        state.ingest(Path("data/cost_100.csv"), Path("data/manifest.json"))
        if state.claim(config["controls"]["lease_seconds"]) is not None:
            raise ValueError("Warm run unexpectedly has pending enrichment")
        verify_pilot(state, warm_calls, config)
        business_stages(state, warm_calls, config)
        measurements["warm"] = {"status": "completed", "new_enrich_calls": 0, "new_downstream_calls": 0,
                                 "incremental_api_spend_usd": "0", "counts": state.counts(),
                                 "end_to_end_seconds": time.perf_counter() - warm_start}
    except BaseException as exc:
        status, error = "failed", type(exc).__name__ + ": " + str(exc)
        measurements.setdefault("cold", {"status": status, "error": error, "input_rows": 100,
                                          "distinct_texts": current["distinct_texts"], "counts": state.counts(),
                                          "end_to_end_seconds": time.perf_counter() - started, "run_id": run_id})
        raise
    finally:
        atomic_json(cost_dir / "measurements.json", measurements)
        export_state(state, cost_dir, False, ledger)
        with state.connect() as db:
            records = []
            for row in db.execute("SELECT * FROM reviews ORDER BY review_id"):
                if row["result"]:
                    records.append(json.loads(row["result"]))
                else:
                    source = json.loads(row["source"])
                    records.append({"review_id": row["review_id"], "source_sha256": source["source_sha256"],
                                    "status": "quarantined", "reason": row["reason"] or "pilot_not_completed"})
            events = [json.loads(row[0]) for row in db.execute("SELECT event FROM calls ORDER BY rowid")]
        write_jsonl(cost_dir / "pilot_records.jsonl", records)
        write_jsonl(cost_dir / "pilot_calls.jsonl", events)
    print(f"Pilot {status}; cold/warm evidence saved in {cost_dir}. {error or ''}")
