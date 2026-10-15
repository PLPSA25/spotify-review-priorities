"""Development-only fallback sensitivity. Never reads golden answers/results."""
import copy
import csv
import hashlib
import json
import math
import sqlite3
import tomllib
from collections import Counter
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from pipeline.batching import pack
from pipeline.classify import parse_jev
from pipeline.disagreement_review import value
from pipeline.prepare import atomic_json
from pipeline.scaling_report import load_state
from pipeline.schema import configuration

ROOT = Path('artifacts/analysis-10000-final')
FIELDS = ('topic','intent','severity_exact','severity_within_one','sentiment_sign','needs_review')


def differences(a,b):
    return {'topic':a['topic']!=b['topic'],'intent':a['intent']!=b['intent'],
            'severity_exact':a['severity']!=b['severity'],
            'severity_within_one':abs(a['severity']-b['severity'])>1,
            'sentiment_sign':value(a,'sentiment_sign')!=value(b,'sentiment_sign'),
            'needs_review':a['needs_review']!=b['needs_review']}


def composite(errors):
    return any(errors[field] for field in ('topic','intent','severity_exact','sentiment_sign'))


def comparison(items,left,right):
    errors = [differences(item[left],item[right]) for item in items]
    return {'n':len(items),'any_core_label_changed':sum(composite(e) for e in errors),
            'any_core_change_rate':sum(composite(e) for e in errors)/len(items) if items else None,
            'by_field':{field:{'different':sum(e[field] for e in errors),'n':len(items),
                               'rate':sum(e[field] for e in errors)/len(items) if items else None} for field in FIELDS}}


def paired_verifier(items):
    result = {'n':len(items),'jev_vs_verifier':comparison(items,'jev','verifier'),
              'fallback_vs_verifier':comparison(items,'final','verifier'),'by_field':{}}
    for field in FIELDS:
        before = [differences(i['jev'],i['verifier'])[field] for i in items]
        after = [differences(i['final'],i['verifier'])[field] for i in items]
        result['by_field'][field] = {'corrected_relative_to_verifier':sum(b and not a for b,a in zip(before,after,strict=True)),
                                    'regressed_relative_to_verifier':sum(not b and a for b,a in zip(before,after,strict=True))}
    return result


def build():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    label_config = configuration(config)
    rows, events = load_state(ROOT/'state.sqlite3')
    by_id = {row['source']['review_id']:row for row in rows}
    by_key = {}
    for row in sorted(rows,key=lambda r:r['source']['review_id']):
        by_key.setdefault(row['key'],row)
    responses = {by_id[e['review_ids'][0]]['key']:e['response'] for e in events
                 if e['stage']=='jev' and e['outcome']=='succeeded' and e['label_config']==label_config}
    jev = {key:parse_jev(reply,.6,0,require_auxiliary=True) for key,reply in responses.items()}
    with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig',newline='') as stream:
        golden = list(csv.DictReader(stream))  # only source IDs/text; no human labels
    golden_ids = {r['review_id'] for r in golden}
    golden_texts = {r['review_text'] for r in golden}
    with closing(sqlite3.connect(f'file:{(ROOT/"state.sqlite3").as_posix()}?mode=ro',uri=True)) as db:
        artifacts = {key:json.loads(saved) for key,saved in db.execute('SELECT key,result FROM artifacts')}
        fallback_results = {key:json.loads(saved) for key,saved in db.execute("SELECT work_key,result FROM stage_results WHERE stage='fallback'")}
        work = {key:{'text':text,'origin_id':origin,'status':status} for key,text,origin,status in db.execute('SELECT key,text,origin_id,status FROM work')}
    active = artifacts['active-routing-tranche']
    selection = artifacts['routing-selection:'+active['id']]
    ranked = selection['ranked_candidates']
    rank = {candidate['key']:index for index,candidate in enumerate(ranked)}
    clean_keys = {key for key,row in by_key.items() if row['source']['review_text'] not in golden_texts and key in jev and row['result']}
    eligible = clean_keys & {key for key,labels in jev.items() if labels['low_confidence']}
    actual = [{'key':key,'jev':jev[key],'final':fallback_results[key]} for key in sorted(eligible & set(fallback_results))]
    verifiers = {}
    for cohort, path in [('checkpoint',Path('artifacts/checkpoint-500/verifier.json')),
                         ('transfer',Path('artifacts/scaling/transfer-verifier/verifier.json'))]:
        saved = json.loads(path.read_text(encoding='utf-8'))
        if not saved['complete']:
            raise ValueError('Incomplete development verifier')
        for rid, labels in saved['predictions'].items():
            if rid in verifiers:
                raise ValueError('Verifier cohorts overlap; do not silently choose a label')
            verifiers[rid] = (cohort,labels)
    verified_rows = []
    for rid,(cohort,labels) in sorted(verifiers.items()):
        if rid in golden_ids or rid not in by_id:
            continue
        row = by_id[rid]
        key = row['key']
        if key not in eligible:
            continue
        verified_rows.append({'review_id':rid,'key':key,'cohort':cohort,'jev':jev[key],
                              'verifier':labels,'final':row['result'],'actual_fallback':key in fallback_results})
    # Primary quality summary: first sorted ID per exact text, independent of labels.
    unique = {}
    for item in verified_rows:
        unique.setdefault(item['key'],item)
    verified = list(unique.values())
    bands = {}
    n = len(active['keys'])
    for low,high in ((0,.1),(.1,.2),(.2,.3),(.3,1)):
        members = [i for i in verified if i['key'] in rank and math.floor(n*low)<=rank[i['key']]<math.floor(n*high)]
        bands[f'{low:.0%}–{high:.0%}'] = comparison(members,'jev','verifier')
    paired = [i for i in verified if i['actual_fallback']]
    human = json.loads(Path('evals/verifier-human-review.json').read_text(encoding='utf-8'))
    human_eligible, human_actual = [], []
    for case in human['cases']:
        verdict = human['verdicts'].get(case['case_id'])
        if verdict is None:
            continue
        key = by_id[case['review_id']]['key']
        if key not in eligible:
            continue
        detail = {'review_id':case['review_id'],'field':case['target_field'],'verdict':verdict['verdict'],
                  'actual_fallback':key in fallback_results,
                  'jev_flag_reasons':jev[key]['needs_review_reasons']}
        human_eligible.append(detail)
        if key in fallback_results:
            target = case['target_field']
            preferred = case['jev'] if verdict['verdict']=='jev_right' else case['verifier'] if verdict['verdict']=='verifier_right' else None
            detail['fallback_matches_human_preferred_shown_label'] = value(fallback_results[key],target)==value(preferred,target) if preferred else None
            human_actual.append(detail)
    old = json.loads((ROOT/'measurements.json').read_text())
    measured = json.loads((ROOT/'resume-measurements.json').read_text())
    run_ids = {old['run_id'],measured['run_id']}
    paid = [e for e in events if e['run_id'] in run_ids]
    costs = {stage:sum(e.get('cost_nanodollars',0) for e in paid if e['stage']==stage)/1e9 for stage in ('jev','extract','fallback')}
    requests = {stage:sum(e['stage']==stage for e in paid) for stage in ('jev','extract','fallback')}
    root_counts = {mode:sum(len(batch['keys']) for batch in selection['batches'] if batch['mode']==mode) for mode in ('extract','fallback','local')}
    root_calls = {mode:sum(batch['mode']==mode for batch in selection['batches']) for mode in ('extract','fallback','local')}
    unit = {mode:costs[mode]/root_counts[mode] for mode in ('extract','fallback')}
    repairs_per_text = {mode:(requests[mode]-root_calls[mode])/root_counts[mode] for mode in ('extract','fallback')}
    previous_projection = json.loads((ROOT/'resume-gate-report.json').read_text())['projection']
    # Conditional future scope after 44 newly classified golden texts all complete.
    future_n = previous_projection['remaining_scope_distinct_texts']-44
    scenarios = []
    sources = {key:by_id[work[key]['origin_id']]['source'] for key in active['keys']}
    for fraction in (.1,.2,.3):
        alternative = copy.deepcopy(config)
        alternative['controls']['fallback_fraction'] = fraction
        quota = math.floor(n*fraction)
        selected = [candidate['key'] for candidate in ranked[:quota]]
        selected_set = set(selected)
        extracts = [key for key in active['keys'] if key not in selected_set and len(work[key]['text'])>config['enrichment']['short_review_chars']]
        mode_keys = {'extract':extracts,'fallback':selected}
        calls = {}
        for mode, keys in mode_keys.items():
            items = [{'key':key,'source':sources[key]} for key in keys]
            labels = {sources[key]['review_id']:jev[key] for key in keys}
            calls[mode] = len(pack(items,labels,alternative,mode=='extract'))
        expected_calls = sum(calls[mode]+len(mode_keys[mode])*repairs_per_text[mode] for mode in mode_keys)
        base = future_n/n*(costs['jev']+sum(unit[mode]*len(mode_keys[mode]) for mode in mode_keys))
        finish_seconds = previous_projection['optimized_finishing_stage_seconds']+(expected_calls-requests['extract']-requests['fallback'])/config['rate_limits']['openai']['rps']
        seconds_per_text = previous_projection['optimized_jev_stage_seconds']/previous_projection['optimized_jev_distinct_texts']+finish_seconds/n
        scenarios.append({'fallback_fraction':fraction,'hash_unchanged':configuration(alternative)==label_config,
                          'reference_texts':n,'reference_quota':quota,'reference_fallback_texts':len(selected),
                          'reference_extraction_texts':len(extracts),'reference_root_calls':calls,
                          'reference_expected_luna_calls_including_repairs':expected_calls,
                          'future_pending_texts_conditional':future_n,
                          'future_fallback_quota':math.floor(future_n*fraction),
                          'base_cost_usd':base,'cap_1_5x_rounded_up_cents_usd':math.ceil(base*1.5*100)/100,
                          'base_hours':future_n*seconds_per_text/3600})
    result = {'label_config':label_config,'golden_accuracy_used':False,
              'recommendation_frozen_at_utc':datetime.now(UTC).isoformat(),
              'recommendation':{'fallback_fraction':.2,'status':'proposal only; not applied',
                                'rationale':'Moderate expansion: existing fallback improves blinded-verifier agreement on paired rows and the 10–20% rank band still has substantial disagreement. Human adjudication warns that Luna/verifier changes can be wrong, especially intent; no measured benefit for wider routing and no justification to spend for30% now. Golden accuracy is excluded from this recommendation.',
                                'proposed_invocation_cap_usd':scenarios[1]['cap_1_5x_rounded_up_cents_usd']},
              'development_state_sha256':hashlib.sha256((ROOT/'state.sqlite3').read_bytes()).hexdigest(),
              'human_verdicts_sha256':hashlib.sha256(Path('evals/verifier-human-review.json').read_bytes()).hexdigest(),
              'eligible_development_unique_texts':len(eligible),'clean_completed_development_unique_texts':len(clean_keys),
              'actual_fallback_eligible_label_changes':comparison(actual,'jev','final'),
              'eligible_verifier_rows':len(verified_rows),'eligible_verifier_unique_texts':len(verified),
              'eligible_jev_vs_blinded_luna_verifier':comparison(verified,'jev','verifier'),
              'incremental_rank_bands_verifier_proxy':bands,
              'actual_fallback_paired_against_verifier':paired_verifier(paired),
              'human_all_verdicts':dict(Counter(v['verdict'] for v in human['verdicts'].values())),
              'human_eligible_count':len(human_eligible),'human_eligible_verdicts':dict(Counter(i['verdict'] for i in human_eligible)),
              'human_eligible_details':human_eligible,'human_actual_fallback_details':human_actual,
              'cost_time_reference':{'cost_by_stage_usd':costs,'request_counts':requests,'root_counts':root_counts,
                                     'unit_luna_cost_per_text_including_repairs':unit,'repairs_per_text':repairs_per_text,
                                     'note':'Costs/routing from actual final-hash analysis tranche, including failures. Added fallback replaces extraction for long texts or local completion for short texts. New batch counts repacked offline; measured repair rates and 1rps pacing projected. Overlap and scaling/mix uncertainty remain.'},
              'scenarios':scenarios,
              'quality_limitations':['Actual fallback outcomes observed only in lowest-confidence 10% selected; no measured 20%/30% run.',
                 'Independent Luna verifier is a different blinded prompt, a proxy for potential label changes on unselected eligible rows, not human correctness or a counterfactual fallback response.',
                 'Human 20 are stratified disagreements, not representative; both-wrong supplies no corrected label. Intent judgments favor Jev in all4 reviewed intent disagreements.',
                 'Golden source IDs/texts are used solely to exclude them from development quality comparisons; no golden human answers or golden evaluation results are read.',
                 'Hash excludes operational fallback_fraction, but raising it can change newly routed predictions; choose before freezing production tranche. Existing completed/cache records are not relabeled.']}
    atomic_json(Path('docs/fallback-options-development.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'human_eligible_details','human_actual_fallback_details','cost_time_reference'}},indent=2))
    return result


if __name__=='__main__':
    build()
