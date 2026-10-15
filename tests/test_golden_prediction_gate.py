import csv
import json
import sqlite3
import tomllib
from contextlib import closing
from pathlib import Path

import pytest

from pipeline import golden_predictions
from pipeline.schema import configuration
from pipeline.state import State


def test_golden_plan_reuses_exact_text_without_reading_human_answers(tmp_path, monkeypatch):
    config = tomllib.loads(Path('config.toml').read_text())
    base = tmp_path/'state.sqlite3'
    state = State(base,configuration(config))
    with state.connect() as db:
        db.execute("INSERT INTO work(key,text,origin_id,status) VALUES ('cached','reusable','original','completed')")
    source = tmp_path/'unlabeled.csv'
    fields = ('review_id','review_text','review_rating','review_likes','app_version','review_timestamp')
    with source.open('w',newline='',encoding='utf-8') as stream:
        writer = csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        for i in range(50):
            writer.writerow(dict(zip(fields,(str(i),'reusable' if i<6 else 'new text '+str(i),'1','0','','2023'))))
    monkeypatch.setattr(golden_predictions,'BASE',base)
    monkeypatch.setattr(golden_predictions,'SOURCE',source)
    monkeypatch.setattr(golden_predictions,'PLAN',tmp_path/'proposal.json')
    plan = golden_predictions.build_plan()
    assert plan['reusable_golden_ids']==6
    assert plan['new_distinct_texts']==44
    assert plan['maximum_calls']==4*(44+int(44*config['controls']['fallback_fraction']))
    assert plan['worst_case_nanodollars']==sum(plan['cost_bounds_nanodollars'].values())
    assert json.loads((tmp_path/'proposal.json').read_text())==plan
    with closing(sqlite3.connect(base)) as db:
        assert db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]==0


def test_golden_paid_dispatch_needs_confirmation(tmp_path):
    with pytest.raises(ValueError,match='Explicit yes'):
        golden_predictions.run(tmp_path/'nonexistent.json',False)
