import pytest

from pipeline.dashboard_snapshot import aggregate_records, canonical, validate_ranking


def record(rid, **extra):
    return dict(review_id=rid, status='completed', topic='other', intent='complaint', severity=2,
                sentiment=-0.5, needs_review=True, needs_review_reasons=['missing_context'],
                label_config='frozen', **extra)


def test_row_and_distinct_result_denominators_and_overlapping_flags():
    original = record('a')
    alias = record('b', cache_source_id='a')
    alias['needs_review_reasons'] += ['language_non_english']
    result = aggregate_records([original, alias,
        {'status':'quarantined','reason':'empty_review_text'},
        {'status':'quarantined','reason':'not_classified_partial_run'},
        {'status':'quarantined','reason':'failed_after_permitted_repair'}])
    assert result['counts'] == {'total_rows':5,'completed_rows':2,'direct_original_rows':1,
         'needs_review_rows':2,'cache_reused_rows':1,'empty_rows':1,'nonempty_rows':4,
         'out_of_scope_rows':1,'terminal_rows':1}
    assert result['flag_reasons'] == {'missing_context':2,'language_non_english':1}


def test_flags_and_hashes_fail_closed():
    row = record('a')
    row['needs_review'] = False
    with pytest.raises(ValueError,match='Flag/reason'):
        aggregate_records([row])
    assert canonical({'z':1.0,'a':'é'}) == '{"a":"é","z":1}'


def test_rank_guard_rejects_wrong_priority_and_totals():
    rows=[{'rank':'1','issue_id':'a','complaint_count':'2','severity_sum':'4','priority_score':'4'}]
    validate_ranking(rows,2,4)
    with pytest.raises(ValueError,match='totals'):
        validate_ranking(rows,3,4)
    rows[0]['priority_score']='5'
    with pytest.raises(ValueError,match='Priority'):
        validate_ranking(rows,2,4)
