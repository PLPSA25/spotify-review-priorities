import copy
import tomllib
from pathlib import Path

import pytest

from pipeline.fallback_options import comparison, differences, paired_verifier
from pipeline.golden_evaluation import fallback_partition, metrics
from pipeline.schema import configuration
from tests.test_enrichment import environment


def labels(**changes):
    return {'topic':'other','intent':'complaint','severity':2,'sentiment':-.5,'needs_review':True,**changes}


def test_core_change_excludes_trivial_same_sign_numeric_shift():
    items = [{'jev':labels(),'final':labels(sentiment=-.4,needs_review=False)}]
    result = comparison(items,'jev','final')
    assert result['any_core_label_changed']==0
    assert result['by_field']['needs_review']['different']==1
    error = differences(labels(),labels(severity=4,sentiment=0))
    assert error['severity_within_one'] and error['sentiment_sign']


def test_paired_verifier_corrections_do_not_hide_regressions():
    items = [{'jev':labels(topic='playback'),'final':labels(),'verifier':labels()},
             {'jev':labels(),'final':labels(topic='billing'),'verifier':labels()}]
    result = paired_verifier(items)
    assert result['by_field']['topic']=={'corrected_relative_to_verifier':1,'regressed_relative_to_verifier':1}


def test_fallback_cap_does_not_change_frozen_hash():
    config = tomllib.loads(Path('config.toml').read_text())
    original = configuration(config)
    original_fraction = config['controls']['fallback_fraction']
    for fraction in (.1,.2,.3):
        alternative = copy.deepcopy(config)
        alternative['controls']['fallback_fraction'] = fraction
        assert configuration(alternative)==original
    assert config['controls']['fallback_fraction']==original_fraction


def test_fallback_split_inherits_cache_ancestry_but_extraction_is_not_fallback(tmp_path):
    _, _, state, _, _ = environment(tmp_path,('tiny','tiny','different'))
    state.save_call({'request_id':'fallback-call','review_ids':['0'],'stage':'fallback','role':'enrich',
                     'outcome':'succeeded','label_config':state.label_config})
    state.save_call({'request_id':'extract-call','review_ids':['2'],'stage':'extract','role':'enrich',
                     'outcome':'succeeded','label_config':state.label_config})
    assert fallback_partition(state.path,{'0','1','2'},state.label_config)=={'0':True,'1':True,'2':False}
    with pytest.raises(ValueError,match='missing'):
        fallback_partition(state.path,{'unknown'},state.label_config)


def test_empty_fallback_group_has_no_claimed_accuracy():
    result = metrics({},{})
    assert all(item['agreement'] is None for item in result['agreement'].values() if 'agreement' in item)
