"""Persist all Jev scores, quota selection and batches before Luna dispatch."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

from pipeline.batching import pack, resolve_luna
from pipeline.calls import InvalidOutput
from pipeline.classify import deterministic_entities, jev_payload, parse_jev
from pipeline.failure_policy import failure_window
from pipeline.providers import ProviderError
from pipeline.schema import digest, record_schema
from pipeline.spend import fallback_quota
from pipeline.state import ConfigMismatch

POLICY = 'lowest-confidence-v1'


def ranking_scores(response):
    answers = response['answers']
    considered = [answers[name] for name in ('topic','intent','severity','sentiment')]
    confidence = min(answer['confidence'] for answer in considered)
    choices = [sorted(answer['probabilities'].values(),reverse=True) for answer in considered if answer['type']=='choice']
    return {'confidence':confidence,'margin':min(values[0]-values[1] for values in choices)}


def select_fallback(candidates, quota):
    return [item['key'] for item in sorted(candidates,key=lambda item:
            (item['confidence'],item['margin'],item['text_hash'],item['origin_id']))[:quota]]


def tranche(state, config):
    """Freeze pending work at start; finish it before accepting a new extension."""
    active = state.artifact('active-routing-tranche')
    with state.connect() as db:
        pending = {row[0] for row in db.execute("SELECT key FROM work WHERE status='pending'")}
        if active and pending & set(active['keys']):
            if pending - set(active['keys']):
                raise ConfigMismatch('Finish the persisted routing tranche before extending input')
            if active['fallback_fraction'] != config['controls']['fallback_fraction']:
                raise ConfigMismatch('Fallback cap changed during a frozen routing tranche')
            return active
        if not pending:
            return None
        # Stable source IDs for fresh jobs, independent of CSV ingestion order.
        db.execute('BEGIN IMMEDIATE')
        for key in sorted(pending):
            row = db.execute('SELECT origin_id FROM work WHERE key=?',(key,)).fetchone()
            if not db.execute('SELECT 1 FROM call_reviews WHERE review_id=?',(row[0],)).fetchone():
                origin = db.execute('SELECT MIN(review_id) FROM reviews WHERE work_key=?',(key,)).fetchone()[0]
                db.execute('UPDATE work SET origin_id=? WHERE key=?',(origin,key))
    result = {'keys':sorted(pending),'label_config':state.label_config,'policy':POLICY,
              'fallback_fraction':config['controls']['fallback_fraction']}
    result['id'] = digest(result)
    state.artifact('active-routing-tranche',result)
    state.artifact('routing-tranche:'+result['id'],result)
    return result


def persist_selection(state, config, frozen):
    artifact_key = 'routing-selection:'+frozen['id']
    saved = state.artifact(artifact_key)
    if saved is not None:
        if saved['label_config'] != state.label_config or digest({key:value for key,value in saved.items() if key!='selection_sha256'}) != saved['selection_sha256']:
            raise ConfigMismatch('Persisted routing selection identity was altered')
        return saved
    candidates, items, labels = [], [], {}
    with state.connect() as db:
        rows = [db.execute('SELECT * FROM work WHERE key=?',(key,)).fetchone() for key in frozen['keys']]
        for row in rows:
            if row['status'] != 'pending':
                continue
            values = state.stage_result(row['key'],'jev')
            if values is None:
                raise ValueError('Cannot select fallback before all Jev items finalize')
            events = [event for event in state.events_for(row['origin_id'],'jev') if event['outcome']=='succeeded']
            if not events:
                raise ValueError('Missing Jev response provenance for routing')
            scores = ranking_scores(events[-1]['response'])
            source = json.loads(db.execute('SELECT source FROM reviews WHERE review_id=?',(row['origin_id'],)).fetchone()[0])
            item = {'key':row['key'],'source':source}
            items.append(item)
            labels[source['review_id']] = values
            if values['low_confidence']:
                candidates.append({'key':row['key'],'origin_id':row['origin_id'],**scores,
                                   'text_hash':hashlib.sha256(row['text'].encode('utf-8')).hexdigest()})
    quota = fallback_quota(len(frozen['keys']),frozen['fallback_fraction'])
    selected = select_fallback(candidates,quota)
    selected_set = set(selected)
    by_key = {item['key']:item for item in items}
    fallbacks = [by_key[key] for key in selected]
    extracts = [item for item in items if item['key'] not in selected_set
                and len(item['source']['review_text']) > config['enrichment']['short_review_chars']]
    local = [item for item in items if item['key'] not in selected_set
             and len(item['source']['review_text']) <= config['enrichment']['short_review_chars']]
    batches = []
    for mode, members in (('extract',extracts),('fallback',fallbacks)):
        for batch in pack(members,labels,config,mode=='extract'):
            batches.append({'mode':mode,'keys':[item['key'] for item in batch]})
    size = config['enrichment']['batch_size']
    for start in range(0,len(local),size):
        batches.append({'mode':'local','keys':[item['key'] for item in local[start:start+size]]})
    result = {'tranche_id':frozen['id'],'label_config':state.label_config,'policy':POLICY,
              'quota':quota,'eligible_count':len(candidates),'selected_keys':selected,
              'ranked_candidates':sorted(candidates,key=lambda item:(item['confidence'],item['margin'],item['text_hash'],item['origin_id'])),
              'batches':batches}
    result['selection_sha256'] = digest(result)
    state.artifact(artifact_key,result)  # durable complete selection before any Luna dispatch
    return result


def run_deterministic(state, calls, config, stop_after=None, admission_stop=None):
    if config['enrichment'].get('fallback_selection_policy') != POLICY:
        raise ValueError('Unsupported deterministic routing policy')
    if record_schema(config)=='record-v2':
        state.require_reasons = True
        with state.connect() as db:
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('require_reasons','true')")
    frozen = tranche(state,config)
    if frozen is None:
        return None
    workers = config['controls']['max_workers']
    if stop_after is not None and (workers != 1 or stop_after < 1):
        raise ValueError('Saved completion interruption requires one worker and a positive count')
    controls, routing = config['controls'], config['enrichment']
    stage_monitor = getattr(state, 'classification_window', None) or failure_window(config)
    state.classification_window = stage_monitor

    def paused():
        return admission_stop is not None and admission_stop.is_set()

    def classify_worker():
        while not calls.stop.is_set() and not paused():
            item = state.claim(controls['lease_seconds'],'jev')
            if item is None:
                return
            source = item['source']
            try:
                values = calls.invoke('typesafe',jev_payload(source['review_text'],config),[source['review_id']],'jev',
                                      lambda reply:parse_jev(reply,routing['confidence_threshold'],routing['probability_margin_threshold'],require_auxiliary=True))
                state.stage_result(item['key'],'jev',values)
                state.release(item)
                stage_monitor.record(item['key'],False)
            except InvalidOutput:
                state.quarantine(item,'invalid_model_output_after_retry')
                stage_monitor.record(item['key'],True)
            except ProviderError as exc:
                if exc.transient and not exc.unknown_charge:
                    state.quarantine(item,'api_retries_exhausted')
                    stage_monitor.record(item['key'],True)
                else:
                    if not exc.unknown_charge:
                        state.release(item)
                    raise
            except BaseException:
                state.release(item)
                raise

    def guarded_classify():
        try:
            classify_worker()
        except BaseException:
            calls.stop.set()
            raise

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(guarded_classify) for _ in range(workers)]
        for future in futures:
            future.result()
    if paused():
        return state.artifact('routing-selection:'+frozen['id'])
    selection = persist_selection(state,config,frozen)
    scope = str(state.path.resolve())+':'+frozen['id']
    for key in selection['selected_keys']:
        if not calls.ledger.allow_fallback(key,scope,selection['quota']):
            raise ConfigMismatch('Persisted fallback selection cannot fit its ledger quota')

    def finish(batch):
        if calls.stop.is_set() or paused():
            return
        items = state.claim_keys(batch['keys'],controls['lease_seconds'])
        labels = {item['source']['review_id']:state.stage_result(item['key'],'jev') for item in items}
        try:
            if batch['mode']=='local':
                for item in items:
                    source, values = item['source'], labels[item['source']['review_id']]
                    record = {name:values[name] for name in ('topic','intent','severity','sentiment','needs_review','needs_review_reasons')}
                    record.update(review_id=source['review_id'],source_sha256=source['source_sha256'],status='completed',
                                  label_config=state.label_config,evidence_quote=source['review_text'],
                                  entities=deterministic_entities(source['review_text'],routing['entity_terms']))
                    state.complete(item,record)
            elif items:
                resolve_luna(state,calls,items,labels,config,batch['mode']=='extract')
        except BaseException as exc:
            calls.stop.set()
            if not isinstance(exc,ProviderError) or not exc.unknown_charge:
                for item in items:
                    state.release(item)
            raise
        return len(items)

    if stop_after is not None:
        finalized = 0
        for batch in selection['batches']:
            with state.connect() as db:
                remaining = [key for key in batch['keys'] if db.execute('SELECT status FROM work WHERE key=?',(key,)).fetchone()[0]=='pending']
            selected_batch = {**batch,'keys':remaining[:stop_after-finalized]}
            finalized += finish(selected_batch)
            if finalized >= stop_after:
                break
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(finish,batch) for batch in selection['batches']]
            for future in futures:
                future.result()
    return selection
