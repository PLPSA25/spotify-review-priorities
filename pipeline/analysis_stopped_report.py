"""Offline stopped-run accounting and explicitly provisional 100k projections."""

import csv
import itertools
import json
import sqlite3
import tomllib
from contextlib import closing
from pathlib import Path

from pipeline.prepare import atomic_json
from pipeline.scaling_report import load_state
from pipeline.schema import configuration


def report():
    directory=Path('artifacts/analysis-10000-final')
    measured=json.loads((directory/'measurements.json').read_text(encoding='utf-8'))
    config=tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    if measured['status']!='failed' or 'outcome unknown' not in measured.get('error','') or measured['label_config']!=configuration(config):
        raise ValueError('No stopped matching-hash measurement')
    rows,events=load_state(directory/'state.sqlite3')
    new=[event for event in events if event['run_id']==measured['run_id']]
    valid=[event for event in new if event['stage']=='jev' and event['outcome']=='succeeded']
    unknown=[event for event in new if not event.get('reservation_settled')]
    _,base_events=load_state(Path('artifacts/checkpoint-500-v3-ab/state.sqlite3'))
    with Path('artifacts/sampling/permutation.csv').open(encoding='utf-8',newline='') as handle:
        scope_ids={row['review_id'] for row in itertools.islice(csv.DictReader(handle),config['scope']['sample_size'])}
    with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig',newline='') as handle:
        scope_ids|={row['review_id'] for row in csv.DictReader(handle)}
    with closing(sqlite3.connect('file:artifacts/ingestion/state.sqlite3?mode=ro',uri=True)) as db:
        scope_texts={text for rid,text in db.execute('SELECT review_id,review_text FROM reviews') if rid in scope_ids}
    completed={row['source']['review_text'] for row in rows if row['result']}
    with closing(sqlite3.connect(f'file:{directory.as_posix()}/state.sqlite3?mode=ro',uri=True)) as db:
        terminal={text for text, in db.execute("SELECT text FROM work WHERE status='quarantined'")}
        integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
    pending_scope=len(scope_texts-completed-terminal)
    jev_per_text=sum(event['cost_nanodollars'] for event in valid)/1e9/len(valid)
    luna_per_text=sum(event.get('cost_nanodollars',0) for event in base_events if event['stage']!='jev')/1e9/479
    # Only an older same-Jev/older-Luna complete 8-worker measurement is available.
    older8=json.loads(Path('artifacts/scaling/workers-8/measurements.json').read_text(encoding='utf-8'))
    previous_throughput=1000/older8['enrichment_seconds']
    result={'status':'stopped_provider_unknown_charge; no resume','label_config':configuration(config),
        'approved_invocation_cap_usd':1.5,'cap_hit':False,'error':measured.get('error'),
        'wall_seconds':measured['wall_seconds'],'workers':8,'counts':measured['counts'],
        'new_completed_rows':measured['counts'].get('completed',0)-measured['initial_counts']['completed'],
        'new_completed_rows_per_second':(measured['counts'].get('completed',0)-measured['initial_counts']['completed'])/measured['wall_seconds'],
        'valid_new_jev_results':len(valid),'valid_new_jev_results_per_second':len(valid)/measured['wall_seconds'],
        'new_terminal_failures':measured['counts'].get('quarantined',0)-measured['initial_counts']['quarantined'],
        'new_attempts':len(new),'known_new_api_cost_usd':measured['new_api_cost_usd'],
        'unknown_calls':len(unknown),'unknown_reservation_usd':measured['ledger']['reserved_nanodollars']/1e9,
        'unknown_request_ids':[event['request_id'] for event in unknown],
        'unknown_review_ids':[rid for event in unknown for rid in event['review_ids']],
        'retained_unknown_leases':measured['pending_leases'],'sqlite_integrity':integrity,
        'project_spend_usd':measured['ledger']['spent_nanodollars']/1e9,
        'project_committed_usd':(measured['ledger']['spent_nanodollars']+measured['ledger']['reserved_nanodollars'])/1e9,
        'projection':{'status':'provisional; analysis did not complete and connectivity must be reconciled',
            'scope_ids':len(scope_ids),'scope_distinct_texts':len(scope_texts),
            'completed_same_hash_scope_texts':len(completed&scope_texts),'terminal_scope_texts':len(terminal&scope_texts),
            'remaining_scope_distinct_texts':pending_scope,
            'jev_unit_cost_source':'79 newly reported successful calls; unknown charges excluded, not treated as zero',
            'luna_unit_cost_source':'Last complete final-hash A/B enrichment, including failures, divided by 479 attempted texts',
            'jev_api_cost_per_text':jev_per_text,'luna_api_cost_per_text':luna_per_text,
            'scope_no_reuse_enrichment_base_usd':len(scope_texts)*(jev_per_text+luna_per_text),
            'scope_incremental_enrichment_base_usd':pending_scope*(jev_per_text+luna_per_text),
            'scope_incremental_enrichment_50pct_allowance_usd':pending_scope*(jev_per_text+luna_per_text)*1.5,
            'prior_complete_eight_worker_texts_per_second':previous_throughput,
            'time_basis_label_config':older8['label_config'],
            'scope_incremental_enrichment_hours_using_prior_eight_worker_rate':pending_scope/previous_throughput/3600,
            'time_limitation':'Older measurement uses Jev-v3 but older Luna-v1/flag hash; not a current final-hash complete eight-worker measurement. No defensible refreshed operational timing from the interrupted 26-second run. Time excludes verification/group/memo and retries beyond measured mix.',
            'cost_limitation':'Assumes input/routing/cache mix transfers. These are estimates, not a paid envelope; excludes finishing analysis_10000, future verifier/group/memo and unresolved bills.'},
        'resume_gate':'Reconcile seven unknown provider outcomes/charges before releasing their held work; no automatic retry or resume. Same hash, valid saved Jev stages and completed provenance are preserved.'}
    atomic_json(directory/'stopped-gate-report.json',result)
    print(json.dumps({key:value for key,value in result.items() if key not in {'unknown_request_ids','unknown_review_ids'}},indent=2))


if __name__=='__main__':
    report()
