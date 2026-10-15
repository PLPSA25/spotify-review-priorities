from pathlib import Path

import pytest

from pipeline.prepare import course_helper
from pipeline.scope_export import export, propagated


def test_propagation_preserves_direct_origin_reasons_and_source_identity():
    helper = course_helper(Path('data/check_submission.py'))
    row = dict(zip(helper.FIELDS, ('alias', 'Good', '5', '0', '', '2023')))
    original = {'review_id': 'origin', 'topic': 'other', 'intent': 'praise', 'sentiment': 1,
                    'severity': 1, 'entities': [], 'evidence_quote': 'Good', 'needs_review': True,
                    'needs_review_reasons': ['missing_context'], 'label_config': 'frozen'}
    result = propagated(row, helper, {'Good': original}, {})
    assert result['cache_source_id'] == 'origin'
    assert result['source_sha256'] == helper.row_sha(row)
    assert result['needs_review_reasons'] == ['missing_context']
    row['review_id'] = 'origin'
    assert 'cache_source_id' not in propagated(row, helper, {'Good': original}, {})


def test_scope_limit_and_terminal_failures_are_distinct():
    helper = course_helper(Path('data/check_submission.py'))
    row = dict(zip(helper.FIELDS, ('a', 'outside', '1', '0', '', '2023')))
    assert propagated(row, helper, {}, {})['reason'] == 'not_classified_partial_run'
    assert propagated(row, helper, {}, {'outside': 'invalid output'})['reason'] == 'invalid output'
    row['review_text'] = '  '
    assert propagated(row, helper, {}, {})['reason'] == 'empty_review_text'


def test_export_cannot_create_ambiguous_plain_and_gzip_files(tmp_path):
    (tmp_path/'records.jsonl.gz').write_bytes(b'preserved-package')
    with pytest.raises(ValueError, match='Compressed grading export exists'):
        export(destination=tmp_path, source=tmp_path/'nonexistent.csv')
    assert not (tmp_path/'records.jsonl').exists()
    assert (tmp_path/'records.jsonl.gz').read_bytes() == b'preserved-package'
