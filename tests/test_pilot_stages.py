"""Real role request shapes with mocked responses, claims and warm artifact reuse."""

from pathlib import Path

from pipeline.classify import enrich_one
from pipeline.pilot_stages import business_stages, verify_pilot
from pipeline.rank import aggregate
from tests.test_enrichment import environment


def test_pilot_downstream_roles_and_zero_call_warm_reuse(tmp_path: Path) -> None:
    _, config, state, _, calls = environment(tmp_path, ("one", "two"))
    config["rate_limits"]["openai"].update(rps=60, rpm=3600, tpm=1000000)
    for _ in range(2):
        enrich_one(state, calls, state.claim(30), config, 0)
    verified = verify_pilot(state, calls, config)
    business = business_stages(state, calls, config)
    assert verified["complete"]
    assert business["memo"]["priority_issue"] == ""
    with state.connect() as db:
        count = db.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
        import json

        memo = next(json.loads(row[0]) for row in db.execute("SELECT event FROM calls")
                    if json.loads(row[0])["role"] == "memo")
    assert memo["request"]["text"]["format"]["schema"]["properties"]["priority_issue"]["enum"] == [""]
    assert "exactly one supplied issue_id" in memo["request"]["instructions"]
    calls.transport.request = lambda *args: (_ for _ in ()).throw(AssertionError("Warm must be offline"))
    assert verify_pilot(state, calls, config) == verified
    assert business_stages(state, calls, config) == business
    with state.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == count


def test_rank_exact_tie_and_half_up() -> None:
    records = [{"review_id": "a", "intent": "complaint", "topic": "billing", "severity": 3},
               {"review_id": "b", "intent": "cancellation", "topic": "access", "severity": 1},
               {"review_id": "c", "intent": "complaint", "topic": "access", "severity": 2},
               {"review_id": "d", "intent": "praise", "topic": "access", "severity": 1}]
    membership, ranking, claims = aggregate(records)
    assert len(membership) == 3
    assert [row["issue_id"] for row in ranking] == ["issue-access", "issue-billing"]
    assert ranking[0]["mean_severity"] == "1.500000"
    assert all(row["value"] == ranking[0][row["metric"]] for row in claims if row["issue_id"] == "issue-access")
