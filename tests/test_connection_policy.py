import json

import pytest

from pipeline.classify import enrich_one, luna_payload
from pipeline.connection_recovery import resolve
from pipeline.failure_policy import FailureWindow, SystemicFailure
from pipeline.providers import MockTransport, ProviderError
from tests.test_enrichment import environment


def test_unknown_retry_is_charged_and_successful(tmp_path):
    _, config, state, ledger, calls = environment(tmp_path, ('tiny',))
    delays = []
    calls.sleep = delays.append

    class Once(MockTransport):
        count = 0
        def request(self, provider, payload):
            self.count += 1
            if self.count == 1:
                raise ProviderError('connection lost', unknown_charge=True)
            return super().request(provider, payload)
    calls.transport = Once()
    enrich_one(state, calls, state.claim(300), config, 0)
    events = state.events_for('0')
    assert state.counts() == {'completed': 1}
    assert delays == [1.0]
    assert events[0]['cost_nanodollars'] == events[0]['reservation_nanodollars']
    assert events[0]['input_tokens'] is None
    assert events[0]['reservation_settled']
    assert ledger.totals()['reserved_nanodollars'] == 0
    assert events[0]['started_at_utc'] < events[0]['finished_at_utc']


def test_connection_exhaustion_quarantines_and_continues(tmp_path):
    _, config, state, ledger, calls = environment(tmp_path, ('bad', 'good'))
    class Bad(MockTransport):
        def request(self, provider, payload):
            if payload['state']['review_text'] == 'bad':
                raise ProviderError('lost', unknown_charge=True)
            return super().request(provider, payload)
    calls.transport = Bad()
    while item := state.claim(300):
        enrich_one(state, calls, item, config, 0)
    assert state.counts() == {'completed': 1, 'quarantined': 1}
    assert len(state.events_for('0')) == 3
    assert ledger.totals()['reserved_nanodollars'] == 0


def test_connection_threshold_minimum_strict_and_rolling():
    monitor = FailureWindow()
    for i in range(19):
        monitor.record(str(i), i < 2)
    with pytest.raises(SystemicFailure):
        monitor.record('19', False)
    monitor = FailureWindow()
    for i in range(20):
        monitor.record(str(i), i == 0)  # exactly 5% does not halt
    for i in range(20, 120):
        monitor.record(str(i), False)
    assert sum(monitor.outcomes) == 0


def test_offline_resolution_idempotent(tmp_path):
    _, config, state, ledger, calls = environment(tmp_path, ('tiny',))
    config['controls']['pessimistic_connection_retries'] = False
    class Lost(MockTransport):
        def request(self, provider, payload):
            raise ProviderError('lost', unknown_charge=True)
    calls.transport = Lost()
    with pytest.raises(ProviderError):
        enrich_one(state, calls, state.claim(300), config, 0)
    request = state.events_for('0')[0]['request_id']
    resolve(state, ledger, [request])
    before = ledger.totals()
    resolve(state, ledger, [request])
    assert ledger.totals() == before
    assert state.leased_count() == 0
    assert json.loads(json.dumps(state.events_for('0')[0]))['outcome'] == 'failed'


def test_luna_uses_same_unknown_accounting_and_retry(tmp_path):
    _, config, state, ledger, calls = environment(tmp_path, ('tiny',))
    source = state.claim(300)['source']
    class Once(MockTransport):
        count = 0
        def request(self, provider, payload):
            self.count += 1
            if self.count == 1:
                raise ProviderError('lost', unknown_charge=True)
            return super().request(provider, payload)
    calls.transport = Once()
    calls.invoke('openai', luna_payload(source, {}, config, False), ['0'], 'luna', lambda response: response)
    assert len(state.events_for('0')) == 2
    assert ledger.totals()['reserved_nanodollars'] == 0
    assert state.events_for('0')[0]['accounting'] == 'pessimistic_unknown_charge'


def test_call_health_halts_admissions_after_minimum(tmp_path):
    _, config, state, ledger, calls = environment(tmp_path, ('tiny',))
    class Lost(MockTransport):
        def request(self, provider, payload):
            raise ProviderError('lost', unknown_charge=True)
    calls.transport = Lost()
    for i in range(19):
        calls.connection_window.record(str(i), i == 0)
    with pytest.raises(SystemicFailure, match='2/20'):
        enrich_one(state, calls, state.claim(300), config, 0)
    assert calls.stop.is_set()
    assert len(state.events_for('0')) == 1
    assert ledger.totals()['reserved_nanodollars'] == 0
