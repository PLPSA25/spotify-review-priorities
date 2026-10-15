"""Offline v3 verifier comparisons and proposed flag policy; never apply it."""

import csv
import json
import random
import tomllib
from pathlib import Path

from pipeline.calibration import disagreement, field_disagreement, field_summary
from pipeline.classify import parse_jev
from pipeline.deterministic import ranking_scores
from pipeline.prepare import atomic_json
from pipeline.scaling_report import load_state, quantile
from pipeline.schema import configuration

ROOT = Path('artifacts/scaling')
OUTPUT = ROOT / 'transfer-verifier'


def summary(items):
    result = {'n': len(items)}
    for kind in ('jev', 'final'):
        errors = sum(bool(item[kind+'_disagreements']) for item in items)
        result[kind] = {'disagreements': errors, 'rate': errors/len(items) if items else None,
                        'fields': field_summary(items, kind)}
    return result


def contrast(items, flagged_ids, bootstrap=None):
    flagged = [item for item in items if item['review_id'] in flagged_ids]
    unflagged = [item for item in items if item['review_id'] not in flagged_ids]
    result = {'flagged': summary(flagged), 'unflagged': summary(unflagged),
              'flag_rate': len(flagged)/len(items) if items else None}
    for kind in ('jev', 'final'):
        f, u = result['flagged'][kind]['rate'], result['unflagged'][kind]['rate']
        difference = f-u if f is not None and u is not None else None
        intervals = []
        if bootstrap is not None:
            counts = [(int(item['review_id'] in flagged_ids), int(bool(item[kind+'_disagreements']))) for item in items]
            for sample in bootstrap:
                fn = fe = un = ue = 0
                for index in sample:
                    flag, error = counts[index]
                    if flag:
                        fn += 1
                        fe += error
                    else:
                        un += 1
                        ue += error
                if fn and un:
                    intervals.append(fe/fn-ue/un)
        result[kind] = {'difference': difference,
                        'relative_rate': f/u if f is not None and u else None,
                        'difference_bootstrap_95': [quantile(intervals, .025), quantile(intervals, .975)] if intervals else None}
    return result


def qualifies(candidate):
    return min(candidate['flagged']['n'], candidate['unflagged']['n']) >= 25 and all(
        candidate[kind]['difference_bootstrap_95'] is not None
        and candidate[kind]['difference_bootstrap_95'][0] > .05
        and candidate[kind]['relative_rate'] is not None
        and candidate[kind]['relative_rate'] >= 1.5 for kind in ('jev', 'final'))


def report():
    saved = json.loads((OUTPUT/'verifier.json').read_text(encoding='utf-8'))
    measurement = json.loads((OUTPUT/'measurements.json').read_text(encoding='utf-8'))
    if not saved['complete'] or not measurement['status'].startswith('completed'):
        raise ValueError('Verifier not at completed gate')
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    if configuration(config) != measurement['label_config']:
        raise ValueError('Frozen config mismatch')
    rows, events = [], []
    for workers in (1, 2, 8):
        state_rows, state_events = load_state(ROOT/f'workers-{workers}/state.sqlite3')
        rows.extend(state_rows)
        events.extend(state_events)
    responses = {event['review_ids'][0]: event['response'] for event in events
                 if event['stage']=='jev' and event['outcome']=='succeeded'}
    fallback_ids = {rid for event in events if event['stage']=='fallback' for rid in event.get('valid_review_ids', [])}
    population, items = [], []
    for row in rows:
        rid = row['source']['review_id']
        response = responses[rid]
        scores = ranking_scores(response)
        original = parse_jev(response, .6, 0, require_auxiliary=True)
        language = response['answers']['language']['choice']
        item = {'review_id': rid, **scores, 'language': language,
                'nonenglish': language!='english',
                'missing_context': response['answers']['missing_context']['noul']>=.5,
                'triage_flag': original['needs_review'], 'final_flag': row['result']['needs_review'],
                'fallback': rid in fallback_ids}
        item['auxiliary_only'] = original['needs_review'] and not original['low_confidence']
        population.append(item)
        if rid not in saved['predictions']:
            continue
        verifier = saved['predictions'][rid]
        item.update(verifier_language=verifier['language'], verifier_missing_context=verifier['missing_context'],
                    jev_disagreements=disagreement(original, verifier),
                    final_disagreements=disagreement(row['result'], verifier),
                    jev_field_errors=field_disagreement(original, verifier),
                    final_field_errors=field_disagreement(row['result'], verifier))
        items.append(item)
    rng = random.Random('spotify-v3-transfer-calibration-v1')
    bootstrap = [[rng.randrange(len(items)) for _ in items] for _ in range(1000)]
    candidates = []
    for confidence in (.4, .5, .6, .65, .7, .75, .8):
        for margin in (0, .05, .1, .15, .2):
            ids = {item['review_id'] for item in items if item['confidence']<confidence or item['margin']<margin}
            candidate = {'confidence': confidence, 'margin': margin, **contrast(items, ids, bootstrap)}
            candidate['material_separation'] = qualifies(candidate)
            candidates.append(candidate)
    qualifying = [candidate for candidate in candidates if candidate['material_separation']]
    strongest = max(qualifying, key=lambda candidate: min(candidate[kind]['difference_bootstrap_95'][0] for kind in ('jev', 'final'))) if qualifying else None
    frozen_candidate = next(candidate for candidate in candidates if candidate['confidence']==.6 and candidate['margin']==0)
    # Preserve the predeclared cutoff when transfer evidence supports it; avoid
    # selecting a new extreme from the same exploratory validation sample.
    chosen = frozen_candidate if frozen_candidate['material_separation'] else strongest
    confidence, margin = (chosen['confidence'], chosen['margin']) if chosen else (0, 0)
    unflagged = [item for item in items if not item['triage_flag']]
    reasons = {'nonenglish_any': lambda item: item['nonenglish'],
               'nonenglish_understood': lambda item: item['language']=='nonenglish_understood',
               'not_understood': lambda item: item['language']=='not_understood',
               'missing_context': lambda item: item['missing_context']}
    auxiliary = {}
    for reason, predicate in reasons.items():
        selected = [item for item in items if item['auxiliary_only'] and predicate(item)]
        reason_rng = random.Random('spotify-v3-auxiliary:'+reason)
        reason_bootstrap = [[reason_rng.randrange(len(selected)+len(unflagged))
                            for _ in range(len(selected)+len(unflagged))] for _ in range(1000)]
        auxiliary[reason] = {'all_3000_auxiliary_only_count': sum(item['auxiliary_only'] and predicate(item) for item in population),
                             'all_3000_reason_count_including_core_overlap': sum(predicate(item) for item in population),
                             'sample_auxiliary_only': summary(selected), 'sample_frozen_unflagged': summary(unflagged),
                             'verifier_missing_context_count_in_auxiliary_only_cohort': sum(item['verifier_missing_context'] for item in selected),
                             'vs_unflagged': contrast(selected+unflagged, {item['review_id'] for item in selected}, reason_bootstrap)}
    # Fallback's opaque needs_review may add a final flag without any Jev trigger.
    judgment = [item for item in items if item['final_flag'] and not item['triage_flag']]
    judgment_other = [item for item in unflagged if item not in judgment]
    judgment_rng = random.Random('spotify-v3-auxiliary:luna-judgment')
    judgment_bootstrap = [[judgment_rng.randrange(len(judgment)+len(judgment_other))
                          for _ in range(len(judgment)+len(judgment_other))] for _ in range(1000)]
    auxiliary['luna_final_flag_without_jev_trigger'] = {
        'all_3000_count': sum(item['final_flag'] and not item['triage_flag'] for item in population),
        'sample': summary(judgment), 'vs_frozen_unflagged': contrast(
            judgment+judgment_other, {item['review_id'] for item in judgment}, judgment_bootstrap),
        'note': 'Opaque Luna judgment has no separate reason field. These rows are also in frozen initial-unflagged; compare to other initial-unflagged rows to avoid overlap.'}
    language_items = [item for item in items if item['nonenglish']]
    language_confirmation = {'sample_jev_nonenglish_flagged': len(language_items),
        'verifier_nonenglish_understood': sum(item['verifier_language']=='nonenglish_understood' for item in language_items),
        'verifier_english': sum(item['verifier_language']=='english' for item in language_items),
        'verifier_not_understood_language_unconfirmed': sum(item['verifier_language']=='not_understood' for item in language_items),
        'verifier_same_broad_nonenglish_or_ununderstood_bucket': sum(item['verifier_language']!='english' for item in language_items),
        'verifier_nonenglish_on_jev_english': sum(item['verifier_language']=='nonenglish_understood' and not item['nonenglish'] for item in items)}
    language_confirmation['confusion'] = {first: {second: sum(item['language']==first and item['verifier_language']==second for item in items)
        for second in ('english','nonenglish_understood','not_understood')} for first in ('english','nonenglish_understood','not_understood')}
    buckets = {}
    for lang, context in ((True, False), (False, True), (True, True)):
        name = f'nonenglish_{lang}_missing_context_{context}'
        buckets[name] = {'population': sum(item['auxiliary_only'] and item['nonenglish']==lang and item['missing_context']==context for item in population),
                         'sample': summary([item for item in items if item['auxiliary_only'] and item['nonenglish']==lang and item['missing_context']==context])}
    def proposed_flag(item):
        return item['nonenglish'] or item['missing_context'] or item['confidence']<confidence or item['margin']<margin
    proposed_config = json.loads(json.dumps(config))
    proposed_config['enrichment'].update(confidence_threshold=confidence, probability_margin_threshold=margin,
        needs_review_policy='required-context-core-v1')
    policy = {'status': 'proposed only; never applied', 'confidence': confidence, 'margin': margin,
              'core_retained': chosen is not None,
              'rule': 'For every final record: original Jev language != english OR missing_context >= .5 OR core confidence/margin below chosen values. Fallback no longer clears these required/core flags.',
              'required_reasons': ['non-English/ununderstood declared rule', 'missing context contract rule'],
              'optional_auxiliary_reasons_dropped': ['unexplained Luna needs_review has no independent reason; it is not a separate proposed trigger'],
              'optional_auxiliary_reason_count': int(bool(judgment)),
              'chosen_core_candidate': chosen,
              'selection_reason': 'Retain the predeclared 0.60/0 if it materially separates both Jev and final disagreement; no target flag rate and no unnecessary post-hoc retuning. Otherwise use strongest qualifying exploratory split.',
              'strongest_exploratory_core_pair': {'confidence': strongest['confidence'], 'margin': strongest['margin']} if strongest else None,
              'proposed_population_flagged': sum(proposed_flag(item) for item in population),
              'population_denominator': len(population),
              'proposed_population_flag_rate': sum(proposed_flag(item) for item in population)/len(population),
              'verified_sample': contrast(items, {item['review_id'] for item in items if proposed_flag(item)}, bootstrap),
              'old_hash': configuration(config), 'proposed_hash': configuration(proposed_config),
              'hash_changes': configuration(config)!=configuration(proposed_config),
              'offline_diagnostic_recomputation_api_usd': 0,
              'strict_same_hash_new_paid_enrich_evidence_needed': True,
              'existing_v3_rows_reprocessing': 3000,
              'reprocessing_measured_mix_estimate_usd': sum(event.get('cost_nanodollars',0) for event in events)/1e9,
              'reprocessing_worst_case_usd': json.loads(Path('artifacts/scaling-proposal/plan.json').read_text(encoding='utf-8'))['total_existing_config_envelope_usd'],
              'migration': 'Preserve old records/calls/hash. Offline derived flags cost zero, but do not silently rehash completed records: matching succeeded enrich evidence is required. Under current strict cache/export policy, a new final policy/hash requires separately approved fresh enrichment of 3000 v3 texts; v2 pilot/checkpoint remain historical.'}
    _, verify_events = load_state(OUTPUT/'state.sqlite3')
    result = {'valid_verifier_rows': len(items), 'excluded_terminal_rows': len(saved['terminal_failures']),
              'verification_cost_usd': sum(event.get('cost_nanodollars',0) for event in verify_events)/1e9,
              'verification_attempts': len(verify_events), 'measurements': measurement,
              'endpoint': 'Any topic/intent/severity exact mismatch or absolute sentiment difference >.25. Excludes entities, needs_review, language from this composite; per-field severity ±1 and sentiment sign shown separately.',
              'procedure': 'Core-only 35-pair grid. Confidence=min four core fields; margin=min three core Choices. 1000 unique-text bootstrap draws, fixed seed spotify-v3-transfer-calibration-v1. Material: >=25/group, lower pointwise 95% difference >5pp and ratio>=1.5 for both Jev and final comparisons. Exploratory, intervals not multiplicity adjusted; verifier comparisons are not human accuracy.',
              'overall': summary(items), 'frozen_initial_flags': contrast(items, {item['review_id'] for item in items if item['triage_flag']}, bootstrap),
              'frozen_final_flags': contrast(items, {item['review_id'] for item in items if item['final_flag']}, bootstrap),
              'auxiliary_only_reasons_overlap': auxiliary, 'auxiliary_only_exclusive_buckets': buckets,
              'nonenglish_confirmation': language_confirmation, 'core_grid': candidates, 'proposed_policy': policy}
    atomic_json(OUTPUT/'report.json', result)
    atomic_json(OUTPUT/'calibration_items.json', items)
    with (OUTPUT/'core-calibration.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['confidence','margin','flagged','unflagged','flag_rate','jev_flagged_rate','jev_unflagged_rate','final_flagged_rate','final_unflagged_rate','final_difference_lower95','final_difference_upper95','material'])
        for candidate in candidates:
            writer.writerow([candidate['confidence'],candidate['margin'],candidate['flagged']['n'],candidate['unflagged']['n'],candidate['flag_rate'],
                candidate['flagged']['jev']['rate'],candidate['unflagged']['jev']['rate'],candidate['flagged']['final']['rate'],candidate['unflagged']['final']['rate'],
                *(candidate['final']['difference_bootstrap_95'] or [None,None]),candidate['material_separation']])
    with (OUTPUT/'core-calibration-fields.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['confidence','margin','prediction','group','field','disagreements','denominator','rate'])
        for candidate in candidates:
            for kind in ('jev','final'):
                for group in ('flagged','unflagged'):
                    for field, values in candidate[group][kind]['fields'].items():
                        writer.writerow([candidate['confidence'],candidate['margin'],kind,group,field,
                                         values['disagreements'],values['denominator'],values['rate']])
    print(json.dumps({key: result[key] for key in ('valid_verifier_rows','excluded_terminal_rows','verification_cost_usd','verification_attempts','nonenglish_confirmation','proposed_policy')}, indent=2))


if __name__ == '__main__':
    report()
