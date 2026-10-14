"""Restore validated saved stages without calls; retain uncertain leased work."""

from typing import Any

from pipeline.classify import parse_jev, parse_luna_batch
from pipeline.spend import Ledger, usage_cost
from pipeline.state import State


def recover(state: State, config: dict[str, Any], ledger: Ledger) -> dict[str, int]:
    restored = blocked = 0
    for item in state.expired_items():
        events = [event for event in state.events_for(item["source"]["review_id"])
                  if event["role"] == "enrich"]
        uncertain = False
        for event in events:
            _, status, _ = ledger.reservation(event["request_id"])
            if status == "reserved" and "response" not in event:
                uncertain = True
                continue
            response = event.get("response", {})
            usage = response.get("usage", {})
            inputs, outputs = usage.get("input_tokens"), usage.get("output_tokens")
            valid_usage = all(type(value) is int and value >= 0 for value in (inputs, outputs))
            if status == "reserved":
                if not valid_usage:
                    uncertain = True
                    continue
                actual = usage_cost(usage, config["planning_rates"], event["provider"])
                ledger.settle(event["request_id"], actual, "recovered_saved_usage")
            event["reservation_settled"] = True
            if event.get("error") == "dispatch_started_outcome_unresolved" and response:
                model = response.get("model")
                if not model or (event["provider"] == "typesafe" and model != config["models"]["jev"]):
                    raise ValueError("Recovery returned model mismatch")
                state.observed_model(event["provider"], model)
                event.update(model=model, input_tokens=inputs, output_tokens=outputs,
                             accounting="recovered_saved_usage",
                             service_tier=response.get("service_tier", "standard" if event["provider"] == "typesafe" else None))
            state.save_call(event)
        if uncertain:
            blocked += 1
            continue
        for event in events:
            candidate = event.get("error") == "dispatch_started_outcome_unresolved" and "response" in event
            if event["outcome"] != "succeeded" and not candidate:
                continue
            if event["label_config"] != state.label_config:
                raise ValueError("Saved recovery event configuration mismatch")
            stage = event["stage"]
            if state.stage_result(item["key"], stage) is not None:
                continue
            try:
                if stage == "jev":
                    result = parse_jev(event["response"], config["enrichment"]["confidence_threshold"], config["enrichment"].get("probability_margin_threshold", 0.15))
                else:
                    if event["service_tier"] not in {"default", "standard"}:
                        raise ValueError("Luna recovery tier requires rate reconciliation")
                    labels = state.stage_result(item["key"], "jev")
                    if labels is None:
                        raise ValueError("Luna recovery lacks saved Jev labels")
                    rid = item["source"]["review_id"]
                    batch = parse_luna_batch(event["response"], {rid: item["source"]},
                                            {rid: labels}, stage == "extract", state.label_config)
                    if rid not in batch["valid"]:
                        event.setdefault("invalid_review_ids", []).append(rid)
                        state.save_call(event)
                        continue
                    result = batch["valid"][rid]
            except (ValueError, KeyError, TypeError) as exc:
                if not candidate:
                    raise
                event.update(outcome="failed", error="Invalid output: " + str(exc))
                state.save_call(event)
                continue
            event.update(outcome="succeeded", error=None)
            state.save_call(event)
            state.stage_result(item["key"], stage, result)
        state.release(item)
        restored += 1
    state.recover_expired()
    return {"released_known_work": restored, "blocked_unknown_charge": blocked}
