"""Descriptive distribution statistics use explicit linear interpolation."""

import pytest

from pipeline.scaling_report import distribution, quantile


def test_confidence_distribution_interpolates_and_includes_endpoints():
    values=[.9,.1,.5,.3]
    assert quantile(values,0)==.1
    assert quantile(values,1)==.9
    assert quantile(values,.5)==pytest.approx(.4)
    summary=distribution(values)
    assert summary['n']==4 and summary['mean']==pytest.approx(.45)
    assert summary['p25']==pytest.approx(.25)
    assert summary['p75']==pytest.approx(.6)
