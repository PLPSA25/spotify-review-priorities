"""Explicitly approved, verifier-only recovery with per-item terminal failure policy."""

import argparse
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
from pipeline.spend import Ledger
from pipeline.state import State
from pipeline.verify_policy import finalize_batch


def run(confirmed, directory=Path('artifacts/checkpoint-500')):
    if not confirmed:
        raise ValueError('Recovery requires explicit approval and --confirm-spend')
    plan=json.loads(Path('docs/checkpoint-verifier-recovery-proposal.json').read_text(encoding='utf-8'))
    config=tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    state=State(directory/'state.sqlite3', configuration(config))
    with state.connect() as db:
        sources={row['review_id']:json.loads(row['source']) for row in db.execute('SELECT * FROM reviews')}
    saved=json.loads((directory/'verifier.json').read_text(encoding='utf-8'))
    predictions=saved['predictions']
    terminal=saved.get('terminal_failures',{})
    pending=set(sources)-set(predictions)-set(terminal)
    if pending!=set(plan['pending_review_ids']) or len(predictions)!=399:
        raise ValueError('Recovery scope changed; review before dispatch')
    if (directory/'recovery_measurements.json').exists():
        raise ValueError('Recovery already attempted; no automatic retry')
    failed=set(plan['already_attempted_failed_ids'])
    fresh=sorted(pending-failed)
    batches=[{rid:sources[rid] for rid in fresh[start:start+50]} for start in range(0,len(fresh),50)]
    batches += [{rid:sources[rid]} for rid in sorted(failed)]

    def payload_for(batch):
        payload=verifier_payload(list(batch.values()),config)
        if set(batch) & failed:
            payload['input'] += '\nQUOTE_REQUIREMENT: Copy an exact nonempty substring of review_text, at most 80 characters; preserve spelling and whitespace.'
        bound=24000 if len(batch)>1 else 10000
        if len(canonical(payload).encode())+config['controls']['token_overhead_bound']>bound:
            raise ValueError('Revised recovery payload exceeds reviewed envelope')
        return payload

    for batch in batches:
        payload_for(batch)
        for rid in batch:
            payload_for({rid:sources[rid]})
    config['controls'].update(run_api_cap_usd=.154, max_transient_attempts=1)
    ledger=Ledger(Path(config['controls']['ledger_path']),config['controls']['project_api_cap_usd'])
    limits={'maximum_calls':104,'cost_bounds_nanodollars':{'jev':0,'luna_enrich':0,'verify':153700000}}
    transport=BoundedTransport(HTTPTransport(keys_from_env(Path('.env')),config['controls']['request_timeout_seconds']),config,limits,sources)
    calls=Calls(state,ledger,transport,config,str(uuid.uuid4()),'resume')
    monitor=failure_window(config)
    for rid in sorted(predictions):
        monitor.record(rid,False)
    measurement={'run_id':calls.run_id,'status':'running','approved_cap_usd':.154,
                 'initial_valid':399,'maximum_calls':104,'worst_case_usd':.1537,
                 'terminal_policy':'>5% in last 100 finalized items, minimum 20; seeded with prior valid outcomes'}
    started=time.perf_counter()
    atomic_json(directory/'recovery_measurements.json',measurement)

    def persist():
        saved.update(predictions=predictions,terminal_failures=terminal,
                     complete=len(predictions)+len(terminal)==500,
                     all_valid=len(predictions)==500,
                     finalized_count=len(predictions)+len(terminal))
        atomic_json(directory/'verifier.json',saved)

    def send(batch,repair):
        return calls.invoke('openai',payload_for(batch),list(batch),
                            'checkpoint-verify-recovery-repair' if repair else 'checkpoint-verify-recovery-initial',
                            lambda reply:parse_luna_batch(reply,batch,{rid:{} for rid in batch},False,state.label_config),
                            role='verify',prompt_version='blinded-quote-v2' if set(batch)&failed else 'blinded-v1',
                            repair_output=False)

    try:
        for batch in batches:
            finalize_batch(batch,send,predictions,terminal,monitor,persist)
            print(f'Verifier finalized: {len(predictions)} valid, {len(terminal)} terminal /500',flush=True)
        persist()
        measurement['status']='completed_with_terminal_failures' if terminal else 'completed'
    except BaseException as exc:
        measurement.update(status='failed',error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        persist()
        measurement.update(wall_seconds=time.perf_counter()-started,valid_predictions=len(predictions),
                           terminal_failures=len(terminal),attempts=transport.count,ledger=ledger.totals())
        atomic_json(directory/'recovery_measurements.json',measurement)
        export_state(state,directory,False,ledger)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-spend',action='store_true')
    args=parser.parse_args()
    run(args.confirm_spend)
