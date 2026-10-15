"""Golden prediction cost gate and approved dispatch; never reads human labels."""
import hashlib
import json
import math
import sqlite3
import time
import tomllib
import uuid
from contextlib import closing
from pathlib import Path

from pipeline.analysis_run import prepare_extension
from pipeline.calls import Calls
from pipeline.checkpoint import BoundedTransport
from pipeline.classify import jev_payload, luna_payload
from pipeline.deterministic import run_deterministic
from pipeline.enrich import export_state, write_jsonl
from pipeline.failure_policy import failure_window
from pipeline.prepare import atomic_json, course_helper
from pipeline.providers import HTTPTransport, keys_from_env
from pipeline.schema import canonical, configuration
from pipeline.spend import Ledger, token_cost

BASE = Path('artifacts/analysis-10000-final/state.sqlite3')
SOURCE = Path('data/golden_50_to_label.csv')
OUTPUT = Path('artifacts/golden-final')
PLAN = Path('docs/golden-final-proposal.json')


def build_plan(save=True):
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    label_config = configuration(config)
    frozen = json.loads(Path('docs/frozen-label-config.json').read_text(encoding='utf-8'))
    if frozen['label_config'] != label_config:
        raise ValueError('Final frozen hash changed')
    helper = course_helper(Path('data/check_submission.py'))
    golden = list(helper.csv_rows(SOURCE))
    if len(golden)!=50 or len({r['review_id'] for r in golden})!=50:
        raise ValueError('Expected original 50 golden IDs')
    with closing(sqlite3.connect(f'file:{BASE.as_posix()}?mode=ro',uri=True)) as db:
        if db.execute("SELECT value FROM metadata WHERE key='label_config'").fetchone()[0] != label_config:
            raise ValueError('Reusable store hash differs')
        done = {text for text, in db.execute("SELECT text FROM work WHERE status='completed'")}
        terminal = {text for text, in db.execute("SELECT text FROM work WHERE status='quarantined'")}
    if any(row['review_text'] in terminal for row in golden):
        raise ValueError('Golden text has retained terminal status; explicit handling required')
    pending = {}
    for row in sorted(golden,key=lambda r:r['review_id']):
        if row['review_text'] not in done:
            source = {field:row[field] for field in helper.FIELDS}
            source['source_sha256'] = helper.row_sha(source)
            pending.setdefault(row['review_text'],source)
    attempts = config['controls']['per_item_call_limit']
    quota = math.floor(len(pending)*config['controls']['fallback_fraction'])
    long = sum(len(text)>config['enrichment']['short_review_chars'] for text in pending)
    luna_ids = min(len(pending),long+quota)
    rates = dict(config['planning_rates'])
    rates['luna_input_per_million'] = max(rates['luna_input_per_million'],rates['luna_cache_write_per_million'])
    jev_bound, luna_bounds = 0, []
    for source in pending.values():
        tokens = len(canonical(jev_payload(source['review_text'],config)).encode())+config['controls']['token_overhead_bound']+1024
        jev_bound += attempts*token_cost(tokens,0,rates,'typesafe')
        tokens = len(canonical(luna_payload(source,{},config,False)).encode())+config['controls']['token_overhead_bound']+1024
        luna_bounds.append(attempts*token_cost(tokens,200,rates,'openai'))
    luna_bound = sum(sorted(luna_bounds,reverse=True)[:luna_ids])
    total = jev_bound+luna_bound
    plan = {'status':'proposal only; awaiting yes; human labels not read',
            'label_config':label_config,'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'base_state':str(BASE),'base_state_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
            'output':str(OUTPUT),'golden_ids':50,'distinct_golden_texts':len({r['review_text'] for r in golden}),
            'reusable_golden_ids':sum(r['review_text'] in done for r in golden),
            'new_golden_ids':sum(r['review_text'] not in done for r in golden),
            'new_distinct_texts':len(pending),'initial_jev_calls':len(pending),
            'long_new_texts':long,'fallback_quota':quota,'luna_enrichment_ids_upper':luna_ids,
            'per_item_call_limit':attempts,'connection_max_attempts':config['controls']['connection_max_attempts'],
            'maximum_calls':attempts*(len(pending)+luna_ids),
            'cost_bounds_nanodollars':{'jev':jev_bound,'luna_enrich':luna_bound,'verify':0},
            'worst_case_nanodollars':total,'worst_case_usd':total/1e9,
            'invocation_cap_usd':str(total/1e9),'workers':8,'planning_rates':config['planning_rates'],
            'exclusions':['No new verifier/group/memo calls','No human labels in model inputs','Entities not evaluated'],
            'evaluation':'After predictions freeze, evaluation code only compares human labels. Missing/terminal predictions count as wrong in denominator50. No changes to prompts, thresholds or routing from golden results.'}
    if save:
        atomic_json(PLAN,plan)
    return plan


def run(approved_path, confirmed=False):
    if not confirmed:
        raise ValueError('Explicit yes and --confirm-spend required')
    reviewed = json.loads(approved_path.read_text(encoding='utf-8'))
    current = build_plan(save=False)
    if current != reviewed:
        raise ValueError('Reviewed golden proposal changed')
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    ledger = Ledger(Path(config['controls']['ledger_path']),10)
    totals = ledger.totals()
    if sum(totals.values())+reviewed['worst_case_nanodollars']>ledger.cap:
        raise ValueError('Insufficient project headroom')
    keys = keys_from_env(Path('.env'))
    state = prepare_extension(BASE,OUTPUT,current['label_config'],SOURCE,Path('data/manifest.json'))
    with state.connect() as db:
        sources = {r['review_id']:json.loads(r['source']) for r in db.execute('SELECT * FROM reviews')}
    config['controls'].update(max_workers=8,run_api_cap_usd=current['invocation_cap_usd'])
    state.failure_window = failure_window(config)
    http = HTTPTransport(keys,config['controls']['request_timeout_seconds'],connect_timeout=config['controls']['connect_timeout_seconds'])
    bounded = BoundedTransport(http,config,current,sources)
    calls = Calls(state,ledger,bounded,config,str(uuid.uuid4()),'initial')
    measured = {'status':'running','run_id':calls.run_id,'label_config':state.label_config,'workers':8}
    started = time.perf_counter()
    try:
        selection = run_deterministic(state,calls,config)
        atomic_json(OUTPUT/'routing-selection.json',selection)
        measured['status'] = 'finished'
    finally:
        http.close()
        measured.update(wall_seconds=time.perf_counter()-started,counts=state.counts(),ledger=ledger.totals())
        atomic_json(OUTPUT/'measurements.json',measured)
        export_state(state,OUTPUT,False,ledger)
        helper = course_helper(Path('data/check_submission.py'))
        ids = {r['review_id'] for r in helper.csv_rows(SOURCE)}
        with state.connect() as db:
            predictions = [json.loads(row[0]) for row in db.execute("SELECT result FROM reviews WHERE status='completed' AND review_id IN ("+','.join('?' for _ in ids)+')',tuple(sorted(ids)))]
        write_jsonl(OUTPUT/'golden-predictions.jsonl',predictions)
    return measured
