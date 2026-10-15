"""Offline same-row v2/v3 enrichment proposal; no dispatch and no golden answers."""

import copy
import hashlib
import json
import tomllib
from pathlib import Path

from pipeline.calibration import disagreement, field_disagreement, field_summary
from pipeline.classify import jev_payload, luna_payload, parse_jev
from pipeline.prepare import atomic_json
from pipeline.scaling_report import load_state
from pipeline.schema import canonical, configuration
from pipeline.spend import token_cost


def comparison(rows, events, predictions):
    responses = {event['review_ids'][0]:event['response'] for event in events
                 if event['stage']=='jev' and event['outcome']=='succeeded'}
    key_responses = {row['key']:responses[row['source']['review_id']] for row in rows if row['source']['review_id'] in responses}
    items = []
    final_items = []
    for row in rows:
        rid = row['source']['review_id']
        if rid not in predictions or row['key'] not in key_responses:
            continue
        # Identical core decoder in both arms, without auxiliary-language override.
        reply = copy.deepcopy(key_responses[row['key']])
        reply['answers'] = {key:value for key,value in reply['answers'].items()
                            if key in {'topic','intent','severity','sentiment'}}
        core = parse_jev(reply,.6,0)
        verifier = predictions[rid]
        item = {'review_id':rid, 'jev_disagreements':disagreement(core,verifier),
                'jev_field_errors':field_disagreement(core,verifier)}
        items.append(item)
        if row['result'] is not None:
            final_items.append({'review_id':rid,'final_disagreements':disagreement(row['result'],verifier),
                                'final_field_errors':field_disagreement(row['result'],verifier)})
    return {'rows':len(items), 'core_jev_fields':field_summary(items,'jev'),
            'final_enrichment_rows':len(final_items),'final_enrichment_fields':field_summary(final_items,'final'),
            'core_composite_disagreements':sum(bool(item['jev_disagreements']) for item in items),
            'final_composite_disagreements':sum(bool(item['final_disagreements']) for item in final_items)}


def plan():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    frozen = json.loads(Path('docs/frozen-label-config.json').read_text(encoding='utf-8'))
    if configuration(config)!=frozen['label_config']:
        raise ValueError('Frozen hash changed')
    rows, events = load_state(Path('artifacts/checkpoint-500/state.sqlite3'))
    saved = json.loads(Path('artifacts/checkpoint-500/verifier.json').read_text(encoding='utf-8'))
    predictions = saved['predictions']
    if len(rows)!=500 or len(predictions)!=500 or not saved['complete']:
        raise ValueError('Checkpoint reference incomplete')
    import csv
    with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig', newline='') as handle:
        golden = {row['review_id'] for row in csv.DictReader(handle)}
    if {row['source']['review_id'] for row in rows} & golden:
        raise ValueError('Golden overlap')
    verified_requests = []
    for event in events:
        if event['role']!='verify':
            continue
        packed = event['request']['input'].split('BEGIN_UNTRUSTED_REVIEWS_JSON\n')[1].split('\nEND_UNTRUSTED_REVIEWS_JSON')[0]
        if any(set(row)!={'review_id','review_text'} for row in json.loads(packed)):
            raise ValueError('Verifier saw nonblinded classification input')
        verified_requests.append(event['request_id'])
    texts = {}
    for row in sorted(rows,key=lambda row:row['source']['review_id']):
        texts.setdefault(row['source']['review_text'],row['source'])
    distinct = len(texts)
    quota = int(distinct * config['controls']['fallback_fraction'])
    rates = dict(config['planning_rates'])
    rates['luna_input_per_million'] = max(rates['luna_input_per_million'],rates['luna_cache_write_per_million'])
    jev_bound = 0
    luna_bounds = []
    for text, source in texts.items():
        inputs = len(canonical(jev_payload(text,config)).encode())+config['controls']['token_overhead_bound']+1024
        jev_bound += 2*token_cost(inputs,0,rates,'typesafe')
        inputs = len(canonical(luna_payload(source,{},config,False)).encode())+config['controls']['token_overhead_bound']+1024
        luna_bounds.append(2*token_cost(inputs,config['enrichment']['luna_output_tokens_per_review'],rates,'openai'))
    long = sum(len(text)>config['enrichment']['short_review_chars'] for text in texts)
    luna_upper = min(distinct,long+quota)
    luna_bound = sum(sorted(luna_bounds,reverse=True)[:luna_upper])
    prior_hashes = sorted({row['result']['label_config'] for row in rows})
    result = {'status':'proposal only; no paid calls', 'input':'data/checkpoint_500.csv',
              'source_sha256':hashlib.sha256(Path('data/checkpoint_500.csv').read_bytes()).hexdigest(),
              'output':'artifacts/checkpoint-500-v3-ab', 'rows':500,'distinct_texts':distinct,
              'label_config':configuration(config),'v2_label_configs':prior_hashes,'workers':2,
              'cache':'Fresh v3 work store; do not import old v2 results. 21 duplicate aliases propagate exact-text results.',
              'initial_jev_calls':distinct,'fallback_quota':quota,'long_distinct_texts':long,
              'luna_enrichment_ids_upper':luna_upper,
              'maximum_calls':2*(distinct+luna_upper),'transient_attempts':1,'repairs_per_item':1,
              'cost_bounds_nanodollars':{'jev':jev_bound,'luna_enrich':luna_bound,'verify':0},
              'worst_case_usd':(jev_bound+luna_bound)/1e9,
              'planning_rates':config['planning_rates'],
              'operational_controls':{key:config['controls'][key] for key in ('fallback_fraction','token_overhead_bound','request_timeout_seconds','project_api_cap_usd')},
              'frozen_verifier_sha256':hashlib.sha256(Path('artifacts/checkpoint-500/verifier.json').read_bytes()).hexdigest(),
              'existing_verifier_independence':{'requests_audited':len(verified_requests),
                  'request_fields':['review_id','review_text'],'first_predictions_supplied':False,
                  'note':'Blinded to Jev/first enrichment outputs. Same provider/model as fallback; not statistical independence or human truth.'},
              'existing_v2_same_row_baseline':comparison(rows,events,predictions),
              'primary_ab':'Historical matched-text Jev prompt comparison; compare only core answers with identical decoder in both arms, without v3 auxiliary override. Report raw v3 core and operational v3 outputs separately.',
              'secondary_comparison':'Operational final enrichment v2 vs final frozen v3. Not prompt-only: old thresholds .75/.15, v3 .60/0; fallback allocation, old quota defect, persistent context and Luna-v2 explicit reason schema/prompt also differ.',
              'fields':['topic','intent','severity_exact','severity_beyond_one','sentiment_sign','sentiment_tolerance_025'],
              'comparison_method':'Same fixed 500 verifier labels, paired per-ID differences and exact-text cluster intervals; show improvements/regressions and alias-weighted vs unique-text summaries. No verifier or golden calls.',
              'exclusions':['No verifier refresh','No grouping/memo','No golden evaluation','No remaining analysis_10000 during A/B'],
              'invocation_cap_usd':.431,
              'final_flag_policy':config['enrichment']['needs_review_policy'],
              'failure_policy':'One permitted repair; terminal failure logged/quarantined and excluded from agreement (denominator disclosed); >5% in rolling 100 after minimum20 finalized is systemic halt.',
              'stop_gate':'After same-row v2/v3 report; explicit yes required before dispatch.'}
    atomic_json(Path('docs/checkpoint-500-v3-ab-proposal.json'),result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    plan()
