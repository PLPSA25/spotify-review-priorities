"""Evaluation-only reader of human golden answers; never feeds production config."""
import csv
import hashlib
import json
import sqlite3
import tomllib
from contextlib import closing
from pathlib import Path

from pipeline.labels import validate_golden
from pipeline.prepare import atomic_json, course_helper
from pipeline.schema import INTENTS, TOPICS, configuration, validate_record


def sign(value):
    return 'negative' if value < 0 else 'positive' if value > 0 else 'neutral'


def metrics(human, predictions):
    """Pure comparison; all reference rows stay in accuracy/confusion denominators."""
    fields = {'topic':list(TOPICS),'intent':list(INTENTS),'severity':[1,2,3,4,5],
              'sentiment_sign':['negative','neutral','positive'],'needs_review':[False,True]}
    summaries, tables = {}, {}
    missing = '<missing>'
    for field, values in fields.items():
        matrix = [[0 for _ in [*values,missing]] for _ in values]
        correct = 0
        for rid, truth in human.items():
            prediction = predictions.get(rid)
            target = sign(truth['sentiment']) if field=='sentiment_sign' else truth[field]
            actual = (sign(prediction['sentiment']) if field=='sentiment_sign' else prediction[field]) if prediction else missing
            matrix[values.index(target)][[*values,missing].index(actual)] += 1
            correct += actual==target
        summaries[field] = {'agree':correct,'denominator':len(human),'agreement':correct/len(human) if human else None}
        tables[field] = {'rows_human':values,'columns_prediction':[*values,missing],'counts':matrix}
    bands = [[0,0,0] for _ in range(5)]
    severity_errors, sentiment_errors = [], []
    within = 0
    for rid, truth in human.items():
        prediction = predictions.get(rid)
        if prediction is None:
            bands[truth['severity']-1][2] += 1
            continue
        delta = abs(truth['severity']-prediction['severity'])
        within += delta<=1
        bands[truth['severity']-1][int(delta>1)] += 1
        severity_errors.append(delta)
        sentiment_errors.append(abs(truth['sentiment']-prediction['sentiment']))
    summaries['severity_within_one'] = {'agree':within,'denominator':len(human),'agreement':within/len(human) if human else None}
    summaries['severity_mae'] = {'value':sum(severity_errors)/len(severity_errors) if severity_errors else None,'denominator_available_predictions':len(severity_errors)}
    summaries['sentiment_mae'] = {'value':sum(sentiment_errors)/len(sentiment_errors) if sentiment_errors else None,'denominator_available_predictions':len(sentiment_errors)}
    summaries['sentiment_within_025'] = {'agree':sum(x<=.25 for x in sentiment_errors),'denominator':len(human),'agreement':sum(x<=.25 for x in sentiment_errors)/len(human) if human else None}
    tables['severity_within_one'] = {'rows_human':[1,2,3,4,5],'columns_prediction':['within_one','beyond_one',missing],'counts':bands}
    return {'agreement':summaries,'confusion':tables,'missing_predictions':len(set(human)-set(predictions))}


def fallback_partition(state_path, ids, label_config):
    """Route grouping by actual work/call ancestry, before looking at human answers."""
    with closing(sqlite3.connect(f'file:{state_path.as_posix()}?mode=ro',uri=True)) as db:
        if db.execute("SELECT value FROM metadata WHERE key='label_config'").fetchone()[0]!=label_config:
            raise ValueError('Routing state hash differs')
        keys = {rid:key for rid,key in db.execute('SELECT review_id,work_key FROM reviews') if rid in ids}
        used = {key for key, in db.execute("SELECT DISTINCT r.work_key FROM call_reviews c JOIN reviews r ON c.review_id=r.review_id WHERE c.stage='fallback'")}
    if set(keys)!=set(ids):
        raise ValueError('Golden IDs missing from routing state')
    return {rid:key in used for rid,key in keys.items()}


def write_tables(output, result):
    output.mkdir(parents=True,exist_ok=True)
    for field, table in result['confusion'].items():
        with (output/(field+'-confusion.csv')).open('w',encoding='utf-8',newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['human / prediction',*table['columns_prediction']])
            writer.writerows([label,*counts] for label,counts in zip(table['rows_human'],table['counts'],strict=True))


def evaluate(predictions_path, output, labels_path=Path('evals/golden_50_human.csv'), source=Path('data/golden_50_to_label.csv'), state_path=None):
    if output.resolve().is_relative_to(Path('data').resolve()):
        raise ValueError('Never write evaluation into preserved data')
    helper = course_helper(Path('data/check_submission.py'))
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    frozen = json.loads(Path('docs/frozen-label-config.json').read_text(encoding='utf-8'))
    if configuration(config)!=frozen['label_config']:
        raise ValueError('Frozen final hash changed before evaluation')
    records = [json.loads(line) for line in predictions_path.read_text(encoding='utf-8').splitlines() if line]
    predictions = {record['review_id']:record for record in records}
    original = {r['review_id']:r for r in helper.csv_rows(source)}
    if len(records)!=len(predictions) or set(predictions)-set(original) or any(record['label_config']!=configuration(config) for record in records):
        raise ValueError('Prediction IDs/configuration differ from frozen golden evaluation')
    for rid, prediction in predictions.items():
        row = original[rid]
        record_source = {field:row[field] for field in helper.FIELDS}
        record_source['source_sha256'] = helper.row_sha(record_source)
        validate_record(prediction,record_source,configuration(config),require_reasons=True)
    route_path = state_path or predictions_path.parent/'state.sqlite3'
    routed = fallback_partition(route_path,set(original),configuration(config)) if route_path.exists() else None
    # Human answers are opened only after the supplied predictions pass preflight.
    validation = validate_golden(labels_path,source,output/'validation.json')
    if validation['status']!='valid':
        raise ValueError('Human golden validation failed; inspect validation report')
    human = {}
    for row in helper.csv_rows(labels_path):
        human[row['review_id']] = {'topic':row['topic'],'intent':row['intent'],
                                  'severity':int(row['severity']),'sentiment':float(row['sentiment']),
                                  'needs_review':row['needs_review']=='true'}
    result = metrics(human,predictions)
    result['fallback_split_available'] = routed is not None
    if routed is not None:
        result['by_fallback'] = {}
        for name, flag in (('luna_fallback',True),('no_luna_fallback',False)):
            selected = {rid:truth for rid,truth in human.items() if routed[rid]==flag}
            subset = metrics(selected,{rid:predictions[rid] for rid in selected if rid in predictions})
            subset['n'] = len(selected)
            result['by_fallback'][name] = subset
            write_tables(output/name,subset)
        result['fallback_group_definition'] = 'Actual independent classification-fallback call ancestry by exact-text work key, including inherited cached results. Extraction-only Luna calls are not classification fallback. Missing predictions remain in their routed group denominator.'
        result['fallback_caution'] = 'Small n, especially fallback; nonrandom confidence-based routing and cache reuse. Group differences are descriptive, not causal fallback benefit. No routing recommendation uses golden results.'
    details = []
    for rid, truth in human.items():
        prediction = predictions.get(rid)
        fields = [field for field in ('topic','intent','severity','needs_review') if prediction is None or truth[field]!=prediction[field]]
        if prediction is None or sign(truth['sentiment'])!=sign(prediction['sentiment']):
            fields.append('sentiment_sign')
        if fields:
            details.append({'review_id':rid,'disagreeing_fields':fields,'human':truth,
                            'prediction':{key:prediction[key] for key in truth} if prediction else None})
    result.update(label_config=configuration(config),entities_evaluated=False,
                  prediction_sha256=hashlib.sha256(predictions_path.read_bytes()).hexdigest(),
                  human_labels_sha256=hashlib.sha256(labels_path.read_bytes()).hexdigest(),
                  model_calls=0,disagreements=details,
                  entities_exclusion='Entities were not hand-labeled; empty by design. Excluded from all golden metrics.',
                  limitation='50 owner-labeled IDs; model agreement is not a guarantee on the corpus. Four labels revised after AI-assisted contract check, final decisions by owner. Golden results never tune prompts, thresholds or routing.',
                  quote_support='Exact-substring validity is checked by enrichment; semantic quote support is not inferred from substring validity or equality with a human quote.')
    atomic_json(output/'report.json',result)
    write_tables(output,result)
    return result
