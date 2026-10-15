"""Fallback choices, source identities and batch plans do not depend on worker arrival."""

import copy
import csv
import json
import tomllib
from pathlib import Path

import pytest

from pipeline.calls import Calls
from pipeline.classify import jev_payload, parse_jev
from pipeline.deterministic import run_deterministic, select_fallback
from pipeline.providers import MockTransport
from pipeline.schema import configuration
from pipeline.spend import Ledger
from pipeline.state import ConfigMismatch, State


def setup_run(directory, workers, reverse=False):
    directory.mkdir()
    config=tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    config['controls'].update(max_workers=workers,fallback_fraction=.34)
    rows=[{'review_id':rid,'review_text':text,'review_rating':'1','review_likes':'0','app_version':'','review_timestamp':'2023'}
          for rid,text in [('z','low'),('a','low'),('b','medium'),('c','high')]]
    source=directory/'synthetic.csv'
    with source.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(list(reversed(rows)) if reverse else rows)
    state=State(directory/'state.sqlite3',configuration(config,True))
    state.ingest(source,Path('data/manifest.json'))
    ledger=Ledger(directory/'ledger.sqlite3',10)

    class Scores(MockTransport):
        def request(self,provider,payload):
            if provider=='openai':
                frozen=state.artifact('active-routing-tranche')
                assert state.artifact('routing-selection:'+frozen['id']) is not None
                with state.connect() as db:
                    assert db.execute("SELECT COUNT(*) FROM stage_results WHERE stage='jev'").fetchone()[0]==3
            response=super().request(provider,payload)
            if provider=='typesafe':
                response['answers']['topic']['confidence']={'low':.1,'medium':.2,'high':.3}[payload['state']['review_text']]
            return response

    calls=Calls(state,ledger,Scores(),config,'run','initial',True,sleep=lambda _:None)
    return config,state,calls


def test_selection_and_persisted_batches_stable_across_workers_and_input_order(tmp_path):
    plans=[]
    for index,workers in enumerate((1,2,8)):
        config,state,calls=setup_run(tmp_path/str(index),workers,reverse=index%2==1)
        selection=run_deterministic(state,calls,config)
        plans.append(selection)
        assert selection['quota']==1 and selection['eligible_count']==3
        assert selection['ranked_candidates'][0]['origin_id']=='a'
        assert selection['selected_keys']==[selection['ranked_candidates'][0]['key']]
        assert state.counts()=={'completed':4}
        with state.connect() as db:
            events=[json.loads(row[0]) for row in db.execute('SELECT event FROM calls')]
        assert [event['review_ids'] for event in events if event['stage']=='fallback']==[['a']]
        count=len(events)
        assert run_deterministic(state,calls,config) is None
        with state.connect() as db:
            assert db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]==count
    assert plans[0]==plans[1]==plans[2]


def test_rank_ties_use_margin_then_hash_not_arrival():
    candidates=[{'key':'c','confidence':.1,'margin':.2,'text_hash':'a','origin_id':'c'},
                {'key':'b','confidence':.1,'margin':.1,'text_hash':'b','origin_id':'b'},
                {'key':'a','confidence':.1,'margin':.1,'text_hash':'a','origin_id':'a'}]
    assert select_fallback(candidates,2)==['a','b']
    assert select_fallback(list(reversed(candidates)),2)==['a','b']


def test_interrupted_selection_is_reused_without_jev_redispatch(tmp_path):
    config,state,calls=setup_run(tmp_path/'interrupted',1)
    first=run_deterministic(state,calls,config,stop_after=1)
    assert state.counts()['pending']>0
    with state.connect() as db:
        before=[json.loads(row[0]) for row in db.execute('SELECT event FROM calls')]
    calls.phase='resume'
    second=run_deterministic(state,calls,config)
    assert first==second and state.counts()=={'completed':4}
    with state.connect() as db:
        events=[json.loads(row[0]) for row in db.execute('SELECT event FROM calls')]
    assert sum(event['stage']=='jev' for event in before)==sum(event['stage']=='jev' for event in events)==3


def test_worker_and_caps_do_not_change_hash_but_policy_and_thresholds_do():
    config=tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    expected=configuration(config)
    changed=copy.deepcopy(config)
    changed['controls'].update(max_workers=8,fallback_fraction=.05)
    assert configuration(changed)==expected
    changed['enrichment']['confidence_threshold']=.61
    assert configuration(changed)!=expected
    changed=copy.deepcopy(config)
    changed['enrichment']['fallback_selection_policy']='other-policy'
    assert configuration(changed)!=expected
    with pytest.raises(ValueError,match='Unsupported'):
        run_deterministic(None,None,changed)


def test_nonenglish_remains_flagged_even_after_fallback(tmp_path):
    config,state,calls=setup_run(tmp_path/'language',1)
    delegate=calls.transport
    class NonEnglish:
        def request(self,provider,payload):
            response=delegate.request(provider,payload)
            if provider=='typesafe' and payload['state']['review_text']=='low':
                response['answers']['language'].update(choice='nonenglish_understood',
                    probabilities={'english':0,'nonenglish_understood':1,'not_understood':0})
            return response
    calls.transport=NonEnglish()
    run_deterministic(state,calls,config)
    with state.connect() as db:
        record=json.loads(db.execute("SELECT result FROM reviews WHERE review_id='a'").fetchone()[0])
    assert record['needs_review'] is True


def test_resume_rejects_changed_cap_without_reselecting(tmp_path):
    config,state,calls=setup_run(tmp_path/'cap',1)
    selection=run_deterministic(state,calls,config,stop_after=1)
    config['controls']['fallback_fraction']=.5
    with pytest.raises(ConfigMismatch,match='cap changed'):
        run_deterministic(state,calls,config)
    frozen=state.artifact('active-routing-tranche')
    assert state.artifact('routing-selection:'+frozen['id'])==selection


def test_frozen_auxiliary_fields_are_required_but_not_confidence_rank_inputs():
    config=tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    response=MockTransport().request('typesafe',jev_payload('synthetic',config))
    response['answers']['language']['confidence']=.01
    result=parse_jev(response,.6,0,require_auxiliary=True)
    assert not result['low_confidence']
    del response['answers']['language']
    with pytest.raises(ValueError,match='requires language'):
        parse_jev(response,.6,0,require_auxiliary=True)
