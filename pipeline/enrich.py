"""Explicit enrichment command; mocks and live data are kept in separate stores."""

import json
import math
import os
import tempfile
import tomllib
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from pipeline.batching import enrich_batch
from pipeline.calls import Calls
from pipeline.classify import jev_payload, luna_payload
from pipeline.deterministic import run_deterministic
from pipeline.failure_policy import failure_window
from pipeline.prepare import atomic_json
from pipeline.providers import HTTPTransport, MockTransport, keys_from_env
from pipeline.recovery import recover
from pipeline.schema import canonical, configuration, record_schema
from pipeline.spend import Ledger, fallback_quota, token_cost
from pipeline.state import State


def write_jsonl(path: Path, values) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            for value in values:
                stream.write(canonical(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_settings(config: dict[str, Any]) -> None:
    models, controls = config["models"], config["controls"]
    policy = config['enrichment'].get('needs_review_policy')
    if policy is not None and (policy != 'persistent-context-reasons-v1' or config['enrichment'].get('luna_prompt') != 'luna-enrich-v2.txt'):
        raise ValueError('Unsupported final reason policy/prompt combination')
    if models["jev"] != "jev-1.13.0" or models["luna"] != "gpt-6-luna":
        raise ValueError("Model is outside the approved Jev/Luna allowlist")
    if models["effort"] not in {"none", "low"}:
        raise ValueError("Only none/low effort is allowed; low needs evaluation justification")
    if type(models["output_token_cap"]) is not int or not 1 <= models["output_token_cap"] <= 128000:
        raise ValueError("Invalid output-token cap")
    positive = ("max_workers", "max_transient_attempts", "jev_requests_per_second",
                "jev_input_tokens_per_second", "token_overhead_bound")
    if any(type(controls[key]) is not int or controls[key] < 1 for key in positive):
        raise ValueError("Worker/retry/rate/token controls must be positive integers")
    if controls["invalid_output_retries"] != 1:
        raise ValueError("Invalid output must receive exactly one repair attempt")
    threshold = config["enrichment"]["confidence_threshold"]
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Confidence threshold must be finite 0..1")
    fallback_quota(1, controls["fallback_fraction"])
    batch_size = config["enrichment"]["batch_size"]
    if type(batch_size) is not int or not 1 <= batch_size <= 50:
        raise ValueError("Luna batch_size must be an integer 1..50")


def export_state(state: State, output: Path, simulated: bool, ledger: Ledger) -> None:
    import json

    with state.connect() as db:
        write_jsonl(output / "enriched.jsonl", (json.loads(row[0]) for row in db.execute(
            "SELECT result FROM reviews WHERE status='completed' ORDER BY review_id")))
        write_jsonl(output / "quarantine.jsonl", (
            {"review_id": row["review_id"], "source_sha256": json.loads(row["source"])["source_sha256"],
             "status": "quarantined", "reason": row["reason"], "attempt_count": row["attempts"]}
            for row in db.execute("SELECT * FROM reviews WHERE status='quarantined' ORDER BY review_id")))
        write_jsonl(output / "calls.jsonl", (json.loads(row[0]) for row in db.execute(
            "SELECT event FROM calls ORDER BY rowid")))
    atomic_json(output / "summary.json", {"simulated": simulated, "label_config": state.label_config,
                                           "counts": state.counts(), "ledger": ledger.totals(),
                                           "warning": "Not a grading export; pending work remains internal."})


def projected_bound(state: State, config: dict[str, Any]) -> int:
    """All pending work with worst-case extraction/fallback and bounded attempts."""
    import json

    with state.connect() as db:
        rows = db.execute("SELECT r.source FROM work w JOIN reviews r ON r.review_id=w.origin_id "
                          "WHERE w.status='pending'").fetchall()
    total = 0
    for row in rows:
        source = json.loads(row[0])
        for provider, payload in (("typesafe", jev_payload(source["review_text"], config)),
                                  ("openai", luna_payload(source, {}, config, False))):
            tokens = len(canonical(payload).encode()) + config["controls"]["token_overhead_bound"]
            output = 0 if provider == "typesafe" else config["models"]["output_token_cap"]
            rates = dict(config["planning_rates"])
            rates["luna_input_per_million"] = max(rates["luna_input_per_million"],
                                                  rates["luna_cache_write_per_million"])
            attempts = config["controls"]["max_transient_attempts"] + config["controls"]["invalid_output_retries"]
            total += attempts * token_cost(tokens, output, rates, provider)
    return total


def run_enrichment(source: Path, output: Path, config_path: Path, manifest: Path,
                   simulated: bool, confirm_spend: bool, stop_after: int | None = None) -> None:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    validate_settings(config)
    if not simulated and not confirm_spend:
        raise ValueError("Paid execution requires --confirm-spend and interactive confirmation")
    if simulated and "mock" not in str(output).lower():
        raise ValueError("Simulated output directory must contain 'mock' to separate evidence")
    full_name = json.loads(manifest.read_text(encoding="utf-8"))["assignment_scope"]["final_input"]
    if source.name == full_name:
        raise ValueError("Full-source enrichment needs Phase 6's saved 100k permutation; use development CSVs now")
    state = State(output / "state.sqlite3", configuration(config, simulated), require_reasons=record_schema(config)=='record-v2')
    state.ingest(source, manifest)
    with state.connect() as db:
        phase = "resume" if db.execute("SELECT COUNT(*) FROM calls").fetchone()[0] else "initial"
        total = db.execute("SELECT COUNT(*) FROM work").fetchone()[0]
    if config["models"]["allow_batch"] or config["models"]["allow_flex"]:
        raise ValueError("Batch/Flex are not enabled in the Phase 3 synchronous adapter")
    if config["models"]["service_tier"] != "default":
        raise ValueError("Phase 3 requires explicit standard/default tier")
    controls = config["controls"]
    if type(controls["max_workers"]) is not int or controls["max_workers"] < 1:
        raise ValueError("max_workers must be positive")
    if stop_after is not None and (stop_after < 1 or controls["max_workers"] != 1):
        raise ValueError("Recorded stop-after requires a positive count and one worker")
    ledger_path = output / "mock-spend.sqlite3" if simulated else Path(controls["ledger_path"])
    ledger = Ledger(ledger_path, controls["project_api_cap_usd"])
    recovery = recover(state, config, ledger)
    if recovery["blocked_unknown_charge"]:
        raise ValueError("Uncertain in-flight work requires charge reconciliation before resuming")
    if state.leased_count():
        raise ValueError("Work is still leased; wait for lease expiry, then reconcile/resume")
    if simulated:
        transport = MockTransport()
    else:
        projected = projected_bound(state, config) / 1_000_000_000
        print(f"Estimated conservative admission envelope: ${projected:.6f}; project cap $"
              f"{controls['project_api_cap_usd']:.2f}. Not a measured bill.")
        if input("Type CONFIRM SPEND to admit paid work: ") != "CONFIRM SPEND":
            raise ValueError("Spending not confirmed; no paid calls made")
        transport = HTTPTransport(keys_from_env(Path(".env")), controls["request_timeout_seconds"])
    run_id = str(uuid.uuid4())
    calls = Calls(state, ledger, transport, config, run_id, phase, simulated)
    quota = fallback_quota(total, controls["fallback_fraction"])
    state.failure_window = failure_window(config)
    calls.fallback_scope = str(state.path.resolve()) + ":" + state.label_config

    def worker() -> int:
        completed = 0
        while stop_after is None or completed < stop_after:
            capacity = config["enrichment"]["batch_size"]
            if stop_after is not None:
                capacity = min(capacity, stop_after - completed)
            items = []
            for _ in range(capacity):
                item = state.claim(controls["lease_seconds"])
                if item is None:
                    break
                items.append(item)
            if not items:
                break
            try:
                enrich_batch(state, calls, items, config, quota)
            except BaseException:
                calls.stop.set()
                raise
            completed += len(items)
        return completed

    try:
        if config['enrichment'].get('fallback_selection_policy') == 'lowest-confidence-v1':
            selection = run_deterministic(state,calls,config,stop_after)
            if selection is not None:
                atomic_json(output/'routing-selection.json',selection)
        else:
            with ThreadPoolExecutor(max_workers=controls["max_workers"]) as pool:
                results = [pool.submit(worker) for _ in range(controls["max_workers"])]
                for result in results:
                    result.result()
    finally:
        if stop_after is not None and phase == "initial":
            state.checkpoint(output / "checkpoint_before.json")
        else:
            state.checkpoint(output / "checkpoint_after.json")
        export_state(state, output, simulated, ledger)
    print(f"{'SIMULATED' if simulated else 'Live'} enrichment states: {state.counts()}")
