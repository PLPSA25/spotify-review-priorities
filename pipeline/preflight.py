"""Reviewable two-call key/model preflight. Planning never contacts providers."""

import copy
import json
import tomllib
import uuid
from pathlib import Path
from typing import Any

from pipeline.calls import Calls
from pipeline.classify import jev_payload, luna_payload, parse_jev, parse_luna
from pipeline.enrich import export_state, validate_settings
from pipeline.labeler import atomic_csv
from pipeline.prepare import atomic_json
from pipeline.providers import HTTPTransport, keys_from_env
from pipeline.schema import canonical, configuration, digest
from pipeline.spend import Ledger, token_cost
from pipeline.state import State


def preflight_plan(config_path: Path, output: Path, check_keys: bool = True) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    validate_settings(config)
    if check_keys:
        keys_from_env(Path(".env"))  # presence only; no values returned, printed or saved
    source = {"review_id": "preflight-synthetic", "review_text": "Music will not play.",
              "source_sha256": "computed_at_execution"}
    jev = jev_payload(source["review_text"], config)
    luna = luna_payload(source, {}, config, False)
    luna["max_output_tokens"] = config["pilot"]["preflight_output_token_cap"]
    plans = []
    for provider, payload in (("typesafe", jev), ("openai", luna)):
        bound = len(canonical(payload).encode()) + config["controls"]["token_overhead_bound"]
        rates = dict(config["planning_rates"])
        if provider == "openai":
            rates["luna_input_per_million"] = max(rates["luna_input_per_million"], rates["luna_cache_write_per_million"])
        cost = token_cost(bound, 0 if provider == "typesafe" else payload["max_output_tokens"], rates, provider)
        plans.append({"provider": provider, "model": payload["model"], "calls": 1,
                      "input_token_bound": bound, "output_token_cap": payload.get("max_output_tokens", 0),
                      "worst_case_nanodollars": cost, "payload_sha256": digest(payload)})
    plan = {"step": "provider_preflight", "maximum_calls": 2, "automatic_retries": 0,
            "calls": plans, "worst_case_nanodollars": sum(item["worst_case_nanodollars"] for item in plans),
            "credentials_present": check_keys, "configuration": configuration(config),
            "status": "awaiting_explicit_yes", "synthetic_text": source["review_text"]}
    atomic_json(output / "plan.json", plan)
    return plan


def run_preflight(config_path: Path, output: Path, confirm_spend: bool, approved_plan: Path) -> None:
    if not confirm_spend:
        raise ValueError("Preflight requires --confirm-spend after explicit yes to the saved plan")
    approved = json.loads(approved_plan.read_text(encoding="utf-8"))
    actual = preflight_plan(config_path, output)
    if approved != actual:
        raise ValueError("Preflight plan changed; obtain a new yes before calling")
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    config = copy.deepcopy(config)
    config["controls"].update(max_transient_attempts=1, invalid_output_retries=0)
    config["models"]["output_token_cap"] = config["pilot"]["preflight_output_token_cap"]
    source_path = output / "synthetic.csv"
    if not source_path.exists():
        fields = ["review_id", "review_text", "review_rating", "review_likes", "app_version", "review_timestamp"]
        row = dict(zip(fields, ["preflight-synthetic", actual["synthetic_text"], "1", "0", "", "2026-10-13"]))
        atomic_csv(source_path, fields, [row])
    state = State(output / "state.sqlite3", configuration(config))
    state.ingest(source_path, Path("data/manifest.json"))
    with state.connect() as db:
        prior = [json.loads(row[0]) for row in db.execute("SELECT event FROM calls ORDER BY rowid")]
        if len(prior) > 1 or (prior and prior[0]["stage"] != "preflight-jev"):
            raise ValueError("Preflight already attempted; review its evidence before authorizing another step")
        source = json.loads(db.execute("SELECT source FROM reviews").fetchone()[0])
    ledger = Ledger(Path(config["controls"]["ledger_path"]), config["controls"]["project_api_cap_usd"])
    run_id = str(uuid.uuid4())
    config["controls"]["run_api_cap_usd"] = actual["worst_case_nanodollars"] / 1_000_000_000
    calls = Calls(state, ledger, HTTPTransport(keys_from_env(Path(".env")), config["controls"]["request_timeout_seconds"]),
                  config, run_id, "initial")
    try:
        if prior:
            previous = prior[0]
            if previous.get("response", {}).get("model") != config["models"]["jev"]:
                raise ValueError("Saved Jev response does not establish approved pinned model")
            parse_jev(previous["response"], config["enrichment"]["confidence_threshold"])
            atomic_json(output / "offline_revalidation.json", {
                "original_request_id": previous["request_id"], "status": "valid_after_rounding_fix",
                "new_provider_calls": 0, "original_failure_preserved": True})
        else:
            calls.invoke("typesafe", jev_payload(source["review_text"], config), [source["review_id"]], "preflight-jev",
                         lambda reply: parse_jev(reply, config["enrichment"]["confidence_threshold"]), repair_output=False)
        calls.invoke("openai", luna_payload(source, {}, config, False), [source["review_id"]], "preflight-luna",
                     lambda reply: parse_luna(reply, source, {}, False, state.label_config),
                     role="verify", repair_output=False)
        with state.connect() as db:
            events = [json.loads(row[0]) for row in db.execute("SELECT event FROM calls ORDER BY rowid")]
        atomic_json(output / "result.json", {"status": "succeeded", "models": [event["model"] for event in events],
                    "usage": [event["response"]["usage"] for event in events],
                    "limit_headers": [event["response"].get("_headers", {}) for event in events],
                    "note": "One success does not establish sustained capacity; console/headers govern limits."})
    finally:
        export_state(state, output, False, ledger)
