"""Jev interpretation, conservative extraction and bounded Luna enrichment."""

import json
import math
import re
from pathlib import Path
from typing import Any

from pipeline.calls import Calls, InvalidOutput
from pipeline.prepare import course_helper
from pipeline.providers import ProviderError
from pipeline.schema import (
    REVIEW_REASONS,
    canonical,
    output_schema,
    record_schema,
    validate_reasons,
    validate_record,
)
from pipeline.spend import SpendStop
from pipeline.state import ConfigMismatch, State


def prompt_root() -> Path:
    return Path(__file__).resolve().parents[1] / "prompts"


def jev_payload(text: str, config: dict[str, Any]) -> dict[str, Any]:
    name = config.get("enrichment", {}).get("jev_prompt", "jev-v1.json")
    if name not in {"jev-v1.json", "jev-v2.json", "jev-v3.json"}:
        raise ValueError("Unknown Jev prompt version")
    definition = json.loads((prompt_root() / name).read_text(encoding="utf-8"))
    questions = definition["questions"]
    state = {"review_text": text}
    if "shared_state_rules" in definition:
        state["trusted_rules"] = definition["shared_state_rules"]
    for question in questions.values():
        if "shared_state_rules" in definition:
            question["instructions"] = "Apply state.trusted_rules to untrusted state.review_text. " + question["instructions"]
        else:
            question["instructions"] = definition["instructions"] + " " + question["instructions"]
    return {"model": config["models"]["jev"], "state": state,
            "questions": questions}


def finite_number(value: Any, lower: float, upper: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError("Invalid finite numeric response")
    return float(value)


def parse_jev(response: dict[str, Any], threshold: float, margin_threshold: float = 0.15,
              require_auxiliary: bool = False) -> dict[str, Any]:
    definition = json.loads((prompt_root() / "jev-v1.json").read_text(encoding="utf-8"))
    answers = response["answers"]
    if require_auxiliary and not {'language','missing_context'} <= set(answers):
        raise ValueError('Frozen prompt requires language and missing-context judgments')
    confidences = []
    margins = []
    values: dict[str, Any] = {}
    for name in ("topic", "intent", "severity", "sentiment") + (("language",) if "language" in answers else ()):
        answer = answers[name]
        question = definition["questions"][name]
        if answer["type"] != question["type"]:
            raise ValueError("Question/answer type mismatch")
        choices = list(question["criteria"]) if name != "sentiment" else [str(i) for i in range(5)]
        probabilities = answer["probabilities"]
        if set(probabilities) != set(choices):
            raise ValueError("Probability options do not match rubric")
        distribution = [finite_number(probabilities[x], 0, 1) for x in choices]
        # API probabilities are rounded; validate their envelope, not exact raw arithmetic.
        if not math.isclose(sum(distribution), 1, abs_tol=0.06):
            raise ValueError("Probabilities do not sum to one")
        confidence = finite_number(answer["confidence"], 0, 1)
        if name != 'language':
            confidences.append(confidence)
        if name == "sentiment":
            score = finite_number(answer["score"], 0, 4)
            if not math.isclose(score, sum(i * probability for i, probability in enumerate(distribution)), abs_tol=0.06):
                raise ValueError("Score differs from probability-weighted level")
            values[name] = score / 2 - 1
        else:
            if answer["choice"] not in choices:
                raise ValueError("Invalid choice")
            if probabilities[answer["choice"]] < max(distribution):
                raise ValueError("Choice differs from highest-probability option")
            values[name] = answer["choice"]
            ordered = sorted(distribution, reverse=True)
            if name != 'language':
                margins.append(ordered[0] - ordered[1])
    values["severity"] = int(values["severity"])
    missing = 0.0
    if "missing_context" in answers:
        if answers["missing_context"]["type"] != "noul":
            raise ValueError("Missing-context answer must be Noul")
        missing = finite_number(answers["missing_context"]["noul"], 0, 1)
    language = values.pop("language", "english")
    if language == "not_understood":
        values.update(topic="other", intent="unclear", severity=1)
    low = min(confidences) < threshold or min(margins) < margin_threshold
    values["needs_review"] = language != "english" or missing >= 0.5 or low
    values["low_confidence"] = low
    values["nonenglish"] = language != "english"
    values['needs_review_reasons'] = [reason for reason, applies in (
        ('language_non_english', language == 'nonenglish_understood'),
        ('language_not_understood', language == 'not_understood'),
        ('missing_context', missing >= .5), ('low_confidence', low)) if applies]
    return values


def deterministic_entities(text: str, terms: list[str]) -> list[str]:
    found = []
    for term in terms:
        for match in re.finditer(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.IGNORECASE):
            if match.group() not in found:
                found.append(match.group())
    return found


def luna_payload(source: dict[str, str], labels: dict[str, Any], config: dict[str, Any],
                 extraction: bool) -> dict[str, Any]:
    name = config['enrichment'].get('luna_prompt', 'luna-enrich-v1.txt')
    if name not in {'luna-enrich-v1.txt', 'luna-enrich-v2.txt'}:
        raise ValueError('Unknown Luna prompt version')
    prefix = (prompt_root() / name).read_text(encoding="utf-8")
    item: dict[str, Any] = {"review_id": source["review_id"], "review_text": source["review_text"]}
    if extraction:
        item["labels"] = {key: labels[key] for key in ("topic", "intent", "severity", "sentiment")}
    return {"model": config["models"]["luna"], "instructions": prefix,
            "input": "TASK: " + ("extraction-only" if extraction else "independent fallback classification")
                     + "\nBEGIN_UNTRUSTED_REVIEWS_JSON\n" + canonical([item])
                     + "\nEND_UNTRUSTED_REVIEWS_JSON",
            "reasoning": {"effort": config["models"]["effort"]},
            "max_output_tokens": config["models"]["output_token_cap"],
            "service_tier": config["models"]["service_tier"], "store": False,
            "text": {"format": {"type": "json_schema", "name": "review_enrichment",
                                  "strict": True, "schema": output_schema(extraction, record_schema(config)=='record-v2')}}}


def luna_batch_payload(items: list[dict[str, Any]], labels: dict[str, dict[str, Any]],
                       config: dict[str, Any], extraction: bool) -> dict[str, Any]:
    if not 1 <= len(items) <= min(50, config["enrichment"]["batch_size"]):
        raise ValueError("Luna batch exceeds configured 1..50 review limit")
    sources = [item["source"] for item in items]
    payload = luna_payload(sources[0], labels[sources[0]["review_id"]], config, extraction)
    packed = []
    for source in sources:
        row: dict[str, Any] = {"review_id": source["review_id"], "review_text": source["review_text"]}
        if extraction:
            row["labels"] = {key: labels[source["review_id"]][key] for key in (
                "topic", "intent", "severity", "sentiment")}
        packed.append(row)
    payload["input"] = payload["input"].split("BEGIN_UNTRUSTED_REVIEWS_JSON", 1)[0] + (
        "BEGIN_UNTRUSTED_REVIEWS_JSON\n" + canonical(packed) + "\nEND_UNTRUSTED_REVIEWS_JSON")
    payload["max_output_tokens"] = min(config["models"]["output_token_cap"],
                                       len(items) * config["enrichment"]["luna_output_tokens_per_review"])
    return payload


def parse_luna(response: dict[str, Any], source: dict[str, str], labels: dict[str, Any],
               extraction: bool, label_config: str, require_reasons: bool = False) -> dict[str, Any]:
    if response.get("status") != "completed":
        raise ValueError("Luna refused or truncated response")
    blocks = response.get("output")
    if not isinstance(blocks, list) or any(not isinstance(block, dict) for block in blocks):
        raise ValueError("Malformed Luna output blocks")
    chunks = []
    for block in blocks:
        content = block.get("content", [])
        if not isinstance(content, list) or any(not isinstance(part, dict) for part in content):
            raise ValueError("Malformed Luna content")
        for part in content:
            if part.get("type") == "output_text":
                if not isinstance(part.get("text"), str):
                    raise ValueError("Luna output text must be a string")
                chunks.append(part["text"])
    helper = course_helper(Path(__file__).resolve().parents[1] / "data/check_submission.py")
    result = helper.loads("".join(chunks))
    if not isinstance(result, dict) or set(result) != {"records"}:
        raise ValueError("Malformed Luna result envelope")
    records = result["records"]
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise ValueError("Luna records must be objects")
    if len(records) != 1 or records[0].get("review_id") != source["review_id"]:
        raise ValueError("Returned batch IDs missing/duplicate/foreign")
    expected = {"review_id", "entities", "evidence_quote"}
    if not extraction:
        expected.update({"topic", "intent", "severity", "sentiment", "needs_review"})
    reason_mode = require_reasons or 'needs_review_reasons' in records[0]
    if reason_mode:
        expected.add('needs_review_reasons')
    if set(records[0]) != expected:
        raise ValueError("Returned record fields do not match the requested schema")
    if reason_mode:
        validate_reasons(records[0]['needs_review_reasons'], None if extraction else records[0]['needs_review'])
    values = {**labels, **records[0]} if extraction else records[0]
    values = {key: value for key, value in values.items() if key not in {"low_confidence", "nonenglish"}}
    values.update(review_id=source["review_id"], source_sha256=source["source_sha256"],
                  status="completed", label_config=label_config)
    if labels.get("nonenglish"):
        values["needs_review"] = True
    if reason_mode:
        initial = set(labels.get('needs_review_reasons', []))
        # Extraction cannot resolve classifier uncertainty. Independent fallback
        # can replace low confidence, but preserves language and context signals.
        retained = initial if extraction else initial - {'low_confidence'}
        reasons = retained | set(records[0]['needs_review_reasons'])
        values['needs_review_reasons'] = [reason for reason in REVIEW_REASONS if reason in reasons]
        values['needs_review'] = bool(reasons)
    elif extraction:
        # Legacy extraction must not publish an inferred reason list alongside
        # historical schemas that did not request final reasons.
        values.pop('needs_review_reasons', None)
    validate_record(values, source, label_config, require_reasons=reason_mode)
    return values


def parse_luna_batch(response: dict[str, Any], sources: dict[str, dict[str, str]],
                     labels: dict[str, dict[str, Any]], extraction: bool,
                     label_config: str, verifier_diagnostics: bool = False, require_reasons: bool = False) -> dict[str, Any]:
    """Validate each requested ID independently; retain valid siblings in a bad response."""
    from collections import Counter

    helper = course_helper(Path(__file__).resolve().parents[1] / "data/check_submission.py")
    if response.get("status") != "completed":
        raise ValueError("Luna refused or truncated batch")
    try:
        texts = [part["text"] for block in response["output"] for part in block.get("content", [])
                 if part.get("type") == "output_text"]
        try:
            envelope = helper.loads("".join(texts))
        except ValueError:
            # Responses can contain multiple messages. Accept only one distinct
            # structured envelope; never choose between conflicting predictions.
            candidates = {}
            for block in response["output"]:
                text = "".join(part["text"] for part in block.get("content", [])
                               if part.get("type") == "output_text")
                try:
                    candidate = helper.loads(text)
                except ValueError:
                    continue
                if isinstance(candidate, dict) and set(candidate) == {"records"}:
                    candidates[canonical(candidate)] = candidate
            if len(candidates) != 1:
                raise ValueError("Missing or conflicting structured message envelopes") from None
            envelope = next(iter(candidates.values()))
        rows = envelope["records"]
        if not isinstance(rows, list):
            raise TypeError("Batch records must be a list")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Malformed batch envelope") from exc
    counts = Counter(row.get("review_id") for row in rows if isinstance(row, dict)
                     and isinstance(row.get("review_id"), str))
    valid, errors = {}, {}
    unexpected = sorted(set(counts) - set(sources))
    for rid, source in sources.items():
        if counts[rid] != 1:
            errors[rid] = "Missing or duplicate returned ID"
            continue
        row = next(row for row in rows if isinstance(row, dict) and row.get("review_id") == rid)
        diagnostics = {}
        if verifier_diagnostics:
            if row.get('language') not in {'english', 'nonenglish_understood', 'not_understood'} or type(row.get('missing_context')) is not bool:
                errors[rid] = 'Missing or invalid independent language/context diagnostics'
                continue
            diagnostics = {field: row[field] for field in ('language', 'missing_context')}
            row = {field: value for field, value in row.items() if field not in diagnostics}
        single = dict(response)
        single["output"] = [{"content": [{"type": "output_text", "text": canonical({"records": [row]})}]}]
        try:
            valid[rid] = parse_luna(single, source, labels[rid], extraction, label_config, require_reasons=require_reasons)
            valid[rid].update(diagnostics)
        except (ValueError, KeyError, TypeError) as exc:
            errors[rid] = str(exc)
    return {"valid": valid, "errors": errors, "unexpected_ids": unexpected}


def enrich_one(state: State, calls: Calls, item: dict[str, Any], config: dict[str, Any],
               quota: int) -> None:
    if config['enrichment'].get('fallback_selection_policy') == 'lowest-confidence-v1' and not calls.simulated:
        raise ValueError('Frozen deterministic config requires run_deterministic, not first-admission enrichment')
    source, routing = item["source"], config["enrichment"]
    try:
        labels = state.stage_result(item["key"], "jev")
        if labels is None:
            labels = calls.invoke("typesafe", jev_payload(source["review_text"], config),
                                  [source["review_id"]], "jev",
                                  lambda response: parse_jev(response, routing["confidence_threshold"], routing.get("probability_margin_threshold", 0.15)))
            state.stage_result(item["key"], "jev", labels)
        fallback = labels["low_confidence"] and calls.ledger.allow_fallback(
            item["key"], calls.fallback_scope, quota)
        if fallback or len(source["review_text"]) > routing["short_review_chars"]:
            stage = "fallback" if fallback else "extract"
            result = state.stage_result(item["key"], stage)
            if result is None:
                result = calls.invoke("openai", luna_payload(source, labels, config, not fallback),
                                      [source["review_id"]], stage,
                                      lambda response: parse_luna(response, source, labels,
                                                                  not fallback, state.label_config, require_reasons=record_schema(config)=='record-v2'))
                state.stage_result(item["key"], stage, result)
        else:
            result = {key: labels[key] for key in ("topic", "intent", "severity", "sentiment", "needs_review", 'needs_review_reasons')}
            result.update(review_id=source["review_id"], source_sha256=source["source_sha256"],
                          status="completed", label_config=state.label_config,
                          entities=deterministic_entities(source["review_text"], routing["entity_terms"]),
                          evidence_quote=source["review_text"])
        state.complete(item, result)
    except (SpendStop, ConfigMismatch):
        state.release(item)
        raise
    except ProviderError as exc:
        if exc.unknown_charge:
            # Keep the lease and reservation: explicit reconciliation is required.
            raise
        if not exc.transient:
            state.release(item)
            raise
        state.quarantine(item, "api_retries_exhausted")
    except InvalidOutput:
        state.quarantine(item, "invalid_model_output_after_retry")
