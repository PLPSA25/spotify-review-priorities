"""Final-hash checkpoint A/B only, paid dispatch requires explicit approval."""

import argparse
import hashlib
import json
import time
import tomllib
import uuid
from pathlib import Path

from pipeline.calls import Calls
from pipeline.checkpoint import BoundedTransport
from pipeline.checkpoint_ab_proposal import comparison
from pipeline.deterministic import run_deterministic
from pipeline.enrich import export_state
from pipeline.failure_policy import failure_window
from pipeline.prepare import atomic_json
from pipeline.providers import HTTPTransport, keys_from_env
from pipeline.scaling_report import load_state
from pipeline.schema import configuration
from pipeline.spend import Ledger
from pipeline.state import State

PASS_CRITERION = {'endpoint':'core-Jev disagreement against fixed blinded verifier on the same 500 rows',
                  'fields':['topic','intent'],'maximum_worsening_percentage_points_each':3,
                  'required_shared_rows':500,'decision':'Both fields must satisfy the limit; otherwise fail. Incomplete shared data cannot pass.'}


def assess_pass(v2, v3):
    if v2['rows']!=500 or v3['rows']!=500:
        return {'status':'inconclusive','passes':False,'reason':'Full shared 500-row criterion unavailable'}
    fields = {}
    for field in ('topic','intent'):
        old = v2['core_jev_fields'][field]['disagreements']
        new = v3['core_jev_fields'][field]['disagreements']
        fields[field] = {'v2_disagreements':old,'v3_disagreements':new,'denominator':500,
                         'change_percentage_points':(new-old)/5,'maximum_v3_disagreements':old+15,
                         'passes':new-old<=15}
    passed = all(value['passes'] for value in fields.values())
    return {'status':'pass' if passed else 'fail','passes':passed,'fields':fields,'predeclared_criterion':PASS_CRITERION}


def run(confirmed=False):
    if not confirmed:
        raise ValueError('Explicit A/B yes and --confirm-spend required')
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    plan = json.loads(Path('docs/checkpoint-500-v3-ab-proposal.json').read_text(encoding='utf-8'))
    frozen = json.loads(Path('docs/frozen-label-config.json').read_text(encoding='utf-8'))
    if plan.get('pass_criterion')!=PASS_CRITERION:
        raise ValueError('Predeclared pass criterion missing/changed')
    if configuration(config)!=plan['label_config'] or configuration(config)!=frozen['label_config']:
        raise ValueError('Final hash differs from reviewed proposal')
    if config['planning_rates']!=plan['planning_rates'] or any(config['controls'][key]!=value for key,value in plan['operational_controls'].items()):
        raise ValueError('Reviewed rates or controls changed')
    if hashlib.sha256(Path(plan['input']).read_bytes()).hexdigest()!=plan['source_sha256']:
        raise ValueError('Reviewed source changed')
    reference = Path('artifacts/checkpoint-500/verifier.json')
    if hashlib.sha256(reference.read_bytes()).hexdigest()!=plan['frozen_verifier_sha256']:
        raise ValueError('Fixed blinded reference changed')
    output = Path(plan['output'])
    if output.exists():
        raise ValueError('A/B already attempted; review before recovery')
    if plan['worst_case_usd']>.431 or plan['invocation_cap_usd']>.431 or plan['maximum_calls']>1128:
        raise ValueError('Reviewed A/B envelope changed')
    keys = keys_from_env(Path('.env'))
    ledger = Ledger(Path(config['controls']['ledger_path']),config['controls']['project_api_cap_usd'])
    totals = ledger.totals()
    worst = sum(plan['cost_bounds_nanodollars'].values())
    if totals['spent_nanodollars']+totals['reserved_nanodollars']+worst>ledger.cap:
        raise ValueError('Project headroom insufficient')
    config['controls'].update(max_workers=2,max_transient_attempts=1,run_api_cap_usd=plan['invocation_cap_usd'])
    state = State(output/'state.sqlite3',configuration(config),require_reasons=True)
    state.ingest(Path(plan['input']),Path('data/manifest.json'))
    with state.connect() as db:
        sources = {row['review_id']:json.loads(row['source']) for row in db.execute('SELECT * FROM reviews')}
        distinct = db.execute('SELECT COUNT(*) FROM work').fetchone()[0]
    if len(sources)!=500 or distinct!=479:
        raise ValueError('Reviewed sample counts changed')
    state.failure_window = failure_window(config)
    transport = BoundedTransport(HTTPTransport(keys,config['controls']['request_timeout_seconds']),config,plan,sources)
    calls = Calls(state,ledger,transport,config,str(uuid.uuid4()),'initial')
    measurement = {'status':'running','label_config':state.label_config,'run_id':calls.run_id}
    started = time.perf_counter()
    atomic_json(output/'measurements.json',measurement)
    atomic_json(output/'predeclared-pass-criterion.json',PASS_CRITERION)
    try:
        selection = run_deterministic(state,calls,config)
        atomic_json(output/'routing-selection.json',selection)
        measurement['status'] = 'completed_with_terminal_failures' if state.counts().get('quarantined') else 'completed'
    except BaseException as exc:
        measurement.update(status='failed',error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        measurement.update(wall_seconds=time.perf_counter()-started,counts=state.counts(),ledger=ledger.totals(),attempts=transport.count)
        atomic_json(output/'measurements.json',measurement)
        export_state(state,output,False,ledger)
    rows,events = load_state(output/'state.sqlite3')
    predictions = json.loads(reference.read_text(encoding='utf-8'))['predictions']
    valid_rows = [row for row in rows if row['result']]
    old_rows,old_events = load_state(Path('artifacts/checkpoint-500/state.sqlite3'))
    shared = {row['source']['review_id'] for row in valid_rows}
    report = {'v2':comparison(old_rows,old_events,predictions),'v3':comparison(rows,events,predictions),
              'paired_final_enrichment':{'v2':comparison([row for row in old_rows if row['source']['review_id'] in shared],old_events,predictions),
                                         'v3':comparison(valid_rows,events,predictions)},
              'excluded_terminal_rows':len(rows)-len(valid_rows),'label_config':state.label_config,
              'status':'A/B gate; remaining analysis_10000 was not dispatched'}
    report['pass_result'] = assess_pass(report['v2'],report['v3'])
    atomic_json(output/'paired-report.json',report)
    print(json.dumps({'measurement':measurement,'report':report},indent=2))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-spend',action='store_true')
    run(parser.parse_args().confirm_spend)
