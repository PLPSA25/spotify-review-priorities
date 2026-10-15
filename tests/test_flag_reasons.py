"""Observability must not turn provisional signals into invented final reasons."""

import copy
import tomllib
from pathlib import Path

from pipeline.classify import jev_payload
from pipeline.flag_reasons import describe
from pipeline.providers import MockTransport


def test_cleared_flags_are_exported_as_initial_only_without_mutation():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    response = MockTransport().request('typesafe',jev_payload('Music will not play.',config))
    response['answers']['topic']['confidence'] = .4
    response['answers']['missing_context']['noul'] = .8
    record = {'review_id':'a','label_config':'unchanged','needs_review':False}
    before = copy.deepcopy((response,record))
    result = describe(response,record,True)
    assert result['initial_missing_context'] and result['initial_low_confidence']
    assert result['initial_flag_cleared_by_fallback']
    assert result['final_reason_attribution'] == []
    assert (response,record) == before


def test_fallback_flag_without_language_requires_unknown_final_reason():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    response = MockTransport().request('typesafe',jev_payload('Music will not play.',config))
    record = {'review_id':'a','label_config':'unchanged','needs_review':True}
    result = describe(response,record,True)
    assert result['final_reason_attribution'] == ['fallback_judgment_unattributed']
    assert not result['final_reason_complete']
