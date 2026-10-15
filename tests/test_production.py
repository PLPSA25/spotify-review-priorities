"""Production preflight/status stay offline and do not leak payloads."""
import json
from pathlib import Path

import pytest

from pipeline import production
from pipeline.prepare import atomic_json
from tests.test_deterministic import setup_run


def test_status_counts_only_selected_scope_and_has_no_review_text(tmp_path,monkeypatch):
    config,state,calls = setup_run(tmp_path/'work',8)
    with state.connect() as db:
        db.execute('CREATE TABLE production_scope(review_id TEXT PRIMARY KEY)')
        db.execute("INSERT INTO production_scope VALUES ('a')")
        db.execute('CREATE TABLE production_work(key TEXT PRIMARY KEY)')
        db.execute("INSERT INTO production_work SELECT work_key FROM reviews WHERE review_id='a'")
    monkeypatch.setattr(production.tomllib,'loads',lambda _:config)
    config['controls']['ledger_path'] = str(calls.ledger.path)
    result = production.status(state.path.parent)
    assert result['scope_counts']=={'pending':1}
    assert result['new_distinct_counts']=={'pending':1}
    assert result['safe_to_resume'] is False
    assert 'review_text' not in json.dumps(result)


def test_authorization_requires_explicit_acknowledgement():
    with pytest.raises(ValueError,match='acknowledge-spend'):
        production.authorize(Path('not-opened.json'))


def test_changed_plan_or_commit_invalidates_authorization(tmp_path,monkeypatch):
    plan_path = tmp_path/'plan.json'
    receipt_path = tmp_path/'authorization.json'
    plan = {'approval_receipt':str(receipt_path)}
    atomic_json(plan_path,plan)
    atomic_json(receipt_path,{'plan_sha256':'altered','git_commit':'unchanged'})
    monkeypatch.setattr(production,'git_head',lambda:'unchanged')
    with pytest.raises(ValueError,match='Authorization plan'):
        production.check_authorization(plan_path,plan)


def test_immutable_evidence_is_not_overwritten(tmp_path):
    (tmp_path/'checkpoint_before.json').write_text('retained')
    with pytest.raises(ValueError,match='Immutable'):
        production.evidence('before',tmp_path)
    assert (tmp_path/'checkpoint_before.json').read_text()=='retained'
