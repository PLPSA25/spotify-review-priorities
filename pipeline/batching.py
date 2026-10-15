"""Multi-review synchronous Luna requests with per-ID salvage and isolated repairs."""

from typing import Any

from pipeline.calls import Calls, InvalidOutput
from pipeline.classify import (
    deterministic_entities,
    jev_payload,
    luna_batch_payload,
    parse_jev,
    parse_luna_batch,
)
from pipeline.providers import ProviderError
from pipeline.schema import canonical, record_schema
from pipeline.spend import SpendStop
from pipeline.state import ConfigMismatch, State


def pack(items: list[dict[str, Any]], labels: dict[str, dict[str, Any]], config: dict[str, Any],
         extraction: bool) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    routing = config["enrichment"]
    for item in items:
        candidate = current + [item]
        fits_count = len(candidate) <= min(50, routing["batch_size"])
        fits_output = len(candidate) * routing["luna_output_tokens_per_review"] <= config["models"]["output_token_cap"]
        fits_input = False
        if fits_count and fits_output:
            payload = luna_batch_payload(candidate, labels, config, extraction)
            fits_input = len(canonical(payload).encode()) + config["controls"]["token_overhead_bound"] <= routing["luna_input_token_bound"]
        if not (fits_count and fits_output and fits_input):
            if not current:
                raise SpendStop("One review exceeds the configured Luna token envelope")
            batches.append(current)
            current = [item]
            payload = luna_batch_payload(current, labels, config, extraction)
            if len(canonical(payload).encode()) + config["controls"]["token_overhead_bound"] > routing["luna_input_token_bound"]:
                raise SpendStop("One review exceeds the configured Luna input envelope")
        else:
            current = candidate
    if current:
        batches.append(current)
    return batches


def resolve_luna(state: State, calls: Calls, items: list[dict[str, Any]],
                 labels: dict[str, dict[str, Any]], config: dict[str, Any], extraction: bool) -> None:
    stage = "extract" if extraction else "fallback"

    def send(batch: list[dict[str, Any]]) -> dict[str, Any]:
        sources = {item["source"]["review_id"]: item["source"] for item in batch}
        try:
            return calls.invoke("openai", luna_batch_payload(batch, labels, config, extraction),
                                list(sources), stage,
                                lambda reply: parse_luna_batch(reply, sources, labels, extraction,
                                                               state.label_config, require_reasons=record_schema(config)=='record-v2'), repair_output=False)
        except InvalidOutput as exc:
            return {"valid": {}, "errors": {rid: str(exc) for rid in sources}}
        except ProviderError as exc:
            if exc.transient and not exc.unknown_charge:
                for item in batch:
                    state.quarantine(item, "api_retries_exhausted")
                return {"valid": {}, "errors": {}, "terminal": True}
            raise

    fresh, repair = [], []
    for item in items:
        rid = item["source"]["review_id"]
        saved = state.stage_result(item["key"], stage)
        if saved is not None:
            state.complete(item, saved)
            continue
        previous = state.events_for(rid, stage)
        failures = sum(rid in event.get("invalid_review_ids", [])
                       or str(event.get("error", "")).startswith("Invalid output:") for event in previous)
        if failures >= 2:
            state.quarantine(item, "invalid_model_output_after_retry")
        elif failures:
            repair.append(item)
        else:
            fresh.append(item)

    for batch in pack(fresh, labels, config, extraction):
        result = send(batch)
        if result.get("terminal"):
            continue
        for item in batch:
            rid = item["source"]["review_id"]
            if rid in result["valid"]:
                record = result["valid"][rid]
                state.stage_result(item["key"], stage, record)
                state.complete(item, record)
            else:
                repair.append(item)
    # Every repair contains only one previously missing/invalid ID, never valid siblings.
    for item in repair:
        result = send([item])
        if result.get("terminal"):
            continue
        rid = item["source"]["review_id"]
        if rid in result["valid"]:
            state.stage_result(item["key"], stage, result["valid"][rid])
            state.complete(item, result["valid"][rid])
        else:
            state.quarantine(item, "invalid_model_output_after_retry")


def enrich_batch(state: State, calls: Calls, items: list[dict[str, Any]],
                 config: dict[str, Any], quota: int) -> None:
    if config['enrichment'].get('fallback_selection_policy') == 'lowest-confidence-v1' and not calls.simulated:
        raise ValueError('Frozen deterministic config requires run_deterministic, not first-admission batching')
    labels: dict[str, dict[str, Any]] = {}
    extracts, fallbacks = [], []
    routing = config["enrichment"]
    try:
        for item in items:
            source = item["source"]
            values = state.stage_result(item["key"], "jev")
            if values is None:
                try:
                    values = calls.invoke("typesafe", jev_payload(source["review_text"], config),
                                          [source["review_id"]], "jev",
                                          lambda reply: parse_jev(reply, routing["confidence_threshold"], routing.get("probability_margin_threshold", 0.15)))
                except InvalidOutput:
                    state.quarantine(item, "invalid_model_output_after_retry")
                    continue
                except ProviderError as exc:
                    if exc.transient and not exc.unknown_charge:
                        state.quarantine(item, "api_retries_exhausted")
                        continue
                    raise
                state.stage_result(item["key"], "jev", values)
            labels[source["review_id"]] = values
            fallback = values["low_confidence"] and calls.ledger.allow_fallback(
                item["key"], calls.fallback_scope, quota)
            if fallback:
                fallbacks.append(item)
            elif len(source["review_text"]) > routing["short_review_chars"]:
                extracts.append(item)
            else:
                record = {key: values[key] for key in (
                    "topic", "intent", "severity", "sentiment", "needs_review", 'needs_review_reasons')}
                record.update(review_id=source["review_id"], source_sha256=source["source_sha256"],
                              status="completed", label_config=state.label_config,
                              evidence_quote=source["review_text"],
                              entities=deterministic_entities(source["review_text"], routing["entity_terms"]))
                state.complete(item, record)
        resolve_luna(state, calls, extracts, labels, config, True)
        resolve_luna(state, calls, fallbacks, labels, config, False)
    except (SpendStop, ConfigMismatch):
        for item in items:
            state.release(item)
        raise
    except ProviderError as exc:
        if not exc.unknown_charge:
            for item in items:
                state.release(item)
        raise
