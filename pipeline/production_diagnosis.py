"""Read-only production halt audit. No State/Ledger constructors or providers."""
import hashlib
import json
import sqlite3
import tomllib
from collections import Counter
from contextlib import closing
from pathlib import Path

from pipeline.classify import luna_batch_payload, luna_payload
from pipeline.prepare import atomic_json
from pipeline.schema import canonical, configuration, validate_record
from pipeline.spend import token_cost

ROOT = Path('artifacts/scope-100k')


def build():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    plan = json.loads(Path('docs/100k-production-plan.json').read_text(encoding='utf-8'))
    counts, failures, connections, extraction_errors, valid = Counter(),[],[],{},{}
    hashes, costs, all_costs = {},Counter(),0
    with closing(sqlite3.connect(f'file:{(ROOT/"state.sqlite3").as_posix()}?mode=ro',uri=True)) as db:
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
        print('SQLite integrity: '+integrity,flush=True)
        receipt = json.loads(db.execute("SELECT result FROM artifacts WHERE key='graceful-invocation'").fetchone()[0])
        run_id = receipt['run_id']
        rows = {rid:{'source':json.loads(source),'key':key,'status':status,'result':json.loads(result) if result else None}
                for rid,source,key,status,result in db.execute('SELECT review_id,source,work_key,status,result FROM reviews')}
        work = {key:{'status':status,'origin_id':origin,'reason':reason} for key,status,origin,reason in db.execute('SELECT key,status,origin_id,reason FROM work')}
        new_keys = {key for key, in db.execute('SELECT key FROM production_work')}
        scoped = {rid for rid, in db.execute('SELECT review_id FROM production_scope')}
        scores = {key:json.loads(result) for key,result in db.execute("SELECT work_key,result FROM stage_results WHERE stage='jev'")}
        active = json.loads(db.execute("SELECT result FROM artifacts WHERE key='active-routing-tranche'").fetchone()[0])
        selection = json.loads(db.execute('SELECT result FROM artifacts WHERE key=?',('routing-selection:'+active['id'],)).fetchone()[0])
        succeeded_jev = set()
        for (raw,) in db.execute('SELECT event FROM calls'):
            e = json.loads(raw)
            hashes[e['request_id']] = hashlib.sha256(canonical(e).encode()).hexdigest()
            if e['run_id']!=run_id:
                continue
            counts[e['phase']+'/'+e['provider']+'/'+e['stage']+'/'+e['outcome']] += 1
            costs[e['provider']] += e.get('cost_nanodollars',0)
            all_costs += e.get('cost_nanodollars',0)
            if e['stage']=='jev' and e['outcome']=='succeeded':
                succeeded_jev.add(rows[e['review_ids'][0]]['key'])
            if e['outcome']=='failed':
                safe = {k:e.get(k) for k in ('request_id','review_ids','provider','stage','phase','attempt','error','original_error','transport_diagnostic','started_at_utc','finished_at_utc','cost_nanodollars')}
                failures.append(safe)
                if e.get('accounting')=='pessimistic_unknown_charge':
                    connections.append(safe)
            for rid,error in e.get('validation_errors',{}).items():
                extraction_errors[rid] = {'error':error,'request_id':e['request_id'],'stage':e['stage']}
            for rid,result in e.get('validated_results',{}).items():
                validate_record(result,rows[rid]['source'],receipt['label_config'],require_reasons=True)
                valid[rid] = {'record':result,'request_id':e['request_id'],'stage':e['stage']}
        lease_count = db.execute('SELECT COUNT(*) FROM work WHERE lease IS NOT NULL').fetchone()[0]
        unresolved = db.execute("SELECT COUNT(*) FROM calls WHERE json_extract(event,'$.accounting') IN ('unknown_charge','unknown_charge_reservation_retained')").fetchone()[0]
    print('Call and validated-response audit complete',flush=True)
    log_hashes = {}
    with (ROOT/'calls.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            e = json.loads(line)
            if e['request_id'] in log_hashes:
                raise ValueError('Duplicate exported request ID')
            log_hashes[e['request_id']] = hashlib.sha256(canonical(e).encode()).hexdigest()
    completed = {rid:row['result'] for rid,row in rows.items() if row['status']=='completed'}
    for rid,record in completed.items():
        validate_record(record,rows[rid]['source'],receipt['label_config'],require_reasons=True)
        if record.get('cache_source_id'):
            origin = completed[record['cache_source_id']]
            if origin.get('cache_source_id'):
                raise ValueError('Chained cache origin')
    replay = {rid:item for rid,item in valid.items() if rows[rid]['status']=='pending'}
    if not succeeded_jev==new_keys&set(scores):
        raise ValueError('Saved new Jev results differ from succeeded call provenance')
    for key in new_keys&set(scores):
        result = scores[key]
        source = rows[work[key]['origin_id']]['source']
        validate_record({**result,'review_id':source['review_id'],'source_sha256':source['source_sha256'],
                         'status':'completed','label_config':receipt['label_config'],
                         'entities':[],'evidence_quote':source['review_text']},source,receipt['label_config'],require_reasons=True)
    # Reconstruct, but DO NOT WRITE, the completed set at the voluntary pause.
    # Paused receipt proves no new final records then: all completions were imported.
    base = Path(plan['base_state'])
    with closing(sqlite3.connect(f'file:{base.as_posix()}?mode=ro',uri=True)) as db:
        base_texts = {text for text, in db.execute("SELECT text FROM work WHERE status='completed'")}
    before = {rid for rid in scoped if rows[rid]['source']['review_text'] in base_texts}
    pause = [json.loads(p.read_text(encoding='utf-8')) for p in ROOT.glob('segment-*.json')]
    pause = [p for p in pause if p['phase']=='initial' and p['status']=='stopped_user']
    if len(pause)!=1 or pause[0]['counts']['completed']!=len(completed)-24 or len(before)!=19719:
        raise ValueError('Unexpected pause baseline; reconstruction not proven')
    with closing(sqlite3.connect(f'file:{Path(config["controls"]["ledger_path"]).as_posix()}?mode=ro',uri=True)) as db:
        ledger = db.execute("SELECT COALESCE(SUM(spent),0),COALESCE(SUM(CASE WHEN state='reserved' THEN amount ELSE 0 END),0) FROM reservations").fetchone()
        own = db.execute('SELECT SUM(spent) FROM reservations WHERE run_id=?',(run_id,)).fetchone()[0]
        latch = db.execute('SELECT details FROM admission_stops WHERE run_id=?',(run_id,)).fetchone()
    # Calls-independent conservative continuation envelope; no paid Jev work remains.
    pending = {key for key in new_keys if work[key]['status']=='pending'}
    replay_keys = {rows[rid]['key'] for rid in replay}
    remaining_modes = Counter()
    byte_bounds = Counter()
    root_calls = Counter()
    root_bounds = Counter()
    remaining_keys = pending-replay_keys
    rates = dict(config['planning_rates'])
    rates['luna_input_per_million'] = max(rates['luna_input_per_million'],rates['luna_cache_write_per_million'])
    touches_before = set()
    with closing(sqlite3.connect(f'file:{(ROOT/"state.sqlite3").as_posix()}?mode=ro',uri=True)) as db:
        # Indexed review/call relation; no second parse of the full raw responses.
        for rid, in db.execute("SELECT DISTINCT cr.review_id FROM call_reviews cr JOIN calls c USING(request_id) WHERE json_extract(c.event,'$.run_id')=? AND json_extract(c.event,'$.phase')='resume'",(run_id,)):
            if rid in before:
                touches_before.add(rid)
    for batch in selection['batches']:
        keys = [key for key in batch['keys'] if key in remaining_keys]
        if not keys:
            continue
        remaining_modes[batch['mode']] += len(keys)
        if batch['mode']=='local':
            continue
        items = [{'key':key,'source':rows[work[key]['origin_id']]['source']} for key in keys]
        labels = {i['source']['review_id']:scores[i['key']] for i in items}
        payload = luna_batch_payload(items,labels,config,batch['mode']=='extract')
        root_bounds[batch['mode']] += token_cost(len(canonical(payload).encode())+config['controls']['token_overhead_bound'],payload['max_output_tokens'],rates,'openai')
        root_calls[batch['mode']] += 1
        for item in items:
            single = luna_payload(item['source'],labels[item['source']['review_id']],config,batch['mode']=='extract')
            bound = len(canonical(single).encode())+config['controls']['token_overhead_bound']+1024
            byte_bounds[batch['mode']] += 4*token_cost(bound,200,rates,'openai')
    error_counts = Counter(e['error'] for e in failures)
    terminal = [{'review_id':work[key]['origin_id'],'reason':work[key]['reason']} for key in sorted(new_keys) if work[key]['status']=='quarantined']
    remaining = round(receipt['cap']*1e9)-own
    unit = json.loads(Path('docs/fallback-options-development.json').read_text(encoding='utf-8'))['cost_time_reference']['unit_luna_cost_per_text_including_repairs']
    expected = sum(remaining_modes[mode]*unit[mode] for mode in ('extract','fallback'))
    report = {'run_id':run_id,'label_config':receipt['label_config'],'hash_still_matches':configuration(config)==receipt['label_config'],
              'halt_error':receipt['error'],'new_work_counts':dict(Counter(work[k]['status'] for k in new_keys)),
              'saved_new_jev_scores':len(new_keys&set(scores)),'saved_scores_equal_succeeded_jev_keys':True,
              'calls':dict(counts),'failure_errors':dict(error_counts),'failed_calls':failures,'connections':connections,
              'new_terminal_items':terminal,'luna_invalid_items':extraction_errors,
              'luna_valid_outputs':len(valid),'valid_pending_replay_count':len(replay),
              'valid_pending_replay_ids':sorted(replay),'remaining_modes_after_proposed_offline_replay':dict(remaining_modes),
              'remaining_root_requests_upper':dict(root_calls),'remaining_all_retries_byte_envelope_usd':sum(byte_bounds.values())/1e9,
              'remaining_root_batch_byte_envelope_usd':sum(root_bounds.values())/1e9,
              'remaining_base_estimate_usd':expected,'remaining_invocation_cap_usd':remaining/1e9,
              'project_spent_usd':ledger[0]/1e9,'project_reserved_usd':ledger[1]/1e9,
              'invocation_spent_usd':own/1e9,'calls_usage_equals_ledger':own==all_costs,
              'provider_cost_usd':{k:v/1e9 for k,v in costs.items()},'cap_latched':bool(latch),'unresolved_call_outcomes':unresolved,
              'integrity':integrity,'leases':lease_count,'completed_validated':len(completed),
              'scoped_completed':len(set(completed)&scoped),'unscoped_imported_completed':len(set(completed)-scoped),
              'call_log_count':len(log_hashes),'sqlite_call_count':len(hashes),'call_log_matches_sqlite_exactly':hashes==log_hashes,
              'monitor_windows':{key:{'n':len(receipt[key]['outcomes']),'failures':sum(receipt[key]['outcomes'])} for key in ('classification_window','terminal_window','connection_window')},
              'before_snapshot_exists':(ROOT/'checkpoint_before.json').exists(),'recoverable_before_ids_count':len(before),
              'posthoc_reconstruction_only':True,'before_reconstruction_sha256':hashlib.sha256(canonical(sorted(before)).encode()).hexdigest(),
              'resume_enrich_ids_in_reconstructed_before':sorted(touches_before),
              'no_live_state_or_windows_modified':True,'api_calls_made_by_audit':0}
    atomic_json(Path('docs/100k-halt-diagnosis.json'),report)
    print(json.dumps({k:v for k,v in report.items() if k not in {'failed_calls','valid_pending_replay_ids'}},indent=2),flush=True)
    return report


if __name__=='__main__':
    build()
