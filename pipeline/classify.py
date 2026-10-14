"""Jev interpretation, conservative extraction and bounded Luna enrichment."""

import json
import math
import re
from pathlib import Path
from typing import Any

from pipeline.calls import Calls, InvalidOutput
from pipeline.prepare import course_helper
from pipeline.providers import ProviderError
from pipeline.schema import canonical, output_schema, validate_record
from pipeline.spend import SpendStop
from pipeline.state import ConfigMismatch, State


def prompt_root() -> Path:
    return Path(__file__).resolve().parents[1] / "prompts"


def jev_payload(text: str, config: dict[str, Any]) -> dict[str, Any]:
    definition = json.loads((prompt_root() / "jev-v1.json").read_text(encoding="utf-8"))
    questions = definition["questions"]
    for question in questions.values():
        question["instructions"] = definition["instructions"] + " " + question["instructions"]
    return {"model": config["models"]["jev"], "state": {"review_text": text},
            "questions": questions}


def finite_number(value: Any, lower: float, upper: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError("Invalid finite numeric response")
    return float(value)


def parse_jev(response: dict[str, Any], threshold: float) -> dict[str, Any]:
    definition = json.loads((prompt_root() / "jev-v1.json").read_text(encoding="utf-8"))
    answers = response["answers"]
    confidences = []
    values: dict[str, Any] = {}
    for name in ("topic", "intent", "severity", "language", "sentiment"):
        answer = answers[name]
        question = definition["questions"][name]
        if answer["type"] != question["type"]:
            raise ValueError("Question/answer type mismatch")
        choices = list(question["criteria"]) if name != "sentiment" else [str(i) for i in range(5)]
        probabilities = answer["probabilities"]
        if set(probabilities) != set(choices):
            raise ValueError("Probability options do not match rubric")
        distribution = [finite_number(probabilities[x], 0, 1) for x in choices]
        if not math.isclose(sum(distribution), 1, abs_tol=1e-5):
            raise ValueError("Probabilities do not sum to one")
        confidence = finite_number(answer["confidence"], 0, 1)
        confidences.append(confidence)
        if name == "sentiment":
            score = finite_number(answer["score"], 0, 4)
            if not math.isclose(score, sum(i * probability for i, probability in enumerate(distribution)), abs_tol=1e-4):
                raise ValueError("Score differs from probability-weighted level")
            values[name] = score / 2 - 1
        else:
            if answer["choice"] not in choices:
                raise ValueError("Invalid choice")
            if probabilities[answer["choice"]] < max(distribution):
                raise ValueError("Choice differs from highest-probability option")
            values[name] = answer["choice"]
    values["severity"] = int(values["severity"])
    if answers["missing_context"]["type"] != "noul":
        raise ValueError("Missing-context answer must be Noul")
    missing = finite_number(answers["missing_context"]["noul"], 0, 1)
    language = values.pop("language")
    if language == "not_understood":
        values.update(topic="other", intent="unclear", severity=1)
    values["needs_review"] = language != "english" or missing >= 0.5 or min(confidences) < threshold
    values["low_confidence"] = min(confidences) < threshold
    values["nonenglish"] = language != "english"
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
    prefix = (prompt_root() / "luna-enrich-v1.txt").read_text(encoding="utf-8")
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
                                  "strict": True, "schema": output_schema(extraction)}}}


def parse_luna(response: dict[str, Any], source: dict[str, str], labels: dict[str, Any],
               extraction: bool, label_config: str) -> dict[str, Any]:
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
    if set(records[0]) != expected:
        raise ValueError("Returned record fields do not match the requested schema")
    values = {**labels, **records[0]} if extraction else records[0]
    values = {key: value for key, value in values.items() if key not in {"low_confidence", "nonenglish"}}
    values.update(review_id=source["review_id"], source_sha256=source["source_sha256"],
                  status="completed", label_config=label_config)
    if labels.get("nonenglish"):
        values["needs_review"] = True
    validate_record(values, source, label_config)
    return values


def enrich_one(state: State, calls: Calls, item: dict[str, Any], config: dict[str, Any],
               quota: int) -> None:
    source, routing = item["source"], config["enrichment"]
    try:
        labels = state.stage_result(item["key"], "jev")
        if labels is None:
            labels = calls.invoke("typesafe", jev_payload(source["review_text"], config),
                                  [source["review_id"]], "jev",
                                  lambda response: parse_jev(response, routing["confidence_threshold"]))
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
                                                                  not fallback, state.label_config))
                state.stage_result(item["key"], stage, result)
        else:
            result = {key: labels[key] for key in ("topic", "intent", "severity", "sentiment", "needs_review")}
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
