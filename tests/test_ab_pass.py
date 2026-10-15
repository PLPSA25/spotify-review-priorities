"""User's predeclared same-500-row criterion has an inclusive 3pp boundary."""

from pipeline.checkpoint_ab import assess_pass


def stats(topic,intent,rows=500):
    return {'rows':rows,'core_jev_fields':{'topic':{'disagreements':topic},'intent':{'disagreements':intent}}}


def test_both_fields_at_three_percentage_point_limit_pass():
    result = assess_pass(stats(54,37),stats(69,52))
    assert result['passes'] and result['status']=='pass'
    assert result['fields']['topic']['change_percentage_points']==3


def test_either_field_above_limit_fails_and_incomplete_cannot_pass():
    assert not assess_pass(stats(54,37),stats(70,37))['passes']
    assert not assess_pass(stats(54,37),stats(54,53))['passes']
    assert assess_pass(stats(54,37),stats(0,0,499))['status']=='inconclusive'


def test_final_failure_does_not_remove_a_successful_core_prediction():
    import tomllib
    from pathlib import Path

    from pipeline.checkpoint_ab_proposal import comparison
    from pipeline.classify import jev_payload, parse_jev
    from pipeline.providers import MockTransport
    config=tomllib.loads(Path('config.toml').read_text(encoding='utf-8'))
    response=MockTransport().request('typesafe',jev_payload('Good music.',config))
    prediction=parse_jev(response,.6,0)
    row={'source':{'review_id':'a'},'key':'key','result':None}
    event={'stage':'jev','outcome':'succeeded','review_ids':['a'],'response':response}
    result=comparison([row],[event],{'a':prediction})
    assert result['rows']==1 and result['core_jev_fields']['topic']['denominator']==1
    assert result['final_enrichment_rows']==0
