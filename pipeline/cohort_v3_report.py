"""Frozen v3 counts, comparison rankings and a fresh qualitative sample; no API."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from pipeline.issue_cohorts_v3 import CONTROL_RULES, CROSS_ID, RULE_HASH, classify
from pipeline.phase7_work import load_inputs
from pipeline.prepare import atomic_json, course_helper
from pipeline.rank import aggregate


def report():
    helper = course_helper(Path('data/check_submission.py'))
    frozen = json.loads(Path('docs/frozen-grouping-v3.json').read_text(encoding='utf-8'))
    assert frozen['rule_hash'] == RULE_HASH
    assert all(helper.sha(Path(name)) == sha for name, sha in frozen['file_sha256'].items())
    records, sources, _, _, prefix = load_inputs()
    eligible = [r for r in records.values() if r['intent'] in {'complaint', 'cancellation'}]
    assignments, details, members = {}, {}, defaultdict(list)
    for record in eligible:
        rid = record['review_id']
        assignments[rid], details[rid] = classify(record['topic'], sources[rid]['review_text'])
        members[assignments[rid]].append(rid)
    _, ranking, _ = aggregate(eligible, lambda r: assignments[r['review_id']])
    _, sample_ranking, _ = aggregate([r for r in eligible if r['review_id'] in prefix], lambda r: assignments[r['review_id']])
    golden = {r['review_text'] for r in helper.csv_rows(Path('data/golden_50_to_label.csv'))}
    previous = json.loads(Path('artifacts/phase7/cohort-v2/spotcheck-records.json').read_text(encoding='utf-8'))
    previously_seen = {r['text'] for rows in [previous['new_issue'], *previous['remaining_cohorts'].values()] for r in rows}
    original = json.loads(Path('artifacts/phase7/cohort-spotcheck.json').read_text(encoding='utf-8'))
    previously_seen |= {r['review_text'] for r in original['selected']}
    seed = 'spotify-phase7-cohort-spotcheck-v3-final'
    fresh = sorted((rid for rid in members[CROSS_ID] if sources[rid]['review_text'] not in golden|previously_seen),
                   key=lambda rid: hashlib.sha256((seed+':'+rid).encode()).digest())[:10]
    taxonomy = []
    for row in ranking:
        iid = row['issue_id']
        examples = sorted((rid for rid in members[iid] if sources[rid]['review_text'] not in golden),
                          key=lambda rid: hashlib.sha256(('phase7-group-v3:'+rid).encode()).digest())
        unique, selected = set(), []
        for rid in examples:
            text = sources[rid]['review_text']
            if text not in unique:
                selected.append(rid)
                unique.add(text)
            if len(selected) == 2:
                break
        taxonomy.append({'rank': int(row['rank']), 'issue_id': iid, 'size': int(row['complaint_count']),
                         'severity_sum': int(row['severity_sum']), 'example_review_ids': selected})
    wanted = {'708979fd', 'be94b3ba', '8ec05eaa', '53d1007a', 'cde44079', 'db6da51a', '74c6a145', 'e850f9da', 'fb00c755', '3a6becfb', '8f775fd4', 'f8ac4df8'}
    checks = [{'review_id': rid, 'issue_id': assignments[rid], 'matched': assignments[rid]==CROSS_ID,
               'details': details[rid]} for rid in assignments if rid[:8] in wanted]
    cross = next(r for r in ranking if r['issue_id']==CROSS_ID)
    v2 = json.loads(Path('docs/phase7-cohort-v2-analysis.json').read_text(encoding='utf-8'))
    result = {'status': 'v3 final; no further tuning regardless of ranking/sample', 'rule_hash': RULE_HASH,
              'cross_count': int(cross['complaint_count']), 'cross_severity_sum': int(cross['severity_sum']),
              'fine_ranking': taxonomy, 'propagated_ranking': ranking, 'random_prefix_ranking': sample_ranking,
              'evidence_tiers': dict(Counter(details[rid]['evidence_tier'] for rid in members[CROSS_ID])),
              'owner_requested_id_checks': checks, 'fresh_sample_seed': seed, 'fresh_sample_ids': fresh,
              'fresh_sample': [{'review_id': rid, 'text': sources[rid]['review_text'], 'details': details[rid]} for rid in fresh],
              'history': {'v1': {'unified_issue': 'not defined; complaints fragmented across topic cohorts'},
                          'v2': {'count': v2['cross_count'], 'severity_sum': v2['cross_severity_sum']},
                          'v3': {'count': int(cross['complaint_count']), 'severity_sum': int(cross['severity_sum'])}},
              'classifier_hash_changed': False, 'model_calls': 0}
    atomic_json(Path('docs/phase7-cohort-v3-analysis.json'), result)
    lines = ['# Frozen v3 — final rule revision and fresh sample', '',
             'Rules were frozen before computing v3 counts or viewing its fresh sample. No further tuning, regardless of resulting rankings or examples. No human golden labels were read. Rule hash: `'+RULE_HASH+'`.', '',
             'V1 had no unified cross-topic issue. V2: '+str(v2['cross_count'])+' reviews / severity_sum '+str(v2['cross_severity_sum'])+'. V3: **'+cross['complaint_count']+' reviews / severity_sum '+cross['severity_sum']+'**.', '',
             'Only owner-requested recall fixes from random spot-checks were added: plural song parts; broader negation/allowance, payment and free-tier restriction evidence; selected-song substitution as a forced-shuffle symptom. Control evidence and restriction/symptom evidence are both required; Premium alone never matches. Explicit Premium evidence and inferred control restrictions stay distinct.', '',
             '## Requested review-ID checks', '']
    for row in checks:
        lines.append(f"- `{row['review_id'][:8]}` → `{row['issue_id']}`; matched **{row['matched']}**; evidence `{row['details'].get('evidence_tier', 'none')}`.")
    for title, rows in [('Propagated baseline top ten', ranking), ('Random-prefix-only top ten', sample_ranking)]:
        lines += ['', '## '+title, '']
        for row in rows[:10]:
            lines.append(f"{row['rank']}. `{row['issue_id']}` — **{row['complaint_count']} reviews**, severity_sum **{row['severity_sum']}**.")
    lines += ['', '## Ten fresh random members', '',
              'Seed `'+seed+'`; original IDs uniformly hash-ordered within the new issue, excluding golden exact texts and previously shown review texts. This is qualitative review, not an accuracy estimate. Sample does not determine any further rule change.', '']
    for rid in fresh:
        text, info = sources[rid]['review_text'], details[rid]
        lines += [f"### `{rid[:8]}` (full `{rid}`)", '', 'Evidence: `'+info['evidence_tier']+'`; controls: '+', '.join(info['control_families'])+'.',
                  'Restriction/symptom: '+json.dumps(info['restriction_match'], ensure_ascii=False), '', '````text', text, '````', '']
    lines += ['Frozen control patterns:', '']
    lines += ['- `'+name+'`: `'+pattern+'`' for name, pattern in CONTROL_RULES.items()]
    Path('docs/phase7-cohort-spotcheck-v3.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    result = report()
    print(json.dumps({k: result[k] for k in ('cross_count', 'cross_severity_sum', 'evidence_tiers', 'history')}, indent=2))
