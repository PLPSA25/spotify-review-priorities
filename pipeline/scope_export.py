"""Offline exact-text propagation from the selected production scope only.

This interim export deliberately leaves business-stage CSVs empty until their gate.
Raw state, calls, checkpoints and the source CSV are never modified.
"""
import argparse
import json
import shutil
from collections import Counter
from contextlib import closing
from pathlib import Path

from pipeline.checker_resume_audit import grading_call_view
from pipeline.enrich import write_jsonl
from pipeline.prepare import atomic_json, course_helper
from pipeline.production import before_checkpoint, sha
from pipeline.schema import LABEL_FIELDS, validate_record
from pipeline.sqlite_read import read_connection


def propagated(row, helper, cache, failed):
    source = dict(row, source_sha256=helper.row_sha(row))
    base = {key: source[key] for key in ('review_id', 'source_sha256')}
    if row['review_text'] in cache:
        original = cache[row['review_text']]
        result = dict(base, status='completed', **{key: original[key] for key in LABEL_FIELDS})
        if row['review_id'] != original['review_id']:
            result['cache_source_id'] = original['review_id']
        validate_record(result, source, original['label_config'], require_reasons=True)
        return result
    reason = ('empty_review_text' if not row['review_text'].strip() else
              failed.get(row['review_text'], 'not_classified_partial_run'))
    return dict(base, status='quarantined', reason=reason)


def export(state_dir=Path('artifacts/scope-100k'), destination=Path('grading'),
           source=Path('data/spotify_reviews_18months.csv')):
    if any((destination/(name+'.gz')).exists() for name in ('records.jsonl', 'calls.jsonl')):
        raise ValueError('Compressed grading export exists; use a fresh staging directory, then repackage. Never create ambiguous plain/gzip pairs.')
    helper = course_helper(Path('data/check_submission.py'))
    source_hash = sha(source)
    manifest = json.loads(Path('data/manifest.json').read_text(encoding='utf-8'))
    if source_hash != manifest['files'][source.name]['sha256']:
        raise ValueError('Source checksum mismatch')
    destination.mkdir(parents=True, exist_ok=True)
    counts, reasons, cache = Counter(), Counter(), {}
    with closing(read_connection(state_dir/'state.sqlite3')) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity check failed')
        receipt = json.loads(db.execute("SELECT result FROM artifacts WHERE key='graceful-invocation'").fetchone()[0])
        if receipt['status'] != 'completed' or not receipt['drained'] or receipt['pending_leases']:
            raise ValueError('Export requires a completed, drained production run')
        config = db.execute("SELECT value FROM metadata WHERE key='label_config'").fetchone()[0]
        failed = dict(db.execute("SELECT r.text,r.reason FROM reviews r JOIN production_scope s USING(review_id) WHERE r.status='quarantined'"))
        selected = db.execute("SELECT r.text,r.result FROM reviews r JOIN production_scope s USING(review_id) WHERE r.status='completed'").fetchall()
        for text, raw in selected:
            record = json.loads(raw)
            original_id = record.get('cache_source_id', record['review_id'])
            if text not in cache:
                original = json.loads(db.execute("SELECT result FROM reviews WHERE review_id=? AND status='completed'", (original_id,)).fetchone()[0])
                if original.get('cache_source_id') or original['label_config'] != config:
                    raise ValueError('Invalid direct cache origin/configuration')
                cache[text] = original
            if any(record[key] != cache[text][key] for key in LABEL_FIELDS):
                raise ValueError('Selected exact-text labels disagree')

        def records():
            for row in helper.csv_rows(source):
                record = propagated(row, helper, cache, failed)
                counts[record['status']] += 1
                counts['cache_reuses'] += bool(record.get('cache_source_id'))
                if record['status'] == 'quarantined':
                    reasons[record['reason']] += 1
                yield record

        write_jsonl(destination/'records.jsonl', records())

        def calls():
            for raw, in db.execute('SELECT event FROM calls ORDER BY rowid'):
                event = grading_call_view(json.loads(raw), receipt['run_id'], config)
                if event is not None:
                    yield event

        # Full event contents retained. Compression/minimal projection is a separate gate.
        write_jsonl(destination/'calls.jsonl', calls())
    if sha(source) != source_hash:
        raise ValueError('Source changed during export')
    for name, origin in (('checkpoint_before.json', before_checkpoint(state_dir)),
                         ('checkpoint_after.json', state_dir/'checkpoint_after.json')):
        target = destination/name
        if target.exists() and sha(target) != sha(origin):
            raise ValueError('Existing exported immutable checkpoint differs')
        if not target.exists():
            shutil.copyfile(origin, target)
    shutil.copyfile(state_dir/'checkpoint_before.reconstructed.provenance.json', destination/'checkpoint_before.provenance.json')
    for name, header in (('membership.csv', 'issue_id,review_id'),
                         ('ranking.csv', 'rank,issue_id,complaint_count,severity_sum,mean_severity,priority_score'),
                         ('claims.csv', 'claim_id,issue_id,metric,value')):
        target = destination/name
        if not target.exists():
            target.write_text(header+'\n', encoding='utf-8')
    atomic_json(destination/'run.json', {
        'version': 'a5-audit-v1', 'analysis_count': sum(counts[key] for key in ('completed', 'quarantined')),
        'analysis_sha256': source_hash, 'classification_input_fields': ['review_text'],
        'allow_multi_issue': False, 'label_config': config, 'sample_prefix': 100000,
        'business_stages': 'pending: group/rank/claims/memo; empty CSV headers are interim only',
        'before_checkpoint': 'Post-hoc reconstruction; see checkpoint_before.provenance.json; not saved during clip 1',
        'cache': 'exact-text saved results; not provider prompt caching',
    })
    result = {'counts': dict(counts), 'quarantine_reasons': dict(reasons),
              'completed_distinct_texts': len(cache), 'source_sha256': source_hash,
              'nonempty_rows': sum(counts[key] for key in ('completed', 'quarantined')) - reasons['empty_review_text'],
              'model_calls': 0, 'business_stages_run': False}
    atomic_json(destination/'coverage.json', result)
    return result


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(export(), indent=2))
