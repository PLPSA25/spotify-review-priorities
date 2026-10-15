"""Approved 500-row blinded v3 transfer verifier, with immutable paid bounds."""

import argparse
import hashlib
import json
import time
import tomllib
import uuid
from pathlib import Path

from pipeline.calls import Calls
from pipeline.checkpoint import BoundedTransport, verifier_payload
from pipeline.classify import parse_luna_batch
from pipeline.enrich import export_state
from pipeline.failure_policy import failure_window
from pipeline.prepare import atomic_json
from pipeline.providers import HTTPTransport, keys_from_env
from pipeline.schema import canonical, configuration
from pipeline.spend import Ledger, token_cost
from pipeline.state import State
from pipeline.verify_policy import finalize_batch

ROOT = Path('artifacts/scaling')
OUTPUT = ROOT / 'transfer-verifier'


def diagnostic_payload(batch, config, repair=False):
    payload = verifier_payload(batch, config)
    schema = payload['text']['format']['schema']['properties']['records']['items']
    schema['properties'].update(language={'type': 'string', 'enum': ['english', 'nonenglish_understood', 'not_understood']},
                                missing_context={'type': 'boolean'})
    schema['required'] += ['language', 'missing_context']
    payload['instructions'] += (' Independently return language: english for understandable English, '
                                'nonenglish_understood for understandable non-English/mixed text, '
                                'not_understood if insufficiently understood. Return missing_context=true '
                                'only when missing context prevents supported topic or impact judgment.')
    payload['max_output_tokens'] = 200 if repair else 200 * len(batch)
    if repair:
        payload['input'] += '\nREPAIR: Return all required fields and an exact nonempty quote of at most 80 characters, preserving spelling and whitespace.'
    return payload


def preflight(config):
    proposal = json.loads((ROOT / 'verifier-transfer-proposal.json').read_text(encoding='utf-8'))
    if configuration(config) != proposal['label_config']:
        raise ValueError('Frozen configuration changed')
    if OUTPUT.exists():
        raise ValueError('Transfer output exists; review before any recovery')
    helper_path = Path('data/golden_50_to_label.csv')
    import csv
    with helper_path.open(encoding='utf-8-sig', newline='') as handle:
        golden = {row['review_id'] for row in csv.DictReader(handle)}
    sources = {}
    from pipeline.scaling_report import load_state
    for workers in (1, 2, 8):
        rows, _ = load_state(ROOT / f'workers-{workers}/state.sqlite3')
        for row in rows:
            if row['result'] and row['source']['review_id'] in proposal['sample_ids']:
                sources[row['source']['review_id']] = row['source']
    if len(sources) != 500 or set(sources) != set(proposal['sample_ids']) or set(sources) & golden:
        raise ValueError('Sample scope changed or golden overlap')
    ordered = [sources[rid] for rid in proposal['sample_ids']]
    batches = [ordered[start:start+50] for start in range(0, 500, 50)]
    payloads = [(diagnostic_payload(batch, config), 24000) for batch in batches]
    payloads += [(diagnostic_payload([source], config, True), 10000) for source in ordered]
    for payload, bound in payloads:
        if len(canonical(payload).encode()) + config['controls']['token_overhead_bound'] > bound:
            raise ValueError('Diagnostic verifier input exceeds approved envelope')
    rates = dict(config['planning_rates'])
    rates['luna_input_per_million'] = max(rates['luna_input_per_million'], rates['luna_cache_write_per_million'])
    worst = 10 * token_cost(24000, 10000, rates, 'openai') + 500 * token_cost(10000, 200, rates, 'openai')
    if worst > 755000000 or proposal['maximum_calls'] != 510:
        raise ValueError('Approved cost/call limits changed')
    return proposal, sources, batches, worst


def run(confirmed=False):
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    proposal, sources, batches, worst = preflight(config)
    print(json.dumps({'mode': 'approved paid run' if confirmed else 'offline preflight',
                      'initial_calls': 10, 'maximum_calls': 510, 'worst_case_usd': worst/1e9,
                      'diagnostics': ['language', 'missing_context'], 'frozen_label_config': configuration(config)}), flush=True)
    if not confirmed:
        return
    keys = keys_from_env(Path('.env'))
    config['controls'].update(run_api_cap_usd=.755, max_transient_attempts=1)
    ledger = Ledger(Path(config['controls']['ledger_path']), config['controls']['project_api_cap_usd'])
    totals = ledger.totals()
    if totals['spent_nanodollars'] + totals['reserved_nanodollars'] + worst > ledger.cap:
        raise ValueError('Insufficient project headroom')
    state = State(OUTPUT / 'state.sqlite3', configuration(config))
    state.ingest(ROOT / 'verifier-transfer-sample.csv', Path('data/manifest.json'))
    plan = {'maximum_calls': 510, 'cost_bounds_nanodollars': {'jev': 0, 'luna_enrich': 0, 'verify': worst}}
    transport = BoundedTransport(HTTPTransport(keys, config['controls']['request_timeout_seconds']), config, plan, sources)
    calls = Calls(state, ledger, transport, config, str(uuid.uuid4()), 'initial')
    predictions, terminal = {}, {}
    monitor = failure_window(config)
    measurement = {'run_id': calls.run_id, 'status': 'running', 'worst_case_usd': worst/1e9,
                   'sample_digest': hashlib.sha256(canonical(proposal['sample_ids']).encode()).hexdigest(),
                   'label_config': state.label_config}
    started = time.perf_counter()
    atomic_json(OUTPUT / 'measurements.json', measurement)

    def persist():
        atomic_json(OUTPUT / 'verifier.json', {'predictions': predictions, 'terminal_failures': terminal,
                    'complete': len(predictions)+len(terminal)==500, 'all_valid': len(predictions)==500})

    def send(batch, repair):
        return calls.invoke('openai', diagnostic_payload(list(batch.values()), config, repair), list(batch),
                            'verify', lambda reply: parse_luna_batch(reply, batch, {rid: {} for rid in batch},
                            False, state.label_config, verifier_diagnostics=True), role='verify',
                            prompt_version='blinded-transfer-diagnostics-v1', schema_version='verify-diagnostics-v1',
                            repair_output=False)

    try:
        for rows in batches:
            batch = {row['review_id']: row for row in rows}
            finalize_batch(batch, send, predictions, terminal, monitor, persist)
            print(f'Transfer verifier: {len(predictions)} valid, {len(terminal)} terminal /500', flush=True)
        measurement['status'] = 'completed_with_terminal_failures' if terminal else 'completed'
    except BaseException as exc:
        measurement.update(status='failed', error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        persist()
        measurement.update(wall_seconds=time.perf_counter()-started, valid_predictions=len(predictions),
                           terminal_failures=len(terminal), attempts=transport.count, ledger=ledger.totals())
        atomic_json(OUTPUT / 'measurements.json', measurement)
        export_state(state, OUTPUT, False, ledger)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-spend', action='store_true')
    run(parser.parse_args().confirm_spend)
