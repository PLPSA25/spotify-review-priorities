"""Approved capped production verification/business stages, with a human memo gate."""
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import time
import tomllib
import uuid
from contextlib import closing
from pathlib import Path

from pipeline.calls import Calls, InvalidOutput
from pipeline.classify import parse_luna_batch
from pipeline.enrich import write_jsonl
from pipeline.failure_policy import failure_window
from pipeline.graceful import window_dump, window_restore
from pipeline.issue_cohorts_v3 import CROSS_ID, CROSS_NAME, RULE_HASH
from pipeline.labeler import atomic_csv
from pipeline.phase7_work import (
    DISPLAY_NAME,
    OUTPUT,
    agreement,
    group_payloads,
    load_inputs,
    memo_payload,
    parse_group,
    parse_memo,
    read_json,
    write_business,
)
from pipeline.pilot_stages import response_json
from pipeline.prepare import atomic_json, course_helper
from pipeline.providers import HTTPTransport, ProviderError, keys_from_env
from pipeline.schema import canonical, configuration
from pipeline.spend import Ledger
from pipeline.sqlite_read import read_connection
from pipeline.state import State
from pipeline.transfer_verify import diagnostic_payload

STAGE_CAPS = {'verify': 1523886500, 'group-01': 16096000, 'group-02': 16096000, 'memo': 14400000}


class ApprovedTransport:
    """Independent pre-network admission; uses persisted attempts, including retries."""
    def __init__(self, delegate, state, run_id, config, verify_plan, groups, memo=None):
        self.delegate, self.state, self.run_id, self.config = delegate, state, run_id, config
        self.allowed = {}
        ids = verify_plan['sample_ids']
        for n, batch in enumerate(verify_plan['batches']):
            self.allowed[batch['payload_sha256']] = ('verify', ids[n*50:(n+1)*50], batch['input_byte_token_bound'], 10000)
        for rid, item in verify_plan['single_repairs'].items():
            self.allowed[item['payload_sha256']] = ('verify', [rid], item['input_byte_token_bound'], 200)
        for stage, item in groups.items():
            self.allowed[item['payload_sha256']] = (stage, item['ids'], 24000, 2048)
        if memo:
            self.allowed[hashlib.sha256(canonical(memo).encode()).hexdigest()] = ('memo', [], 24000, 1200)

    def request(self, provider, payload):
        fingerprint = hashlib.sha256(canonical(payload).encode()).hexdigest()
        accepted = self.allowed.get(fingerprint)
        # Group/memo semantic repair appends a bounded validation suffix. Match
        # the original immutable payload and still enforce the complete byte bound.
        if accepted is None and '\nVALIDATION_ERROR: ' in payload.get('input', ''):
            original = copy.deepcopy(payload)
            original['input'] = original['input'].split('\nVALIDATION_ERROR: ', 1)[0]
            accepted = self.allowed.get(hashlib.sha256(canonical(original).encode()).hexdigest())
        if provider != 'openai' or not accepted:
            raise ProviderError('Payload is outside approved Phase 7 plan', known_uncharged=True)
        stage, ids, bound, output = accepted
        if payload['model'] != self.config['models']['luna'] or payload.get('service_tier') != 'default' or payload.get('reasoning') != {'effort': 'none'}:
            raise ProviderError('Approved model/settings changed', known_uncharged=True)
        if len(canonical(payload).encode())+self.config['controls']['token_overhead_bound'] > bound or payload['max_output_tokens'] != output:
            raise ProviderError('Approved token envelope exceeded', known_uncharged=True)
        with self.state.connect() as db:
            events = [json.loads(r[0]) for r in db.execute('SELECT event FROM calls ORDER BY rowid')]
        events = [e for e in events if e['run_id'] == self.run_id]
        current = events[-1] if events else None
        if not current or current['stage'] != stage or current['review_ids'] != ids:
            raise ProviderError('Dispatch event differs from approved scope', known_uncharged=True)
        own = [e for e in events if e['stage'] == stage]
        if len(events) > 1522 or sum(e['reservation_nanodollars'] for e in own) > STAGE_CAPS[stage]:
            raise ProviderError('Approved stage/call bound exhausted', known_uncharged=True)
        if stage == 'verify':
            if any(sum(rid in e['review_ids'] for e in own) > 4 for rid in ids):
                raise ProviderError('Four-attempt verifier limit exhausted', known_uncharged=True)
        elif len(own) > 4:
            raise ProviderError('Four-attempt business limit exhausted', known_uncharged=True)
        return self.delegate.request(provider, payload)


def finalize_verifier(batch, send, predictions, terminal, monitor, persist):
    try:
        result = send(batch, False)
    except InvalidOutput as exc:
        result = {'valid': {}, 'errors': dict.fromkeys(batch, str(exc))}
    except ProviderError as exc:
        if not exc.transient:
            raise
        for rid in batch:
            terminal[rid] = {'reason': 'connection_or_api_attempts_exhausted', 'error': str(exc)}
        persist()
        for rid in batch:
            monitor.record(rid, True)
        return
    predictions.update(result['valid'])
    persist()  # every valid sibling survives a monitor stop
    for rid in result['valid']:
        monitor.record(rid, False)
    for rid in result['errors']:
        try:
            repair = send({rid: batch[rid]}, True)
        except InvalidOutput as exc:
            repair = {'valid': {}, 'errors': {rid: str(exc)}}
        except ProviderError as exc:
            if not exc.transient:
                raise
            repair = {'valid': {}, 'errors': {rid: str(exc)}}
        failed = rid not in repair['valid']
        if failed:
            terminal[rid] = {'reason': 'failed_after_permitted_repair', 'error': repair['errors'].get(rid, 'Missing repaired ID')}
        else:
            predictions[rid] = repair['valid'][rid]
        persist()
        monitor.record(rid, failed)


def prepare():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    records, sources, verify, taxonomy, prefix = load_inputs('v3')
    helper = course_helper(Path('data/check_submission.py'))
    frozen_group = read_json(Path('docs/frozen-grouping-v3.json'))
    if frozen_group['rule_hash'] != RULE_HASH or any(helper.sha(Path(f)) != sha for f,sha in frozen_group['file_sha256'].items()):
        raise ValueError('Final grouping rules changed after freeze')
    if configuration(config) != verify['label_config'] or helper.sha(Path(verify['sample_csv'])) != verify['sample_csv_sha256']:
        raise ValueError('Frozen classifier or verifier sample changed')
    for filename, expected in verify['payload_builder_file_sha256'].items():
        if helper.sha(Path(filename)) != expected:
            raise ValueError('Frozen verifier payload builder changed: '+filename)
    groups = group_payloads(config, taxonomy, sources)
    if len(groups) != 2:
        raise ValueError('Expected two approved group requests')
    for n, item in enumerate(verify['batches']):
        batch = [sources[rid] for rid in verify['sample_ids'][n*50:(n+1)*50]]
        if hashlib.sha256(canonical(diagnostic_payload(batch, config)).encode()).hexdigest() != item['payload_sha256']:
            raise ValueError('Verifier payload differs from approved byte-bound proposal')
    needed = set(verify['sample_ids']) | {rid for group in groups.values() for rid in group['ids']}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_csv(OUTPUT/'source-registry.csv', list(helper.FIELDS), [{f: sources[rid][f] for f in helper.FIELDS} for rid in sorted(needed)])
    state = State(OUTPUT/'state.sqlite3', configuration(config))
    state.ingest(OUTPUT/'source-registry.csv', Path('data/manifest.json'))
    # Pin the already observed response model, not a newly guessed alias/version.
    with closing(read_connection(Path('artifacts/scope-100k/state.sqlite3'))) as db:
        observed = db.execute("SELECT value FROM metadata WHERE key='openai_returned_model'").fetchone()[0]
    state.observed_model('openai', observed)
    receipt = state.artifact('phase7-invocation')
    if receipt is None:
        receipt = {'run_id': str(uuid.uuid4()), 'status': 'prepared', 'cap_usd': 1.58,
                   'label_config': state.label_config, 'source_gzip_sha256': {str(p): helper.sha(p) for p in Path('grading').glob('*.gz')}}
        state.artifact('phase7-invocation', receipt)
    if receipt['label_config'] != configuration(config) or receipt['cap_usd'] != 1.58:
        raise ValueError('Invocation identity changed')
    if receipt['status'] == 'prepared':
        receipt.update(grouping_rule_hash=RULE_HASH, v3_final=True)
        state.artifact('phase7-invocation', receipt)
    return config, records, sources, verify, taxonomy, prefix, groups, state, receipt


def export_calls(state):
    with state.connect() as db:
        write_jsonl(OUTPUT/'calls.jsonl', (json.loads(r[0]) for r in db.execute('SELECT event FROM calls ORDER BY rowid')))


def staging_check(state):
    """Check current business work without changing tracked compressed exports."""
    folder = OUTPUT/'grading-check'
    folder.mkdir(exist_ok=True)
    for name in ('run.json', 'ingestion.json', 'checkpoint_before.json', 'checkpoint_after.json', 'checkpoint_before.provenance.json'):
        shutil.copyfile(Path('grading')/name, folder/name)
    # A hard link preserves the exact tracked bytes and avoids a second 52MB copy.
    records = folder/'records.jsonl.gz'
    if not records.exists():
        records.hardlink_to(Path('grading/records.jsonl.gz').resolve())
    for name in ('membership.csv', 'ranking.csv'):
        shutil.copyfile(OUTPUT/name, folder/name)
    shutil.copyfile(OUTPUT/'grading_claims.csv', folder/'claims.csv')

    def events():
        with gzip.open('grading/calls.jsonl.gz', 'rt', encoding='utf-8') as stream:
            for line in stream:
                yield json.loads(line)
        with state.connect() as db:
            for raw, in db.execute('SELECT event FROM calls ORDER BY rowid'):
                yield json.loads(raw)

    # Working staging only. Committed grading/*.gz remain byte-for-byte unchanged.
    import gzip
    write_jsonl(folder/'calls.jsonl', events())
    subprocess.run([str(Path('.venv/Scripts/python.exe')), 'data/check_submission.py', 'check',
                    '--reference', 'local-reference.json', '--submission', str(folder),
                    '--out', str(OUTPUT/'self-check.json')], check=True)
    return read_json(OUTPUT/'self-check.json')


def run(confirmed=False, memo=False, spotcheck_reviewed=False):
    review_gate = Path('docs/phase7-review-gate.json')
    if confirmed and review_gate.exists() and read_json(review_gate)['status'] == 'hold_all_paid_stages':
        raise ValueError('Owner requires offline v2 cohort review before verifier, group or memo calls')
    config, records, sources, verify, _taxonomy, prefix, groups, state, receipt = prepare()
    print(json.dumps({'mode': 'approved paid stages' if confirmed else 'offline preflight', 'run_id': receipt['run_id'],
                      'cap_usd': 1.58, 'initial_verify_calls': 10, 'group_calls': 2,
                      'group_input_byte_bounds': {k: len(canonical(v['payload']).encode())+2048 for k,v in groups.items()},
                      'v3_rules_frozen': True, 'stop_after_memo_draft': True}), flush=True)
    if not confirmed:
        return
    final_authorized = review_gate.exists() and read_json(review_gate)['status'] == 'approved_v3_through_memo_draft'
    if (not memo and receipt['status'] != 'prepared') or (memo and (receipt['status'] not in {'ready_for_memo_draft', 'awaiting_spotcheck_review'} or not (spotcheck_reviewed or final_authorized))):
        raise ValueError('No automatic stage rerun or memo before explicit owner review')
    keys = keys_from_env(Path('.env'))
    config['controls']['run_api_cap_usd'] = 1.58
    ledger = Ledger(Path(config['controls']['ledger_path']), config['controls']['project_api_cap_usd'])
    if ledger.run_stop(receipt['run_id']) or ledger.totals()['reserved_nanodollars']:
        raise ValueError('Reservation or cap latch requires a recovery gate')
    transport = HTTPTransport(keys, config['controls']['request_timeout_seconds'], connect_timeout=config['controls']['connect_timeout_seconds'])
    business = None
    names = read_json(OUTPUT/'group-names.json') if memo else {}
    memo_pack = None
    if memo:
        business = write_business(records, sources, prefix)
        memo_pack, specific, claim_ids = memo_payload(config, business, names)
    approved = ApprovedTransport(transport, state, receipt['run_id'], config, verify, groups, memo_pack)
    calls = Calls(state, ledger, approved, config, receipt['run_id'], 'initial')
    calls.max_calls = 1522
    calls.connection_window = window_restore(failure_window(config), receipt.get('connection_window'))
    started = time.perf_counter()
    receipt['status'] = 'running_memo' if memo else 'running_verifier'
    state.artifact('phase7-invocation', receipt)
    try:
        if not memo:
            predictions, terminal = {}, {}
            monitor = failure_window(config)

            def persist():
                atomic_json(OUTPUT/'verifier.json', {'predictions': predictions, 'terminal_failures': terminal,
                            'processed': len(predictions)+len(terminal), 'sample_size': 500})

            def send(batch, repair):
                return calls.invoke('openai', diagnostic_payload(list(batch.values()), config, repair), list(batch), 'verify',
                                    lambda reply: parse_luna_batch(reply, batch, {rid: {} for rid in batch}, False,
                                    state.label_config, verifier_diagnostics=True, require_reasons=True),
                                    role='verify', prompt_version='blinded-transfer-diagnostics-v1',
                                    schema_version='verify-production-final-v1', repair_output=False)

            for start in range(0, 500, 50):
                batch = {rid: sources[rid] for rid in verify['sample_ids'][start:start+50]}
                finalize_verifier(batch, send, predictions, terminal, monitor, persist)
                print(json.dumps({'stage': 'verify', 'valid': len(predictions), 'terminal': len(terminal), 'sample': 500}), flush=True)
            with closing(read_connection(Path('artifacts/scope-100k/state.sqlite3'))) as db:
                fallback = set()
                for raw, in db.execute("SELECT event FROM calls"):
                    event = json.loads(raw)
                    if event['stage'] == 'fallback':
                        fallback.update(event.get('valid_review_ids', event['review_ids'] if event['outcome']=='succeeded' else []))
            report = agreement(records, predictions, fallback)
            report.update(terminal_verifier_items=len(terminal), sampled=500)
            atomic_json(OUTPUT/'verifier-agreement.json', report)
            receipt['status'] = 'running_groups'
            state.artifact('phase7-invocation', receipt)
            outputs = {}
            for stage, pack in groups.items():
                result = calls.invoke('openai', pack['payload'], pack['ids'], stage,
                                      lambda reply, expected=pack['issue_ids']: parse_group(response_json(reply), expected),
                                      role='group', prompt_version='production-cohort-names-v1', schema_version='issue-names-v1')
                outputs[stage] = result
                names.update({r['issue_id']: r['name'] for r in result['issues']})
                atomic_json(OUTPUT/'group-outputs.json', outputs)
                atomic_json(OUTPUT/'group-names.json', names)
                print(json.dumps({'stage': stage, 'named_issues': len(result['issues'])}), flush=True)
            # Owner-directed title supported by the separate five-row spot-check;
            # raw model names remain preserved in group-outputs and call responses.
            names['billing--premium-upgrade-mentions'] = DISPLAY_NAME
            names['other--unspecified'] = 'General dissatisfaction — no stated cause'
            names[CROSS_ID] = CROSS_NAME
            atomic_json(OUTPUT/'group-names.json', names)
            business = write_business(records, sources, prefix)
            receipt['status'] = 'ready_for_memo_draft'
        else:
            result = calls.invoke('openai', memo_pack, [], 'memo', lambda reply: parse_memo(response_json(reply), specific, claim_ids),
                                  role='memo', prompt_version='production-memo-draft-v1', schema_version='memo-draft-v1')
            atomic_json(OUTPUT/'memo-draft.json', result)
            render_memo(result, business, names)
            receipt['status'] = 'memo_draft_awaiting_owner_review'
        export_calls(state)
        checker = staging_check(state)
        receipt['checker_flags'] = checker['issue_counts']
    except BaseException as exc:
        receipt.update(status='failed', error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        transport.close()
        receipt['last_segment_seconds'] = time.perf_counter()-started
        receipt['connection_window'] = window_dump(calls.connection_window)
        receipt['ledger'] = ledger.totals()
        with ledger.connect() as db:
            receipt['invocation_spent_usd'] = db.execute('SELECT COALESCE(SUM(spent),0) FROM reservations WHERE run_id=?', (receipt['run_id'],)).fetchone()[0]/1e9
        state.artifact('phase7-invocation', receipt)
        export_calls(state)
        atomic_json(OUTPUT/'receipt.json', receipt)
        print(json.dumps({k: receipt[k] for k in ('status', 'invocation_spent_usd', 'last_segment_seconds', 'ledger')}), flush=True)


def render_memo(result, business, names):
    _, _, claims = business
    by_id = {r['claim_id']: r for r in claims}
    numerical = ['scope:completed_rows', 'scope:nonempty_rows', 'scope:coverage_percent_rounded',
                 'scope:complaint_rows', 'scope:unspecified_complaint_rows', 'scope:unspecified_percent_rounded',
                 'other--unspecified:rank', 'other--unspecified:severity_sum']
    specific = result['recommended_issue_id']
    numerical += [specific+':rank', specific+':complaint_count', specific+':severity_sum', 'sample:'+specific+':rank',
                  'sample:'+specific+':complaint_count', 'sample:'+specific+':severity_sum']
    lines = ['# Memo draft — owner review required', '',
             ('Other—unspecified is the first-ranked bucket under the contract severity-sum rule: '
             'general dissatisfaction with no stated cause.'), '',
             result['top_bucket_explanation'].replace('unclassified complaint', 'complaint with an unspecified cause'), '',
             'Recommended specific issue: '+names[specific]+'.', '', result['recommendation'], '',
             result['random_prefix_comparison'], '', result['limitations'], '', 'Alternatives:',
             *['- '+s for s in result['alternatives']], '', '## Numerical evidence (every value from claims.csv)', '']
    def cited(cid):
        return str(by_id[cid]['value'])+' [`'+cid+'`]'
    lines += [
        'Completed coverage is '+cited('scope:completed_rows')+' of '+cited('scope:nonempty_rows')+
        ' nonempty rows, approximately '+cited('scope:coverage_percent_rounded')+'%.', '',
        'Unspecified cohorts contain '+cited('scope:unspecified_complaint_rows')+' of '+
        cited('scope:complaint_rows')+' complaint/cancellation rows, approximately '+
        cited('scope:unspecified_percent_rounded')+'%.', '',
        'The recommended issue ranks '+cited(specific+':rank')+' in the propagated baseline ('+
        cited(specific+':complaint_count')+' members; severity_sum '+cited(specific+':severity_sum')+
        ') and '+cited('sample:'+specific+':rank')+' in the random-prefix-only view ('+
        cited('sample:'+specific+':complaint_count')+' members; severity_sum '+cited('sample:'+specific+':severity_sum')+').', '',
        ('The propagated baseline weights repeated exact texts by every original row. The random-prefix-only view '
        'restricts membership to the seeded random prefix, reducing the additional weighting introduced by '
        'out-of-prefix cache propagation. Neither view establishes a causal Premium restriction for every '
        'inferred lexical match; the fresh sample includes station repetition with no shuffle, an ambiguous fit.'), '',
    ]
    for cid in numerical:
        row = by_id[cid]
        lines.append(f"- {row['metric']}: **{row['value']}** [`{cid}`; scope `{row['scope']}`].")
    lines += ['', ('The top bucket is general dissatisfaction with no stated cause; its formal rank is retained. '
              'The recommended intervention addresses the top specifically identified actionable cohort. '
              'The completion/unspecified percentages above are rounded from the full claims file.'), '',
              ('All numeric values above come from `artifacts/phase7/claims.csv`, copied for review as '
              '[claims.csv](phase7/claims.csv). The grading adapter projects '
              'only the four baseline issue metrics accepted by the supplied checker. This remains a draft, not final submission.')]
    Path('docs/phase7-memo-draft.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-spend', action='store_true')
    parser.add_argument('--memo', action='store_true')
    parser.add_argument('--spotcheck-reviewed', action='store_true')
    arguments = parser.parse_args()
    run(arguments.confirm_spend, arguments.memo, arguments.spotcheck_reviewed)
