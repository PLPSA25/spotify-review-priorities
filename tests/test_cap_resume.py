"""Latched monetary admission stops drain safely and preserve same-hash work."""

import json
import time

import pytest

from pipeline.calls import Calls
from pipeline.classify import jev_payload, luna_batch_payload
from pipeline.deterministic import run_deterministic
from pipeline.providers import MockTransport
from pipeline.schema import canonical
from pipeline.spend import Ledger, SpendStop, money, token_cost
from pipeline.state import State
from tests.test_enrichment import environment


def test_latched_cap_stays_closed_after_inflight_reservation_settles(tmp_path):
    ledger=Ledger(tmp_path/'ledger.sqlite3',10)
    ledger.reserve('first','limited',money(.01),.01,latch_stop=True)
    with pytest.raises(SpendStop):
        ledger.reserve('denied','limited',1,.01,latch_stop=True)
    ledger.settle('first',0,'cancelled_before_dispatch')
    assert ledger.run_stop('limited')['cause']=='invocation_cap'
    with pytest.raises(SpendStop):
        ledger.reserve('no-reopening','limited',1,.01,latch_stop=True)
    ledger.reserve('new-approval','reviewed-resume',1,.01,latch_stop=True)


def test_eight_worker_cap_stop_leaves_no_torn_records_or_leases_and_resumes(tmp_path):
    _,config,state,ledger,calls=environment(tmp_path,('aa','bb','cc','dd','ee','ff','gg','hh'))
    config['controls']['max_workers']=8
    cost=token_cost(len(canonical(jev_payload('aa',config)).encode())+2048,0,config['planning_rates'],'typesafe')
    config['controls']['run_api_cap_usd']=cost/1e9
    class Slow(MockTransport):
        def request(self,provider,payload):
            time.sleep(.05)
            return super().request(provider,payload)
    calls.transport=Slow()
    with pytest.raises(SpendStop):
        run_deterministic(state,calls,config)
    assert calls.stop.is_set() and ledger.run_stop(calls.run_id)
    assert state.leased_count()==0 and state.counts()=={'pending':8}
    with state.connect() as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        prior=[json.loads(row[0]) for row in db.execute('SELECT event FROM calls')]
        assert db.execute('SELECT COUNT(*) FROM reviews WHERE result IS NOT NULL').fetchone()[0]==0
    successful_ids={rid for event in prior if event['outcome']=='succeeded' for rid in event['review_ids']}
    assert ledger.totals()['reserved_nanodollars']==0
    reopened=State(state.path,state.label_config)
    config['controls']['run_api_cap_usd']=.5
    resumed=Calls(reopened,ledger,MockTransport(),config,'approved-resume','resume',True,sleep=lambda _:None)
    run_deterministic(reopened,resumed,config)
    assert reopened.counts()=={'completed':8}
    with reopened.connect() as db:
        events=[json.loads(row[0]) for row in db.execute('SELECT event FROM calls')]
    assert not any(successful_ids.intersection(event['review_ids']) for event in events if event['run_id']=='approved-resume')


def test_cap_between_partial_luna_batch_and_repair_preserves_valid_siblings(tmp_path):
    _,config,state,ledger,calls=environment(tmp_path,('aa','bb','cc','dd','ee','ff','gg','hh'))
    config['controls'].update(max_workers=1,fallback_fraction=1)
    config['rate_limits']['openai']['rps']=1000
    with state.connect() as db:
        sources=[json.loads(row[0]) for row in db.execute('SELECT source FROM reviews')]
    payload=luna_batch_payload([{'source':source} for source in sources],{source['review_id']:{} for source in sources},config,False)
    inputs=len(canonical(payload).encode())+2048
    rates={**config['planning_rates'],'luna_input_per_million':config['planning_rates']['luna_cache_write_per_million']}
    budget=8*token_cost(100,20,config['planning_rates'],'typesafe')+token_cost(inputs,payload['max_output_tokens'],rates,'openai')
    config['controls']['run_api_cap_usd']=(budget+1)/1e9
    class Partial(MockTransport):
        def request(self,provider,payload):
            result=super().request(provider,payload)
            if provider=='typesafe':
                result['answers']['topic']['confidence']=.2
            else:
                records=json.loads(result['output'][0]['content'][0]['text'])
                records['records'][0]['evidence_quote']='not in source'
                result['output'][0]['content'][0]['text']=json.dumps(records)
                inputs=len(canonical(payload).encode())+2048
                result['usage']={'input_tokens':inputs,'output_tokens':payload['max_output_tokens'],
                                 'input_tokens_details':{'cache_write_tokens':inputs}}
            return result
    calls.transport=Partial()
    with pytest.raises(SpendStop):
        run_deterministic(state,calls,config)
    assert state.counts()=={'completed':7,'pending':1} and state.leased_count()==0
    assert ledger.totals()['reserved_nanodollars']==0
    with state.connect() as db:
        old_events=[json.loads(row[0]) for row in db.execute('SELECT event FROM calls')]
        completed={row[0] for row in db.execute("SELECT review_id FROM reviews WHERE status='completed'")}
        plan=state.artifact('routing-selection:'+state.artifact('active-routing-tranche')['id'])
    config['controls']['run_api_cap_usd']=.5
    resumed=Calls(state,ledger,MockTransport(),config,'approved-repair','resume',True,sleep=lambda _:None)
    run_deterministic(state,resumed,config)
    assert state.counts()=={'completed':8}
    with state.connect() as db:
        events=[json.loads(row[0]) for row in db.execute('SELECT event FROM calls')]
        current=state.artifact('routing-selection:'+state.artifact('active-routing-tranche')['id'])
    new=[event for event in events if event['run_id']=='approved-repair']
    assert len(new)==1 and new[0]['stage']=='fallback'
    assert not completed.intersection(new[0]['review_ids'])
    assert len(old_events)==9 and current==plan
