"""Drain eight workers without cancelling admitted requests or their repairs.

Separate admission signal from Calls.stop (which aborts retries on hard failures).
One run ID and cap survive a voluntary pause. This module never creates a client.
"""
import threading
import time
import uuid
from pathlib import Path

from pipeline.deterministic import run_deterministic
from pipeline.failure_policy import FailureWindow, failure_window
from pipeline.prepare import atomic_json
from pipeline.schema import configuration
from pipeline.spend import SpendStop


def window_dump(window):
    with window.lock:
        return {'outcomes':list(window.outcomes),'seen':sorted(window.seen)}


def window_restore(window, saved):
    if saved:
        window.outcomes.extend(saved['outcomes'])
        window.seen.update(saved['seen'])
    return window


def run_segment(state, calls, config, output: Path, resume=False, poll_seconds=.05, recovery=False):
    """Run a prepared store; caller supplies mocked or explicitly authorized Calls.

    Refuse stale stop files, outstanding leases/reservations and cap-hit resumes.
    A receipt is committed only after every executor has drained.
    """
    if config['controls']['max_workers'] != 8:
        raise ValueError('Graceful production wrapper requires eight workers')
    if configuration(config, calls.simulated) != state.label_config:
        raise ValueError('Wrapper configuration hash differs')
    output.mkdir(parents=True, exist_ok=True)
    stop_file = output/'stop.request'
    saved = state.artifact('graceful-invocation')
    identity = {'run_id':calls.run_id,'label_config':state.label_config,
                'cap':config['controls']['run_api_cap_usd'],
                'fallback_fraction':config['controls']['fallback_fraction']}
    if stop_file.exists():
        raise ValueError('Unacknowledged stop.request exists; inspect the drained receipt first')
    if state.leased_count() or calls.ledger.totals()['reserved_nanodollars']:
        raise ValueError('Outstanding leases/reservations require recovery')
    if resume:
        if not saved or any(saved[k] != v for k,v in identity.items()):
            raise ValueError('Resume must preserve invocation ID, cap, hash and fallback fraction')
        allowed = saved['status']=='stopped_user' or (recovery and saved['status']=='recovery_ready')
        if not allowed or calls.ledger.run_stop(calls.run_id):
            raise ValueError('Only a drained voluntary pause can resume without a new gate')
    elif saved:
        raise ValueError('Invocation exists; use explicit resume')
    calls.phase = 'resume' if resume else 'initial'
    prior = saved or {}
    state.classification_window = window_restore(failure_window(config),prior.get('classification_window'))
    state.failure_window = window_restore(failure_window(config),prior.get('terminal_window'))
    calls.connection_window = window_restore(FailureWindow(label='Unknown-charge/connection failures'),prior.get('connection_window'))
    admission_stop, done = threading.Event(), threading.Event()

    def watch():
        while not done.is_set():
            if stop_file.exists():
                admission_stop.set()
            done.wait(poll_seconds)

    receipt = {**identity,'status':'running','segment_id':str(uuid.uuid4()),'phase':calls.phase,
               'started_epoch':time.time()}
    state.artifact('graceful-invocation',receipt)
    watcher = threading.Thread(target=watch,daemon=True)
    watcher.start()
    started = time.perf_counter()
    error = None
    try:
        run_deterministic(state,calls,config,admission_stop=admission_stop)
        receipt['status'] = 'stopped_user' if admission_stop.is_set() else 'completed'
    except SpendStop as exc:
        receipt.update(status='stopped_cap' if calls.ledger.run_stop(calls.run_id) else 'stopped_integrity',error=str(exc))
    except BaseException as exc:  # noqa: BLE001 -- persist receipt, then re-raise below
        error = exc
        receipt.update(status='failed',error=type(exc).__name__+': '+str(exc))
    finally:
        done.set()
        watcher.join()
        receipt.update(wall_seconds=time.perf_counter()-started,counts=state.counts(),
                       pending_leases=state.leased_count(),ledger=calls.ledger.totals(),
                       classification_window=window_dump(state.classification_window),
                       terminal_window=window_dump(state.failure_window),
                       connection_window=window_dump(calls.connection_window))
        with calls.ledger.connect() as db:
            receipt['invocation_spent_nanodollars'] = db.execute('SELECT COALESCE(SUM(spent),0) FROM reservations WHERE run_id=?',(calls.run_id,)).fetchone()[0]
        receipt['drained'] = not receipt['pending_leases'] and not receipt['ledger']['reserved_nanodollars']
        if not receipt['drained']:
            receipt['status'] = 'recovery_required'
        state.artifact('graceful-invocation',receipt)
        atomic_json(output/('segment-'+receipt['segment_id']+'.json'),receipt)
        atomic_json(output/'stop-receipt.json',receipt)
        # Acknowledge only after durable drained evidence. Never erase a hard stop.
        if receipt['status']=='stopped_user' and receipt['drained'] and stop_file.exists():
            stop_file.rename(output/('stop-ack-'+receipt['segment_id']+'.request'))
    if error:
        raise error
    return receipt


def saved_run_id(state):
    saved = state.artifact('graceful-invocation')
    if not saved:
        raise ValueError('No saved invocation to resume')
    return saved['run_id']


def run_plan(plan_path, confirmed=False, resume=False):
    """Paid entry point; draft plans and calls without confirmation stay offline."""
    import json
    import tomllib

    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    if not confirmed:
        return {'status':'offline only; no dispatch','plan':str(plan_path),
                'execution_approved':plan.get('execution_approved',False)}
    if plan.get('approval_receipt'):
        from pipeline.production import check_authorization
        check_authorization(plan_path,plan,resume)
    elif not plan.get('execution_approved') or not plan.get('preflight_verified'):
        raise ValueError('Draft plan cannot execute; approved prepared-state plan and preflight required')
    if plan.get('workers') != 8:
        raise ValueError('Approved worker count must be eight')
    from pipeline.calls import Calls
    from pipeline.enrich import export_state
    from pipeline.providers import HTTPTransport, keys_from_env
    from pipeline.spend import Ledger
    from pipeline.state import State

    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    config['controls'].update(max_workers=8,run_api_cap_usd=plan['invocation_cap_usd'],
                              fallback_fraction=plan['proposed_fallback_fraction'])
    if configuration(config)!=plan['label_config']:
        raise ValueError('Approved plan hash changed')
    output = Path(plan['output'])
    if not (output/'state.sqlite3').exists():
        raise ValueError('Prepared scope store required; never dispatch on an empty state')
    state = State(output/'state.sqlite3',plan['label_config'],require_reasons=True)
    ledger = Ledger(Path(config['controls']['ledger_path']),config['controls']['project_api_cap_usd'])
    run_id = saved_run_id(state) if resume else str(uuid.uuid4())
    transport = HTTPTransport(keys_from_env(Path('.env')),config['controls']['request_timeout_seconds'],
                              connect_timeout=config['controls']['connect_timeout_seconds'])
    calls = Calls(state,ledger,transport,config,run_id,'resume' if resume else 'initial')
    try:
        return run_segment(state,calls,config,output,resume)
    finally:
        transport.close()
        export_state(state,output,False,ledger)
