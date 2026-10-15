"""Calibration endpoints and material-separation rules use saved values only."""

from pipeline.transfer_report import contrast, qualifies


def test_material_rule_requires_both_predictions_and_sufficient_groups():
    candidate = {'flagged': {'n': 30}, 'unflagged': {'n': 40},
                 'jev': {'difference_bootstrap_95': [.06, .3], 'relative_rate': 2},
                 'final': {'difference_bootstrap_95': [.08, .4], 'relative_rate': 1.6}}
    assert qualifies(candidate)
    candidate['final']['relative_rate'] = 1.4
    assert not qualifies(candidate)
    candidate['final']['relative_rate'] = 2
    candidate['unflagged']['n'] = 24
    assert not qualifies(candidate)


def test_contrast_counts_fields_and_empty_groups_without_invented_rates():
    names = ('topic','intent','severity_exact','severity_beyond_one','sentiment_sign','sentiment_tolerance_025')
    items = [{'review_id': rid, 'jev_disagreements': ['topic'] if rid=='a' else [],
              'final_disagreements': [], 'jev_field_errors': dict.fromkeys(names, rid=='a'),
              'final_field_errors': dict.fromkeys(names, False)} for rid in ('a','b')]
    result = contrast(items, {'a'}, [[0,1],[0,1]])
    assert result['flagged']['jev']['disagreements'] == 1
    assert result['unflagged']['jev']['rate'] == 0
    assert result['jev']['difference_bootstrap_95'] == [1,1]
    assert result['flagged']['final']['fields']['severity_beyond_one']['disagreements'] == 0
    empty = contrast(items, {'a','b'})
    assert empty['unflagged']['jev']['rate'] is None
    assert empty['jev']['difference'] is None
