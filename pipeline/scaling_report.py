"""Offline scaling gate: usage, v2/v3 flags and a proposed verifier transfer sample."""

import csv
import hashlib
import itertools
import json
import math
import sqlite3
import statistics
import tomllib
from pathlib import Path

from pipeline.checkpoint import verifier_payload
from pipeline.classify import parse_jev
from pipeline.deterministic import ranking_scores
from pipeline.prepare import atomic_json
from pipeline.schema import canonical
from pipeline.spend import token_cost


def quantile(values,fraction):
    ordered=sorted(values)
    index=(len(ordered)-1)*fraction
    lower=math.floor(index)
    upper=math.ceil(index)
    return ordered[lower]+(ordered[upper]-ordered[lower])*(index-lower)


def distribution(values):
    return {'n':len(values),'mean':statistics.mean(values),'min':min(values),'p10':quantile(values,.1),
            'p25':quantile(values,.25),'median':quantile(values,.5),'p75':quantile(values,.75),'p90':quantile(values,.9),'max':max(values)}


def load_state(path):
    with sqlite3.connect(f'file:{path.as_posix()}?mode=ro',uri=True) as db:
        rows=[{'source':json.loads(source),'result':json.loads(result) if result else None,'key':key}
              for source,result,key in db.execute('SELECT source,result,work_key FROM reviews')]
        events=[json.loads(event) for event, in db.execute('SELECT event FROM calls')]
    return rows,events


def comparison(rows,events,v3):
    succeeded=[event for event in events if event['stage']=='jev' and event['outcome']=='succeeded']
    by_id={event['review_ids'][0]:event for event in succeeded}
    by_key={row['key']:by_id[row['source']['review_id']] for row in rows if row['source']['review_id'] in by_id}
    items=[]
    for row in rows:
        if row['key'] not in by_key:
            continue
        event=by_key[row['key']]
        labels=parse_jev(event['response'],.6,0,require_auxiliary=v3)
        scores=ranking_scores(event['response'])
        answers=event['response']['answers']
        language=answers.get('language',{}).get('choice')
        missing=answers.get('missing_context',{}).get('noul')
        items.append({'review_id':row['source']['review_id'],'confidence':scores['confidence'],
                      'margin':scores['margin'],'triage_flag':labels['needs_review'],
                      'low_core_confidence':scores['confidence']<.6,
                      'nonenglish':language is not None and language!='english',
                      'language':language,'missing_context':missing is not None and missing>=.5,
                      'final_flag':row['result']['needs_review'] if row['result'] else None})
    attempts=[event for event in events if event['stage']=='jev']
    billed=[event['input_tokens'] for event in attempts if type(event.get('input_tokens')) is int]
    distinct=len(by_key)
    confidence=[item['confidence'] for item in items]
    unique_confidence=[ranking_scores(event['response'])['confidence'] for event in succeeded]
    fields={field:distribution([event['response']['answers'][field]['confidence'] for event in succeeded])
            for field in ('topic','intent','severity','sentiment')}
    nonenglish=[item for item in items if item['nonenglish']]
    result={'rows_with_valid_jev':len(items),'distinct_texts_with_valid_jev':distinct,'jev_attempts':len(attempts),
            'jev_calls_with_reported_input_usage':len(billed),'jev_mean_input_tokens_per_reported_call':statistics.mean(billed),
            'jev_mean_input_tokens_per_successful_distinct_text_including_attempts':sum(billed)/distinct,
            'jev_total_reported_input_tokens':sum(billed),'triage_flagged':sum(item['triage_flag'] for item in items),
            'triage_flag_rate':sum(item['triage_flag'] for item in items)/len(items),
            'core_confidence_flagged':sum(item['low_core_confidence'] for item in items),
            'nonenglish_flagged':len(nonenglish),
            'language_not_understood':sum(item['language']=='not_understood' for item in items),
            'missing_context_flagged':sum(item['missing_context'] for item in items),
            'auxiliary_only_flagged':sum(item['triage_flag'] and not item['low_core_confidence'] for item in items),
            'language_evidence_available':v3,'confidence_distribution_by_row':distribution(confidence),
            'confidence_distribution_by_distinct_text':distribution(unique_confidence),'per_field_confidence':fields,
            'confidence_histogram':{name:sum(lower<=value<upper for value in unique_confidence)
                                    for name,lower,upper in [('[0,.2)',0,.2),('[.2,.4)',.2,.4),('[.4,.6)',.4,.6),('[.6,.8)',.6,.8),('[.8,1]',.8,1.000001)]},
            'final_flagged':sum(bool(item['final_flag']) for item in items),
            'final_flag_denominator':sum(item['final_flag'] is not None for item in items),
            'nonenglish_final_unflagged':sum(item['final_flag'] is False for item in nonenglish)}
    return result,items


def report():
    config=tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    plan=json.loads(Path('artifacts/scaling-proposal/plan.json').read_text(encoding='utf-8'))
    output=Path('artifacts/scaling')
    all_rows,all_events,measured=[] ,[],[]
    for proposed in plan['slices']:
        directory=output/f"workers-{proposed['workers']}"
        measurement=json.loads((directory/'measurements.json').read_text(encoding='utf-8'))
        if not measurement['status'].startswith('completed'):
            raise ValueError('Incomplete scaling run: no completed gate report')
        rows,events=load_state(directory/'state.sqlite3')
        stats,items=comparison(rows,events,True)
        cost=sum(event.get('cost_nanodollars',0) for event in events)/1e9
        per_role={stage:sum(event.get('cost_nanodollars',0) for event in events if event['stage']==stage)/1e9 for stage in ('jev','fallback','extract')}
        fallback_ids={rid for event in events if event['stage']=='fallback' for rid in event['review_ids']}
        extract_ids={rid for event in events if event['stage']=='extract' for rid in event['review_ids']}
        timing=measurement['enrichment_seconds']
        measured.append({'workers':proposed['workers'],'rows':len(rows),'counts':measurement['counts'],'seconds':timing,
                         'completed_rows_per_second':measurement['counts'].get('completed',0)/timing,
                         'api_cost_usd':cost,'cost_by_stage_usd':per_role,'attempts':len(events),
                         'failed_attempts':sum(event['outcome']=='failed' for event in events),
                         'warm_seconds':measurement['warm_seconds'],'warm_new_calls':measurement['warm_new_calls'],
                         'fallback_distinct_ids':len(fallback_ids),'extraction_only_distinct_ids':len(extract_ids),
                         'v3':stats})
        atomic_json(directory/'flag_diagnostic.json',{'summary':stats,'items':items})
        all_rows.extend(rows)
        all_events.extend(events)
    old_rows,old_events=load_state(Path('artifacts/checkpoint-500/state.sqlite3'))
    v2,_=comparison(old_rows,old_events,False)
    v3,items=comparison(all_rows,all_events,True)
    rates=config['planning_rates']
    mean_tokens=v3['jev_mean_input_tokens_per_successful_distinct_text_including_attempts']
    jev_scope=77913*mean_tokens*rates['jev_input_per_million']/1e6
    enrich_cost=sum(event.get('cost_nanodollars',0) for event in all_events if event['role']=='enrich')/1e9
    cost_per_text=enrich_cost/3000
    with Path('artifacts/sampling/permutation.csv').open(encoding='utf-8',newline='') as handle:
        scope_ids={row['review_id'] for row in itertools.islice(csv.DictReader(handle),config['scope']['sample_size'])}
    with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig',newline='') as handle:
        golden_ids={row['review_id'] for row in csv.DictReader(handle)}
    scope_ids |= golden_ids
    with sqlite3.connect('file:artifacts/ingestion/state.sqlite3?mode=ro',uri=True) as db:
        scope_texts={text for rid,text in db.execute('SELECT review_id,review_text FROM reviews') if rid in scope_ids}
    completed=[row for row in all_rows if row['result']]
    reusable=len({row['source']['review_text'] for row in completed}&scope_texts)
    pending_scope=77913-reusable
    old_verifier_cost=sum(event.get('cost_nanodollars',0) for event in old_events if event['role']=='verify')/1e9
    pilot_events=[json.loads(line) for line in Path('cost/pilot_calls.jsonl').read_text(encoding='utf-8').splitlines()]
    fixed=sum(event.get('cost_nanodollars',0) for event in pilot_events if event['role'] in {'group','memo'} and event['outcome']=='succeeded')/1e9
    latest=json.loads((output/'workers-8/measurements.json').read_text(encoding='utf-8'))['ledger']
    spent=latest['spent_nanodollars']/1e9
    variable=(5448+75918)*cost_per_text+3*old_verifier_cost  # transfer, analysis and final 500 passes
    projections={'scope_distinct_texts':77913,'measured_jev_input_tokens_per_text_including_attempts':mean_tokens,
                 'jev_100k_scope_no_reuse_api_usd':jev_scope,
                 'old_v2_jev_100k_scope_api_usd':77913*v2['jev_mean_input_tokens_per_successful_distinct_text_including_attempts']*rates['jev_input_per_million']/1e6,
                 'scope_enrichment_no_reuse_api_base_usd':77913*cost_per_text,
                 'scope_enrichment_no_reuse_api_50pct_variable_allowance_usd':77913*cost_per_text*1.5,
                 'slice_completed_texts_reusable_in_scope':reusable,'remaining_scope_texts_if_slices_reused':pending_scope,
                 'scope_incremental_enrichment_if_slices_reused_api_usd':pending_scope*cost_per_text,
                 'remaining_analysis_distinct_texts':5448,'scope_after_all_10k_same_hash_reuse_distinct_texts':75918,
                 'project_base_api_usd':spent+variable+2*fixed,'project_50pct_future_variable_allowance_api_usd':spent+1.5*variable+2*fixed,
                 'assumptions':'Observed v3 slice token/routing mix extrapolated. Three future 500-row verifier passes use historical cost including failures; two fixed group/memo runs use pilot succeeded-role overhead. Not worst-case guarantees.'}
    sample=sorted((row for row in completed if row['source']['review_id'] not in golden_ids),
                  key=lambda row:hashlib.sha256(('spotify-v3-transfer-500-v1:'+row['source']['review_id']).encode()).digest())[:500]
    if len(sample)!=500:
        raise ValueError('Insufficient completed non-golden slice rows')
    batch_bounds=[len(canonical(verifier_payload([row['source'] for row in sample[start:start+50]],config)).encode())
                  +config['controls']['token_overhead_bound'] for start in range(0,500,50)]
    singleton_bounds=[len(canonical(verifier_payload([row['source']],config)).encode())
                      +config['controls']['token_overhead_bound']+1024 for row in sample]
    if max(batch_bounds)>24000 or max(singleton_bounds)>10000:
        raise ValueError('Transfer verifier sample exceeds reviewed input bounds')
    verify_rates=dict(rates)
    verify_rates['luna_input_per_million']=max(rates['luna_input_per_million'],rates['luna_cache_write_per_million'])
    verify_bound=10*token_cost(24000,10000,verify_rates,'openai')+500*token_cost(10000,200,verify_rates,'openai')
    proposal={'status':'proposed only; never dispatched','sample_size':500,'golden_excluded':True,
              'seed':'spotify-v3-transfer-500-v1','source':'completed rows from all three scaling slices',
              'sample_ids':[row['source']['review_id'] for row in sample],
              'sample_workers_distribution':{str(workers):sum(row['source']['review_id'] in {r['source']['review_id'] for r in all_rows[index*1000:(index+1)*1000]} for row in sample) for index,workers in enumerate((1,2,8))},
              'label_config':plan['frozen_label_config'],'initial_calls':10,'batch_size':50,'singleton_repairs_upper':500,
              'maximum_calls':510,'worst_case_nanodollars':verify_bound,'transient_attempts':1,
              'batch_input_token_bound':24000,'batch_output_cap':10000,'singleton_input_bound':10000,'singleton_output_cap':200,
              'offline_preflight_max_batch_bytes_plus_overhead':max(batch_bounds),
              'offline_preflight_max_singleton_bytes_plus_overhead_and_repair':max(singleton_bounds),
              'terminal_policy':'Invalid after one repair: terminally failed, excluded from calibration, continue unless >5% terminal failures in rolling window.',
              'procedure':'Original text plus rubric, no first labels. Recompute the same 35 pairs, field breakdown and auxiliary-only cohorts; frozen 0.60/0 remains the primary transfer check. No golden evaluation.',
              'stop_gate':'After verifier transfer report, before remaining analysis_10000. New paid approval required.'}
    atomic_json(output/'verifier-transfer-proposal.json',proposal)
    with (output/'verifier-transfer-sample.csv').open('w',encoding='utf-8',newline='') as handle:
        fields=['review_id','review_text','review_rating','review_likes','app_version','review_timestamp']
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader()
        writer.writerows({field:row['source'][field] for field in fields} for row in sample)
    flag_change=v3['triage_flag_rate']-v2['triage_flag_rate']
    result={'frozen_label_config':plan['frozen_label_config'],'measured_slices':measured,'v2_checkpoint':v2,'v3_slices':v3,
            'triage_flag_rate_change_percentage_points':flag_change*100,
            'confidence_median_change':v3['confidence_distribution_by_distinct_text']['median']-v2['confidence_distribution_by_distinct_text']['median'],
            'project_spend_usd':spent,'project_reserved_usd':latest['reserved_nanodollars']/1e9,'projections':projections,
            'calibration_transfer_recommendation':'Run the proposed verifier transfer sample and repeat development diagnostics before remaining analysis_10000; do not change the frozen threshold based only on flag rates or unlabeled confidence distributions.',
            'limitations':['V2 has no language/context answers; 36.2% is confidence-only triage, not final stored flags.',
                           'V2 checkpoint and v3 disjoint unique-text slices differ in input mix. Differences cannot establish a causal prompt effect.',
                           'Language counts are model-identified, not human-verified. No golden labels read.',
                           'Fresh saved-result cache on each slice; provider prompt caching uncontrolled. Measured usage categories retained in calls.',
                           'Current scope costs and time projections are estimates, refreshed from measured v3 usage, not a 100k execution.']}
    atomic_json(output/'gate-report.json',result)
    print(json.dumps({'slices':[{key:value for key,value in row.items() if key!='v3'} for row in measured],
                      'v2_input_tokens':v2['jev_mean_input_tokens_per_reported_call'],'v3_input_tokens':v3['jev_mean_input_tokens_per_reported_call'],
                      'v2_flag_rate':v2['triage_flag_rate'],'v3_flag_rate':v3['triage_flag_rate'],
                      'v3_nonenglish':v3['nonenglish_flagged'],'v3_auxiliary_only_flags':v3['auxiliary_only_flagged'],
                      'confidence_v2':v2['confidence_distribution_by_distinct_text'],'confidence_v3':v3['confidence_distribution_by_distinct_text'],
                      'project_spend':spent,'projections':projections,'verifier_proposal_worst_case_usd':verify_bound/1e9},indent=2))


if __name__=='__main__':
    report()
