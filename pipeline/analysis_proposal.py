"""Offline analysis_10000 proposal, admitted only after the predeclared A/B passes."""

import csv
import hashlib
import json
import math
import tomllib
from pathlib import Path

from pipeline.classify import jev_payload, luna_payload
from pipeline.prepare import atomic_json
from pipeline.scaling_report import load_state
from pipeline.schema import canonical, configuration, validate_record
from pipeline.spend import token_cost

BASE = Path('artifacts/checkpoint-500-v3-ab')


def build():
    report = json.loads((BASE/'paired-report.json').read_text(encoding='utf-8'))
    if report['pass_result']['status']!='pass' or not report['pass_result']['passes']:
        raise ValueError('A/B has not passed; no analysis gate proposal')
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    label_config = configuration(config)
    if label_config!=report['label_config'] or label_config!=json.loads(Path('docs/frozen-label-config.json').read_text(encoding='utf-8'))['label_config']:
        raise ValueError('Final hash mismatch')
    rows, events = load_state(BASE/'state.sqlite3')
    with Path('data/analysis_10000.csv').open(encoding='utf-8-sig',newline='') as handle:
        analysis = list(csv.DictReader(handle))
    if len(analysis)!=10000 or len({row['review_id'] for row in analysis})!=10000:
        raise ValueError('Analysis input counts changed')
    by_id = {row['review_id']:row for row in analysis}
    completed_texts, terminal_texts = set(), set()
    for row in rows:
        source = row['source']
        if source['review_id'] not in by_id or any(by_id[source['review_id']][key]!=source[key] for key in by_id[source['review_id']]):
            raise ValueError('Base provenance differs from analysis source')
        if row['result']:
            validate_record(row['result'],source,label_config,require_reasons=True)
            if not row['result'].get('cache_source_id') and not any(event['role']=='enrich' and event['outcome']=='succeeded' and event['label_config']==label_config
                    and source['review_id'] in event['review_ids'] for event in events):
                raise ValueError('Direct completed record lacks matching succeeded evidence')
            completed_texts.add(source['review_text'])
        else:
            terminal_texts.add(source['review_text'])
    texts = {}
    for source in sorted(analysis,key=lambda row:row['review_id']):
        if source['review_text'] not in completed_texts|terminal_texts and source['review_text'].strip():
            texts.setdefault(source['review_text'],source)
    with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig',newline='') as handle:
        golden = {row['review_id'] for row in csv.DictReader(handle)}
    if set(by_id)&golden:
        raise ValueError('Development input contains golden IDs')
    distinct = len(texts)
    quota = math.floor(distinct*config['controls']['fallback_fraction'])
    long = sum(len(text)>config['enrichment']['short_review_chars'] for text in texts)
    rates = dict(config['planning_rates'])
    rates['luna_input_per_million'] = max(rates['luna_input_per_million'],rates['luna_cache_write_per_million'])
    jev = 0
    luna = []
    for text, source in texts.items():
        inputs = len(canonical(jev_payload(text,config)).encode())+config['controls']['token_overhead_bound']+1024
        jev += 2*token_cost(inputs,0,rates,'typesafe')
        inputs = len(canonical(luna_payload(source,{},config,False)).encode())+config['controls']['token_overhead_bound']+1024
        luna.append(2*token_cost(inputs,200,rates,'openai'))
    luna_upper = min(distinct,long+quota)
    luna_bound = sum(sorted(luna,reverse=True)[:luna_upper])
    worst = jev+luna_bound
    measurements = json.loads((BASE/'measurements.json').read_text(encoding='utf-8'))
    measured_cost = sum(event.get('cost_nanodollars',0) for event in events)/1e9
    result = {'status':'proposal only; awaiting explicit yes','workers':8,'label_config':label_config,
        'input':'data/analysis_10000.csv','input_sha256':hashlib.sha256(Path('data/analysis_10000.csv').read_bytes()).hexdigest(),
        'output':'artifacts/analysis-10000-final','base_state':str(BASE/'state.sqlite3'),
        'base_state_sha256':hashlib.sha256((BASE/'state.sqlite3').read_bytes()).hexdigest(),
        'ab_report_sha256':hashlib.sha256((BASE/'paired-report.json').read_bytes()).hexdigest(),
        'rows':10000,'distinct_texts':len({row['review_text'] for row in analysis}),
        'already_completed_original_ids':sum(bool(row['result']) for row in rows),
        'reusable_rows_including_exact_text_aliases':sum(row['review_text'] in completed_texts for row in analysis),
        'reusable_distinct_texts':len(completed_texts),
        'retained_terminal_rows':sum(row['review_text'] in terminal_texts for row in analysis),
        'retained_terminal_distinct_texts':len(terminal_texts),
        'new_pending_rows':sum(row['review_text'] not in completed_texts|terminal_texts for row in analysis),
        'new_distinct_texts':distinct,'fallback_quota':quota,'long_new_texts':long,
        'luna_enrichment_ids_upper':luna_upper,'initial_jev_calls':distinct,
        'maximum_calls':2*(distinct+luna_upper),'cost_bounds_nanodollars':{'jev':jev,'luna_enrich':luna_bound,'verify':0},
        'worst_case_usd':worst/1e9,'invocation_cap_usd':math.ceil(worst/1e6)/1000,
        'observed_mix_estimate_usd':distinct*measured_cost/479,
        'project_spend_usd':measurements['ledger']['spent_nanodollars']/1e9,
        'project_total_if_full_envelope_spent_usd':(measurements['ledger']['spent_nanodollars']+worst)/1e9,
        'planning_rates':config['planning_rates'],
        'operational_controls':{key:config['controls'][key] for key in ('fallback_fraction','token_overhead_bound','request_timeout_seconds','project_api_cap_usd')},
        'transient_attempts':1,'invalid_output_repairs':1,
        'reuse_method':'Read-only SQLite backup of final-hash A/B state, then validated ingestion of analysis_10000. Original sources/calls/direct cache origins retained. Imported calls are provenance only, not newly billed. Terminal text stays quarantined and is not retried.',
        'historical_slice_cache':'Old-hash 3000 slice records are not reusable; their source texts are part of the new pending work.',
        'roles':['enrich'],'verifier_group_memo_calls':0,
        'failure_policy':'Continue after one permitted repair then quarantine terminal failures; systemic >5% in rolling100 after minimum20, plus spend/auth/unknown-charge integrity stops.',
        'stop_gate':'After full analysis_10000 enrichment report, before 100k, verifier refresh, golden evaluation or downstream paid work.'}
    atomic_json(Path('docs/analysis-10000-final-proposal.json'),result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    build()
