"""Common record validation and immutable enrichment configuration identity."""

import hashlib
import json
import math
from pathlib import Path
from typing import Any

TOPICS = ("access", "usability", "playback", "downloads", "catalog", "billing", "support", "other")
INTENTS = ("cancellation", "complaint", "request", "praise", "unclear")
LABEL_FIELDS = ("topic", "intent", "sentiment", "severity", "entities", "evidence_quote",
                "needs_review", "label_config")


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
               for name in ("jev-v1.json", "luna-enrich-v1.txt")}
    return digest({"models": config["models"], "routing": config["enrichment"],
                   "prompts": prompts, "schema_version": "record-v1", "extractor": "exact-v1",
                   "simulated": simulated})


def validate_record(record: dict[str, Any], source: dict[str, str], label_config: str) -> None:
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
    entities = record.get("entities")
    if not isinstance(entities, list) or any(not isinstance(x, str) or not x.strip() for x in entities):
        raise ValueError("Entities must be a list of nonempty strings")
    quote = record.get("evidence_quote")
    if not isinstance(quote, str) or not quote.strip() or quote not in source["review_text"]:
        raise ValueError("Quote must be a nonempty exact source substring")


def output_schema(extraction: bool) -> dict[str, Any]:
    properties: dict[str, Any] = {"review_id": {"type": "string"},
                                  "entities": {"type": "array", "items": {"type": "string"}},
                                  "evidence_quote": {"type": "string"}}
    if not extraction:
        properties.update(topic={"type": "string", "enum": list(TOPICS)},
                          intent={"type": "string", "enum": list(INTENTS)},
                          severity={"type": "integer", "minimum": 1, "maximum": 5},
                          sentiment={"type": "number", "minimum": -1, "maximum": 1},
                          needs_review={"type": "boolean"})
    item = {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}
    return {"type": "object", "properties": {"records": {"type": "array", "items": item}},
            "required": ["records"], "additionalProperties": False}
