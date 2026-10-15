"""Reproducible zero-API v2 preview and random cohort spot-checks."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from pipeline.issue_cohorts_v2 import (
    CONTROL_RULES,
    CROSS_ID,
    CROSS_NAME,
    RULE_HASH,
    classify,
    within_topic,
)
from pipeline.issue_preview import issue_id as old_issue
from pipeline.labeler import atomic_csv
from pipeline.phase7_work import load_inputs
from pipeline.prepare import atomic_json, course_helper
from pipeline.rank import aggregate

DESTINATION = Path('artifacts/phase7/cohort-v2')
SEED = 'spotify-phase7-cohort-spotcheck-v2'


def samples(ids, count, sources, golden_texts, cohort):
    eligible = [rid for rid in ids if sources[rid]['review_text'] not in golden_texts]
    return sorted(eligible, key=lambda rid: hashlib.sha256((SEED+':'+cohort+':'+rid).encode()).digest())[:count]


def quoted_example(rid, records, sources, details):
    text = sources[rid]['review_text']
    longest = max((len(m.group()) for m in re.finditer(r'`+', text)), default=0)
    fence = '`'*max(3, longest+1)
    lines = [f"- ID `{rid[:8]}` (full `{rid}`), frozen topic `{records[rid]['topic']}`."]
    if 'evidence_tier' in details:
        lines += [f"  Evidence tier: **{details['evidence_tier']}**; controls: "+', '.join(details['control_families'])+'.',
                  '  Control matches: '+', '.join('`'+s+'`' for s in details['control_matches'])+'.',
                  '  Restriction/pressure match: `'+details['restriction_match']+'`.']
        for kind in details['control_families']:
            lines.append('  Control rule `'+kind+'`: `'+CONTROL_RULES[kind]+'`.')
    else:
        lines += ['  Remaining-cohort rule: `'+details['matched_rule']+'`.',
                  '  Match: `'+details.get('matched_text', 'none')+'`.']
    lines += ['', fence+'text', text, fence, '']
    return lines


def report():
    records, sources, _, _, prefix = load_inputs()
    helper = course_helper(Path('data/check_submission.py'))
    golden = {r['review_text'] for r in helper.csv_rows(Path('data/golden_50_to_label.csv'))}
    eligible = [r for r in records.values() if r['intent'] in {'complaint', 'cancellation'}]
    old, new, details, members = {}, {}, {}, defaultdict(list)
    losses, losses_score, topic_count, topic_score, tiers, tier_scores = (Counter() for _ in range(6))
    stop_fix_ids = []
    for r in eligible:
        rid, text = r['review_id'], sources[r['review_id']]['review_text']
        old[rid] = old_issue(r['topic'], text)
        new[rid], details[rid] = classify(r['topic'], text)
        members[new[rid]].append(rid)
        fixed, _ = within_topic(r['topic'], text)
        if fixed != old[rid]:
            stop_fix_ids.append(rid)
        if new[rid] == CROSS_ID:
            losses[old[rid]] += 1
            losses_score[old[rid]] += r['severity']
            topic_count[r['topic']] += 1
            topic_score[r['topic']] += r['severity']
            tiers[details[rid]['evidence_tier']] += 1
            tier_scores[details[rid]['evidence_tier']] += r['severity']
    _, before, _ = aggregate(eligible, lambda r: old[r['review_id']])
    membership, after, claims = aggregate(eligible, lambda r: new[r['review_id']])
    _, sample_after, _ = aggregate([r for r in eligible if r['review_id'] in prefix], lambda r: new[r['review_id']])
    assert len(membership) == 70239 and len({r['review_id'] for r in membership}) == 70239
    assert sum(int(r['severity_sum']) for r in before) == sum(int(r['severity_sum']) for r in after)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    atomic_csv(DESTINATION/'proposed_membership.csv', ['issue_id', 'review_id'], membership)
    fields = ['rank', 'issue_id', 'complaint_count', 'severity_sum', 'mean_severity', 'priority_score']
    atomic_csv(DESTINATION/'proposed_ranking.csv', fields, after)
    atomic_csv(DESTINATION/'proposed_claims.csv', ['claim_id', 'issue_id', 'metric', 'value'], claims)
    contributions = [{'topic': t, 'review_count': topic_count[t], 'severity_sum': topic_score[t]} for t in
                     ('access', 'usability', 'playback', 'downloads', 'catalog', 'billing', 'support', 'other')]
    transfers = [{'source_cohort': iid, 'moved_count': losses[iid], 'moved_severity_sum': losses_score[iid],
                  'remaining_count': len(members[iid])} for iid in sorted(losses, key=lambda s: (-losses[s], s))]
    chosen_cross = samples(members[CROSS_ID], 10, sources, golden, CROSS_ID)
    chosen_remaining = {r['source_cohort']: samples(members[r['source_cohort']], 5, sources, golden, r['source_cohort']) for r in transfers}
    old_spot = json.loads(Path('artifacts/phase7/cohort-spotcheck.json').read_text(encoding='utf-8'))
    cited = []
    selected_positions = {'billing--premium-upgrade-mentions': {3, 4, 5}, 'usability--queue-playlist-controls': {1, 2, 3, 5},
                          'billing--price-paywalls': {2, 3, 5}}
    positions = Counter()
    for row in old_spot['selected']:
        positions[row['cohort']] += 1
        if positions[row['cohort']] in selected_positions.get(row['cohort'], set()):
            cited.append({'old_cohort': row['cohort'], 'old_example': positions[row['cohort']],
                          'review_id': row['review_id'], 'new_cohort': new[row['review_id']],
                          'evidence': details[row['review_id']]})
    result = {'status': 'offline proposal; all paid Phase 7 stages held', 'rule_hash': RULE_HASH,
              'classifier_hash_changed': False, 'issue_name': CROSS_NAME, 'issue_id': CROSS_ID,
              'cross_count': len(members[CROSS_ID]), 'cross_severity_sum': topic_score.total(),
              'source_topics': contributions, 'source_cohort_transfers': transfers,
              'evidence_tiers': {tier: {'count': count, 'severity_sum': tier_scores[tier]} for tier, count in tiers.items()},
              'old_ranking': before, 'v2_ranking': after, 'random_prefix_v2_ranking': sample_after,
              'old_issue_count': len(before), 'v2_issue_count': len(after),
              'continuity_false_positive_rows_fixed': len(stop_fix_ids),
              'continuity_false_positive_example_09d5682f': [{'review_id': rid, 'new_issue': new[rid]} for rid in old if rid.startswith('09d5682f')],
              'sample_seed': SEED, 'new_issue_spotcheck_ids': chosen_cross,
              'remaining_cohort_spotcheck_ids': chosen_remaining, 'owner_cited_examples': cited,
              'memberships': len(membership), 'total_severity_sum': sum(int(r['severity_sum']) for r in after),
              'model_calls': 0, 'graded_exports_changed': False}
    initial_path = DESTINATION/'initial-candidate/phase7-cohort-v2-analysis.json'
    if initial_path.exists():
        initial = json.loads(initial_path.read_text(encoding='utf-8'))
        result.update(initial_candidate_preserved_at=str(initial_path.parent),
                      initial_candidate_rule_hash=initial['rule_hash'], initial_candidate_count=initial['cross_count'],
                      sampling_seed_unchanged_after_rule_validation=True)
    result['residual_premium_display_name_proposed'] = 'Premium subscription and upgrade complaints'
    atomic_json(Path('docs/phase7-cohort-v2-analysis.json'), result)
    atomic_json(DESTINATION/'spotcheck-records.json', {'new_issue': [{'review_id': rid, 'text': sources[rid]['review_text'], 'details': details[rid]} for rid in chosen_cross],
                'remaining_cohorts': {iid: [{'review_id': rid, 'text': sources[rid]['review_text'], 'details': details[rid]} for rid in ids] for iid,ids in chosen_remaining.items()}})
    lines = ['# Phase 7 cohort spot-check v2 — review before all paid calls', '',
             '**No Phase 7 API calls have been made.** Verifier, group and memo calls are held until the owner reviews this file. These are proposed memberships only; grading exports and classifications are unchanged.', '',
             '## Cross-topic grouping is permitted', '',
             'Contract `data/GRADING_CONTRACT.md:94–95`: "The required baseline uses completed `complaint` and `cancellation` records. Each must belong to at least one issue." and "Normally use one issue per complaint." No requirement confines an issue to a topic. The checker at `data/check_submission.py:255–280` validates original IDs, complaint intent and unique membership; it does not compare an issue with the primary topic. `allow_multi_issue:false` is preserved: every eligible ID belongs to exactly one issue.', '',
             '## Proposed definition and precedence', '',
             '**'+CROSS_NAME+'** (`'+CROSS_ID+'`) takes precedence over all within-topic cohorts, including `other`. It requires a control-family match plus restriction/pressure evidence; Premium alone cannot match. Primary topic, severity, intent, label_config and all labels stay unchanged. Grouping-rule hash: `'+RULE_HASH+'`.', '',
             'Control families: shuffle/unshuffle; play-in-order or song selection; previous/back; repeat/loop; skip/forward (not skip ads); seek/rewind/specific or favorite song parts. The owner-cited generic Price #2/#3 descriptions additionally match the explicitly named `basic-player-control-paraphrase` rule, together with payment/upgrade restriction—not a Premium keyword alone.', '',
             '**Evidence distinction:** explicit paywall/Premium linkage is separated from free-tier restriction and inferred update/forced-shuffle/multiple-controls-denied paths. Queue #1–#3 do not explicitly establish Premium gating; including those owner-selected examples therefore entails an inference. Those rows remain visibly marked inferred; the requested title is a provisional theme, not proof that every member is a free user or was paywalled. Paid-customer statements exclude inferred paths. Review the evidence tiers below before accepting this attribution.', '',
             'Non-stop/non stop/non–stop/nonstop and without-stopping continuity claims no longer count as stoppage failures. Exclusion applies to the protected occurrence only, so a later actual "music stops" still counts.', '',
             '## Measured offline redistribution', '',
             f"New cross-topic issue: **{len(members[CROSS_ID]):,} IDs**, severity_sum **{topic_score.total():,}**. Total eligible IDs and severity_sum remain unchanged. Proposed issue count: {len(before)} → {len(after)}.", '']
    for row in contributions:
        lines.append(f"- `{row['topic']}`: **{row['review_count']:,}** reviews; severity_sum **{row['severity_sum']:,}**.")
    lines += ['', 'Evidence tiers:', '']
    for tier, count in tiers.items():
        lines.append(f'- `{tier}`: **{count:,}** IDs; severity_sum **{tier_scores[tier]:,}**.')
    lines += ['', f'Continuity-protection correction changes {len(stop_fix_ids):,} original within-topic assignments before cross-theme precedence. The reported false positive `09d5682f` is now `'+next(new[rid] for rid in old if rid.startswith('09d5682f'))+'`.', '',
              '## Top ten: current v1 ranking', '']
    for row in before[:10]:
        lines.append(f"{row['rank']}. `{row['issue_id']}` — size **{int(row['complaint_count']):,}**, severity_sum **{int(row['severity_sum']):,}**.")
    lines += ['', '## Top ten: proposed v2 ranking', '']
    for row in after[:10]:
        lines.append(f"{row['rank']}. `{row['issue_id']}` — size **{int(row['complaint_count']):,}**, severity_sum **{int(row['severity_sum']):,}**.")
    lines += ['', '## Random-prefix-only v2 comparison', '',
              'Only completed original IDs within the first 100,000 permutation IDs contribute here; forced golden additions outside the prefix and propagated out-of-prefix aliases are excluded.', '']
    for row in sample_after[:10]:
        lines.append(f"{row['rank']}. `{row['issue_id']}` — size **{int(row['complaint_count']):,}**, severity_sum **{int(row['severity_sum']):,}**.")
    lines += ['', '## Check of the owner-cited examples', '']
    for row in cited:
        lines.append(f"- `{row['review_id'][:8]}` ({row['old_cohort']} #{row['old_example']}) → `{row['new_cohort']}`; evidence `{row['evidence'].get('evidence_tier', 'within-topic')}`.")
    lines += ['', '## New issue: ten random members', '',
              'Sampling is uniform over member original IDs via SHA-256(seed + cohort + ID); seed `'+SEED+'`. Golden exact texts are excluded from examples. Repeated exact texts remain eligible to preserve row weighting. This is qualitative review, not an accuracy estimate.', '']
    for rid in chosen_cross:
        lines += quoted_example(rid, records, sources, details[rid])
    lines += ['', '## Cohorts that lost members: five random remaining members each', '',
              'These samples come from each **remaining** cohort, not its transferred rows, so the owner can assess what is left. Transfers and residual sizes are shown first. If fewer than five eligible remaining examples exist, all are shown rather than fabricated.', '']
    for row in transfers:
        iid = row['source_cohort']
        lines += ['### '+iid, '', f"Moved **{row['moved_count']:,}** IDs / severity_sum **{row['moved_severity_sum']:,}** to the new issue. Remaining **{row['remaining_count']:,}** IDs.", '']
        for rid in chosen_remaining[iid]:
            lines += quoted_example(rid, records, sources, details[rid])
    lines += ['', '## Premium residual display name and stop condition', '',
              'Do not retain the control-specific display name "Premium-only controls and upgrade pressure" for the residual. The five residual examples mix upgrade pressure, free-tier dissatisfaction, lyrics access and platform comparison. Proposed residual display name: "Premium subscription and upgrade complaints"; stable issue ID stays `billing--premium-upgrade-mentions`. No primary topic changes.', '',
              'Stop here for owner review. No production verifier, group or memo call; no change to frozen labels, no human golden labels read, no final membership/claims applied, and no grading gzip rewrite/recommit. V2 must be accepted before adapting the pending Phase 7 runner and its group evidence packs.']
    lines += ['', '## Offline rule-validation refinement and reproducibility', '',
              'The initial forced-shuffle matcher also caught algorithm-only repetition (only shuffling particular songs). It was narrowed to forced mode/control wording, with regression tests. Conditional "if you do not buy Premium" is now explicit gating. The initial candidate and sample are preserved in `artifacts/phase7/cohort-v2/initial-candidate/`; the same seed was retained and no examples were hand-swapped. This report uses the revised rule hash above.', '',
              'Reproduce with `.venv/Scripts/python.exe -m pipeline.cohort_v2_report`. Full rules are in `pipeline/issue_cohorts_v2.py`. A synthetic cross-topic fixture passes the actual supplied checker; this is a mechanical test, not model execution evidence.']
    Path('docs/phase7-cohort-spotcheck-v2.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    result = report()
    print(json.dumps({key: result[key] for key in ('cross_count', 'cross_severity_sum', 'source_topics', 'evidence_tiers',
                     'old_issue_count', 'v2_issue_count', 'continuity_false_positive_rows_fixed')}, indent=2))
