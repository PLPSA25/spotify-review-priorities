"""Deterministic, public aggregate/sample snapshot. No providers or human labels."""
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

from pipeline.prepare import atomic_json

DOCS = Path('docs/phase7')
OUTPUT = Path('artifacts/dashboard')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def table(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def normalize(value):
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return int(value) if isinstance(value, float) and value.is_integer() else value


def canonical(value):
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def atomic_bytes(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_bytes(content)
    temporary.replace(path)


def aggregate_records(records):
    counts = Counter()
    distributions = {name: Counter() for name in ('topic', 'intent', 'severity', 'sentiment_sign')}
    reasons, quarantine = Counter(), Counter()
    label_configs = set()
    for record in records:
        counts['total_rows'] += 1
        if record['status'] == 'quarantined':
            quarantine[record['reason']] += 1
            continue
        if record['status'] != 'completed':
            raise ValueError('Unexpected exported status')
        counts['completed_rows'] += 1
        counts['cache_reused_rows' if record.get('cache_source_id') else 'direct_original_rows'] += 1
        label_configs.add(record['label_config'])
        for field in ('topic', 'intent', 'severity'):
            distributions[field][str(record[field])] += 1
        sentiment = record['sentiment']
        distributions['sentiment_sign']['positive' if sentiment > 0 else 'negative' if sentiment < 0 else 'neutral'] += 1
        if record['needs_review']:
            counts['needs_review_rows'] += 1
        flags = record.get('needs_review_reasons', [])
        if bool(flags) != record['needs_review']:
            raise ValueError('Flag/reason mismatch in source')
        reasons.update(set(flags))
    counts['empty_rows'] = quarantine.get('empty_review_text', 0)
    counts['nonempty_rows'] = counts['total_rows']-counts['empty_rows']
    counts['out_of_scope_rows'] = quarantine.get('not_classified_partial_run', 0)
    counts['terminal_rows'] = sum(quarantine.values())-counts['empty_rows']-counts['out_of_scope_rows']
    if len(label_configs) != 1:
        raise ValueError('Mixed or empty classification configurations')
    return {'counts': dict(counts), 'distributions': {k: dict(v) for k,v in distributions.items()},
            'flag_reasons': dict(reasons), 'quarantine_reasons': dict(quarantine),
            'label_config': next(iter(label_configs))}


def validate_ranking(rows, expected_count, expected_sum):
    if sum(int(r['complaint_count']) for r in rows) != expected_count or sum(int(r['severity_sum']) for r in rows) != expected_sum:
        raise ValueError('Ranking totals disagree with frozen business evidence')
    order = sorted(rows, key=lambda r: (-int(r['severity_sum']), r['issue_id']))
    if rows != order or any(int(r['rank']) != n for n,r in enumerate(rows,1)):
        raise ValueError('Ranking order is not contract order')
    if any(r['priority_score'] != r['severity_sum'] for r in rows):
        raise ValueError('Priority must equal severity_sum')


def build():
    approval = read(DOCS/'memo-owner-approval.json')
    memo_path = Path('docs/phase7-memo-draft.md')
    if approval['status'] != 'owner_approved' or sha(memo_path) != approval['memo_sha256']:
        raise ValueError('Approved memo bytes changed')
    sources = [Path('grading/records.jsonl.gz'), Path('grading/ingestion.json'), memo_path,
               Path('docs/frozen-grouping-v3.json'), DOCS/'memo-owner-approval.json',
               DOCS/'ranking.csv', DOCS/'sample_ranking.csv', DOCS/'claims.csv', DOCS/'secondary-claims.csv',
               DOCS/'group-names.json', DOCS/'group-outputs.json', DOCS/'verifier-agreement.json',
               DOCS/'memo-draft.json', Path('docs/phase7-cohort-v3-analysis.json')]
    with gzip.open('grading/records.jsonl.gz','rt',encoding='utf-8') as stream:
        summary = aggregate_records(json.loads(line) for line in stream)
    if summary['counts']['total_rows'] != 660622 or summary['counts']['completed_rows'] != 237722:
        raise ValueError('Production coverage changed')
    names = read(DOCS/'group-names.json')
    rankings = {'baseline': table(DOCS/'ranking.csv'), 'random_prefix': table(DOCS/'sample_ranking.csv')}
    for rows in rankings.values():
        validate_ranking(rows, sum(int(r['complaint_count']) for r in rows), sum(int(r['severity_sum']) for r in rows))
        for row in rows:
            row['name'] = names[row['issue_id']]
    validate_ranking(rankings['baseline'], 70239, 154528)
    ranking_by_id = {r['issue_id']: r for r in rankings['baseline']}
    claims = table(DOCS/'claims.csv')
    for claim in claims:
        if claim['metric'] not in {'complaint_count', 'severity_sum', 'mean_severity', 'priority_score'} or ranking_by_id[claim['issue_id']][claim['metric']] != claim['value']:
            raise ValueError('Baseline claim mismatch')
    taxonomy = read(Path('docs/phase7-cohort-v3-analysis.json'))
    example_issues = {rid: row['issue_id'] for row in taxonomy['fine_ranking'] for rid in row['example_review_ids']}
    quote_evidence = read(DOCS/'memo-revision-evidence.json')
    example_issues[quote_evidence['quote_id']] = 'cross-topic--free-tier-premium-controls'
    sources.append(DOCS/'memo-revision-evidence.json')
    needed = set(example_issues)
    examples = []
    with Path('data/spotify_reviews_18months.csv').open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            if row['review_id'] in needed:
                examples.append({'review_id': row['review_id'], 'issue_id': example_issues[row['review_id']], 'text': row['review_text']})
    if len(examples) != len(needed):
        raise ValueError('Missing bounded example source')
    sources.append(Path('data/spotify_reviews_18months.csv'))
    ingestion = read(Path('grading/ingestion.json'))
    payload = {
        'version': 1,
        'meta': {'label_config': summary.pop('label_config'), 'grouping_hash': taxonomy['rule_hash'],
                 'memo_approval': approval, 'review_period': {'from': ingestion['first_review'], 'to': ingestion['last_review']},
                 'source_hashes': {p.as_posix(): sha(p) for p in sources},
                 'definitions': {'priority': 'severity_sum, descending; ties by issue ID',
                   'population': 'Completed complaint/cancellation original rows, including exact-text aliases',
                   'random_prefix': 'Completed members of the first 100,000 IDs in the seeded uniform permutation; 40 terminal IDs excluded',
                   'flags': 'Reasons overlap; one row can have several reasons',
                   'cache': 'Exact-text saved-result cache, not provider prompt caching',
                   'examples': 'Two selected examples per issue, plus the approved memo quote; not a random accuracy sample'},
                 'contains_full_records': False, 'model_calls_from_dashboard': False},
        'summary': summary, 'rankings': rankings,
        'claims': {'baseline': claims, 'secondary': table(DOCS/'secondary-claims.csv')},
        'examples': sorted(examples, key=lambda x: (x['issue_id'], x['review_id'])),
        'artifacts': {'memo': memo_path.read_text(encoding='utf-8'), 'original_memo': read(DOCS/'memo-draft.json'),
                      'groups': read(DOCS/'group-outputs.json'), 'verifier': read(DOCS/'verifier-agreement.json')},
    }
    payload = normalize(payload)
    snapshot_id = hashlib.sha256(canonical(payload).encode()).hexdigest()
    snapshot = {'snapshot_id': snapshot_id, 'payload': payload}
    encoded = (canonical(snapshot)+'\n').encode()
    for path in (OUTPUT/'snapshot.json', Path('web/.local/dashboard.json')):
        atomic_bytes(path, encoded)
    manifest = {'snapshot_id': snapshot_id, 'file_sha256': hashlib.sha256(encoded).hexdigest(),
                'snapshot_bytes': len(encoded), 'free_plan_storage_limit_bytes': 1000000000,
                'size_is_import_payload_not_postgres_disk_usage': True,
                'examples': len(examples), 'issues_per_view': {k: len(v) for k,v in rankings.items()},
                'contains_full_records': False, 'summary_counts': summary['counts'],
                'sources': payload['meta']['source_hashes'], 'new_api_calls': 0}
    atomic_json(Path('docs/phase8-snapshot-manifest.json'), manifest)
    # A small fixture copy is aggregate/sample-only and safe for public local tests.
    Path('web/tests').mkdir(parents=True,exist_ok=True)
    atomic_bytes(Path('web/tests')/'snapshot.json', encoded)
    print(json.dumps({k:manifest[k] for k in ('snapshot_id','snapshot_bytes','examples','issues_per_view','contains_full_records')}))
    return snapshot


if __name__ == '__main__':
    build()
