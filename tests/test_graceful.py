"""No-network eight-worker pause/resume and one shared invocation cap."""
import csv
import json
import time
from pathlib import Path

import pytest

from pipeline.graceful import run_segment
from pipeline.providers import MockTransport
from tests.test_deterministic import setup_run


def test_pause_during_jev_drains_then_resumes_without_repeating_scores(tmp_path):
    config,state,calls = setup_run(tmp_path/'work',8)
    output = tmp_path/'receipts'
    output.mkdir()
    original = calls.transport

    class StopDuringScore:
        def request(self,provider,payload):
            (output/'stop.request').touch()
            time.sleep(.08)
            return original.request(provider,payload)

    calls.transport = StopDuringScore()
    paused = run_segment(state,calls,config,output)
    assert paused['status']=='stopped_user' and paused['drained']
    assert state.counts().get('pending')
    assert not (output/'stop.request').exists()
    with state.connect() as db:
        scores = db.execute("SELECT COUNT(*) FROM stage_results WHERE stage='jev'").fetchone()[0]
        prior_ids = {r[0] for r in db.execute('SELECT request_id FROM calls')}
    assert scores > 0
    calls.transport = original
    resumed = run_segment(state,calls,config,output,resume=True)
    assert resumed['status']=='completed' and resumed['drained']
    assert resumed['run_id']==paused['run_id']
    assert resumed['invocation_spent_nanodollars']>=paused['invocation_spent_nanodollars']
    with state.connect() as db:
        events = [json.loads(r[0]) for r in db.execute('SELECT event FROM calls')]
    assert sum(e['stage']=='jev' for e in events)==3
    assert all(e['phase']=='resume' for e in events if e['request_id'] not in prior_ids)


def test_stale_stop_and_changed_resume_cap_refused(tmp_path):
    config,state,calls = setup_run(tmp_path/'work',8)
    output = tmp_path/'receipts'
    output.mkdir()
    (output/'stop.request').touch()
    with pytest.raises(ValueError,match='Unacknowledged'):
        run_segment(state,calls,config,output)
    (output/'stop.request').unlink()
    identity = {'run_id':calls.run_id,'label_config':state.label_config,
                'cap':config['controls']['run_api_cap_usd'],'fallback_fraction':.34,'status':'stopped_user'}
    state.artifact('graceful-invocation',identity)
    config['controls']['run_api_cap_usd'] += .01
    with pytest.raises(ValueError,match='preserve invocation'):
        run_segment(state,calls,config,output,resume=True)


def test_shared_cap_latches_and_cannot_resume_without_gate(tmp_path):
    config,state,calls = setup_run(tmp_path/'work',8)
    config['controls']['run_api_cap_usd'] = .000000001
    result = run_segment(state,calls,config,tmp_path/'receipts')
    assert result['status']=='stopped_cap' and result['drained']
    assert calls.ledger.run_stop(calls.run_id)
    with pytest.raises(ValueError,match='voluntary'):
        run_segment(state,calls,config,tmp_path/'receipts',resume=True)


def test_finish_pause_preserves_selection_completed_ids_and_health(tmp_path, monkeypatch):
    config,state,calls = setup_run(tmp_path/'work',8)
    monkeypatch.setattr(calls.ledger,'admit',lambda *args,**kwargs:0)
    rows = [{'review_id':f'extra-{i}','review_text':f'Synthetic long review {i} '+('x'*300),
             'review_rating':'1','review_likes':'0','app_version':'','review_timestamp':'2023'} for i in range(450)]
    source = tmp_path/'extra.csv'
    with source.open('w',encoding='utf-8',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    state.ingest(source,Path('data/manifest.json'))
    output = tmp_path/'receipts'
    output.mkdir()
    delegate = MockTransport()

    class StopDuringFinish:
        def request(self,provider,payload):
            if provider=='openai':
                (output/'stop.request').touch()
                time.sleep(.12)
            return delegate.request(provider,payload)

    calls.transport = StopDuringFinish()
    first = run_segment(state,calls,config,output)
    assert first['status']=='stopped_user' and first['drained']
    frozen = state.artifact('active-routing-tranche')
    selection = state.artifact('routing-selection:'+frozen['id'])
    with state.connect() as db:
        before = {r[0] for r in db.execute("SELECT review_id FROM reviews WHERE status='completed'")}
    assert before and state.counts().get('pending')
    calls.transport = delegate
    second = run_segment(state,calls,config,output,resume=True)
    assert second['status']=='completed'
    assert state.artifact('routing-selection:'+frozen['id'])==selection
    assert set(first['connection_window']['seen']) <= set(second['connection_window']['seen'])
    with state.connect() as db:
        resumed = [json.loads(r[0]) for r in db.execute('SELECT event FROM calls')]
    assert not before & {rid for e in resumed if e['phase']=='resume' for rid in e['review_ids']}


def test_graceful_stop_allows_admitted_repair_to_finish(tmp_path):
    config,state,calls = setup_run(tmp_path/'work',8)
    output = tmp_path/'receipts'
    output.mkdir()
    delegate = calls.transport

    class RepairAfterStop:
        def request(self,provider,payload):
            reply = delegate.request(provider,payload)
            if 'validation_error' not in payload.get('state',{}):
                (output/'stop.request').touch()
                time.sleep(.08)
                reply['answers'].pop('topic')
            return reply

    calls.transport = RepairAfterStop()
    result = run_segment(state,calls,config,output)
    assert result['status']=='stopped_user' and result['drained']
    with state.connect() as db:
        events = [json.loads(row[0]) for row in db.execute('SELECT event FROM calls')]
    assert any(e['attempt']==2 and e['outcome']=='succeeded' for e in events)


def test_draft_command_is_offline_and_refuses_paid_dispatch():
    from pipeline.graceful import run_plan
    plan = Path('docs/100k-run-proposal-draft.json')
    assert run_plan(plan)['status']=='offline only; no dispatch'
    with pytest.raises(ValueError,match='Draft plan cannot execute'):
        run_plan(plan,confirmed=True)
