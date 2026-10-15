"""Final reason integrity, sticky context/language and cache propagation."""

import copy
import json
import tomllib
from pathlib import Path

import pytest

from pipeline.classify import jev_payload, luna_payload, parse_jev, parse_luna
from pipeline.providers import MockTransport
from pipeline.schema import configuration, validate_record


def example():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    source = {'review_id':'a','source_sha256':'hash','review_text':'Music fails.'}
    response = MockTransport().request('typesafe',jev_payload(source['review_text'],config))
    response['answers']['topic']['confidence'] = .4
    response['answers']['missing_context']['noul'] = .8
    labels = parse_jev(response,.6,0,True)
    return config,source,labels


def reply(source, reasons, flagged=None, extraction=False):
    row = {'review_id':source['review_id'],'entities':[],'evidence_quote':source['review_text'],
           'needs_review_reasons':reasons}
    if not extraction:
        row.update(topic='other',intent='unclear',severity=1,sentiment=0,
                   needs_review=bool(reasons) if flagged is None else flagged)
    return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps({'records':[row]})}]}]}


def test_fallback_clears_only_initial_low_confidence_and_context_is_sticky():
    _,source,labels = example()
    assert labels['needs_review_reasons'] == ['missing_context','low_confidence']
    result = parse_luna(reply(source,[]),source,labels,False,'final',require_reasons=True)
    assert result['needs_review_reasons'] == ['missing_context'] and result['needs_review']
    labels['needs_review_reasons'] = ['low_confidence']
    result = parse_luna(reply(source,[]),source,labels,False,'final',require_reasons=True)
    assert result['needs_review_reasons'] == [] and not result['needs_review']


@pytest.mark.parametrize('language',['language_non_english','language_not_understood'])
def test_each_original_language_reason_persists(language):
    _,source,labels = example()
    labels.update(nonenglish=True,needs_review_reasons=[language,'low_confidence'])
    result = parse_luna(reply(source,[]),source,labels,False,'final',require_reasons=True)
    assert result['needs_review_reasons'] == [language] and result['needs_review']


def test_luna_context_and_language_signals_are_saved_even_without_jev_signal():
    _,source,_ = example()
    result = parse_luna(reply(source,['missing_context','language_non_english']),source,
                      {'needs_review_reasons':[]},False,'final',require_reasons=True)
    assert result['needs_review_reasons'] == ['language_non_english','missing_context']
    validate_record(result,source,'final',require_reasons=True)


def test_extraction_preserves_low_confidence_and_unions_model_context():
    _,source,labels = example()
    labels.update(topic='other',intent='unclear',severity=1,sentiment=0,needs_review_reasons=['low_confidence'])
    result = parse_luna(reply(source,['missing_context'],extraction=True),source,labels,True,'final',require_reasons=True)
    assert result['needs_review_reasons'] == ['missing_context','low_confidence']


@pytest.mark.parametrize('reasons,flagged',[([],True),(['missing_context'],False),(['bogus'],True),(['missing_context','missing_context'],True)])
def test_bad_model_reason_boolean_or_enum_is_rejected(reasons,flagged):
    _,source,labels = example()
    with pytest.raises(ValueError):
        parse_luna(reply(source,reasons,flagged),source,labels,False,'final',require_reasons=True)


def test_reason_field_required_for_new_schema_and_hash_excludes_workers():
    config,source,labels = example()
    bad = reply(source,[])
    row = json.loads(bad['output'][0]['content'][0]['text'])['records'][0]
    del row['needs_review_reasons']
    bad['output'][0]['content'][0]['text'] = json.dumps({'records':[row]})
    with pytest.raises(ValueError,match='fields'):
        parse_luna(bad,source,labels,False,'final',require_reasons=True)
    for extraction in (False,True):
        schema = luna_payload(source,labels,config,extraction)['text']['format']['schema']
        assert 'needs_review_reasons' in schema['properties']['records']['items']['required']
    changed = copy.deepcopy(config)
    changed['controls'].update(max_workers=8,fallback_fraction=.01)
    assert configuration(changed) == configuration(config)
    changed['enrichment']['needs_review_policy'] = 'different-policy'
    assert configuration(changed) != configuration(config)


def test_cache_alias_copies_explicit_reasons_and_flags(tmp_path):
    from pipeline.classify import enrich_one
    from tests.test_enrichment import environment
    _,config,state,_,calls = environment(tmp_path,('duplicate','duplicate'))
    class Context(MockTransport):
        def request(self,provider,payload):
            result = super().request(provider,payload)
            if provider=='typesafe':
                result['answers']['missing_context']['noul'] = .8
            return result
    calls.transport = Context()
    enrich_one(state,calls,state.claim(300),config,0)
    with state.connect() as db:
        records = [json.loads(row[0]) for row in db.execute('SELECT result FROM reviews')]
    assert len(records)==2
    assert all(record['needs_review_reasons']==['missing_context'] and record['needs_review'] for record in records)
    assert sum('cache_source_id' in record for record in records)==1


def test_reason_requirement_persists_when_reopening_store(tmp_path):
    from pipeline.state import State
    first = State(tmp_path/'state.sqlite3','final-hash',require_reasons=True)
    assert first.require_reasons
    assert State(first.path,'final-hash').require_reasons


def test_ab_cannot_dispatch_without_confirmation(monkeypatch):
    from pipeline.checkpoint_ab import run
    monkeypatch.setattr('pipeline.checkpoint_ab.keys_from_env',lambda _:pytest.fail('No key access without approval'))
    with pytest.raises(ValueError,match='Explicit A/B yes'):
        run(False)
