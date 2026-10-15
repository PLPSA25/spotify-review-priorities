"""Execute only the reviewed checkpoint-500 enrichment and blinded verification."""

import argparse
import copy
import json
import threading
import time
import tomllib
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pipeline.batching import enrich_batch
from pipeline.calls import Calls
from pipeline.classify import jev_payload, luna_batch_payload, luna_payload, parse_luna_batch
from pipeline.enrich import export_state
from pipeline.failure_policy import failure_window
from pipeline.pilot_stages import completed_records
from pipeline.prepare import atomic_json, course_helper
from pipeline.providers import HTTPTransport, ProviderError, keys_from_env
from pipeline.schema import canonical, configuration
from pipeline.spend import Ledger, fallback_quota, token_cost
from pipeline.state import State
from pipeline.verify_policy import finalize_batch


class BoundedTransport:
    """Enforce the reviewed per-stage envelope atomically before network dispatch."""

    def __init__(self, delegate, config, plan, sources):
        self.delegate, self.config, self.plan = delegate, config, plan
        self.lock = threading.Lock()
        self.costs = dict.fromkeys(plan['cost_bounds_nanodollars'], 0)
        self.count = 0
        self.attempts = {}
        self.single_bounds = {}
        for rid, source in sources.items():
            for provider, payload in [('typesafe', jev_payload(source['review_text'], config)),
                                      ('openai', luna_payload(source, {}, config, False))]:
                self.single_bounds[provider, rid] = len(canonical(payload).encode()) + config['controls']['token_overhead_bound'] + 1024

    def request(self, provider, payload):
        if provider == 'typesafe':
            stage = 'jev'
            ids = [payload['state']['review_text']]
            text = ids[0]
            # The source text alone is enough to select the reviewed input envelope.
            expected = jev_payload(text, self.config)
            bound = len(canonical(expected).encode()) + self.config['controls']['token_overhead_bound'] + 1024
        else:
            stage = 'verify' if 'TASK: blinded verification' in payload['input'] else 'luna_enrich'
            packed = payload['input'].split('BEGIN_UNTRUSTED_REVIEWS_JSON\n', 1)[1].split('\nEND_UNTRUSTED_REVIEWS_JSON', 1)[0]
            rows = json.loads(packed)
            ids = [row['review_id'] for row in rows]
            if len(ids) != len(set(ids)):
                raise ProviderError('Duplicate bounded input ID', known_uncharged=True)
            bound = (24000 if len(ids) > 1 else 10000) if stage == 'verify' else sum(self.single_bounds['openai', rid] for rid in ids)
            if payload['max_output_tokens'] > 200 * len(ids):
                raise ProviderError('Output exceeds approved bound', known_uncharged=True)
        inputs = len(canonical(payload).encode()) + self.config['controls']['token_overhead_bound']
        if inputs > bound:
            raise ProviderError('Input exceeds approved bound', known_uncharged=True)
        rates = dict(self.config['planning_rates'])
        rates['luna_input_per_million'] = max(rates['luna_input_per_million'], rates['luna_cache_write_per_million'])
        reservation = token_cost(inputs, payload.get('max_output_tokens', 0), rates, provider)
        with self.lock:
            if self.count >= self.plan['maximum_calls'] or self.costs[stage] + reservation > self.plan['cost_bounds_nanodollars'][stage]:
                raise ProviderError('Approved stage envelope exhausted', known_uncharged=True)
            if any(self.attempts.get((stage, rid), 0) >= self.plan.get('per_item_call_limit', 2) for rid in ids):
                raise ProviderError('Approved per-item attempts exhausted', known_uncharged=True)
            self.count += 1
            self.costs[stage] += reservation
            for rid in ids:
                self.attempts[stage, rid] = self.attempts.get((stage, rid), 0) + 1
        return self.delegate.request(provider, payload)


def verifier_payload(batch, config):
    role_config = copy.deepcopy(config)
    role_config['enrichment']['batch_size'] = 50
    role_config['models']['output_token_cap'] = 10000
    labels = {source['review_id']: {} for source in batch}
    payload = luna_batch_payload([{'source': source} for source in batch], labels, role_config, False)
    payload['input'] = payload['input'].replace('independent fallback classification', 'blinded verification', 1)
    return payload


def run(config_path, approved_path, output, confirmed):
    if not confirmed:
        raise ValueError('Explicit spend approval required')
    config = tomllib.loads(config_path.read_text(encoding='utf-8'))
    plan = json.loads(approved_path.read_text(encoding='utf-8'))
    if configuration(config) != plan['config_hash'] or plan['total_worst_case_nanodollars'] > 1140000000:
        raise ValueError('Reviewed configuration/budget changed')
    state = State(output / 'state.sqlite3', configuration(config))
    with state.connect() as db:
        if db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]:
            raise ValueError('Existing paid attempts: review before any resume')
    state.ingest(Path('data/checkpoint_500.csv'), Path('data/manifest.json'))
    with state.connect() as db:
        sources = {row['review_id']: json.loads(row['source']) for row in db.execute('SELECT * FROM reviews')}
        distinct = db.execute('SELECT COUNT(*) FROM work').fetchone()[0]
    if len(sources) != 500 or distinct != plan['distinct_texts']:
        raise ValueError('Reviewed source counts changed')
    helper = course_helper(Path('data/check_submission.py'))
    golden_ids = {row['review_id'] for row in helper.csv_rows(Path('data/golden_50_to_label.csv'))}
    verify_ids = sorted(set(sources) - golden_ids)
    if len(verify_ids) != 500:
        raise ValueError('Reviewed verifier scope changed')
    # Check every verifier batch before any paid call.
    for start in range(0, 500, 50):
        payload = verifier_payload([sources[rid] for rid in verify_ids[start:start + 50]], config)
        if len(canonical(payload).encode()) + config['controls']['token_overhead_bound'] > 24000:
            raise ValueError('Verifier batch exceeds reviewed input envelope')
    ledger = Ledger(Path(config['controls']['ledger_path']), config['controls']['project_api_cap_usd'])
    config['controls'].update(max_workers=2, max_transient_attempts=1, run_api_cap_usd=1.14)
    transport = BoundedTransport(HTTPTransport(keys_from_env(Path('.env')), config['controls']['request_timeout_seconds']), config, plan, sources)
    calls = Calls(state, ledger, transport, config, str(uuid.uuid4()), 'initial')
    quota = fallback_quota(distinct, config['controls']['fallback_fraction'])
    state.failure_window = failure_window(config)
    started = time.perf_counter()
    measurements = {'workers': 2, 'cache_condition': plan['cache_condition'], 'label_config': state.label_config,
                    'run_id': calls.run_id, 'approved_cap_usd': 1.14, 'status': 'running'}
    atomic_json(output / 'measurements.json', measurements)

    def worker():
        while not calls.stop.is_set():
            items = []
            for _ in range(config['enrichment']['batch_size']):
                item = state.claim(config['controls']['lease_seconds'])
                if item is not None:
                    items.append(item)
            if not items:
                return
            try:
                enrich_batch(state, calls, items, config, quota)
            except BaseException:
                calls.stop.set()
                raise
            print(f'Saved checkpoint progress: {state.counts()}', flush=True)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]
            for future in futures:
                future.result()
        measurements['enrichment_seconds'] = time.perf_counter() - started
        if state.counts().get('pending', 0):
            raise ValueError('Unresolved pending work: cannot proceed')
        _, completed_sources = completed_records(state)
        verify_ids = [rid for rid in verify_ids if rid in completed_sources]
        verify_started = time.perf_counter()
        predictions = {}
        terminal = {}
        verifier_monitor = failure_window(config)
        def persist_verifier():
            atomic_json(output / 'verifier.json', {'complete': False, 'predictions': predictions, 'terminal_failures': terminal})

        def send_verifier(batch, repair):
            return calls.invoke('openai', verifier_payload(list(batch.values()), config), list(batch),
                                'checkpoint-verify-repair' if repair else 'checkpoint-verify',
                                lambda reply: parse_luna_batch(reply, batch, {rid: {} for rid in batch}, False, state.label_config),
                                role='verify', prompt_version='blinded-v1', repair_output=False)
        for start in range(0, len(verify_ids), 50):
            batch = {rid: sources[rid] for rid in verify_ids[start:start + 50]}
            finalize_batch(batch, send_verifier, predictions, terminal, verifier_monitor, persist_verifier)
            print(f'Saved blinded verifier: {len(predictions)}/500', flush=True)
        measurements['verification_seconds'] = time.perf_counter() - verify_started
        atomic_json(output / 'verifier.json', {'complete': len(predictions)+len(terminal) == len(verify_ids), 'all_valid': len(predictions)==len(verify_ids),
                                             'terminal_failures': terminal, 'predictions': predictions,
                                             'sample_ids': verify_ids, 'procedure': 'Original text and rubric only; golden excluded.'})
        measurements['status'] = 'completed_with_terminal_failures' if terminal or state.counts().get('quarantined') else 'completed'
    except BaseException as exc:
        measurements.update(status='failed', error=type(exc).__name__ + ': ' + str(exc))
        raise
    finally:
        measurements['end_to_end_seconds'] = time.perf_counter() - started
        measurements['counts'] = state.counts()
        measurements['ledger'] = ledger.totals()
        measurements['attempts'] = transport.count
        atomic_json(output / 'measurements.json', measurements)
        export_state(state, output, False, ledger)
    records, _ = completed_records(state)
    print(f'Checkpoint complete: {len(records)} records, no subsequent stage dispatched.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('config.toml'))
    parser.add_argument('--approved-plan', type=Path, default=Path('docs/checkpoint-500-proposal.json'))
    parser.add_argument('--output', type=Path, default=Path('artifacts/checkpoint-500'))
    parser.add_argument('--confirm-spend', action='store_true')
    args = parser.parse_args()
    run(args.config, args.approved_plan, args.output, args.confirm_spend)
