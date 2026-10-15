"""Approved-only 1/2/8 worker slices; stop before the remaining analysis_10000."""

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
from pipeline.schema import configuration
from pipeline.spend import Ledger
from pipeline.state import State


def run(confirmed, plan_path=Path('artifacts/scaling-proposal/plan.json')):
    if not confirmed:
        raise ValueError('Scaling requires new explicit yes and --confirm-spend')
    plan=json.loads(plan_path.read_text(encoding='utf-8'))
    config=tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    frozen=json.loads(Path('docs/frozen-label-config.json').read_text(encoding='utf-8'))
    if configuration(config)!=plan['frozen_label_config'] or plan['frozen_label_config']!=frozen['label_config']:
        raise ValueError('Frozen config changed; obtain revised approval')
    if plan['planning_rates']!=config['planning_rates'] or any(config['controls'][key]!=value for key,value in plan['operational_controls'].items()):
        raise ValueError('Reviewed rates/controls changed')
    for proposed in plan['slices']:
        if hashlib.sha256(Path(proposed['csv']).read_bytes()).hexdigest()!=proposed['sha256']:
            raise ValueError('Reviewed slice bytes changed')
        path=Path('artifacts/scaling')/f"workers-{proposed['workers']}"
        if (path/'state.sqlite3').exists() or (path/'measurements.json').exists():
            raise ValueError('Scaling output already exists; review before a resume or new experiment')
    keys=keys_from_env(Path('.env'))
    ledger=Ledger(Path(config['controls']['ledger_path']),config['controls']['project_api_cap_usd'])
    totals=ledger.totals()
    if (totals['spent_nanodollars']+totals['reserved_nanodollars'])/1e9+plan['total_existing_config_envelope_usd']>config['controls']['project_api_cap_usd']:
        raise ValueError('Reviewed scaling envelopes exceed current project headroom')
    for proposed in plan['slices']:
        workers=proposed['workers']
        output=Path('artifacts/scaling')/f'workers-{workers}'
        state=State(output/'state.sqlite3',configuration(config))
        state.ingest(Path(proposed['csv']),Path('data/manifest.json'))
        with state.connect() as db:
            sources={row['review_id']:json.loads(row['source']) for row in db.execute('SELECT * FROM reviews')}
        config['controls'].update(max_workers=workers,max_transient_attempts=1,
                                  run_api_cap_usd=proposed['existing_config_enrichment_envelope_usd'])
        state.failure_window=failure_window(config)
        transport=BoundedTransport(HTTPTransport(keys,config['controls']['request_timeout_seconds']),config,proposed,sources)
        calls=Calls(state,ledger,transport,config,str(uuid.uuid4()),'initial')
        measurements={'workers':workers,'label_config':state.label_config,'input_sha256':proposed['sha256'],
                      'result_cache':'cold empty; no cross-slice reuse','status':'running','run_id':calls.run_id}
        started=time.perf_counter()
        atomic_json(output/'measurements.json',measurements)
        try:
            selection=run_deterministic(state,calls,config)
            atomic_json(output/'routing-selection.json',selection)
            measurements.update(status='completed_with_terminal_failures' if state.counts().get('quarantined') else 'completed',
                                enrichment_seconds=time.perf_counter()-started)
            class NoDispatch:
                def request(self,provider,payload):
                    raise AssertionError('Warm replay must not dispatch')
            warm=time.perf_counter()
            warm_calls=Calls(state,ledger,NoDispatch(),config,str(uuid.uuid4()),'resume')
            assert run_deterministic(state,warm_calls,config) is None
            measurements.update(warm_seconds=time.perf_counter()-warm,warm_new_calls=0)
        except BaseException as exc:
            measurements.update(status='failed',error=type(exc).__name__+': '+str(exc))
            raise
        finally:
            measurements.update(wall_seconds=time.perf_counter()-started,counts=state.counts(),attempts=transport.count,ledger=ledger.totals())
            atomic_json(output/'measurements.json',measurements)
            export_state(state,output,False,ledger)
        print(f"Scaling slice {workers} workers saved: {state.counts()}",flush=True)
    print('Scaling gate reached; remaining analysis_10000 work was not dispatched.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-spend',action='store_true')
    args=parser.parse_args()
    run(args.confirm_spend)
