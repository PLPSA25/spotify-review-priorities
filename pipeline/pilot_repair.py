"""Separately approved memo-only continuation; enrichment is never dispatched."""

import json
import time
import tomllib
import uuid
from pathlib import Path
from typing import Any

from pipeline.calls import Calls
from pipeline.enrich import export_state, write_jsonl
from pipeline.labeler import atomic_csv
from pipeline.pilot_stages import business_stages, verify_pilot
from pipeline.prepare import atomic_json
from pipeline.providers import HTTPTransport, keys_from_env
from pipeline.schema import canonical, configuration, digest
from pipeline.spend import Ledger, token_cost
from pipeline.state import State


class Captured(Exception):
    pass


def repair_plan(config_path: Path, directory: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text())
    state = State(directory / "state.sqlite3", configuration(config))
    if state.counts() != {"completed": 100}:
        raise ValueError("Memo repair requires all 100 reviews already completed")
    captured = {}

    class CaptureCalls:
        def invoke(self, provider, payload, ids, stage, parse, **kwargs):
            if kwargs.get("role") != "memo":
                raise ValueError("Repair must reuse all existing upstream artifacts")
            captured.update(payload=payload, ids=ids, stage=stage)
            raise Captured()

    try:
        business_stages(state, CaptureCalls(), config)
    except Captured:
        pass
    if not captured:
        raise ValueError("Memo already saved; no paid repair needed")
    payload = captured["payload"]
    bound = len(canonical(payload).encode()) + config["controls"]["token_overhead_bound"]
    rates = dict(config["planning_rates"])
    rates["luna_input_per_million"] = max(rates["luna_input_per_million"], rates["luna_cache_write_per_million"])
    plan = {"step": "pilot_memo_v2_only", "provider": "openai", "model": payload["model"],
            "maximum_calls": 2, "initial_calls": 1, "invalid_output_repairs": 1, "transient_retries": 0,
            "input_token_bound_per_call": bound, "output_token_cap_per_call": payload["max_output_tokens"],
            "payload_sha256": digest(payload), "configuration": state.label_config,
            "worst_case_nanodollars": 2 * token_cost(bound, payload["max_output_tokens"], rates, "openai"),
            "enrichment_and_verifier_and_group_calls": 0, "warm_replay_calls": 0,
            "status": "awaiting_explicit_yes"}
    # Calls adds a validation error to input on repair; reserve a bounded allowance.
    plan["worst_case_nanodollars"] += token_cost(2048, 0, rates, "openai")
    atomic_json(directory / "memo_repair_plan.json", plan)
    return plan


def run_repair(config_path: Path, directory: Path, approved_path: Path, confirmed: bool) -> None:
    if not confirmed:
        raise ValueError("Memo repair requires --confirm-spend after explicit yes")
    approved = json.loads(approved_path.read_text())
    current = repair_plan(config_path, directory)
    if approved != current:
        raise ValueError("Memo repair plan changed; obtain a new yes")
    config = tomllib.loads(config_path.read_text())
    config["controls"].update(max_transient_attempts=1, invalid_output_retries=1,
                              run_api_cap_usd=current["worst_case_nanodollars"] / 1e9)
    state = State(directory / "state.sqlite3", configuration(config))
    with state.connect() as db:
        if any(json.loads(row[0])["stage"] == "pilot-memo-v2" for row in db.execute("SELECT event FROM calls")):
            raise ValueError("Memo repair already attempted; no automatic repeat")
    ledger = Ledger(Path(config["controls"]["ledger_path"]), config["controls"]["project_api_cap_usd"])
    calls = Calls(state, ledger, HTTPTransport(keys_from_env(Path(".env")), config["controls"]["request_timeout_seconds"]),
                  config, str(uuid.uuid4()), "resume")
    calls.max_calls = 2
    measurements = json.loads((directory / "measurements.json").read_text())
    started = time.perf_counter()
    try:
        business = business_stages(state, calls, config)
        atomic_json(directory / "business.json", business)
        for name, fields in (("membership", ["issue_id", "review_id"]),
                             ("ranking", ["rank", "issue_id", "complaint_count", "severity_sum", "mean_severity", "priority_score"]),
                             ("claims", ["claim_id", "issue_id", "metric", "value"])):
            atomic_csv(directory / (name + ".csv"), fields, business[name])
        measurements["memo_continuation"] = {"status": "completed", "end_to_end_seconds": time.perf_counter() - started,
                                             "original_cold_failure_preserved": True}

        class NoDispatch:
            def request(self, provider, payload):
                raise AssertionError("Warm replay cannot dispatch")

        warm_start = time.perf_counter()
        warm_calls = Calls(state, ledger, NoDispatch(), config, str(uuid.uuid4()), "resume")
        verify_pilot(state, warm_calls, config)
        business_stages(state, warm_calls, config)
        measurements["warm"] = {"status": "completed", "new_enrich_calls": 0, "new_downstream_calls": 0,
                                 "incremental_api_spend_usd": "0", "counts": state.counts(),
                                 "end_to_end_seconds": time.perf_counter() - warm_start}
    except BaseException as exc:
        measurements["memo_continuation"] = {"status": "failed", "error": type(exc).__name__ + ": " + str(exc)}
        raise
    finally:
        atomic_json(directory / "measurements.json", measurements)
        export_state(state, directory, False, ledger)
        with state.connect() as db:
            events = [json.loads(row[0]) for row in db.execute("SELECT event FROM calls ORDER BY rowid")]
        write_jsonl(directory / "pilot_calls.jsonl", events)
