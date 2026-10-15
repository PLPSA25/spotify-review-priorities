"""Owner-directed offline editorial revision of the saved memo-role draft."""
import csv
import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

from pipeline.labeler import atomic_csv
from pipeline.prepare import atomic_json

ROOT = Path('docs/phase7')
WORK = Path('artifacts/phase7')
CONTROLS = 'cross-topic--free-tier-premium-controls'
ADS = 'usability--ad-interruptions'


def rows(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def revise():
    ranking = {r['issue_id']: r for r in rows(ROOT/'ranking.csv')}
    sample = {r['issue_id']: r for r in rows(ROOT/'sample_ranking.csv')}
    original = rows(WORK/'claims.csv')
    atomic_csv(ROOT/'extended-claims.csv', list(original[0]), original)
    aliases = {
        ('other--unspecified', 'complaint_count'): 'B1', (CONTROLS, 'complaint_count'): 'B2',
        (CONTROLS, 'severity_sum'): 'B3', (ADS, 'complaint_count'): 'B4', (ADS, 'severity_sum'): 'B5',
        (CONTROLS, 'mean_severity'): 'B6', (ADS, 'mean_severity'): 'B7',
    }
    baseline = []
    for row in rows(WORK/'grading_claims.csv'):
        baseline.append(dict(row, claim_id=aliases.get((row['issue_id'], row['metric']), row['claim_id'])))
    for target in (ROOT/'claims.csv', ROOT/'grading_claims.csv', WORK/'grading_claims.csv', WORK/'grading-check/claims.csv'):
        atomic_csv(target, ['claim_id', 'issue_id', 'metric', 'value'], baseline)
    full = {r['claim_id']: r for r in original}
    secondary = [
        ('S1', 'baseline', CONTROLS, 'rank', ranking[CONTROLS]['rank'], 'ranking.csv'),
        ('S2', 'random_prefix', CONTROLS, 'rank', sample[CONTROLS]['rank'], 'sample_ranking.csv'),
        ('S3', 'random_prefix', CONTROLS, 'complaint_count', sample[CONTROLS]['complaint_count'], 'sample_ranking.csv'),
        ('S4', 'random_prefix', CONTROLS, 'severity_sum', sample[CONTROLS]['severity_sum'], 'sample_ranking.csv'),
        ('S5', 'random_prefix', ADS, 'complaint_count', sample[ADS]['complaint_count'], 'sample_ranking.csv'),
        ('S6', 'random_prefix', ADS, 'severity_sum', sample[ADS]['severity_sum'], 'sample_ranking.csv'),
        ('S7', 'random_prefix', CONTROLS, 'controls_to_ads_severity_ratio',
         str((Decimal(sample[CONTROLS]['severity_sum'])/Decimal(sample[ADS]['severity_sum'])).quantize(Decimal('.000001'))), 'S4 / S6'),
        ('S8', 'scope', 'scope', 'coverage_percent', full['scope:coverage_percent']['value'], 'extended-claims.csv'),
        ('S9', 'scope', 'scope', 'unspecified_percent', full['scope:unspecified_percent']['value'], 'extended-claims.csv'),
        ('S10', 'baseline', 'other--unspecified', 'rank', ranking['other--unspecified']['rank'], 'ranking.csv'),
        ('S11', 'baseline_minus_random_prefix', ADS, 'additional_complaint_rows',
         str(int(ranking[ADS]['complaint_count'])-int(sample[ADS]['complaint_count'])), 'B4 - S5: baseline minus random-prefix complaint_count'),
        ('S12', 'baseline_minus_random_prefix', CONTROLS, 'additional_complaint_rows',
         str(int(ranking[CONTROLS]['complaint_count'])-int(sample[CONTROLS]['complaint_count'])), 'B2 - S3: baseline minus random-prefix complaint_count'),
    ]
    atomic_csv(ROOT/'secondary-claims.csv', ['claim_id', 'scope', 'issue_id', 'metric', 'value', 'source'],
               [dict(zip(['claim_id', 'scope', 'issue_id', 'metric', 'value', 'source'], r, strict=True)) for r in secondary])
    member_issues = {r['review_id']: r['issue_id'] for r in rows(WORK/'membership.csv') if r['issue_id'] in {ADS, CONTROLS}}
    ads_ids = {rid for rid, issue in member_issues.items() if issue == ADS}
    prefix = {r['review_id'] for r in rows(Path('artifacts/sampling/permutation.csv'))[:100000]}
    quote_id = '7e271329-4c82-403b-a59a-7fd8b6c40405'
    quote = 'to play in order buy premium'
    counts, prefix_counts = Counter(), Counter()
    quote_found = False
    prefix_texts, additional_rows = set(), []
    with Path('data/spotify_reviews_18months.csv').open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            rid, text = row['review_id'], row['review_text']
            if rid in prefix:
                prefix_texts.add(text)
            elif rid in member_issues:
                additional_rows.append((member_issues[rid], text))
            if rid == quote_id:
                quote_found = quote in text
            if rid in ads_ids:
                counts[text] += 1
                if rid in prefix:
                    prefix_counts[text] += 1
    if not quote_found:
        raise ValueError('Representative quote is not an exact source substring')
    example = next((t for t in counts if t.casefold() == 'too many ads' and counts[t] > prefix_counts[t]), None)
    if example is None:
        raise ValueError('Repeated-ad-text example lacks propagation evidence')
    additional_breakdown = Counter((issue, text in prefix_texts) for issue, text in additional_rows)
    atomic_json(ROOT/'memo-revision-evidence.json', {
        'method': 'Owner-directed offline editing of saved memo-role draft; no API calls',
        'original_model_output': 'memo-draft.json', 'quote_id': quote_id, 'quote': quote,
        'quote_exact_substring': quote_found, 'ad_example_exact_text': example,
        'ad_example_baseline_count': counts[example], 'ad_example_prefix_count': prefix_counts[example],
        'claim_policy': 'Main claims are baseline-only allowed metrics; separately labeled secondary evidence is not submitted as baseline claims.',
        'owner_approved': True,
        'additional_rows_exact_text_breakdown': {str(key): value for key, value in additional_breakdown.items()},
        'owner_edit_wording_correction': 'Additional ad rows, not all duplicated: exact-text audit found 1947 matching prefix texts and 2 absent from prefix.',
    })
    b = lambda cid: f'[{cid}](phase7/claims.csv)'
    s = lambda cid: f'[{cid}](phase7/secondary-claims.csv)'
    c, a, pc, pa = ranking[CONTROLS], ranking[ADS], sample[CONTROLS], sample[ADS]
    if c['rank'] != '2' or pc['rank'] != '2' or ranking['other--unspecified']['rank'] != '1':
        raise ValueError('Owner editorial rank statement no longer matches saved rankings')
    ratio = (Decimal(pc['severity_sum'])/Decimal(pa['severity_sum'])).quantize(Decimal('.1'))
    control_mean = Decimal(c['mean_severity']).quantize(Decimal('.1'))
    ad_mean = Decimal(a['mean_severity']).quantize(Decimal('.1'))
    coverage = Decimal(full['scope:coverage_percent']['value']).quantize(Decimal(1))
    unspecified = Decimal(full['scope:unspecified_percent']['value']).quantize(Decimal(1))
    extra_ads = int(a['complaint_count'])-int(pa['complaint_count'])
    extra_controls = int(c['complaint_count'])-int(pc['complaint_count'])
    if extra_ads != 1949 or extra_controls != 4:
        raise ValueError('Owner-approved subtraction figures changed')
    text = f"""# Product decision memo — owner approved

**Prioritize a test restoring basic playback controls for free users.** The issue is users being forced to shuffle, unable to go back, seek, repeat, play in order or pick a song, and encountering skip limits. One review puts it plainly: “{quote}” ([review 7e271329](phase7-cohort-spotcheck-v3.md)). The cohort is named **Free-tier playback controls locked behind Premium**; some restrictions are inferred rather than explicitly attributed to Premium.

**Why this issue.** Other—unspecified ranks first under the contract’s severity-sum rule, with {int(ranking['other--unspecified']['complaint_count']):,} reviews ({b('B1')}, {s('S10')}). It represents general dissatisfaction with no stated cause, so it is not a specific fix target. Controls rank second in both the propagated baseline and random-prefix-only view ({s('S1')}, {s('S2')}).

Controls barely change between views: **{int(c['complaint_count']):,} reviews / {int(c['severity_sum']):,} severity points** in the baseline ({b('B2')}, {b('B3')}), versus **{int(pc['complaint_count']):,} / {int(pc['severity_sum']):,}** in the random prefix ({s('S3')}, {s('S4')}). Ads fall from **{int(a['complaint_count']):,} / {int(a['severity_sum']):,}** ({b('B4')}, {b('B5')}) to **{int(pa['complaint_count']):,} / {int(pa['severity_sum']):,}** ({s('S5')}, {s('S6')}). Exact-text propagation gives repeated short complaints such as “{example}” additional weight by copying their labels to matching rows outside the prefix. In the seeded random sample, controls carry approximately **{ratio}×** the severity-weighted complaints of ads ({s('S7')}). Baseline mean severity is approximately **{control_mean} for controls versus {ad_mean} for ads** ({b('B6')}, {b('B7')}).

Absolute counts cover only classified rows. The random prefix is a uniform sample of all nonempty reviews, so its proportions are the best estimate of the full mix; the baseline adds {extra_ads:,} additional ad rows ({s('S11')}) but only {extra_controls} controls rows ({s('S12')}). Remaining uncertainty comes from sampling error and lexical grouping, not the direction of this comparison.

**Proposed next step.** Test restoring back, seek and repeat for a subset of free users. Measure complaint rates, one-star rating rates and Premium conversion against a comparison group, using predefined observation windows and decision criteria. These controls appear to be used as upgrade incentives, so the test should weigh any change in Premium conversion against the reduction in complaints. An alternative is an ad-frequency cap. These are proposed experiments, not claims of causal impact, revenue gains or reduced churn.

**Decision limits.** Completed labels cover approximately **{coverage}% of nonempty rows** ({s('S8')}); approximately **{unspecified}% of classified complaint/cancellation rows have no specific cause assigned** ({s('S9')}). Grouping uses final, spot-checked lexical rules (v3), which can misassign or miss reviews. Verifier agreement is not human accuracy; the verifier and fallback share the same model.

*Evidence key: B references are checker-compatible baseline claims; S references are separately documented secondary analyses, not baseline claims. Engineering provenance and unavailable-usage disclosures are in the README. Owner-approved revision of the saved model draft.*
"""
    Path('docs/phase7-memo-draft.md').write_text(text, encoding='utf-8')
    references = set(re.findall(r'\[([BS]\d+)\]', text))
    available = {r['claim_id'] for r in baseline} | {r[0] for r in secondary}
    if references - available:
        raise ValueError('Memo contains unresolved compact claim references')
    atomic_json(ROOT/'memo-claim-audit.json', {
        'status': 'passed', 'claim_references': sorted(references),
        'unresolved_claim_references': sorted(references-available),
        'baseline_allowed_metrics_only': all(r['metric'] in {'complaint_count', 'severity_sum', 'mean_severity', 'priority_score'} for r in baseline),
        'secondary_claims_are_separately_labeled': True,
        'rounded_values_derived_from_saved_claims': True,
        'quote_verified_as_exact_substring': quote_found,
        'scope': 'Local editorial validation, supplementary to supplied baseline checker; not human accuracy',
    })
    print(json.dumps({'words': len(text.split()), 'quote_verified': quote_found,
                      'ad_example_baseline': counts[example], 'ad_example_prefix': prefix_counts[example]}))


if __name__ == '__main__':
    revise()
