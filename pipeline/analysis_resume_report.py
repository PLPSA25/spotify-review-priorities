"""Offline measured resume gate and explicitly estimated 100k projection."""
import csv
import itertools
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from pipeline.prepare import atomic_json
from pipeline.scaling_report import load_state


def report():
    output = Path('artifacts/analysis-10000-final')
    measured = json.loads((output/'resume-measurements.json').read_text())
    if measured['status']=='running':
        raise ValueError('Run has not reached its gate')
    rows, events = load_state(output/'state.sqlite3')
    original = json.loads((output/'measurements.json').read_text())
    analysis = [e for e in events if e['run_id'] in {original['run_id'],measured['run_id']}]
    new = [e for e in events if e['run_id']==measured['run_id']]
    first_segment_path = output/'resume-maintenance-segment.json'
    first_segment = json.loads(first_segment_path.read_text()) if first_segment_path.exists() else None
    optimized = new[first_segment['new_attempts']:] if first_segment else new
    optimized_jev = [e for e in optimized if e['stage']=='jev' and e.get('finished_at_utc')]
    jev_seconds = (max(datetime.fromisoformat(e['finished_at_utc']) for e in optimized_jev)-min(datetime.fromisoformat(e['started_at_utc']) for e in optimized_jev)).total_seconds()
    optimized_jev_texts = len({rid for e in optimized_jev for rid in e['review_ids']})
    total_active_seconds = measured['wall_seconds']+measured.get('prior_segment_seconds',0)
    combined_rows_per_second = measured['new_completed_rows']/total_active_seconds
    with Path('artifacts/sampling/permutation.csv').open(encoding='utf-8',newline='') as stream:
        scope_ids = {r['review_id'] for r in itertools.islice(csv.DictReader(stream),100000)}
    # Original unlabeled source IDs only, never human golden labels.
    with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig',newline='') as stream:
        scope_ids |= {r['review_id'] for r in csv.DictReader(stream)}
    with closing(sqlite3.connect('file:artifacts/ingestion/state.sqlite3?mode=ro',uri=True)) as db:
        scope_texts = {text for rid,text in db.execute('SELECT review_id,review_text FROM reviews') if rid in scope_ids}
    complete = {r['source']['review_text'] for r in rows if r['result']}
    with closing(sqlite3.connect(f'file:{output.as_posix()}/state.sqlite3?mode=ro',uri=True)) as db:
        terminals = {text for (text,) in db.execute("SELECT text FROM work WHERE status='quarantined'")}
        pending = db.execute("SELECT COUNT(*) FROM work WHERE status='pending'").fetchone()[0]
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
    remaining = len(scope_texts-complete-terminals)
    # This resume has 79 valid scores saved before timing began; disclose this warm-start bias.
    finalized_distinct = measured['initial_pending_distinct_texts']-pending
    texts_per_second = finalized_distinct/measured['wall_seconds']
    # Normalize Jev stage by only texts actually scored in the optimized segment;
    # finishing stage covers the original pending tranche, including saved scores.
    finish_seconds = max(0,measured['wall_seconds']-jev_seconds)
    seconds_per_text = jev_seconds/optimized_jev_texts + finish_seconds/finalized_distinct
    cost = sum(e.get('cost_nanodollars',0) for e in analysis)/1e9
    attempted_texts = 7969
    per_text = cost/attempted_texts
    incremental = remaining*per_text
    project_spend = measured['ledger']['spent_nanodollars']/1e9
    jev = [e for e in analysis if e['stage']=='jev' and e['outcome']=='succeeded']
    reused = sum(bool(e.get('response',{}).get('_transport',{}).get('connection_reused')) for e in new)
    retry_reasons = {'previous_attempt_connection_recovery':0,'new_connection_retry':0,
                     'output_repair':0,'http_or_other_retry':0}
    previous = {}
    for event in events:
        key = (event['stage'],event['review_ids'][0])
        prior = previous.get(key)
        if event['run_id']==measured['run_id'] and event['attempt']>1:
            if prior and prior.get('accounting')=='pessimistic_unknown_charge':
                reason = 'new_connection_retry' if prior['run_id']==measured['run_id'] else 'previous_attempt_connection_recovery'
            elif prior and (str(prior.get('error','')).startswith('Invalid output:') or prior.get('invalid_review_ids')):
                reason = 'output_repair'
            else:
                reason = 'http_or_other_retry'
            retry_reasons[reason] += 1
        for rid in event['review_ids']:
            previous[event['stage'],rid] = event
    result = {'measurement':measured,'sqlite_integrity':integrity,
              'analysis_total_accounted_usd':cost,
              'original_invocation_remaining_usd':(1500000000-round(cost*1e9))/1e9,
              'successful_reused_connections':reused,
              'retry_calls_by_reason':retry_reasons,
              'combined_active_seconds_including_maintenance_segment':total_active_seconds,
              'combined_new_rows_per_second':combined_rows_per_second,
              'projection':{'scope_ids':len(scope_ids),'scope_distinct_texts':len(scope_texts),
                            'completed_scope_distinct_texts':len(complete&scope_texts),
                            'terminal_scope_distinct_texts':len(terminals&scope_texts),
                            'remaining_scope_distinct_texts':remaining,
                            'resume_finalized_distinct_texts':finalized_distinct,
                            'resume_distinct_texts_per_second':texts_per_second,
                            'optimized_jev_distinct_texts':optimized_jev_texts,
                            'optimized_jev_stage_seconds':jev_seconds,
                            'optimized_finishing_stage_seconds':finish_seconds,
                            'normalized_seconds_per_new_distinct_text':seconds_per_text,
                            '100k_incremental_enrichment_hours':remaining*seconds_per_text/3600,
                            '100k_full_scope_enrichment_hours':len(scope_texts)*seconds_per_text/3600,
                            'analysis_accounted_cost_per_distinct_text':per_text,
                            '100k_incremental_enrichment_base_usd':incremental,
                            '100k_incremental_enrichment_50pct_allowance_usd':incremental*1.5,
                            'project_total_with_incremental_base_usd':project_spend+incremental,
                            'project_total_with_incremental_50pct_allowance_usd':project_spend+incremental*1.5,
                            'jev_mean_reported_input_tokens':sum(e['input_tokens'] for e in jev)/len(jev),
                            'time_basis':'Final-hash eight-worker keep-alive timing. A maintenance pause removed a redundant audit-log scan; its first timing segment is archived. Primary combined rows/s includes both active segments (excludes maintenance downtime). Projection uses optimized-segment Jev seconds divided by texts actually scored in that segment, plus finishing seconds divided by the original pending tranche. This corrects for all saved Jev scores and avoids treating warm scores as free production throughput. Assumes production mix transfers; excludes exports and future downstream stages.',
                            'cost_basis':'Both analysis attempts, including all repairs and seven pessimistic charges, divided by 7969 new distinct texts. Assumes review lengths, routing and observed billing/cache mix transfer; 50% allowance is an estimate, not a paid envelope.',
                            'exclusions':'No verifier, golden evaluation, grouping/memo, deployment or retry of terminal scope items included.'}}
    atomic_json(output/'resume-gate-report.json',result)
    p=result['projection']
    text = f'''# Final-hash analysis resume gate

Status: {measured['status']}. Eight workers, final hash `{measured['label_config']}`. No further paid work dispatched.

Measured {measured['new_completed_rows']} new completed rows over {total_active_seconds:.3f}s of active execution: **{combined_rows_per_second:.3f} rows/s** including the initial maintenance segment. Final segment alone: {measured['wall_seconds']:.3f}s / {measured['rows_per_second']:.3f} rows/s, with saved Jev scores (warm start). Final counts: {measured['counts']}. New terminal rows: {measured['new_terminal_rows']}. Pending leases: {measured['pending_leases']}. SQLite integrity: {integrity}.

Connection failures by phase: {measured['connection_failures_by_phase']}; retries (including previous-attempt recovery): {measured['retry_calls']}; retry breakdown: {retry_reasons}; total new calls: {measured['new_attempts']}. Successful reused connections: {reused}. Per-worker HTTPS keep-alive, explicit connect/TLS timeout 15s and read/write timeout 60s; failed connections close before the next audited retry. Send failures remain charge-uncertain; no hidden resends.

Resume reported usage cost: ${measured['reported_usage_cost_nanodollars']/1e9:.9f}; pessimistic new charges: ${measured['pessimistic_cost_nanodollars']/1e9:.9f}. Resume accounted cost: ${measured['new_api_cost_nanodollars']/1e9:.9f}, below the approved $1.494586788 remaining cap. Both analysis attempts including original seven pessimistic charges: ${cost:.9f}. Project accounted spend: ${project_spend:.9f} / $10. Historical seven charges are estimated at reservation cost, not measured provider usage.

100k scope: {p['scope_ids']} IDs / {p['scope_distinct_texts']} texts; completed reuse {p['completed_scope_distinct_texts']} texts, terminal {p['terminal_scope_distinct_texts']}, remaining {remaining}. Measured resume finalization throughput: {texts_per_second:.3f} distinct texts/s. Estimated remaining 100k enrichment: {p['100k_incremental_enrichment_hours']} hours; ${incremental:.6f} base, ${incremental*1.5:.6f} with 50% allowance. Project total including current spend: ${project_spend+incremental:.6f} base / ${project_spend+incremental*1.5:.6f} with allowance.

{p['time_basis']} {p['cost_basis']} {p['exclusions']}

This is a measured development gate and an estimated production projection, not approval to start 100k. Stop here.
'''
    Path('docs/analysis-10000-resume-gate.md').write_text(text,encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    report()
