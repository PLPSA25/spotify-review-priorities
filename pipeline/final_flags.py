"""Offline final freeze and historical flag-rate proxy; never relabel paid evidence."""

import hashlib
import json
import tomllib
from collections import Counter
from pathlib import Path

from pipeline.classify import parse_jev
from pipeline.prepare import atomic_json
from pipeline.scaling_report import load_state
from pipeline.schema import configuration, record_schema


def freeze():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    routing = config['enrichment']
    if (routing['jev_prompt'],routing['confidence_threshold'],routing['probability_margin_threshold'],routing.get('needs_review_policy')) != ('jev-v3.json',.6,0,'persistent-context-reasons-v1'):
        raise ValueError('Approved final rules not configured')
    path = Path('docs/frozen-label-config.json')
    previous = json.loads(path.read_text(encoding='utf-8'))
    archive = Path('docs/frozen-label-config-before-reasons.json')
    if not archive.exists():
        archive.write_bytes(path.read_bytes())
    else:
        previous = json.loads(archive.read_text(encoding='utf-8'))
    frozen = {**previous, 'label_config':configuration(config),'models':config['models'],
        'enrichment':routing,'schema_version':record_schema(config),
        'prompt_file_sha256':{name:hashlib.sha256((Path('prompts')/name).read_bytes()).hexdigest()
            for name in (routing['jev_prompt'],routing['luna_prompt'])},
        'auxiliary_flag_policy':'Jev emits explicit reasons: nonenglish_understood -> language_non_english; not_understood -> language_not_understood; Noul >=.5 -> missing_context; minimum core confidence <.60 or minimum core Choice margin <0 -> low_confidence. Local completion preserves them. Extraction unions all Jev and Luna reasons. Independent fallback unions Luna reasons with Jev language and missing_context reasons, discarding only Jev low_confidence. Final needs_review equals bool(needs_review_reasons), with canonical unique reason order. An empty list is always present for unflagged completed records and direct cache aliases copy the list.',
        'new_prompt_evidence':'Jev-v3 measured on 3000 slices; .60/0 core separation confirmed on blinded v3 sample. Luna-v2 reason schema/prompt has no live evidence yet.',
        'previous_label_config':previous['label_config'],
        'final_freeze_basis':'User approved explicit final reasons and persistent missing_context from either model, including fallback; language flags unchanged and low confidence may clear at fallback. No historical paid record or call was rehashed.',
        'verification_transfer_evidence':'artifacts/scaling/transfer-verifier/report.json'}
    atomic_json(path,frozen)
    counts = Counter()
    proxy = []
    for workers in (1,2,8):
        rows, events = load_state(Path(f'artifacts/scaling/workers-{workers}/state.sqlite3'))
        replies = {event['review_ids'][0]:event['response'] for event in events if event['stage']=='jev' and event['outcome']=='succeeded'}
        fallback = {rid for event in events if event['stage']=='fallback' for rid in event.get('valid_review_ids',[])}
        for row in rows:
            rid = row['source']['review_id']
            labels = parse_jev(replies[rid],.6,0,True)
            reasons = labels['needs_review_reasons']
            known = [reason for reason in reasons if rid not in fallback or reason!='low_confidence']
            projected = row['result']['needs_review'] or 'missing_context' in known
            counts.update(known)
            counts['proxy_flagged'] += projected
            counts['restored_missing_context_flags'] += projected and not row['result']['needs_review']
            counts['unattributed_flagged_fallback'] += projected and not known
            counts['historical_flagged_fallback_without_reason_schema'] += rid in fallback and row['result']['needs_review']
            proxy.append({'review_id':rid,'historical_label_config':row['result']['label_config'],
                          'known_retained_reasons':known,'proxy_needs_review':bool(projected),
                          'new_luna_reasons_unavailable':rid in fallback})
    result = {'method':'Offline carry-forward proxy: retain historical final booleans, restore every stored Jev context flag, retain language and nonfallback confidence reasons. No new Luna-v2 outputs; missing context/uncertainty identified by that prompt is unmeasured. Not new-hash completed classifications.',
        'rows':3000,'counts':dict(counts),'proxy_flag_rate':counts['proxy_flagged']/3000,
        'known_reason_rates':{reason:counts[reason]/3000 for reason in ('language_non_english','language_not_understood','missing_context','low_confidence')},
        'old_label_config':previous['label_config'],'new_label_config':configuration(config),'api_calls':0}
    atomic_json(Path('docs/final-flag-offline-projection.json'),result)
    atomic_json(Path('artifacts/scaling/final-flag-offline-proxy.json'),{'summary':result,'items':proxy})
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    freeze()
