"""Recover unambiguous validated message blocks offline; preserve original failures."""

import copy
import json
import sqlite3
from pathlib import Path

from pipeline.classify import parse_luna_batch
from pipeline.prepare import atomic_json
from pipeline.schema import canonical


def recover(directory=Path('artifacts/checkpoint-500')):
    path=directory/'verifier.json'
    saved=json.loads(path.read_text(encoding='utf-8'))
    with sqlite3.connect(f'file:{directory.as_posix()}/state.sqlite3?mode=ro',uri=True) as db:
        sources={rid:json.loads(source) for rid,source in db.execute('SELECT review_id,source FROM reviews')}
        events=[json.loads(event) for event, in db.execute('SELECT event FROM calls')]
    recovered={}
    conflicts=[]
    evidence=[]
    for event in events:
        if event['role']!='verify' or event['outcome']!='failed' or 'response' not in event:
            continue
        expected={rid:sources[rid] for rid in event['review_ids']}
        candidates={rid:[] for rid in expected}
        for index,block in enumerate(event['response'].get('output',[])):
            for part in block.get('content',[]):
                if part.get('type')!='output_text':
                    continue
                single=copy.deepcopy(event['response'])
                single['output']=[{'content':[part]}]
                try:
                    parsed=parse_luna_batch(single,expected,{rid:{} for rid in expected},False,event['label_config'])
                except (ValueError,KeyError,TypeError):
                    continue
                for rid,record in parsed['valid'].items():
                    candidates[rid].append((index,record))
        for rid,items in candidates.items():
            if rid in saved['predictions'] or not items:
                continue
            if len({canonical(record) for _,record in items})!=1:
                conflicts.append(rid)
                continue
            index,record=items[0]
            recovered[rid]=record
            evidence.append({'review_id':rid,'request_id':event['request_id'],'output_message_index':index})
    saved['predictions'].update(recovered)
    saved['complete']=len(saved['predictions'])==500
    saved['offline_recovery']={'new_valid_predictions':len(recovered),'conflicting_ids':conflicts,
                               'evidence':evidence,'method':'Validate each output_text message independently; require identical candidates when multiple valid blocks exist. Original failed call events unchanged.'}
    atomic_json(path,saved)
    atomic_json(directory/'verifier_recovery.json',saved['offline_recovery'])
    print(json.dumps({'recovered':len(recovered),'valid_total':len(saved['predictions']),'conflicts':conflicts}))


if __name__=='__main__':
    recover()
