"""Offline development-only triage diagnostics; golden answers are never read."""

import csv
import json
import random
import sqlite3
import tomllib
from pathlib import Path

from pipeline.classify import parse_jev
from pipeline.prepare import atomic_json
from pipeline.schema import configuration


def disagreement(a, b):
    fields = [field for field in ('topic', 'intent', 'severity') if a[field] != b[field]]
    if abs(a['sentiment'] - b['sentiment']) > .25:
        fields.append('sentiment')
    return fields


def field_disagreement(a, b):
    sign = lambda value: (value > 0) - (value < 0)
    return {'topic': a['topic'] != b['topic'], 'intent': a['intent'] != b['intent'],
            'severity_exact': a['severity'] != b['severity'],
            'severity_beyond_one': abs(a['severity'] - b['severity']) > 1,
            'sentiment_sign': sign(a['sentiment']) != sign(b['sentiment']),
            'sentiment_tolerance_025': abs(a['sentiment'] - b['sentiment']) > .25}


def field_summary(items, kind='final'):
    names=('topic','intent','severity_exact','severity_beyond_one','sentiment_sign','sentiment_tolerance_025')
    return {name: {'disagreements': sum(item[kind+'_field_errors'][name] for item in items),
                   'denominator': len(items),
                   'rate': sum(item[kind+'_field_errors'][name] for item in items)/len(items) if items else None}
            for name in names}


def analyze(directory=Path('artifacts/checkpoint-500'), allow_partial=False):
    verifier = json.loads((directory / 'verifier.json').read_text(encoding='utf-8'))
    if not verifier['complete'] and not allow_partial:
        raise ValueError('Incomplete verifier: no calibration')
    with sqlite3.connect(f'file:{directory.as_posix()}/state.sqlite3?mode=ro', uri=True) as db:
        rows = [{'source': json.loads(source), 'result': json.loads(result), 'key': key}
                for source, result, key in db.execute("SELECT source,result,work_key FROM reviews WHERE status='completed'")]
        events = [json.loads(event) for event, in db.execute('SELECT event FROM calls')]
    responses = {event['review_ids'][0]: event['response'] for event in events
                 if event['stage'] == 'jev' and event['outcome'] == 'succeeded'}
    key_response = {row['key']: responses[row['source']['review_id']] for row in rows if row['source']['review_id'] in responses}
    metrics = []
    grouped = {}
    for row in rows:
        if row['source']['review_id'] not in verifier['predictions']:
            continue
        rid = row['source']['review_id']
        response = key_response[row['key']]
        answers = response['answers']
        considered = [answers[name] for name in ('topic', 'intent', 'severity', 'sentiment', 'language') if name in answers]
        confidence = min(answer['confidence'] for answer in considered)
        margins = [sorted(answer['probabilities'].values(), reverse=True) for answer in considered if answer['type'] != 'score']
        margin = min(values[0]-values[1] for values in margins)
        original = parse_jev(response, .75, .15)
        prediction = verifier['predictions'][rid]
        item = {'review_id': rid, 'key': row['key'], 'confidence': confidence, 'margin': margin,
                'always_flag': original['nonenglish'] or answers.get('missing_context', {}).get('noul', 0) >= .5,
                'nonenglish': original['nonenglish'], 'final_flag': row['result']['needs_review'],
                'jev_disagreements': disagreement(original, prediction),
                'final_disagreements': disagreement(row['result'], prediction),
                'jev_field_errors':field_disagreement(original,prediction),
                'final_field_errors':field_disagreement(row['result'],prediction)}
        metrics.append(item)
        grouped.setdefault(row['key'], []).append(item)
    candidates = []
    keys = sorted(grouped)
    # Fixed bootstrap samples reuse identical text clusters across all candidate pairs.
    rng = random.Random('spotify-checkpoint-calibration-v1')
    samples = [[rng.randrange(len(keys)) for _ in keys] for _ in range(1000)]
    for confidence in (.4, .5, .6, .65, .7, .75, .8):
        for margin in (0, .05, .1, .15, .2):
            flags = {item['review_id']: item['always_flag'] or item['confidence'] < confidence or item['margin'] < margin for item in metrics}
            flagged = [item for item in metrics if flags[item['review_id']]]
            unflagged = [item for item in metrics if not flags[item['review_id']]]
            candidate = {'confidence': confidence, 'margin': margin, 'flagged': len(flagged), 'unflagged': len(unflagged), 'flag_rate': len(flagged)/len(metrics)}
            for kind in ('jev', 'final'):
                field = kind + '_disagreements'
                f = sum(bool(item[field]) for item in flagged)
                u = sum(bool(item[field]) for item in unflagged)
                fr = f/len(flagged) if flagged else None
                ur = u/len(unflagged) if unflagged else None
                effects = []
                clusters = [[sum(flags[i['review_id']] for i in grouped[key]),
                             sum(not flags[i['review_id']] for i in grouped[key]),
                             sum(flags[i['review_id']] and bool(i[field]) for i in grouped[key]),
                             sum(not flags[i['review_id']] and bool(i[field]) for i in grouped[key])] for key in keys]
                for sample in samples:
                    counts = [sum(clusters[index][column] for index in sample) for column in range(4)]
                    if counts[0] and counts[1]:
                        effects.append(counts[2]/counts[0] - counts[3]/counts[1])
                effects.sort()
                candidate[kind] = {'flagged_disagreements': f, 'unflagged_disagreements': u,
                                   'fields_overall':field_summary(metrics,kind),
                                   'fields_flagged':field_summary(flagged,kind),
                                   'fields_unflagged':field_summary(unflagged,kind),
                                   'flagged_rate': fr, 'unflagged_rate': ur,
                                   'difference': fr-ur if fr is not None and ur is not None else None,
                                   'difference_cluster_bootstrap_95': [effects[int(.025*len(effects))], effects[min(len(effects)-1,int(.975*len(effects)))]] if effects else None,
                                   'per_field': {name: {'flagged': sum(name in item[field] for item in flagged), 'unflagged': sum(name in item[field] for item in unflagged)} for name in ('topic', 'intent', 'severity', 'sentiment')}}
            candidates.append(candidate)
    qualifying = [c for c in candidates if min(c['flagged'], c['unflagged']) >= 25
                  and all(c[k]['difference_cluster_bootstrap_95'][0] > .05
                          and c[k]['flagged_rate'] >= 1.5*c[k]['unflagged_rate'] for k in ('jev', 'final'))]
    recommendation = max(qualifying, key=lambda c: min(c[k]['difference_cluster_bootstrap_95'][0] for k in ('jev', 'final'))) if qualifying else None
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    proposed = json.loads(json.dumps(config))
    if recommendation:
        proposed['enrichment'].update(confidence_threshold=recommendation['confidence'], probability_margin_threshold=recommendation['margin'])
    result = {'data':'checkpoint_500 development only; no golden evaluation', 'rows':len(metrics), 'distinct_texts':len(keys),
              'verifier_complete': verifier['complete'], 'missing_verifier_records':len(rows)-len(metrics),
              'excluded_terminal_records':len(verifier.get('terminal_failures',{})),
              'unprocessed_records':len(rows)-len(metrics)-len(verifier.get('terminal_failures',{})),
              'actual_final_flags_field_summary':{'overall':field_summary(metrics),
                  'flagged':field_summary([item for item in metrics if item['final_flag']]),
                  'unflagged':field_summary([item for item in metrics if not item['final_flag']])},
              'final_flagged':sum(item['final_flag'] for item in metrics), 'nonenglish':sum(item['nonenglish'] for item in metrics),
              'endpoint':'Any topic/intent/severity disagreement or sentiment absolute difference > 0.25; excludes entities and needs_review.',
              'procedure':'Exploratory grid, 1000 exact-text cluster bootstrap samples, seed spotify-checkpoint-calibration-v1. Intervals are pointwise, not multiplicity adjusted; verifier is not human truth.',
              'recommendation':recommendation if verifier['complete'] else None,
              'exploratory_partial_candidate':recommendation if not verifier['complete'] else None,
              'current_hash':configuration(config), 'proposed_hash':configuration(proposed) if verifier['complete'] else configuration(config),
              'policy_status':'proposed only; records and frozen runtime configuration unchanged', 'candidates':candidates}
    atomic_json(directory / 'calibration.json', result)
    atomic_json(directory / 'calibration_items.json', metrics)
    with (directory/'calibration_fields.csv').open('w',encoding='utf-8',newline='') as handle:
        writer=csv.writer(handle)
        writer.writerow(['confidence','margin','prediction','group','field','disagreements','denominator','rate'])
        for candidate in candidates:
            for kind in ('jev','final'):
                for group in ('overall','flagged','unflagged'):
                    for field,values in candidate[kind]['fields_'+group].items():
                        writer.writerow([candidate['confidence'],candidate['margin'],kind,group,field,values['disagreements'],values['denominator'],values['rate']])
    with (directory / 'calibration.csv').open('w',encoding='utf-8',newline='') as handle:
        writer=csv.writer(handle)
        writer.writerow(['confidence','margin','flagged','unflagged','flag_rate','jev_flagged_disagreements','jev_unflagged_disagreements','final_flagged_disagreements','final_unflagged_disagreements','final_flagged_rate','final_unflagged_rate','final_difference_lower95','final_difference_upper95'])
        for c in candidates:
            writer.writerow([c['confidence'],c['margin'],c['flagged'],c['unflagged'],c['flag_rate'],c['jev']['flagged_disagreements'],c['jev']['unflagged_disagreements'],c['final']['flagged_disagreements'],c['final']['unflagged_disagreements'],c['final']['flagged_rate'],c['final']['unflagged_rate'],*(c['final']['difference_cluster_bootstrap_95'] or [None,None])])
    print(json.dumps({key:value for key,value in result.items() if key!='candidates'},indent=2))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-partial', action='store_true')
    args=parser.parse_args()
    analyze(allow_partial=args.allow_partial)
