import copy
import hashlib
import json

import pytest

from pipeline.calls import InvalidOutput
from pipeline.failure_policy import FailureWindow, SystemicFailure
from pipeline.phase7 import ApprovedTransport, finalize_verifier
from pipeline.phase7_work import parse_group, parse_memo, write_business
from pipeline.providers import ProviderError
from pipeline.schema import canonical
from tests.test_enrichment import environment


class CountingTransport:
    def __init__(self):
        self.count = 0

    def request(self, provider, payload):
        self.count += 1
        return {'accepted': True}


def fingerprint(payload):
    return hashlib.sha256(canonical(payload).encode()).hexdigest()


def test_guard_counts_batch_and_singleton_attempts_for_each_id(tmp_path):
    _, config, state, _, _ = environment(tmp_path, ('a', 'b'))
    root = {'model': config['models']['luna'], 'reasoning': {'effort': 'none'},
            'service_tier': 'default', 'input': 'fixed root', 'max_output_tokens': 10000}
    repair = dict(root, input='fixed repair', max_output_tokens=200)
    plan = {'sample_ids': ['0', '1'], 'batches': [{'payload_sha256': fingerprint(root), 'input_byte_token_bound': 24000}],
            'single_repairs': {'0': {'payload_sha256': fingerprint(repair), 'input_byte_token_bound': 10000}}}
    delegate = CountingTransport()
    guard = ApprovedTransport(delegate, state, 'paid', config, plan, {})

    def event(n, ids):
        state.save_call({'request_id': str(n), 'run_id': 'paid', 'role': 'verify', 'stage': 'verify',
                         'outcome': 'failed', 'review_ids': ids, 'reservation_nanodollars': 100})

    event(1, ['0', '1'])
    guard.request('openai', root)
    event(2, ['0', '1'])
    guard.request('openai', root)
    event(3, ['0'])
    guard.request('openai', repair)
    event(4, ['0'])
    guard.request('openai', repair)
    event(5, ['0'])
    with pytest.raises(ProviderError, match='Four-attempt'):
        guard.request('openai', repair)
    assert delegate.count == 4
    with pytest.raises(ProviderError, match='outside approved'):
        guard.request('openai', dict(repair, input='changed text'))
    assert delegate.count == 4


def test_guard_rejects_group_stage_reservations_before_network(tmp_path):
    _, config, state, _, _ = environment(tmp_path, ('a',))
    payload = {'model': config['models']['luna'], 'reasoning': {'effort': 'none'},
               'service_tier': 'default', 'input': 'bounded group', 'max_output_tokens': 2048}
    delegate = CountingTransport()
    guard = ApprovedTransport(delegate, state, 'paid', config,
                              {'sample_ids': [], 'batches': [], 'single_repairs': {}},
                              {'group-01': {'payload_sha256': fingerprint(payload), 'ids': ['0']}})
    state.save_call({'request_id': 'over-budget', 'run_id': 'paid', 'role': 'group', 'stage': 'group-01',
                     'outcome': 'failed', 'review_ids': ['0'], 'reservation_nanodollars': 16096001})
    with pytest.raises(ProviderError, match='stage/call bound'):
        guard.request('openai', payload)
    assert delegate.count == 0


def test_verifier_preserves_all_valid_siblings_before_monitor_stop():
    predictions, terminal, snapshots = {}, {}, []
    monitor = FailureWindow(window=10, minimum=2, threshold=.25)
    monitor.record('older', True)
    with pytest.raises(SystemicFailure):
        finalize_verifier({'a': {}, 'b': {}},
                          lambda *_: {'valid': {'a': {'topic': 'other'}, 'b': {'topic': 'other'}}, 'errors': {}},
                          predictions, terminal, monitor, lambda: snapshots.append(copy.deepcopy(predictions)))
    assert set(predictions) == {'a', 'b'}
    assert set(snapshots[-1]) == {'a', 'b'}


def test_bad_verifier_item_gets_one_semantic_repair_then_next_batch_continues():
    predictions, terminal, invocations = {}, {}, []

    def send(batch, repair):
        invocations.append((set(batch), repair))
        if repair:
            raise InvalidOutput('still malformed')
        return {'valid': {rid: {} for rid in batch if rid != 'bad'},
                'errors': {'bad': 'malformed'} if 'bad' in batch else {}}

    monitor = FailureWindow()
    finalize_verifier({'good': {}, 'bad': {}}, send, predictions, terminal, monitor, lambda: None)
    finalize_verifier({'later': {}}, send, predictions, terminal, monitor, lambda: None)
    assert set(predictions) == {'good', 'later'}
    assert set(terminal) == {'bad'}
    assert sum(repair for _, repair in invocations) == 1


def test_exhausted_connection_batch_is_terminal_without_inventing_labels():
    predictions, terminal = {}, {}

    def exhausted(*_):
        raise ProviderError('attempts exhausted', transient=True)

    finalize_verifier({'a': {}, 'b': {}}, exhausted, predictions, terminal, FailureWindow(), lambda: None)
    assert predictions == {}
    assert set(terminal) == {'a', 'b'}


def test_fine_ranking_keeps_other_first_and_full_claims_have_scope_metrics(tmp_path):
    records = {
        'a': {'review_id': 'a', 'topic': 'other', 'intent': 'complaint', 'severity': 4},
        'b': {'review_id': 'b', 'topic': 'usability', 'intent': 'complaint', 'severity': 2},
        'c': {'review_id': 'c', 'topic': 'other', 'intent': 'praise', 'severity': 1},
    }
    sources = {'a': {'review_text': 'bad'}, 'b': {'review_text': 'ads'}}
    ranking, sample, claims = write_business(records, sources, {'b', 'c'}, tmp_path)
    assert ranking[0]['issue_id'] == 'other--unspecified'
    assert ranking[0]['priority_score'] == ranking[0]['severity_sum'] == '4'
    assert sample[0]['issue_id'] == 'usability--ad-interruptions'
    by_id = {c['claim_id']: c for c in claims}
    assert by_id['scope:completed_rows']['value'] == '3'
    assert by_id['scope:unspecified_percent_rounded']['value'] == '50'
    assert by_id['sample:usability--ad-interruptions:rank']['value'] == '1'
    assert 'scope:completed_rows' not in (tmp_path/'grading_claims.csv').read_text()
    assert json.loads((tmp_path/'business-summary.json').read_text())['grouping_rule_hash']


def test_names_and_memo_reject_foreign_ids_and_unsupported_numerals():
    with pytest.raises(ValueError, match='Group IDs'):
        parse_group({'issues': [{'issue_id': 'x', 'name': 'Wrong'}]}, ['y'])
    prose = {'top_bucket_explanation': 'General dissatisfaction without a stated cause.',
             'recommended_issue_id': 'ads', 'recommendation': 'Reduce disruptive ads.',
             'random_prefix_comparison': 'Compare the sample ranking.', 'limitations': 'Partial coverage.',
             'alternatives': ['Investigate playback.'], 'claim_ids': ['scope:coverage']}
    assert parse_memo(prose, 'ads', {'scope:coverage'}) == prose
    with pytest.raises(ValueError, match='numeric digits'):
        parse_memo(dict(prose, recommendation='Cut ads by 20 percent.'), 'ads', {'scope:coverage'})
    with pytest.raises(ValueError, match='foreign claims'):
        parse_memo(dict(prose, claim_ids=['invented']), 'ads', {'scope:coverage'})
    with pytest.raises(ValueError, match='undeclared or foreign'):
        parse_memo(dict(prose, recommendation='Reduce ads. [invented]'), 'ads', {'scope:coverage'})


def test_owner_v2_hold_blocks_all_paid_stages_before_preparation(monkeypatch):
    from pathlib import Path

    from pipeline.phase7 import run

    monkeypatch.setattr('pipeline.phase7.prepare', lambda: pytest.fail('Must not prepare or dispatch while owner hold is active'))
    assert Path('docs/phase7-review-gate.json').is_file()
    monkeypatch.setattr('pipeline.phase7.read_json', lambda _: {'status': 'hold_all_paid_stages'})
    with pytest.raises(ValueError, match='offline v2 cohort review'):
        run(True)
    with pytest.raises(ValueError, match='offline v2 cohort review'):
        run(True, memo=True, spotcheck_reviewed=True)


def test_memo_renders_saved_baseline_and_prefix_claims(tmp_path, monkeypatch):
    from pipeline.phase7 import render_memo

    records = {
        'a': {'review_id': 'a', 'topic': 'other', 'intent': 'complaint', 'severity': 4},
        'b': {'review_id': 'b', 'topic': 'usability', 'intent': 'complaint', 'severity': 2},
    }
    business = write_business(records, {'a': {'review_text': 'bad'}, 'b': {'review_text': 'ads'}}, {'b'}, tmp_path/'work')
    (tmp_path/'docs').mkdir()
    issue = 'usability--ad-interruptions'
    with monkeypatch.context() as context:
        context.chdir(tmp_path)
        render_memo({'recommended_issue_id': issue, 'top_bucket_explanation': 'No stated cause.',
                     'recommendation': 'Investigate interruptions.', 'random_prefix_comparison': 'Compare views.',
                     'limitations': 'Partial coverage.', 'alternatives': []}, business, {issue: 'Ad interruptions'})
    text = (tmp_path/'docs/phase7-memo-draft.md').read_text(encoding='utf-8')
    assert '2 [`usability--ad-interruptions:rank`]' in text
    assert '1 [`sample:usability--ad-interruptions:rank`]' in text
    assert 'out-of-prefix cache propagation' in text
    assert '[claims.csv](phase7/claims.csv)' in text
