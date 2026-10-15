"""Approved final-hash analysis extension: reuse A/B evidence, no automatic retries."""

import argparse
import hashlib
import json
import sqlite3
import time
import tomllib
import uuid
from contextlib import closing
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


def prepare_extension(base, output, label_config, source, manifest):
    if output.exists():
        raise ValueError('Analysis output exists; explicit recovery review required')
    output.mkdir(parents=True)
    with closing(sqlite3.connect(f'file:{base.as_posix()}?mode=ro',uri=True)) as original, closing(sqlite3.connect(output/'state.sqlite3')) as target:
        original.backup(target)
    state = State(output/'state.sqlite3',label_config,require_reasons=True)
    state.ingest(source,manifest)
    return state


def run(confirmed=False):
    if not confirmed:
        raise ValueError('Analysis requires new explicit yes and --confirm-spend')
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    plan = json.loads(Path('docs/analysis-10000-final-proposal.json').read_text(encoding='utf-8'))
    frozen = json.loads(Path('docs/frozen-label-config.json').read_text(encoding='utf-8'))
    if configuration(config)!=plan['label_config'] or configuration(config)!=frozen['label_config']:
        raise ValueError('Reviewed final hash changed')
    if plan['workers']!=8 or plan['planning_rates']!=config['planning_rates'] or any(config['controls'][key]!=value for key,value in plan['operational_controls'].items()):
        raise ValueError('Reviewed worker/rates/controls changed')
    for name, digest in (('input','input_sha256'),('base_state','base_state_sha256')):
        if hashlib.sha256(Path(plan[name]).read_bytes()).hexdigest()!=plan[digest]:
            raise ValueError('Reviewed source/base evidence changed')
    report_path = Path(plan['base_state']).parent/'paired-report.json'
    if hashlib.sha256(report_path.read_bytes()).hexdigest()!=plan['ab_report_sha256'] or not json.loads(report_path.read_text(encoding='utf-8'))['pass_result']['passes']:
        raise ValueError('Reviewed passing A/B report changed')
    worst = sum(plan['cost_bounds_nanodollars'].values())
    if worst>7441328042 or plan['invocation_cap_usd']!=1.50 or plan['maximum_calls']>19028:
        raise ValueError('Reviewed analysis envelope changed')
    keys = keys_from_env(Path('.env'))
    ledger = Ledger(Path(config['controls']['ledger_path']),config['controls']['project_api_cap_usd'])
    totals = ledger.totals()
    if totals['spent_nanodollars']+totals['reserved_nanodollars']+min(worst,1500000000)>ledger.cap:
        raise ValueError('Project headroom insufficient')
    output = Path(plan['output'])
    state = prepare_extension(Path(plan['base_state']),output,configuration(config),Path(plan['input']),Path('data/manifest.json'))
    expected = {'completed':plan['reusable_rows_including_exact_text_aliases'],
                'pending':plan['new_pending_rows'],'quarantined':plan['retained_terminal_rows']}
    if state.counts()!=expected:
        raise ValueError('Reviewed reuse/pending/terminal counts changed')
    with state.connect() as db:
        sources = {row['review_id']:json.loads(row['source']) for row in db.execute('SELECT * FROM reviews')}
        imported_calls = db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]
    config['controls'].update(max_workers=8,max_transient_attempts=1,run_api_cap_usd=plan['invocation_cap_usd'])
    state.failure_window = failure_window(config)
    transport = BoundedTransport(HTTPTransport(keys,config['controls']['request_timeout_seconds']),config,plan,sources)
    calls = Calls(state,ledger,transport,config,str(uuid.uuid4()),'initial')
    measurement = {'status':'running','label_config':state.label_config,'run_id':calls.run_id,
                   'workers':8,'imported_provenance_calls_not_new_charges':imported_calls,
                   'initial_counts':state.counts(),'approved_invocation_cap_usd':1.50}
    started = time.perf_counter()
    atomic_json(output/'measurements.json',measurement)
    try:
        selection = run_deterministic(state,calls,config)
        atomic_json(output/'routing-selection.json',selection)
        measurement['status'] = 'completed_with_terminal_failures' if state.counts().get('quarantined') else 'completed'
    except SpendStop as exc:
        measurement.update(status='stopped_cap' if ledger.run_stop(calls.run_id) else 'stopped_integrity',
                           error=str(exc),admission_stop=ledger.run_stop(calls.run_id))
    except BaseException as exc:
        measurement.update(status='failed',error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        measurement.update(wall_seconds=time.perf_counter()-started,counts=state.counts(),
                           ledger=ledger.totals(),new_attempts=transport.count,
                           pending_leases=state.leased_count())
        _, events = load_state(state.path)
        measurement['new_api_cost_usd'] = sum(event.get('cost_nanodollars',0) for event in events if event['run_id']==calls.run_id)/1e9
        atomic_json(output/'measurements.json',measurement)
        export_state(state,output,False,ledger)
    print(json.dumps(measurement,indent=2),flush=True)
    print('Analysis gate reached; no automatic resume, verifier, golden evaluation, 100k or downstream calls dispatched.',flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-spend',action='store_true')
    run(parser.parse_args().confirm_spend)
