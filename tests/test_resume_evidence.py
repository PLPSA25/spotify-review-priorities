import json

import pytest

from pipeline.prepare import atomic_json
from pipeline.resume_evidence import audit, snapshot
from tests.test_enrichment import environment, record


def finish(state, item, phase='initial'):
    rid = item['source']['review_id']
    state.save_call({'request_id':'synthetic-call-'+rid,'run_id':'demo','phase':phase,'role':'enrich',
                     'outcome':'succeeded','review_ids':[rid],'stage':'jev',
                     'label_config':state.label_config,'cost_nanodollars':1,'simulated':False})
    state.complete(item,record(item['source'],state.label_config))


def test_recorded_resume_proves_strict_growth_and_paid_new_original(tmp_path):
    _, _, state, _, _ = environment(tmp_path,('first','second'))
    item = state.claim(300)
    finish(state,item)
    before = tmp_path/'before.json'
    snapshot(state.path,before)
    item = state.claim(300)
    rid = item['source']['review_id']
    finish(state,item,'resume')
    after = tmp_path/'after.json'
    snapshot(state.path,after)
    result = audit(state.path,before,after,{'demo'},tmp_path/'audit.json')
    assert result['status']=='pass'
    assert result['before_strict_subset_after']
    assert result['new_direct_paid_resume_ids']==[rid]
    assert result['resume_enrich_ids_in_before']==[]
    # An imported historical resume must not masquerade as this demonstration.
    with pytest.raises(ValueError,match='evidence failed'):
        audit(state.path,before,after,{'other-run'},tmp_path/'invalid.json')


def test_resume_audit_rejects_relabel_and_non_strict_growth(tmp_path):
    _, _, state, _, _ = environment(tmp_path,('first',))
    item = state.claim(300)
    finish(state,item)
    before = tmp_path/'before.json'
    snapshot(state.path,before)
    with pytest.raises(ValueError):
        audit(state.path,before,before,{'demo'},tmp_path/'audit.json')
    assert json.loads((tmp_path/'audit.json').read_text())['status']=='fail'
    with pytest.raises(ValueError,match='overwrite'):
        snapshot(state.path,state.path)
    with pytest.raises(ValueError,match='overwrite'):
        audit(state.path,before,before,{'demo'},before)
    with pytest.raises(ValueError,match='Explicit'):
        audit(state.path,before,before,set(),tmp_path/'audit.json')


def test_snapshot_keeps_only_declared_scope_ids(tmp_path):
    _, _, state, _, _ = environment(tmp_path,('first','second'))
    while item := state.claim(300):
        finish(state,item)
    source = tmp_path/'scope.csv'
    source.write_text('review_id\n1\n')
    saved = snapshot(state.path,tmp_path/'checkpoint.json',source)
    assert saved['completed_ids']==['1']
    atomic_json(tmp_path/'check.json',saved)
