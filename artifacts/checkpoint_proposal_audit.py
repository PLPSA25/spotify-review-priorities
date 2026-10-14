"""Offline checkpoint proposal from saved evidence; never reads human golden labels."""
import copy
import csv
import json
import sqlite3
import tomllib
from pathlib import Path

from pipeline.classify import jev_payload, luna_payload
from pipeline.schema import canonical, configuration
from pipeline.spend import token_cost

config = tomllib.loads(Path('config.toml').read_text())
events = [json.loads(line) for line in Path('cost/pilot_calls.jsonl').read_text().splitlines()]
records = [json.loads(line) for line in Path('cost/pilot_records.jsonl').read_text().splitlines()]
flagged = {r['review_id'] for r in records if r['needs_review']}
reasons = {name: set() for name in ['low_confidence', 'low_margin', 'nonenglish', 'missing_context']}
for event in events:
    if event['stage'] != 'jev' or event['outcome'] != 'succeeded':
        continue
    answers = event['response']['answers']
    rid = event['review_ids'][0]
    considered = [answers[n] for n in ['topic', 'intent', 'severity', 'sentiment', 'language'] if n in answers]
    if min(a['confidence'] for a in considered) < .75:
        reasons['low_confidence'].add(rid)
    margins = [sorted(a['probabilities'].values(), reverse=True) for a in considered if a['type'] != 'score']
    if min(p[0]-p[1] for p in margins) < .15:
        reasons['low_margin'].add(rid)
    if answers.get('language', {}).get('choice', 'english') != 'english':
        reasons['nonenglish'].add(rid)
    if answers.get('missing_context', {}).get('noul', 0) >= .5:
        reasons['missing_context'].add(rid)
union = set().union(*reasons.values())
luna = [{k: e.get(k) for k in ['request_id', 'stage', 'review_ids', 'outcome', 'cost_nanodollars']} for e in events if e['role']=='enrich' and e['provider']=='openai']
with Path('data/checkpoint_500.csv').open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
unique = {r['review_text']: r for r in rows if r['review_text'].strip()}
with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig', newline='') as f:
    golden_ids = {r['review_id'] for r in csv.DictReader(f)}
rates = dict(config['planning_rates'])
rates['luna_input_per_million'] = max(rates['luna_input_per_million'], rates['luna_cache_write_per_million'])
costs = {'jev': 0, 'luna_enrich': 0, 'verify': 0}
luna_singletons = []
for row in unique.values():
    for provider, payload in [('typesafe', jev_payload(row['review_text'], config)), ('openai', luna_payload(row, {}, config, False))]:
        # Singleton envelope including 1024 extra bytes for repair diagnostics.
        inputs = len(canonical(payload).encode()) + config['controls']['token_overhead_bound'] + 1024
        outputs = 0 if provider == 'typesafe' else 200
        attempts = 2
        if provider == 'typesafe':
            costs['jev'] += token_cost(inputs, outputs, rates, provider) * attempts
        else:
            luna_singletons.append(token_cost(inputs, outputs, rates, provider) * attempts)
fallback_max = int(len(unique)*config['controls']['fallback_fraction'])
luna_ids_max = sum(len(t)>240 for t in unique) + fallback_max
costs['luna_enrich'] = sum(sorted(luna_singletons, reverse=True)[:luna_ids_max])
verify_n = len([r for r in rows if r['review_id'] not in golden_ids])
verify_batches = (verify_n+49)//50
costs['verify'] = verify_batches*token_cost(24000,10000,rates,'openai') + verify_n*token_cost(10000,200,rates,'openai')
with sqlite3.connect('file:artifacts/spend.sqlite3?mode=ro', uri=True) as db:
    spent,reserved=db.execute("SELECT SUM(spent), SUM(CASE WHEN state='reserved' THEN amount ELSE 0 END) FROM reservations").fetchone()
scaled=copy.deepcopy(config)
scaled['controls']['max_workers']=2
scaled['controls']['fallback_fraction']=.05
result = {'pilot_flagged': len(flagged), 'pilot_denominator':len(records),
          'reason_counts_overlapping_flagged': {k:len(v & flagged) for k,v in reasons.items()},
          'unexplained_flagged':len(flagged-union), 'jev_reason_union':len(union),
          'luna_calls':luna, 'fallback_unique_ids':len(set(r for e in luna if e['stage']=='fallback' for r in e['review_ids'])),
          'config_hash':configuration(config), 'workers_and_cap_hash_unchanged':configuration(config)==configuration(scaled),
          'checkpoint_rows':len(rows),'distinct_texts':len(unique),'long_texts':sum(len(t)>240 for t in unique),
          'golden_overlap': len(golden_ids & {r['review_id'] for r in rows}),
          'cache_condition':'cold empty result cache; no pilot reuse for comparison',
          'workers':2,'verification_reviews':verify_n,'verification_initial_batches':verify_batches,
          'cost_bounds_nanodollars':costs,'total_worst_case_nanodollars':sum(costs.values()),
          'project_spent_nanodollars':spent,'project_reserved_nanodollars':reserved,
          'transient_attempts':1,'invalid_output_repairs':1,
          'fallback_ids_upper':fallback_max,'luna_enrich_ids_upper':luna_ids_max,
          'initial_calls_upper':len(unique)+luna_ids_max+verify_batches,
          'maximum_calls':len(unique)*2+luna_ids_max*2+verify_batches+verify_n,
          'approval_status':'awaiting_yes; no paid calls made'}
Path('docs/checkpoint-500-proposal.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
