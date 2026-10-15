"""Offline disjoint development-slice proposal; never makes provider calls."""

import csv
import hashlib
import json
import tomllib
from pathlib import Path

from pipeline.classify import jev_payload, luna_payload
from pipeline.prepare import atomic_json
from pipeline.schema import canonical, configuration
from pipeline.spend import token_cost


def plan(output=Path('artifacts/scaling-proposal')):
    config=tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    with Path('data/analysis_10000.csv').open(encoding='utf-8-sig',newline='') as handle:
        reader=csv.DictReader(handle)
        fields=reader.fieldnames
        rows=list(reader)
    with Path('data/checkpoint_500.csv').open(encoding='utf-8-sig',newline='') as handle:
        prior_texts={row['review_text'] for row in csv.DictReader(handle)}
    with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig',newline='') as handle:
        golden_ids={row['review_id'] for row in csv.DictReader(handle)}
    texts={}
    for row in sorted(rows,key=lambda row:row['review_id']):
        if row['review_id'] not in golden_ids and row['review_text'].strip() and row['review_text'] not in prior_texts:
            texts.setdefault(row['review_text'],row)
    ordered=sorted(texts,key=lambda text:hashlib.sha256(('spotify-scaling-slices-v1:'+text).encode()).digest())
    if len(ordered)<3000:
        raise ValueError('Insufficient disjoint development texts')
    measured=json.loads(Path('artifacts/checkpoint-500/report.json').read_text(encoding='utf-8'))['measured']
    throughput=measured['enrichment_distinct_texts_per_second']
    per_text=measured['cost_by_role_usd']['enrich']/479
    historical_config=json.loads(Path('cost/pilot_plan.json').read_text(encoding='utf-8'))
    reference_config=json.loads(json.dumps(config))
    reference_config['enrichment']['jev_prompt']='jev-v2.json'
    added_bytes=max(0,len(canonical(jev_payload('Music will not play.',config)).encode())-
                    len(canonical(jev_payload('Music will not play.',reference_config)).encode()))
    # New auxiliary tokens are unmeasured; explicitly assumed four UTF-8 bytes/token.
    added_cost_per_text=(added_bytes/4)*config['planning_rates']['jev_input_per_million']/1e6
    per_text += added_cost_per_text
    rates=dict(config['planning_rates'])
    rates['luna_input_per_million']=max(rates['luna_input_per_million'],rates['luna_cache_write_per_million'])
    slices=[]
    output.mkdir(parents=True,exist_ok=True)
    for index,workers in enumerate((1,2,8)):
        chosen=[texts[text] for text in ordered[index*1000:(index+1)*1000]]
        path=output/f'workers-{workers}-1000.csv'
        with path.open('w',encoding='utf-8',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields)
            writer.writeheader()
            writer.writerows(chosen)
        jev_cost=0
        luna_costs=[]
        for row in chosen:
            payload=jev_payload(row['review_text'],config)
            inputs=len(canonical(payload).encode())+config['controls']['token_overhead_bound']+1024
            jev_cost+=2*token_cost(inputs,0,rates,'typesafe')
            payload=luna_payload(row,{},config,False)
            inputs=len(canonical(payload).encode())+config['controls']['token_overhead_bound']+1024
            luna_costs.append(2*token_cost(inputs,200,rates,'openai'))
        long=sum(len(row['review_text'])>240 for row in chosen)
        luna_upper=min(1000,long+100)
        luna_envelope=sum(sorted(luna_costs,reverse=True)[:luna_upper])
        envelope=(jev_cost+luna_envelope)/1e9
        slices.append({'workers':workers,'rows':1000,'distinct_texts':1000,'long_texts':long,
                       'mean_text_chars':sum(len(row['review_text']) for row in chosen)/1000,
                       'csv':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                       'enrichment_expected_api_usd':1000*per_text,
                       'enrichment_conservative_mix_api_usd':1500*per_text,
                       'existing_config_enrichment_envelope_usd':envelope,
                       'cost_bounds_nanodollars':{'jev':jev_cost,'luna_enrich':luna_envelope,'verify':0},
                       'modeled_enrichment_seconds_linear_workers':1000/(throughput*(workers/2)),
                       'modeled_enrichment_seconds_50pct_slowdown':1500/(throughput*(workers/2)),
                       'initial_jev_calls':1000,'luna_enrichment_ids_upper':luna_upper,
                       'maximum_calls':2000+2*luna_upper})
    selected={row['review_id'] for text in ordered[:3000] for row in [texts[text]]}
    result={'status':'offline proposal, not paid execution','source':'analysis_10000.csv',
            'selection':'Seeded exact-text hash ordering; one original representative ID per text; mutually disjoint IDs and texts; exclude all checkpoint texts and golden IDs.',
            'source_sha256':hashlib.sha256(Path('data/analysis_10000.csv').read_bytes()).hexdigest(),
            'frozen_label_config':configuration(config),
            'slices':slices,'total_expected_api_usd':sum(s['enrichment_expected_api_usd'] for s in slices),
            'total_conservative_mix_api_usd':sum(s['enrichment_conservative_mix_api_usd'] for s in slices),
            'total_existing_config_envelope_usd':sum(s['existing_config_enrichment_envelope_usd'] for s in slices),
            'maximum_calls':sum(s['maximum_calls'] for s in slices),
            'transient_attempts':1,'invalid_output_repairs':1,
            'planning_rates':config['planning_rates'],
            'operational_controls':{key:config['controls'][key] for key in ('fallback_fraction','token_overhead_bound','project_api_cap_usd','request_timeout_seconds')},
            'approval_status':'awaiting_yes','slice_result_cache':'fresh and empty for each run',
            'paid_roles':['enrich'],'verification_group_memo_calls':0,
            'stop_gate':'After the three scaling slices; do not process the remaining analysis_10000 rows.',
            'new_prompt_expected_cost_assumption':{'extra_payload_bytes_per_jev_call':added_bytes,
                'assumed_bytes_per_extra_token':4,'extra_api_usd_per_text':added_cost_per_text,
                'measured_new_prompt_usage':False,'historical_pilot_config':historical_config['configuration']},
            'remaining_analysis_rows':len(rows)-len(selected),'remaining_analysis_distinct_texts':len({row['review_text'] for row in rows})-3000,
            'single_analysis_10k_no_reuse_expected_enrichment_usd':8448*per_text,
            'single_analysis_10k_reusing_slices_expected_enrichment_usd':5448*per_text,
            'limitations':['Time at 1/8 workers is modeled linear scaling, not measured. Rate limits can invalidate it.',
                           'Disjoint inputs confound worker effect with review mix; report lengths/language/routing and avoid causal speedup claims.',
                           'Unique-text representatives exclude duplicate propagation workload; cold saved-result cache required. Provider caching cannot be reset.',
                           'Expected costs extrapolate historical 11.9% fallback mix, not a new-config measured mix. Conservative token envelope uses frozen prompts, 10% quota, long texts and bounded repairs.',
                           'No verification/group/memo calls included. One 10k measurement retained for contract/project instructions; reuse requires validated provenance and frozen config.']}
    atomic_json(output/'plan.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    plan()
