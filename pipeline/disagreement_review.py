"""Offline, resumable human adjudication of development verifier disagreements."""
import csv
import hashlib
import json
import os
import sys
import tomllib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pipeline.classify import parse_jev
from pipeline.prepare import atomic_json
from pipeline.scaling_report import load_state
from pipeline.schema import configuration, digest

FIELDS = ('topic','intent','severity','sentiment_sign','needs_review')
VERDICTS = ('jev_right','verifier_right','both_wrong','unclear')
DEFAULT = Path('evals/verifier-human-review.json')


def value(labels, field):
    number = labels['sentiment'] if field=='sentiment_sign' else None
    return ('negative' if number<0 else 'positive' if number>0 else 'neutral') if field=='sentiment_sign' else labels[field]


def select(candidates, limit=20):
    if type(limit) is not int or not 1<=limit<=20:
        raise ValueError('Review limit must be 1–20')
    selected, used_texts = [], set()
    pools = {field:sorted([row for row in candidates if field in row['disagreements']],
                         key=lambda row:hashlib.sha256(('human-review-v1:'+field+':'+row['review_id']).encode()).hexdigest())
             for field in FIELDS}
    # One field per case, round-robin strata, no duplicate review text.
    while len(selected)<limit:
        added = False
        for field in FIELDS:
            eligible = next((row for row in pools[field] if row['review_text'] not in used_texts),None)
            if eligible is None:
                continue
            case = {**eligible,'target_field':field}
            case['case_id'] = digest({'review_id':case['review_id'],'field':field,'text':case['review_text']})
            selected.append(case)
            used_texts.add(case['review_text'])
            added = True
            if len(selected)==limit:
                break
        if not added:
            break
    return selected


def prepare(output=DEFAULT, limit=20):
    if output.exists():
        saved = json.loads(output.read_text(encoding='utf-8'))
        if saved.get('version')!='verifier-human-review-v1':
            raise ValueError('Unrecognized review session')
        return saved
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig',newline='') as stream:
        golden = list(csv.DictReader(stream))
    golden_ids = {row['review_id'] for row in golden}
    golden_texts = {row['review_text'] for row in golden}
    verifier_path = Path('artifacts/checkpoint-500/verifier.json')
    saved = json.loads(verifier_path.read_text(encoding='utf-8'))
    if not saved['complete'] or len(saved['predictions'])!=500:
        raise ValueError('Blinded checkpoint verifier incomplete')
    state_path = Path('artifacts/analysis-10000-final/state.sqlite3')
    rows, events = load_state(state_path)
    responses = {e['review_ids'][0]:e['response'] for e in events if e['stage']=='jev' and e['outcome']=='succeeded' and e['label_config']==configuration(config)}
    by_key = {row['key']:responses[row['source']['review_id']] for row in rows if row['source']['review_id'] in responses}
    candidates = []
    for row in rows:
        source = row['source']
        rid = source['review_id']
        if rid in golden_ids or source['review_text'] in golden_texts or rid not in saved['predictions'] or not row['result']:
            continue
        if row['result']['label_config']!=configuration(config):
            raise ValueError('Human review source has wrong final hash')
        jev = parse_jev(by_key[row['key']],config['enrichment']['confidence_threshold'],config['enrichment']['probability_margin_threshold'],require_auxiliary=True)
        verifier = saved['predictions'][rid]
        disagreement = [field for field in FIELDS if value(jev,field)!=value(verifier,field)]
        if disagreement:
            keys = ('topic','intent','severity','sentiment','needs_review')
            candidates.append({'review_id':rid,'review_text':source['review_text'],'disagreements':disagreement,
                               'jev':{key:jev[key] for key in keys},'verifier':{key:verifier[key] for key in keys}})
    cases = select(candidates,limit)
    session = {'version':'verifier-human-review-v1','label_config':configuration(config),
               'procedure':'Development checkpoint verifier vs final-hash operational Jev before fallback; golden IDs AND exact golden texts excluded; terminal records excluded. Round-robin disagreement fields; unique text per case. Verdict applies only to target field. This selected disagreement sample is not an overall accuracy estimate and never rewrites labels/config.',
               'source_state_sha256':hashlib.sha256(state_path.read_bytes()).hexdigest(),
               'verifier_sha256':hashlib.sha256(verifier_path.read_bytes()).hexdigest(),
               'candidate_records':len(candidates),'cases':cases,'verdicts':{}}
    atomic_json(output,session)
    save_summary(output,session)
    return session


def summarize(session):
    cases = {case['case_id']:case for case in session['cases']}
    summary = {'selected':len(cases),'reviewed':len(session['verdicts']),
               'remaining':len(cases)-len(session['verdicts']),
               'verdicts':dict(Counter(v['verdict'] for v in session['verdicts'].values())),
               'selected_by_field':dict(Counter(c['target_field'] for c in cases.values())),
               'by_field':{field:dict(Counter(v['verdict'] for key,v in session['verdicts'].items() if cases[key]['target_field']==field)) for field in FIELDS},
               'limitation':'Stratified disagreement-only judgments of displayed target field; not corpus accuracy. Unclear is retained. Both-wrong does not invent a replacement label.',
               'model_calls':0}
    return summary


def save_summary(output, session):
    atomic_json(output.with_name(output.stem+'-summary.json'),summarize(session))


def next_case(session):
    return next((case for case in session['cases'] if case['case_id'] not in session['verdicts']),None)


def record(output, session, case_id, verdict):
    case = next_case(session)
    if case is None or case['case_id']!=case_id or verdict not in VERDICTS:
        raise ValueError('Stale/invalid review verdict; no answer saved')
    session['verdicts'][case_id] = {'verdict':verdict,'recorded_at_utc':datetime.now(UTC).isoformat()}
    atomic_json(output,session)
    save_summary(output,session)


def display(case):
    return (f"Review {case['review_id']} | judge target field: {case['target_field']}\n"
            f"--- original review text ---\n{case['review_text']}\n--- end review text ---\n"
            f"Jev: {json.dumps(case['jev'],ensure_ascii=False)}\n"
            f"Verifier: {json.dumps(case['verifier'],ensure_ascii=False)}\n"
            '1 Jev right | 2 verifier right | 3 both wrong | 4 unclear | q quit')


def review(output=DEFAULT, limit=20, ask=input, show=print, peek=False, verdict=None, case_id=None):
    if show is print and hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    output.parent.mkdir(parents=True,exist_ok=True)
    lock = output.with_suffix(output.suffix+'.lock')
    with lock.open('x',encoding='utf-8') as stream:
        stream.write(str(os.getpid()))
    session = None
    try:
        session = prepare(output,limit)
        if verdict is not None:
            record(output,session,case_id,verdict)
        if peek or verdict is not None:
            case = next_case(session)
            if case:
                show(display(case))
        else:
            while case := next_case(session):
                show(display(case))
                answer = ask('Your verdict: ').strip().lower()
                if answer=='q':
                    break
                choices = {str(i+1):name for i,name in enumerate(VERDICTS)}
                answer = choices.get(answer,answer.replace(' ','_'))
                if answer not in VERDICTS:
                    show('Choose 1–4, a verdict name, or q. No answer saved.')
                    continue
                record(output,session,case['case_id'],answer)
    except (EOFError,KeyboardInterrupt):
        show('Stopped safely; completed verdicts saved, unfinished case unchanged.')
    finally:
        lock.unlink()
    if session is None:
        return {'status':'stopped before session loaded','model_calls':0}
    result = summarize(session)
    show(json.dumps(result,indent=2))
    return result
