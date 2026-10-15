import copy
import json

import pytest

from pipeline.disagreement_review import prepare, record, review, select, summarize
from pipeline.golden_evaluation import evaluate, metrics
from pipeline.prepare import course_helper
from pipeline.schema import configuration
from tests.test_labels import fixtures


def candidates():
    labels = {'topic':'other','intent':'complaint','severity':2,'sentiment':-.5,'needs_review':True}
    return [{'review_id':str(i),'review_text':'synthetic '+str(i),'disagreements':['topic','intent','severity','sentiment_sign','needs_review'],
             'jev':labels,'verifier':labels} for i in range(30)]


def session():
    return {'version':'verifier-human-review-v1','cases':select(candidates()),'verdicts':{}}


def test_stratified_deterministic_unique_text_and_limit():
    selected = select(candidates())
    assert selected==select(list(reversed(candidates())))
    assert len(selected)==20
    assert len({case['review_text'] for case in selected})==20
    assert all(sum(case['target_field']==field for case in selected)==4 for field in ('topic','intent','severity','sentiment_sign','needs_review'))
    with pytest.raises(ValueError):
        select(candidates(),21)


def test_human_save_quit_resume_and_stale_verdict(tmp_path):
    output = tmp_path/'review.json'
    output.write_text(json.dumps(session()))
    answers = iter(('invalid','1','q'))
    result = review(output,ask=lambda _:next(answers),show=lambda _:None)
    assert result['reviewed']==1
    saved = prepare(output)
    first = saved['cases'][0]
    assert saved['verdicts'][first['case_id']]['verdict']=='jev_right'
    with pytest.raises(ValueError,match='Stale'):
        record(output,saved,first['case_id'],'verifier_right')
    second = saved['cases'][1]
    record(output,saved,second['case_id'],'unclear')
    assert summarize(saved)['reviewed']==2
    assert not output.with_suffix('.json.lock').exists()


def test_interruption_does_not_invent_verdict(tmp_path):
    output = tmp_path/'review.json'
    output.write_text(json.dumps(session()))
    def stopped(_):
        raise KeyboardInterrupt
    assert review(output,ask=stopped,show=lambda _:None)['reviewed']==0
    assert json.loads(output.read_text())['verdicts']=={}


def test_unicode_review_on_legacy_windows_output(tmp_path,monkeypatch):
    import io
    output = tmp_path/'review.json'
    saved = session()
    saved['cases'][0]['review_text']='synthetic 😩 café'
    output.write_text(json.dumps(saved),encoding='utf-8')
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw,encoding='cp1252')
    monkeypatch.setattr('sys.stdout',stream)
    assert review(output,ask=lambda _:'q')['reviewed']==0
    stream.flush()
    assert '😩' in raw.getvalue().decode('utf-8')


def test_human_review_concurrent_session_is_rejected(tmp_path):
    output = tmp_path/'review.json'
    output.with_suffix('.json.lock').write_text('synthetic existing session')
    with pytest.raises(FileExistsError):
        review(output,show=lambda _:None)


def test_golden_metrics_detect_planted_error_and_keep_missing_denominator():
    truth = {'topic':'other','intent':'complaint','severity':2,'sentiment':-.5,'needs_review':True}
    human = {str(i):copy.deepcopy(truth) for i in range(3)}
    predictions = {'0':copy.deepcopy(truth),'1':dict(truth,topic='playback',severity=3,sentiment=0,needs_review=False)}
    result = metrics(human,predictions)
    assert result['agreement']['topic']['agree']==1
    assert result['agreement']['topic']['denominator']==3
    assert result['agreement']['severity_within_one']['agree']==2
    assert result['agreement']['severity']['agree']==1
    assert result['agreement']['sentiment_sign']['agree']==1
    assert result['agreement']['needs_review']['agree']==1
    assert result['missing_predictions']==1
    assert all(sum(map(sum,table['counts']))==3 for table in result['confusion'].values())
    assert result['agreement']['severity_mae']['denominator_available_predictions']==2


def test_evaluation_only_reads_synthetic_answers_and_writes_confusions(tmp_path):
    import tomllib
    from pathlib import Path
    source, labels = fixtures(tmp_path)
    original = labels.read_bytes()
    helper = course_helper(Path('data/check_submission.py'))
    config = tomllib.loads(Path('config.toml').read_text())
    predictions = []
    for row in list(helper.csv_rows(source))[:49]:
        predictions.append({'review_id':row['review_id'],'source_sha256':helper.row_sha(row),
                            'status':'completed','label_config':configuration(config),
                            'topic':'other','intent':'unclear','severity':1,'sentiment':0,
                            'entities':[],'evidence_quote':row['review_text'],
                            'needs_review':True,'needs_review_reasons':['missing_context']})
    path = tmp_path/'predictions.jsonl'
    path.write_text('\n'.join(json.dumps(row) for row in predictions),encoding='utf-8')
    result = evaluate(path,tmp_path/'report',labels,source)
    assert result['agreement']['topic']['agree']==49
    assert result['agreement']['topic']['denominator']==50
    assert result['missing_predictions']==1
    assert result['entities_evaluated'] is False
    assert result['model_calls']==0
    assert labels.read_bytes()==original
    assert (tmp_path/'report'/'severity_within_one-confusion.csv').is_file()


def test_evaluation_does_not_open_human_answers_without_predictions(tmp_path,monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('Human answers must not be opened before prediction preflight')
    monkeypatch.setattr('pipeline.golden_evaluation.validate_golden',forbidden)
    with pytest.raises(FileNotFoundError):
        evaluate(tmp_path/'missing-predictions.jsonl',tmp_path/'report')
