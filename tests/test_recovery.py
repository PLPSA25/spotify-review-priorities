"""Known results recover without dispatch; unknown costs require explicit evidence."""

import copy
import json
from pathlib import Path

import pytest

from pipeline.classify import enrich_one, jev_payload
from pipeline.providers import MockTransport
from pipeline.reconcile import reconcile_charge
from pipeline.recovery import recover
from pipeline.spend import money
from tests.test_enrichment import environment


def test_saved_response_restored_after_crash_without_paid_relabel(tmp_path: Path) -> None:
    _, config, state, ledger, calls = environment(tmp_path, ("short",))
    state.claim(-1)
    response = MockTransport().request("typesafe", jev_payload("short", config))
    ledger.reserve("crashed", "run", money(0.01), 1)
    event = {"request_id": "crashed", "review_ids": ["0"], "stage": "jev", "attempt": 1,
             "provider": "typesafe", "role": "enrich", "model": "jev-1.13.0",
             "label_config": state.label_config, "outcome": "failed", "phase": "initial",
             "reservation_settled": False, "error": "dispatch_started_outcome_unresolved",
             "response": response}
    state.save_call(event)
    assert recover(state, config, ledger) == {"released_known_work": 1, "blocked_unknown_charge": 0}
    assert ledger.totals()["reserved_nanodollars"] == 0

    def fail_request(provider, payload):
        raise AssertionError("Saved valid Jev output must not be dispatched again")

    calls.transport.request = fail_request
    enrich_one(state, calls, state.claim(30), config, 0)
    assert state.counts() == {"completed": 1}
    assert state.events_for("0")[0]["outcome"] == "succeeded"
    assert state.events_for("0")[0]["model"] == "jev-1.13.0"


def test_unknown_charge_blocks_until_receipt_reconciled(tmp_path: Path) -> None:
    _, config, state, ledger, _ = environment(tmp_path, ("short",))
    state.claim(-1)
    ledger.reserve("unknown", "run", money(0.01), 1)
    state.save_call({"request_id": "unknown", "review_ids": ["0"], "stage": "jev", "attempt": 1,
                     "provider": "typesafe", "role": "enrich", "label_config": state.label_config,
                     "outcome": "failed", "reservation_settled": False, "error": "timeout"})
    assert recover(state, config, ledger)["blocked_unknown_charge"] == 1
    assert state.claim(30) is None
    receipt = tmp_path / "receipt.txt"
    receipt.write_text("Synthetic accounting evidence only.")
    with pytest.raises(ValueError, match="confirm-reconciliation"):
        reconcile_charge(ledger.path, "unknown", "0.002", receipt, 10, False)
    reconcile_charge(ledger.path, "unknown", "0.002", receipt, 10, True)
    assert ledger.totals()["spent_nanodollars"] == money(0.002)
    assert recover(state, config, ledger)["released_known_work"] == 1
    assert state.claim(30) is not None


def test_saved_malformed_response_does_not_become_success(tmp_path: Path) -> None:
    _, config, state, ledger, _ = environment(tmp_path, ("short",))
    state.claim(-1)
    response = MockTransport().request("typesafe", jev_payload("short", config))
    response = copy.deepcopy(response)
    response["answers"]["topic"]["choice"] = "wrong"
    ledger.reserve("bad", "run", money(0.01), 1)
    state.save_call({"request_id": "bad", "review_ids": ["0"], "stage": "jev", "attempt": 1,
                     "provider": "typesafe", "role": "enrich", "model": "jev-1.13.0",
                     "label_config": state.label_config, "outcome": "failed",
                     "reservation_settled": False, "error": "dispatch_started_outcome_unresolved",
                     "response": response})
    recover(state, config, ledger)
    assert state.events_for("0")[0]["outcome"] == "failed"
    assert state.stage_result(state.claim(30)["key"], "jev") is None


def test_recovery_artifacts_never_include_evidence_contents(tmp_path: Path) -> None:
    _, _, _, ledger, _ = environment(tmp_path)
    ledger.reserve("id", "r", 100, 1)
    evidence = tmp_path / "receipt.txt"
    evidence.write_text("DO_NOT_COPY_THIS_CONTENT")
    reconcile_charge(ledger.path, "id", "0.000000001", evidence, 10, True)
    reports = list(tmp_path.glob("reconciliation-*.json"))
    assert len(reports) == 1
    assert "DO_NOT_COPY_THIS_CONTENT" not in reports[0].read_text()
    assert json.loads(reports[0].read_text())["source"] == "human_verified"
