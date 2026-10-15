"""Stored-output recovery, reconstructed snapshots and owner-only dispatch."""
import json

import pytest

from pipeline.checker_resume_audit import check, grading_call_view
from pipeline.failure_policy import FailureWindow
from pipeline.graceful import run_segment
from pipeline.prepare import atomic_json
from pipeline.production import before_checkpoint, sha
from pipeline.production_recovery import recover_results, run_continuation
from pipeline.resume_evidence import snapshot
from tests.test_deterministic import setup_run
from tests.test_enrichment import environment, record


def test_stored_output_recovery_has_no_new_calls_or_charges(tmp_path):
    _,_,state,ledger,_ = environment(tmp_path,('first','second','third'))
    valid = {}
    with state.connect() as db:
        sources = [json.loads(row[0]) for row in db.execute('SELECT source FROM reviews')]
    for source in sources:
        rid = source['review_id']
        state.save_call({'request_id':'paid-'+rid,'review_ids':[rid],'run_id':'original',
                         'stage':'extract','role':'enrich','phase':'resume','outcome':'succeeded','label_config':state.label_config})
        valid[rid] = {**record(source,state.label_config),'needs_review_reasons':[]}
    state.failure_window = FailureWindow()
    before = ledger.totals()
    assert recover_results(state,valid)==3
    assert ledger.totals()==before
    assert state.counts()=={'completed':3} and state.leased_count()==0
    with state.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]==3
    with pytest.raises(ValueError,match='pending'):
        recover_results(state,valid)


def test_reconstructed_before_requires_matching_provenance_hash(tmp_path):
    reconstructed = tmp_path/'checkpoint_before.reconstructed.json'
    atomic_json(reconstructed,{'completed_ids':['original'],'label_config':'hash'})
    atomic_json(tmp_path/'checkpoint_before.reconstructed.provenance.json',{'reconstructed_sha256':sha(reconstructed)})
    assert before_checkpoint(tmp_path)==reconstructed
    reconstructed.write_text('changed')
    with pytest.raises(ValueError,match='changed'):
        before_checkpoint(tmp_path)


def test_recovery_ready_requires_explicit_recovery_mode(tmp_path):
    config,state,calls = setup_run(tmp_path/'run',8)
    state.artifact('graceful-invocation',{'run_id':calls.run_id,'label_config':state.label_config,
                   'cap':config['controls']['run_api_cap_usd'],'fallback_fraction':.34,'status':'recovery_ready'})
    with pytest.raises(ValueError,match='voluntary'):
        run_segment(state,calls,config,tmp_path/'output',resume=True)
    assert run_segment(state,calls,config,tmp_path/'output',resume=True,recovery=True)['status']=='completed'


def test_continuation_default_does_not_read_keys_or_dispatch():
    assert run_continuation()['api_calls']==0


def test_grading_view_retains_raw_phase_and_filters_incompatible_history():
    event = {'role':'enrich','label_config':'final','run_id':'old','phase':'resume'}
    result = grading_call_view(event,'production','final')
    assert result['phase']=='initial' and result['source_phase']=='resume' and result['imported']
    assert event['phase']=='resume' and 'imported' not in event
    assert grading_call_view({**event,'label_config':'old-hash'},'production','final') is None


def test_supplied_checker_resume_section_executes_offline(tmp_path):
    _,_,state,_,_ = environment(tmp_path,('first','second'))
    for phase in ('initial','resume'):
        item = state.claim(300)
        rid = item['source']['review_id']
        state.save_call({'request_id':'fake-paid-'+rid,'review_ids':[rid],'run_id':'demo',
                         'stage':'jev','role':'enrich','phase':phase,'outcome':'succeeded',
                         'label_config':state.label_config,'model':'synthetic-model',
                         'input_tokens':1,'output_tokens':0})
        state.complete(item,record(item['source'],state.label_config))
        snapshot(state.path,tmp_path/(phase+'.json'))
    result = check(state.path,tmp_path/'initial.json',tmp_path/'resume.json','demo',tmp_path/'checker.json')
    assert result['resume_rules_status']=='pass' and result['resume_flags']=={}
    assert result['new_direct_resume_logged_count']==1
    assert not result['full_submission_check']
