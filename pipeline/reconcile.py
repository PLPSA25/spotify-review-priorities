"""Explicit human reconciliation of an uncertain charge; no provider calls."""

import hashlib
import uuid
from pathlib import Path

from pipeline.prepare import atomic_json
from pipeline.spend import Ledger, money


def reconcile_charge(ledger_path: Path, reservation: str, cost_usd: str,
                     evidence: Path, cap: float, confirmed: bool) -> None:
    if not confirmed:
        raise ValueError("Reconciliation requires --confirm-reconciliation and verified cost evidence")
    if not ledger_path.is_file() or not evidence.is_file():
        raise ValueError("Existing ledger and local reconciliation evidence are required")
    evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    ledger = Ledger(ledger_path, cap)
    amount = money(cost_usd)
    report = {"reservation": reservation, "cost_nanodollars": amount,
              "evidence_sha256": evidence_sha, "source": "human_verified",
              "note": "No token usage invented; original calls retain unavailable usage."}
    atomic_json(ledger_path.parent / ("reconciliation-" + str(uuid.uuid4()) + ".json"), report)
    ledger.settle(reservation, amount, "human_verified:" + evidence_sha)
