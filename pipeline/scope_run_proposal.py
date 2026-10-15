"""Offline production draft using development recommendation, never golden accuracy."""
import csv
import hashlib
import itertools
import json
import shutil
import sqlite3
import tomllib
from contextlib import closing
from pathlib import Path

from pipeline.prepare import atomic_json
from pipeline.schema import configuration


def build():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    development = json.loads(Path('docs/fallback-options-development.json').read_text(encoding='utf-8'))
    accounting = json.loads(Path('docs/pre-100k-accounting-snapshot.json').read_text(encoding='utf-8'))
    proposed = development['recommendation']['fallback_fraction']
    scenario = next(o for o in development['scenarios'] if o['fallback_fraction']==proposed)
    base = Path('artifacts/golden-final/state.sqlite3')
    with Path('artifacts/sampling/permutation.csv').open(encoding='utf-8',newline='') as stream:
        ids = {r['review_id'] for r in itertools.islice(csv.DictReader(stream),100000)}
    with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig',newline='') as stream:
        ids |= {r['review_id'] for r in csv.DictReader(stream)}
    with closing(sqlite3.connect('file:artifacts/ingestion/state.sqlite3?mode=ro',uri=True)) as db:
        scope = {text for rid,text in db.execute('SELECT review_id,review_text FROM reviews') if rid in ids}
    with closing(sqlite3.connect(f'file:{base.as_posix()}?mode=ro',uri=True)) as db:
        done = {text for text, in db.execute("SELECT text FROM work WHERE status='completed'")}
        failed = {text for text, in db.execute("SELECT text FROM work WHERE status='quarantined'")}
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
        leases = db.execute('SELECT COUNT(*) FROM work WHERE lease IS NOT NULL').fetchone()[0]
    pending = len(scope-done-failed)
    if pending!=scenario['future_pending_texts_conditional'] or development['label_config']!=configuration(config):
        raise ValueError('Actual reusable scope/frozen hash differs; recalculate development projection')
    cap = scenario['cap_1_5x_rounded_up_cents_usd'] if proposed!=.1 else 6.80
    jev_expected = development['cost_time_reference']['cost_by_stage_usd']['jev']/scenario['reference_texts']*pending
    result = {'status':'draft only; not executed; fresh approval required',
              'workers':8,'label_config':configuration(config),'proposed_fallback_fraction':proposed,
              'actual_config_fallback_fraction':config['controls']['fallback_fraction'],
              'recommendation_applied':config['controls']['fallback_fraction']==proposed,'hash_changes':False,'golden_accuracy_used_for_routing':False,
              'fallback_20_approval':'Owner approved frozen prompt and 20% for 100k; applied to controls; paid run awaits yes',
              'execution_approved':False,
              'recommendation_frozen_at_utc':development['recommendation_frozen_at_utc'],
              'recommendation_sha256':hashlib.sha256(Path('docs/fallback-options-development.json').read_bytes()).hexdigest(),
              'base_state':str(base),'base_state_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),
              'scope_ids':len(ids),'scope_distinct_texts':len(scope),'reusable_scope_distinct_texts':len(scope&done),
              'retained_terminal_scope_distinct_texts':len(scope&failed),'new_distinct_texts':pending,
              'fallback_slots_upper':int(pending*proposed),'base_cost_usd':scenario['base_cost_usd'],
              'base_hours':scenario['base_hours'],'invocation_cap_usd':cap,
              'cap_applies_across_initial_and_resume':True,
              'project_spent_usd':accounting['ledger_spent_usd'],
              'project_total_at_invocation_cap_usd':accounting['ledger_spent_usd']+cap,
              'project_headroom_after_full_invocation_usd':10-accounting['ledger_spent_usd']-cap,
              'typesafe_balance_user_reported_usd':10.41,
              'typesafe_expected_cost_usd':jev_expected,
              'typesafe_conservative_1_5x_usd':jev_expected*1.5,
              'openai_expected_cost_usd':scenario['base_cost_usd']-jev_expected,
              'openai_conservative_1_5x_usd':(scenario['base_cost_usd']-jev_expected)*1.5,
              'openai_org_limit_usd':20,'openai_october_spend_user_reported_usd':.18,
              'openai_org_remaining_limit_user_reported_usd':19.82,
              'openai_prepaid_credit_user_reported_usd':9.82,
              'openai_effective_available_before_unbilled_usage_usd':9.82,
              'openai_project_logged_cost_usd':accounting['accounted_by_provider_usd']['openai'],
              'preflight_requires_org_dashboard_remaining_and_unbilled_usage_check':True,
              'disk_free_gib':shutil.disk_usage('.').free/2**30,'disk_free_required_gib_assumption':10,
              'base_sqlite_integrity':integrity,'base_pending_leases':leases,
              'local_commit_required_before_start':True,'push':False,
              'runner_status':'8-worker graceful wrapper implemented; prepared scope store, approved execution plan, preflight and local commit still required',
              'recording_stop':'After about five minutes create stop.request; drain and save Jev stages. Before may contain only imported completed rows; wait for completed growth and real paid calls after resume.',
              'recording_proofs':['checkpoint_before.json','checkpoint_after.json','resume-audit.json','raw calls and source_phase-aware grading calls','recording manifest'],
              'after_run':'Propagate exact-text results with direct cache origins; all source IDs retained; nonempty out-of-scope rows quarantined as not_classified_partial_run. Terminal failures keep their actual reasons.',
              'next_gate':'Stop after 100k enrichment and offline cache/export evidence; no downstream paid calls without separate approval.'}
    atomic_json(Path('docs/100k-run-proposal-draft.json'),result)
    print(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    build()
