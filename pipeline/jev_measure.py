"""One explicitly approved Jev prompt measurement; no pilot dispatch."""

import copy
import json
import tomllib
import uuid
from pathlib import Path
from typing import Any

from pipeline.calls import Calls
from pipeline.classify import jev_payload, parse_jev
from pipeline.enrich import export_state
from pipeline.labeler import atomic_csv
from pipeline.prepare import atomic_json
from pipeline.providers import HTTPTransport, keys_from_env
from pipeline.schema import canonical, configuration, digest
from pipeline.spend import Ledger, token_cost
from pipeline.state import State


def measurement_plan(config_path: Path, output: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    keys_from_env(Path(".env"))
    payload = jev_payload("Music will not play.", config)
    bound = len(canonical(payload).encode()) + config["controls"]["token_overhead_bound"]
    plan = {"step": "jev-v2-measurement", "maximum_calls": 1, "automatic_retries": 0,
            "provider": "typesafe", "model": payload["model"], "synthetic_text": "Music will not play.",
            "input_token_bound": bound, "target_billed_input_tokens": 1000,
            "worst_case_nanodollars": token_cost(bound, 0, config["planning_rates"], "typesafe"),
            "payload_sha256": digest(payload), "configuration": configuration(config),
            "status": "awaiting_explicit_yes"}
    atomic_json(output / "plan.json", plan)
    return plan


def run_measurement(config_path: Path, output: Path, approved_plan: Path, confirm_spend: bool) -> None:
    if not confirm_spend:
        raise ValueError("Measurement requires --confirm-spend after explicit yes")
    approved = json.loads(approved_plan.read_text(encoding="utf-8"))
    plan = measurement_plan(config_path, output)
    if approved != plan:
        raise ValueError("Measurement plan changed; obtain a new yes")
    config = copy.deepcopy(tomllib.loads(config_path.read_text(encoding="utf-8")))
    config["controls"].update(max_transient_attempts=1, invalid_output_retries=0,
                              run_api_cap_usd=plan["worst_case_nanodollars"] / 1e9)
    source_path = output / "synthetic.csv"
    if not source_path.exists():
        fields = ["review_id", "review_text", "review_rating", "review_likes", "app_version", "review_timestamp"]
        atomic_csv(source_path, fields, [dict(zip(fields, ["jev-v2-synthetic", plan["synthetic_text"], "1", "0", "", "2026-10-14"]))])
    state = State(output / "state.sqlite3", configuration(config))
    state.ingest(source_path, Path("data/manifest.json"))
    with state.connect() as db:
        if db.execute("SELECT 1 FROM calls LIMIT 1").fetchone():
            raise ValueError("Measurement already attempted; no automatic repeat")
    ledger = Ledger(Path(config["controls"]["ledger_path"]), config["controls"]["project_api_cap_usd"])
    calls = Calls(state, ledger, HTTPTransport(keys_from_env(Path(".env")), config["controls"]["request_timeout_seconds"]),
                  config, str(uuid.uuid4()), "initial")
    calls.max_calls = 1
    try:
        labels = calls.invoke("typesafe", jev_payload(plan["synthetic_text"], config), ["jev-v2-synthetic"],
                              "jev-v2-measurement", lambda response: parse_jev(response,
                              config["enrichment"]["confidence_threshold"],
                              config["enrichment"]["probability_margin_threshold"]), repair_output=False)
        with state.connect() as db:
            event = json.loads(db.execute("SELECT event FROM calls").fetchone()[0])
        tokens = event["response"]["usage"]["input_tokens"]
        atomic_json(output / "result.json", {"status": "succeeded", "labels": labels,
                    "model": event["model"], "billed_input_tokens": tokens, "target_met": tokens <= 1000,
                    "scope_distinct_texts": 77913,
                    "jev_scope_usd_at_synthetic_length": tokens * 77913 * config["planning_rates"]["jev_input_per_million"] / 1e6,
                    "projection_note": "Synthetic-length estimate; real review lengths and retries add cost."})
    finally:
        export_state(state, output, False, ledger)
