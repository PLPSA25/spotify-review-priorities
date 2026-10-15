"""Independent diagnostic parsing and paid transfer bounds, without network."""

import json
import tomllib
from pathlib import Path

from pipeline.classify import parse_luna_batch
from pipeline.schema import configuration
from pipeline.transfer_verify import diagnostic_payload


def test_transfer_payload_blinded_preserves_enrichment_hash_and_caps():
    config = tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    old_hash = configuration(config)
    rows = [{'review_id': str(i), 'review_text': 'Good music.'} for i in range(50)]
    payload = diagnostic_payload(rows, config)
    packed = payload['input'].split('BEGIN_UNTRUSTED_REVIEWS_JSON\n')[1].split('\nEND_UNTRUSTED_REVIEWS_JSON')[0]
    assert all(set(row) == {'review_id', 'review_text'} for row in json.loads(packed))
    assert payload['max_output_tokens'] == 10000
    assert diagnostic_payload(rows[:1], config, True)['max_output_tokens'] == 200
    assert configuration(config) == old_hash


def test_transfer_diagnostics_missing_invalid_item_retains_valid_sibling():
    sources = {rid: {'review_id': rid, 'review_text': 'Good music.', 'source_sha256': 'hash'} for rid in ('a', 'b')}
    record = {'topic': 'other', 'intent': 'praise', 'severity': 1, 'sentiment': 1,
              'needs_review': False, 'entities': [], 'evidence_quote': 'Good music.',
              'language': 'english', 'missing_context': False}
    rows = [{**record, 'review_id': 'a'}, {**record, 'review_id': 'b', 'missing_context': 'no'}]
    reply = {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps({'records': rows})}]}]}
    result = parse_luna_batch(reply, sources, {rid: {} for rid in sources}, False, 'hash', verifier_diagnostics=True)
    assert set(result['valid']) == {'a'} and set(result['errors']) == {'b'}
    assert result['valid']['a']['language'] == 'english'
    assert result['valid']['a']['missing_context'] is False
    result = parse_luna_batch(reply, sources, {rid: {} for rid in sources}, False, 'hash')
    assert not result['valid']  # Enrichment schema remains strict.
