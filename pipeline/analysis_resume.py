"""Explicitly approved eight-worker final-hash resume; stop at its gate."""
import argparse
import hashlib
import json
import time
import tomllib
import uuid
from pathlib import Path

from pipeline.calls import Calls
from pipeline.checkpoint import BoundedTransport
from pipeline.deterministic import run_deterministic
from pipeline.enrich import export_state
from pipeline.failure_policy import failure_window
from pipeline.prepare import atomic_json
from pipeline.providers import HTTPTransport, keys_from_env
from pipeline.scaling_report import load_state
from pipeline.schema import configuration
from pipeline.spend import Ledger, SpendStop
from pipeline.state import State


def run(confirmed=False, maintenance=False):
    if not confirmed:
        raise ValueError('Explicit resume approval required')
    output = Path('artifacts/analysis-10000-final')
    destination = output/'resume-measurements.json'
    previous_segment = None
    if maintenance:
        previous_segment = json.loads(destination.read_text())
        if previous_segment.get('error') != "KeyError: 'cause'" or previous_segment['pending_leases'] or previous_segment['pessimistic_cost_nanodollars']:
            raise ValueError('Not the reviewed drained audit-scan maintenance pause')
        archived = output/'resume-maintenance-segment.json'
        if archived.exists():
            raise ValueError('Maintenance continuation already attempted')
        archived.write_bytes(destination.read_bytes())
    elif destination.exists():
        raise ValueError('Resume already attempted; a new recovery gate is required')
    config = tomllib.loads(Path('config.toml').read_text())
    original = json.loads(Path('docs/analysis-10000-final-proposal.json').read_text())
    receipt = json.loads((output/'connection-recovery-report.json').read_text())
    frozen = json.loads(Path('docs/frozen-label-config.json').read_text())
    if configuration(config) != receipt['label_config'] or configuration(config) != frozen['label_config']:
        raise ValueError('Final hash changed')
    if hashlib.sha256(Path(original['input']).read_bytes()).hexdigest() != original['input_sha256']:
        raise ValueError('Analysis input changed')
    cap = 1494586788
    if receipt['remaining_invocation_cap_nanodollars'] != cap:
        raise ValueError('Reviewed remaining cap changed')
    ledger = Ledger(Path(config['controls']['ledger_path']),10)
    if ledger.totals() != (previous_segment['ledger'] if maintenance else receipt['project_ledger']):
        raise ValueError('Ledger changed since reviewed recovery')
    state = State(output/'state.sqlite3',configuration(config),require_reasons=True)
    if state.leased_count() or state.counts() != (previous_segment['counts'] if maintenance else receipt['counts']):
        raise ValueError('Recovered state changed')
    with state.connect() as db:
        sources = {r['review_id']:json.loads(r['source']) for r in db.execute('SELECT * FROM reviews')}
        pending = db.execute("SELECT COUNT(*) FROM work WHERE status='pending'").fetchone()[0]
    config['controls'].update(max_workers=8,run_api_cap_usd='1.494586788')
    plan = dict(original)
    plan.update(maximum_calls=37733-(previous_segment['new_attempts'] if maintenance else 0),per_item_call_limit=4,
                cost_bounds_nanodollars={k:2*v for k,v in original['cost_bounds_nanodollars'].items()})
    http = HTTPTransport(keys_from_env(Path('.env')),config['controls']['request_timeout_seconds'],
                         connect_timeout=config['controls']['connect_timeout_seconds'])
    transport = BoundedTransport(http,config,plan,sources)
    state.failure_window = failure_window(config)
    calls = Calls(state,ledger,transport,config,previous_segment['run_id'] if maintenance else str(uuid.uuid4()),'resume')
    if maintenance:
        with state.connect() as db:
            existing = [json.loads(r[0]) for r in db.execute('SELECT event FROM calls')]
        existing = [e for e in existing if e['run_id']==calls.run_id]
        for event in existing[-100:]:
            calls.connection_window.record(event['request_id'],event['accounting']=='pessimistic_unknown_charge')
        stop = ledger.run_stop(calls.run_id)
        if stop != {'reason':'manual_integrity_pause_remove_redundant_audit_scan','cap_hit':False}:
            raise ValueError('Not a manual non-budget stop')
        with ledger.connect() as db:
            db.execute('DELETE FROM admission_stops WHERE run_id=?',(calls.run_id,))
    measured = {'status':'running','label_config':state.label_config,'run_id':calls.run_id,
                'workers':8,'cap_nanodollars':cap,'initial_counts':state.counts(),
                'initial_pending_distinct_texts':pending,'health_window_reset':not maintenance,
                'maintenance_continuation':maintenance,
                'prior_segment_seconds':previous_segment['wall_seconds'] if maintenance else 0,
                'connect_timeout_seconds':15,'read_timeout_seconds':60,
                'cache_condition':'Resume: completed records and 79 saved new Jev results reused; provider prompt-cache billing measured, not assumed.'}
    started = time.perf_counter()
    atomic_json(destination,measured)
    try:
        selection = run_deterministic(state,calls,config)
        atomic_json(output/'routing-selection.json',selection)
        measured['status'] = 'completed_with_terminal_failures' if state.counts().get('quarantined') else 'completed'
    except SpendStop as exc:
        measured.update(status='stopped_cap' if ledger.run_stop(calls.run_id) else 'stopped_integrity',error=str(exc))
    except BaseException as exc:
        measured.update(status='failed',error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        measured.update(wall_seconds=time.perf_counter()-started,counts=state.counts(),
                        ledger=ledger.totals(),new_attempts=transport.count+(previous_segment['new_attempts'] if maintenance else 0),pending_leases=state.leased_count())
        http.close()
        _, events = load_state(state.path)
        new = [e for e in events if e['run_id']==calls.run_id]
        measured['new_api_cost_nanodollars'] = sum(e.get('cost_nanodollars',0) for e in new)
        measured['reported_usage_cost_nanodollars'] = sum(e.get('cost_nanodollars',0) for e in new if e['accounting']=='calculated_from_reported_billing_categories')
        measured['pessimistic_cost_nanodollars'] = sum(e.get('cost_nanodollars',0) for e in new if e['accounting']=='pessimistic_unknown_charge')
        measured['connection_failures_by_phase'] = {phase:sum(e.get('transport_diagnostic',{}).get('failure_phase')==phase for e in new if e.get('transport_diagnostic')) for phase in ('connect','send','post_send')}
        measured['retry_calls'] = sum(e['attempt']>1 for e in new)
        measured['new_completed_rows'] = state.counts().get('completed',0)-measured['initial_counts']['completed']
        measured['rows_per_second'] = measured['new_completed_rows']/measured['wall_seconds']
        measured['new_terminal_rows'] = state.counts().get('quarantined',0)-measured['initial_counts']['quarantined']
        atomic_json(destination,measured)
        export_state(state,output,False,ledger)
    print(json.dumps(measured,indent=2),flush=True)
    print('Analysis gate reached; no further paid work dispatched.',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-spend',action='store_true')
    parser.add_argument('--continue-maintenance',action='store_true')
    args = parser.parse_args()
    run(args.confirm_spend,args.continue_maintenance)
