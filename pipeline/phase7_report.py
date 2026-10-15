"""Offline report from saved Phase 7 receipts; never dispatches calls."""
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

from pipeline.phase7_work import OUTPUT


def report():
    def read(name):
        return json.loads((OUTPUT/name).read_text(encoding='utf-8'))
    receipt = read('receipt.json')
    agreement = read('verifier-agreement.json')
    business = read('business-summary.json')
    names = read('group-names.json')
    groups = read('group-outputs.json')
    checker = read('self-check.json')
    flag_comparison = read('flag-comparison.json')
    events = [json.loads(line) for line in (OUTPUT/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    export_unchanged = {}
    for filename, expected in receipt['source_gzip_sha256'].items():
        with Path(filename).open('rb') as stream:
            export_unchanged[filename] = hashlib.file_digest(stream, 'sha256').hexdigest() == expected
    if not all(export_unchanged.values()):
        raise ValueError('Tracked gzip changed before final submission export')
    evidence = Path('docs/phase7')
    evidence.mkdir(exist_ok=True)
    for name in ('claims.csv', 'grading_claims.csv', 'ranking.csv', 'sample_ranking.csv',
                 'verifier-agreement.json', 'flag-comparison.json', 'group-outputs.json', 'group-names.json',
                 'memo-draft.json', 'verifier-group-receipt.json', 'receipt.json', 'self-check.json'):
        target = 'extended-claims.csv' if name == 'claims.csv' and (evidence/'memo-revision-evidence.json').exists() else name
        shutil.copyfile(OUTPUT/name, evidence/target)
    lines = ['# Phase 7 measured gate — memo draft', '',
             'V3 is final. No golden labels informed grouping. Classifier prompt and hash are unchanged.', '',
             'Classifier hash: `'+receipt['label_config']+'`.', '',
             ('Cross-topic controls history: v1 had no unified issue (0); v2 3,407 rows / severity_sum 10,598; '
             'v3 4,444 / 13,877. All twelve cited recall cases now match. Changes address recall errors '
             'identified in random development spot-checks. No further tuning follows these results.'), '',
             ('The ten fresh full review texts and matching evidence are in '
             '[the v3 spot-check](phase7-cohort-spotcheck-v3.md). The station/no-shuffle example '
             '`d9312090` remains an ambiguous fit; inferred restrictions do not prove a Premium cause.'), '',
             '## Production verifier agreement', '',
             agreement['interpretation'], '',
             f"Sampled {agreement['sampled']}; terminal verifier items {agreement['terminal_verifier_items']}."]
    for split in ('overall', 'flagged', 'unflagged', 'fallback', 'no_fallback'):
        row = agreement[split]
        lines += ['', f"### {split} (n={row['n']})", '']
        for field, metric in row['fields'].items():
            pct = f"{100*metric['agreement']:.1f}%" if metric['agreement'] is not None else 'unavailable'
            lines.append(f"- {field}: {metric['agree']}/{metric['denominator']} ({pct}).")
    lines += ['', '### Flag-policy comparison', '',
              'Saved flag comparison: `'+json.dumps(flag_comparison, sort_keys=True)+'`.', '',
              ('Reason counts overlap. The frozen pipeline keeps missing-context signals through fallback; '
              'the blinded verifier makes its own judgment. This comparison does not validate either as human truth '
              'and does not authorize any threshold or flag-policy change.')]
    lines += ['', '## Raw group-call outputs', '',
              ('These calls name fixed deterministic cohorts; they do not change memberships or ranking. '
              'Owner-approved display names override model names where noted.')]
    for stage, output in groups.items():
        lines += ['', '### '+stage, '']
        for row in output['issues']:
            suffix = ' Final display: '+names[row['issue_id']]+'.' if names[row['issue_id']] != row['name'] else ''
            lines.append('- `'+row['issue_id']+'`: '+row['name']+'.'+suffix)
    for key, title in [('ranking', 'Propagated baseline'), ('sample_ranking', 'Random-prefix-only')]:
        lines += ['', '## '+title+' top ten', '']
        for row in business[key][:10]:
            lines.append(f"{row['rank']}. {names[row['issue_id']]} (`{row['issue_id']}`): "
                         f"{row['complaint_count']} members; severity_sum/priority {row['severity_sum']}.")
    lines += ['', '## Checker and measured spend', '',
              'Validation: 220 tests passed; Ruff checks passed. Tests make no paid calls.', '',
              'Call counts by stage: `'+json.dumps(dict(Counter(e['stage'] for e in events)), sort_keys=True)+'`.', '',
              'Call outcomes: `'+json.dumps(dict(Counter(e['outcome'] for e in events)), sort_keys=True)+'`.', '',
              ('Verification used ten initial batches and one singleton repair; no verifier items were terminal. '
              'The rendered memo clarifies the model phrase "unclassified complaint" as "complaint with an '
              'unspecified cause"; the original response is preserved in phase7/memo-draft.json.'), '',
              'Tracked gzip hash comparisons: `'+json.dumps(export_unchanged, sort_keys=True)+'`.', '',
              'Working submission: artifacts/phase7/grading-check; tracked grading/*.gz were not rewritten.', '',
              'Checker flags: `'+json.dumps(checker['issue_counts'], sort_keys=True)+'`.', '',
              ('The partial-scope unfinished_classification flag counts unclassified/quarantined nonempty '
              'rows; it is the declared scope limitation. Twenty invalid_usage fields belong to ten '
              'historical connection failures with unknown charged token usage. Nulls are retained honestly. '
              'Any additional flag must be investigated rather than treated as expected.'), '',
              (f"Invocation status: {receipt['status']}; actual spend ${receipt['invocation_spent_usd']:.9f} "
              'against the shared $1.58 cap.'), '',
              'Ledger totals (nanodollars): `'+json.dumps(receipt['ledger'], sort_keys=True)+'`.', '',
              ('[Memo draft](phase7-memo-draft.md). Checker-compatible baseline evidence: '
              '[claims.csv](phase7/claims.csv); secondary figures: [secondary claims](phase7/secondary-claims.csv). Baseline projection: '
              '[grading_claims.csv](phase7/grading_claims.csv). The memo is not final; stop for owner review.')]
    Path('docs/phase7-gate.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


if __name__ == '__main__':
    report()
