"""Provenance import preserves aliases and terminal failures without new calls."""

import csv
import json
from pathlib import Path

import pytest

from pipeline.analysis_run import prepare_extension, run
from pipeline.classify import enrich_one
from tests.test_enrichment import environment


def test_extension_reuses_successes_preserves_terminal_and_only_new_text_pending(tmp_path):
    base_dir = tmp_path/'base'
    base_dir.mkdir()
    _,config,state,_,calls = environment(base_dir,('good','failed'))
    first=state.claim(300)
    if first['source']['review_text']=='failed':
        state.quarantine(first,'invalid_model_output_after_retry')
        enrich_one(state,calls,state.claim(300),config,0)
    else:
        enrich_one(state,calls,first,config,0)
        state.quarantine(state.claim(300),'invalid_model_output_after_retry')
    with state.connect() as db:
        originals=[json.loads(row[0]) for row in db.execute('SELECT source FROM reviews')]
        prior_calls=db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]
    source=tmp_path/'analysis.csv'
    fields=['review_id','review_text','review_rating','review_likes','app_version','review_timestamp']
    with source.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader()
        writer.writerows({key:row[key] for key in fields} for row in originals)
        template={key:originals[0][key] for key in fields}
        writer.writerow({**template,'review_id':'alias','review_text':'good'})
        writer.writerow({**template,'review_id':'new','review_text':'new text'})
    extended=prepare_extension(state.path,tmp_path/'analysis',state.label_config,source,Path('data/manifest.json'))
    assert extended.counts()=={'completed':2,'pending':1,'quarantined':1}
    with extended.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]==prior_calls
        alias=json.loads(db.execute("SELECT result FROM reviews WHERE review_id='alias'").fetchone()[0])
        assert alias['cache_source_id'] in {'0','1'}
        assert alias['needs_review_reasons']==[]
        assert db.execute("SELECT reason FROM reviews WHERE text='failed'").fetchone()[0]=='invalid_model_output_after_retry'
    with pytest.raises(ValueError,match='exists'):
        prepare_extension(state.path,tmp_path/'analysis',state.label_config,source,Path('data/manifest.json'))


def test_analysis_requires_approval_before_key_access(monkeypatch):
    monkeypatch.setattr('pipeline.analysis_run.keys_from_env',lambda _:pytest.fail('Unapproved key access'))
    with pytest.raises(ValueError,match='new explicit yes'):
        run(False)
