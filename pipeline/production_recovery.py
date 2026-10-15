"""Approved offline recovery; paid continuation is invoked by the owner only."""
import json
import shutil
import sqlite3
import subprocess
import threading
import tomllib
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from pipeline.batching import commit_validated
from pipeline.failure_policy import failure_window
from pipeline.graceful import window_dump, window_restore
from pipeline.monitor_migration import split_legacy_terminal_history
from pipeline.prepare import atomic_json
from pipeline.production import OUTPUT, PLAN, git_head, sha, validate_plan
from pipeline.resume_evidence import audit, snapshot
from pipeline.schema import configuration, validate_record
from pipeline.state import State

RECOVERY = OUTPUT/'recovery'
CONTINUATION = RECOVERY/'continuation.json'


def recover_results(state, valid):
    """Only stored, validated outputs; no transport or ledger instance exists."""
    keys = {}
    with state.connect() as db:
        for rid,result in valid.items():
            row = db.execute('SELECT source,work_key,status FROM reviews WHERE review_id=?',(rid,)).fetchone()
            validate_record(result,json.loads(row['source']),state.label_config,require_reasons=True)
            if row['status']!='pending':
                raise ValueError('Replay only pending validated originals')
            keys[rid] = row['work_key']
    for start in range(0,len(keys),20):
        members = list(keys)[start:start+20]
        items = state.claim_keys([keys[rid] for rid in members],300)
        if len(items)!=len(members):
            raise ValueError('Replay items changed')
        commit_validated(state,SimpleNamespace(stop=threading.Event()),items,
                         {rid:valid[rid] for rid in members},'extract')
    return len(keys)


def apply_offline():
    """Owner approved this exact recovery; refuse changed baseline or repeat apply."""
    if RECOVERY.exists():
        raise ValueError('Recovery directory exists; inspect, never replay blindly')
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    diagnostic = json.loads(Path('docs/100k-halt-diagnosis.json').read_text(encoding='utf-8'))
    proposal = json.loads(Path('docs/100k-monitor-migration-proposal.json').read_text(encoding='utf-8'))
    original_call_log_sha256 = sha(OUTPUT/'calls.jsonl')
    original_path = OUTPUT/'stop-receipt.json'
    original = json.loads(original_path.read_text(encoding='utf-8'))
    if sha(original_path)!=proposal['original_receipt_sha256'] or original['status']!='failed' or not original['drained']:
        raise ValueError('Halt receipt changed or not drained')
    if configuration(tomllib.loads(Path('config.toml').read_text(encoding='utf-8')))!=original['label_config']:
        raise ValueError('Frozen hash changed')
    validate_plan(plan)
    with closing(sqlite3.connect(f'file:{(OUTPUT/"state.sqlite3").as_posix()}?mode=ro',uri=True)) as db:
        current = json.loads(db.execute("SELECT result FROM artifacts WHERE key='graceful-invocation'").fetchone()[0])
        if current!=original or db.execute('SELECT COUNT(*) FROM work WHERE lease IS NOT NULL').fetchone()[0]:
            raise ValueError('Live failed state differs')
        bad = {key for key, in db.execute("SELECT w.key FROM work w JOIN production_work p USING(key) WHERE w.status='quarantined'")}
        bad_origins = {origin for origin, in db.execute("SELECT w.origin_id FROM work w JOIN production_work p USING(key) WHERE w.status='quarantined'")}
        sources = {rid:json.loads(source) for rid,source in db.execute('SELECT review_id,source FROM reviews')}
        pending = {rid for rid, in db.execute("SELECT review_id FROM reviews WHERE status='pending'")}
        valid = {}
        for raw, in db.execute("SELECT DISTINCT c.event FROM calls c JOIN call_reviews cr USING(request_id) WHERE cr.stage='extract'"):
            event = json.loads(raw)
            if event['run_id']==original['run_id'] and event['outcome']=='succeeded':
                valid.update({rid:value for rid,value in event.get('validated_results',{}).items() if rid in pending})
    if set(valid)!=set(diagnostic['valid_pending_replay_ids']) or len(valid)!=133 or len(bad)!=3:
        raise ValueError('Reviewed replay/terminal identities changed')
    ledger_path = Path(tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))['controls']['ledger_path'])
    with closing(sqlite3.connect(f'file:{ledger_path.as_posix()}?mode=ro',uri=True)) as db:
        ledger_before = list(db.execute('SELECT id,run_id,amount,spent,state,accounting FROM reservations ORDER BY id'))
        if any(row[4]=='reserved' for row in ledger_before) or db.execute('SELECT 1 FROM admission_stops WHERE run_id=?',(original['run_id'],)).fetchone():
            raise ValueError('Reservation or latch prevents reviewed recovery')
        if sum(row[3] for row in ledger_before if row[1]==original['run_id'])!=3704475953:
            raise ValueError('Reviewed invocation spend changed')
    migration = split_legacy_terminal_history(original,bad)
    RECOVERY.mkdir()
    shutil.copy2(original_path,RECOVERY/'original-stop-receipt.json')
    shutil.copy2(OUTPUT/'authorization.json',RECOVERY/'original-authorization.json')
    for path in OUTPUT.glob('segment-*.json'):
        shutil.copy2(path,RECOVERY/path.name)
    for source,dest in ((OUTPUT/'state.sqlite3',RECOVERY/'state.before-recovery.sqlite3'),
                        (ledger_path,RECOVERY/'ledger.before-recovery.sqlite3')):
        with closing(sqlite3.connect(f'file:{source.as_posix()}?mode=ro',uri=True)) as db, closing(sqlite3.connect(dest)) as target:
            db.backup(target)
    print('Original state, ledger and receipts backed up; zero calls.',flush=True)
    base = Path(plan['base_state'])
    if sha(base)!=plan['base_state_sha256']:
        raise ValueError('Preserved pre-run base state changed')
    with closing(sqlite3.connect(f'file:{base.as_posix()}?mode=ro',uri=True)) as db:
        old_texts = {text for text, in db.execute("SELECT text FROM work WHERE status='completed'")}
    import csv
    with Path(plan['scope_csv']).open(encoding='utf-8',newline='') as stream:
        selected = {r['review_id'] for r in csv.DictReader(stream)}
    before = sorted(rid for rid in selected if sources[rid]['review_text'] in old_texts)
    pauses = [json.loads(p.read_text(encoding='utf-8')) for p in RECOVERY.glob('segment-*.json')]
    pause = next(p for p in pauses if p['status']=='stopped_user' and p['phase']=='initial')
    if len(before)!=19719 or pause['counts']['completed']!=28224 or len(pause['classification_window']['seen'])!=5570:
        raise ValueError('Pause reconstruction evidence differs')
    reconstructed = OUTPUT/'checkpoint_before.reconstructed.json'
    if reconstructed.exists() or (OUTPUT/'checkpoint_before.json').exists():
        raise ValueError('Before evidence already exists; never overwrite')
    atomic_json(reconstructed,{'completed_ids':before,'label_config':original['label_config']})
    provenance = {'created_at_utc':datetime.now(UTC).isoformat(),'kind':'post-hoc reconstruction; not saved during clip-1',
                  'owner_account':r'A paste produced scope-evidence beforeSet-Location C:\dev\Spotify; argparse rejected it and no before file was written.',
                  'recording_observed_state':{'status':'stopped_user','phase':'initial','drained':True,
                    'scoped_completed':19719,'saved_new_jev_scores':5570,'safe_to_resume':True,'run_id':original['run_id']},
                  'method':'Intersect pinned selected review IDs with completed exact texts in preserved pre-run base. Initial pause receipt proves no new final completions then; current later completions are not used to infer the before cohort.',
                  'base_state_sha256':sha(base),'selected_csv_sha256':sha(Path(plan['scope_csv'])),
                  'original_pause_receipt_sha256':sha(RECOVERY/('segment-'+pause['segment_id']+'.json')),
                  'count':len(before),'reconstructed_sha256':sha(reconstructed)}
    atomic_json(OUTPUT/'checkpoint_before.reconstructed.provenance.json',provenance)
    state = State(OUTPUT/'state.sqlite3',original['label_config'],require_reasons=True)
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    state.failure_window = window_restore(failure_window(config),migration['terminal_window'])
    state.artifact('original-failed-invocation:'+original['segment_id'],original)
    state.artifact('approved-stage-history-repartition',{
        'original_receipt_sha256':proposal['original_receipt_sha256'],'original_preserved_at':str(RECOVERY/'original-stop-receipt.json'),
        'classification_unchanged':True,'connection_unchanged':True,'reassigned_jev_keys':sorted(bad),
        'pre_replay_terminal_window':migration['terminal_window'],'applied':True})
    recovered = recover_results(state,valid)
    from pipeline.enrich import export_state
    export_state(state,OUTPUT,False,SimpleNamespace(totals=lambda:{'spent_nanodollars':4474552938,'reserved_nanodollars':0}))
    if sha(OUTPUT/'calls.jsonl')!=original_call_log_sha256:
        raise ValueError('Offline recovery changed raw call log bytes')
    ready = {**original,'status':'recovery_ready','counts':state.counts(),
             'terminal_window':window_dump(state.failure_window),'offline_recovered':recovered,
             'recovery_timestamp_utc':datetime.now(UTC).isoformat(),
             'original_failed_segment':original['segment_id']}
    state.artifact('graceful-invocation',ready)
    atomic_json(RECOVERY/'ready-receipt.json',ready)
    with state.connect() as db:
        if bad_origins!={row[0] for row in db.execute("SELECT w.origin_id FROM work w JOIN production_work p USING(key) WHERE w.status='quarantined'")}:
            raise ValueError('Terminal identities changed')
        if db.execute('SELECT COUNT(*) FROM work WHERE lease IS NOT NULL').fetchone()[0]:
            raise ValueError('Offline recovery left a lease')
    with closing(sqlite3.connect(f'file:{ledger_path.as_posix()}?mode=ro',uri=True)) as db:
        if ledger_before!=list(db.execute('SELECT id,run_id,amount,spent,state,accounting FROM reservations ORDER BY id')):
            raise ValueError('Ledger changed during offline recovery')
    if sha(original_path)!=proposal['original_receipt_sha256']:
        raise ValueError('Original failed receipt was overwritten')
    after = OUTPUT/'checkpoint_after.offline-recovery.json'
    result = snapshot(state.path,after,Path(plan['scope_csv']))
    proof = audit(state.path,reconstructed,after,{original['run_id']},RECOVERY/'resume-audit.offline-recovery.json')
    from pipeline.checker_resume_audit import check
    checker = check(state.path,reconstructed,after,original['run_id'],RECOVERY/'supplied-checker-resume.json')
    report = {'status':'offline recovery complete; owner continuation only','recovered_outputs':recovered,
              'run_id':original['run_id'],'label_config':state.label_config,'counts':state.counts(),
              'before_count':len(before),'before_sha256':sha(reconstructed),'after_count':len(result['completed_ids']),
              'resume_proof':proof['status'],'new_direct_paid_resume_count':len(proof['new_direct_paid_resume_ids']),
              'supplied_checker_resume_rules':checker['resume_rules_status'],'checker_other_flags':checker['other_section_flags'],
              'remaining_invocation_cap_usd':3.575524047,'project_spend_usd':4.474552938,
              'ledger_unchanged':True,'terminal_items_unchanged':True,'original_failed_receipt_unchanged':True,
              'raw_call_log_bytes_unchanged':True,
              'api_calls':0,'state_after_recovery_sha256':sha(state.path)}
    atomic_json(RECOVERY/'offline-report.json',report)
    atomic_json(Path('docs/100k-offline-recovery-result.json'),report)
    print(json.dumps(report,indent=2),flush=True)
    return report


def seal_continuation():
    """Offline bind the owner-run command to the reviewed local commit and state."""
    if subprocess.check_output(['git','status','--porcelain'],text=True).strip():
        raise ValueError('Commit reviewed code before sealing continuation')
    result = json.loads((RECOVERY/'offline-report.json').read_text(encoding='utf-8'))
    if CONTINUATION.exists():
        raise ValueError('Continuation authorization already sealed')
    value = {**result,'git_commit':git_head(),'plan_sha256':sha(PLAN),
             'ready_receipt_sha256':sha(RECOVERY/'ready-receipt.json'),
             'shared_invocation_cap_usd':7.28,'owner_runs_paid_command_only':True}
    atomic_json(CONTINUATION,value)
    return {'status':'sealed offline; no calls','git_commit':value['git_commit'],'remaining_usd':3.575524047}


def run_continuation(path=CONTINUATION,confirmed=False):
    if not confirmed:
        return {'status':'offline; owner must explicitly run --confirm-spend','api_calls':0}
    receipt = json.loads(path.read_text(encoding='utf-8'))
    if receipt['git_commit']!=git_head() or receipt['plan_sha256']!=sha(PLAN) or subprocess.check_output(['git','status','--porcelain'],text=True).strip():
        raise ValueError('Recovery authorization/code/plan changed')
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    config = validate_plan(plan)
    ready = json.loads((RECOVERY/'ready-receipt.json').read_text(encoding='utf-8'))
    if sha(RECOVERY/'ready-receipt.json')!=receipt['ready_receipt_sha256'] or sha(OUTPUT/'state.sqlite3')!=receipt['state_after_recovery_sha256']:
        raise ValueError('Reviewed recovered state or receipt changed')
    config['controls'].update(max_workers=8,run_api_cap_usd=7.28)
    from pipeline.calls import Calls
    from pipeline.enrich import export_state
    from pipeline.graceful import run_segment
    from pipeline.providers import HTTPTransport, keys_from_env
    from pipeline.spend import Ledger
    state = State(OUTPUT/'state.sqlite3',receipt['label_config'],require_reasons=True)
    if state.artifact('graceful-invocation')!=ready or ready['run_id']!=receipt['run_id']:
        raise ValueError('Recovery-ready identity changed')
    ledger = Ledger(Path(config['controls']['ledger_path']),10)
    if ledger.totals()!={'spent_nanodollars':4474552938,'reserved_nanodollars':0} or ledger.run_stop(receipt['run_id']):
        raise ValueError('Ledger or latch changed; review before continuing')
    transport = HTTPTransport(keys_from_env(Path('.env')),config['controls']['request_timeout_seconds'],
                              connect_timeout=config['controls']['connect_timeout_seconds'])
    calls = Calls(state,ledger,transport,config,receipt['run_id'],'resume')
    try:
        return run_segment(state,calls,config,OUTPUT,resume=True,recovery=True)
    finally:
        transport.close()
        export_state(state,OUTPUT,False,ledger)
