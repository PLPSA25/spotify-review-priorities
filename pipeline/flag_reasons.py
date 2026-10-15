"""Offline observability export: preserve initial signals versus final flag origin."""

import csv
import json
import tomllib
from collections import Counter
from pathlib import Path

from pipeline.classify import parse_jev
from pipeline.deterministic import ranking_scores
from pipeline.prepare import atomic_json
from pipeline.scaling_report import load_state
from pipeline.schema import configuration


def describe(response, record, fallback, confidence=.6, margin=0):
    labels = parse_jev(response, confidence, margin, require_auxiliary=True)
    scores = ranking_scores(response)
    missing = response['answers']['missing_context']['noul'] >= .5
    signals = []
    if labels['nonenglish']:
        signals.append('language')
    if missing:
        signals.append('missing_context')
    if labels['low_confidence']:
        signals.append('low_confidence')
    final_reasons = []
    if record['needs_review']:
        if not fallback:
            final_reasons = signals.copy()
        else:
            if labels['nonenglish']:
                final_reasons.append('language')
            # No final reason schema exists for independent fallback output.
            final_reasons.append('fallback_judgment_unattributed')
    return {'review_id': record['review_id'], 'label_config': record['label_config'],
            'language_choice': response['answers']['language']['choice'],
            'missing_context_probability': response['answers']['missing_context']['noul'],
            **scores, 'initial_language': labels['nonenglish'], 'initial_missing_context': missing,
            'initial_low_confidence': labels['low_confidence'],
            'initial_below_confidence': scores['confidence'] < confidence,
            'initial_below_margin': scores['margin'] < margin,
            'initial_reasons': signals, 'initial_needs_review': labels['needs_review'],
            'final_needs_review': record['needs_review'], 'classification_fallback': fallback,
            'initial_flag_cleared_by_fallback': labels['needs_review'] and not record['needs_review'],
            'final_reason_attribution': final_reasons,
            'final_reason_complete': not (record['needs_review'] and fallback)}


def export():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    items = []
    for workers in (1, 2, 8):
        rows, events = load_state(Path(f'artifacts/scaling/workers-{workers}/state.sqlite3'))
        responses = {event['review_ids'][0]: event['response'] for event in events
                     if event['stage']=='jev' and event['outcome']=='succeeded'}
        by_key = {row['key']: responses[row['source']['review_id']] for row in rows if row['source']['review_id'] in responses}
        fallback_keys = {row['key'] for row in rows if any(row['source']['review_id'] in event.get('valid_review_ids', [])
                         for event in events if event['stage']=='fallback')}
        for row in rows:
            if row['result']['label_config'] != configuration(config):
                raise ValueError('Export config mismatch')
            items.append(describe(by_key[row['key']], row['result'], row['key'] in fallback_keys,
                config['enrichment']['confidence_threshold'],config['enrichment']['probability_margin_threshold']))
    path = Path('artifacts/scaling/flag-reasons.csv')
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(items[0]))
        writer.writeheader()
        for item in items:
            writer.writerow({key: json.dumps(value) if isinstance(value,list) else value for key,value in item.items()})
    initial = Counter(reason for item in items for reason in item['initial_reasons'])
    final = Counter(reason for item in items for reason in item['final_reason_attribution'])
    summary = {'rows': len(items), 'initial_overlapping_reason_counts': dict(initial),
               'final_overlapping_attributable_counts': dict(final),
               'cleared_initial_flags': sum(item['initial_flag_cleared_by_fallback'] for item in items),
               'final_reason_incomplete': sum(not item['final_reason_complete'] for item in items),
               'label_config': configuration(config), 'calls': 0,
               'note': 'Observability only. Initial reason signals are not necessarily the cause of a final fallback flag. Original labels/calls/config unchanged.'}
    atomic_json(Path('artifacts/scaling/flag-reasons-summary.json'),summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    export()
