"""Offline recovery receipt and resume proposal. No credential loading or network."""
import json
import tomllib
from pathlib import Path

from pipeline.connection_recovery import resolve
from pipeline.enrich import export_state
from pipeline.prepare import atomic_json
from pipeline.schema import configuration
from pipeline.spend import Ledger
from pipeline.state import State


def run():
    output = Path('artifacts/analysis-10000-final')
    config = tomllib.loads(Path('config.toml').read_text())
    old = json.loads((output/'stopped-gate-report.json').read_text())
    state = State(output/'state.sqlite3', old['label_config'], require_reasons=True)
    if configuration(config) != old['label_config']:
        raise ValueError('Frozen hash changed')
    ledger = Ledger(Path(config['controls']['ledger_path']), 10)
    receipts = resolve(state, ledger, old['unknown_request_ids'])
    export_state(state, output, False, ledger)
    spent = round(old['known_new_api_cost_usd']*1e9) + sum(r['charged_nanodollars'] for r in receipts)
    report = {'status':'offline recovery complete; resume awaiting yes',
              'label_config':state.label_config, 'receipts':receipts,
              'invocation_accounted_nanodollars':spent,
              'remaining_invocation_cap_nanodollars':1500000000-spent,
              'project_ledger':ledger.totals(), 'counts':state.counts(),
              'remaining_leases':state.leased_count(),
              'diagnosis':{'provider':'typesafe','endpoint':'https://api.typesafe.ai/v1/systemone',
                           'saved_exception_type':'ProviderError',
                           'saved_exception_message':receipts[0]['original_error'],
                           'underlying_exception':'Not retained: TimeoutError or urllib.error.URLError was replaced, from None',
                           'timestamps':'Per-call UTC timestamps were not saved. Measurement file mtime 2026-10-14T22:58:16.669065Z; run duration 26.122006s. This is an approximate run window, not exact call timestamps.',
                           'burst':'Seven adjacent dispatches 77–83; latencies 21.594–21.625s, consistent with an early-run burst rather than spread-out failures.',
                           'pool':'Shared HTTPTransport wrapper; urllib creates HTTPConnection each request and forces Connection: close. No persistent pool or configured pool size; up to eight simultaneous connections.',
                           'likely_cause':'Transient connection-establishment/network or upstream reachability failure. Similar ~21.6s timings suggest transport-level connection timeout; concurrency/TLS churn could amplify it. Exact cause unproven; no HTTP status or response received.'},
              'resume':{'workers':2,'cap_nanodollars':1500000000-spent,
                        'jev_pending_distinct_texts':7890,'saved_new_jev_results_reused':79,
                        'luna_review_id_upper_bound':1545,'fallback_quota_original_tranche':796,
                        'connection_max_attempts':3,'per_item_call_limit':4,
                        'health_window':'Explicit operator reset on new approved invocation; >5% of last100 completed calls, minimum20. Old attempt had7/86=8.14%, and remains in audit history.',
                        'call_bound':4*(7890+1545)-7,
                        'cost':'Hard maximum is remaining invocation cap, including pessimistic charges and outstanding reservations. Larger retry envelope does not authorize larger spending. Budget admission remains latched/resumable.',
                        'scope':'Only remaining analysis_10000 enrichment. No verifier, golden evaluation, 100k, grouping or memo.'}}
    atomic_json(output/'connection-recovery-report.json', report)
    atomic_json(Path('docs/analysis-10000-resume-proposal.json'), report['resume'] | {'label_config':state.label_config,'status':'awaiting explicit yes'})
    print(json.dumps({k:v for k,v in report.items() if k not in {'receipts','diagnosis'}}, indent=2))


if __name__ == '__main__':
    run()
