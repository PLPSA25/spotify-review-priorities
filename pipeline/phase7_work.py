"""Offline production cohorts, numerical claims and reviewable memo inputs."""
import csv
import gzip
import hashlib
import itertools
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from pipeline.issue_cohorts_v3 import CROSS_ID, RULE_HASH, classify
from pipeline.issue_preview import RULE_HASH as V1_RULE_HASH
from pipeline.issue_preview import RULES
from pipeline.labeler import atomic_csv
from pipeline.pilot_stages import object_schema, role_payload
from pipeline.prepare import atomic_json, course_helper
from pipeline.rank import aggregate
from pipeline.schema import canonical

OUTPUT = Path('artifacts/phase7')
DISPLAY_NAME = 'Premium subscription and upgrade complaints'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def load_inputs(version='v1'):
    helper = course_helper(Path('data/check_submission.py'))
    with gzip.open('grading/records.jsonl.gz', 'rt', encoding='utf-8') as stream:
        records = {r['review_id']: r for line in stream if (r := json.loads(line))['status'] == 'completed'}
    proposal = read_json(Path('docs/phase7-production-verifier-proposal.json'))
    taxonomy = read_json(Path('docs/phase7-cohort-v3-analysis.json' if version == 'v3' else 'docs/phase7-taxonomy-preview.json'))
    if taxonomy['rule_hash'] != (RULE_HASH if version == 'v3' else V1_RULE_HASH) or len(records) != 237722:
        raise ValueError('Approved production/taxonomy changed')
    needed = {rid for rid, r in records.items() if r['intent'] in {'complaint', 'cancellation'}} | set(proposal['sample_ids'])
    sources = {r['review_id']: dict(r, source_sha256=helper.row_sha(r))
               for r in helper.csv_rows(Path('data/spotify_reviews_18months.csv')) if r['review_id'] in needed}
    if set(sources) != needed:
        raise ValueError('Missing original source')
    with Path('artifacts/sampling/permutation.csv').open(encoding='utf-8', newline='') as stream:
        prefix = {r['review_id'] for r in itertools.islice(csv.DictReader(stream), 100000)}
    return records, sources, proposal, taxonomy, prefix


def group_payloads(config, taxonomy, sources):
    payloads = {}
    rows = taxonomy['fine_ranking']
    schema = object_schema({'issues': {'type': 'array', 'items': object_schema({
        'issue_id': {'type': 'string'}, 'name': {'type': 'string'}})}})
    instructions = (
        'Name every supplied fixed cohort with a short accurate complaint description, at most eighty characters. '
        'Return exactly the supplied issue IDs once each. Membership and primary topic are fixed in code. '
        'These are lexical cohorts, not validated causes: preserve uncertainty and unspecified buckets. '
        'Call other--unspecified "General dissatisfaction — no stated cause". '
        'Primary topics remain frozen; one cross-topic control restriction theme spans topics without relabeling them. '
        'For billing--premium-upgrade-mentions use a complaint-specific name only when supported by evidence; '
        'the approved residual name is "Premium subscription and upgrade complaints". '
        'No new IDs, facts, numbers, classification edits or membership changes.')
    for start in range(0, len(rows), 25):
        cohorts, ids = [], []
        for row in rows[start:start+25]:
            topic, subissue = row['issue_id'].split('--', 1)
            pattern = dict(RULES[topic]).get(subissue) if topic in RULES else None
            examples = []
            for rid in row['example_review_ids']:
                text = sources[rid]['review_text']
                match = re.search(pattern, text, re.IGNORECASE) if pattern else None
                offset = max(0, match.start()-35) if match else 0
                quote = text[offset:offset+120]
                examples.append({'review_id': rid, 'quote': quote})
                ids.append(rid)
            cohorts.append({'issue_id': row['issue_id'], 'matched_rule': ('Frozen v3 control + restriction gate; explicit and inferred evidence distinguished' if row['issue_id'] == CROSS_ID else pattern or 'No specific within-topic match'),
                            'evidence': examples})
        stage = f'group-{start//25+1:02d}'
        payload = role_payload(config, instructions, {'cohorts': cohorts}, schema, 2048, 'production_issue_names')
        bound = len(canonical(payload).encode()) + config['controls']['token_overhead_bound']
        if bound > 24000 or len(ids) > 50 or len(ids) != len(set(ids)):
            raise ValueError('Group pack exceeds approved envelope')
        payloads[stage] = {'payload': payload, 'ids': ids, 'issue_ids': [r['issue_id'] for r in rows[start:start+25]],
                           'payload_sha256': hashlib.sha256(canonical(payload).encode()).hexdigest()}
    return payloads


def parse_group(value, expected):
    rows = value.get('issues')
    if not isinstance(rows, list) or len(rows) != len(expected) or any(not isinstance(r, dict) for r in rows) or {r.get('issue_id') for r in rows} != set(expected):
        raise ValueError('Group IDs missing, duplicated or foreign')
    if any(not isinstance(r.get('name'), str) or not r['name'].strip() or len(r['name']) > 80 for r in rows):
        raise ValueError('Group names must be nonempty and at most eighty characters')
    return value


def write_business(records, sources, prefix, output=OUTPUT):
    output.mkdir(parents=True, exist_ok=True)
    mapper = lambda r: classify(r['topic'], sources[r['review_id']]['review_text'])[0]
    membership, ranking, baseline = aggregate(list(records.values()), mapper)
    _, sample_ranking, sample = aggregate([r for rid, r in records.items() if rid in prefix], mapper)
    atomic_csv(output/'membership.csv', ['issue_id', 'review_id'], membership)
    fields = ['rank', 'issue_id', 'complaint_count', 'severity_sum', 'mean_severity', 'priority_score']
    atomic_csv(output/'ranking.csv', fields, ranking)
    atomic_csv(output/'sample_ranking.csv', fields, sample_ranking)
    claims = [dict(r, scope='baseline') for r in baseline]
    claims += [dict(r, claim_id='sample:'+r['claim_id'], scope='random_prefix') for r in sample]
    for scope, rows in [('baseline', ranking), ('random_prefix', sample_ranking)]:
        for row in rows:
            claims.append({'claim_id': ('sample:' if scope == 'random_prefix' else '')+row['issue_id']+':rank',
                           'issue_id': row['issue_id'], 'metric': 'rank', 'value': row['rank'], 'scope': scope})
    unspecified = sum(int(r['complaint_count']) for r in ranking if r['issue_id'].endswith('--unspecified'))
    metrics = {'completed_rows': len(records), 'nonempty_rows': 660609,
               'complaint_rows': len(membership), 'unspecified_complaint_rows': unspecified,
               'prefix_ids': len(prefix), 'prefix_completed_rows': len(set(records)&prefix)}
    for name, numerator, denominator in [('coverage', len(records), 660609), ('unspecified', unspecified, len(membership))]:
        pct = Decimal(numerator)*100/Decimal(denominator)
        metrics[name+'_percent'] = str(pct.quantize(Decimal('.000001'), rounding=ROUND_HALF_UP))
        metrics[name+'_percent_rounded'] = str(pct.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    for metric, value in metrics.items():
        claims.append({'claim_id': 'scope:'+metric, 'issue_id': 'scope', 'metric': metric,
                       'value': str(value), 'scope': 'scope'})
    atomic_csv(output/'claims.csv', ['claim_id', 'issue_id', 'metric', 'value', 'scope'], claims)
    # The supplied checker only permits the four baseline metrics. The complete
    # memo claims remain in the full CSV, not disguised as baseline issue values.
    atomic_csv(output/'grading_claims.csv', ['claim_id', 'issue_id', 'metric', 'value'], baseline)
    atomic_json(output/'business-summary.json', {'ranking': ranking, 'sample_ranking': sample_ranking,
                'metrics': metrics, 'grouping_rule_hash': RULE_HASH, 'full_claims': str(output/'claims.csv'),
                'grading_claims_projection': str(output/'grading_claims.csv')})
    return ranking, sample_ranking, claims


def agreement(records, predictions, fallback_ids):
    def summarize(ids):
        pairs = [(records[rid], predictions[rid]) for rid in ids]
        functions = {'topic': lambda a,b: a['topic']==b['topic'], 'intent': lambda a,b: a['intent']==b['intent'],
                     'severity_exact': lambda a,b: a['severity']==b['severity'],
                     'severity_within_one': lambda a,b: abs(a['severity']-b['severity']) <= 1,
                     'sentiment_sign': lambda a,b: (a['sentiment']>0)-(a['sentiment']<0)==(b['sentiment']>0)-(b['sentiment']<0),
                     'needs_review': lambda a,b: a['needs_review']==b['needs_review']}
        return {'n': len(pairs), 'fields': {name: {'agree': sum(fn(a,b) for a,b in pairs),
                'denominator': len(pairs), 'agreement': sum(fn(a,b) for a,b in pairs)/len(pairs) if pairs else None}
                for name,fn in functions.items()}}
    ids = set(predictions)
    flagged = {rid for rid in ids if records[rid]['needs_review']}
    fallback = {rid for rid in ids if records[rid].get('cache_source_id', rid) in fallback_ids}
    return {'overall': summarize(ids), 'flagged': summarize(flagged), 'unflagged': summarize(ids-flagged),
            'fallback': summarize(fallback), 'no_fallback': summarize(ids-fallback),
            'interpretation': 'Blinded Luna agreement, not human accuracy; fallback also uses Luna. Duplicate texts induce dependence. Entities excluded.'}


def memo_payload(config, business, group_names):
    ranking, sample, claims = business
    specific = next(r for r in ranking if not r['issue_id'].endswith('--unspecified'))['issue_id']
    selected_ids = {ranking[0]['issue_id'], specific} | {r['issue_id'] for r in ranking[:5]} | {r['issue_id'] for r in sample[:5]}
    selected_claims = [r for r in claims if r['scope']=='scope' or r['issue_id'] in selected_ids]
    schema = object_schema({
        'top_bucket_explanation': {'type': 'string'}, 'recommended_issue_id': {'type': 'string'},
        'recommendation': {'type': 'string'}, 'random_prefix_comparison': {'type': 'string'},
        'limitations': {'type': 'string'}, 'alternatives': {'type': 'array', 'items': {'type': 'string'}},
        'claim_ids': {'type': 'array', 'items': {'type': 'string'}}})
    data = {'baseline_top': ranking[:5], 'random_prefix_top': sample[:5], 'claims': selected_claims,
            'names': {iid: group_names[iid] for iid in sorted(selected_ids)}, 'required_recommendation_id': specific}
    instructions = (
        'Write a memo draft from saved claims only. Return prose without numeric digits; code appends a claims-backed numerical summary. '
        'Explicitly state the top bucket is general dissatisfaction with no stated cause, not a specific actionable defect. '
        'Recommend required_recommendation_id, the top specific actionable issue; compare alternatives and the random-prefix-only ranking. '
        'Explain partial coverage and the large unspecified share using claim IDs, not invented figures. '
        'Include duplicate-text weighting, lexical cohort uncertainty, preserved classifier errors, verifier/fallback correlation, '
        'expressed cancellation versus observed churn, unknown failed-call usage, and reconstructed before-checkpoint provenance. '
        'No causal, revenue or churn estimates. Cite only supplied claim IDs; do not embed IDs or numbers in prose. '
        'Do not call a generic residual the recommended product fix.')
    payload = role_payload(config, instructions, data, schema, 1200, 'production_memo_draft')
    if len(canonical(payload).encode())+config['controls']['token_overhead_bound'] > 24000:
        raise ValueError('Memo pack exceeds approved input bound')
    return payload, specific, {r['claim_id'] for r in selected_claims}


def parse_memo(value, specific, claim_ids):
    if value.get('recommended_issue_id') != specific:
        raise ValueError('Memo must recommend the top specific cohort')
    cited = value.get('claim_ids')
    if not isinstance(cited, list) or not cited or not set(cited) <= claim_ids:
        raise ValueError('Memo cites missing/foreign claims')
    prose = [value.get(k) for k in ('top_bucket_explanation', 'recommendation', 'random_prefix_comparison', 'limitations')]
    prose += value.get('alternatives', [])
    if any(not isinstance(s, str) or not s.strip() or re.search(r'\d', s) for s in prose):
        raise ValueError('Memo prose must be nonempty and contain no numeric digits')
    inline = {cid for text in prose for cid in re.findall(r'\[([^\]]+)\]', text)}
    if not inline <= set(cited):
        raise ValueError('Memo prose cites undeclared or foreign claims')
    return value
