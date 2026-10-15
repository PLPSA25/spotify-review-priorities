"""Approved checkpoint scope/dispatch guards use no network."""

import json
import tomllib
from pathlib import Path

import pytest

from pipeline.calibration import disagreement
from pipeline.checkpoint import BoundedTransport, verifier_payload
from pipeline.classify import jev_payload, parse_luna_batch
from pipeline.providers import ProviderError
from pipeline.schema import canonical
from pipeline.spend import Ledger


def test_verifier_50_blinded_and_bounded():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    sources = [{'review_id': str(i), 'review_text': 'Music is good.'} for i in range(50)]
    payload = verifier_payload(sources, config)
    packed = payload['input'].split('BEGIN_UNTRUSTED_REVIEWS_JSON\n')[1].split('\nEND_UNTRUSTED_REVIEWS_JSON')[0]
    assert len(json.loads(packed)) == 50
    assert all(set(row) == {'review_id', 'review_text'} for row in json.loads(packed))
    assert payload['max_output_tokens'] == 10000
    assert config['models']['output_token_cap'] == 4096
    assert len(canonical(payload).encode()) + 2048 <= 24000


def test_attempt_and_stage_bounds_stop_before_dispatch():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    plan = {'cost_bounds_nanodollars': {'jev': 100000000, 'luna_enrich': 100000000, 'verify': 100000000}, 'maximum_calls': 100}

    class Fake:
        def __init__(self):
            self.count = 0

        def request(self, provider, payload):
            self.count += 1
            return {}

    delegate = Fake()
    transport = BoundedTransport(delegate, config, plan, {'1': {'review_id': '1', 'review_text': 'Good'}})
    payload = jev_payload('Good', config)
    transport.request('typesafe', payload)
    transport.request('typesafe', payload)
    with pytest.raises(ProviderError, match='attempts exhausted'):
        transport.request('typesafe', payload)
    assert delegate.count == 2
    oversized = jev_payload('Good', config)
    oversized['state']['validation_error'] = 'x' * 10000
    with pytest.raises(ProviderError, match='Input exceeds'):
        transport.request('typesafe', oversized)
    assert delegate.count == 2


def test_calibration_endpoint_excludes_flag_entities_and_uses_tolerance():
    first = {'topic': 'other', 'intent': 'praise', 'severity': 1, 'sentiment': .5,
             'needs_review': False, 'entities': []}
    second = {**first, 'sentiment': .75, 'needs_review': True, 'entities': ['Spotify']}
    assert disagreement(first, second) == []
    second['sentiment'] = .751
    assert disagreement(first, second) == ['sentiment']


def test_shared_ledger_does_not_borrow_other_scope_fallback_slots(tmp_path):
    ledger = Ledger(tmp_path / 'spend.sqlite3', 10)
    assert ledger.allow_fallback('pilot-text', 'pilot', 1)
    assert ledger.allow_fallback('other-text', 'checkpoint', 1)
    assert not ledger.allow_fallback('pilot-text', 'checkpoint', 1)
    assert ledger.allow_fallback('pilot-text', 'checkpoint', 2)
    assert not ledger.allow_fallback('third-text', 'checkpoint', 2)
    assert ledger.allow_fallback('pilot-text', 'checkpoint', 2)


def test_verifier_messages_select_unique_envelope_and_reject_conflicts():
    source={'review_id':'one','source_sha256':'hash','review_text':'Good music.'}
    record={'review_id':'one','topic':'other','intent':'praise','severity':1,'sentiment':1,
            'needs_review':False,'entities':[],'evidence_quote':'Good music.'}
    def block(text):
        return {'content':[{'type':'output_text','text':text}]}
    reply={'status':'completed','output':[block('Explanation.'),block(json.dumps({'records':[record]}))]}
    parsed=parse_luna_batch(reply,{'one':source},{'one':{}},False,'config')
    assert set(parsed['valid'])=={'one'}
    reply['output'].append(block(json.dumps({'records':[{**record,'topic':'catalog'}]})))
    with pytest.raises(ValueError,match='conflicting'):
        parse_luna_batch(reply,{'one':source},{'one':{}},False,'config')
