"""Common record validation and immutable enrichment configuration identity."""

import hashlib
import json
import math
from pathlib import Path
from typing import Any

TOPICS = ("access", "usability", "playback", "downloads", "catalog", "billing", "support", "other")
INTENTS = ("cancellation", "complaint", "request", "praise", "unclear")
LABEL_FIELDS = ("topic", "intent", "sentiment", "severity", "entities", "evidence_quote",
                "needs_review", "needs_review_reasons", "label_config")
REVIEW_REASONS = ('language_non_english', 'language_not_understood', 'missing_context', 'low_confidence')


def record_schema(config):
    return 'record-v2' if config['enrichment'].get('needs_review_policy') == 'persistent-context-reasons-v1' else 'record-v1'


def validate_reasons(reasons, flagged=None):
    if not isinstance(reasons, list) or any(type(reason) is not str or reason not in REVIEW_REASONS for reason in reasons):
        raise ValueError('Invalid needs_review_reasons')
    if len(reasons) != len(set(reasons)):
        raise ValueError('Duplicate needs_review_reasons')
    if flagged is not None and (type(flagged) is not bool or flagged != bool(reasons)):
        raise ValueError('needs_review must match needs_review_reasons')


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def cache_key(text: str, label_config: str) -> str:
    return digest([hashlib.sha256(text.encode("utf-8")).hexdigest(), label_config])


def configuration(config: dict[str, Any], simulated: bool = False) -> str:
    root = Path(__file__).resolve().parents[1]
    prompts = {name: (root / "prompts" / name).read_text(encoding="utf-8")
               for name in (config["enrichment"].get("jev_prompt", "jev-v1.json"), config['enrichment'].get('luna_prompt', 'luna-enrich-v1.txt'))}
    return digest({"models": config["models"], "routing": config["enrichment"],
                   "prompts": prompts, "schema_version": record_schema(config), "extractor": "exact-v1",
                   "simulated": simulated})


def validate_record(record: dict[str, Any], source: dict[str, str], label_config: str, require_reasons: bool = False) -> None:
    if record.get("review_id") != source["review_id"]:
        raise ValueError("Returned source ID mismatch")
    if record.get("source_sha256") != source["source_sha256"]:
        raise ValueError("Returned source hash mismatch")
    if record.get("status") != "completed" or record.get("label_config") != label_config:
        raise ValueError("Record status/configuration mismatch")
    if record.get("topic") not in TOPICS or record.get("intent") not in INTENTS:
        raise ValueError("Invalid topic or intent")
    severity, sentiment = record.get("severity"), record.get("sentiment")
    if type(severity) is not int or not 1 <= severity <= 5:
        raise ValueError("Severity must be integer 1..5")
    if type(sentiment) not in (int, float) or not math.isfinite(sentiment) or not -1 <= sentiment <= 1:
        raise ValueError("Sentiment must be finite -1..1")
    if type(record.get("needs_review")) is not bool:
        raise ValueError("needs_review must be boolean")
    if require_reasons or 'needs_review_reasons' in record:
        validate_reasons(record.get('needs_review_reasons'), record['needs_review'])
    entities = record.get("entities")
    if not isinstance(entities, list) or any(not isinstance(x, str) or not x.strip() for x in entities):
        raise ValueError("Entities must be a list of nonempty strings")
    quote = record.get("evidence_quote")
    if not isinstance(quote, str) or not quote.strip() or quote not in source["review_text"]:
        raise ValueError("Quote must be a nonempty exact source substring")


def output_schema(extraction: bool, reasons: bool = False) -> dict[str, Any]:
    properties: dict[str, Any] = {"review_id": {"type": "string"},
                                  "entities": {"type": "array", "items": {"type": "string"}},
                                  "evidence_quote": {"type": "string"}}
    if not extraction:
        properties.update(topic={"type": "string", "enum": list(TOPICS)},
                          intent={"type": "string", "enum": list(INTENTS)},
                          severity={"type": "integer", "minimum": 1, "maximum": 5},
                          sentiment={"type": "number", "minimum": -1, "maximum": 1},
                          needs_review={"type": "boolean"})
    if reasons:
        properties['needs_review_reasons'] = {'type': 'array', 'items': {'type': 'string', 'enum': list(REVIEW_REASONS)}}
    item = {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}
    return {"type": "object", "properties": {"records": {"type": "array", "items": item}},
            "required": ["records"], "additionalProperties": False}
