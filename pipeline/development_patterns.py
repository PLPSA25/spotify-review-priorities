"""Offline development-only evidence; never reads golden answers or evaluation."""
import csv
import json
from collections import Counter
from pathlib import Path

from pipeline.classify import parse_jev
from pipeline.prepare import atomic_json
from pipeline.scaling_report import load_state


def patterns(text, language=None):
    text = text.lower()
    found = []
    for name, terms in {
        'ads':('advert',' ads','ad ','add starts'),
        'recommendations_lyrics':('recommend','lyric','mixes','podcast','song','catalog'),
        'billing_premium':('premium','pay','subscrib','charg','expensive'),
        'mixed_issue':(' but ','however','1-','2-'),
        'general_evaluation':('good','great','best','worst','awesome','sucks','amazing','love','hate'),
        'boycott_unrelated':('boycott','sweden','quran','qur\'an'),
        'historical_resolution':('update:','old post','working again'),
        'blocked_restricted_function':('cannot',"can't",'not work','not play','offline','stops','restricted'),
        'feature_request':('please','would','ability to','do something'),
    }.items():
        if any(term in text for term in terms):
            found.append(name)
    if language and language != 'english':
        found.append('non_english_or_not_understood')
    return found or ['other']


def build():
    rows, events = load_state(Path('artifacts/analysis-10000-final/state.sqlite3'))
    by_id = {row['source']['review_id']:row for row in rows}
    with Path('data/golden_50_to_label.csv').open(encoding='utf-8-sig',newline='') as stream:
        excluded = list(csv.DictReader(stream))  # source only, no human labels
    excluded_ids = {r['review_id'] for r in excluded}
    excluded_texts = {r['review_text'] for r in excluded}
    responses = {by_id[e['review_ids'][0]]['key']:e['response'] for e in events
                 if e['stage']=='jev' and e['outcome']=='succeeded'}
    unique = {}
    for path in ('artifacts/checkpoint-500/verifier.json','artifacts/scaling/transfer-verifier/verifier.json'):
        for rid, verifier in sorted(json.loads(Path(path).read_text(encoding='utf-8'))['predictions'].items()):
            if rid not in by_id or rid in excluded_ids:
                continue
            row = by_id[rid]
            text, key = row['source']['review_text'],row['key']
            if text in excluded_texts or not row['result'] or key not in responses:
                continue
            reply = responses[key]
            jev = parse_jev(reply,.60,0,require_auxiliary=True)
            fields = [f for f in ('topic','intent','severity') if jev[f]!=verifier[f]]
            unique.setdefault(key,{'review_id':rid,'text':text,'jev':jev,'verifier':verifier,
                                  'disagreements':fields,'patterns':patterns(text,reply['answers']['language']['choice'])})
    items = list(unique.values())
    human = json.loads(Path('evals/verifier-human-review.json').read_text(encoding='utf-8'))
    cases = [{**case,'patterns':patterns(case['review_text']),
              'verdict':human['verdicts'][case['case_id']]['verdict']} for case in human['cases']]
    categories = sorted({p for item in items for p in item['patterns']})
    summary = {}
    for category in categories:
        selected = [i for i in items if category in i['patterns']]
        reviewed = [i for i in cases if category in i['patterns']]
        summary[category] = {'texts':len(selected),'disagree_any_target_field':sum(bool(i['disagreements']) for i in selected),
                             'field_disagreements':dict(Counter(f for i in selected for f in i['disagreements'])),
                             'human_cases':len(reviewed),'human_verdicts':dict(Counter(i['verdict'] for i in reviewed))}
    result = {'golden_labels_or_results_read':False,'unique_texts':len(items),
              'method':'Overlapping lexical screening categories, NOT semantic error labels. Includes agreements as denominator. Non-English uses stored Jev language. Manually inspect examples before asserting violations.',
              'same_model_caution':'Verifier and fallback are both Luna. Blinding hides Jev output but does not remove shared-model bias. Agreement gain is partly self-agreement. Owner verdicts are independent human evidence; selected 20 are not population accuracy.',
              'summary':summary,'items':items,'human_cases':cases}
    atomic_json(Path('docs/development-pattern-evidence.json'),result)
    print(json.dumps({'n':len(items),'summary':summary},indent=2))
    return result


if __name__=='__main__':
    build()
