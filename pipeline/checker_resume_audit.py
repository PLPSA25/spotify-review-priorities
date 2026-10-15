"""Execute the supplied checker's resume section, not a full submission audit."""
import ast
import json
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

from pipeline.prepare import atomic_json
from pipeline.production import sha


def grading_call_view(event, run_id, label_config):
    # Old incompatible enrichment belongs to raw provenance, not current grading.
    if event['role']=='enrich' and event['label_config']!=label_config:
        return None
    result = dict(event)
    if event['run_id']!=run_id:
        result.update(source_phase=event['phase'],source_run_id=event['run_id'],
                      imported=True,phase='initial')
    return result


def check(state_path, before_path, after_path, run_id, destination):
    source = Path('data/check_submission.py')
    tree = ast.parse(source.read_text(encoding='utf-8'))
    function = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='audit')
    nodes = [n for n in function.body if 314<=n.lineno<=370]
    if not nodes or nodes[-1].lineno!=369:
        raise ValueError('Checker changed; review exact resume section before using')
    flags = []
    before = json.loads(before_path.read_text(encoding='utf-8'))
    after = json.loads(after_path.read_text(encoding='utf-8'))
    with closing(sqlite3.connect(f'file:{state_path.as_posix()}?mode=ro',uri=True)) as db:
        config = db.execute("SELECT value FROM metadata WHERE key='label_config'").fetchone()[0]
        records = {rid:json.loads(result) for rid,result in db.execute("SELECT review_id,result FROM reviews WHERE status='completed'")}
        expected = {rid for rid, in db.execute('SELECT review_id FROM reviews')}

        def lines(_name):
            for raw, in db.execute('SELECT event FROM calls'):
                event = grading_call_view(json.loads(raw),run_id,config)
                if event is not None:
                    yield event

        namespace = {'obj':lambda name:before if name=='checkpoint_before.json' else after,
                     'lines':lines,'valid':records,'cached':{rid for rid,r in records.items() if r.get('cache_source_id')},
                     'expected':expected,'flag':lambda key,_detail:flags.append(key)}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source)+':resume-section','exec'),namespace)  # noqa: S102
    resume_codes = {'duplicate_checkpoint_id','resume_snapshot_mismatch','reprocessed_checkpoint','resume_call_evidence'}
    relevant = [f for f in flags if f in resume_codes]
    result = {'resume_rules_status':'pass' if not relevant else 'fail','resume_flags':dict(Counter(relevant)),
              'before_count':len(before['completed_ids']),'after_count':len(after['completed_ids']),
              'initial_logged_count':len(namespace['initial_logged']),
              'new_direct_resume_logged_count':len((namespace['after']-namespace['before']-namespace['cached'])&namespace['resume_logged']),
              'checker_file_sha256':sha(source),'checker_lines_executed':[314,370],
              'full_submission_check':False,'other_section_flags':dict(Counter(f for f in flags if f not in resume_codes)),
              'grading_view':'Imported phase mapped to initial with source_phase/source_run_id preserved; incompatible historical enrich hash omitted from grading view only. Raw calls unchanged.',
              'checkpoint_before_kind':'explicit post-hoc reconstruction; not contemporaneous video snapshot','api_calls':0}
    atomic_json(destination,result)
    if relevant:
        raise ValueError('Supplied checker resume rules failed; inspect saved report')
    return result
