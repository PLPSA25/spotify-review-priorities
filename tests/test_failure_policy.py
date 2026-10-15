"""Terminal item failure is durable and does not prevent later valid work."""

import pytest

from pipeline.calibration import field_disagreement
from pipeline.calls import InvalidOutput
from pipeline.failure_policy import FailureWindow, SystemicFailure
from pipeline.verify_policy import finalize_batch


def test_failed_repair_persists_terminal_and_later_batch_runs():
    predictions, terminal, snapshots, sent = {}, {}, [], []
    monitor=FailureWindow()

    def send(batch,repair):
        sent.append((list(batch),repair))
        if 'bad' in batch:
            raise InvalidOutput('Invalid exact quote')
        return {'valid':{'good':{'review_id':'good'}},'errors':{}}

    def persist():
        snapshots.append((dict(predictions),dict(terminal)))

    finalize_batch({'bad':{}},send,predictions,terminal,monitor,persist)
    finalize_batch({'good':{}},send,predictions,terminal,monitor,persist)
    assert terminal['bad']['status']=='terminally_failed'
    assert set(predictions)=={'good'}
    assert sent==[(['bad'],False),(['bad'],True),(['good'],False)]
    assert snapshots[0][1]['bad']['status']=='terminally_failed'


def test_systemic_window_counts_final_items_not_attempts():
    monitor=FailureWindow()
    for index in range(100):
        monitor.record(str(index),False)
    for index in range(5):
        monitor.record('bad'+str(index),True)
    monitor.record('bad0',True)  # duplicate notification cannot inflate failure rate
    with pytest.raises(SystemicFailure,match='6/100'):
        monitor.record('sixth',True)


def test_single_failure_does_not_halt_short_run():
    monitor=FailureWindow()
    monitor.record('bad',True)
    for index in range(19):
        monitor.record(str(index),False)
    assert sum(monitor.outcomes)==1


def test_severity_tolerance_and_sentiment_sign_include_neutral():
    a={'topic':'other','intent':'praise','severity':2,'sentiment':-.1}
    b={**a,'severity':3,'sentiment':0}
    result=field_disagreement(a,b)
    assert result['severity_exact'] and not result['severity_beyond_one']
    assert result['sentiment_sign'] and not result['sentiment_tolerance_025']
    assert field_disagreement(a,{**b,'severity':4})['severity_beyond_one']
