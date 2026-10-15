"""Offline freeze, development sentiment-sign check and sample-overlap audit."""

import csv
import hashlib
import itertools
import json
import sqlite3
import tomllib
from pathlib import Path

from pipeline.deterministic import POLICY
from pipeline.prepare import atomic_json
from pipeline.schema import configuration


def freeze():
    config=tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    routing=config['enrichment']
    if routing.get('needs_review_policy') == 'persistent-context-reasons-v1':
        from pipeline.final_flags import freeze as freeze_final
        freeze_final()
        return
    if (routing['confidence_threshold'],routing['probability_margin_threshold'],routing['fallback_selection_policy']) != (.6,0,POLICY):
        raise ValueError('Approved calibration/policy not configured')
    current=configuration(config)
    calibration=json.loads(Path('artifacts/checkpoint-500/calibration.json').read_text(encoding='utf-8'))
    if len(calibration['candidates'])!=35 or (calibration['recommendation']['confidence'],calibration['recommendation']['margin']) != (.6,0):
        raise ValueError('Approved development calibration evidence changed')
    frozen={'label_config':current,'models':config['models'],'enrichment':routing,
            'schema_version':'record-v1','extractor':'exact-v1','simulated':False,
            'prompt_file_sha256':{name:hashlib.sha256((Path('prompts')/name).read_bytes()).hexdigest()
                                 for name in (routing['jev_prompt'],'luna-enrich-v1.txt')},
            'excluded_from_label_hash':['controls including workers/fallback cap','scope','rates','verification','pilot'],
            'fallback_policy':'All Jev scores persisted; eligible exact texts ranked by minimum confidence, minimum Choice margin, exact-text SHA-256, canonical source ID. Persist selection and batch plan before Luna dispatch. Immutable extension tranches.',
            'approved_calibration_source':'checkpoint_500 development comparisons against blinded model verifier; not human accuracy',
            'confidence_scope':'Minimum topic/intent/severity/sentiment confidence; minimum topic/intent/severity Choice margin. Auxiliary language/context do not alter the calibrated confidence trigger.',
            'auxiliary_flag_policy':'Every returned non-English/not-understood language result or missing_context >= 0.5 forces needs_review; missing auxiliary answers invalidate v3 output.',
            'new_prompt_evidence':'v3 restores explicit language/missing-context judgments; unchanged v2 core questions. New prompt usage/quality not live-measured yet.',
            'calibration_record_label_config':calibration['current_hash'],
            'calibration_evidence_sha256':hashlib.sha256(Path('artifacts/checkpoint-500/calibration.json').read_bytes()).hexdigest(),
            'golden_policy':'No golden labels read for calibration, routing, prompts or design.'}
    atomic_json(Path('docs/frozen-label-config.json'),frozen)
    for name in ('calibration.csv','calibration_fields.csv'):
        (Path('docs')/name).write_bytes((Path('artifacts/checkpoint-500')/name).read_bytes())
    verifier=json.loads(Path('artifacts/checkpoint-500/verifier.json').read_text(encoding='utf-8'))
    with sqlite3.connect('file:artifacts/checkpoint-500/state.sqlite3?mode=ro',uri=True) as db:
        records=[json.loads(result) for result, in db.execute("SELECT result FROM reviews WHERE status='completed'")]
    counters={'total':0,'sign_disagreements':0,'near_zero_either':0,'near_zero_sign_disagreements':0,
              'far_sign_disagreements':0,'neutral_vs_nonzero_disagreements':0,'opposite_nonzero_sign_disagreements':0}
    for row in records:
        rid=row['review_id']
        if rid not in verifier['predictions']:
            continue
        first,second=row['sentiment'],verifier['predictions'][rid]['sentiment']
        different=(first>0)-(first<0)!=(second>0)-(second<0)
        near=abs(first)<.2 or abs(second)<.2
        counters['total']+=1
        counters['sign_disagreements']+=different
        counters['near_zero_either']+=near
        counters['near_zero_sign_disagreements']+=near and different
        counters['far_sign_disagreements']+=not near and different
        counters['neutral_vs_nonzero_disagreements']+=different and (first==0 or second==0)
        counters['opposite_nonzero_sign_disagreements']+=first*second<0
    counters.update(near_zero_definition='abs(sentiment) < 0.2 on either side; sign -1/0/+1 with exact zero neutral',
                    near_disagreement_rate=counters['near_zero_sign_disagreements']/counters['near_zero_either'],
                    far_disagreement_rate=counters['far_sign_disagreements']/(counters['total']-counters['near_zero_either']),
                    share_sign_disagreements_near_zero=counters['near_zero_sign_disagreements']/counters['sign_disagreements'],
                    share_all_rows_near_zero=counters['near_zero_either']/counters['total'])
    atomic_json(Path('docs/sentiment-sign-diagnostic.json'),counters)
    with Path('artifacts/sampling/permutation.csv').open(encoding='utf-8',newline='') as handle:
        prefix={row['review_id'] for row in itertools.islice(csv.DictReader(handle),config['scope']['sample_size'])}
    with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig',newline='') as handle:
        original_golden_ids={row['review_id'] for row in csv.DictReader(handle)}
    scope_ids=prefix|original_golden_ids
    with Path('data/analysis_10000.csv').open(encoding='utf-8-sig',newline='') as handle:
        analysis=list(csv.DictReader(handle))
    with sqlite3.connect('file:artifacts/ingestion/state.sqlite3?mode=ro',uri=True) as db:
        scope_texts={text for rid,text in db.execute('SELECT review_id,review_text FROM reviews') if rid in scope_ids}
    inside=[row for row in analysis if row['review_id'] in scope_ids]
    outside=[row for row in analysis if row['review_id'] not in scope_ids]
    outside_same_text=[row for row in outside if row['review_text'] in scope_texts]
    texts={row['review_text'] for row in analysis}
    overlap={'analysis_rows':len(analysis),'scope_ids':len(scope_ids),'inside_scope_by_original_id':len(inside),
             'outside_scope_by_original_id':len(outside),'outside_ids_whose_text_is_in_scope':len(outside_same_text),
             'inside_or_exact_text_reused_rows':len(inside)+len(outside_same_text),
             'analysis_distinct_texts':len(texts),'analysis_distinct_texts_reused_in_scope':len(texts&scope_texts),
             'analysis_distinct_texts_outside_scope_texts':len(texts-scope_texts),
             'reuse_status':'Potential reuse only; development work not paid yet. Requires identical frozen hash, succeeded enrich evidence and direct cache provenance.',
             'label_config':current}
    atomic_json(Path('docs/development-scope-overlap.json'),overlap)
    print(json.dumps({'freeze':current,'sentiment':counters,'overlap':overlap},indent=2))


if __name__=='__main__':
    freeze()
