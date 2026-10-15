"""Refresh checkpoint costs/time forecasts from measured development evidence."""

import json
from collections import Counter
from pathlib import Path

from pipeline.prepare import atomic_json


def report(directory=Path('artifacts/checkpoint-500')):
    measurements=json.loads((directory/'measurements.json').read_text(encoding='utf-8'))
    if measurements['counts'].get('completed')!=500:
        raise ValueError('No completed enrichment measurement')
    verified=json.loads((directory/'verifier.json').read_text(encoding='utf-8'))
    verify_seconds=measurements.get('verification_seconds',measurements['end_to_end_seconds']-measurements['enrichment_seconds'])
    recovery_path=directory/'recovery_measurements.json'
    recovery=json.loads(recovery_path.read_text(encoding='utf-8')) if recovery_path.exists() else None
    if recovery:
        verify_seconds += recovery['wall_seconds']
    ledger_totals=recovery['ledger'] if recovery else measurements['ledger']
    events=[json.loads(line) for line in (directory/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    records=[json.loads(line) for line in (directory/'enriched.jsonl').read_text(encoding='utf-8').splitlines()]
    roles=Counter()
    stages=Counter()
    costs=Counter()
    for event in events:
        roles[event['role']]+=1
        stages[event['stage']]+=1
        costs[event['role']]+=event.get('cost_nanodollars',0)
    fallback_ids={rid for event in events if event['stage']=='fallback' for rid in event['review_ids']}
    extract_ids={rid for event in events if event['stage']=='extract' for rid in event['review_ids']}
    models=sorted({event['model'] for event in events})
    unknown=[event['request_id'] for event in events if not event.get('reservation_settled')]
    invalid=[{'request_id':event['request_id'],'stage':event['stage'],'invalid_review_ids':event.get('invalid_review_ids',[]),'error':event.get('error')} for event in events if event.get('invalid_review_ids') or event.get('error')]
    distinct=479
    seconds=measurements['enrichment_seconds']
    scope=json.loads(Path('artifacts/sampling/scope.json').read_text(encoding='utf-8'))
    project=json.loads(Path('cost/project_budget.json').read_text(encoding='utf-8'))
    pilot_events=[json.loads(line) for line in Path('cost/pilot_calls.jsonl').read_text(encoding='utf-8').splitlines()]
    fixed=sum(event.get('cost_nanodollars',0) for event in pilot_events if event['role'] in {'group','memo'} and event['outcome']=='succeeded')/1e9
    # Existing union count includes development and saved sample; unmeasured length/mix assumptions remain.
    remaining=project['distinct_text_union']-distinct
    enrich_per_text=costs['enrich']/1e9/distinct
    verify_pass=costs['verify']/1e9*500/len(verified['predictions'])
    spent=ledger_totals['spent_nanodollars']/1e9
    variable=remaining*enrich_per_text+2*verify_pass
    extra_scaling=2*8448*enrich_per_text
    projected_scope_seconds=77913/(distinct/seconds)
    result={'measured':{'run_status':measurements['status'],'verifier_complete':verified['complete'], 'valid_verifier_predictions':len(verified['predictions']),
                       'recovery_status':recovery['status'] if recovery else None,
                       'recovery_wall_seconds':recovery['wall_seconds'] if recovery else None,
                       'rows':len(records),'distinct_texts':distinct,'cache_aliases':sum('cache_source_id' in record for record in records),
                       'flagged':sum(record['needs_review'] for record in records),'workers':2,
                       'end_to_end_seconds':measurements['end_to_end_seconds'],'enrichment_seconds':seconds,
                       'verification_attempt_seconds':verify_seconds,
                       'enrichment_input_rows_per_second':500/seconds,'enrichment_distinct_texts_per_second':distinct/seconds,
                       'end_to_end_rows_per_second':500/measurements['end_to_end_seconds'],
                       'pilot_end_to_end_rows_per_second':100/58.622409100004006,
                       'pilot_enrichment_seconds':None,'comparison':'Same cold result cache, different review sets and verification scope; no isolated worker speedup claim.',
                       'roles':dict(roles),'stages':dict(stages),'models':models,'fallback_distinct_ids':len(fallback_ids),'extraction_distinct_ids':len(extract_ids),
                       'cost_by_role_usd':{role:value/1e9 for role,value in costs.items()},'checkpoint_spend_usd':sum(costs.values())/1e9,
                       'project_spend_usd':spent,'project_reserved_usd':ledger_totals['reserved_nanodollars']/1e9,
                       'unresolved_request_ids':unknown,'invalid_output_events':invalid},
            'estimated':{'scope_distinct_texts':77913,'scope_enrichment_seconds_no_reuse':projected_scope_seconds,
                         'verification_500_seconds':verify_seconds if verified['complete'] else None,
                         'scope_model_seconds_excluding_unmeasured_fixed_overhead':projected_scope_seconds+verify_seconds if verified['complete'] else None,
                         'scope_enrichment_seconds_50pct_slowdown':1.5*projected_scope_seconds,
                         'remaining_project_variable_api_usd':variable,'remaining_fixed_two_group_memo_usd':2*fixed,
                         'project_base_usd':spent+variable+2*fixed,'project_conservative_usd':spent+1.5*variable+2*fixed,
                         'extra_two_cold_10k_scaling_runs_api_base_usd':extra_scaling,
                         'project_with_three_cold_10k_runs_base_usd':spent+variable+extra_scaling+2*fixed,
                         'project_with_three_cold_10k_runs_conservative_usd':spent+1.5*(variable+extra_scaling)+2*fixed},
            'limitations':['Usage-rate calculated costs; provider receipts not reconciled.',
                           'Future costs/times extrapolate checkpoint mix and constant sustained throughput, not measured 10k/100k. Verification attempt time sums interrupted and recovery timers, excludes offline repair/setup time; not one uninterrupted pass.',
                           'New threshold/selection policy changes config; cache invalidation and routing mix require recalculation before approval.',
                           'Fixed-stage pilot cost extrapolated; future fixed stage wall time and local compute cost unknown.',
                           'Provider prompt caching was not controlled; raw billed categories retained.',
                           f'Saved scope profile keys: {sorted(scope)}']}
    atomic_json(directory/'report.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    report()
