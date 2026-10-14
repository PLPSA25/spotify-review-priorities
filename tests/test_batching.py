"""Batch packing, valid-sibling retention and per-ID repairs without paid calls."""

import json
from pathlib import Path

import pytest

from pipeline.batching import enrich_batch, pack
from pipeline.classify import luna_batch_payload, parse_luna_batch
from pipeline.providers import MockTransport
from pipeline.spend import SpendStop
from tests.test_enrichment import environment


def test_partial_response_retries_only_invalid_ids(tmp_path: Path) -> None:
    _, config, state, _, calls = environment(tmp_path, ("first long review", "second long review", "third long review"))
    config["enrichment"]["short_review_chars"] = 1
    config["rate_limits"]["openai"].update(rps=60, rpm=3600, tpm=1000000)
    items = [state.claim(30) for _ in range(3)]
    sent = []
    base = MockTransport()

    class Partial:
        def request(self, provider, payload):
            response = base.request(provider, payload)
            if provider == "openai":
                packed = payload["input"].split("BEGIN_UNTRUSTED_REVIEWS_JSON\n")[1].split("\nEND_UNTRUSTED_REVIEWS_JSON")[0]
                ids = [item["review_id"] for item in json.loads(packed)]
                sent.append(ids)
                if len(ids) > 1:
                    records = json.loads(response["output"][0]["content"][0]["text"])["records"]
                    records[1]["evidence_quote"] = "not in source"
                    records = records[:-1]  # one invalid quote and one missing ID
                    response["output"][0]["content"][0]["text"] = json.dumps({"records": records})
            return response

    calls.transport = Partial()
    enrich_batch(state, calls, items, config, 0)
    assert state.counts() == {"completed": 3}
    assert len(sent[0]) == 3 and len(sent) == 3
    assert all(len(batch) == 1 for batch in sent[1:])
    assert sent[0][0] not in [rid for batch in sent[1:] for rid in batch]


def test_batch_limits_and_token_envelope(tmp_path: Path) -> None:
    _, config, state, _, _ = environment(tmp_path, tuple("long " + str(i) for i in range(21)))
    items = [state.claim(30) for _ in range(21)]
    labels = {item["source"]["review_id"]: {"topic": "other", "intent": "unclear", "severity": 1, "sentiment": 0}
              for item in items}
    batches = pack(items, labels, config, True)
    assert [len(batch) for batch in batches] == [20, 1]
    with pytest.raises(ValueError, match="limit"):
        luna_batch_payload(items, labels, config, True)
    config["enrichment"]["luna_input_token_bound"] = 1
    with pytest.raises(SpendStop):
        pack(items, labels, config, True)


def test_duplicate_foreign_and_missing_ids_keep_valid_sibling(tmp_path: Path) -> None:
    _, config, state, _, _ = environment(tmp_path, ("one", "two", "three"))
    items = [state.claim(30) for _ in range(3)]
    sources = {item["source"]["review_id"]: item["source"] for item in items}
    labels = {rid: {"topic": "other", "intent": "unclear", "severity": 1, "sentiment": 0,
                    "needs_review": False} for rid in sources}
    response = MockTransport().request("openai", luna_batch_payload(items, labels, config, True))
    records = json.loads(response["output"][0]["content"][0]["text"])["records"]
    duplicated = records[1]
    rows = [records[0], duplicated, duplicated, {"review_id": "foreign", "entities": [], "evidence_quote": "x"}]
    response["output"][0]["content"][0]["text"] = json.dumps({"records": rows})
    result = parse_luna_batch(response, sources, labels, True, state.label_config)
    assert list(result["valid"]) == [records[0]["review_id"]]
    assert len(result["errors"]) == 2
    assert result["unexpected_ids"] == ["foreign"]
