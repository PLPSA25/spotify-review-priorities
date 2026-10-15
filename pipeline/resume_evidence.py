"""Offline recording snapshots and no-relabel evidence; no provider imports."""
import csv
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from pipeline.prepare import atomic_json


def snapshot(state, destination, scope_csv=None):
    if destination.resolve()==state.resolve() or (scope_csv and destination.resolve()==scope_csv.resolve()) or destination.resolve().is_relative_to(Path('data').resolve()):
        raise ValueError('Checkpoint must not overwrite state or preserved source data')
    selected = None
    if scope_csv:
        with scope_csv.open(encoding='utf-8-sig',newline='') as stream:
            selected = {row['review_id'] for row in csv.DictReader(stream)}
    with closing(sqlite3.connect(f'file:{state.as_posix()}?mode=ro',uri=True)) as db:
        config = db.execute("SELECT value FROM metadata WHERE key='label_config'").fetchone()[0]
        completed = {rid for rid, in db.execute("SELECT review_id FROM reviews WHERE status='completed'")}
    if selected is not None:
        completed &= selected
    result = {'completed_ids':sorted(completed),'label_config':config}
    atomic_json(destination,result)
    return result


def audit(state, before_path, after_path, run_ids, output):
    if output.resolve() in {state.resolve(),before_path.resolve(),after_path.resolve()} or output.resolve().is_relative_to(Path('data').resolve()):
        raise ValueError('Audit must not overwrite evidence or preserved source data')
    if not run_ids:
        raise ValueError('Explicit production demo run IDs required; imported development calls excluded')
    before = json.loads(before_path.read_text(encoding='utf-8'))
    after = json.loads(after_path.read_text(encoding='utf-8'))
    b, a = set(before['completed_ids']), set(after['completed_ids'])
    added = a-b
    with closing(sqlite3.connect(f'file:{state.as_posix()}?mode=ro',uri=True)) as db:
        config = db.execute("SELECT value FROM metadata WHERE key='label_config'").fetchone()[0]
        records = {rid:json.loads(record) for rid,record in db.execute("SELECT review_id,result FROM reviews WHERE status='completed'")}
        touched, new_paid = set(), set()
        for raw, in db.execute('SELECT event FROM calls'):
            e = json.loads(raw)
            if e['run_id'] not in run_ids or e['phase']!='resume' or e['role']!='enrich':
                continue
            touched.update(e['review_ids'])
            if e['outcome']=='succeeded' and e['label_config']==config and not e.get('simulated',False) and e.get('cost_nanodollars',0)>0:
                new_paid.update(rid for rid in e['review_ids'] if rid in added and not records.get(rid,{}).get('cache_source_id'))
    result = {'status':'pass' if b<a<=set(records) and not b&touched and bool(new_paid) and before['label_config']==after['label_config']==config else 'fail',
              'before_count':len(b),'after_count':len(a),'new_completed_ids':len(a-b),
              'before_strict_subset_after':b<a,'after_subset_completed':a<=set(records),
              'resume_enrich_ids_in_before':sorted(b&touched),'new_direct_paid_resume_ids':sorted(new_paid),
              'label_config':config,'demo_run_ids':sorted(run_ids),'model_calls':0,
              'note':'Audits explicit production demo run IDs only. Final grading adapter must preserve source_phase and map imported development-call phase to initial relative to this recording; raw historical logs remain unchanged.'}
    atomic_json(output,result)
    if result['status']!='pass':
        raise ValueError('Resume evidence failed; inspect saved audit')
    return result
