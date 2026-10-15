"""Regression: stage attribution, float ties and paid-sibling salvage; offline."""
import copy

import pytest

from pipeline.batching import commit_validated
from pipeline.classify import jev_payload, parse_jev
from pipeline.deterministic import run_deterministic
from pipeline.failure_policy import FailureWindow, SystemicFailure
from pipeline.monitor_migration import split_legacy_terminal_history
from pipeline.providers import MockTransport
from tests.test_enrichment import environment, record


def test_only_float_noise_is_accepted_not_real_probability_gap(tmp_path):
    _,config,_,_,_ = environment(tmp_path)
    reply = MockTransport().request('typesafe',jev_payload('synthetic',config))
    language = reply['answers']['language']
    language.update(choice='nonenglish_understood',probabilities={
        'english':.46,'nonenglish_understood':.45999999999999996,'not_understood':.08})
    assert parse_jev(reply,.6,0,require_auxiliary=True)['nonenglish']
    language['probabilities'].update(english=.47,nonenglish_understood=.45)
    with pytest.raises(ValueError,match='highest-probability'):
        parse_jev(reply,.6,0,require_auxiliary=True)


def test_jev_failures_not_mixed_into_finalization_window(tmp_path,monkeypatch):
    texts = tuple(['bad-a','bad-b','bad-c']+[f'valid synthetic {i}' for i in range(30)])
    _,config,state,ledger,calls = environment(tmp_path,texts)
    config['controls'].update(max_workers=8,fallback_fraction=0)
    monkeypatch.setattr(ledger,'admit',lambda *args,**kwargs:0)
    state.classification_window = FailureWindow()
    for i in range(100):
        state.classification_window.record('prior-'+str(i),False)
    state.failure_window = FailureWindow()

    class BadChoices(MockTransport):
        def request(self,provider,payload):
            response = super().request(provider,payload)
            if provider=='typesafe' and payload['state']['review_text'].startswith('bad-'):
                response['answers']['topic']['choice']='invalid-topic'
            return response

    calls.transport = BadChoices()
    run_deterministic(state,calls,config)
    assert state.counts()=={'completed':30,'quarantined':3}
    assert sum(state.classification_window.outcomes)==3
    assert len(state.failure_window.outcomes)==30 and sum(state.failure_window.outcomes)==0


def test_all_valid_paid_siblings_saved_and_completed_even_when_monitor_trips(tmp_path):
    _,_,state,_,calls = environment(tmp_path,('one','two','three','four'))
    state.failure_window = FailureWindow(window=20,minimum=2)
    state.failure_window.record('prior-failed',True)
    items = [state.claim(300) for _ in range(4)]
    valid = {i['source']['review_id']:record(i['source'],state.label_config) for i in items}
    # Saved provider-success evidence predates finalization (no call dispatched).
    with state.connect() as db:
        db.executemany('INSERT INTO enrich_evidence VALUES (?)',[(rid,) for rid in valid])
    with pytest.raises(SystemicFailure):
        commit_validated(state,calls,items,valid,'extract')
    assert calls.stop.is_set()
    assert state.counts()=={'completed':4} and state.leased_count()==0
    assert all(state.stage_result(i['key'],'extract')==valid[i['source']['review_id']] for i in items)


def test_migration_is_pure_keeps_all_original_windows_and_classifier_failures():
    receipt = {'classification_window':{'outcomes':[False]*100,'seen':['bad','a','b']},
               'connection_window':{'outcomes':[False],'seen':['request']},
               'terminal_window':{'outcomes':[True,False,False],'seen':['bad','a','b']}}
    original = copy.deepcopy(receipt)
    proposal = split_legacy_terminal_history(receipt,{'bad'})
    assert receipt==original
    assert proposal['original_windows']==original
    assert proposal['classification_window']==original['classification_window']
    assert proposal['connection_window']==original['connection_window']
    assert proposal['terminal_window']=={'outcomes':[False,False],'seen':['a','b']}
    assert not proposal['applied']
    receipt['terminal_window']['outcomes']=[True,False,True]
    with pytest.raises(ValueError,match='Unrecognized history'):
        split_legacy_terminal_history(receipt,{'bad'})
