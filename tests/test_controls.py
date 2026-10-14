"""Additional boundary tests for budget-before-dispatch and fallback quotas."""

import copy
from pathlib import Path

import pytest

from pipeline.classify import enrich_one, jev_payload
from pipeline.enrich import validate_settings
from pipeline.providers import MockTransport
from pipeline.spend import SpendStop
from tests.test_enrichment import environment


def test_cap_stops_before_transport_and_keeps_pending(tmp_path: Path) -> None:
    _, config, state, ledger, calls = environment(tmp_path, ("short",))
    ledger.cap = 0

    def never_called(provider, payload):
        raise AssertionError("No request may dispatch after budget admission fails")

    calls.transport.request = never_called
    with pytest.raises(SpendStop):
        enrich_one(state, calls, state.claim(30), config, 0)
    assert state.counts() == {"pending": 1}
    assert state.claim(30) is not None
    assert ledger.totals() == {"spent_nanodollars": 0, "reserved_nanodollars": 0}


def test_fallback_quota_cannot_reset_on_resume(tmp_path: Path) -> None:
    _, config, state, _, calls = environment(tmp_path, ("first", "second"))
    mock = MockTransport()

    class LowConfidence:
        def request(self, provider, payload):
            response = mock.request(provider, payload)
            if provider == "typesafe":
                response["answers"]["topic"]["confidence"] = 0.5
            return response

    calls.transport = LowConfidence()
    first = state.claim(30)
    enrich_one(state, calls, first, config, 1)
    calls.run_id, calls.phase = "resumed-run", "resume"
    second = state.claim(30)
    enrich_one(state, calls, second, config, 1)
    assert state.counts() == {"completed": 2}
    events = state.events_for(first["source"]["review_id"]) + state.events_for(second["source"]["review_id"])
    assert sum(event["stage"] == "fallback" for event in events) == 1


def test_cache_origin_requires_own_call_evidence(tmp_path: Path) -> None:
    from tests.test_enrichment import record

    _, _, state, _, _ = environment(tmp_path, ("same", "same"))
    item = state.claim(30)
    with pytest.raises(ValueError, match="lacks succeeded"):
        state.complete(item, record(item["source"], state.label_config))
    assert state.counts() == {"pending": 2}


def test_unapproved_model_and_invalid_settings_rejected(tmp_path: Path) -> None:
    _, config, _, _, _ = environment(tmp_path)
    changed = copy.deepcopy(config)
    changed["models"]["luna"] = "expensive-unapproved-model"
    with pytest.raises(ValueError, match="allowlist"):
        validate_settings(changed)
    changed = copy.deepcopy(config)
    changed["models"]["effort"] = "high"
    with pytest.raises(ValueError, match="none/low"):
        validate_settings(changed)
    response = MockTransport().request("typesafe", jev_payload("synthetic", config))
    assert response["_simulated"] is True
