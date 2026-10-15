"""Offline paired field changes with exact-text clustered descriptive intervals."""

import copy
import hashlib
import json
import random
from pathlib import Path

from pipeline.calibration import field_disagreement
from pipeline.classify import parse_jev
from pipeline.prepare import atomic_json
from pipeline.scaling_report import load_state, quantile


def inputs(directory):
    rows, events = load_state(directory/'state.sqlite3')
    replies = {event['review_ids'][0]:event['response'] for event in events if event['stage']=='jev' and event['outcome']=='succeeded'}
    by_key = {row['key']:replies[row['source']['review_id']] for row in rows if row['source']['review_id'] in replies}
    result = {}
    for row in rows:
        if row['key'] not in by_key:
            continue
        reply = copy.deepcopy(by_key[row['key']])
        reply['answers'] = {key:value for key,value in reply['answers'].items() if key in {'topic','intent','severity','sentiment'}}
        result[row['source']['review_id']] = {'core':parse_jev(reply,.6,0), 'final':row['result'],
            'text_hash':hashlib.sha256(row['source']['review_text'].encode()).hexdigest()}
    return result


def report():
    base = Path('artifacts/checkpoint-500')
    output = Path('artifacts/checkpoint-500-v3-ab')
    predictions = json.loads((base/'verifier.json').read_text(encoding='utf-8'))['predictions']
    a,b = inputs(base),inputs(output)
    result = {}
    for view in ('core','final'):
        ids = sorted(rid for rid in set(a)&set(b)&set(predictions) if a[rid][view] is not None and b[rid][view] is not None)
        groups = {}
        for rid in ids:
            groups.setdefault(a[rid]['text_hash'],[]).append(rid)
        clusters = list(groups.values())
        rng = random.Random('spotify-checkpoint-ab-paired-v1:'+view)
        draws = [[rng.randrange(len(clusters)) for _ in clusters] for _ in range(1000)]
        ae = {rid:field_disagreement(a[rid][view],predictions[rid]) for rid in ids}
        be = {rid:field_disagreement(b[rid][view],predictions[rid]) for rid in ids}
        fields = {}
        for field in next(iter(ae.values())):
            improved = sum(ae[rid][field] and not be[rid][field] for rid in ids)
            regressed = sum(not ae[rid][field] and be[rid][field] for rid in ids)
            counts = [(len(cluster),sum(int(be[rid][field])-int(ae[rid][field]) for rid in cluster)) for cluster in clusters]
            effects = [sum(counts[index][1] for index in draw)/sum(counts[index][0] for index in draw)*100 for draw in draws]
            fields[field] = {'rows':len(ids),'improved':improved,'regressed':regressed,
                'unchanged':len(ids)-improved-regressed,'change_percentage_points':(regressed-improved)/len(ids)*100,
                'difference_cluster_bootstrap_95_pp':[quantile(effects,.025),quantile(effects,.975)],
                'distinct_text_v2_disagreements':sum(ae[cluster[0]][field] for cluster in clusters),
                'distinct_text_v3_disagreements':sum(be[cluster[0]][field] for cluster in clusters),
                'distinct_text_denominator':len(clusters)}
        result[view] = {'rows':len(ids),'distinct_texts':len(clusters),'fields':fields}
    result['procedure'] = '1000 exact-text-cluster bootstrap draws, seed spotify-checkpoint-ab-paired-v1 per view; pointwise intervals, not adjusted for multiple fields. User pass criterion uses observed core rates, not these intervals. Fixed blinded verifier, not human accuracy.'
    atomic_json(output/'paired-details.json',result)
    print(json.dumps({'core_paired_fields':result['core']['fields'],'final_rows':result['final']['rows']},indent=2))


if __name__=='__main__':
    report()
