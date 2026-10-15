"""Offline production preparation, safe progress and explicit spend authorization."""
import csv
import hashlib
import itertools
import json
import shutil
import sqlite3
import subprocess
import time
import tomllib
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from pipeline.labeler import atomic_csv
from pipeline.prepare import atomic_json, course_helper
from pipeline.resume_evidence import audit, snapshot
from pipeline.schema import configuration
from pipeline.state import State

PLAN = Path('docs/100k-production-plan.json')
OUTPUT = Path('artifacts/scope-100k')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def git_head():
    return subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()


def prepare():
    """Build selected source and backup imported evidence, never invoke a provider."""
    if OUTPUT.exists() or PLAN.exists():
        raise ValueError('Production preparation exists; inspect it, never overwrite')
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    frozen = json.loads(Path('docs/frozen-label-config.json').read_text(encoding='utf-8'))
    draft = json.loads(Path('docs/100k-run-proposal-draft.json').read_text(encoding='utf-8'))
    if configuration(config)!=frozen['label_config'] or config['controls']['fallback_fraction']!=.2:
        raise ValueError('Expected approved final hash and 20% fallback')
    helper = course_helper(Path('data/check_submission.py'))
    raw = Path('data/spotify_reviews_18months.csv')
    manifest = json.loads(Path('data/manifest.json').read_text(encoding='utf-8'))
    if sha(raw)!=manifest['files'][raw.name]['sha256']:
        raise ValueError('Original full CSV checksum differs')
    with Path('artifacts/sampling/permutation.csv').open(encoding='utf-8',newline='') as stream:
        ids = {r['review_id'] for r in itertools.islice(csv.DictReader(stream),100000)}
    ids |= {r['review_id'] for r in helper.csv_rows(Path('data/golden_50_to_label.csv'))}
    # Stream preserved raw source; never regenerate source values from predictions.
    rows = [{f:r[f] for f in helper.FIELDS} for r in helper.csv_rows(raw) if r['review_id'] in ids]
    if len(rows)!=100041 or len({r['review_text'] for r in rows})!=77913:
        raise ValueError('Reviewed scope differs')
    OUTPUT.mkdir(parents=True)
    source = OUTPUT/'selected.csv'
    atomic_csv(source,list(helper.FIELDS),sorted(rows,key=lambda r:r['review_id']))
    base = Path(draft['base_state'])
    if sha(base)!=draft['base_state_sha256']:
        raise ValueError('Reviewed imported state changed')
    with closing(sqlite3.connect(f'file:{base.as_posix()}?mode=ro',uri=True)) as original, closing(sqlite3.connect(OUTPUT/'state.sqlite3')) as target:
        original.backup(target)
    state = State(OUTPUT/'state.sqlite3',configuration(config),require_reasons=True)
    state.ingest(source,Path('data/manifest.json'))
    with state.connect() as db:
        db.execute('CREATE TABLE production_scope(review_id TEXT PRIMARY KEY)')
        db.executemany('INSERT INTO production_scope VALUES (?)',[(rid,) for rid in sorted(ids)])
        db.execute('CREATE TABLE production_work(key TEXT PRIMARY KEY)')
        db.execute("INSERT INTO production_work SELECT key FROM work WHERE status='pending'")
        pending = db.execute('SELECT COUNT(*) FROM production_work').fetchone()[0]
        scoped_counts = dict(db.execute('SELECT r.status,COUNT(*) FROM reviews r JOIN production_scope s USING(review_id) GROUP BY r.status'))
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
    if pending!=75874 or state.leased_count() or integrity!='ok':
        raise ValueError('Prepared state differs from reviewed new-text count or integrity')
    plan = {**draft,'status':'prepared offline; awaiting owner yes; no calls',
            'recommendation_applied':True,'fallback_20_approval':'Approved and applied; paid run still awaits owner yes',
            'execution_approved':False,'preflight_verified':False,'output':str(OUTPUT),
            'scope_csv':str(source),'scope_csv_sha256':sha(source),
            'source_file':str(raw),'source_sha256':sha(raw),
            'prepared_state_sha256':sha(state.path),'scoped_initial_counts':scoped_counts,
            'operational_controls':config['controls'],'planning_rates':config['planning_rates'],
            'approval_receipt':str(OUTPUT/'authorization.json'),
            'recording_stop':'After about five minutes: stop admissions, drain saved Jev stages; final completed-row growth may occur only later after resume.'}
    atomic_json(PLAN,plan)
    return {'status':'prepared offline','scope_ids':len(ids),'new_texts':pending,'scoped_initial_counts':scoped_counts,'plan':str(PLAN),'api_calls':0}


def authorize(plan_path, acknowledged=False):
    """Offline receipt, run by owner only AFTER the chat cost gate is approved."""
    if not acknowledged:
        raise ValueError('Explicit --acknowledge-spend required after owner yes')
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    validate_plan(plan,initial=True)
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],text=True).strip():
        raise ValueError('Commit reviewed work locally before authorization')
    receipt = {'plan_sha256':sha(plan_path),'git_commit':git_head(),'authorized_at_utc':datetime.now(UTC).isoformat(),
               'invocation_cap_usd':plan['invocation_cap_usd'],'provider_balances_rechecked_by_owner':True}
    atomic_json(Path(plan['approval_receipt']),receipt)
    return {'status':'authorized offline; zero calls','git_commit':receipt['git_commit'],'shared_cap_usd':plan['invocation_cap_usd']}


def validate_plan(plan, initial=False):
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    if configuration(config)!=plan['label_config'] or config['controls']!=plan['operational_controls'] or config['planning_rates']!=plan['planning_rates']:
        raise ValueError('Reviewed configuration, controls or rates changed')
    if sha(Path(plan['scope_csv']))!=plan['scope_csv_sha256'] or sha(Path(plan['source_file']))!=plan['source_sha256']:
        raise ValueError('Selected or original input changed')
    if shutil.disk_usage('.').free < 10*2**30:
        raise ValueError('Less than 10 GiB free; stop')
    if initial and sha(Path(plan['output'])/'state.sqlite3')!=plan['prepared_state_sha256']:
        raise ValueError('Prepared initial state changed')
    with closing(sqlite3.connect(f'file:{Path(config["controls"]["ledger_path"]).as_posix()}?mode=ro',uri=True)) as db:
        total = db.execute("SELECT COALESCE(SUM(spent+CASE WHEN state='reserved' THEN amount ELSE 0 END),0) FROM reservations").fetchone()[0]
    if initial and total != round(plan['project_spent_usd']*1e9):
        raise ValueError('Project ledger changed since this cost gate; review before start')
    if initial and total+round(plan['invocation_cap_usd']*1e9)>round(config['controls']['project_api_cap_usd']*1e9):
        raise ValueError('Insufficient project headroom for approved cap')
    return config


def check_authorization(plan_path, plan, resume=False):
    receipt = json.loads(Path(plan['approval_receipt']).read_text(encoding='utf-8'))
    if receipt['plan_sha256']!=sha(plan_path) or receipt['git_commit']!=git_head():
        raise ValueError('Authorization plan or committed code changed')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],text=True).strip():
        raise ValueError('Uncommitted changes since authorization')
    validate_plan(plan,initial=not resume)


def status(output=OUTPUT):
    """Read-only allow-listed counters: never print payloads, reviews or keys."""
    with closing(sqlite3.connect(f'file:{(output/"state.sqlite3").as_posix()}?mode=ro',uri=True)) as db:
        counts = dict(db.execute('SELECT r.status,COUNT(*) FROM reviews r JOIN production_scope s USING(review_id) GROUP BY r.status'))
        row = db.execute("SELECT result FROM artifacts WHERE key='graceful-invocation'").fetchone()
        saved = json.loads(row[0]) if row else {}
        new = dict(db.execute('SELECT w.status,COUNT(*) FROM work w JOIN production_work p USING(key) GROUP BY w.status'))
        scored = db.execute('SELECT COUNT(*) FROM work w JOIN production_work p USING(key) WHERE w.jev_done=1').fetchone()[0]
        leases = db.execute('SELECT COUNT(*) FROM work WHERE lease IS NOT NULL').fetchone()[0]
    result = {'status':saved.get('status','prepared'),'phase':saved.get('phase'),
              'invocation_id':saved.get('run_id'),'workers':8,'fallback_fraction':.2,
              'scope_counts':counts,'new_distinct_counts':new,'saved_new_jev_scores':scored,
              'leases':leases,'shared_cap_usd':saved.get('cap',7.28),
              'elapsed_segment_seconds':round(time.time()-saved['started_epoch'],1) if saved.get('status')=='running' else saved.get('wall_seconds')}
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    path = Path(config['controls']['ledger_path'])
    with closing(sqlite3.connect(f'file:{path.as_posix()}?mode=ro',uri=True)) as db:
        spent,reserved = db.execute("SELECT COALESCE(SUM(spent),0),COALESCE(SUM(CASE WHEN state='reserved' THEN amount ELSE 0 END),0) FROM reservations").fetchone()
        own = db.execute("SELECT COALESCE(SUM(spent+CASE WHEN state='reserved' THEN amount ELSE 0 END),0) FROM reservations WHERE run_id=?",(saved.get('run_id',''),)).fetchone()[0]
        stop = db.execute('SELECT details FROM admission_stops WHERE run_id=?',(saved.get('run_id',''),)).fetchone()
    result.update(project_spent_usd=spent/1e9,reserved_usd=reserved/1e9,invocation_committed_usd=own/1e9,
                  invocation_remaining_usd=(round(result['shared_cap_usd']*1e9)-own)/1e9,
                  cap_latched=bool(stop))
    result['safe_to_resume'] = saved.get('status')=='stopped_user' and not leases and not reserved and not stop
    result['safe_to_continue_recovery'] = saved.get('status')=='recovery_ready' and not leases and not reserved and not stop
    return result


def evidence(which, output=OUTPUT):
    """Immutable snapshots; show counts and proofs, not review text or raw errors."""
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    target = output/('checkpoint_'+which+'.json')
    if which not in {'before','after'}:
        raise ValueError('Choose before or after')
    if target.exists():
        raise ValueError('Immutable checkpoint already exists; do not overwrite')
    with closing(sqlite3.connect(f'file:{(output/"state.sqlite3").as_posix()}?mode=ro',uri=True)) as db:
        receipt = json.loads(db.execute("SELECT result FROM artifacts WHERE key='graceful-invocation'").fetchone()[0])
    if which=='before' and (receipt['status']!='stopped_user' or not receipt['drained']):
        raise ValueError('Before snapshot requires a drained voluntary pause')
    if which=='after':
        before = set(json.loads(before_checkpoint(output).read_text(encoding='utf-8'))['completed_ids'])
        with closing(sqlite3.connect(f'file:{(output/"state.sqlite3").as_posix()}?mode=ro',uri=True)) as db:
            completed = {rid for rid, in db.execute("SELECT r.review_id FROM reviews r JOIN production_scope s USING(review_id) WHERE r.status='completed'")}
            events = (json.loads(e) for e, in db.execute('SELECT event FROM calls ORDER BY rowid DESC'))
            paid = any(e['run_id']==receipt['run_id'] and e['phase']=='resume' and e['outcome']=='succeeded' and not e.get('simulated') and e.get('cost_nanodollars',0)>0 and set(e['review_ids']) & (completed-before) for e in events)
        if not before < completed or not paid:
            raise ValueError('After checkpoint not ready: wait for new completed rows and a real paid resume call; no snapshot written')
    result = snapshot(output/'state.sqlite3',target,Path(plan['scope_csv']))
    try:
        proof = audit(output/'state.sqlite3',before_checkpoint(output),target,{receipt['run_id']},output/'resume-audit.json') if which=='after' else None
    except ValueError:
        # Preserve the attempted snapshot for diagnosis; never overwrite evidence.
        raise ValueError('After proof failed; preserve evidence and stop at a recovery gate') from None
    return {'checkpoint':str(target),'count':len(result['completed_ids']),'sha256':sha(target),
            'proof':{k:proof[k] for k in ('status','before_count','after_count','before_strict_subset_after','after_subset_completed','resume_enrich_ids_in_before')} if proof else None,
            'new_direct_paid_resume_count':len(proof['new_direct_paid_resume_ids']) if proof else None}


def proof(output=OUTPUT):
    with closing(sqlite3.connect(f'file:{(output/"state.sqlite3").as_posix()}?mode=ro',uri=True)) as db:
        receipt = json.loads(db.execute("SELECT result FROM artifacts WHERE key='graceful-invocation'").fetchone()[0])
    result = audit(output/'state.sqlite3',before_checkpoint(output),output/'checkpoint_after.json',
                   {receipt['run_id']},output/'resume-audit.json')
    return {key:result[key] for key in ('status','before_count','after_count','before_strict_subset_after','after_subset_completed','resume_enrich_ids_in_before')} | {'new_direct_paid_resume_count':len(result['new_direct_paid_resume_ids'])}


def before_checkpoint(output=OUTPUT):
    reconstructed = output/'checkpoint_before.reconstructed.json'
    if reconstructed.exists():
        provenance = json.loads((output/'checkpoint_before.reconstructed.provenance.json').read_text(encoding='utf-8'))
        if sha(reconstructed)!=provenance['reconstructed_sha256']:
            raise ValueError('Reconstructed before checkpoint changed')
        return reconstructed
    return output/'checkpoint_before.json'
